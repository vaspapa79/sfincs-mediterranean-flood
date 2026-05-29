"""Derive a SCS Curve Number GeoTIFF from ESA WorldCover via the lookup
in the event YAML config (infiltration: section).

The output `data/cn_raster.tif` is what hydromt-sfincs setup_cn_infiltration
ingests when the data catalog has a `cn_raster:` entry.

Adapted from implementation/strymonas_forecast_v2/scripts/prep_cn_raster.py
— same TR-55 AMC formula, generalised to any event by reading bbox/buffer
from the skill's _common.EventCfg.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

from _common import load_config, ensure_dir


def main():
    cfg = load_config()
    if not cfg.infiltration["enabled"]:
        print("infiltration.enabled=false in config — skipping CN raster prep")
        return 0

    data = ensure_dir(cfg.paths["data_dir"])
    wc_vrt = data / "esa_worldcover" / "esa_worldcover_2021.vrt"
    if not wc_vrt.exists():
        sys.exit(f"missing WorldCover VRT: {wc_vrt} — run download_worldcover.py first")

    cn_lookup = {int(k): int(v) for k, v in cfg.infiltration["cn_lookup"].items()}
    print(f"CN lookup (WorldCover class -> CN): {cn_lookup}")

    b = cfg.bbox
    buf = float(b.get("era5_buffer_deg", 0.2))
    west = float(b["west"]) - buf
    east = float(b["east"]) + buf
    south = float(b["south"]) - buf
    north = float(b["north"]) + buf

    with rasterio.open(wc_vrt) as src:
        win = src.window(west, south, east, north)
        win = win.round_offsets().round_lengths()
        wc = src.read(1, window=win)
        tr = src.window_transform(win)
        crs = src.crs
        nod = src.nodata
        print(f"WorldCover clip: shape={wc.shape}  crs={crs}  nodata={nod}")
        print(f"  unique classes: {sorted(np.unique(wc).tolist())[:20]}")

    cn = np.zeros_like(wc, dtype=np.uint8)
    default_cn = 76  # cropland-like default
    for c in np.unique(wc):
        if c == nod:
            continue
        cn_v = cn_lookup.get(int(c), default_cn)
        cn[wc == c] = cn_v

    amc = int(cfg.infiltration["amc"])
    # Cast to float to avoid uint8 overflow in AMC correction
    # (e.g. 23 * 88 = 2024 overflows uint8 max of 255 → wraps to 232 → wrong CN_III)
    cn_f = cn.astype(np.float32)
    if amc == 1:
        cn_f = 4.2 * cn_f / (10.0 - 0.058 * cn_f)
    elif amc == 3:
        cn_f = 23.0 * cn_f / (10.0 + 0.13 * cn_f)
    cn = np.clip(np.round(cn_f), 1, 100).astype(np.uint8)
    print(f"CN raster: shape={cn.shape}  HSG={cfg.infiltration['hsg']}  "
          f"AMC={amc}  range=[{cn.min()}..{cn.max()}]  mean={cn.mean():.1f}")

    out = data / "cn_raster.tif"
    profile = {
        "driver": "GTiff", "height": cn.shape[0], "width": cn.shape[1],
        "count": 1, "dtype": "uint8", "crs": crs, "transform": tr,
        "compress": "deflate", "tiled": True, "nodata": 0,
    }
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(cn, 1)
    print(f"wrote: {out}  ({out.stat().st_size/1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
