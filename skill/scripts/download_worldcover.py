"""Download ESA WorldCover 10 m v200 tiles intersecting the bbox and
build a VRT at data/esa_worldcover/esa_worldcover_2021.vrt.
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
    dest = ensure_dir(cfg.paths["data_dir"] / "esa_worldcover")
    tiles = cfg.worldcover_tiles()
    base = "https://esa-worldcover.s3.amazonaws.com/v200/2021/map"
    headers = {"User-Agent": f"Mozilla/5.0 ({cfg.event_slug} WorldCover fetcher)"}

    for n, e in tiles:
        name = f"ESA_WorldCover_10m_2021_v200_{n}{e}_Map"
        out = dest / f"{name}.tif"
        if out.exists() and out.stat().st_size > 1024 * 1024:
            print(f"  skip (cached): {name} ({out.stat().st_size/1e6:.1f} MB)")
            continue
        url = f"{base}/{name}.tif"
        print(f"downloading: {url}")
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                out.write_bytes(r.read())
            print(f"  wrote: {out.name} ({out.stat().st_size/1e6:.1f} MB)")
        except urllib.error.HTTPError as exc:
            print(f"  FAILED ({exc.code}): {name}")

    tifs = sorted(dest.glob("ESA_WorldCover_10m_2021_v200_*_Map.tif"))
    if not tifs:
        sys.exit("no WorldCover tiles on disk; cannot build VRT")
    vrt = dest / "esa_worldcover_2021.vrt"
    gdalbuildvrt = cfg.env.get("gdalbuildvrt", "gdalbuildvrt")
    subprocess.run([str(gdalbuildvrt), "-overwrite", str(vrt)] + [str(t) for t in tifs],
                   check=True)
    print(f"WorldCover VRT built: {vrt}  ({len(tifs)} tile(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
