"""CODE-15 D (2026-10-20) — water-volume bookkeeping of the harness v1.4.2 runs, from the model files only.

Pineios (`pineios_enhanced_v142`): the injected peak per source point (sfincs.dis, the columns SFINCS read) and the total injected
volume over the simulated window tstart..tstop against the rain volume that fell on the active domain in the same window
(netampr forcing precip_2d.nc, mm/h left-labelled rates, integrated per forcing cell and weighted by the active model area each
forcing cell covers) — the "rainfall-driven" sentence needs these numbers. Emilia (`emilia_enhanced_8aoi_v142`): the injected
volume per river against observed-flood volume proxies: the EMS-observed flooded area inside the evaluation mask (the validator's
rasterisation) times nominal depths (0.5 m, 1.0 m), and the modelled volume inside that observed extent (sum of hmax over the
observed cells). Rain volumes are given for both events for context.

Usage: python -I d_volumes_v142.py --repo <worktree> [--runs pineios_enhanced_v142,emilia_enhanced_8aoi_v142] [--out-dir .../code15]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

THR = 0.10
NOMINAL_DEPTHS_M = (0.5, 1.0)
DEFAULT_RUNS = ["pineios_enhanced_v142", "emilia_enhanced_8aoi_v142"]


def rain_volume(precip_nc: Path, model_x, model_y, active: np.ndarray, dx: float, t0, t1) -> dict:
    """Rain volume [m3] over the active model area between t0 and t1 from the netampr file (rates in mm/h at the forcing grid)."""
    import pandas as pd
    import xarray as xr
    ds = xr.open_dataset(precip_nc)
    var = [v for v in ds.data_vars if ds[v].ndim == 3][0]
    da = ds[var]
    tidx = ds.indexes["time"]
    if hasattr(tidx, "to_datetimeindex"):                                               # cftime (julian calendar in the hydromt file) -> datetime64
        tidx = tidx.to_datetimeindex(unsafe=True)
    t = pd.DatetimeIndex(tidx)
    sel = (t >= pd.Timestamp(t0)) & (t < pd.Timestamp(t1))
    da = da.isel(time=np.where(sel)[0])
    tt = t[sel]
    steps_h = np.diff(tt.values).astype("timedelta64[s]").astype(float) / 3600.0
    steps_h = np.append(steps_h, steps_h[-1] if steps_h.size else 0.0)               # left-labelled rates: each stamp holds until the next
    rates = np.nan_to_num(np.asarray(da.values, dtype=float))                          # (time, y, x) mm/h
    depth_mm = np.tensordot(steps_h, rates, axes=(0, 0))                               # mm per forcing cell over the window
    fx = np.asarray(da.x.values, dtype=float); fy = np.asarray(da.y.values, dtype=float)
    # active model area per forcing cell: nearest forcing cell of every active model cell centre
    mx = np.asarray(model_x)[active]; my = np.asarray(model_y)[active]
    ix = np.clip(np.rint((mx - fx[0]) / (fx[1] - fx[0])).astype(int), 0, fx.size - 1)
    iy = np.clip(np.rint((my - fy[0]) / (fy[1] - fy[0])).astype(int), 0, fy.size - 1)
    counts = np.zeros(depth_mm.shape, dtype=float)
    np.add.at(counts, (iy, ix), 1.0)
    area = counts * dx * dx
    vol = float(np.sum(depth_mm / 1000.0 * area))
    a_act = float(area.sum())
    return {"file": precip_nc.name, "variable": var, "n_steps": int(rates.shape[0]), "step_h": float(np.median(steps_h)) if steps_h.size else None,
            "window": [str(t0), str(t1)], "active_area_km2": a_act / 1e6, "rain_volume_m3": vol, "mean_depth_over_active_mm": (vol / a_act * 1000.0 if a_act else None),
            "max_cell_depth_mm": float(depth_mm.max())}


def injected(model: Path, tref, t0, t1) -> dict:
    """Peak and volume per injected source over [t0, t1] from sfincs.dis (SFINCS interpolates linearly between the listed times)."""
    import pandas as pd
    dis = np.loadtxt(model / "sfincs.dis"); dis = dis[None, :] if dis.ndim == 1 else dis
    times = pd.Timestamp(tref) + pd.to_timedelta(dis[:, 0], unit="s")
    sel = (times >= pd.Timestamp(t0)) & (times <= pd.Timestamp(t1))
    tsec = dis[sel, 0]; q = dis[sel, 1:]
    snap = json.loads((model / "sfincs_src_snap.json").read_text(encoding="utf-8")) if (model / "sfincs_src_snap.json").exists() else None
    names = [p["name"] for p in snap["points"] if p["injected"]] if snap else [f"src{i + 1}" for i in range(q.shape[1])]
    cols = []
    for j in range(q.shape[1]):
        vol = float(np.trapezoid(q[:, j], tsec))
        cols.append({"name": names[j] if j < len(names) else f"src{j + 1}", "peak_m3s": float(q[:, j].max()), "mean_m3s": float(q[:, j].mean()), "volume_m3": vol,
                     "snap": next((p for p in (snap or {}).get("points", []) if p["name"] == (names[j] if j < len(names) else None)), None)})
    return {"n_sources": q.shape[1], "window": [str(t0), str(t1)], "sources": cols, "total_volume_m3": float(sum(c["volume_m3"] for c in cols)),
            "combined_peak_m3s": float(q.sum(axis=1).max())}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = a.out_dir or (repo / "reproduction" / "v14_rerun" / "code15")
    sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(repo / "validation")); sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    from _common import load_config
    from validate_event_v2 import _rasterise_polys_to_grid, _list_shps, _select_obs_shps, open_sfincs_light
    from eval_exclusion import read_mask_for_grid
    from truth_cache import cache_key, cached_bool
    R = repo / "reproduction" / "v14_rerun"
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "threshold_m": THR, "runs": {}}
    md = []
    for run in [x for x in a.runs.split(",") if x]:
        cfg = load_config(["--config", str(R / "configs" / f"{run}.yaml")])
        model = cfg.paths["model_dir"]
        s = open_sfincs_light(model)
        active = s["msk"] > 0
        dx = float(s["dx"])
        rec = json.loads((R / "results" / f"{run}_record.json").read_text(encoding="utf-8")) if (R / "results" / f"{run}_record.json").exists() else {}
        inj = injected(model, cfg.tref, cfg.tstart, cfg.tstop)
        sampled = (rec.get("q_outlet_cells") or {}).get("points") or (json.loads((cfg.paths["data_dir"] / "q_outlet_cells.json").read_text(encoding="utf-8"))["points"] if (cfg.paths["data_dir"] / "q_outlet_cells.json").exists() else [])
        rain = rain_volume(model / "precip_2d.nc", s["x"], s["y"], active, dx, cfg.tstart, cfg.tstop)
        zsmax = s["ds"]["zsmax"].max(dim="timemax").values
        hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
        wet = (hmax > THR) & active
        model_flood = {"wet_area_km2": float(wet.sum() * dx * dx / 1e6), "volume_m3": float(np.sum(hmax[wet]) * dx * dx)}
        ev = {"run": run, "event": cfg.event_slug, "window_simulated": [str(cfg.tstart), str(cfg.tstop)], "injected": inj,
              "sampled_points": [{"name": p["name"], "cell_lonlat": p["cell_lonlat"], "column_peak_m3s": p["column_peak_m3s"], "inject": p.get("inject", True)} for p in sampled],
              "rain_on_active_domain": rain, "injected_over_rain": (inj["total_volume_m3"] / rain["rain_volume_m3"] if rain["rain_volume_m3"] else None),
              "model_flood_hmax_gt_thr": model_flood}
        if cfg.event_slug.startswith("emilia"):
            excl = read_mask_for_grid(R / "masks" / "emilia_exclusion.tif", s)
            ems_dir = cfg.paths["data_dir"] / "ems_polygons"
            obs = _select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
            aois = _list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
            cache_dir = R / "phase4" / "truth_buffer" / "_cache"
            ems_wet = cached_bool(cache_dir, cache_key(cfg.event_slug, s, obs, "plain_validator"), lambda: _rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))
            aoi_uni = cached_bool(cache_dir, cache_key(cfg.event_slug, s, aois, "aoi_union"), lambda: _rasterise_polys_to_grid(aois, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))
            mask = active & aoi_uni & ~excl
            obs_cells = ems_wet & mask
            a_obs = float(obs_cells.sum() * dx * dx)
            ev["observed_flood_proxy"] = {"evaluation_mask": "AOI ∩ active minus exclusion (v1.4)", "observed_area_km2": a_obs / 1e6,
                                          "modelled_volume_inside_observed_extent_m3": float(np.sum(hmax[obs_cells]) * dx * dx),
                                          "modelled_mean_hmax_inside_observed_extent_m": (float(hmax[obs_cells].mean()) if obs_cells.any() else None),
                                          **{f"nominal_{d:.1f}m_m3": a_obs * d for d in NOMINAL_DEPTHS_M}}
            ev["injected_over_proxies"] = {k: (inj["total_volume_m3"] / v if v else None) for k, v in ev["observed_flood_proxy"].items() if k.endswith("_m3")}
        out["runs"][run] = ev
        # ---- markdown
        md += [f"### {run} — simulated window {cfg.tstart:%Y-%m-%d %H:%M} → {cfg.tstop:%Y-%m-%d %H:%M} UTC", "",
               "| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |", "|---|---|---|---|---|"]
        for c in inj["sources"]:
            sn = c["snap"] or {}
            md.append(f"| {c['name']} | {c['peak_m3s']:.2f} | {c['mean_m3s']:.2f} | {c['volume_m3'] / 1e6:.2f} | z_b {sn.get('zb_m')} m, {sn.get('distance_m')} m, {sn.get('uparea_km2')} km² |")
        for p in sampled:
            if not p.get("inject", True):
                md.append(f"| {p['name']} (sampled, not injected) | {p['column_peak_m3s']:.2f} | — | — | cell {tuple(p['cell_lonlat'])} |")
        md += [f"| **total injected** | combined peak {inj['combined_peak_m3s']:.2f} | | **{inj['total_volume_m3'] / 1e6:.2f}** | |", "",
               f"Rain on the active domain ({rain['active_area_km2']:.0f} km²) in the window: **{rain['rain_volume_m3'] / 1e6:.1f} × 10⁶ m³** (mean depth {rain['mean_depth_over_active_mm']:.0f} mm, max cell {rain['max_cell_depth_mm']:.0f} mm; `{rain['file']}`, {rain['n_steps']} steps of {rain['step_h']:.2f} h). "
               f"Injected / rain = **{100 * ev['injected_over_rain']:.1f} %**. Modelled flood (hmax > {THR} m): {model_flood['wet_area_km2']:.0f} km², {model_flood['volume_m3'] / 1e6:.1f} × 10⁶ m³ of water standing at hmax.", ""]
        if "observed_flood_proxy" in ev:
            o = ev["observed_flood_proxy"]; r = ev["injected_over_proxies"]
            md += [f"Observed flood (EMS, inside the evaluation mask): {o['observed_area_km2']:.1f} km². Proxies: modelled volume inside the observed extent {o['modelled_volume_inside_observed_extent_m3'] / 1e6:.1f} × 10⁶ m³ "
                   f"(mean modelled hmax there {o['modelled_mean_hmax_inside_observed_extent_m']:.2f} m); nominal 0.5 m {o['nominal_0.5m_m3'] / 1e6:.1f}, 1.0 m {o['nominal_1.0m_m3'] / 1e6:.1f} × 10⁶ m³. "
                   f"Total injected / proxy: {100 * r['modelled_volume_inside_observed_extent_m3']:.0f} % (modelled), {100 * r['nominal_0.5m_m3']:.0f} % (0.5 m), {100 * r['nominal_1.0m_m3']:.0f} % (1.0 m).", ""]
        print(f"{run}: injected {inj['total_volume_m3'] / 1e6:.2f} Mm3 (peaks {[round(c['peak_m3s'], 1) for c in inj['sources']]}), rain {rain['rain_volume_m3'] / 1e6:.1f} Mm3 -> {100 * ev['injected_over_rain']:.1f} %")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d_volumes_v142.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    (out_dir / "d_volumes_v142.md").write_text(f"# Injected discharge vs rain / observed-flood volumes, harness v1.4.2 (CODE-15 D) — generated {out['utc']} by `reproduction/v14_rerun/scripts/d_volumes_v142.py`\n\n"
                                               "Volumes over the simulated window (tstart..tstop); injected = trapezoid integral of the sfincs.dis columns SFINCS read; rain = netampr rates integrated per forcing cell and weighted by the "
                                               "active model area each forcing cell covers.\n\n" + "\n".join(md), encoding="utf-8")
    print("wrote", out_dir / "d_volumes_v142.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
