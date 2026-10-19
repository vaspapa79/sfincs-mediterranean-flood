"""Render sfincs_build.yml from the template and invoke `hydromt build sfincs`.

Optional blocks (rendered only when the relevant config section enables them):
  - infiltration  -> setup_cn_infiltration (needs cn_raster in data_catalog)
  - wind_pressure -> setup_wind_forcing_from_grid + setup_pressure_forcing_from_grid
  - coastal_bc    -> harness v1.3: pavbnd: 1 in setup_config (legacy; SFINCS treats pavbnd <= 1 as
                     "no correction", see PAVBND_REF_PA);
                     harness v1.4: pavbnd: 101325 (reference pressure, Pa) + water-level boundary
                     points with bzs = 0 m injected post-build (inject_waterlevel_bnd).
  - harness v1.4  -> setup_precip_forcing_from_grid gets the time convention of the rain source
                     (precip_forcing_kwargs): IMERG rates left-labelled, ERA5 accumulations right-labelled.

Upstream Q is injected post-build (sfincs.src + sfincs.dis + sfincs.inp patch)
to sidestep a pandas-2.x incompatibility in hydromt-sfincs's
setup_discharge_forcing — same workaround used by strymonas_forecast_v2. The
v1.4 water-level boundary uses the same post-build route for the same reason
(set_forcing_1d calls RangeIndex.is_integer, removed in pandas 3).
"""
from __future__ import annotations

import shutil
import string
import subprocess
import sys
from pathlib import Path

from _common import SKILL_DIR, load_config

# --- harness v1.4 constants (CODE-12) ---------------------------------------------------------
# D2: SFINCS v2.3.0 (sfincs_boundaries.f90:796-800) adds (pavbnd - p_atm)/(rhow*g) to the boundary
# water level only when pavbnd > 1.0, with pavbnd read as a REAL in Pa (sfincs_input.f90:93,
# default 0.0). The published value 1 is therefore "off". v1.4 writes the standard atmosphere.
PAVBND_REF_PA = 101325.0
# D2: spacing of the water-level boundary points along the msk=2 cells [m] — the hydromt_sfincs
# setup_waterlevel_bnd_from_mask default (10 km); the ERA5 MSLP field (~28 km) is smooth at this scale
# and SFINCS evaluates the correction per boundary CELL anyway (patmb(ib), sfincs_meteo.f90:1328-1335).
BND_SPACING_M = 10000.0
# D1: time convention of each rain source for setup_precip_forcing_from_grid (hydromt_sfincs 1.2.2).
# IMERG half-hourly files carry the mean rate [mm/h] stamped at the START of the 30-min window;
# ERA5 `tp` is accumulated over the hour ENDING at the validity time (ECMWF ERA5 documentation),
# which hydromt converts to a left-labelled rate with time_label=right (identical to the v1.3 default).
_PRECIP_TIME_CONVENTION = {
    "imerg_half_hourly": {"cumulative_input": False, "time_label": "left"},
    "era5_hourly": {"cumulative_input": True, "time_label": "right"},
}


def precip_forcing_kwargs(cfg) -> dict:
    """Extra setup_precip_forcing_from_grid kwargs: {} for v1.3 (hydromt defaults, as published)."""
    if cfg.harness_version == "v1.3":
        return {}
    try:
        return dict(_PRECIP_TIME_CONVENTION[cfg.rain_source])
    except KeyError:
        raise ValueError(f"harness v1.4: no precipitation time convention registered for "
                         f"rain_source {cfg.rain_source!r}") from None


def _precip_extra(cfg) -> str:
    def fmt(v):
        return str(v).lower() if isinstance(v, bool) else str(v)
    return "".join(f"\n  {k}: {fmt(v)}" for k, v in precip_forcing_kwargs(cfg).items())


def _infiltration_block(cfg) -> str:
    if not cfg.infiltration["enabled"]:
        return ""
    return (
        "\nsetup_cn_infiltration:\n"
        "  cn: cn_raster\n"
    )


def _wind_block(cfg) -> str:
    if not cfg.wind_pressure["enabled"]:
        return ""
    return (
        "\nsetup_wind_forcing_from_grid:\n"
        "  wind: era5_hourly\n"
    )


def _pressure_block(cfg) -> str:
    if not cfg.wind_pressure["enabled"]:
        return ""
    return (
        "\nsetup_pressure_forcing_from_grid:\n"
        "  press: era5_hourly\n"
    )


def _pavbnd_line(cfg) -> str:
    if not cfg.coastal_bc["enabled"]:
        return ""
    if cfg.harness_version == "v1.4":
        return f"\n  pavbnd: {int(PAVBND_REF_PA)}"
    pav = int(cfg.coastal_bc["pavbnd"])
    return f"\n  pavbnd: {pav}"


# --- harness v1.4 / D4 coastal set-up (CODE-13) ---------------------------------------------
# D4-3: SFINCS v2.3.0 initialises zs(nm) = max(z_zmin(nm), zsini) (sfincs_initial_conditions.F90:43,
# 98-100), so a very low zsini starts every active cell dry regardless of zb (the published zsini = 0
# started every cell with zb < 0 wet: lagoons, polders, DEM pits).
ZSINI_DRY = -9999


def open_sea_split(active, dep):
    """Split the active dep <= 0 cells into (i) open sea — connected to the grid edge through dep <= 0
    cells (4-connectivity, the face connectivity SFINCS fluxes use) — and (ii) inland dep <= 0 cells.
    Returns (sea0, open_sea, inland) boolean arrays of the grid shape."""
    import numpy as np
    from scipy import ndimage

    active = np.asarray(active, dtype=bool)
    dep = np.asarray(dep, dtype=float)
    sea0 = active & np.isfinite(dep) & (dep <= 0)
    lab, _ = ndimage.label(sea0, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    edge = np.zeros_like(sea0)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    labs = np.unique(lab[edge & sea0])
    labs = labs[labs > 0]
    open_sea = np.isin(lab, labs) & sea0
    return sea0, open_sea, sea0 & ~open_sea


def coastal_ring(open_sea, active):
    """One-cell ring of open-sea cells 8-adjacent to land (= active cells that are not open sea, incl.
    inland dep <= 0 cells). Returns (ring, exclude) with exclude = open_sea minus the ring."""
    import numpy as np
    from scipy import ndimage

    open_sea = np.asarray(open_sea, dtype=bool)
    land = np.asarray(active, dtype=bool) & ~open_sea
    near_land = ndimage.binary_dilation(land, structure=np.ones((3, 3), dtype=bool))
    ring = open_sea & near_land
    return ring, open_sea & ~ring


def prepare_coastal_exclusion(cfg, work: Path, catalog: Path) -> dict:
    """Harness v1.4 / D4 pre-build step: derive the open-sea exclusion polygon from a grid + dep + active-mask
    hydromt build (same region/res/zmin/zmax/fill/drop settings as the real build), so that
    setup_mask_active(exclude_mask=..., all_touched=False) deactivates the open sea except the coastal ring,
    which setup_mask_bounds(zmax=0) then turns into msk = 2. Writes <work>/open_sea_exclude.geojson and
    <work>/coastal_prep.json; returns the statistics (exclude_mask = None when the domain has no open sea)."""
    import json

    import numpy as np
    import xarray as xr
    from hydromt_sfincs import SfincsModel

    work = Path(work)
    root = work / "_coastal_prep"
    if root.exists():
        shutil.rmtree(root)
    g = cfg.grid
    mod = SfincsModel(root=str(root), mode="w+", data_libs=[str(catalog)])
    mod.setup_grid_from_region(region={"bbox": cfg.bbox_list}, res=g["res"], crs=cfg.epsg, rotated=False)
    mod.setup_dep(datasets_dep=[{"elevtn": "copdem30"}])
    mod.setup_mask_active(zmin=g["zmin"], zmax=g["zmax"], fill_area=g["fill_area_km2"], drop_area=g["drop_area_km2"])
    msk = mod.mask
    dep = mod.grid["dep"].values
    active = msk.values >= 1
    sea0, open_sea, inland = open_sea_split(active, dep)
    ring, exclude = coastal_ring(open_sea, active)
    cell_km2 = g["res"] ** 2 / 1e6
    stats = {"harness_version": cfg.harness_version, "n_active_before": int(active.sum()), "n_dep_le_0": int(sea0.sum()),
             "n_open_sea": int(open_sea.sum()), "open_sea_km2": round(float(open_sea.sum() * cell_km2), 2),
             "n_inland_dep_le_0": int(inland.sum()), "n_ring": int(ring.sum()), "ring_length_km": round(float(ring.sum() * g["res"] / 1000), 1),
             "n_exclude": int(exclude.sum()), "n_active_after_expected": int(active.sum() - exclude.sum()),
             "connectivity": {"open_sea": 4, "ring_adjacency": 8}, "zsini": ZSINI_DRY, "exclude_mask": None}
    if exclude.any():
        da = xr.DataArray(exclude.astype("uint8"), coords=msk.coords, dims=msk.dims, name="exclude")
        da.raster.set_crs(msk.raster.crs)
        da.raster.set_nodata(0)
        gdf = da.raster.vectorize()
        gdf = gdf[gdf["value"] == 1][["geometry"]]
        out = work / "open_sea_exclude.geojson"
        if out.exists():
            out.unlink()
        gdf.to_file(out, driver="GeoJSON")
        stats["exclude_mask"] = str(out).replace("\\", "/")
        stats["n_exclude_polygons"] = int(len(gdf))
    (work / "coastal_prep.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"  coastal prep (v1.4/D4): open sea {stats['n_open_sea']} cells ({stats['open_sea_km2']} km2), ring {stats['n_ring']} "
          f"cells, inland dep<=0 kept {stats['n_inland_dep_le_0']}, excluded {stats['n_exclude']}", flush=True)
    return stats


def _mask_active_extra(cfg, exclude_mask) -> str:
    if cfg.harness_version != "v1.4" or not exclude_mask:
        return ""
    return f"\n  exclude_mask: {str(exclude_mask).replace(chr(92), '/')}\n  all_touched: false"


def render_build_yml(cfg, exclude_mask=None) -> str:
    """Render the HydroMT build file for a config (pure: nothing written).

    exclude_mask: path of the open-sea exclusion polygon from prepare_coastal_exclusion (v1.4 only; ignored
    under v1.3 so the published records render unchanged)."""
    tmpl = (SKILL_DIR / "templates" / "sfincs_build.yml.tmpl").read_text()
    grid = cfg.grid
    return string.Template(tmpl).substitute({
        "zsini": ZSINI_DRY if cfg.harness_version == "v1.4" else 0,
        "mask_active_extra": _mask_active_extra(cfg, exclude_mask),
        "tref": cfg.tref.strftime("%Y%m%d %H%M%S"),
        "tstart": cfg.tstart.strftime("%Y%m%d %H%M%S"),
        "tstop": cfg.tstop.strftime("%Y%m%d %H%M%S"),
        "manning_land": grid["manning_land"],
        "manning_sea": grid["manning_sea"],
        "west": cfg.bbox["west"], "south": cfg.bbox["south"],
        "east": cfg.bbox["east"], "north": cfg.bbox["north"],
        "res": grid["res"], "epsg": cfg.epsg,
        "subgrid_pixels": grid["subgrid_pixels"],
        "manning_lookup": str(cfg.paths["manning_lookup"]).replace("\\", "/"),
        "zmin": grid["zmin"], "zmax": grid["zmax"],
        "fill_area": grid["fill_area_km2"],
        "drop_area": grid["drop_area_km2"],
        "pavbnd_line": _pavbnd_line(cfg),
        "infiltration_block": _infiltration_block(cfg),
        "wind_block": _wind_block(cfg),
        "pressure_block": _pressure_block(cfg),
        "rain_dataset": cfg.rain_source,
        "precip_extra": _precip_extra(cfg),
    })


def waterlevel_bnd_points(da_msk, distance: float = BND_SPACING_M):
    """Points every `distance` m along the water-level boundary (msk = 2 cells), in the mask CRS.

    Same geometry as hydromt_sfincs.SfincsModel.setup_waterlevel_bnd_from_mask (1.2.2, sfincs.py
    2094-2111), whose set_forcing_1d call fails under pandas 3 — hence this post-build route.
    """
    import geopandas as gpd
    import numpy as np
    from hydromt_sfincs import utils

    crs = da_msk.raster.crs
    if int((da_msk == 2).sum()) == 0:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    gdf_msk = utils.get_bounds_vector(da_msk)
    gdf_msk2 = gdf_msk[gdf_msk["value"] == 2]
    if crs.is_geographic:
        distance = distance / 111111.0
    pts = []
    for geom in gdf_msk2.geometry:
        for d in np.arange(0, geom.length, distance):
            p = geom.interpolate(d)
            pts.append((p.x, p.y))
    if not pts:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    return gpd.GeoDataFrame(geometry=gpd.points_from_xy(*zip(*pts)), crs=crs)


def _as_datetime(t):
    """'YYYYmmdd HHMMSS' (sfincs.inp), ISO-like strings, or datetime objects (hydromt read_config)."""
    import datetime as _dt
    if isinstance(t, _dt.datetime):
        return t
    s = str(t).strip()
    for fmt in ("%Y%m%d %H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time stamp {t!r}")


def write_waterlevel_bnd(model_dir: Path, gdf, tref, tstop) -> int:
    """Write sfincs.bnd (x y) + sfincs.bzs (0 m at tref and at tstop) and add the inp keys.

    Returns the number of boundary points. Idempotent on the inp patch.
    """
    import pandas as pd
    from hydromt_sfincs import utils

    model_dir = Path(model_dir)
    n = len(gdf)
    utils.write_xy(model_dir / "sfincs.bnd", gdf, fmt="%.2f")
    t0, t1 = _as_datetime(tref), _as_datetime(tstop)
    df = pd.DataFrame(0.0, index=pd.DatetimeIndex([t0, t1]), columns=list(range(n)))
    utils.write_timeseries(model_dir / "sfincs.bzs", df, t0)
    inp = model_dir / "sfincs.inp"
    txt = inp.read_text()
    if "bndfile" not in txt:
        txt = txt.rstrip() + "\nbndfile = sfincs.bnd\nbzsfile = sfincs.bzs\n"
        inp.write_text(txt)
    return n


def inject_waterlevel_bnd(cfg, model_dir: Path) -> int:
    """Harness v1.4 / D2 post-build step: bnd points along the msk=2 cells + bzs = 0 m.

    No-op (returns 0) for v1.3 or when coastal_bc is disabled. With bzs = 0 m (tide neglected,
    Sect. 3.3.3) and pavbnd = PAVBND_REF_PA in sfincs.inp, SFINCS sets the boundary water level to
    (pavbnd - p_atm(cell, t))/(rhow g) — the inverse barometer from the ERA5 MSLP forcing.
    """
    if cfg.harness_version != "v1.4":
        return 0
    from hydromt_sfincs import SfincsModel

    mod = SfincsModel(root=str(model_dir), mode="r")
    mod.read_config()
    mod.read_grid()
    gdf = waterlevel_bnd_points(mod.mask, BND_SPACING_M)
    if len(gdf) == 0:
        print("  no msk=2 cells — no water-level boundary written.")
        return 0
    n = write_waterlevel_bnd(Path(model_dir), gdf, tref=str(mod.config["tref"]), tstop=str(mod.config["tstop"]))
    print(f"  injected water-level boundary: {n} bnd points every {BND_SPACING_M:.0f} m along the "
          f"msk=2 cells, bzs = 0 m, pavbnd = {PAVBND_REF_PA:.0f} Pa", flush=True)
    return n


def inject_q_forcing(cfg, model_dir: Path) -> None:
    """Write sfincs.src + sfincs.dis and patch sfincs.inp.

    Bypasses hydromt-sfincs's setup_discharge_forcing (pandas-2.x bug:
    RangeIndex.is_integer was removed). Same workaround as v2 forecast.
    """
    import pandas as pd
    import pyproj

    q = cfg.upstream_q
    if not q["enabled"] or not q["src_points"]:
        return
    csv_path = cfg.paths["data_dir"] / "q_outlet.csv"
    if not csv_path.exists():
        print(f"  WARN: {csv_path} missing — run prep_q_at_outlets.py before "
              f"build_model.py; skipping Q injection.")
        return

    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    utm = []
    for sp in q["src_points"]:
        # Use src_lon/src_lat if present (injection location differs from sampling location)
        inj_lon = float(sp.get("src_lon", sp["lon"]))
        inj_lat = float(sp.get("src_lat", sp["lat"]))
        utm.append((sp["name"], *to_utm.transform(inj_lon, inj_lat)))

    src_path = model_dir / "sfincs.src"
    with open(src_path, "w") as f:
        for name, x, y in utm:
            f.write(f"{x:.2f}  {y:.2f}\n")

    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    tref = cfg.tref
    dis_path = model_dir / "sfincs.dis"
    with open(dis_path, "w") as f:
        for ts, row in df.iterrows():
            t_sec = (ts.to_pydatetime() - tref).total_seconds()
            vals = "  ".join(f"{float(v):.2f}" for v in row.values)
            f.write(f"{t_sec:.0f}  {vals}\n")

    inp = model_dir / "sfincs.inp"
    txt = inp.read_text()
    if "srcfile" not in txt:
        txt = txt.rstrip() + "\nsrcfile = sfincs.src\ndisfile = sfincs.dis\n"
        inp.write_text(txt)
    print(f"  injected Q forcing: {len(utm)} src points, {len(df)} timesteps "
          f"({utm[0][0]} ...)", flush=True)


def main():
    cfg = load_config()
    work = cfg.paths["work_dir"]
    work.mkdir(parents=True, exist_ok=True)

    exclude_mask = None
    if cfg.harness_version == "v1.4":
        # D4: open sea inactive except the coastal ring (msk = 2); every cell starts dry (zsini)
        prep = prepare_coastal_exclusion(cfg, work, work / "data_catalog.yml")
        exclude_mask = prep["exclude_mask"]
    rendered = render_build_yml(cfg, exclude_mask=exclude_mask)
    yml_path = work / "sfincs_build.yml"
    yml_path.write_text(rendered, encoding="utf-8")
    print(f"wrote: {yml_path}")

    model_dir = cfg.paths["model_dir"]
    if model_dir.exists():
        for child in model_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"cleared: {model_dir}")
    model_dir.mkdir(parents=True, exist_ok=True)

    hydromt = cfg.env.get("hydromt")
    if not hydromt:
        sys.exit("env.hydromt path not set in config")

    cmd = [
        str(hydromt), "build", "sfincs", str(model_dir),
        "-i", str(yml_path),
        "-d", str(work / "data_catalog.yml"),
        "--fo", "-vv",
    ]
    print(f"running: {' '.join(cmd)}", flush=True)
    res = subprocess.run(cmd, cwd=str(work))
    if res.returncode != 0:
        sys.exit(f"hydromt build failed with exit code {res.returncode}")
    print(f"HydroMT build succeeded -> {model_dir}")

    # Post-HydroMT (harness v1.4): water-level boundary points + bzs = 0 m for the IB correction
    inject_waterlevel_bnd(cfg, model_dir)
    # Post-HydroMT: inject discharge forcing if configured
    inject_q_forcing(cfg, model_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
