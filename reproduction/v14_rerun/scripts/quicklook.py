"""Quick-look maximum-depth PNG of one SFINCS run against the EMS truth union (no scoring here).

Usage: python -I quicklook.py --repo <worktree> --config <yaml> [--work <work dir override>] --out <png>
       [--metrics <validation json>] [--exclusion-tif <tif>] [--title "..."]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--metrics", type=Path)
    ap.add_argument("--exclusion-tif", type=Path)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    if a.work:
        os.environ["SFINCS_WORK_DIR"] = str(a.work)
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from _common import load_config
    import validate_event_v2 as V
    cfg = load_config(["--config", str(a.config)])
    s = V.open_sfincs_light(cfg.paths["model_dir"])          # zsmax only; the hourly zs would be 2.4 GB (+ depths) on the Crete grid
    s["xmin"] = float(s["x"].min()) - s["dx"] / 2; s["xmax"] = float(s["x"].max()) + s["dx"] / 2
    s["ymin"] = float(s["y"].min()) - s["dy"] / 2; s["ymax"] = float(s["y"].max()) + s["dy"] / 2
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aoi = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
    ems_wet = V._rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    aoi_m = V._rasterise_polys_to_grid(aoi, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) if aoi else np.ones_like(ems_wet)
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    hmax = np.where(s["msk"] > 0, hmax, np.nan)
    excl = None
    if a.exclusion_tif:
        from eval_exclusion import read_mask_for_grid
        excl = read_mask_for_grid(a.exclusion_tif, s)
    ext = [s["xmin"] / 1000, s["xmax"] / 1000, s["ymin"] / 1000, s["ymax"] / 1000]
    fig, ax = plt.subplots(figsize=(10, 10 * (s["ymax"] - s["ymin"]) / (s["xmax"] - s["xmin"])), dpi=110)
    ax.set_facecolor("0.35")                                                       # inactive cells = dark grey
    ax.imshow(np.where(s["msk"] > 0, 0.08, np.nan), extent=ext, origin="lower", cmap="Greys", vmin=0, vmax=1)   # active = light
    if excl is not None:
        ax.imshow(np.where(excl, 0.45, np.nan), extent=ext, origin="lower", cmap="Greys", vmin=0, vmax=1, alpha=0.8)
    hm = np.where(hmax > 0.10, hmax, np.nan)
    im = ax.imshow(hm, extent=ext, origin="lower", cmap="Blues", norm=LogNorm(vmin=0.1, vmax=max(5.0, float(np.nanmax(hm)) if np.isfinite(np.nanmax(hm)) else 5.0)))
    ax.contour(aoi_m.astype(float), levels=[0.5], extent=ext, origin="lower", colors="k", linewidths=0.6, linestyles="--")
    ax.contour(ems_wet.astype(float), levels=[0.5], extent=ext, origin="lower", colors="red", linewidths=0.6)
    txt = ""
    if a.metrics and a.metrics.exists():
        m = json.loads(a.metrics.read_text(encoding="utf-8"))["validation"]
        c = m["strict_threshold_sweep"]["h>0.10m"]
        txt = (f"h>0.10 m: CSI {c['csi']:.3f}  HR {c['hr']:.3f}  FAR {c['far']:.3f}  B {c['bias']:.2f}  GSS {c['gss']:.3f}\n"
               f"eval {m['evaluation_area_km2']:.0f} km2, observed {m['observed_wet_km2_strict']:.1f} km2, "
               f"modelled wet (eval) {(c['tp'] + c['fp']) * s['cell_area_km2']:.1f} km2")
    ax.set_title((a.title or f"{cfg.event_label}") + ("\n" + txt if txt else ""), fontsize=9)
    ax.set_xlabel("UTM E (km)"); ax.set_ylabel("UTM N (km)")
    cb = fig.colorbar(im, ax=ax, shrink=0.6); cb.set_label("max depth (m), h > 0.10 m")
    ax.plot([], [], color="red", lw=1, label="EMS observed flood"); ax.plot([], [], color="k", ls="--", lw=1, label="AOI union")
    if excl is not None:
        ax.plot([], [], color="0.6", lw=6, label="excluded (WC80 ∪ open sea)")
    ax.legend(loc="lower left", fontsize=8)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
