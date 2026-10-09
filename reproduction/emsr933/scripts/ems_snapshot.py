"""CODE-10 Stage 0b — snapshot the EMSR933 activation from the public EMS API and
download every RELEASED vector package (statusCode 'F' with a downloadPath).

The snapshot fixes the provisional cut-off for validation: Stage 4 scores against
exactly the packages listed in the manifest written here, nothing released later.

Outputs
  <out-dir>/ems_api_snapshot_<UTC>.json         raw API bytes, as received
  <out-dir>/ems_snapshot_<UTC>_manifest.json    parsed AOIs/products + download/inventory record
  <out-dir>/ems_snapshot_<UTC>.md               human-readable AOI/product table
  <event-root>/ems_snapshots/<UTC>/zips/        original ZIPs (sha256 in manifest)
  <event-root>/ems_snapshots/<UTC>/extracted/<stem>/   extracted packages

Usage (sfincs-viz python, isolated mode):
  python -I ems_snapshot.py --event-root D:/ELKAK/implementation/emsr933_crete \
      --out-dir <worktree>/reproduction/emsr933
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

API = "https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code={code}"
UA = {"User-Agent": "Mozilla/5.0 (ELKAK EMSR933 snapshot)", "Accept": "application/json, application/zip, */*"}
UTM = 32634  # project CRS for every ELKAK event; areas/sizes reported in this CRS


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def safe_extract(zbytes: bytes, dest: Path) -> list[str]:
    """Extract a ZIP refusing absolute paths / '..' members (zip-slip)."""
    import io
    dest.mkdir(parents=True, exist_ok=False)
    root = dest.resolve()
    names = []
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        for m in zf.infolist():
            target = (dest / m.filename).resolve()
            if not str(target).startswith(str(root)):
                raise RuntimeError(f"unsafe member path in zip: {m.filename!r}")
            names.append(m.filename)
        zf.extractall(dest)
    return names


def wkt_bbox(wkt: str) -> tuple[float, float, float, float]:
    xy = [tuple(map(float, t.split())) for t in re.findall(r"-?\d+\.?\d* -?\d+\.?\d*", wkt)]
    xs, ys = zip(*xy)
    return min(xs), min(ys), max(xs), max(ys)


def aoi_geometry_summary(wkt: str) -> dict:
    from shapely import wkt as swkt
    from shapely.ops import transform
    import pyproj
    g = swkt.loads(wkt)
    tr = pyproj.Transformer.from_crs(4326, UTM, always_xy=True).transform
    gu = transform(tr, g)
    minx, miny, maxx, maxy = gu.bounds
    c = g.centroid
    return {"bbox_lonlat": [round(v, 6) for v in wkt_bbox(wkt)],
            "centroid_lonlat": [round(c.x, 4), round(c.y, 4)],
            "size_km_utm34": [round((maxx - minx) / 1000, 1), round((maxy - miny) / 1000, 1)],
            "area_km2_utm34": round(gu.area / 1e6, 2)}


def inventory(pkg_dir: Path) -> dict:
    """List files; for each vector layer: features, CRS, fields, polygon area (UTM 34N),
    and the distinct values of metadata-like attribute fields."""
    import pyogrio
    import geopandas as gpd
    files = sorted(p for p in pkg_dir.rglob("*") if p.is_file())
    out = {"files": [{"path": str(p.relative_to(pkg_dir)).replace("\\", "/"), "bytes": p.stat().st_size}
                     for p in files], "layers": []}
    metaish = re.compile(r"(date|time|sens|sat|src|source|acq|orb|pol|res|det|method|notation|obj|desc|"
                         r"event|type|platform|mission|provider|area|qa|conf)", re.I)
    for p in files:
        if p.suffix.lower() not in (".shp", ".gpkg", ".geojson", ".json", ".kml"):
            continue
        try:
            for lyr in pyogrio.list_layers(p):
                lname = lyr[0]
                info = pyogrio.read_info(p, layer=lname)
                rec = {"file": str(p.relative_to(pkg_dir)).replace("\\", "/"), "layer": lname,
                       "features": int(info.get("features", -1)), "crs": info.get("crs"),
                       "geometry_type": info.get("geometry_type"),
                       "fields": [str(f) for f in info.get("fields", [])]}
                if rec["features"] > 0:
                    gdf = gpd.read_file(p, layer=lname)
                    vals = {}
                    for col in gdf.columns:
                        if col == "geometry" or not metaish.search(str(col)):
                            continue
                        u = sorted({str(v) for v in gdf[col].dropna().tolist()})
                        vals[col] = u[:12] + ([f"... (+{len(u) - 12} more)"] if len(u) > 12 else [])
                    rec["metadata_values"] = vals
                    if gdf.crs is not None and str(rec["geometry_type"]).lower().find("polygon") >= 0:
                        gu = gdf.to_crs(epsg=UTM)
                        rec["area_km2_sum_utm34"] = round(float(gu.area.sum()) / 1e6, 4)
                        rec["area_km2_union_utm34"] = round(float(gu.union_all().area) / 1e6, 4)
                out["layers"].append(rec)
        except Exception as e:  # keep going; record the failure
            out["layers"].append({"file": str(p.relative_to(pkg_dir)), "error": f"{e.__class__.__name__}: {e}"})
    return out


def main() -> int:
    # The Windows console is cp1252; the table contains non-ASCII (→, ×). The first run
    # (snapshot 20261009T124720Z) crashed on the final console echo AFTER all files were written.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="EMSR933")
    ap.add_argument("--event-root", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    t_fetch = dt.datetime.now(dt.timezone.utc)
    tag = t_fetch.strftime("%Y%m%dT%H%M%SZ")
    url = API.format(code=args.code)
    raw = get(url, timeout=120)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    snap = args.out_dir / f"ems_api_snapshot_{tag}.json"
    snap.write_bytes(raw)
    j = json.loads(raw)
    act = j["results"][0]
    print(f"snapshot {snap.name}: {len(raw)} B sha256={sha256(raw)[:16]}…  fetched {t_fetch.isoformat()}")

    snap_root = args.event_root / "ems_snapshots" / tag
    zdir, xdir = snap_root / "zips", snap_root / "extracted"
    zdir.mkdir(parents=True, exist_ok=False)   # new, empty directory for untrusted downloads
    xdir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "snapshot_utc": t_fetch.strftime("%Y-%m-%dT%H:%M:%SZ"), "api_url": url,
        "raw_json": snap.name, "raw_json_bytes": len(raw), "raw_json_sha256": sha256(raw),
        "activation": {k: act.get(k) for k in ("code", "name", "category", "subCategory", "eventTime",
                                                "activationTime", "closed", "activator", "centroid",
                                                "extent", "productsPath", "reportLink")},
        "event_root": str(args.event_root), "zips_dir": str(zdir), "extracted_dir": str(xdir),
        "aois": [],
    }
    for aoi in sorted(act["aois"], key=lambda a: a["number"]):
        arec = {"number": aoi["number"], "name": aoi["name"], "extent_wkt": aoi["extent"],
                **aoi_geometry_summary(aoi["extent"]), "products": []}
        prods = sorted(aoi.get("products", []),
                       key=lambda p: (p["type"] != "DEL", p["type"], p.get("monitoringNumber") or 0))
        for p in prods:
            v = p.get("version") or {}
            ptype = p["type"] + (f"_MONIT{int(p['monitoringNumber']):02d}" if p.get("monitoring") else "")
            prec = {"id": p["id"], "type": p["type"], "label": ptype, "monitoring": p.get("monitoring"),
                    "monitoringNumber": p.get("monitoringNumber"), "feasible": p.get("feasible"),
                    "mapsCount": p.get("mapsCount"), "expectedDelivery": p.get("expectedDelivery"),
                    "statusCode": v.get("statusCode"), "version": v.get("number"),
                    "deliveryTime": v.get("deliveryTime"), "reason": v.get("reason"),
                    "downloadPath": p.get("downloadPath") or None,
                    "api_layers": [L.get("name") for L in (p.get("layers") or [])],
                    "images": [{k: im.get(k) for k in ("sensorName", "sensorType", "resolutionClass",
                                                       "acquisitionTime", "fileName")}
                               for im in (p.get("images") or [])]}
            released = prec["statusCode"] == "F" and bool(prec["downloadPath"])
            prec["released"] = released
            if released:
                dl = prec["downloadPath"]
                stem = dl.rstrip("/").rsplit("/", 1)[-1]
                stem = stem[:-4] if stem.endswith(".zip") else stem
                try:
                    zb = get(dl)
                    (zdir / f"{stem}.zip").write_bytes(zb)
                    members = safe_extract(zb, xdir / stem)
                    prec["download"] = {"stem": stem, "zip_bytes": len(zb), "zip_sha256": sha256(zb),
                                        "n_members": len(members),
                                        "downloaded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
                    prec["inventory"] = inventory(xdir / stem)
                    print(f"  AOI{aoi['number']:02d} {ptype:12s} id={p['id']} downloaded {stem}.zip "
                          f"({len(zb)/1024:.0f} kB, {len(members)} members)")
                except urllib.error.HTTPError as e:
                    prec["download"] = {"stem": stem, "error": f"HTTP {e.code}"}
                    print(f"  AOI{aoi['number']:02d} {ptype:12s} id={p['id']} DOWNLOAD FAILED HTTP {e.code}")
            arec["products"].append(prec)
        manifest["aois"].append(arec)

    mpath = args.out_dir / f"ems_snapshot_{tag}_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown table
    L = [f"# EMSR933 API snapshot {manifest['snapshot_utc']}", "",
         f"- API: `{url}` → `{snap.name}` ({len(raw)} B, sha256 `{sha256(raw)}`)",
         f"- Activation: {act.get('name')} · {act.get('category')}/{act.get('subCategory')} · "
         f"eventTime {act.get('eventTime')} · activationTime {act.get('activationTime')} · closed={act.get('closed')}",
         "- Status codes (API `version.statusCode`): F = finished/released, I = in production, N = not produced.",
         "", "| AOI | name | bbox lon/lat (W,S,E,N) | centroid | size km (UTM34) | product | id | status | released | expected | delivered | image (sensor, class, acquired UTC) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in manifest["aois"]:
        first = True
        for p in a["products"]:
            img = "; ".join(f"{i['sensorName']} ({i['sensorType']}, {i['resolutionClass']}) {i['acquisitionTime']}"
                            for i in p["images"]) or "—"
            cells = [f"{a['number']:02d}", a["name"], ", ".join(f"{v:.3f}" for v in a["bbox_lonlat"]),
                     f"{a['centroid_lonlat'][0]:.3f}/{a['centroid_lonlat'][1]:.3f}",
                     f"{a['size_km_utm34'][0]}×{a['size_km_utm34'][1]}"] if first else ["", "", "", "", ""]
            cells += [p["label"], str(p["id"]), p["statusCode"] or "?", "yes" if p["released"] else "no",
                      p["expectedDelivery"] or "—", p["deliveryTime"] or "—", img]
            L.append("| " + " | ".join(cells) + " |")
            first = False
    (args.out_dir / f"ems_snapshot_{tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nmanifest: {mpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
