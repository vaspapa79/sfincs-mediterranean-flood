"""Download Copernicus DEM 30 m 1° tiles intersecting the bbox and build
a VRT mosaic at data/copdem30/copdem30.vrt.

Source: AWS Open Data (public, no auth).
"""
from __future__ import annotations

import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

from _common import load_config, ensure_dir


def main():
    cfg = load_config()
    dest = ensure_dir(cfg.paths["data_dir"] / "copdem30")
    tiles = cfg.dem_tiles()
    base = "https://copernicus-dem-30m.s3.amazonaws.com"
    headers = {"User-Agent": f"Mozilla/5.0 ({cfg.event_slug} DEM fetcher)"}

    for n, e in tiles:
        name = f"Copernicus_DSM_COG_10_{n}_00_{e}_00_DEM"
        out = dest / f"{name}.tif"
        if out.exists() and out.stat().st_size > 1024 * 1024:
            print(f"  skip (cached): {name} ({out.stat().st_size/1e6:.1f} MB)")
            continue
        url = f"{base}/{name}/{name}.tif"
        print(f"downloading: {url}")
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out.write_bytes(r.read())
            print(f"  wrote: {out.name} ({out.stat().st_size/1e6:.1f} MB)")
        except urllib.error.HTTPError as exc:
            print(f"  FAILED ({exc.code}): {name}")

    # Build VRT
    tifs = sorted(dest.glob("*.tif"))
    if not tifs:
        sys.exit("no DEM tiles on disk; cannot build VRT")
    vrt = dest / "copdem30.vrt"
    gdalbuildvrt = cfg.env.get("gdalbuildvrt", "gdalbuildvrt")
    subprocess.run([str(gdalbuildvrt), "-overwrite", str(vrt)] + [str(t) for t in tifs],
                   check=True)
    print(f"VRT built: {vrt}  ({len(tifs)} tiles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
