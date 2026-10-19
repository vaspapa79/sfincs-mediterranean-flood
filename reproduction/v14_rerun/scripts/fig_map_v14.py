"""Phase 4d (GO Phases 3-5, 2026-10-19) — maximum-inundation map of one v1.4 run against the EMS truth (Figures 3, 5, 7, 8, 9
equivalents; Crete per cluster), PNG + the data behind it as CSV (per-AOI TP / FP / FN km² and the union row).

Rendering: hmax > threshold in blue (depth shaded), EMS observed polygons as red outlines, AOI polygons dashed black,
cells removed by the v1.4 evaluation mask (WorldCover 80 ∪ open sea) hatched grey, inactive cells white; UTM axes in km.
`--clusters name=west,south,east,north` (lon/lat) draws one panel per cluster (Crete: Lefka Ori / Psiloritis / Dikti–Lasithi).
Usage: python -I fig_map_v14.py --repo <worktree> --config <run yaml> --exclusion-tif <tif> --metrics <v14 json> --out <png> [--title ...] [--clusters ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--exclusion-tif", type=Path)
    ap.add_argument("--metrics", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--title", default="")
    ap.add_argument("--threshold", type=float, default=0.10)
    ap.add_argument("--clusters", action="append", default=[], help="name=west,south,east,north (lon/lat): one panel per cluster")
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    os.environ.setdefault("GDAL_DATA", os.path.join(os.environ.get("CONDA_PREFIX", ""), "Library", "share", "gdal"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    import pyproj
    from _common import load_config
    import validate_event_v2 as V
    cfg = load_config(["--config", str(a.config)])
    s = V.open_sfincs_light(cfg.paths["model_dir"])
    excl = None
    if a.exclusion_tif:
        from eval_exclusion import read_mask_for_grid
        excl = read_mask_for_grid(a.exclusion_tif, s)
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aois = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
    ems_wet = V._rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    aoi_m = V._rasterise_polys_to_grid(aois, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) if aois else np.ones_like(ems_wet)
    active = s["msk"] > 0
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    wet = (hmax > a.threshold) & active
    universe = active & aoi_m & (~excl if excl is not None else True)
    x, y = s["x"], s["y"]
    ext = [x.min() / 1e3 - s["dx"] / 2e3, x.max() / 1e3 + s["dx"] / 2e3, y.min() / 1e3 - s["dy"] / 2e3, y.max() / 1e3 + s["dy"] / 2e3]
    A = s["cell_area_km2"]
    # ---- data behind the figure: per-AOI contingency on the v1.4 universe
    rows = []
    for shp in aois:
        am = V._rasterise_polys_to_grid([shp], s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) & universe
        c = V._contingency_full(wet, ems_wet, am)
        rows.append({"aoi_file": shp.name, "universe_km2": round(am.sum() * A, 2), "obs_km2": round((ems_wet & am).sum() * A, 3), "model_km2": round((wet & am).sum() * A, 3),
                     "tp_km2": round(c["tp"] * A, 3), "fp_km2": round(c["fp"] * A, 3), "fn_km2": round(c["fn"] * A, 3), "csi": c["csi"], "hr": c["hr"], "far": c["far"], "bias": c["bias"]})
    c = V._contingency_full(wet, ems_wet, universe)
    rows.append({"aoi_file": "UNION", "universe_km2": round(universe.sum() * A, 2), "obs_km2": round((ems_wet & universe).sum() * A, 3), "model_km2": round((wet & universe).sum() * A, 3),
                 "tp_km2": round(c["tp"] * A, 3), "fp_km2": round(c["fp"] * A, 3), "fn_km2": round(c["fn"] * A, 3), "csi": c["csi"], "hr": c["hr"], "far": c["far"], "bias": c["bias"]})
    rows.append({"aoi_file": "WHOLE_ACTIVE_DOMAIN", "universe_km2": round(active.sum() * A, 2), "obs_km2": round((ems_wet & active).sum() * A, 3), "model_km2": round((wet & active).sum() * A, 3),
                 "tp_km2": round(float(np.nanmax(np.where(active, hmax, np.nan))), 3), "fp_km2": None, "fn_km2": None, "csi": None, "hr": None, "far": None, "bias": None})
    rows[-1]["note"] = "tp_km2 column of this row = peak hmax (m) over the active domain; model_km2 = wet area over the whole active domain"
    for r in rows[:-1]:
        r["note"] = ""
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    # ---- panels
    panels = []
    if a.clusters:
        tr = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
        for cl in a.clusters:
            name, box = cl.split("=", 1)
            w_, s_, e_, n_ = (float(v) for v in box.split(","))
            x0, y0 = tr.transform(w_, s_); x1, y1 = tr.transform(e_, n_)
            panels.append((name, [x0 / 1e3, x1 / 1e3, y0 / 1e3, y1 / 1e3]))
    else:
        panels.append((a.title or cfg.event_label, ext))
    cmap = LinearSegmentedColormap.from_list("depth", ["#cfe3f7", "#4a90d9", "#08306b"])
    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(7.2 if n == 1 else 3.6 * n, 6.0 if n == 1 else 3.6), squeeze=False)
    depth = np.where(wet, np.minimum(hmax, 3.0), np.nan)
    for ax, (name, pe) in zip(axes[0], panels):
        base = np.where(active, 0.92, np.nan)
        ax.imshow(base, extent=ext, origin="lower", cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        if excl is not None:
            ax.imshow(np.where(excl & active, 0.6, np.nan), extent=ext, origin="lower", cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        im = ax.imshow(depth, extent=ext, origin="lower", cmap=cmap, vmin=0, vmax=3.0, interpolation="nearest")
        ax.contour(ems_wet.astype(float), levels=[0.5], extent=ext, origin="lower", colors="red", linewidths=0.5)
        if aois:
            ax.contour(aoi_m.astype(float), levels=[0.5], extent=ext, origin="lower", colors="k", linewidths=0.6, linestyles="dashed")
        ax.set_xlim(pe[0], pe[1]); ax.set_ylim(pe[2], pe[3]); ax.set_aspect("equal")
        ax.set_title(name, fontsize=9); ax.set_xlabel("UTM E (km)"); ax.set_ylabel("UTM N (km)")
    cb = fig.colorbar(im, ax=axes[0].tolist(), shrink=0.7, pad=0.02); cb.set_label(f"hmax (m), cells > {a.threshold:g} m")
    axes[0][0].plot([], [], color="red", lw=1, label="EMS observed flood"); axes[0][0].plot([], [], color="k", ls="--", lw=1, label="EMS areas of interest")
    axes[0][0].fill([], [], color="0.6", label="removed by the v1.4 evaluation mask"); axes[0][0].legend(fontsize=6.5, loc="lower left", frameon=True)
    m = json.loads(a.metrics.read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"] if a.metrics and a.metrics.exists() else None
    sub = f"CSI {m['csi']:.3f}  HR {m['hr']:.3f}  FAR {m['far']:.3f}  B {m['bias']:.2f}" if m else ""
    fig.suptitle((a.title or cfg.event_label) + (f" — {sub}" if sub and n > 1 else ""), fontsize=9)
    if n == 1 and sub:
        axes[0][0].text(0.01, 0.99, sub, transform=axes[0][0].transAxes, va="top", fontsize=7, bbox=dict(fc="white", ec="none", alpha=0.8))
    fig.savefig(a.out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", a.out, "and", a.out.with_suffix(".csv"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
