"""Fetch Esri World Imagery z12 tiles matched to the SFINCS UTM bbox
(buffered) and reproject to EPSG = crs.epsg.

Reads model/sfincs_map.nc to discover the exact UTM extent — depends on
run_sfincs.py finishing first.
"""
from __future__ import annotations

import math
import sys
import time
import urllib.request
from pathlib import Path

from _common import load_config, ensure_dir


def main():
    cfg = load_config()
    import numpy as np
    import xarray as xr
    import pyproj
    from PIL import Image
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, Resampling

    work = cfg.paths["work_dir"]
    out_png = cfg.paths["data_dir"] / "basemap_satellite.png"
    out_attrib = cfg.paths["data_dir"] / "basemap_attribution.txt"
    tile_cache = ensure_dir(cfg.paths["data_dir"] / "tile_cache_esri_z12")

    dmap = xr.open_dataset(cfg.paths["model_dir"] / "sfincs_map.nc")
    x = dmap["x"].values; y = dmap["y"].values
    anim = cfg.animation
    buf = float(anim.get("basemap_buffer_m", 3000))
    utm_xmin = float(x.min()) - buf; utm_xmax = float(x.max()) + buf
    utm_ymin = float(y.min()) - buf; utm_ymax = float(y.max()) + buf
    print(f"UTM bbox (buffered): ({utm_xmin:.0f},{utm_ymin:.0f}) - "
          f"({utm_xmax:.0f},{utm_ymax:.0f}) = "
          f"{utm_xmax-utm_xmin:.0f} x {utm_ymax-utm_ymin:.0f} m")

    to_ll = pyproj.Transformer.from_crs(cfg.epsg, 4326, always_xy=True)
    lon_sw, lat_sw = to_ll.transform(utm_xmin, utm_ymin)
    lon_ne, lat_ne = to_ll.transform(utm_xmax, utm_ymax)
    lon_se, lat_se = to_ll.transform(utm_xmax, utm_ymin)
    lon_nw, lat_nw = to_ll.transform(utm_xmin, utm_ymax)
    lon_min = min(lon_sw, lon_nw); lon_max = max(lon_se, lon_ne)
    lat_min = min(lat_sw, lat_se); lat_max = max(lat_nw, lat_ne)

    ZOOM = int(anim.get("basemap_zoom", 12))

    def latlon_to_tile(lat, lon, z):
        n = 2.0 ** z
        xt = int((lon + 180.0) / 360.0 * n)
        yt = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
        return xt, yt

    xt_min, yt_max = latlon_to_tile(lat_min, lon_min, ZOOM)
    xt_max, yt_min = latlon_to_tile(lat_max, lon_max, ZOOM)
    nx_t = xt_max - xt_min + 1
    ny_t = yt_max - yt_min + 1
    print(f"zoom {ZOOM}: {nx_t}x{ny_t} = {nx_t*ny_t} tiles")

    def download_tile(z, x, y, cache_dir):
        out = cache_dir / f"z{z}_x{x}_y{y}.png"
        if out.exists() and out.stat().st_size > 256:
            return out
        url = (f"https://server.arcgisonline.com/ArcGIS/rest/services/"
               f"World_Imagery/MapServer/tile/{z}/{y}/{x}")
        req = urllib.request.Request(url,
                                     headers={"User-Agent": f"Mozilla/5.0 ({cfg.event_slug} basemap)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out.write_bytes(r.read())
        return out

    mosaic = Image.new("RGB", (nx_t * 256, ny_t * 256))
    for yi, yt in enumerate(range(yt_min, yt_max + 1)):
        for xi, xt in enumerate(range(xt_min, xt_max + 1)):
            tp = download_tile(ZOOM, xt, yt, tile_cache)
            mosaic.paste(Image.open(tp).convert("RGB"), (xi * 256, yi * 256))
            time.sleep(0.04)
    print(f"mosaic: {mosaic.size}")

    def tile_to_lonlat(xt, yt, z):
        n = 2.0 ** z
        lon = xt / n * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yt / n))))
        return lon, lat

    lon_w, lat_n = tile_to_lonlat(xt_min, yt_min, ZOOM)
    lon_e, lat_s = tile_to_lonlat(xt_max + 1, yt_max + 1, ZOOM)
    to_merc = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)
    mx_w, my_n = to_merc.transform(lon_w, lat_n)
    mx_e, my_s = to_merc.transform(lon_e, lat_s)
    arr = np.array(mosaic)
    src_transform = from_bounds(mx_w, my_s, mx_e, my_n, arr.shape[1], arr.shape[0])

    tgt_res = 60.0
    tgt_W = int(round((utm_xmax - utm_xmin) / tgt_res))
    tgt_H = int(round((utm_ymax - utm_ymin) / tgt_res))
    tgt_transform = from_bounds(utm_xmin, utm_ymin, utm_xmax, utm_ymax, tgt_W, tgt_H)
    dst = np.zeros((3, tgt_H, tgt_W), dtype=np.uint8)
    for b in range(3):
        reproject(source=arr[:, :, b], destination=dst[b],
                  src_transform=src_transform, src_crs="EPSG:3857",
                  dst_transform=tgt_transform, dst_crs=f"EPSG:{cfg.epsg}",
                  resampling=Resampling.bilinear)
    out_arr = np.transpose(dst, (1, 2, 0))
    Image.fromarray(out_arr, mode="RGB").save(out_png, optimize=True)
    print(f"basemap saved: {out_png} ({out_png.stat().st_size/1024:.0f} kB) "
          f"shape={out_arr.shape}")
    out_attrib.write_text(
        "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community.\n"
        "Source: ArcGIS World Imagery — Free for non-commercial use with attribution.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
