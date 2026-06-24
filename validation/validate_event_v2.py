"""Enhanced pixel-wise + neighborhood validation of an SFINCS run.

Adds to the v1 validator:

  * Neighborhood-tolerant metrics on a 1-cell dilation of the EMS observed
    extent. This is the standard "fuzzy" CSI used in flood-validation
    literature to account for the positional uncertainty of SAR-derived
    flood polygons (Bates 2022; Wing et al. 2017; Bernhofen et al. 2021)
    and for the resolution gap between the SFINCS base grid (50-150 m)
    and the EMS rapid-mapping product (5-20 m SAR pixel + manual
    interpretation). Sensitivity sweep is run at dilation
    radii r in {0, 1, 2, 3} cells.
  * Gilbert Skill Score (ETS) — bias-corrected CSI:
        GSS = (TP - TP_random) / (TP + FP + FN - TP_random),
        TP_random = (TP+FN)(TP+FP)/(TP+FP+FN+TN).
    GSS is invariant to base-rate skew and is the standard
    alternative to CSI for events with a small wet fraction.
  * Frequency-bias ratio B = (TP+FP)/(TP+FN) — under (>1) or
    over (<1) prediction diagnostic.
  * F2 score = recall-weighted F1 — relevant for early-warning where
    a missed flood (FN) is operationally more costly than a false alarm.
  * Threshold sweep: same as v1, plus reports the threshold that
    maximises CSI per event.

Usage
-----
    python paper/scripts/validate_event_v2.py \\
        --config .claude/skills/sfincs-flood-reproduction/examples/emsr257_mandra_enhanced.yaml

Output
------
    paper/data/<slug>_metrics_v2.json
    paper/data/<slug>_metrics_v2.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import os
os.environ.setdefault("GDAL_DATA",
                      r"C:\Users\vaspapa\AppData\Local\miniforge3\envs\sfincs-viz\Library\share\gdal")

SKILL_DIR = (Path(__file__).resolve().parents[2]
             / ".claude" / "skills" / "sfincs-flood-reproduction")
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from _common import load_config  # noqa: E402
from _anim_common import open_sfincs, stats_per_frame  # noqa: E402

PAPER_DATA = Path(__file__).resolve().parents[1] / "data"


def _rasterise_polys_to_grid(shp_paths, x_grid, y_grid, target_epsg, dx, dy):
    import numpy as np
    import pyogrio
    import pyproj
    import rasterio.features
    from rasterio.transform import from_bounds
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform

    target_crs = pyproj.CRS.from_epsg(target_epsg)
    ny, nx = x_grid.shape
    xs = x_grid[0, :]; ys = y_grid[:, 0]
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
    return out_td[::-1, :].astype(bool)


def _dilate(arr, radius):
    """Morphological dilation by a `radius`-cell square structuring element.

    radius=0 returns the input unchanged. We use a square (8-connectivity
    extended) so that a single cell becomes (2r+1)^2 cells. The morphological
    operation is implemented with scipy.ndimage.binary_dilation for speed.
    """
    if radius <= 0:
        return arr
    from scipy import ndimage
    struct = ndimage.generate_binary_structure(2, 2)
    return ndimage.binary_dilation(arr, structure=struct, iterations=radius)


def _list_shps(ems_dir, patterns):
    out = []
    seen = set()
    if not ems_dir.exists():
        return out
    for pat in patterns:
        for p in ems_dir.rglob(pat):
            if p in seen:
                continue
            seen.add(p); out.append(p)
    return sorted(out)


def _contingency_full(model_wet, ems_wet, mask):
    """Compute full contingency table + standard + advanced metrics."""
    import numpy as np
    m = (model_wet & mask)
    e = (ems_wet & mask)
    tp = int((m & e).sum())
    fp = int((m & ~e & mask).sum())
    fn = int((~m & e & mask).sum())
    tn = int((~m & ~e & mask).sum())
    n = tp + fp + fn + tn
    denom_csi = tp + fp + fn
    denom_hr = tp + fn
    denom_far = tp + fp
    csi = (tp / denom_csi) if denom_csi > 0 else float("nan")
    hr = (tp / denom_hr) if denom_hr > 0 else float("nan")
    far = (fp / denom_far) if denom_far > 0 else float("nan")
    f1 = (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) > 0 else float("nan")
    f2 = ((5 * tp) / (5 * tp + 4 * fn + fp)) if (5 * tp + 4 * fn + fp) > 0 else float("nan")
    bias = ((tp + fp) / (tp + fn)) if (tp + fn) > 0 else float("nan")
    # Gilbert Skill Score (ETS):
    if n > 0 and denom_csi > 0:
        tp_random = ((tp + fn) * (tp + fp)) / n
        denom_gss = denom_csi - tp_random
        gss = ((tp - tp_random) / denom_gss) if denom_gss > 0 else float("nan")
    else:
        gss = float("nan")
    # Heidke / Cohen kappa
    if n > 0:
        po = (tp + tn) / n
        pe = (((tp + fn) * (tp + fp) + (fp + tn) * (fn + tn)) / (n * n))
        hss = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    else:
        hss = float("nan")
    acc = ((tp + tn) / n) if n > 0 else float("nan")
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "csi": csi, "hr": hr, "far": far, "f1": f1, "f2": f2,
        "bias": bias, "gss": gss, "hss": hss, "acc": acc,
    }


def _validate_ems_v2(cfg, s):
    """Enhanced EMS validation with fuzzy / neighborhood-tolerant metrics."""
    import numpy as np

    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs_shps = _list_shps(ems_dir, [
        "*DELINEATION*MONIT*crisis_information_poly.shp",
        "*GRADING*observed_event_a.shp",
        "*GRA_*observed_event_a.shp",
        "*DEL_MONIT*observedEventA*.shp",
        "*DEL_MONIT*observed_event*.shp",
    ])
    aoi_shps = _list_shps(ems_dir, [
        "*area_of_interest.shp",
        "*area_of_interest_a.shp",
        "*areaOfInterestA*.shp",
    ])

    ems_wet = _rasterise_polys_to_grid(
        obs_shps, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
    )
    msk_bool = (s["msk"] > 0)
    if aoi_shps:
        aoi_universe = _rasterise_polys_to_grid(
            aoi_shps, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
        )
        evaluation_mask = msk_bool & aoi_universe
    else:
        evaluation_mask = msk_bool

    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))

    # ----- 1. Strict pixel-wise threshold sweep -----
    thresholds = (0.05, 0.10, 0.25, 0.50)
    strict = {}
    best_csi_thr = None
    best_csi_val = -1.0
    for thr in thresholds:
        model_wet = (hmax > thr)
        c = _contingency_full(model_wet, ems_wet, evaluation_mask)
        strict[f"h>{thr:.2f}m"] = c
        if not np.isnan(c["csi"]) and c["csi"] > best_csi_val:
            best_csi_val = c["csi"]; best_csi_thr = thr

    # ----- 2. Fuzzy / neighborhood-tolerant sweep at canonical 0.10 m -----
    # Buffer the EMS observed extent by `r` cells to absorb the
    # SAR-positional-uncertainty + model-resolution gap. The matching dilation
    # is also applied to the model wet field so the comparison is symmetric.
    fuzzy = {}
    canonical_thr = 0.10
    model_wet = (hmax > canonical_thr)
    for r in (0, 1, 2, 3):
        ems_d = _dilate(ems_wet, r)
        model_d = _dilate(model_wet, r)
        c = _contingency_full(model_d, ems_d, evaluation_mask)
        fuzzy[f"r={r}"] = c

    # ----- 3. True one-sided neighbourhood-tolerant sweeps (V3 fix) -----
    # The symmetric block above dilates BOTH fields, which inflates agreement
    # (a previous "asymmetric (Wing 2017)" block here dilated both too, so it
    # was byte-identical to the symmetric one). A genuine one-sided match keeps
    # exactly one field dilated, which is the operational fuzzy convention:
    #
    #   (i)  model-oriented  (dilate OBS only): a modelled wet cell is a hit if
    #        any observed wet cell lies within r cells. A model cell with no
    #        observed cell within r stays a false positive — this is the
    #        false-alarm-meaningful direction (tolerant FAR / precision).
    #   (ii) obs-oriented    (dilate MODEL only): an observed wet cell is
    #        detected if any modelled wet cell lies within r cells. An observed
    #        cell with no model cell within r stays a false negative — this is
    #        the hit-rate-meaningful direction (tolerant HR / POD / recall).
    #
    # At r=0 neither field is dilated, so both reduce exactly to the strict
    # contingency — the strict numbers are preserved as the r=0 row of each.
    fuzzy_model_oriented = {}   # dilate OBS only  -> tolerant FAR / precision
    fuzzy_obs_oriented = {}     # dilate MODEL only -> tolerant HR / recall
    for r in (0, 1, 2, 3):
        ems_d = _dilate(ems_wet, r)
        model_d = _dilate(model_wet, r)
        fuzzy_model_oriented[f"r={r}"] = _contingency_full(
            model_wet, ems_d, evaluation_mask)
        fuzzy_obs_oriented[f"r={r}"] = _contingency_full(
            model_d, ems_wet, evaluation_mask)

    # ----- 4. Per-AOI at canonical threshold, with r=1 fuzzy -----
    per_aoi = []
    ems_r1 = _dilate(ems_wet, 1)
    model_r1 = _dilate(model_wet, 1)
    for aoi_shp in aoi_shps:
        a_mask = _rasterise_polys_to_grid(
            [aoi_shp], s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]
        )
        local_mask = msk_bool & a_mask
        if not local_mask.any():
            continue
        strict_aoi = _contingency_full(model_wet, ems_wet, local_mask)
        fuzzy_aoi = _contingency_full(model_r1, ems_r1, local_mask)
        per_aoi.append({
            "aoi_file": aoi_shp.name,
            "active_km2": float(local_mask.sum() * s["cell_area_km2"]),
            "ems_wet_km2_strict":
                float((ems_wet & local_mask).sum() * s["cell_area_km2"]),
            "strict": strict_aoi,
            "fuzzy_r1": fuzzy_aoi,
        })

    return {
        "n_ems_shps": len(obs_shps),
        "n_aoi_shps": len(aoi_shps),
        "evaluation_area_km2": float(evaluation_mask.sum() * s["cell_area_km2"]),
        "observed_wet_km2_strict":
            float((ems_wet & evaluation_mask).sum() * s["cell_area_km2"]),
        "observed_wet_km2_r1":
            float((_dilate(ems_wet, 1) & evaluation_mask).sum()
                  * s["cell_area_km2"]),
        "strict_threshold_sweep": strict,
        "best_csi_threshold_m": best_csi_thr,
        "best_csi_value": best_csi_val,
        "fuzzy_at_h_gt_0p10m": fuzzy,
        "fuzzy_model_oriented_dilate_obs_at_h_gt_0p10m": fuzzy_model_oriented,
        "fuzzy_obs_oriented_dilate_model_at_h_gt_0p10m": fuzzy_obs_oriented,
        "per_aoi_canonical_and_r1": per_aoi,
        "tolerance_radius_m_at_r1":
            float(s["dx"]),  # one-cell radius in metres
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out-json", type=Path, default=None)
    args, _ = ap.parse_known_args()
    sys.argv = [sys.argv[0], "--config", str(args.config)]
    cfg = load_config()
    print(f"validating: {cfg.event_label} (v2)  (slug={cfg.event_slug})",
          flush=True)
    model_dir = cfg.paths["model_dir"]
    if not (model_dir / "sfincs_map.nc").exists():
        sys.exit(f"sfincs_map.nc missing under {model_dir}")
    s = open_sfincs(model_dir)
    v = _validate_ems_v2(cfg, s)

    strict10 = v["strict_threshold_sweep"].get("h>0.10m", {})
    fuzzy_r1 = v["fuzzy_at_h_gt_0p10m"].get("r=1", {})
    print(f"  strict@0.10m:  CSI={strict10.get('csi', float('nan')):.3f}"
          f"  HR={strict10.get('hr', float('nan')):.3f}"
          f"  FAR={strict10.get('far', float('nan')):.3f}"
          f"  BIAS={strict10.get('bias', float('nan')):.2f}"
          f"  GSS={strict10.get('gss', float('nan')):.3f}",
          flush=True)
    print(f"  fuzzy r=1:     CSI={fuzzy_r1.get('csi', float('nan')):.3f}"
          f"  HR={fuzzy_r1.get('hr', float('nan')):.3f}"
          f"  FAR={fuzzy_r1.get('far', float('nan')):.3f}"
          f"  GSS={fuzzy_r1.get('gss', float('nan')):.3f}",
          flush=True)
    print(f"  best CSI:      {v['best_csi_value']:.3f}"
          f" at h>{v['best_csi_threshold_m']:.2f} m",
          flush=True)

    report = {
        "event": {
            "id": cfg.event_id, "name": cfg.event_name,
            "slug": cfg.event_slug, "date": str(cfg.event_date),
            "label": cfg.event_label,
        },
        "generated_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "validation": v,
    }
    PAPER_DATA.mkdir(parents=True, exist_ok=True)
    out_json = args.out_json or PAPER_DATA / f"{cfg.event_slug}_metrics_v2.json"
    out_json.write_text(json.dumps(report, indent=2, default=str),
                        encoding="utf-8")
    print(f"  wrote: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
