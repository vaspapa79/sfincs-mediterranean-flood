"""Stage 5a (GO Phases 3-5, 2026-10-19): freeze the final EMSR933 truth set from the post-closure EMS API snapshot.
Reads the products CSV written by ems_package_metadata.py for the new snapshot and the one of the provisional cut-off,
assigns the rule_ledger.md section 8 scoring tiers, states which packages enter the validator's truth (its product
preference: every released delineation package of an AOI; a grading package only where no delineation exists), and
writes STAGE5_TRUTH_FREEZE.md + stage5_truth_freeze.json. Nothing is retyped: every value comes from the CSVs/manifest.
Usage: python -I stage5_truth_freeze.py --new <products.csv> --old <products.csv> --manifest <manifest.json> --out-dir <reproduction/emsr933>
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path

TIER2 = "post-event optical trace -> observed vs modelled km2 at h > 0.10 m only"
TIER3 = "no product released -> excluded"
TIERS = {"03": ("1", "near-peak SAR delineation -> scored (CSI/HR/FAR/B/GSS at h > 0.10 m, sweeps, CSI*/B*); the only headline"),
         "01": ("2", TIER2), "04": ("2", TIER2), "06": ("2", TIER2), "07": ("2", TIER2),
         "02": ("3", TIER3), "05": ("3", TIER3), "08": ("3", TIER3)}


def change_since(oldk: dict, r: dict) -> str:
    o = oldk.get((r["aoi"], r["product"]))
    if o is None:
        return "new"
    if o["status"] != r["status"]:
        return f"status {o['status']} -> {r['status']}"
    if o["zip_sha256"] != r["zip_sha256"]:
        return "zip changed"
    return "unchanged"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True, type=Path)
    ap.add_argument("--old", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    new = list(csv.DictReader(open(a.new, encoding="utf-8")))
    old = list(csv.DictReader(open(a.old, encoding="utf-8")))
    man = json.loads(a.manifest.read_text(encoding="utf-8"))
    oldk = {(r["aoi"], r["product"]): r for r in old}
    rel = [r for r in new if r["released"] == "True"]
    by_aoi: dict[str, list[dict]] = {}
    for r in rel:
        by_aoi.setdefault(r["aoi"], []).append(r)
    truth = []
    for aoi, rows in by_aoi.items():
        dels = [r for r in rows if r["product"].startswith("DEL")]
        for r in rows:
            is_del = r["product"].startswith("DEL")
            enters = (is_del if dels else True) and TIERS[aoi][0] != "3"
            reason = "delineation package" if is_del else ("grading dropped: a delineation exists for this AOI" if dels else "grading (no delineation)")
            truth.append({"aoi": aoi, "aoi_name": r["aoi_name"], "product": r["product"], "product_id": r["product_id"], "tier": TIERS[aoi][0],
                          "enters_scored_truth": enters, "reason": reason, "post_sensor": r["post_sensor"], "post_acq_utc": r["post_acq_utc"],
                          "pre_ref": r["pre_ref"], "delivered": r["delivered"], "obs_km2_union": r["obs_km2_union"],
                          "obs_km2_by_notation": r["obs_km2_by_notation"], "not_analysed_km2": r["not_analysed_km2"], "aoi_km2": r["aoi_km2"],
                          "zip_sha256": r["zip_sha256"], "zip_bytes": r["zip_bytes"], "change_since_cutoff": change_since(oldk, r)})
    truth.sort(key=lambda t: (t["aoi"], t["product"]))
    act = man["activation"]
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "snapshot_utc": man["snapshot_utc"], "api_url": man["api_url"],
           "raw_json_sha256": man["raw_json_sha256"], "activation_closed": act.get("closed"), "activation_time": act.get("activationTime"),
           "event_time": act.get("eventTime"), "provisional_cutoff_csv": str(a.old), "final_csv": str(a.new), "released_packages": len(rel),
           "api_rows": len(new), "aois_without_product": sorted({r["aoi"] for r in new} - set(by_aoi)), "extracted_dir": man.get("extracted_dir"),
           "packages": truth, "tier_rule": "rule_ledger.md section 8 item 3 (written 2026-10-19T09:12:53Z, before any Crete run)",
           "truth_dir_for_runs": "D:/ELKAK/implementation/emsr933_crete/data/ems_polygons (copy of the extracted packages; junctioned into every Crete run dir)"}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "stage5_truth_freeze.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    snap_tag = man["snapshot_utc"].replace("-", "").replace(":", "")
    tier1 = " + ".join(f"{t['product']} ({t['post_sensor']})" for t in truth if t["aoi"] == "03" and t["enters_scored_truth"])
    L = [f"# EMSR933 - Stage 5a: final truth set frozen from the post-closure EMS API snapshot ({man['snapshot_utc']})", "",
         f"Generated {rec['utc']} by `scripts/stage5_truth_freeze.py` from `{a.new.name}` (vs the provisional cut-off `{a.old.name}`) and the snapshot "
         f"manifest (raw API JSON sha256 `{man['raw_json_sha256'][:16]}...`). Activation closed: **{act.get('closed')}**. Released packages: **{len(rel)}** "
         f"of {len(new)} API rows; AOIs without any released product: {', '.join(rec['aois_without_product'])}. Tiers: rule_ledger.md section 8 item 3.", "",
         "| AOI | product | id | tier | enters scored truth | post-event image (acquisition UTC) | obs km2 (union) | notAnalysed km2 | AOI km2 | zip sha256 | since 9 Oct cut-off |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in truth:
        enters = "yes" if t["enters_scored_truth"] else ("no - " + t["reason"])
        L.append(f"| {t['aoi']} {t['aoi_name']} | {t['product']} | {t['product_id']} | {t['tier']} | {enters} | {t['post_sensor']} | "
                 f"{t['obs_km2_union']} | {t['not_analysed_km2']} | {t['aoi_km2']} | `{t['zip_sha256'][:12]}` | {t['change_since_cutoff']} |")
    L += ["",
          "Tier 1 (scored) = AOI03 Tzermiado: the validator unions every released delineation package of the AOI (`_select_obs_shps`, "
          f"`include_del_product: true`): {tier1}; the grading package released after the cut-off is dropped by the delineation-first rule "
          "(kept on disk; its acquisition is listed for the time-matched diagnostic).",
          "Tier 2 (km2 only) = AOIs 01, 04, 06, 07 (one optical DEL_MONIT01 each). Tier 3 (excluded) = AOIs 02, 05, 08 (every product "
          "'N - remote sensing limitations'). No all-AOI union score.",
          f"Files: `stage5_truth_freeze.json`, `{a.new.name}`, `{a.new.with_suffix('.md').name}`, `ems_snapshot_{snap_tag}_manifest.json`; "
          f"packages extracted under `{man.get('extracted_dir')}`."]
    (a.out_dir / "STAGE5_TRUTH_FREEZE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
