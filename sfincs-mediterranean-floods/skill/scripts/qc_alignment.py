"""Static QC alignment figure: satellite + SFINCS hmax + EMS overlays."""
from __future__ import annotations

import sys
from pathlib import Path

from _common import load_config


def main():
    cfg = load_config()
    import numpy as np
    import xarray as xr
    from PIL import Image
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.patches import Patch

    from _anim_common import open_sfincs, load_polys_paths

    out_png = cfg.paths["deliverable_dir"] / "3_figures" / f"{cfg.event_slug}_qc_alignment.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    s = open_sfincs(cfg.paths["model_dir"])
    zsmax = s["ds"]["zsmax"].isel(timemax=-1).values
    hmax = np.maximum(zsmax - s["zb"], 0)
    hmax_m = np.where((s["msk"] > 0) & (hmax > 0.05), hmax, np.nan)

    polys = load_polys_paths(
        cfg.paths["data_dir"] / "ems_polygons",
        cfg.epsg,
        [
            ("ems", ["*DELINEATION*MONIT*crisis_information_poly.shp",
                      "*GRADING*observed_event_a.shp",
                      "*GRA_*observed_event_a.shp"], 80.0),
            ("aoi", ["*area_of_interest.shp",
                      "*area_of_interest_a.shp"], 60.0),
            ("hyd", ["*DELINEATION*hydrography_poly.shp",
                      "*GRADING*hydrography_l.shp",
                      "*GRA_*hydrography_l.shp"], 40.0),
        ],
    )
    print(f"polys: EMS {len(polys['ems'])}  AOI {len(polys['aoi'])}  hyd {len(polys['hyd'])}")

    bm_path = cfg.paths["data_dir"] / "basemap_satellite.png"
    bm = np.array(Image.open(bm_path).convert("RGB"))
    buf = float(cfg.animation.get("basemap_buffer_m", 3000))
    bm_xmin = s["xmin"] - buf; bm_xmax = s["xmax"] + buf
    bm_ymin = s["ymin"] - buf; bm_ymax = s["ymax"] + buf

    fig, ax = plt.subplots(figsize=(14, 11))
    ax.imshow(bm, extent=[bm_xmin, bm_xmax, bm_ymin, bm_ymax],
              origin="upper", interpolation="bilinear", alpha=0.9)
    vmax = max(float(np.nanmax(hmax_m)), 0.5) if np.isfinite(np.nanmax(hmax_m)) else 1.0
    pm = ax.pcolormesh(s["x"], s["y"], hmax_m, cmap="Blues",
                       norm=LogNorm(vmin=0.05, vmax=max(vmax, 0.5)),
                       shading="auto", alpha=0.8)

    def draw(geoms, **kw):
        for xs, ys in geoms:
            ax.plot(xs, ys, **kw)

    draw(polys["hyd"], color="cyan", linewidth=0.8, alpha=0.85)
    draw(polys["aoi"], color="#facc15", linewidth=1.3, alpha=0.85)
    draw(polys["ems"], color="red", linewidth=0.6, alpha=0.85)

    ax.set_xlim(s["xmin"], s["xmax"])
    ax.set_ylim(s["ymin"], s["ymax"])
    ax.set_aspect("equal")
    ax.set_title(f"{cfg.event_label} QC alignment\n"
                 f"satellite + SFINCS hmax (log Blues) + EMS observed flood (red) + AOI (yellow) + hydrography (cyan)")
    ax.set_xlabel(f"Easting (EPSG:{cfg.epsg}) [m]")
    ax.set_ylabel("Northing [m]")
    plt.colorbar(pm, ax=ax, label="hmax [m] (log)")
    ax.legend(handles=[
        Patch(facecolor="none", edgecolor="red", label="EMS observed flood"),
        Patch(facecolor="none", edgecolor="#facc15", label="EMS AOI"),
        Patch(facecolor="none", edgecolor="cyan", label="Permanent hydrography"),
    ], loc="lower right", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote: {out_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
