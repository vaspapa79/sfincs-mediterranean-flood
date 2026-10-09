"""CODE-10 Stage 0 — assemble the human-readable availability summary and the AUDIT.md block
straight from the Stage-0 JSON records (no hand-typed numbers).

Usage: python -I stage0_summary.py --dir <worktree>/reproduction/emsr933 --commit <hash>
Writes <dir>/data_availability_summary.md and, with --audit-out, the paste-ready
docs/AUDIT.md block (generated after the stage commit so it can cite the hash).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def latest(d: Path, pat: str) -> Path:
    c = sorted(d.glob(pat))
    if not c:
        sys.exit(f"missing {pat} in {d}")
    return c[-1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--commit", default="<commit>")
    ap.add_argument("--audit-out", type=Path, default=None, help="write the AUDIT.md block here")
    a = ap.parse_args()
    d = a.dir
    av_p = latest(d, "data_availability_2*.json")
    pr_p = latest(d, "era5t_probe_2*.json")
    mf_p = latest(d, "ems_snapshot_*_manifest.json")
    pc_p = latest(d, "ems_snapshot_*_products.csv")
    pf_p = d / "preflight_stage0.json"
    av, pr, mf, pf = (json.loads(p.read_text(encoding="utf-8")) for p in (av_p, pr_p, mf_p, pf_p))
    prods = list(csv.DictReader(pc_p.open(encoding="utf-8")))

    il, ifn = av["imerg_late"], av["imerg_final"]
    e5 = av["era5"]
    gl = av["glofas"]
    era5_days = [f"2026-09-{x}" for x in (e5.get("constraints_2026-09_days") or []) if x >= "27"] + \
                [f"2026-10-{x}" for x in (e5.get("constraints_2026-10_days") or []) if x <= "07"]
    win = [f"2026-09-{x}" for x in ("27", "28", "29", "30")] + [f"2026-10-0{x}" for x in range(1, 8)]
    missing_era5 = [x for x in win if x not in era5_days]
    g4i = [f"2026-09-{x}" for x in (gl.get("version_4_0_intermediate_2026-09_days") or []) if x >= "27"] + \
          [f"2026-10-{x}" for x in (gl.get("version_4_0_intermediate_2026-10_days") or []) if x <= "07"]
    exp = pr["per_day_expver"]

    L = [f"# EMSR933 input-data availability — window {av['window'][0]} … {av['window'][1]}", "",
         f"Checked {av['checked_utc']} (`{av_p.name}`); ERA5T probe `{pr_p.name}`. bbox W,S,E,N = {av['bbox_WSEN']}.", "",
         "| input | product | status for the window | evidence |", "|---|---|---|---|",
         f"| precipitation (R1) | IMERG **Late** Run V07 half-hourly `GPM_3IMERGHHL` | {il['n_granules']}/{il['expected_full_window']} granules; "
         f"suffix {', '.join(il['version_suffixes'])}; per day {sorted(set(il['per_day'].values()))} | CMR search; first `{il['first'].split(':')[-1]}` |",
         f"| precipitation (R1) | IMERG **Final** Run V07 `GPM_3IMERGHH` | {ifn['n_granules']}/{ifn['expected_full_window']} granules | CMR search |",
         f"| meteo (baseline rain, R6 wind/MSLP) | ERA5 single levels (CDS) | requestable {era5_days[0]} … {era5_days[-1]}; **not yet: {', '.join(missing_era5) or 'none'}**; "
         f"catalogue extent end {e5['catalogue_temporal_extent'][0][1]} | CDS constraints + catalogue |",
         f"| ERA5 vs ERA5T | expver per day | " + "; ".join(f"{k}: {'/'.join(v)}" for k, v in exp.items()) + " | one-point retrieval |",
         f"| upstream Q (R3, if triggered) | GloFAS v4 `intermediate` (EWDS) | {g4i[0]} … {g4i[-1]} | EWDS constraints |",
         f"| | GloFAS v4 `consolidated` / v5 | none for Sep–Oct 2026 | EWDS constraints |",
         f"| | pipeline request vocabulary (`hyear/hmonth`) | {gl['pipeline_vocabulary_hyear_hmonth'][:40]}… | EWDS constraints |",
         f"| DEM | Copernicus GLO-30 (AWS) | " + ", ".join(f"{t['tile'][22:25]}{t['tile'][29:33]}:{t['http']}" for t in av['copdem_glo30']) + " | HTTP HEAD |",
         f"| land cover | ESA WorldCover 2021 v200 (AWS) | " + ", ".join(f"{t['tile'][-12:-4]}:{t['http']}" for t in av['worldcover_2021_v200']) + " | HTTP HEAD |",
         ""]
    (d / "data_availability_summary.md").write_text("\n".join(L), encoding="utf-8")

    act = mf["activation"]
    rel = [p for p in prods if p["released"] == "True"]
    B = [f"### EMSR933 Crete — Stage 0 provenance (CODE-10, prospective held-out event)",
         f"Branch `emsr933-crete` (worktree `.worktrees/emsr933-crete`, base v1.3.0 `ccd423a`), commit `{a.commit}`. "
         f"Records in `reproduction/emsr933/`.",
         f"- EMS API snapshot **{mf['snapshot_utc']}** = provisional truth cut-off: `{mf['raw_json']}` "
         f"({mf['raw_json_bytes']} B, sha256 `{mf['raw_json_sha256']}`); API `{mf['api_url']}`.",
         f"- Activation (from snapshot JSON): eventTime `{act['eventTime']}` UTC, activationTime `{act['activationTime']}` UTC, "
         f"{act['category']}/{act['subCategory']}, closed={act['closed']}.",
         f"- Released packages at the cut-off ({len(rel)}; product id · post-event source per package `source_v1` · observed km² union EPSG:32634):"]
    for p in rel:
        B.append(f"  - AOI{p['aoi']} {p['aoi_name']} {p['product']} id {p['product_id']} · {p['post_sensor']} · "
                 f"obs {p['obs_km2_union']} km² ({p['obs_polygons']} polys; {p['obs_km2_by_notation']}) · zip sha256 `{p['zip_sha256'][:16]}…`")
    B.append(f"  - Not released: " + "; ".join(f"AOI{p['aoi']} {p['product']} {p['status']}" for p in prods if p["released"] != "True"))
    B.append(f"- Availability ({av['checked_utc']}): IMERG Late V07 {il['n_granules']}/{il['expected_full_window']} "
             f"({', '.join(il['version_suffixes'])}); IMERG Final {ifn['n_granules']}; ERA5 requestable to {era5_days[-1]} "
             f"(ERA5T per probe: " + ", ".join(f"{k}={'/'.join(v)}" for k, v in exp.items()) + f"); GloFAS v4 intermediate to {g4i[-1]}.")
    B.append(f"- Preflight {pf['utc']}: " + ("OK" if not pf["fails"] else "FAILED " + ", ".join(pf["fails"])) +
             f" (hydromt {pf['versions'].get('hydromt')}, hydromt_sfincs {pf['versions'].get('hydromt_sfincs')}, "
             f"numpy {pf['versions'].get('numpy')}, GDAL {pf['versions'].get('GDAL(rasterio)')}).")
    if a.audit_out:
        a.audit_out.write_text("\n".join(B) + "\n", encoding="utf-8")
    print("\n".join(L)); print(); print("\n".join(B))
    return 0


if __name__ == "__main__":
    sys.exit(main())
