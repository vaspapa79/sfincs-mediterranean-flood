"""R6 figure export (MESE close-out, part C) - shared helpers for every figure generator.

Imported by r6_figures.py (sfincs-viz env: F3-F11 + the F1 data preparation) and by r6_fig1_overview.py (cartopy env: F1),
so it uses only APIs common to matplotlib 3.8 / 3.11 and Pillow 10 / 12.

  * export geometry: 174 mm (two-column) or 84 mm (one-column) wide, height <= 234 mm; 600 dpi for line art and combination
    figures (raster + line/text, every map), 300 dpi only for pure halftone;
  * lettering: sans-serif (Arial), 8 pt everywhere (panel letters 9 pt bold) - checked on the rendered figure;
  * writers: F<n>.tiff (RGB, LZW, dpi tag) + F<n>_preview.png (<= 2 MB) + figures/meta/F<n>.json (provenance for the manifest);
  * layout checks on the rendered figure: every text >= 8 pt, inside the canvas, no two texts overlapping.
"""
from __future__ import annotations

import datetime as dt
import io
import json
from pathlib import Path

MM = 1.0 / 25.4                       # inch per mm
WIDTH_2COL_MM = 174.0
WIDTH_1COL_MM = 84.0
MAX_HEIGHT_MM = 234.0
DPI_COMBINATION = 600                 # raster + line/text (every map) and line art
DPI_HALFTONE = 300                    # pure halftone only (none in this set)
PREVIEW_MAX_BYTES = 2 * 1024 * 1024
MIN_PT = 8.0

R6 = Path(__file__).resolve().parents[1]          # <repo>/reproduction/r6
REPO = R6.parents[1]
FIG_DIR = R6 / "figures"
META_DIR = FIG_DIR / "meta"
DATA_DIR = FIG_DIR / "data"
CACHE_DIR = FIG_DIR / "_cache"

# Okabe & Ito (2008) colour-blind-safe qualitative palette
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7"}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(p) -> str:
    """Repository-relative POSIX path when under the worktree, else the absolute POSIX path."""
    p = Path(p)
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def apply_style(mpl) -> None:
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "legend.title_fontsize": 8, "figure.titlesize": 8,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.pad": 2.0,
        "ytick.major.pad": 2.0, "axes.labelpad": 2.5, "axes.titlepad": 3.0, "lines.linewidth": 1.0,
        "patch.linewidth": 0.6, "hatch.linewidth": 0.5, "legend.frameon": False, "legend.handlelength": 1.8,
        "legend.borderaxespad": 0.3, "legend.columnspacing": 1.2, "legend.handletextpad": 0.5,
        "figure.facecolor": "white", "savefig.facecolor": "white", "axes.unicode_minus": True,
        "mathtext.default": "regular", "mathtext.fontset": "custom", "mathtext.rm": "Arial", "mathtext.it": "Arial:italic",
        "mathtext.bf": "Arial:bold", "mathtext.sf": "Arial", "image.interpolation": "nearest",
    })


def fig_mm(plt, width_mm: float, height_mm: float):
    if height_mm > MAX_HEIGHT_MM + 1e-6:
        raise ValueError(f"figure height {height_mm:.1f} mm exceeds {MAX_HEIGHT_MM} mm")
    return plt.figure(figsize=(width_mm * MM, height_mm * MM))


def ax_mm(fig, left_mm, bottom_mm, width_mm, height_mm, **kw):
    """Axes placed in millimetres from the lower-left corner of the figure."""
    W, H = fig.get_size_inches() / MM
    return fig.add_axes([left_mm / W, bottom_mm / H, width_mm / W, height_mm / H], **kw)


def panel_letter(ax, letter, x=0.0, y=1.0, dx_pt=0.0, dy_pt=3.0, ha="left", va="bottom", text=None, **kw):
    """Bold (a)/(b)/... (optionally followed by a plain-weight `text`) above the upper-left corner of `ax`."""
    import matplotlib.transforms as mtrans
    tr = ax.transAxes + mtrans.ScaledTranslation(dx_pt / 72.0, dy_pt / 72.0, ax.figure.dpi_scale_trans)
    t = ax.text(x, y, f"({letter})", transform=tr, ha=ha, va=va, fontsize=9, fontweight="bold", **kw)
    if text:
        ax.figure.canvas.draw()
        bb = t.get_window_extent(renderer=ax.figure.canvas.get_renderer())
        w_pt = bb.width * 72.0 / ax.figure.dpi
        tr2 = ax.transAxes + mtrans.ScaledTranslation((dx_pt + w_pt + 3.0) / 72.0, dy_pt / 72.0, ax.figure.dpi_scale_trans)
        ax.text(x, y, text, transform=tr2, ha="left", va=va, fontsize=8, **kw)
    return t


# --------------------------------------------------------------------------------------------------- layout checks
def layout_report(fig, min_pt: float = MIN_PT, tol_px: float = 1.0, ignore_overlap_pairs=(), extra_texts=(), dpi=None,
                  edge_mm: float = 0.3):
    """Draw `fig` (at the export `dpi`: text metrics are hinted per resolution) and return a list of problems: texts below
    `min_pt`, texts closer than `edge_mm` to the canvas edge (or outside it), overlapping texts.

    Only visible, non-empty texts that the renderer actually places are considered (tick labels included)."""
    from matplotlib.text import Text
    dpi0 = fig.get_dpi()
    if dpi:
        fig.set_dpi(dpi)
    try:
        return _layout_problems(fig, Text, min_pt, tol_px, ignore_overlap_pairs, extra_texts, edge_mm)
    finally:
        fig.set_dpi(dpi0)


def _layout_problems(fig, Text, min_pt, tol_px, ignore_overlap_pairs, extra_texts, edge_mm):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    edge = edge_mm * MM * fig.get_dpi()
    # tick labels of ticks outside the view interval are kept by matplotlib but never drawn: skip exactly those
    undrawn = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            eps = 1e-9 * max(1.0, abs(hi - lo))
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not (lo - eps <= tick.get_loc() <= hi + eps):
                    undrawn.update((id(tick.label1), id(tick.label2)))
    texts, seen = [], set()
    for t in list(fig.findobj(Text)) + list(extra_texts() if callable(extra_texts) else extra_texts):
        if id(t) in seen or not t.get_visible() or not t.get_text().strip() or id(t) in undrawn:
            continue
        seen.add(id(t))
        try:
            bb = t.get_window_extent(renderer=r)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        texts.append((t, bb))
    problems = []
    for t, bb in texts:
        if t.get_fontsize() < min_pt - 1e-6:
            problems.append(f"font {t.get_fontsize():.2f} pt < {min_pt} pt: {t.get_text()!r}")
        if bb.x0 < edge or bb.y0 < edge or bb.x1 > W - edge or bb.y1 > H - edge:
            problems.append(f"text within {edge_mm} mm of / outside the canvas edge ({bb.x0:.0f},{bb.y0:.0f},{bb.x1:.0f},{bb.y1:.0f} "
                            f"vs {W}x{H} px): {t.get_text()!r}")
    ign = {frozenset(p) for p in ignore_overlap_pairs}
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            (ti, bi), (tj, bj) = texts[i], texts[j]
            if frozenset((ti.get_text(), tj.get_text())) in ign:
                continue
            ox = min(bi.x1, bj.x1) - max(bi.x0, bj.x0)
            oy = min(bi.y1, bj.y1) - max(bi.y0, bj.y0)
            if ox > tol_px and oy > tol_px:
                problems.append(f"overlap: {ti.get_text()!r} x {tj.get_text()!r}")
    return problems, [t.get_text() for t, _ in texts]


# --------------------------------------------------------------------------------------------------- writers
def _render_rgb(fig, dpi):
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    buf.seek(0)
    im = Image.open(buf)
    im.load()
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
        im = bg
    return im


def _preview(im, dpi, path: Path):
    """Reduced PNG <= 2 MB: Lanczos down-scaling to ~300 / 250 / 200 / 150 dpi-equivalent, palette as a last resort."""
    from PIL import Image
    im2, target = im, dpi
    for target in (300, 250, 200, 150, 120):
        s = target / float(dpi)
        im2 = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        im2.save(path, format="PNG", optimize=True, dpi=(target, target))
        if path.stat().st_size <= PREVIEW_MAX_BYTES:
            return im2.size, target
    im3 = im2.convert("P", palette=Image.ADAPTIVE, colors=256)
    im3.save(path, format="PNG", optimize=True, dpi=(target, target))
    if path.stat().st_size > PREVIEW_MAX_BYTES:
        raise RuntimeError(f"preview {path} still > 2 MB")
    return im3.size, target


def portable(s) -> str:
    """A recorded path without the account: the home directory becomes '~', a conda installation '<conda>'."""
    import re as _re
    s = str(s).replace("\\", "/")
    home = str(Path.home()).replace("\\", "/")
    s = _re.sub(r"^.*?/anaconda3(?=/)", "<conda>", s) if "/anaconda3/" in s else s
    return s.replace(home, "~")


def export(fig, name: str, *, dpi: int, width_mm: float, script: str, sources: list, notes: str = "",
           column: str = "two-column", check=True, ignore_overlap_pairs=(), extra_texts=(), tiff_writer: str = "pil"):
    """Render once, check the canvas against the export spec, write <name>.tiff + <name>_preview.png + meta/<name>.json.

    tiff_writer "pil" (Pillow/libtiff LZW) or "tifffile" (tifffile + imagecodecs LZW): the cartopy env's Pillow 10.0.1 /
    libtiff 4.5.0 crashes natively on LZW writes, so F1 uses tifffile; both give an RGB 8-bit, LZW, dpi-tagged TIFF."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    w_in, h_in = fig.get_size_inches()
    if abs(w_in / MM - width_mm) > 0.01:
        raise ValueError(f"{name}: figure width {w_in / MM:.2f} mm != {width_mm} mm")
    height_mm = h_in / MM
    if height_mm > MAX_HEIGHT_MM + 1e-6:
        raise ValueError(f"{name}: height {height_mm:.1f} mm > {MAX_HEIGHT_MM} mm")
    problems, drawn = layout_report(fig, ignore_overlap_pairs=ignore_overlap_pairs, extra_texts=extra_texts, dpi=dpi) if check else ([], [])
    for p in problems:
        print(f"  [layout] {name}: {p}")
    if problems and check == "strict":
        raise RuntimeError(f"{name}: {len(problems)} layout problem(s)")
    im = _render_rgb(fig, dpi)
    exp_w, exp_h = width_mm * MM * dpi, height_mm * MM * dpi
    if abs(im.width - exp_w) > 1.0 or abs(im.height - exp_h) > 1.0:
        raise RuntimeError(f"{name}: rendered {im.width}x{im.height} px, expected {exp_w:.1f}x{exp_h:.1f} px")
    tif = FIG_DIR / f"{name}.tiff"
    if tiff_writer == "tifffile":
        import numpy as np
        import tifffile
        tifffile.imwrite(tif, np.asarray(im), photometric="rgb", compression="lzw", resolution=(dpi, dpi), resolutionunit="INCH")
    else:
        im.save(tif, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    t_tif = utc_now()
    png = FIG_DIR / f"{name}_preview.png"
    psize, pdpi = _preview(im, dpi, png)
    t_png = utc_now()
    meta = {"figure": name, "column": column, "script": script, "sources": [portable(rel(s) if isinstance(s, Path) else s) for s in sources],
            "notes": notes, "layout_problems": problems, "texts_drawn": sorted(set(drawn)),
            "files": [{"file": tif.name, "px": [im.width, im.height], "dpi": dpi, "width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2),
                       "format": "TIFF, RGB 8-bit, LZW", "tiff_writer": tiff_writer, "bytes": tif.stat().st_size, "generated_utc": t_tif},
                      {"file": png.name, "px": list(psize), "dpi": pdpi, "width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2),
                       "format": "PNG preview (reduced)", "bytes": png.stat().st_size, "generated_utc": t_png}]}
    (META_DIR / f"{name}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {tif.name} {im.width}x{im.height} px @ {dpi} dpi ({width_mm:g} x {height_mm:.1f} mm, {tif.stat().st_size / 1e6:.1f} MB); "
          f"{png.name} {psize[0]}x{psize[1]} ({png.stat().st_size / 1e6:.2f} MB); layout problems: {len(problems)}")
    return meta
