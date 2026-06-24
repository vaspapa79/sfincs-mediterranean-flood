"""B3 — reference-data (truth) uncertainty for the three canonical runs.

No SFINCS re-run; everything from stored sfincs_map.nc + EMS polygons/metadata.

(a) Polygon positional uncertainty: re-score strict CSI/HR/FAR against the EMS
    observed extent buffered (eroded/dilated) by ~the EMS SAR positional spec
    (~10-20 m Sentinel-1; manuscript Sec 3.5). Reports the CSI range. Distinct
    from the Sec 8 AOI-mask +/-1 km sensitivity (which moves the evaluation
    domain, not the truth polygon).
(b) Acquisition vs modelled peak: tabulate each EMS product (type + SAR/optical
    acquisition datetime) and the modelled time-of-peak-hmax; report the offset.
(c) all_touched=True half-cell extent inflation (V4) for Methods disclosure.

Output: docs/truth_uncertainty.md  (+ docs/truth_uncertainty_buffer.csv)
"""
from __future__ import annotations
import csv, datetime as dt, glob, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ELKAK = REPO.parent
DOCS = REPO / "docs"
SKILL = ELKAK / ".claude" / "skills" / "sfincs-flood-reproduction"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(REPO / "validation"))
os.environ.setdefault("GDAL_DATA", os.environ.get("SFINCS_GDAL_DATA",
    r"C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/Library/share/gdal"))

from _anim_common import open_sfincs, stats_per_frame  # noqa: E402
from validate_event_v2 import _list_shps, _contingency_full  # noqa: E402

EPSG = 32634
POS_SPEC_M = 20.0    # EMS Sentinel-1 positional uncertainty upper bound (~10-20 m)
BUFFERS_M = [-20, 0, 20]   # erode / metric / dilate by ~the positional spec

CANON = [
    {"slug": "pineios", "label": "Pineios EMSR692 (v1 enhanced)",
     "model": ELKAK / "implementation/pineios_sfincs_enhanced/model",
     "ems": ELKAK / "implementation/pineios_sfincs_enhanced/data/ems_polygons",
     "event": "2023-09-06", "kind": "pineios",
     "obs": ["*DEL_MONIT*observedEventA*.shp", "*DEL_MONIT*observed_event*.shp"],
     "aoi": ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"]},
    {"slug": "strymonas", "label": "Strymonas EMSR122 (v3)",
     "model": ELKAK / "implementation/emsr122_sfincs_v3/model_author_ref",
     "ems": ELKAK / "implementation/emsr122_sfincs_v3/data/ems_polygons",
     "event": "2015-03-31", "kind": "strymonas",
     "obs": ["*DELINEATION*MONIT*crisis_information_poly.shp"],
     "aoi": ["*area_of_interest.shp", "*area_of_interest_a.shp"]},
    {"slug": "mandra", "label": "Mandra EMSR257 (v1 enhanced)",
     "model": ELKAK / "implementation/mandra_sfincs_enhanced/model",
     "ems": ELKAK / "implementation/mandra_sfincs_enhanced/data/ems_polygons",
     "event": "2017-11-15", "kind": "mandra",
     "obs": ["*GRADING*observed_event_a.shp", "*GRA_*observed_event_a.shp"],
     "aoi": ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"]},
]


# ---------- geometry helpers ----------
def load_geoms(shp_paths, target_epsg=EPSG):
    import pyogrio, pyproj
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform
    tgt = pyproj.CRS.from_epsg(target_epsg)
    out = []
    for shp in shp_paths:
        if not shp.exists():
            continue
        info = pyogrio.read_info(shp)
        src = pyproj.CRS.from_user_input(info["crs"])
        _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
        gs = [from_wkb(g) for g in gw]
        if src != tgt:
            tr = pyproj.Transformer.from_crs(src, tgt, always_xy=True).transform
            gs = [shp_transform(tr, g) for g in gs]
        out.extend([g for g in gs if not g.is_empty])
    return out


def _transform(s):
    from rasterio.transform import from_bounds
    ny, nx = s["x"].shape
    xs = s["x"][0, :]; ys = s["y"][:, 0]
    west = float(xs.min()) - s["dx"] / 2; east = float(xs.max()) + s["dx"] / 2
    south = float(ys.min()) - s["dy"] / 2; north = float(ys.max()) + s["dy"] / 2
    return from_bounds(west, south, east, north, nx, ny), ny, nx


def rasterize(geoms, s, all_touched=True, buffer_m=0.0):
    import numpy as np, rasterio.features
    transform, ny, nx = _transform(s)
    gg = []
    for g in geoms:
        gb = g.buffer(buffer_m) if buffer_m else g
        if gb.is_empty:
            continue
        gg.append(gb)
    if not gg:
        return np.zeros((ny, nx), dtype=bool)
    out = rasterio.features.rasterize(((g, 1) for g in gg), out_shape=(ny, nx),
                                      transform=transform, all_touched=all_touched,
                                      dtype="uint8")
    return out[::-1, :].astype(bool)


def rasterize_fine(geoms, s, refine, all_touched=True):
    """Rasterize geometries onto a `refine`x finer grid over the model extent.
    Returns the fine bool array (refine*ny, refine*nx), y-flipped to match the
    model orientation (north-up rows ascending like s)."""
    import numpy as np, rasterio.features
    from rasterio.transform import from_bounds
    ny, nx = s["x"].shape
    xs = s["x"][0, :]; ys = s["y"][:, 0]
    west = float(xs.min()) - s["dx"] / 2; east = float(xs.max()) + s["dx"] / 2
    south = float(ys.min()) - s["dy"] / 2; north = float(ys.max()) + s["dy"] / 2
    fny, fnx = ny * refine, nx * refine
    transform = from_bounds(west, south, east, north, fnx, fny)
    if not geoms:
        return np.zeros((fny, fnx), dtype=bool)
    out = rasterio.features.rasterize(((g, 1) for g in geoms), out_shape=(fny, fnx),
                                      transform=transform, all_touched=all_touched,
                                      dtype="uint8")
    return out[::-1, :].astype(bool)


def block_any(fine, refine):
    """Down-sample a fine bool grid to the model grid: a model cell is wet if ANY
    of its refine x refine sub-cells is wet (the all_touched-equivalent rule)."""
    fny, fnx = fine.shape
    return fine.reshape(fny // refine, refine, fnx // refine, refine).any(axis=(1, 3))


def morph(fine, k):
    """Dilate (k>0) or erode (k<0) a bool grid by |k| cells (square SE)."""
    if k == 0:
        return fine
    from scipy import ndimage
    st = ndimage.generate_binary_structure(2, 2)
    fn = ndimage.binary_dilation if k > 0 else ndimage.binary_erosion
    return fn(fine, structure=st, iterations=abs(k))


def model_hmax_and_mask(s, aoi_wet):
    import numpy as np
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    msk = s["msk"] > 0
    return (hmax > 0.10), (msk & aoi_wet if aoi_wet is not None else msk)


# ---------- (b) acquisition metadata ----------
def _src_rows(dbf):
    import pyogrio
    meta, _, _, attrs = pyogrio.raw.read(str(dbf))
    cols = list(meta["fields"])
    n = len(attrs[0]) if attrs else 0
    return [{c: attrs[cols.index(c)][r] for c in cols} for r in range(n)]


def _parse_dt(date_s, time_s):
    """src_date 'DD/MM/YYYY' (+ time 'T04:39:47Z' or 'HH:MM:SS') -> datetime."""
    d = str(date_s).strip()
    try:
        if "/" in d:
            day, mon, yr = (int(x) for x in d.split("/"))
            base = dt.datetime(yr, mon, day)
        else:
            base = dt.datetime.fromisoformat(d[:10])
    except Exception:
        return None
    t = str(time_s).strip().lstrip("T").rstrip("Z")
    try:
        if t and t not in ("Not Applicable", "None"):
            hh, mm, ss = (t.split(":") + ["0", "0"])[:3]
            base = base.replace(hour=int(hh), minute=int(mm), second=int(float(ss)))
    except Exception:
        pass
    return base


def product_table(ev):
    """Return list of {product, type, aoi, sensor, datetime} for OBSERVED products."""
    rows = []
    obs_shps = _list_shps(ev["ems"], ev["obs"])
    for shp in obs_shps:
        pdir = shp.parent
        name = pdir.name if pdir.name not in ("VECTOR", "Maps") else pdir.parent.name
        ptype = ("DELINEATION-MONIT" if "MONIT" in name and "DEL" in name.upper()
                 else "GRADING" if "GRADING" in name.upper() or "GRA" in name.upper()
                 else "DELINEATION" if "DEL" in name.upper() else "?")
        aoi = next((p for p in name.split("_") if "AOI" in p or any(c.isdigit() for c in p[:2])), name.split("_")[1] if "_" in name else "")
        sensor, when = "?", None
        if ev["kind"] in ("pineios", "mandra"):
            sdbf = glob.glob(str(pdir / "*source*.dbf")) + glob.glob(str(pdir / "**/*source*.dbf"), recursive=True)
            for r in (_src_rows(sdbf[0]) if sdbf else []):
                if str(r.get("eventphase")).lower().startswith("post") and \
                   str(r.get("source_nam")) not in ("Open Street Map", "CLC", "EuroBoundaryMap", "Not Applicable", "Null"):
                    w = _parse_dt(r.get("src_date"), r.get("source_tm"))
                    if w and (when is None or w < when):
                        sensor, when = str(r.get("source_nam")), w
        else:  # strymonas: acquisition date in the obs polygon's own src_date
            rr = _src_rows(shp.with_suffix(".dbf"))
            ds = [r.get("src_date") for r in rr if r.get("src_date")]
            if ds:
                sensor = "Sentinel-1 (DELINEATION)"
                when = _parse_dt(str(ds[0])[:10].replace("-", "/")[:0] or ds[0], None) \
                    if not isinstance(ds[0], str) else _parse_dt(ds[0], None)
                # ds[0] is numpy datetime64 date
                import numpy as np
                if isinstance(ds[0], np.datetime64):
                    when = dt.datetime.fromisoformat(str(ds[0])[:10])
        rows.append({"product": name, "type": ptype, "aoi": aoi,
                     "sensor": sensor, "datetime": when})
    return rows


def modelled_peak(s):
    flooded, maxdepth = stats_per_frame(s)
    import numpy as np
    t = s["times"].astype("datetime64[s]")
    i_area = int(np.argmax(flooded)); i_dep = int(np.argmax(maxdepth))
    to_dt = lambda x: dt.datetime.utcfromtimestamp(x.astype("int64"))
    return {"t_peak_area": to_dt(t[i_area]), "peak_area_km2": float(flooded[i_area]),
            "t_peak_depth": to_dt(t[i_dep]), "peak_depth_m": float(maxdepth[i_dep]),
            "t_start": to_dt(t[0]), "t_end": to_dt(t[-1])}


def main():
    import numpy as np
    DOCS.mkdir(parents=True, exist_ok=True)
    buf_csv_rows = []
    md = ["# Reference-data (truth) uncertainty — B3", "",
          f"EMS SAR positional spec used for the polygon buffer: **±{POS_SPEC_M:.0f} m** "
          "(upper bound of the ~10–20 m Sentinel-1 positional uncertainty informing the EMS "
          "interpretation; manuscript Sec 3.5). All from stored `sfincs_map.nc` + EMS polygons "
          "(no SFINCS re-run). Strymonas scored vs the author-reference output (0.183/0.328).", ""]

    sec_a, sec_b, sec_c = [], [], []
    for ev in CANON:
        print(f"[{ev['slug']}] opening model + loading polygons ...", flush=True)
        s = open_sfincs(ev["model"])
        aoi_geoms = load_geoms(_list_shps(ev["ems"], ev["aoi"]))
        aoi_wet = rasterize(aoi_geoms, s, all_touched=True) if aoi_geoms else None
        obs_geoms = load_geoms(_list_shps(ev["ems"], ev["obs"]))

        # ---- (a) buffer sweep in the RASTER domain (fast; no geometry union) ----
        # Rasterise obs onto a ~POS_SPEC_M fine grid, erode/dilate by 1 fine cell
        # (≈ the positional spec), down-sample to the model grid (any-wet rule).
        refine = max(1, round(s["dx"] / POS_SPEC_M))
        fine_cell = s["dx"] / refine
        print(f"[{ev['slug']}] fine grid refine={refine} (~{fine_cell:.0f} m); "
              f"rasterising {len(obs_geoms)} obs polys ...", flush=True)
        obs_fine = rasterize_fine(obs_geoms, s, refine, all_touched=True)
        model_wet, emask = model_hmax_and_mask(s, aoi_wet)
        rowvals = {}
        for d in BUFFERS_M:
            k = int(round(d / fine_cell))
            ems_b = block_any(morph(obs_fine, k), refine)
            c = _contingency_full(model_wet, ems_b, emask)
            rowvals[d] = c
            buf_csv_rows.append({"event": ev["slug"], "buffer_m": d, "csi": c["csi"],
                                 "hr": c["hr"], "far": c["far"], "obs_wet_km2":
                                 float((ems_b & emask).sum() * s["cell_area_km2"])})
        csis = [rowvals[d]["csi"] for d in BUFFERS_M]
        sec_a.append((ev, rowvals, min(csis), max(csis)))

        # ---- (b) acquisition vs modelled peak ----
        print(f"[{ev['slug']}] (b) peak + metadata; (c) all_touched ...", flush=True)
        pt = modelled_peak(s)
        prods = product_table(ev)
        sec_b.append((ev, prods, pt))

        # ---- (c) all_touched inflation (direct model-grid rasterise; fast in C) ----
        obs_T = rasterize(obs_geoms, s, all_touched=True)
        obs_F = rasterize(obs_geoms, s, all_touched=False)
        msk = s["msk"] > 0
        ca = s["cell_area_km2"]
        c_obs = {"T": float((obs_T & msk).sum() * ca), "F": float((obs_F & msk).sum() * ca)}
        if aoi_wet is not None:
            aoi_F = rasterize(aoi_geoms, s, all_touched=False)
            c_aoi = {"T": float((aoi_wet & msk).sum() * ca), "F": float((aoi_F & msk).sum() * ca)}
        else:
            c_aoi = None
        sec_c.append((ev, c_obs, c_aoi, s["dx"]))

    # ===== (a) write =====
    md += ["## (a) Polygon positional uncertainty — CSI range", "",
           f"The observed EMS extent is eroded / dilated by ~the EMS positional spec (±{POS_SPEC_M:.0f} m). "
           "Because that distance is sub-grid (cells 50–150 m), the buffer is applied in the raster "
           "domain: obs is rasterised onto a ~20 m fine grid, eroded/dilated by one fine cell, then "
           "down-sampled to the model grid (any-sub-cell-wet rule), and scored strict h>0.10 m on the "
           "canonical mask. The CSI range is the band attributable to truth-polygon position; it is "
           "**much smaller** than the Sec 8 AOI-mask ±1 km band (which moves the evaluation domain, not "
           "the truth boundary).", "",
           f"| Event | CSI erode −{POS_SPEC_M:.0f} m | CSI metric (0) | CSI dilate +{POS_SPEC_M:.0f} m | CSI range (±half) |",
           "|---|--:|--:|--:|--:|"]
    for ev, rv, lo, hi in sec_a:
        md.append(f"| {ev['label']} | {rv[-20]['csi']:.3f} | {rv[0]['csi']:.3f} | "
                  f"{rv[20]['csi']:.3f} | {lo:.3f}–{hi:.3f} (±{(hi-lo)/2:.3f}) |")
    md.append("")

    # ===== (b) write =====
    md += ["## (b) EMS acquisition vs modelled peak", "",
           "EMS product type + SAR/optical acquisition datetime (UTC) per observed product, vs the "
           "modelled time of peak flooded area / peak depth from `sfincs_map.nc`.", ""]
    for ev, prods, pt in sec_b:
        md += [f"### {ev['label']}",
               f"- Modelled sim window: {pt['t_start']:%Y-%m-%d %H:%M} → {pt['t_end']:%Y-%m-%d %H:%M} UTC",
               f"- **Modelled peak flooded area**: {pt['t_peak_area']:%Y-%m-%d %H:%M} UTC "
               f"({pt['peak_area_km2']:.1f} km²); peak max-depth: {pt['t_peak_depth']:%Y-%m-%d %H:%M} "
               f"UTC ({pt['peak_depth_m']:.2f} m)", "",
               "| Observed product | Type | AOI | Sensor | Acquisition (UTC) | Offset peak−acq |",
               "|---|---|---|---|---|--:|"]
        # distinct acquisitions, sorted
        seen = set()
        for p in sorted(prods, key=lambda r: (r["datetime"] or dt.datetime.min)):
            when = p["datetime"]
            key = (p["type"], p["aoi"], when)
            if key in seen:
                continue
            seen.add(key)
            if when:
                off = pt["t_peak_area"] - when
                offh = off.total_seconds() / 3600.0
                offs = f"{offh:+.1f} h ({offh/24:+.1f} d)"
                wstr = f"{when:%Y-%m-%d %H:%M}"
            else:
                offs, wstr = "n/a", "n/a"
            md.append(f"| {p['product']} | {p['type']} | {p['aoi']} | {p['sensor']} | {wstr} | {offs} |")
        # summary
        acqs = sorted({p["datetime"] for p in prods if p["datetime"]})
        if acqs:
            span = (acqs[-1] - acqs[0]).total_seconds() / 86400.0
            off0 = (pt["t_peak_area"] - acqs[0]).total_seconds() / 3600.0
            md += ["", f"Acquisitions span {acqs[0]:%Y-%m-%d %H:%M} → {acqs[-1]:%Y-%m-%d %H:%M} "
                   f"({span:.1f} d, {len(acqs)} overpass time(s)). Modelled peak is "
                   f"{off0:+.1f} h ({off0/24:+.1f} d) from the **first** overpass. "
                   "Note: the observed extent is a union over these acquisitions, so a single "
                   "model-snapshot offset is only indicative.", ""]
    # ===== (c) write =====
    md += ["## (c) all_touched=True extent inflation (V4 disclosure)", "",
           "Polygons are burned with `all_touched=True` (any cell the polygon touches is set wet), "
           "which enlarges both the observed extent and the AOI mask by up to ~half a cell along "
           "each boundary vs centroid rasterisation (`all_touched=False`). For Methods disclosure:", "",
           "| Event | cell (m) | obs wet aT=T (km²) | aT=F (km²) | obs inflation | AOI aT=T (km²) | aT=F (km²) | AOI inflation |",
           "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for ev, c_obs, c_aoi, dx in sec_c:
        oi = (c_obs["T"] - c_obs["F"]) / c_obs["F"] * 100 if c_obs["F"] else float("nan")
        if c_aoi:
            ai = (c_aoi["T"] - c_aoi["F"]) / c_aoi["F"] * 100 if c_aoi["F"] else float("nan")
            md.append(f"| {ev['label']} | {dx:.0f} | {c_obs['T']:.3f} | {c_obs['F']:.3f} | "
                      f"+{oi:.1f}% | {c_aoi['T']:.1f} | {c_aoi['F']:.1f} | +{ai:.1f}% |")
        else:
            md.append(f"| {ev['label']} | {dx:.0f} | {c_obs['T']:.3f} | {c_obs['F']:.3f} | "
                      f"+{oi:.1f}% | n/a | n/a | n/a |")
    md += ["", "The inflation scales with the perimeter-to-area ratio: largest (relative) for the "
           "small, fragmented GRADING/observed extents and smaller for the broad AOI masks. This is a "
           "known, disclosed bias in the validation rasterisation (finding V4); it affects all runs "
           "identically and slightly favours hit rate over FAR.", ""]

    (DOCS / "truth_uncertainty.md").write_text("\n".join(md), encoding="utf-8")
    with open(DOCS / "truth_uncertainty_buffer.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["event", "buffer_m", "csi", "hr", "far", "obs_wet_km2"])
        w.writeheader()
        for r in buf_csv_rows:
            w.writerow(r)
    print("wrote docs/truth_uncertainty.md + truth_uncertainty_buffer.csv")
    # console anchor check
    for ev, rv, lo, hi in sec_a:
        print(f"  {ev['slug']}: CSI@0={rv[0]['csi']:.3f} range {lo:.3f}-{hi:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
