"""CODE-19 A4 — EMSR773 areas of interest: the activation as the EMS dashboard API lists it today (saved as a snapshot) against
the model domain of the run of record (valencia_enhanced_164_v142), and the AOIs the run's cached EMS download holds.

Counts: n = AOIs in the activation; m_bbox = AOIs whose API extent intersects the configured lon/lat bbox; m_grid = AOIs whose
extent intersects the model grid rectangle (UTM); m_active = AOIs whose extent holds at least one active cell (msk > 0);
cached = AOIs with files under the run's data/ems_polygons (the snapshot the truth was built from). No model run, no scoring.

Usage (sfincs-viz env): python -I code19_a4_emsr773_aois.py --repo <worktree> [--api-json <saved API response>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

API = "https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR773"
RUN = "valencia_enhanced_164_v142"


def fetch(url: str, out: Path) -> bytes:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    out.write_bytes(data)
    return data


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--api-json", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    for p in (repo / "skill" / "scripts", repo / "validation"):
        sys.path.insert(0, str(p))
    import numpy as np
    import pyproj
    from shapely import wkt
    from shapely.geometry import box
    from shapely.ops import transform as shp_transform
    from _common import load_config
    import validate_event_v2 as V

    out_dir = repo / "reproduction" / "v14_rerun" / "code19"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    if a.api_json:
        raw = a.api_json.read_bytes(); snap_path = a.api_json; fetched = None
    else:
        snap_path = out_dir / f"ems_api_snapshot_EMSR773_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
        raw = fetch(API, snap_path); fetched = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    j = json.loads(raw.decode("utf-8"))
    r = j["results"][0]
    assert r["code"] == "EMSR773", r["code"]
    cfg = load_config(["--config", str(repo / "reproduction" / "v14_rerun" / "configs" / f"{RUN}.yaml")])
    b = cfg.bbox
    bbox_ll = box(float(b["west"]), float(b["south"]), float(b["east"]), float(b["north"]))
    s = V.open_sfincs_light(cfg.paths["model_dir"])
    x, y, msk = s["x"], s["y"], s["msk"]
    s["ds"].close()
    dx, dy = s["dx"], s["dy"]
    grid_utm = box(x.min() - dx / 2, y.min() - dy / 2, x.max() + dx / 2, y.max() + dy / 2)
    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True).transform
    active = msk > 0
    xa, ya = x[active], y[active]
    cached = sorted({m.group(1) for p in (cfg.paths["data_dir"] / "ems_polygons").iterdir() for m in [re.search(r"_(AOI\d\d)_", p.name)] if m})
    aois = []
    for aoi in r.get("aois", []):
        g = wkt.loads(aoi["extent"]) if aoi.get("extent") else None
        g_utm = shp_transform(to_utm, g) if g is not None else None
        prods = aoi.get("products") or []
        inside = 0
        if g_utm is not None:
            minx, miny, maxx, maxy = g_utm.bounds
            sel = (xa >= minx) & (xa <= maxx) & (ya >= miny) & (ya <= maxy)
            if sel.any():
                from shapely import points, contains_xy
                inside = int(np.count_nonzero(contains_xy(g_utm, xa[sel], ya[sel])))
        aois.append({"number": aoi.get("number"), "name": aoi.get("name"), "extent_wkt": aoi.get("extent"),
                     "n_products": len(prods), "product_types": sorted({str(p.get("productType") or p.get("type") or "") for p in prods}) if isinstance(prods, list) else None,
                     "intersects_bbox": bool(g is not None and g.intersects(bbox_ll)), "intersects_grid": bool(g_utm is not None and g_utm.intersects(grid_utm)),
                     "active_cells_inside": inside, "cached": f"AOI{int(aoi['number']):02d}" in cached if aoi.get("number") is not None else None})
    out = {"utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "api": API, "api_fetched_utc": fetched, "snapshot_file": str(snap_path.relative_to(repo)).replace("\\", "/") if snap_path.is_relative_to(repo) else str(snap_path),
           "snapshot_sha256": hashlib.sha256(raw).hexdigest(), "activation": {k: r.get(k) for k in ("code", "name", "activationTime", "eventTime", "status")},
           "run": RUN, "config_bbox_lonlat": [float(b["west"]), float(b["south"]), float(b["east"]), float(b["north"])], "epsg": cfg.epsg,
           "grid_rectangle_utm": list(grid_utm.bounds), "active_cells": int(active.sum()),
           "n_aois": len(aois), "m_bbox": sum(a_["intersects_bbox"] for a_ in aois), "m_grid": sum(a_["intersects_grid"] for a_ in aois),
           "m_active": sum(a_["active_cells_inside"] > 0 for a_ in aois), "cached_aois": cached, "aois": aois}
    (out_dir / "a4_emsr773_aois.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EMSR773 {r.get('name')}: {out['n_aois']} AOIs; intersect bbox {out['m_bbox']}, grid {out['m_grid']}, with active cells {out['m_active']}; cached {cached}")
    for a_ in aois:
        print(f"  AOI{int(a_['number']):02d} {a_['name']}: products {a_['n_products']} {a_['product_types']}; bbox {a_['intersects_bbox']} grid {a_['intersects_grid']} active cells {a_['active_cells_inside']}; cached {a_['cached']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
