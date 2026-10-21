"""R6 figure export (MESE close-out, part C) - F1: six-event overview on Natural Earth (cartopy env).

(a) Mediterranean locator (Mercator) with the six model domains, labelled by event name and EMS code only;
(b)-(g) one panel per event in the run's own UTM zone: model-domain box (sfincs_map.nc grid extent) and the EMS AOI centroids.
Inputs: figures/data/F1_inputs.json, written by `r6_figures.py --fig F1data` (sfincs-viz env: model grids + AOI shapefiles),
and ONLY the Natural Earth shapefiles already cached in the cartopy data directory (no web tiles, no downloads: a missing file
is an error). Natural Earth is public domain.
Usage (cartopy env, base anaconda python):  python -I r6_fig1_overview.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r6_fig_common as C  # noqa: E402

SCRIPT = C.rel(Path(__file__))
INPUTS = C.DATA_DIR / "F1_inputs.json"
LAND, SEA, COAST, BORDER = "#ece9e2", "#dce9f3", "#6f6f6f", "#8a8a8a"
DOMAIN = C.OI["blue"]
AOI_FC = C.OI["orange"]
LOC_EXTENT = (-6.0, 31.5, 33.2, 46.0)            # lon0, lon1, lat0, lat1 of the locator (all six domains + labels)
# label anchor offsets (deg) from each domain centre in the locator, and alignment - layout only
LOC_LABEL = {"pineios": (-2.8, 1.0, "right"), "mandra": (1.9, -0.45, "left"), "strymonas": (-1.8, 1.55, "right"),
             "valencia": (1.6, -2.0, "left"), "emilia": (2.2, 1.0, "left"), "crete": (-1.6, -0.75, "right")}


def ne_path(kind: str, name: str, res: str) -> Path:
    import cartopy
    p = Path(cartopy.config["data_dir"]) / "shapefiles" / "natural_earth" / kind / f"ne_{res}_{name}.shp"
    if not p.exists():
        raise FileNotFoundError(f"Natural Earth file not cached: {p} (no download by design)")
    return p


_GEOMS = {}


def ne_clip(kind, name, res, box):
    """Geometries of a cached Natural Earth layer clipped to box = (lon0, lat0, lon1, lat1)."""
    import shapely.geometry as sg
    from cartopy.io import shapereader
    key = (kind, name, res)
    if key not in _GEOMS:
        _GEOMS[key] = list(shapereader.Reader(str(ne_path(kind, name, res))).geometries())
    b = sg.box(*box)
    out = []
    for g in _GEOMS[key]:
        if g.intersects(b):
            gi = g.intersection(b)
            if not gi.is_empty:
                out.append(gi)
    return out


def add_base(ax, box, res):
    import cartopy.crs as ccrs
    pc = ccrs.PlateCarree()
    ax.set_facecolor(SEA)
    ax.add_geometries(ne_clip("physical", "land", res, box), crs=pc, facecolor=LAND, edgecolor="none", zorder=1)
    ax.add_geometries(ne_clip("physical", "coastline", res, box), crs=pc, facecolor="none", edgecolor=COAST, linewidth=0.35, zorder=2)
    ax.add_geometries(ne_clip("cultural", "admin_0_boundary_lines_land", res, box), crs=pc, facecolor="none", edgecolor=BORDER,
                      linewidth=0.45, linestyle=(0, (3, 1.5)), zorder=2)
    return [C.rel(ne_path("physical", "land", res)), C.rel(ne_path("physical", "coastline", res)),
            C.rel(ne_path("cultural", "admin_0_boundary_lines_land", res))]


def nice_step(lo, hi, max_labels=3):
    """Smallest round step giving at most `max_labels` (and at least 2 where possible) grid lines inside [lo, hi]."""
    for s in (0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 5.0):
        n = math.floor(hi / s + 1e-9) - math.ceil(lo / s - 1e-9) + 1
        if n <= max_labels:
            return s
    return 10.0


def nice_length(km):
    best = 1
    for v in (1, 2, 5, 10, 20, 25, 50, 100, 200):
        if v <= km:
            best = v
    return best


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    import matplotlib.ticker as mticker
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    import cartopy.crs as ccrs
    from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
    C.apply_style(matplotlib)
    D = json.loads(INPUTS.read_text(encoding="utf-8"))
    ev = D["events"]
    if [e["event"] for e in ev] != ["pineios", "mandra", "strymonas", "valencia", "emilia", "crete"]:
        raise AssertionError("unexpected event order in F1_inputs.json")
    pc = ccrs.PlateCarree()
    halo = [pe.withStroke(linewidth=2.2, foreground="white")]
    W = C.WIDTH_2COL_MM
    # ---------------------------------------------------------------- geometry (mm)
    L, RM, T, B = 12.0, 3.0, 6.0, 13.0             # bottom: lon labels of the last row + the figure legend
    lon0, lon1, lat0, lat1 = LOC_EXTENT
    merc = ccrs.Mercator(central_longitude=13.0)
    xy = merc.transform_points(pc, np.array([lon0, lon1]), np.array([lat0, lat1]))
    LW = W - L - RM
    LH = LW * (xy[1, 1] - xy[0, 1]) / (xy[1, 0] - xy[0, 0])
    GAPX, PW, PH = 12.0, None, 44.0
    PW = (W - L - RM - 2 * GAPX) / 3
    ROWGAP = 15.0                                   # lon labels of the row above + panel titles
    H = T + LH + ROWGAP + PH + ROWGAP + PH + B
    fig = C.fig_mm(plt, W, H)
    # ---------------------------------------------------------------- (a) locator
    axL = C.ax_mm(fig, L, H - T - LH, LW, LH, projection=merc)
    axL.set_extent([lon0, lon1, lat0, lat1], crs=pc)
    ne_src = add_base(axL, (lon0 - 1, lat0 - 1, lon1 + 1, lat1 + 1), "50m")
    gls = []
    gl = axL.gridlines(crs=pc, draw_labels=True, linewidth=0.3, color="0.6", linestyle=":", xlocs=list(range(-5, 35, 5)),
                       ylocs=[35, 40, 45], zorder=3)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = {"size": 8}
    gls.append(gl)
    for e in ev:
        lo, la = np.array(e["domain_lonlat"]).T
        axL.fill(lo, la, transform=pc, facecolor=DOMAIN, alpha=0.35, edgecolor="none", zorder=4)
        axL.plot(lo, la, transform=pc, color=DOMAIN, lw=0.9, zorder=5)
        cx, cy = (lo.min() + lo.max()) / 2, (la.min() + la.max()) / 2
        dx, dy, ha = LOC_LABEL[e["event"]]
        axL.plot([cx, cx + dx * 0.92], [cy, cy + dy * 0.92], transform=pc, color="0.25", lw=0.5, zorder=3)
        t = axL.text(cx + dx, cy + dy, f"{e['name']} ({e['ems']})", transform=pc, ha=ha, va="center", fontsize=8, zorder=6)
        t.set_path_effects(halo)
    C.panel_letter(axL, "a", text="Mediterranean locator")
    leg_h = [Patch(facecolor=matplotlib.colors.to_rgba(DOMAIN, 0.35), edgecolor=DOMAIN, linewidth=0.9, label="model domain (grid extent)"),
             Line2D([], [], ls="none", marker="o", ms=4.2, mfc=AOI_FC, mec="k", mew=0.5, label="EMS area-of-interest centroid"),
             Line2D([], [], ls="none", marker="o", ms=4.2, mfc="white", mec="k", mew=0.7, label="EMS AOI, tier 3 (no product released)")]
    fig.legend(handles=leg_h, loc="lower center", bbox_to_anchor=(0.5, 0.8 / H), ncol=3, frameon=False, borderaxespad=0.0,
               columnspacing=2.0)
    # ---------------------------------------------------------------- (b)-(g) event panels
    srcs = [INPUTS]
    for i, e in enumerate(ev):
        row, col = divmod(i, 3)
        left = L + col * (PW + GAPX)
        bottom = B + (1 - row) * (PH + ROWGAP)
        zone = e["utm_zone"]
        proj = ccrs.UTM(zone=int(zone[:-1]), southern_hemisphere=zone.endswith("S"))
        x0, x1, y0, y1 = e["domain_xy"]
        t3 = e.get("aois_tier3", [])
        ax_ = np.array([x0, x1] + [a["x"] for a in e["aois"] + t3])
        ay_ = np.array([y0, y1] + [a["y"] for a in e["aois"] + t3])
        ex0, ex1, ey0, ey1 = ax_.min(), ax_.max(), ay_.min(), ay_.max()
        mx, my = 0.08 * (ex1 - ex0), 0.08 * (ey1 - ey0)
        ex0, ex1, ey0, ey1 = ex0 - mx, ex1 + mx, ey0 - 3.0 * my, ey1 + my        # bottom strip below all data: the scale bar
        cxm, cym = (ex0 + ex1) / 2, (ey0 + ey1) / 2
        w, h = ex1 - ex0, ey1 - ey0
        if w / h < PW / PH:
            w = h * PW / PH
        else:
            h = w * PH / PW
        ext = (cxm - w / 2, cxm + w / 2, cym - h / 2, cym + h / 2)
        ax = C.ax_mm(fig, left, bottom, PW, PH, projection=proj)
        ax.set_extent(ext, crs=proj)
        # lon/lat box of the panel (densified edges) for clipping the Natural Earth layers
        n = 40
        bx = np.r_[np.linspace(ext[0], ext[1], n), np.full(n, ext[1]), np.linspace(ext[1], ext[0], n), np.full(n, ext[0])]
        by = np.r_[np.full(n, ext[2]), np.linspace(ext[2], ext[3], n), np.full(n, ext[3]), np.linspace(ext[3], ext[2], n)]
        ll = pc.transform_points(proj, bx, by)
        box = (ll[:, 0].min() - 0.3, ll[:, 1].min() - 0.3, ll[:, 0].max() + 0.3, ll[:, 1].max() + 0.3)
        add_base(ax, box, "10m")
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transData, facecolor=matplotlib.colors.to_rgba(DOMAIN, 0.12),
                               edgecolor=DOMAIN, linewidth=1.1, zorder=4))
        ax.plot([a["x"] for a in e["aois"]], [a["y"] for a in e["aois"]], ls="none", marker="o", ms=4.2, mfc=AOI_FC, mec="k", mew=0.5,
                transform=ax.transData, zorder=6)
        if t3:                                       # Crete tier 3: AOIs of the activation without any released product
            ax.plot([a["x"] for a in t3], [a["y"] for a in t3], ls="none", marker="o", ms=4.2, mfc="white", mec="k", mew=0.7,
                    transform=ax.transData, zorder=6)
        bot = pc.transform_points(proj, np.linspace(ext[0], ext[1], n), np.full(n, ext[2]))      # lon along the bottom edge
        lef = pc.transform_points(proj, np.full(n, ext[0]), np.linspace(ext[2], ext[3], n))      # lat along the left edge
        sx = nice_step(bot[:, 0].min(), bot[:, 0].max())
        sy = nice_step(lef[:, 1].min(), lef[:, 1].max())
        g = ax.gridlines(crs=pc, draw_labels=True, linewidth=0.3, color="0.6", linestyle=":", zorder=3,
                         xlocs=mticker.MultipleLocator(sx), ylocs=mticker.MultipleLocator(sy))
        g.top_labels = g.right_labels = False
        g.bottom_labels, g.left_labels = "x", "y"
        g.x_inline = g.y_inline = False
        g.rotate_labels = False
        g.xlabel_style = g.ylabel_style = {"size": 8}
        g.xformatter = LongitudeFormatter(number_format=".1f" if sx < 1 else ".0f", dateline_direction_label=False)
        g.yformatter = LatitudeFormatter(number_format=".1f" if sy < 1 else ".0f")
        gls.append(g)
        # scale bar (lower right)
        km = nice_length(0.28 * w / 1e3)
        xe = ext[1] - 0.06 * w
        xs = xe - km * 1e3
        yb = ext[2] + 0.05 * h
        need_strip = (y0 - ext[2]) / h
        if need_strip < 0.16:
            raise AssertionError(f"{e['event']}: bottom strip {need_strip:.2f} too small for the scale bar")
        ax.plot([xs, xe], [yb, yb], color="k", lw=1.6, solid_capstyle="butt", transform=ax.transData, zorder=7)
        st = ax.text((xs + xe) / 2, yb + 0.02 * h, f"{km:g} km", ha="center", va="bottom", fontsize=8, transform=ax.transData, zorder=7)
        st.set_path_effects(halo)
        C.panel_letter(ax, "bcdefg"[i], text=f"{e['name']} ({e['ems']})")
        srcs += e["sources"]
        print(f"  ({'bcdefg'[i]}) {e['name']}: UTM {zone}, panel {w / 1e3:.0f} x {h / 1e3:.0f} km, grid step {sx:g}/{sy:g} deg, "
              f"scale bar {km} km, {len(e['aois'])} AOI centroids" + (f" + {len(t3)} tier-3 (hollow)" if t3 else ""))
    srcs += ne_src
    srcs += [C.rel(ne_path("physical", "land", "10m")), C.rel(ne_path("physical", "coastline", "10m")),
             C.rel(ne_path("cultural", "admin_0_boundary_lines_land", "10m"))]
    C.export(fig, "F1", dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT, sources=srcs,
             extra_texts=lambda: [t for g_ in gls for t in g_.label_artists], tiff_writer="tifffile",
             notes="locator (Mercator) + one panel per event in its UTM zone; domain boxes = sfincs_map.nc grid extents of the "
                   "canonical runs; AOI centroids from the runs' EMS area-of-interest polygons; Natural Earth 1:50m (locator) and "
                   "1:10m (panels) from the local cartopy cache only; events labelled by name and EMS code only")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
