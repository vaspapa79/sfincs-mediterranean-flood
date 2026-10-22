"""CODE-20 B3 (response letter only) — the EMSR773 areas nested in AOI01 (Valencia province), the three nested areas that carry a
DEL product (Horta Sud, Algemesí, Yatova), the observed-flood area of those products, and whether the province-level AOI01
delineations (DEL_PRODUCT of 31 Oct 2024; DEL_MONIT01 of 3 Nov 2024 = the truth used in scoring) cover the same polygons.

Geometry only: polygon areas and overlaps in the model CRS (EPSG:32630); no model output is read and nothing is re-scored.
Inputs: the EMS API snapshot and the AOI record of CODE-19 (code19/ems_api_snapshot_EMSR773_*.json, code19/a4_emsr773_aois.json),
the observedEventA GeoJSON layers of the products as served by the EMS viewer (downloaded to --geojson-dir; each file is
recorded with URL, SHA-256 and size), and the run's cached AOI01 DEL_MONIT01 shapefile (cross-check of the GeoJSON copy).
Writes reproduction/v14_rerun/code20/b3_emsr773_nested.json.

Usage (sfincs-viz env): python -I code20_b3_emsr773_nested.py --repo <worktree> --geojson-dir <dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import sys
from pathlib import Path

EPSG = 32630
S3 = "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com"
LAYERS = {  # product -> (AOI number, folder, layer stem)
    "AOI03 DEL_PRODUCT (Horta Sud)": (3, "DEL_PRODUCT", "EMSR773_AOI03_DEL_PRODUCT_observedEventA_v1"),
    "AOI04 DEL_PRODUCT (Algemesi)": (4, "DEL_PRODUCT", "EMSR773_AOI04_DEL_PRODUCT_observedEventA_v1"),
    "AOI11 DEL_PRODUCT (Yatova)": (11, "DEL_PRODUCT", "EMSR773_AOI11_DEL_PRODUCT_observedEventA_v1"),
    "AOI01 DEL_PRODUCT": (1, "DEL_PRODUCT", "EMSR773_AOI01_DEL_PRODUCT_observedEventA_v1"),
    "AOI01 DEL_MONIT01 (truth used)": (1, "DEL_MONIT01", "EMSR773_AOI01_DEL_MONIT01_observedEventA_v1"),
}
NESTED_DEL = {3: "AOI03 DEL_PRODUCT (Horta Sud)", 4: "AOI04 DEL_PRODUCT (Algemesi)", 11: "AOI11 DEL_PRODUCT (Yatova)"}


def covered_fraction(poly, other) -> float:
    """Fraction of poly's area that lies inside other (0 when either is missing or poly has no area)."""
    if poly is None or other is None or poly.is_empty or poly.area <= 0:
        return 0.0
    return float(poly.intersection(other).area / poly.area)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def valid(g):
    from shapely.validation import make_valid
    return g if g.is_valid else make_valid(g)


def union(geoms):
    from shapely.ops import unary_union
    return unary_union([valid(g) for g in geoms if g is not None and not g.is_empty])


def load_obs(path: Path):
    import geopandas as gpd
    g = gpd.read_file(path).to_crs(EPSG)
    if "notation" not in g.columns:
        g["notation"] = "—"
    return g


def by_notation(g) -> dict:
    out = {}
    for nt, sub in g.groupby(g["notation"].fillna("—")):
        u = union(list(sub.geometry))
        out[str(nt)] = {"features": int(len(sub)), "km2": round(u.area / 1e6, 3), "_geom": u}
    tot = union(list(g.geometry))
    out["all"] = {"features": int(len(g)), "km2": round(tot.area / 1e6, 3), "_geom": tot}
    return out


def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if not k.startswith("_")}
    if isinstance(d, list):
        return [strip(x) for x in d]
    return d


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import pyproj
    from shapely import wkt
    from shapely.ops import transform as shp_transform
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--geojson-dir", required=True, type=Path)
    ap.add_argument("--run-dir", type=Path, default=Path("D:/ELKAK/implementation/v14/valencia_enhanced_164_v142"))
    a = ap.parse_args()
    repo = a.repo.resolve()
    c19 = repo / "reproduction" / "v14_rerun" / "code19"
    out_dir = repo / "reproduction" / "v14_rerun" / "code20"
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_path = sorted(c19.glob("ems_api_snapshot_EMSR773_*.json"))[-1]
    snap = json.loads(snap_path.read_text(encoding="utf-8"))["results"][0]
    a4_path = c19 / "a4_emsr773_aois.json"
    a4 = json.loads(a4_path.read_text(encoding="utf-8"))
    active = {r["number"]: r["active_cells_inside"] for r in a4["aois"]}
    to_utm = pyproj.Transformer.from_crs(4326, EPSG, always_xy=True).transform
    ext = {x["number"]: shp_transform(to_utm, wkt.loads(x["extent"])) for x in snap["aois"]}
    names = {x["number"]: x["name"] for x in snap["aois"]}
    a01 = ext[1]
    # 1. nesting (AOI extents inside the AOI01 extent) and the domain
    aois = []
    for x in snap["aois"]:
        n = x["number"]
        if n == 1:
            continue
        frac = covered_fraction(ext[n], a01)
        aois.append({"number": n, "name": x["name"], "extent_km2": round(ext[n].area / 1e6, 1), "inside_aoi01_fraction": round(frac, 4), "nested": frac >= 0.999,
                     "active_cells_in_domain": active.get(n, 0), "product_types": [p["type"] for p in x["products"]],
                     "del_products": [{"id": p["id"], "version": (p.get("version") or {}).get("number"), "status": (p.get("version") or {}).get("statusCode"),
                                       "delivery": (p.get("version") or {}).get("deliveryTime"), "monitoring_number": p.get("monitoringNumber"),
                                       "images": [(i["sensorName"], i["acquisitionTime"]) for i in p.get("images", [])],
                                       "stats_ha": {k: v["None"]["total"] for k, v in (p.get("stats") or {}).items() if "None" in v and "lood" in k},
                                       "download": p.get("downloadPath")} for p in x["products"] if p["type"] == "DEL"]})
    nested = [r for r in aois if r["nested"]]
    nested_dom = [r for r in nested if r["active_cells_in_domain"] > 0]
    nested_del = [r for r in nested if r["del_products"]]
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code20_b3_emsr773_nested.py",
           "scope": "geometry only (polygon areas and overlaps in EPSG:32630); no model output read, nothing re-scored",
           "inputs": {"ems_api_snapshot": {"file": snap_path.relative_to(repo).as_posix(), "sha256": sha256(snap_path)},
                      "a4_record": {"file": a4_path.relative_to(repo).as_posix(), "sha256": sha256(a4_path)}},
           "aoi01": {"name": names[1], "extent_km2": round(a01.area / 1e6, 1)},
           "counts": {"aois_total": len(snap["aois"]), "nested_in_aoi01_by_extent": len(nested), "nested_and_in_model_domain": len(nested_dom),
                      "nested_with_del_product": [f"AOI{r['number']:02d} {r['name']}" for r in nested_del],
                      "nested_with_del_product_in_domain": [f"AOI{r['number']:02d} {r['name']}" for r in nested_del if r["active_cells_in_domain"] > 0],
                      "nested_with_del_product_outside_domain": [f"AOI{r['number']:02d} {r['name']}" for r in nested_del if r["active_cells_in_domain"] == 0]},
           "aois": aois}
    # 2. the observedEventA layers
    layers = {}
    for key, (n, folder, stem) in LAYERS.items():
        p = a.geojson_dir / f"{stem}.json"
        if not p.exists():
            layers[key] = {"present": False}
            continue
        g = load_obs(p)
        bn = by_notation(g)
        layers[key] = {"present": True, "aoi": n, "url": f"{S3}/EMSR773/AOI{n:02d}/{folder}/{stem}.json", "file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size,
                       "fetched_utc": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "crs_of_file": str(g.crs), "by_notation": bn,
                       "attribute_values": {c: sorted({str(v) for v in g[c].dropna().unique()})[:12] for c in ("event_type", "obj_desc", "det_method", "notation") if c in g.columns}}
    # cross-check: the run's cached AOI01 DEL_MONIT01 shapefile against the GeoJSON copy
    shp = sorted(glob.glob(str(a.run_dir / "data" / "ems_polygons" / "EMSR773_AOI01_DEL_MONIT01_v1" / "*observedEventA*.shp")))
    if shp and layers["AOI01 DEL_MONIT01 (truth used)"].get("present"):
        gs = load_obs(Path(shp[0]))
        tot = union(list(gs.geometry)).area / 1e6
        gj = layers["AOI01 DEL_MONIT01 (truth used)"]["by_notation"]["all"]["km2"]
        rec["monit01_crosscheck"] = {"cached_shapefile": Path(shp[0]).as_posix(), "features": int(len(gs)), "union_km2": round(tot, 3), "geojson_union_km2": gj,
                                     "identical_to_3dp": abs(tot - gj) < 0.0015}
    # 3. coverage of the nested products by the AOI01 delineations (and the reverse, inside each nested extent)
    refs = {k: layers[k] for k in ("AOI01 DEL_PRODUCT", "AOI01 DEL_MONIT01 (truth used)") if layers[k].get("present")}
    both = union([v["by_notation"]["all"]["_geom"] for v in refs.values()]) if refs else None
    cov = {}
    for n, key in NESTED_DEL.items():
        L = layers.get(key)
        if not L or not L.get("present"):
            continue
        e = ext[n]
        row = {"aoi": f"AOI{n:02d} {names[n]}", "extent_km2": round(e.area / 1e6, 1), "observed_km2": {k: v["km2"] for k, v in L["by_notation"].items()},
               "api_stats_ha": next((r["del_products"][0]["stats_ha"] for r in aois if r["number"] == n), None), "covered_by": {}}
        for rk, R in list(refs.items()) + ([("union of both AOI01 delineations", {"by_notation": {"all": {"_geom": both}}})] if both is not None else []):
            A = R["by_notation"]["all"]["_geom"]
            A_in = A.intersection(e)
            fl = L["by_notation"].get("Flooded area", {}).get("_geom")
            row["covered_by"][rk] = {"fraction_of_product_all_inside_aoi01_delineation": round(covered_fraction(L["by_notation"]["all"]["_geom"], A), 4),
                                     "fraction_of_product_flooded_area_inside_aoi01_delineation": round(covered_fraction(fl, A), 4) if fl is not None else None,
                                     "aoi01_observed_km2_inside_this_extent": round(A_in.area / 1e6, 3),
                                     "fraction_of_aoi01_observed_inside_extent_covered_by_product": round(covered_fraction(A_in, L["by_notation"]["all"]["_geom"]), 4),
                                     "intersection_km2": round(L["by_notation"]["all"]["_geom"].intersection(A).area / 1e6, 3)}
        cov[key] = row
    rec["layers"] = strip(layers)
    rec["coverage"] = strip(cov)
    out = out_dir / "b3_emsr773_nested.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"counts": rec["counts"], "coverage": rec["coverage"], "monit01_crosscheck": rec.get("monit01_crosscheck")}, indent=1, ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
