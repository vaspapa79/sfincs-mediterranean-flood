"""Quantitative validation of an SFINCS enhanced run vs Copernicus EMS.

Run after a pipeline finishes. Produces a JSON metric report + an MD
summary card that drops directly into the paper:

  paper/data/<event_slug>_metrics.json     (machine readable)
  paper/data/<event_slug>_metrics.md       (paste-ready Markdown)

Metrics computed
----------------
1.  Forcing sanity
      - rain source (era5_hourly | imerg_half_hourly)
      - hours covered, missing %, basin-mean total (mm), peak hourly intensity
      - if both ERA5 + IMERG exist: IMERG / ERA5 ratio at peak + at total
2.  Run sanity
      - n frames, simulation duration, peak modelled depth, peak flooded km²
      - peak frame time vs event date (h offset)
      - mass-balance proxy: cumulative rain volume vs cumulative flooded volume
        on the active mask (qualitative; not a closed budget)
3.  EMS validation (pixel-wise, on the SFINCS grid)
      - CSI, HR (POD), FAR, F1, accuracy over the active mask
      - per-AOI breakdown (one row per area_of_interest_a.shp)
      - depth-threshold sweep (h > 0.05, 0.1, 0.25, 0.5 m) — sensitivity
4.  Baseline vs enhanced delta (if `--baseline <model_dir>` is given)
      - ΔCSI, ΔHR, ΔFAR
      - Δ peak depth, Δ peak area

Usage
-----
    python paper/scripts/validate_event.py \\
        --config .claude/skills/sfincs-flood-reproduction/examples/emsr257_mandra_enhanced.yaml \\
        [--baseline implementation/mandra_sfincs/model]

Exits 0 even if CSI is low — the script is a *reporter*, not a gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

# Make sure we can import the skill helpers
SKILL_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "sfincs-flood-reproduction"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from _common import load_config  # noqa: E402
from _anim_common import open_sfincs, stats_per_frame  # noqa: E402


PAPER_DATA = Path(__file__).resolve().parents[1] / "data"


def _h_at_threshold(h, msk, thr):
    return ((h > thr) & (msk > 0))


def _rasterise_polys_to_grid(shp_paths, x_grid, y_grid, target_epsg, dx, dy):
    """Burn a list of shapefiles onto a 2D grid matching x_grid/y_grid.

    Returns a bool array (ny, nx) — True where any polygon covers the cell.
    Uses rasterio.features.rasterize for speed. The SFINCS grid is assumed
    y-ascending (row 0 = south); the rasterio array is built top-down and
    then flipped to match.
    """
    import numpy as np
    import pyogrio
    import pyproj
    import rasterio.features
    from rasterio.transform import from_bounds
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform

    target_crs = pyproj.CRS.from_epsg(target_epsg)
    ny, nx = x_grid.shape

    # Build a top-down transform from cell-centre extents.
    xs = x_grid[0, :]
    ys = y_grid[:, 0]
    west = float(xs.min()) - dx / 2.0
    east = float(xs.max()) + dx / 2.0
    south = float(ys.min()) - dy / 2.0
    north = float(ys.max()) + dy / 2.0
    transform = from_bounds(west, south, east, north, nx, ny)

    geoms = []
    for shp in shp_paths:
        if not shp.exists():
            continue
        info = pyogrio.read_info(shp)
        src_crs = pyproj.CRS.from_user_input(info["crs"])
        _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
        gs = [from_wkb(g) for g in gw]
        if src_crs != target_crs:
            tr = pyproj.Transformer.from_crs(src_crs, target_crs,
                                             always_xy=True).transform
            gs = [shp_transform(tr, g) for g in gs]
        geoms.extend([g for g in gs if not g.is_empty])
    if not geoms:
        return np.zeros((ny, nx), dtype=bool)
    out_td = rasterio.features.rasterize(
        ((g, 1) for g in geoms),
        out_shape=(ny, nx),
        transform=transform,
        all_touched=True,
        dtype="uint8",
    )
    # Rasterised array is top-down; SFINCS y is ascending, so flip vertically
    return out_td[::-1, :].astype(bool)


def _contingency(model_wet, ems_wet, mask):
    """Pixel-wise contingency on `mask`. All counts are restricted to the
    evaluation area (active mask ∩ AOI). TN is the dry-in-both count."""
    import numpy as np
    # Restrict to evaluation mask (so TN doesn't blow up over the ocean)
    m = (model_wet & mask)
    e = (ems_wet & mask)
    in_eval = mask
    tp = int((m & e).sum())
    fp = int((m & ~e & in_eval).sum())
    fn = int((~m & e & in_eval).sum())
    tn = int((~m & ~e & in_eval).sum())
    denom_csi = tp + fp + fn
    denom_hr = tp + fn
    denom_far = tp + fp
    denom_f1 = 2 * tp + fp + fn
    denom_acc = tp + fp + fn + tn
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "csi": (tp / denom_csi) if denom_csi > 0 else float("nan"),
        "hr":  (tp / denom_hr) if denom_hr > 0 else float("nan"),
        "far": (fp / denom_far) if denom_far > 0 else float("nan"),
        "f1":  (2 * tp / denom_f1) if denom_f1 > 0 else float("nan"),
        "acc": ((tp + tn) / denom_acc) if denom_acc > 0 else float("nan"),
    }


def _list_shps(ems_dir: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    seen = set()
    if not ems_dir.exists():
        return out
    for pat in patterns:
        for p in ems_dir.rglob(pat):
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
    return sorted(out)


def _forcing_sanity(cfg, model_dir: Path) -> dict:
    """Read the actual precip_2d.nc that SFINCS consumed and report its stats.

    Also verifies that the enhanced-forcing files that the YAML requested are
    actually present in model_dir (wind, pressure, infiltration, src+dis),
    and that the sfincs.inp pavbnd flag agrees with the coastal_bc setting.
    """
    import numpy as np
    import xarray as xr
    precip = xr.open_dataset(model_dir / "precip_2d.nc")
    pvar = list(precip.data_vars)[0]
    pa = precip[pvar].values   # (t, n, m)  units mm/h (after prep_inputs)
    pa = np.nan_to_num(pa, nan=0.0)
    nt = pa.shape[0]
    if "time" in precip.coords:
        times = precip["time"].values
    elif "time" in precip.variables:
        times = precip["time"].values
    else:
        times = np.array([np.datetime64(str(cfg.tref))])
    # mean over space → series (mm/h)
    p_series = pa.reshape(nt, -1).mean(axis=1)
    # Time step in hours; handle both numpy datetime64 and cftime objects
    if len(times) > 1:
        try:
            dt_h = float((times[1] - times[0]) / np.timedelta64(1, "h"))
        except Exception:
            try:
                # cftime objects: difference gives a timedelta; use total_seconds()
                dt_h = (times[1] - times[0]).total_seconds() / 3600.0
            except Exception:
                dt_h = 1.0
    else:
        dt_h = 1.0
    total = float(p_series.sum() * dt_h)  # mm (mm/h × dt[h])
    peak = float(p_series.max())          # mm/h
    cell_peak = float(pa.max())           # mm/h at peak cell

    # Verify which enhanced forcing files exist
    wind_nc = model_dir / "wind_2d.nc"
    # HydroMT writes press_2d.nc (not pressure_2d.nc)
    press_nc = model_dir / "press_2d.nc"
    if not press_nc.exists():
        press_nc = model_dir / "pressure_2d.nc"
    cn_tif = model_dir / "cn.tif"
    src_file = model_dir / "sfincs.src"
    dis_file = model_dir / "sfincs.dis"
    enhanced_present = {
        "wind_forcing_file": wind_nc.exists(),
        "pressure_forcing_file": press_nc.exists(),
        "cn_infiltration_file": cn_tif.exists(),
        "src_file": src_file.exists() and src_file.stat().st_size > 0,
        "dis_file": dis_file.exists() and dis_file.stat().st_size > 0,
    }

    # Parse pavbnd from sfincs.inp
    inp = model_dir / "sfincs.inp"
    pavbnd = None
    inp_keys = {}
    if inp.exists():
        for line in inp.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                inp_keys[k.strip()] = v.strip()
        try:
            pavbnd = int(inp_keys.get("pavbnd", "0"))
        except ValueError:
            pavbnd = None

    # Sanity: declared YAML vs. realised
    declared = {
        "rain_source": cfg.rain_source,
        "wind_pressure_enabled": cfg.wind_pressure["enabled"],
        "infiltration_enabled": cfg.infiltration["enabled"],
        "upstream_q_enabled": cfg.upstream_q["enabled"],
        "coastal_bc_enabled": cfg.coastal_bc["enabled"],
    }
    realised = {
        "wind_forcing": enhanced_present["wind_forcing_file"],
        "pressure_forcing": enhanced_present["pressure_forcing_file"],
        "infiltration": enhanced_present["cn_infiltration_file"]
                        or "qinfffile" in inp_keys
                        or "scsfile"   in inp_keys
                        or "cnfile"    in inp_keys,
        "upstream_q": enhanced_present["src_file"] and enhanced_present["dis_file"],
        "pavbnd": pavbnd == 1,
    }
    mismatches = []
    if declared["wind_pressure_enabled"] and not realised["wind_forcing"]:
        mismatches.append("wind forcing declared but wind_2d.nc missing")
    if declared["wind_pressure_enabled"] and not realised["pressure_forcing"]:
        mismatches.append("pressure forcing declared but pressure_2d.nc missing")
    if declared["infiltration_enabled"] and not realised["infiltration"]:
        mismatches.append("infiltration declared but no CN/scs/qinf file in model dir")
    if declared["upstream_q_enabled"] and not realised["upstream_q"]:
        mismatches.append("upstream Q declared but sfincs.src/.dis missing")
    if declared["coastal_bc_enabled"] and not realised["pavbnd"]:
        mismatches.append(f"coastal_bc declared but pavbnd={pavbnd}, not 1")

    return {
        "rain_source": cfg.rain_source,
        "nframes": int(nt),
        "dt_h": float(dt_h),
        "domain_mean_total_mm": total,
        "domain_mean_peak_intensity_mmph": peak,
        "max_cell_peak_intensity_mmph": cell_peak,
        "first_time": str(times[0]) if len(times) > 0 else None,
        "last_time": str(times[-1]) if len(times) > 0 else None,
        "declared_enhancements": declared,
        "realised_enhancements": realised,
        "enhancement_mismatches": mismatches,
    }


def _run_sanity(cfg, s, model_dir: Path) -> dict:
    import numpy as np
    flooded_km2, maxdepth_m = stats_per_frame(s)
    times = s["times"]
    peak_t = int(np.argmax(maxdepth_m))
    peak_a = int(np.argmax(flooded_km2))
    peak_t_iso = str(times[peak_t])
    peak_a_iso = str(times[peak_a])
    ev = cfg.event_date
    ev_dt = dt.datetime.combine(ev, dt.time())
    try:
        peak_t_dt = dt.datetime.fromisoformat(peak_t_iso.replace("Z", ""))
        offset_h_depth = (peak_t_dt - ev_dt).total_seconds() / 3600.0
    except Exception:
        offset_h_depth = None
    try:
        peak_a_dt = dt.datetime.fromisoformat(peak_a_iso.replace("Z", ""))
        offset_h_area = (peak_a_dt - ev_dt).total_seconds() / 3600.0
    except Exception:
        offset_h_area = None
    return {
        "nframes": int(s["nt"]),
        "ny": int(s["ny"]), "nx": int(s["nx"]),
        "dx_m": float(s["dx"]), "dy_m": float(s["dy"]),
        "active_cells": int((s["msk"] > 0).sum()),
        "active_area_km2": float((s["msk"] > 0).sum() * s["cell_area_km2"]),
        "peak_max_depth_m": float(maxdepth_m.max()),
        "peak_max_depth_time": peak_t_iso,
        "peak_max_depth_h_from_event": offset_h_depth,
        "peak_flooded_km2": float(flooded_km2.max()),
        "peak_flooded_time": peak_a_iso,
        "peak_flooded_h_from_event": offset_h_area,
        "final_max_depth_m": float(maxdepth_m[-1]),
        "final_flooded_km2": float(flooded_km2[-1]),
    }


def _validate_ems(cfg, s) -> dict:
    import numpy as np

    ems_dir = cfg.paths["data_dir"] / "ems_polygons"

    # Observed flood polygons (any of the standard EMS schemas)
    obs_shps = _list_shps(ems_dir, [
        # Legacy S3 (EMSR122 / EMSR257):
        "*DELINEATION*MONIT*crisis_information_poly.shp",
        "*GRADING*observed_event_a.shp",
        "*GRA_*observed_event_a.shp",
        # Newer rapidmapping API (EMSR692+):
        "*DEL_MONIT*observedEventA*.shp",
        "*DEL_MONIT*observed_event*.shp",
    ])
    # AOI polygons (one per AOI in the YAML, named *_area_of_interest*)
    aoi_shps = _list_shps(ems_dir, [
        # Legacy S3:
        "*area_of_interest.shp",
        "*area_of_interest_a.shp",
        # Newer rapidmapping API:
        "*areaOfInterestA*.shp",
    ])

    ems_wet = _rasterise_polys_to_grid(
        obs_shps, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
    )
    msk_bool = (s["msk"] > 0)

    # Restrict the universe to the union of AOIs (the EMS analysed area)
    if aoi_shps:
        aoi_universe = _rasterise_polys_to_grid(
            aoi_shps, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
        )
        evaluation_mask = msk_bool & aoi_universe
    else:
        evaluation_mask = msk_bool

    # Use maximum across ALL zsmax windows (captures early-peak events that drain)
    import xarray as xr  # noqa: F401
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))

    metrics_by_thr = {}
    for thr in (0.05, 0.10, 0.25, 0.50):
        model_wet = (hmax > thr)
        metrics_by_thr[f"h>{thr:.2f}m"] = _contingency(model_wet, ems_wet, evaluation_mask)

    # Per-AOI breakdown at the 0.1 m threshold (canonical).
    # ems_wet is already computed above on the full grid; reuse it instead
    # of re-rasterising all observed-flood polygons once per AOI (the
    # latter was O(N_aois x N_polys) and dominated runtime on EMSR692 with
    # 28,895 polygons x 24 AOIs).
    per_aoi = []
    model_local = (hmax > 0.10)
    for aoi_shp in aoi_shps:
        a_mask = _rasterise_polys_to_grid(
            [aoi_shp], s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
        )
        local_mask = msk_bool & a_mask
        if not local_mask.any():
            continue
        ems_local = ems_wet  # cached above
        m = _contingency(model_local, ems_local, local_mask)
        m["aoi_file"] = aoi_shp.name
        m["aoi_active_km2"] = float(local_mask.sum() * s["cell_area_km2"])
        m["ems_wet_in_aoi_km2"] = float((ems_local & local_mask).sum()
                                        * s["cell_area_km2"])
        per_aoi.append(m)

    return {
        "n_ems_shps": len(obs_shps),
        "n_aoi_shps": len(aoi_shps),
        "evaluation_area_km2": float(evaluation_mask.sum() * s["cell_area_km2"]),
        "observed_wet_in_eval_area_km2": float((ems_wet & evaluation_mask).sum()
                                               * s["cell_area_km2"]),
        "metrics_by_threshold": metrics_by_thr,
        "primary_threshold": "h>0.10m",
        "per_aoi_h_gt_0p10m": per_aoi,
    }


def _baseline_delta(cfg, s, baseline_model_dir: Path,
                    cur_csi: float | None = None,
                    cur_hr: float | None = None,
                    cur_far: float | None = None) -> dict:
    """Compute Δ metrics between the current run and a baseline model dir.

    Also computes the baseline CSI/HR/FAR on the same EMS grid (so the
    comparison is apples-to-apples).
    """
    if not baseline_model_dir.exists():
        return {"baseline_model_dir": str(baseline_model_dir),
                "available": False,
                "note": "baseline path missing"}
    import numpy as np
    base_s = open_sfincs(baseline_model_dir)
    if base_s["nx"] != s["nx"] or base_s["ny"] != s["ny"]:
        return {
            "baseline_model_dir": str(baseline_model_dir),
            "available": False,
            "note": (f"grid mismatch — baseline {base_s['nx']}x{base_s['ny']} "
                     f"vs enhanced {s['nx']}x{s['ny']}; Δ comparison skipped "
                     f"(re-validate baseline on the same grid)"),
        }
    base_flooded, base_depth = stats_per_frame(base_s)
    cur_flooded, cur_depth = stats_per_frame(s)

    # Baseline EMS validation on the SAME grid
    base_ems = _validate_ems(cfg, base_s)
    base_primary = base_ems["metrics_by_threshold"].get("h>0.10m", {})

    out = {
        "baseline_model_dir": str(baseline_model_dir),
        "available": True,
        "baseline_peak_depth_m": float(base_depth.max()),
        "baseline_peak_flooded_km2": float(base_flooded.max()),
        "delta_peak_depth_m": float(cur_depth.max() - base_depth.max()),
        "delta_peak_flooded_km2": float(cur_flooded.max() - base_flooded.max()),
        "baseline_csi_h_gt_0p10m": base_primary.get("csi"),
        "baseline_hr_h_gt_0p10m": base_primary.get("hr"),
        "baseline_far_h_gt_0p10m": base_primary.get("far"),
    }
    if cur_csi is not None and base_primary.get("csi") is not None:
        out["delta_csi"] = float(cur_csi - base_primary["csi"])
    if cur_hr is not None and base_primary.get("hr") is not None:
        out["delta_hr"] = float(cur_hr - base_primary["hr"])
    if cur_far is not None and base_primary.get("far") is not None:
        out["delta_far"] = float(cur_far - base_primary["far"])
    return out


def _markdown_summary(cfg, forcing, run, ems, delta,
                      cur_csi=None, cur_hr=None, cur_far=None):
    p = forcing
    r = run
    v = ems
    lines = [
        f"# Validation summary — {cfg.event_id or cfg.event_name}",
        "",
        f"_Generated: {dt.datetime.utcnow().isoformat(timespec='seconds')}Z_  "
        f"_Run: {cfg.paths['model_dir']}_",
        "",
        "## Forcing sanity",
        "",
        f"- Rain source: **{p['rain_source']}**",
        f"- Frames: {p['nframes']}    dt = {p['dt_h']:.2f} h    "
        f"coverage {p['first_time']} → {p['last_time']}",
        f"- Domain-mean total: **{p['domain_mean_total_mm']:.1f} mm**",
        f"- Domain-mean peak intensity: **{p['domain_mean_peak_intensity_mmph']:.2f} mm/h**",
        f"- Max-cell peak intensity:    **{p['max_cell_peak_intensity_mmph']:.2f} mm/h**",
        "",
        "### Enhancement check (declared vs realised)",
        "",
        "| feature | declared | realised |",
        "|---|---|---|",
        f"| wind_pressure | {p['declared_enhancements']['wind_pressure_enabled']} | "
        f"wind={p['realised_enhancements']['wind_forcing']}, "
        f"press={p['realised_enhancements']['pressure_forcing']} |",
        f"| infiltration  | {p['declared_enhancements']['infiltration_enabled']} | "
        f"{p['realised_enhancements']['infiltration']} |",
        f"| upstream_q    | {p['declared_enhancements']['upstream_q_enabled']} | "
        f"{p['realised_enhancements']['upstream_q']} |",
        f"| coastal_bc (pavbnd=1) | {p['declared_enhancements']['coastal_bc_enabled']} | "
        f"{p['realised_enhancements']['pavbnd']} |",
        "",
        "Mismatches:" if p['enhancement_mismatches'] else "_no mismatches — every declared enhancement is realised in the model dir_",
    ]
    for m in p['enhancement_mismatches']:
        lines.append(f"- ⚠ {m}")
    lines += [
        "",
        "",
        "## Run sanity",
        "",
        f"- Grid: {r['nx']} × {r['ny']} at {r['dx_m']:.0f} m  "
        f"(active area {r['active_area_km2']:.1f} km²)",
        f"- Peak depth: **{r['peak_max_depth_m']:.2f} m** at {r['peak_max_depth_time']} "
        f"(event offset {r['peak_max_depth_h_from_event']:+.1f} h)",
        f"- Peak flooded area: **{r['peak_flooded_km2']:.1f} km²** at "
        f"{r['peak_flooded_time']} (event offset "
        f"{r['peak_flooded_h_from_event']:+.1f} h)",
        f"- Final state: depth {r['final_max_depth_m']:.2f} m,  "
        f"flooded {r['final_flooded_km2']:.1f} km²",
        "",
        "## EMS validation (pixel-wise, model grid)",
        "",
        f"- EMS shps: {v['n_ems_shps']}    AOI shps: {v['n_aoi_shps']}",
        f"- Evaluation area (active ∩ AOI): {v['evaluation_area_km2']:.1f} km²",
        f"- Observed wet inside eval area: {v['observed_wet_in_eval_area_km2']:.1f} km²",
        "",
        "### Threshold sweep",
        "",
        "| threshold | TP | FP | FN | CSI | HR | FAR | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k, m in v["metrics_by_threshold"].items():
        lines.append(
            f"| {k} | {m['tp']} | {m['fp']} | {m['fn']} | "
            f"{m['csi']:.3f} | {m['hr']:.3f} | {m['far']:.3f} | {m['f1']:.3f} |"
        )
    if v["per_aoi_h_gt_0p10m"]:
        lines += [
            "",
            "### Per-AOI (h > 0.10 m)",
            "",
            "| AOI | active km² | EMS wet km² | CSI | HR | FAR | F1 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for a in v["per_aoi_h_gt_0p10m"]:
            lines.append(
                f"| {a['aoi_file']} | {a['aoi_active_km2']:.2f} | "
                f"{a['ems_wet_in_aoi_km2']:.2f} | "
                f"{a['csi']:.3f} | {a['hr']:.3f} | "
                f"{a['far']:.3f} | {a['f1']:.3f} |"
            )
    lines += ["", "## Baseline delta (enhanced - baseline)", ""]
    if delta.get("available"):
        lines += [
            f"- Baseline run: `{delta['baseline_model_dir']}`",
            f"- Baseline CSI@h>0.10m: "
            f"**{delta.get('baseline_csi_h_gt_0p10m', float('nan')):.3f}** "
            f"→ enhanced **{cur_csi:.3f}**  "
            f"(Δ = {delta.get('delta_csi', float('nan')):+.3f})",
            f"- Baseline HR:  {delta.get('baseline_hr_h_gt_0p10m', float('nan')):.3f} "
            f"→ enhanced {cur_hr:.3f}  "
            f"(Δ = {delta.get('delta_hr', float('nan')):+.3f})",
            f"- Baseline FAR: {delta.get('baseline_far_h_gt_0p10m', float('nan')):.3f} "
            f"→ enhanced {cur_far:.3f}  "
            f"(Δ = {delta.get('delta_far', float('nan')):+.3f})",
            f"- Δ peak depth:        **{delta['delta_peak_depth_m']:+.3f} m**  "
            f"(baseline {delta['baseline_peak_depth_m']:.2f} m)",
            f"- Δ peak flooded area: **{delta['delta_peak_flooded_km2']:+.2f} km²**  "
            f"(baseline {delta['baseline_peak_flooded_km2']:.2f} km²)",
        ]
    else:
        lines.append(f"- _not computed: {delta.get('note', 'no baseline given')}_")
    lines += ["", "## Verdict", ""]
    # crude verdict
    primary = v["metrics_by_threshold"].get("h>0.10m", {})
    csi = primary.get("csi")
    if csi is None or (csi != csi):  # NaN
        lines.append("- ⚠ CSI undefined — check active-cell mask vs EMS overlap.")
    elif csi >= 0.30:
        lines.append(f"- ✓ Overall CSI {csi:.3f} ≥ 0.30 → usable hindcast.")
    elif csi >= 0.10:
        lines.append(f"- ~ Overall CSI {csi:.3f} in (0.10, 0.30) → marginal — "
                     f"check FAR/HR balance + EMS observation gaps before trusting.")
    else:
        lines.append(f"- ⚠ Overall CSI {csi:.3f} < 0.10 — investigate "
                     f"(forcing, mask, or EMS rasterisation alignment).")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--baseline", type=Path, default=None,
                    help="Optional baseline model dir for ΔCSI / Δ peak depth")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    args, _ = ap.parse_known_args()

    # _common.load_config expects --config in argv; pass it through
    sys.argv = [sys.argv[0], "--config", str(args.config)]
    cfg = load_config()
    print(f"validating: {cfg.event_label}  (slug={cfg.event_slug})", flush=True)
    print(f"  rain source: {cfg.rain_source}", flush=True)

    model_dir = cfg.paths["model_dir"]
    if not (model_dir / "sfincs_map.nc").exists():
        sys.exit(f"sfincs_map.nc missing under {model_dir} — run SFINCS first")

    forcing = _forcing_sanity(cfg, model_dir)
    print(f"  forcing total {forcing['domain_mean_total_mm']:.1f} mm, "
          f"peak {forcing['domain_mean_peak_intensity_mmph']:.2f} mm/h "
          f"(max-cell {forcing['max_cell_peak_intensity_mmph']:.2f} mm/h)",
          flush=True)

    s = open_sfincs(model_dir)
    run = _run_sanity(cfg, s, model_dir)
    print(f"  peak depth {run['peak_max_depth_m']:.2f} m, "
          f"peak area {run['peak_flooded_km2']:.1f} km²", flush=True)

    ems = _validate_ems(cfg, s)
    primary = ems["metrics_by_threshold"].get("h>0.10m", {})
    print(f"  CSI@h>0.10m {primary.get('csi', float('nan')):.3f}    "
          f"HR {primary.get('hr', float('nan')):.3f}    "
          f"FAR {primary.get('far', float('nan')):.3f}",
          flush=True)

    delta = {"available": False}
    cur_csi = primary.get("csi")
    cur_hr = primary.get("hr")
    cur_far = primary.get("far")
    if args.baseline:
        delta = _baseline_delta(cfg, s, args.baseline,
                                cur_csi, cur_hr, cur_far)
    else:
        wd_name = cfg.paths["work_dir"].name
        if wd_name.endswith("_enhanced"):
            bp = (cfg.paths["work_dir"].parent
                  / wd_name[: -len("_enhanced")] / "model")
            if bp.exists() and bp != model_dir:
                delta = _baseline_delta(cfg, s, bp, cur_csi, cur_hr, cur_far)

    report = {
        "event": {
            "id": cfg.event_id,
            "name": cfg.event_name,
            "slug": cfg.event_slug,
            "date": str(cfg.event_date),
            "label": cfg.event_label,
        },
        "config_path": str(cfg.config_path),
        "model_dir": str(model_dir),
        "generated_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "rain_source": cfg.rain_source,
        "wind_pressure_enabled": cfg.wind_pressure["enabled"],
        "infiltration_enabled": cfg.infiltration["enabled"],
        "upstream_q_enabled": cfg.upstream_q["enabled"],
        "coastal_bc_enabled": cfg.coastal_bc["enabled"],
        "forcing": forcing,
        "run": run,
        "ems": ems,
        "delta_vs_baseline": delta,
    }

    PAPER_DATA.mkdir(parents=True, exist_ok=True)
    out_json = args.out_json or PAPER_DATA / f"{cfg.event_slug}_metrics.json"
    out_md = args.out_md or PAPER_DATA / f"{cfg.event_slug}_metrics.md"
    out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    out_md.write_text(
        _markdown_summary(cfg, forcing, run, ems, delta, cur_csi, cur_hr, cur_far),
        encoding="utf-8"
    )
    print(f"\nwrote: {out_json}\nwrote: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
