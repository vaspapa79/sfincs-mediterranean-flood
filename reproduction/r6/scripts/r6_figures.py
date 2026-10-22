"""R6 figure export (MESE close-out, part C) - F3-F11 and the F1 input data, re-rendered at the export size.

Post-processing only: reads the frozen v1.4.x records (reproduction/v14_rerun/{configs,results,masks,phase4,phase5}) and the
model outputs (D:/ELKAK/implementation/v14/<run>/model/sfincs_map.nc); writes only under reproduction/r6/figures/.
No SFINCS / pipeline step is run; no existing script, record or figure is modified (the phase-4 truth-raster cache is read
only; rasters it does not hold are cached under r6/figures/_cache).

  F1data  model-domain boxes + EMS AOI centroids of the six canonical runs -> figures/data/F1_inputs.json
          (drawn by r6_fig1_overview.py in the cartopy env)
  F3 F5 F6 F7 F8  maximum-inundation maps, content of phase4/figures/map_<run>_v14.png (fig_map_v14.py): h_max > 0.10 m by
          depth, EMS observed flood (red), EMS AOIs (dashed), cells excluded from the evaluation universe (grey); no score printed
  F4      Pineios / Mandra domain-mean rainfall, ERA5 / raw IMERG / bias-corrected IMERG, in the design of the R5 figures
          (manuscript/paper_submission_v5/_make_{pineios,mandra}_rain.py), data = phase4/rain/<run>_v14{.json,_series.csv};
          every total / peak / watershed-box value printed is read from the rain JSON and asserted against the series CSV,
          the configuration and the IMERG files (the run fails otherwise)
  F9      Crete (crete_canonical_r2on): (a) island overview, (b) AOI03 Tzermiado zoom (tier 1, rule_ledger.md section 8 item 3);
          no metric printed, no all-AOI union score computed
  F10 F11 cross-event skill / sweeps, content of fig_skill_sweeps_v14.py (--in-tag _v142 --pineios-run pineios_enhanced_v142),
          run of record only (CODE-17 A1/A2: release history is reported in the tables, not in the main-text figures)

Usage (sfincs-viz env):  python -I r6_figures.py [--fig all | --fig F3 --fig F9 ...]
then (cartopy env):       python -I r6_fig1_overview.py ;  and  python -I r6_fig_manifest.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r6_fig_common as C  # noqa: E402

REPO = C.REPO
V14 = REPO / "reproduction" / "v14_rerun"
CFG_DIR, RES, MASKS, P4, P5 = V14 / "configs", V14 / "results", V14 / "masks", V14 / "phase4", V14 / "phase5"
P4_CACHE = P4 / "time_matched" / "_cache"            # phase-4 truth rasters (read only)
SCRIPT = C.rel(Path(__file__))

# canonical runs of record (close-out brief, 2026-10-21), in manuscript order
RUNS = {"pineios": "pineios_enhanced_v142", "mandra": "mandra_enhanced", "strymonas": "strymonas_enhanced_postD6_v142",
        "valencia": "valencia_enhanced_164_v142", "emilia": "emilia_enhanced_8aoi_v142", "crete": "crete_canonical_r2on"}
ORDER = ["pineios", "mandra", "strymonas", "valencia", "emilia", "crete"]
MAP_FIGS = {"F3": "pineios", "F5": "mandra", "F6": "strymonas", "F7": "valencia", "F8": "emilia"}
AOI_PATTERNS = ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"]     # as fig_map_v14.py
THRESHOLD = 0.10                                     # scoring depth threshold (m); record key "h>0.10m"
DEPTH_CAP = 3.0                                      # colour-scale cap (m), as fig_map_v14.py
DEPTH_COLOURS = ["#cfe3f7", "#4a90d9", "#08306b"]    # as fig_map_v14.py
BASE_GREY, EXCL_GREY = "#ebebeb", "#999999"          # grey 0.92 (active) / 0.6 (removed by the mask), as fig_map_v14.py
OBS_RED = "red"
# the scripts that drew the R5 rainfall figures (pineios_rain_timeseries.png / mandra_rain_timeseries.png, byte-identical in
# ELKAK2/NHESS/); their design is kept for F4
R5_RAIN_SCRIPTS = [Path("D:/ELKAK/manuscript/paper_submission_v5/_make_pineios_rain.py"),
                   Path("D:/ELKAK/manuscript/paper_submission_v5/_make_mandra_rain.py")]
HMAX = r"$\it{h}_{\rm max}$"


def thr_key(t: float = THRESHOLD) -> str:
    return f"h>{t:.2f}m"


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def setup_env():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    prefix = Path(sys.executable).resolve().parent
    for var, sub in (("GDAL_DATA", ("Library", "share", "gdal")), ("PROJ_LIB", ("Library", "share", "proj"))):
        p = prefix.joinpath(*sub)
        if not os.environ.get(var) and p.exists():
            os.environ[var] = str(p)
    if os.environ.get("PROJ_LIB") and not os.environ.get("PROJ_DATA"):
        os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"]
    for p in (V14 / "scripts", REPO / "validation", REPO / "skill" / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def mpl_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C.apply_style(matplotlib)
    return matplotlib, plt


def jload(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_cfg(run):
    from _common import load_config
    p = CFG_DIR / f"{run}.yaml"
    return load_config(["--config", str(p)]), p


def utm_label(epsg: int) -> str:
    import pyproj
    z = pyproj.CRS.from_epsg(epsg).utm_zone
    return f"UTM {z}" if z else pyproj.CRS.from_epsg(epsg).name


# =================================================================================================== model fields
def truth_raster(cfg, s, shps, tag):
    """EMS polygons rasterised on the model grid exactly as the validator does; the phase-4 cache is reused read-only."""
    import numpy as np
    import validate_event_v2 as V
    from truth_cache import cache_key, cached_bool
    key = cache_key(cfg.event_slug, s, shps, tag)
    p4 = P4_CACHE / f"{key}.npz"
    if p4.exists():
        with np.load(p4) as z:
            return np.unpackbits(z["bits"])[: int(z["n"])].reshape(tuple(z["shape"])).astype(bool)
    return cached_bool(C.CACHE_DIR, key, lambda: V._rasterise_polys_to_grid(list(shps), s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))


def load_run(event):
    import numpy as np
    import validate_event_v2 as V
    from eval_exclusion import read_mask_for_grid
    run = RUNS[event]
    cfg, cfg_path = load_cfg(run)
    rec = jload(RES / f"{run}_record.json")
    need(rec["event"] == event and rec["run"] == run, f"{run}: record event/run mismatch")
    model_nc = cfg.paths["model_dir"] / "sfincs_map.nc"
    s = V.open_sfincs_light(cfg.paths["model_dir"])
    excl_tif = MASKS / f"{rec['event']}_exclusion.tif"
    excl = read_mask_for_grid(excl_tif, s)
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aois = V._list_shps(ems_dir, AOI_PATTERNS)
    ems_wet = truth_raster(cfg, s, obs, "truth_union")
    aoi_m = truth_raster(cfg, s, aois, "aoi_all") if aois else np.ones_like(ems_wet)
    active = s["msk"] > 0
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    s["ds"].close()
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    wet = (hmax > THRESHOLD) & active
    x, y = s["x"], s["y"]
    need(y[1, 0] > y[0, 0], f"{run}: expected y ascending in sfincs_map.nc")
    ext = [x.min() / 1e3 - s["dx"] / 2e3, x.max() / 1e3 + s["dx"] / 2e3, y.min() / 1e3 - s["dy"] / 2e3, y.max() / 1e3 + s["dy"] / 2e3]
    return SimpleNamespace(event=event, run=run, cfg=cfg, cfg_path=cfg_path, rec=rec, s=s, excl=excl, excl_tif=excl_tif, obs=obs,
                           aois=aois, ems_wet=ems_wet, aoi_m=aoi_m, active=active, hmax=hmax, wet=wet, ext=ext, model_nc=model_nc,
                           ems_dir=ems_dir)


def check_union_vs_record(F):
    """The map shows exactly the scored fields: the strict contingency on the v1.4 universe equals the record."""
    import validate_event_v2 as V
    universe = F.active & F.aoi_m & ~F.excl
    c = V._contingency_full(F.wet, F.ems_wet, universe)
    src = RES / f"{F.run}_v14_newmask.json"
    ref = jload(src)["validation"]["strict_threshold_sweep"][thr_key()]
    for k in ("tp", "fp", "fn", "tn"):
        if k in ref:
            need(int(c[k]) == int(ref[k]), f"{F.run}: {k} {c[k]} != record {ref[k]} ({C.rel(src)})")
    print(f"  {F.run}: map fields reproduce the record contingency (tp {c['tp']} fp {c['fp']} fn {c['fn']}) of {C.rel(src)}")
    return src


def draw_layers(ax, F, aoi_layers=None, lw_obs=0.5):
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    kw = dict(extent=F.ext, origin="lower", interpolation="nearest")
    ax.imshow(np.where(F.active, 1.0, np.nan), cmap=ListedColormap([BASE_GREY]), vmin=0, vmax=1, **kw)
    ax.imshow(np.where(F.excl & F.active, 1.0, np.nan), cmap=ListedColormap([EXCL_GREY]), vmin=0, vmax=1, **kw)
    cmap = LinearSegmentedColormap.from_list("depth", DEPTH_COLOURS)
    im = ax.imshow(np.where(F.wet, np.minimum(F.hmax, DEPTH_CAP), np.nan), cmap=cmap, vmin=0, vmax=DEPTH_CAP, **kw)
    ax.contour(F.ems_wet.astype(float), levels=[0.5], extent=F.ext, origin="lower", colors=OBS_RED, linewidths=lw_obs)
    for arr, style in (aoi_layers if aoi_layers is not None else [(F.aoi_m, dict(colors="k", linewidths=0.7, linestyles="dashed"))]):
        ax.contour(arr.astype(float), levels=[0.5], extent=F.ext, origin="lower", **style)
    return im


EXCL_LABEL = "excluded from the evaluation universe (permanent water, open sea)"   # CODE-17 A4 wording


def map_legend_handles(aoi_handles=None, two_line_excl=False):
    """Legend entries of the maps; two_line_excl breaks the exclusion entry for a single-column legend (F9)."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    excl = EXCL_LABEL.replace(" (", "\n(") if two_line_excl else EXCL_LABEL
    h = [Patch(facecolor=BASE_GREY, edgecolor="0.55", linewidth=0.4, label=f"active cell, {HMAX} ≤ {THRESHOLD:.2f} m"),
         Patch(facecolor=EXCL_GREY, edgecolor="none", label=excl),
         Line2D([], [], color=OBS_RED, lw=0.9, label="EMS observed flood")]
    h += aoi_handles if aoi_handles is not None else [Line2D([], [], color="k", lw=0.8, ls="--", label="EMS areas of interest")]
    return h


def depth_colorbar(fig, im, cax):
    cb = fig.colorbar(im, cax=cax, extend="max")
    cb.set_label(f"Maximum depth {HMAX} (m)")
    cb.ax.tick_params(labelsize=8, width=0.6, length=2.5)
    cb.outline.set_linewidth(0.6)
    return cb


def fig_map(name, event):
    matplotlib, plt = mpl_setup()
    F = load_run(event)
    rec_json = check_union_vs_record(F)
    ex = F.ext
    xw, yh = ex[1] - ex[0], ex[3] - ex[2]
    W = C.WIDTH_2COL_MM
    L, RM, T, B = 15.0, 24.0, 3.0, 22.0             # left (y labels), right (colour bar), top, bottom (x labels + legend)
    MW = W - L - RM
    MH = MW * yh / xw
    H = T + MH + B
    fig = C.fig_mm(plt, W, H)
    ax = C.ax_mm(fig, L, B, MW, MH)
    im = draw_layers(ax, F)
    ax.set_xlim(ex[0], ex[1]); ax.set_ylim(ex[2], ex[3]); ax.set_aspect("equal")
    utm = utm_label(F.cfg.epsg)
    ax.set_xlabel(f"Easting (km, {utm})"); ax.set_ylabel(f"Northing (km, {utm})")
    cbh = min(MH * 0.7, 80.0)
    depth_colorbar(fig, im, C.ax_mm(fig, L + MW + 3.0, B + (MH - cbh) / 2, 3.0, cbh))
    fig.legend(handles=map_legend_handles(), loc="lower left", bbox_to_anchor=(L / W, 1.5 / H), ncol=2, frameon=False,
               borderaxespad=0.0, handlelength=2.2)
    sources = [F.cfg_path, F.model_nc, F.excl_tif, F.ems_dir, rec_json]
    C.export(fig, name, dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT, sources=sources,
             notes=f"run {F.run}; content of phase4/figures/map_{F.run}_v14.png (fig_map_v14.py) re-rendered at the export size; "
                   f"no score printed")
    plt.close(fig)


# =================================================================================================== F9 Crete
SNAPSHOT = REPO / "reproduction" / "emsr933" / "ems_api_snapshot_20261019T133437Z.json"   # EMS API snapshot used for the truth freeze


def crete_tier3(tiers):
    """Tier-3 AOIs (no product released): the codes from the tiers-JSON rule, names + extents (WKT, EPSG:4326) from the
    EMS API snapshot - these AOIs have no shapefile in the run's ems_polygons."""
    from shapely import wkt
    m = re.search(r"tier 3 excluded \(([\d/]+)\)", tiers["rule"])
    need(m is not None, "tiers JSON rule does not list the tier-3 AOIs")
    codes = m.group(1).split("/")
    need(not set(codes) & set(tiers["aois"]), "a tier-3 AOI carries a tier-1/2 record")
    snap = jload(SNAPSHOT)["results"][0]
    need(snap["code"] == "EMSR933", "the snapshot is not EMSR933")
    out = {}
    for a in snap["aois"]:
        k = f"{int(a['number']):02d}"
        if k in codes:
            out[k] = (a["name"], wkt.loads(a["extent"]))
    need(sorted(out) == sorted(codes), f"tier-3 AOIs {codes} not all in the snapshot")
    return out


def _boxes_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]


def place_labels(fig, ax, items, obstacles, pad=0.8, offsets=(1.0, 2.5, 4.0, 6.0, 8.5),
                 sides=("N", "S", "W", "E", "NE", "NW", "SE", "SW")):
    """Place each (text, box=(x0,x1,y0,y1)) label outside every obstacle rectangle (AOI boxes, the panel-(b) frame) and every
    label already placed, inside the axes; data units. Raises if no position is free."""
    import matplotlib.patheffects as pe
    r = fig.canvas.get_renderer()
    ax.apply_aspect()
    inv = ax.transData.inverted()
    (X0, X1), (Y0, Y1) = ax.get_xlim(), ax.get_ylim()
    placed, texts = [], []
    for text, (bx0, bx1, by0, by1) in items:
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        done = False
        for off in offsets:
            for side in sides:
                pos = {"N": (cx, by1 + off, "center", "bottom"), "S": (cx, by0 - off, "center", "top"),
                       "W": (bx0 - off, cy, "right", "center"), "E": (bx1 + off, cy, "left", "center"),
                       "NE": (bx1 + off, by1 + off, "left", "bottom"), "NW": (bx0 - off, by1 + off, "right", "bottom"),
                       "SE": (bx1 + off, by0 - off, "left", "top"), "SW": (bx0 - off, by0 - off, "right", "top")}[side]
                t = ax.text(pos[0], pos[1], text, ha=pos[2], va=pos[3], fontsize=8, zorder=7)
                bb = t.get_window_extent(renderer=r)
                (dx0, dy0), (dx1, dy1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
                rect = (dx0 - pad, dx1 + pad, dy0 - pad, dy1 + pad)
                inside = X0 < rect[0] and rect[1] < X1 and Y0 < rect[2] and rect[3] < Y1
                if inside and not any(_boxes_overlap(rect, o) for o in obstacles + placed):
                    t.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])
                    placed.append(rect)
                    texts.append(t)
                    done = True
                    break
                t.remove()
            if done:
                break
        need(done, f"no free position for the label {text!r}")
    return texts


def fig9(name="F9"):
    import numpy as np
    import pyproj
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from shapely.ops import transform as shp_transform
    import validate_event_v2 as V
    matplotlib, plt = mpl_setup()
    F = load_run("crete")
    tiers_path = P5 / f"{F.run}_tiers.json"
    tiers = jload(tiers_path)
    need("no union score" in tiers.get("rule", ""), "Crete tiers JSON does not carry the no-union rule")
    t1 = sorted(k for k, v in tiers["aois"].items() if v.get("tier") == 1)
    need(t1 == ["03"], f"Crete tier-1 AOIs {t1} != ['03']")
    # tier-1/2 AOI groups (by AOI number) of the run's AOI shapefiles; tier-3 extents from the EMS API snapshot
    groups = {}
    for p in F.aois:
        m = re.search(r"AOI(\d\d)", p.name)
        groups.setdefault(m.group(1), []).append(p)
    need(set(groups) == set(tiers["aois"]), f"AOI groups {sorted(groups)} != tiers JSON AOIs {sorted(tiers['aois'])}")
    rasters = {k: truth_raster(F.cfg, F.s, v, f"r6_aoi_group_{k}") for k, v in groups.items()}
    to_utm = pyproj.Transformer.from_crs(4326, F.cfg.epsg, always_xy=True).transform

    def to_km(a_, b_):
        X, Y = to_utm(a_, b_)
        return np.asarray(X) / 1e3, np.asarray(Y) / 1e3
    t3 = {k: (nm, shp_transform(to_km, poly)) for k, (nm, poly) in crete_tier3(tiers).items()}
    # tier-1 cross-check: AOI03 universe / own truth / contingency = tiers JSON (the only Crete score; not printed)
    r03 = tiers["aois"]["03"]
    need(sorted(p.name for p in groups["03"]) == sorted(r03["aoi_files"]), "AOI03 AOI files differ from the tiers JSON")
    obs03 = [p for p in F.obs if p.name in r03["obs_files"]]
    need(len(obs03) == len(r03["obs_files"]), "AOI03 observed files differ from the tiers JSON")
    truth03 = truth_raster(F.cfg, F.s, obs03, "r6_truth_aoi03")
    uni03 = F.active & ~F.excl & rasters["03"]
    c = V._contingency_full(F.hmax > THRESHOLD, truth03, uni03)
    ref = r03["strict_threshold_sweep"][thr_key()]
    for k in ("tp", "fp", "fn", "tn"):
        need(int(c[k]) == int(ref[k]), f"Crete AOI03 {k} {c[k]} != tiers JSON {ref[k]}")
    need(abs(uni03.sum() * F.s["cell_area_km2"] - r03["universe_km2"]) < 0.01, "AOI03 universe km2 mismatch")
    t3_txt = ", ".join(f"AOI{k} {v[0]}" for k, v in sorted(t3.items()))
    print(f"  crete: AOI03 (tier 1) fields reproduce {C.rel(tiers_path)} (tp {c['tp']} fp {c['fp']} fn {c['fn']}); no union computed; "
          f"tier 3 from the snapshot: {t3_txt}")

    x, y = F.s["x"][0, :] / 1e3, F.s["y"][:, 0] / 1e3
    hx, hy = F.s["dx"] / 2e3, F.s["dy"] / 2e3
    iy = np.where(F.active.any(axis=1))[0]
    ix = np.where(F.active.any(axis=0))[0]
    pad = 2.0
    ov = [x[ix[0]] - pad, x[ix[-1]] + pad, y[iy[0]] - pad, y[iy[-1]] + pad]          # active extent + 2 km
    box = {}
    for k, ras in rasters.items():
        gy, gx = np.where(ras)
        box[k] = (x[gx.min()] - hx, x[gx.max()] + hx, y[gy.min()] - hy, y[gy.max()] + hy)
    for k, (_, poly) in t3.items():
        b = poly.bounds
        box[k] = (b[0], b[2], b[1], b[3])
    zb = [box["03"][0] - 1.0, box["03"][1] + 1.0, box["03"][2] - 2.0, box["03"][3] + 2.0]   # AOI03 + 1 km (E-W) / 2 km (N-S)
    W = C.WIDTH_2COL_MM
    L, RA = 15.0, 3.0
    AW = W - L - RA
    AH = AW * (ov[3] - ov[2]) / (ov[1] - ov[0])
    BW = 86.0
    BH = BW * (zb[3] - zb[2]) / (zb[1] - zb[0])
    T, GAP, B = 6.0, 17.0, 11.0
    H = T + AH + GAP + BH + B
    fig = C.fig_mm(plt, W, H)
    axA = C.ax_mm(fig, L, B + BH + GAP, AW, AH)
    axB = C.ax_mm(fig, L, B, BW, BH)
    styles = {1: dict(colors="k", linewidths=1.0, linestyles="solid"), 2: dict(colors="k", linewidths=0.7, linestyles="dashed")}
    layers = [(rasters[k], styles[tiers["aois"][k]["tier"]]) for k in sorted(rasters)]
    t3_style = dict(color="0.35", lw=0.9, ls=(0, (1.0, 1.4)))
    utm = utm_label(F.cfg.epsg)
    for ax, e, lw_obs in ((axA, ov, 0.5), (axB, zb, 0.7)):
        im = draw_layers(ax, F, aoi_layers=layers, lw_obs=lw_obs)
        for _, poly in t3.values():
            xs, ys = poly.exterior.xy
            ax.plot(xs, ys, zorder=5, **t3_style)
        ax.set_xlim(e[0], e[1])
        ax.set_ylim(e[2], e[3])
        ax.set_aspect("equal")
        ax.set_xlabel(f"Easting (km, {utm})")
        ax.set_ylabel(f"Northing (km, {utm})")
    C.panel_letter(axA, "a", text="Crete, island overview: all eight EMS areas of interest")
    C.panel_letter(axB, "b", text=f"AOI03 {r03['name']} (tier 1)")
    axA.add_patch(Rectangle((zb[0], zb[2]), zb[1] - zb[0], zb[3] - zb[2], fill=False, ec=C.OI["blue"], lw=0.9, zorder=6))
    # short AOI labels, each clear of every AOI box and of the panel-(b) frame
    obstacles = [tuple(b) for b in box.values()] + [tuple(zb)]
    # AOI03 lies inside the panel-(b) frame: its label is anchored on that frame so it stays next to AOI03
    place_labels(fig, axA, [(f"AOI{k}", tuple(zb) if k == "03" else box[k]) for k in sorted(box)], obstacles)
    # colour bar, AOI key (number, name, tier) and legend beside (b)
    cx = L + BW + 7.0
    cbh = 28.0
    depth_colorbar(fig, im, C.ax_mm(fig, cx, B + BH - cbh, 3.0, cbh))
    names = {k: v["name"] for k, v in tiers["aois"].items()}
    names.update({k: v[0] for k, v in t3.items()})
    tier = {k: v["tier"] for k, v in tiers["aois"].items()}
    tier.update({k: 3 for k in t3})
    key = "\n".join(f"AOI{k}  {names[k]} (tier {tier[k]})" for k in sorted(names))
    fig.text((cx + 16.0) / W, (B + BH) / H, key, ha="left", va="top", fontsize=8, linespacing=1.25)
    aoi_h = [Line2D([], [], color="k", lw=1.0, ls="-", label="EMS AOI, tier 1 (scored)"),
             Line2D([], [], color="k", lw=0.8, ls="--", label="EMS AOI, tier 2 (area only)"),
             Line2D([], [], label="EMS AOI, tier 3 (no product released)", **t3_style),
             Line2D([], [], color=C.OI["blue"], lw=0.9, label="extent of panel (b)")]
    fig.legend(handles=map_legend_handles(aoi_h, two_line_excl=True), loc="lower left", bbox_to_anchor=(cx / W, B / H), ncol=1, frameon=False,
               borderaxespad=0.0, handlelength=2.2)
    sources = [F.cfg_path, F.model_nc, F.excl_tif, F.ems_dir, tiers_path, SNAPSHOT]
    C.export(fig, name, dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT, sources=sources,
             notes=f"run {F.run}; (a) island overview with all eight EMSR933 AOIs, (b) AOI03 Tzermiado zoom; tier 1 (AOI03) solid, "
                   f"tier 2 dashed, tier 3 (no product released; extents from the EMS API snapshot) grey dotted; AOI labels placed "
                   f"clear of every box line; tier-1 contingency asserted against the tiers JSON; no metric printed, no all-AOI "
                   f"union score computed")
    plt.close(fig)


# =================================================================================================== F4 rainfall
def _read_precip(nc_path: Path):
    """(rate DataArray with datetime64 time, step_h, grid spacing deg) of an IMERG / ERA5 file of the pipeline."""
    import netCDF4
    import numpy as np
    import xarray as xr
    ds = xr.open_dataset(nc_path, decode_times=False)
    if "valid_time" in ds.coords and "time" not in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    t = ds["time"]
    dates = netCDF4.num2date(t.values, t.attrs.get("units", "hours since 1970-01-01"), calendar=t.attrs.get("calendar", "standard"),
                             only_use_cftime_datetimes=True)
    ds = ds.assign_coords(time=np.array([np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:{d.second:02d}")
                                         for d in dates], dtype="datetime64[ns]"))
    v = "precip" if "precip" in ds else list(ds.data_vars)[0]
    da = ds[v]
    tt = da["time"].values
    step_h = float(np.median(np.diff(tt).astype("timedelta64[s]").astype(float)) / 3600.0)
    res = float(np.median(np.abs(np.diff(da["latitude"].values))))
    return ds, da, step_h, res, dict(ds.attrs)


def _box_total(da, step_h, box, t0, t1):
    """Mean over the cells whose centre lies in box (W,S,E,N) of sum(rate x step) for t0 <= t < t1 (NaN = 0)."""
    import numpy as np
    w, s, e, n = box
    lat, lon = da["latitude"].values, da["longitude"].values
    sub = da.isel(latitude=np.where((lat >= s) & (lat <= n))[0], longitude=np.where((lon >= w) & (lon <= e))[0])
    tt = sub["time"].values
    sel = (tt >= np.datetime64(t0)) & (tt < np.datetime64(t1))
    tot = sub.isel(time=np.where(sel)[0]).fillna(0.0).sum(dim="time") * step_h
    return float(tot.mean())


def rain_checked(run):
    """Every number F4 prints comes from the rain JSON; each is asserted against the series CSV, the config and the files."""
    import numpy as np
    import pandas as pd
    rj_path, csv_path = P4 / "rain" / f"{run}_v14.json", P4 / "rain" / f"{run}_v14_series.csv"
    rj = jload(rj_path)
    cfg, cfg_path = load_cfg(run)
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    bc = cfg.rain_bias_correct
    src = rj["sources"]
    # (1) watershed box, anchor and event window: configuration = JSON (r2 block, both IMERG records)
    wb_cfg = [float(v) for v in str(bc["watershed_bbox"]).split(",")]
    wb_r2 = [float(v) for v in str(rj["r2"]["watershed_bbox"]).split(",")]
    wb_raw = [float(v) for v in src["imerg_raw"]["watershed_event_window"]["watershed_bbox"]]
    wb_cor = [float(v) for v in src["imerg"]["watershed_event_window"]["watershed_bbox"]]
    need(wb_cfg == wb_r2 == wb_raw == wb_cor, f"{run}: watershed bbox config {wb_cfg} / JSON {wb_r2} {wb_raw} {wb_cor} differ")
    need(float(bc["target_mm"]) == float(rj["r2"]["target_mm"]) == float(rj["r2_realised"]["target_mm"]), f"{run}: target_mm differs")
    ev0, ev1 = (pd.Timestamp(v) for v in rj["windows"]["event"])
    need(ev0 == pd.Timestamp(bc["event_start"]) and ev1 == pd.Timestamp(bc["event_end"]) + pd.Timedelta(minutes=30),
         f"{run}: event window {ev0}..{ev1} != config {bc['event_start']}..{bc['event_end']} + 30 min")
    f0, f1 = (pd.Timestamp(v) for v in rj["windows"]["forcing"])
    need(f0 == pd.Timestamp(cfg.tref) and f1 == pd.Timestamp(cfg.tstop), f"{run}: forcing window != config tref..tstop")
    # (2) the realised R2 numbers are internally consistent in the JSON
    raw_ws = src["imerg_raw"]["watershed_event_window"]["domain_mean_total_mm"]
    cor_ws = src["imerg"]["watershed_event_window"]["domain_mean_total_mm"]
    rr = rj["r2_realised"]
    need(raw_ws == rr["raw_watershed_mean_mm"] and cor_ws == rr["corrected_watershed_mean_mm"], f"{run}: r2_realised != watershed records")
    need(math.isclose(rr["factor"], cor_ws / raw_ws, rel_tol=1e-12), f"{run}: factor != corrected / raw")
    need(abs(cor_ws - rr["target_mm"]) < 0.01, f"{run}: corrected watershed mean {cor_ws} != target {rr['target_mm']}")
    # (3) the watershed-box values recomputed from the IMERG files equal the JSON values
    info = {}
    for key in ("imerg_raw", "imerg", "era5"):
        ds, da, step_h, res, attrs = _read_precip(Path(src[key]["file"]))
        need(math.isclose(step_h, src[key]["by_window"]["forcing"]["step_h"]), f"{run}: {key} step {step_h} != JSON")
        info[key] = {"step_h": step_h, "res_deg": res, "attrs": attrs}
        if key != "era5":
            v = _box_total(da, step_h, wb_cfg, ev0.to_datetime64(), ev1.to_datetime64())
            ref = src[key]["watershed_event_window"]["domain_mean_total_mm"]
            need(abs(v - ref) < 1e-3, f"{run}: {key} watershed-box total recomputed {v:.4f} != JSON {ref:.4f}")
        ds.close()
    m = re.search(r"([\d.]+)x applied to event window (.+?) to (.+?) so watershed bbox \(([-\d.,]+)\)", info["imerg"]["attrs"].get("bias_correction", ""))
    need(m is not None, f"{run}: no bias_correction attribute in the corrected IMERG file")
    need(abs(float(m.group(1)) - rr["factor"]) < 5e-4, f"{run}: file factor {m.group(1)} != JSON factor {rr['factor']:.4f}")
    need([float(v) for v in m.group(4).split(",")] == wb_cfg, f"{run}: file watershed bbox {m.group(4)} != {wb_cfg}")
    need(pd.Timestamp(m.group(2)) == ev0 and pd.Timestamp(m.group(3)) == pd.Timestamp(bc["event_end"]), f"{run}: file window differs")
    # (4) the plotted series (forcing window) integrate / peak to the JSON totals and peaks printed in the legend
    series, totals = {}, {}
    for key in ("era5", "imerg", "imerg_raw"):
        sr = df[key].dropna()
        sr = sr[(sr.index >= f0) & (sr.index < f1)]
        bw = src[key]["by_window"]["forcing"]
        tot, pk = float(sr.sum() * bw["step_h"]), float(sr.max())
        need(len(sr) == bw["n_steps"], f"{run}: {key} {len(sr)} series steps != JSON n_steps {bw['n_steps']}")
        need(abs(tot - bw["domain_mean_total_mm"]) < 0.05, f"{run}: {key} series total {tot:.3f} != JSON {bw['domain_mean_total_mm']:.3f}")
        need(abs(pk - bw["domain_mean_peak_mm_h"]) < 1e-3, f"{run}: {key} series peak {pk:.4f} != JSON {bw['domain_mean_peak_mm_h']:.4f}")
        series[key] = sr
        totals[key] = (bw["domain_mean_total_mm"], bw["domain_mean_peak_mm_h"])
    print(f"  {run}: rain JSON values asserted (config, IMERG files, series CSV): watershed raw {raw_ws:.1f} -> {cor_ws:.1f} mm, "
          f"factor {rr['factor']:.3f}")
    return SimpleNamespace(run=run, cfg=cfg, cfg_path=cfg_path, rj=rj, rj_path=rj_path, csv_path=csv_path, series=series, totals=totals,
                           raw_ws=raw_ws, cor_ws=cor_ws, factor=rr["factor"], ev=(ev0, ev1), forcing=(f0, f1), info=info,
                           files=[Path(src[k]["file"]) for k in ("imerg_raw", "imerg", "era5")])


def _step_text(step_h):
    return "hourly" if math.isclose(step_h, 1.0) else f"{step_h * 60:.0f}-min"


def fig4(name="F4"):
    import matplotlib.dates as mdates
    import pandas as pd
    from matplotlib.patches import Patch
    matplotlib, plt = mpl_setup()
    W = C.WIDTH_2COL_MM
    # per panel, from the bottom: legend block (LEG, outside the plot area), tick labels + x label (XL), the axes (PH); the panel
    # letter sits in the GAP above each axes. The legend no longer overlaps the shaded R2 window (CODE-17 figure check).
    L, RM, T, PH, XL, LEG, GAP, B = 14.0, 8.0, 6.0, 54.0, 9.0, 20.0, 9.0, 2.0
    BLOCK = PH + XL + LEG
    H = T + BLOCK + GAP + BLOCK + B
    fig = C.fig_mm(plt, W, H)
    style = {"era5": ("ERA5", "#dc2626", "-", 1.0), "imerg": ("bias-corrected IMERG", "#1d4ed8", "-", 0.8),
             "imerg_raw": ("raw IMERG", "#60a5fa", "--", 0.8)}        # R5 design (_make_pineios_rain.py / _make_mandra_rain.py)
    sources = []
    for i, (letter, event) in enumerate((("a", "pineios"), ("b", "mandra"))):
        Rn = rain_checked(RUNS[event])
        bottom = B + (1 - i) * (BLOCK + GAP) + XL + LEG
        ax = C.ax_mm(fig, L, bottom, W - L - RM, PH)
        ax.axvspan(*Rn.ev, color="#fde8cf", lw=0, zorder=0)
        for key in ("era5", "imerg", "imerg_raw"):
            lab, col, ls, lw = style[key]
            tot, pk = Rn.totals[key]
            inf = Rn.info[key]
            sr = Rn.series[key]
            ax.plot(sr.index, sr.values, ls, color=col, lw=lw, zorder=3,
                    label=f"{lab} ({_step_text(inf['step_h'])}, {inf['res_deg']:.2g}°): total {tot:.1f} mm, peak {pk:.2f} mm h$^{{-1}}$")
        h, l = ax.get_legend_handles_labels()
        h.append(Patch(facecolor="#fde8cf", edgecolor="none"))
        l.append(f"R2 window: watershed-box mean {Rn.raw_ws:.1f} → {Rn.cor_ws:.1f} mm (×{Rn.factor:.2f})")
        fig.legend(h, l, loc="upper left", bbox_to_anchor=(L / W, (bottom - XL) / H), ncol=1, frameon=False, borderaxespad=0.0,
                   handlelength=2.2)
        ymax = max(v[1] for v in Rn.totals.values())
        ax.set_ylim(-0.02 * ymax, 1.12 * ymax)
        pad = pd.Timedelta(hours=6)                               # the axis ends 6 h beyond the edge ticks (no label at the frame)
        ax.set_xlim(Rn.forcing[0] - pad, Rn.forcing[1] + pad)
        span_d = (Rn.forcing[1] - Rn.forcing[0]).days
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2 if span_d > 8 else 1))
        ax.xaxis.set_minor_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.grid(True, alpha=0.3, lw=0.4)
        ax.set_ylabel("domain-mean precipitation (mm h$^{-1}$)")
        ax.set_xlabel(f"time (UTC), {Rn.forcing[0].year}")
        C.panel_letter(ax, letter, text=f"{Rn.cfg.event_name} ({Rn.cfg.event_id})")
        sources += [Rn.cfg_path, Rn.rj_path, Rn.csv_path, *Rn.files]
    sources += [q for q in R5_RAIN_SCRIPTS if q.exists()]
    C.export(fig, name, dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT, sources=sources,
             notes="design kept from the R5 rainfall figures (manuscript/paper_submission_v5/_make_{pineios,mandra}_rain.py: "
                   "ERA5 red, bias-corrected IMERG blue, raw IMERG light-blue dashed, totals and peaks in the legend, which sits "
                   "below each panel so that it overlaps neither the curves nor the shaded window); data = "
                   "model-bbox mean over the forcing window (tref..tstop) from phase4/rain; shaded = R2 event window; every value "
                   "asserted against the rain JSON")
    plt.close(fig)


# =================================================================================================== F10 / F11
def _split_label(lab):
    lab = lab.split(" [")[0]
    m = re.match(r"(.+?) \((.+)\)$", lab)
    return (m.group(1), m.group(2)) if m else (lab, "")


def fig10(name="F10"):
    """Cross-event skill of the six runs of record: strict CSI, fuzzy CSI (r = 1) and CSI* at the best depth threshold, over the
    literature benchmark bands. Run of record only (CODE-17 A1): no earlier-release series, no version label in the legend."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    import fig_skill_sweeps_v14 as FS
    matplotlib, plt = mpl_setup()
    ce_path = P4 / "cross_event_v14_v142.json"
    ce = jload(ce_path)
    runs = list(ce["events"])
    need(runs == [RUNS[e] for e in ORDER], f"cross-event runs {runs} != canonical runs of record")
    # values: the enhanced_v14 blocks (as fig_skill_sweeps_v14.py); cross-checks against the sources
    rows = []
    for run in runs:
        e = ce["events"][run]
        v = e["enhanced_v14"]
        if run == RUNS["crete"]:
            tiers_path = P5 / f"{run}_tiers.json"
            t03 = jload(tiers_path)["aois"]["03"]
            need(t03["tier"] == 1 and "tier 1" in e["label"], "Crete cross-event block is not the tier-1 AOI03 block")
            need(v["strict"]["csi"] == t03["strict_threshold_sweep"][thr_key()]["csi"], "Crete strict CSI != tiers JSON AOI03")
            need(v["fuzzy_r1"]["csi"] == t03["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"], "Crete fuzzy r=1 CSI != tiers JSON AOI03")
            need(v["csi_star"]["csi"] == t03["csi_star"]["csi"], "Crete CSI* != tiers JSON AOI03")
        else:
            srcj = jload(REPO / e["sources"]["enhanced_v14"].replace("\\", "/"))["validation"]
            need(v["strict"]["csi"] == srcj["strict_threshold_sweep"][thr_key()]["csi"], f"{run}: strict CSI != source record")
            need(v["fuzzy_r1"]["csi"] == srcj["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"], f"{run}: fuzzy r=1 CSI != source record")
        nm, code = _split_label(e["label"])
        rows.append({"tick": f"{nm}\n({code})", "s14": v["strict"]["csi"], "f14": v["fuzzy_r1"]["csi"], "cs": (v.get("csi_star") or {}).get("csi")})
    W = C.WIDTH_2COL_MM
    L, RM, T, AH, B = 14.0, 3.0, 3.0, 58.0, 23.0
    H = T + AH + B
    fig = C.fig_mm(plt, W, H)
    ax = C.ax_mm(fig, L, B, W - L - RM, AH)
    band_labels = []
    for lab, lo, hi, col in FS.BANDS:                 # literature constants of fig_skill_sweeps_v14.py; citations go to the caption
        generic = lab.split(" (")[0] + " range"
        ax.axhspan(lo, hi, color=col, zorder=0, lw=0)
        band_labels.append(Patch(facecolor=col, edgecolor="none", label=generic))
    ax.axhline(FS.WING_MEDIAN, color="0.45", ls=":", lw=1.0, zorder=1)
    med = Line2D([], [], color="0.45", ls=":", lw=1.0, label="benchmark median")
    off = {"s14": -0.2, "f14": 0.0, "cs": 0.2}
    sty = {"s14": dict(marker="o", color=C.OI["blue"], mfc=C.OI["blue"]),
           "f14": dict(marker="s", color=C.OI["green"], mfc=C.OI["green"]),
           "cs": dict(marker="^", color=C.OI["vermillion"], mfc=C.OI["vermillion"])}
    labels = {"s14": "strict CSI", "f14": "fuzzy CSI (r = 1)", "cs": "CSI* (best depth threshold)"}
    handles = {}
    for k in ("s14", "f14", "cs"):
        xs = [i + off[k] for i, r in enumerate(rows) if r[k] is not None]
        ys = [r[k] for r in rows if r[k] is not None]
        (ln,) = ax.plot(xs, ys, ls="none", ms=5.0, mew=0.9, zorder=4, label=labels[k], **sty[k])
        handles[k] = ln
    ax.set_xticks(range(len(rows))); ax.set_xticklabels([r["tick"] for r in rows])
    ax.set_xlim(-0.6, len(rows) - 0.4)
    top = max([r[k] for r in rows for k in ("s14", "f14", "cs") if r[k] is not None] + [hi for _, _, hi, _ in FS.BANDS])
    ax.set_ylim(0, math.ceil((top + 0.04) * 10) / 10)
    ax.set_ylabel(f"CSI ({HMAX} > {THRESHOLD:.2f} m)")
    ax.tick_params(axis="x", length=0, pad=3)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    order = [handles["s14"], handles["f14"], handles["cs"], band_labels[0], band_labels[1], med]
    fig.legend(handles=order, loc="lower left", bbox_to_anchor=(L / W, 1.0 / H), ncol=3, frameon=False, borderaxespad=0.0)
    C.export(fig, name, dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT,
             sources=[ce_path, P5 / "crete_canonical_r2on_tiers.json", V14 / "scripts" / "fig_skill_sweeps_v14.py"],
             notes=f"run-of-record markers only (strict CSI, fuzzy r = 1 CSI, CSI* at the best threshold) of phase4/figures/"
                   f"fig10_skill_v14_v142.png; no earlier-release series, no version label (release history: S7/S10); Crete = "
                   "tier-1 AOI03 block (asserted against the tiers JSON); benchmark bands = the literature constants of "
                   "fig_skill_sweeps_v14.py, labelled without author names (citations belong in the caption)")
    plt.close(fig)


def fig11(name="F11"):
    """(a) Pineios CSI / HR / FAR against the depth threshold, (b) Mandra CSI / HR / F2 against the fuzzy radius; the runs of
    record only (CODE-17 A2): no earlier-release series, legend entries are the score names."""
    matplotlib, plt = mpl_setup()
    ce = jload(P4 / "cross_event_v14_v142.json")
    pin_run, man_run = RUNS["pineios"], RUNS["mandra"]
    srcs = {"pin": RES / f"{pin_run}_v14_newmask.json", "man": RES / f"{man_run}_v14_newmask.json"}
    J = {k: jload(v)["validation"] for k, v in srcs.items()}
    need(ce["harness_label"] == jload(RES / f"{pin_run}_record.json")["harness_tag"], "Pineios harness label inconsistent with its record")
    for k, run in (("pin", pin_run), ("man", man_run)):
        need(J[k]["strict_threshold_sweep"][thr_key()]["csi"] == ce["events"][run]["enhanced_v14"]["strict"]["csi"],
             f"{run}: strict CSI of the record != cross-event JSON")
    man_cfg, man_cfg_path = load_cfg(man_run)
    res_m = int(man_cfg.grid["res"])
    thr = [(k, float(re.match(r"h>([\d.]+)m", k).group(1))) for k in J["pin"]["strict_threshold_sweep"]]
    thr.sort(key=lambda kv: kv[1])
    W = C.WIDTH_2COL_MM
    L, GAPX, RM, T, AH, B = 13.0, 15.0, 3.0, 6.0, 56.0, 20.0
    AW = (W - L - GAPX - RM) / 2
    H = T + AH + B
    fig = C.fig_mm(plt, W, H)
    a1 = C.ax_mm(fig, L, B, AW, AH)
    a2 = C.ax_mm(fig, L + AW + GAPX, B, AW, AH)
    met = {"csi": ("CSI", C.OI["blue"], "o"), "hr": ("HR", C.OI["green"], "s"), "far": ("FAR", C.OI["vermillion"], "^"),
           "f2": ("F2", C.OI["purple"], "D")}

    def draw(ax, xs, getter, metrics, key):
        hs = []
        for m in metrics:
            lab, col, mk = met[m]
            (ln,) = ax.plot(xs, [getter(J[key], x)[m] for x in xs], "-", color=col, marker=mk, ms=3.8, mew=0.8, lw=1.0, mfc=col, label=lab)
            hs.append(ln)
        return hs
    xs_a = [t for _, t in thr]
    key_of = {t: k for k, t in thr}
    ha = draw(a1, xs_a, lambda v, t: v["strict_threshold_sweep"][key_of[t]], ("csi", "hr", "far"), "pin")
    rs = sorted(int(k.split("=")[1]) for k in J["man"]["fuzzy_at_h_gt_0p10m"])
    hb = draw(a2, rs, lambda v, r: v["fuzzy_at_h_gt_0p10m"][f"r={r}"], ("csi", "hr", "f2"), "man")
    a1.set_xticks(xs_a); a1.set_xticklabels([f"{t:.2f}" for t in xs_a])
    a1.set_xlabel(f"depth threshold: {HMAX} > x (m)")
    a2.set_xticks(rs); a2.set_xlabel(f"neighbourhood radius r (cells of {res_m} m)")
    for ax in (a1, a2):
        ax.set_ylabel("score")
        lo = min(min(l.get_ydata()) for l in ax.get_lines())
        ax.set_ylim(math.floor((lo - 0.03) * 10) / 10, 1.02)
        ax.grid(True, alpha=0.3, lw=0.4)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    pe_, pm_ = _split_label(ce["events"][pin_run]["label"]), _split_label(ce["events"][man_run]["label"])
    C.panel_letter(a1, "a", text=f"{pe_[0]} ({pe_[1]}): depth-threshold sweep")
    C.panel_letter(a2, "b", text=f"{pm_[0]} ({pm_[1]}): fuzzy-tolerance sweep")
    for ax, hs in ((a1, ha), (a2, hb)):
        pos = ax.get_position()
        fig.legend(handles=hs, loc="lower left", bbox_to_anchor=(pos.x0, 1.0 / H), ncol=3, frameon=False, borderaxespad=0.0)
    C.export(fig, name, dpi=C.DPI_COMBINATION, width_mm=W, script=SCRIPT,
             sources=[*srcs.values(), RES / f"{pin_run}_record.json", man_cfg_path, P4 / "cross_event_v14_v142.json"],
             notes=f"runs of record only ({pin_run}, {man_run}): content of phase4/figures/fig11_sweeps_v14_v142.png without the "
                   "earlier-release series; legend = score names (CSI, HR, FAR / F2; F2 = 5 TP / (5 TP + 4 FN + FP) as recorded "
                   "by the validator); integer radius ticks")
    plt.close(fig)


# =================================================================================================== F1 inputs
def f1_data():
    import numpy as np
    import pyogrio
    import pyproj
    import xarray as xr
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform, unary_union
    import validate_event_v2 as V
    out = {"generated_utc": C.utc_now(), "script": SCRIPT, "note": "model-domain boxes = sfincs_map.nc grid extent (cell edges); "
           "AOI centroids = centroid (model CRS) of the union of each AOI's area-of-interest polygons, as listed by fig_map_v14.py",
           "events": []}
    for event in ORDER:
        run = RUNS[event]
        cfg, cfg_path = load_cfg(run)
        model_nc = cfg.paths["model_dir"] / "sfincs_map.nc"
        with xr.open_dataset(model_nc) as dm:
            x, y = dm["x"].values, dm["y"].values
        dx, dy = float(x[0, 1] - x[0, 0]), abs(float(y[1, 0] - y[0, 0]))
        x0, x1, y0, y1 = float(x.min() - dx / 2), float(x.max() + dx / 2), float(y.min() - dy / 2), float(y.max() + dy / 2)
        crs = pyproj.CRS.from_epsg(cfg.epsg)
        tr = pyproj.Transformer.from_crs(crs, 4326, always_xy=True)
        n = 80
        xs = np.r_[np.linspace(x0, x1, n), np.full(n, x1), np.linspace(x1, x0, n), np.full(n, x0)]
        ys = np.r_[np.full(n, y0), np.linspace(y0, y1, n), np.full(n, y1), np.linspace(y1, y0, n)]
        lon, lat = tr.transform(xs, ys)
        ems_dir = cfg.paths["data_dir"] / "ems_polygons"
        files = V._list_shps(ems_dir, AOI_PATTERNS)
        groups = {}
        for p in files:
            m = re.search(r"AOI(\d+)", p.name) or re.search(r"EMSR\d+_(\d{2})[A-Z]", p.name)
            need(m is not None, f"{run}: no AOI number in {p.name}")
            info = pyogrio.read_info(p)
            to_model = pyproj.Transformer.from_crs(pyproj.CRS.from_user_input(info["crs"]), crs, always_xy=True).transform
            _, _, gw, _ = pyogrio.raw.read(str(p), return_fids=True)
            groups.setdefault(m.group(1), {"files": [], "geoms": []})
            groups[m.group(1)]["files"].append(p)
            groups[m.group(1)]["geoms"] += [shp_transform(to_model, from_wkb(g)) for g in gw if g is not None]
        aois = []
        for k in sorted(groups):
            u = unary_union(groups[k]["geoms"])
            c = u.centroid
            clon, clat = tr.transform(c.x, c.y)
            aois.append({"aoi": k, "lon": clon, "lat": clat, "x": c.x, "y": c.y, "inside_domain": bool(x0 <= c.x <= x1 and y0 <= c.y <= y1),
                         "files": [C.rel(p) for p in groups[k]["files"]]})
        extra, extra_src = [], []
        if event == "crete":
            ll_to_model = pyproj.Transformer.from_crs(4326, crs, always_xy=True).transform
            for k, (nm, poly) in sorted(crete_tier3(jload(P5 / f"{run}_tiers.json")).items()):
                c = shp_transform(ll_to_model, poly).centroid
                clon, clat = tr.transform(c.x, c.y)
                extra.append({"aoi": k, "name": nm, "tier": 3, "lon": clon, "lat": clat, "x": c.x, "y": c.y,
                              "inside_domain": bool(x0 <= c.x <= x1 and y0 <= c.y <= y1)})
            extra_src = [C.rel(SNAPSHOT), C.rel(P5 / f"{run}_tiers.json")]
        out["events"].append({"event": event, "run": run, "name": cfg.event_name, "ems": cfg.event_id, "epsg": cfg.epsg,
                              "utm_zone": crs.utm_zone, "domain_xy": [x0, x1, y0, y1], "domain_lonlat": [[float(a), float(b)] for a, b in zip(lon, lat)],
                              "aois": aois, "aois_tier3": extra, "sources": [C.rel(cfg_path), C.rel(model_nc), C.rel(ems_dir), *extra_src]})
        print(f"  {run}: domain {x0 / 1e3:.1f}-{x1 / 1e3:.1f} x {y0 / 1e3:.1f}-{y1 / 1e3:.1f} km (EPSG {cfg.epsg}); "
              f"{len(aois)} AOIs ({sum(a['inside_domain'] for a in aois)} centroids inside the domain)"
              + (f" + {len(extra)} tier-3 AOIs from the EMS API snapshot" if extra else ""))
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = C.DATA_DIR / "F1_inputs.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", C.rel(p))


# =================================================================================================== main
def main() -> int:
    setup_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fig", action="append", default=[], help="F1data F3 F4 F5 F6 F7 F8 F9 F10 F11 | all (default)")
    a = ap.parse_args()
    figs = a.fig or ["all"]
    if "all" in figs:
        figs = ["F1data", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11"]
    for f in figs:
        print(f"[{C.utc_now()}] {f}", flush=True)
        if f == "F1data":
            f1_data()
        elif f in MAP_FIGS:
            fig_map(f, MAP_FIGS[f])
        elif f == "F4":
            fig4()
        elif f == "F9":
            fig9()
        elif f == "F10":
            fig10()
        elif f == "F11":
            fig11()
        else:
            raise SystemExit(f"unknown figure {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
