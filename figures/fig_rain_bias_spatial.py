"""Spatial proof that the gauge-anchored IMERG bias correction rescales rainfall
MAGNITUDE without relocating the storm core.

Companion to the domain-mean time-series figures (Fig 4 Pineios / Fig 6 Mandra):
those show only the temporal mean; this adds the spatial dimension and shows that
within the bias-correction sub-window the correction is a single multiplicative
factor (corrected = raw x factor at EVERY cell), so the raw and corrected fields
share an IDENTICAL spatial pattern and the convective core cannot move — it sits
where the raw IMERG core sits, over the observed-maximum region.

Two rows (Mandra EMSR257, Pineios EMSR692) x three columns
(RAW | BIAS-CORRECTED | RATIO=corrected/raw). The ratio panel is a flat constant
equal to the factor — the direct proof the correction is purely multiplicative.

Uses the ACTUAL pipeline fields: imerg_<event>.raw.nc (raw) and imerg_<event>.nc
(corrected, factor recorded in the `bias_correction` global attribute). Nothing is
synthesised. Accumulation is over the bias-correction sub-window only, where the
factor is applied uniformly.

Run:  python figures/fig_rain_bias_spatial.py
Out:  figures/fig_rain_bias_spatial.png  (300 dpi; EPS/TIFF by changing EXT)
"""
from __future__ import annotations
import re
from pathlib import Path

import numpy as np
import xarray as xr
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import Normalize

IMPL = Path(r"D:/ELKAK/implementation")
OUT = Path(__file__).resolve().parent / "fig_rain_bias_spatial.png"
EXT_DPI = 300

EVENTS = [
    dict(key="MANDRA", id="EMSR257", base=IMPL / "mandra_sfincs_enhanced",
         imerg="imerg_mandra", aoi_glob="*area_of_interest*.shp",
         # NOA-Vília gauge (Lagouvardos et al. 2017; Diakakis et al. 2019)
         gauge=("NOA-Vília", 23.236, 38.165, "~200 mm (gauge anchor,\nDiakakis et al. 2019)")),
    dict(key="PINEIOS", id="EMSR692", base=IMPL / "pineios_sfincs_enhanced",
         imerg="imerg_pineios", aoi_glob="*areaOfInterestA*.shp",
         # Zagora / Pelion gauge maximum (Dimitriou et al. 2024)
         gauge=("Zagora\n(Pelion)", 23.10, 39.45, "754 mm\n(Dimitriou et al. 2024)")),
]


def parse_bias(ds):
    """Return (factor, t0, t1, target, watershed bbox) from the global attr."""
    s = ds.attrs["bias_correction"]
    fac = float(re.search(r"([\d.]+)x", s).group(1))
    t0, t1 = re.search(r"window (.+?) to (.+?) so", s).groups()
    tgt = float(re.search(r"matches ([\d.]+) mm", s).group(1))
    bb = tuple(float(x) for x in re.search(r"\(([-\d.,]+)\)", s).group(1).split(","))
    return fac, t0.strip(), t1.strip(), tgt, bb


def accumulate(ds, t0, t1):
    p = ds["precip"].sel(time=slice(t0, t1))
    ti = p.indexes["time"]
    dt_h = (ti[1] - ti[0]).total_seconds() / 3600.0
    return p.sum("time") * dt_h          # mm


def bbox_mean(field, bb):
    w, s, e, n = bb
    lat = field.latitude.values
    la = slice(n, s) if lat[0] > lat[-1] else slice(s, n)
    sub = field.sel(latitude=la, longitude=slice(w, e))
    return float(np.nanmean(sub.values))


def mesh_edges(coord):
    c = np.asarray(coord, float)
    d = np.diff(c)
    return np.concatenate([[c[0] - d[0] / 2], c[:-1] + d / 2, [c[-1] + d[-1] / 2]])


def aoi_rects(base, glob_pat):
    import glob as _g
    rects, seen = [], {}
    for f in _g.glob(str(base / "data" / "ems_polygons" / "**" / glob_pat), recursive=True):
        # dissolve to one rectangle per AOI id (e.g. AOI01 / 01STRYMONAS)
        m = re.search(r"(AOI\d+|\d{2}[A-Z]+)", Path(f).name)
        key = m.group(1) if m else Path(f).name
        b = gpd.read_file(f).to_crs(4326).total_bounds
        if key in seen:
            o = seen[key]
            seen[key] = [min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])]
        else:
            seen[key] = list(b)
    return list(seen.values())


def main():
    fig, axes = plt.subplots(2, 3, figsize=(15, 9.2))
    for row, ev in enumerate(EVENTS):
        raw = xr.open_dataset(ev["base"] / "data" / f"{ev['imerg']}.raw.nc")
        cor = xr.open_dataset(ev["base"] / "data" / f"{ev['imerg']}.nc")
        fac, t0, t1, tgt, ws = parse_bias(cor)
        ra = accumulate(raw, t0, t1)
        co = accumulate(cor, t0, t1)
        ratio = (co / ra.where(ra > 0)).values
        lon_e, lat_e = mesh_edges(ra.longitude.values), mesh_edges(ra.latitude.values)
        # geometries
        region = gpd.read_file(ev["base"] / "model" / "gis" / "region.geojson").to_crs(4326)
        rects = aoi_rects(ev["base"], ev["aoi_glob"])
        # zoom to the basin: model domain + AOIs + gauge, with a small margin
        rb = region.total_bounds  # w,s,e,n
        gx, gy = ev["gauge"][1], ev["gauge"][2]
        zx0 = min(rb[0], gx) - 0.06; zx1 = max(rb[2], gx) + 0.06
        zy0 = min(rb[1], gy) - 0.06; zy1 = max(rb[3], gy) + 0.06
        # corrected max cell
        jj, ii = np.unravel_index(int(np.nanargmax(co.values)), co.shape)
        cmx_lon, cmx_lat, cmx_val = float(co.longitude[ii]), float(co.latitude[jj]), float(co.max())
        gname, glon, glat, gnote = ev["gauge"]

        vmax_raw = float(np.nanpercentile(ra.values, 99.5))
        vmax_cor = float(np.nanpercentile(co.values, 99.5))
        panels = [
            (ra.values, "Greys" if False else "YlGnBu", vmax_raw,
             f"RAW IMERG  ({t0[:10]}–{t1[:10]})", bbox_mean(ra, ws)),
            (co.values, "YlGnBu", vmax_cor,
             f"BIAS-CORRECTED (x{fac:g})", bbox_mean(co, ws)),
        ]
        for col, (data, cmap, vmax, title, bmean) in enumerate(panels):
            ax = axes[row, col]
            pm = ax.pcolormesh(lon_e, lat_e, data, cmap=cmap,
                               norm=Normalize(0, vmax), shading="flat")
            cb = fig.colorbar(pm, ax=ax, fraction=0.046, pad=0.02)
            cb.set_label("accumulated rainfall (mm)", fontsize=8)
            region.boundary.plot(ax=ax, color="k", lw=1.3, zorder=5)
            for (w, s, e, n) in rects:
                ax.add_patch(Rectangle((w, s), e - w, n - s, fill=False,
                                       ec="crimson", lw=1.0, ls="--", zorder=6))
            ax.plot(cmx_lon, cmx_lat, marker="*", ms=16, mfc="gold", mec="k",
                    mew=0.8, zorder=8)
            ax.plot(glon, glat, marker="v", ms=9, mfc="white", mec="k", mew=1.2, zorder=8)
            ax.annotate(gname, (glon, glat), textcoords="offset points",
                        xytext=(6, 4), fontsize=7, fontweight="bold", zorder=9)
            ax.set_title(f"{ev['key']} ({ev['id']}) — {title}", fontsize=9.5)
            ax.text(0.02, 0.97, f"basin-mean: {bmean:.0f} mm\ncore max: {cmx_val:.0f} mm",
                    transform=ax.transAxes, va="top", ha="left", fontsize=8,
                    bbox=dict(fc="white", ec="0.5", alpha=0.85, pad=2), zorder=10)
            ax.set_xlim(zx0, zx1); ax.set_ylim(zy0, zy1)
            ax.set_aspect(1.0 / np.cos(np.deg2rad(float(ra.latitude.mean()))))
            ax.set_xlabel("lon (°E)", fontsize=8); ax.set_ylabel("lat (°N)", fontsize=8)
            ax.tick_params(labelsize=7)

        # ratio panel
        ax = axes[row, 2]
        pm = ax.pcolormesh(lon_e, lat_e, ratio, cmap="RdBu_r",
                           norm=Normalize(fac - 0.05, fac + 0.05), shading="flat")
        cb = fig.colorbar(pm, ax=ax, fraction=0.046, pad=0.02)
        cb.set_label("corrected / raw", fontsize=8)
        region.boundary.plot(ax=ax, color="k", lw=1.3, zorder=5)
        rmin, rmax = np.nanmin(ratio), np.nanmax(ratio)
        ax.set_title(f"{ev['key']} — RATIO ≡ {fac:g} (constant)", fontsize=9.5)
        ax.text(0.02, 0.97,
                f"ratio = {rmin:.3f}–{rmax:.3f}\n(uniform x{fac:g}\n→ core fixed)",
                transform=ax.transAxes, va="top", ha="left", fontsize=8,
                bbox=dict(fc="white", ec="0.5", alpha=0.85, pad=2), zorder=10)
        ax.set_xlim(zx0, zx1); ax.set_ylim(zy0, zy1)
        ax.set_aspect(1.0 / np.cos(np.deg2rad(float(ra.latitude.mean()))))
        ax.set_xlabel("lon (°E)", fontsize=8); ax.set_ylabel("lat (°N)", fontsize=8)
        ax.tick_params(labelsize=7)
        print(f"{ev['key']}: factor x{fac:g}  window {t0[:10]}..{t1[:10]}  "
              f"basin-mean raw->cor = {bbox_mean(ra, ws):.0f} -> {bbox_mean(co, ws):.0f} mm  "
              f"(target {tgt:.0f}); core max {cmx_val:.0f} mm at ({cmx_lon:.2f},{cmx_lat:.2f}); "
              f"ratio range [{rmin:.3f},{rmax:.3f}]")

    fig.suptitle("Gauge-anchored IMERG bias correction: magnitude rescaled, storm core fixed\n"
                 "(accumulation over the bias-correction sub-window; black = model domain, "
                 "red dashed = EMS AOIs, ★ = corrected core max, ▽ = gauge)",
                 fontsize=11, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT, dpi=EXT_DPI, bbox_inches="tight")
    print(f"wrote {OUT} @ {EXT_DPI} dpi")


if __name__ == "__main__":
    main()
