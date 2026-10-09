"""CODE-10 Stage 0b — per-product metadata table from a downloaded EMS snapshot.

Reads <out-dir>/ems_snapshot_<tag>_manifest.json and, for every released package, the
in-package `source_v1` table (gpkg) and the observedEventA / notAnalysedA / areaOfInterestA
layers. Writes <out-dir>/ems_snapshot_<tag>_products.{csv,md}. Areas in EPSG:32634 (km2).

Usage: python -I ems_package_metadata.py --manifest <out-dir>/ems_snapshot_<tag>_manifest.json
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
UTM = 32634


def layer_area(gpkg: Path, layer: str):
    import geopandas as gpd
    import pyogrio
    if layer not in [l[0] for l in pyogrio.list_layers(gpkg)]:
        return None, None
    g = gpd.read_file(gpkg, layer=layer)
    if g.empty:
        return g, 0.0
    gu = g.to_crs(epsg=UTM)
    return gu, float(gu.union_all().area) / 1e6


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    args = ap.parse_args()
    import pyogrio
    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    tag = args.manifest.name.replace("ems_snapshot_", "").replace("_manifest.json", "")
    t_event = dt.datetime.fromisoformat(m["activation"]["eventTime"])
    xroot = Path(m["extracted_dir"])
    rows = []
    for a in m["aois"]:
        for p in a["products"]:
            base = {"aoi": f"{a['number']:02d}", "aoi_name": a["name"], "product": p["label"],
                    "product_id": p["id"], "status": p["statusCode"], "released": p["released"],
                    "expected": p["expectedDelivery"] or "", "delivered": p["deliveryTime"] or "",
                    "reason": p["reason"] or ""}
            if not p["released"]:
                im = p["images"][0] if p["images"] else {}
                rows.append({**base, "post_sensor": im.get("sensorName", ""),
                             "post_acq_utc": im.get("acquisitionTime", ""), "source": "API images[] (no package)"})
                continue
            stem = p["download"]["stem"]
            gp = next((xroot / stem).rglob("*.gpkg"))
            src = pyogrio.read_dataframe(gp, layer="source_v1", read_geometry=False)
            obs, obs_km2 = layer_area(gp, "observedEventA_v1")
            _, na_km2 = layer_area(gp, "notAnalysedA_v1")
            _, aoi_km2 = layer_area(gp, "areaOfInterestA_v1")
            dmg_ids = sorted({str(v) for v in obs["dmg_src_id"].dropna()}) if obs is not None else []
            post = src[src["src_id"].astype(str).isin(dmg_ids)]
            pre = src[(src["eventphase"] == "Pre-event") & src["sensor_res"].ne("Not Applicable")
                      & ~src["source_nam"].isin(["Open Street Map", "CLC", "FABDEM"])]
            post_s = "; ".join(f"{r.source_nam} {r.src_date} {r.source_tm} ({r.sensor_res})" for r in post.itertuples())
            pre_s = "; ".join(f"{r.source_nam} {r.src_date} ({r.sensor_res})" for r in pre.itertuples())
            # acquisition datetime of the (first) post-event source -> lag after EMS eventTime
            lag_h = ""
            if len(post):
                r = post.iloc[0]
                d = dt.datetime.strptime(f"{r.src_date}{r.source_tm}", "%d/%m/%Y" + "T%H:%M:%SZ")
                lag_h = round((d - t_event).total_seconds() / 3600, 1)
            by_not = {}
            if obs is not None and len(obs):
                for key, grp in obs.groupby(obs["notation"].fillna("?")):
                    by_not[key] = round(float(grp.union_all().area) / 1e6, 4)
            mm = ""
            if obs is not None and "event_type" in obs:
                mm = ", ".join(sorted({str(v) for v in obs["event_type"].dropna()}))
            files = [f["path"] for f in p["inventory"]["files"]]
            rows.append({**base,
                         "post_sensor": post_s, "post_acq_utc": "", "pre_ref": pre_s,
                         "lag_from_eventTime_h": lag_h,
                         "obs_polygons": 0 if obs is None else len(obs),
                         "obs_km2_union": round(obs_km2, 4) if obs_km2 is not None else "",
                         "obs_km2_by_notation": json.dumps(by_not, ensure_ascii=False),
                         "obs_event_types": mm,
                         "obs_det_methods": ", ".join(sorted({str(v) for v in obs["det_method"].dropna()})) if obs is not None else "",
                         "not_analysed_km2": round(na_km2, 3) if na_km2 is not None else 0.0,
                         "aoi_km2": round(aoi_km2, 2) if aoi_km2 is not None else "",
                         "other_layers": ", ".join(sorted({Path(f).stem.split("_")[-2] for f in files
                                                           if f.endswith(".shp")} - {"observedEventA", "areaOfInterestA"})),
                         "zip_sha256": p["download"]["zip_sha256"], "zip_bytes": p["download"]["zip_bytes"],
                         "source": f"package {stem}.gpkg:source_v1"})
    cols = ["aoi", "aoi_name", "product", "product_id", "status", "released", "expected", "delivered",
            "reason", "post_sensor", "post_acq_utc", "pre_ref", "lag_from_eventTime_h", "obs_polygons",
            "obs_km2_union", "obs_km2_by_notation", "obs_event_types", "obs_det_methods",
            "not_analysed_km2", "aoi_km2", "other_layers", "zip_bytes", "zip_sha256", "source"]
    out_csv = args.manifest.parent / f"ems_snapshot_{tag}_products.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    md = [f"# EMSR933 released-product metadata (snapshot {m['snapshot_utc']})", "",
          f"EMS eventTime {m['activation']['eventTime']} UTC; lag = post-event acquisition − eventTime. "
          "Areas: union in EPSG:32634. Source of sensor/date: the package's own `source_v1` table "
          "(matched by observedEventA.dmg_src_id); identical to the API `images[]` record.", "",
          "| AOI | product | id | post-event source (date, time, res.) | lag h | obs polygons | obs km² | by notation (km²) | event types | not-analysed km² | AOI km² | other layers |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r["released"]:
            continue
        md.append(f"| {r['aoi']} {r['aoi_name']} | {r['product']} | {r['product_id']} | {r['post_sensor']} | "
                  f"{r['lag_from_eventTime_h']} | {r['obs_polygons']} | {r['obs_km2_union']} | "
                  f"{r['obs_km2_by_notation']} | {r['obs_event_types']} | {r['not_analysed_km2']} | "
                  f"{r['aoi_km2']} | {r['other_layers']} |")
    md += ["", "Not released at the snapshot:", ""]
    for r in rows:
        if not r["released"]:
            md.append(f"- AOI{r['aoi']} {r['aoi_name']} {r['product']} (id {r['product_id']}): status {r['status']}"
                      f"{' — ' + r['reason'] if r['reason'] else ''}"
                      f"{'; expected ' + r['expected'] if r['expected'] else ''}; image {r['post_sensor']} "
                      f"{r['post_acq_utc']}")
    out_md = args.manifest.parent / f"ems_snapshot_{tag}_products.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\n-> {out_csv}\n-> {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
