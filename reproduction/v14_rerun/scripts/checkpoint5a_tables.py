"""Checkpoint 5a (GO Phases 3-5, 2026-10-19) — one table per Phase-3 group from the JSON records; nothing retyped.

Groups: a Table-12 ablations, b S2 Strymonas v1 (pre-fix source), c R2 anchor sweeps, d the eight C2 runs + the two
Pineios audit rows, e the Strymonas lead-in sensitivity. Four-column format where a published number exists
(v1.3 as published | v1.3 rescored with the new mask | v1.4 (+D6) new mask | delta); where only a manuscript sentence
exists the "published" column quotes it and the rescored column is empty (no output survives).
Usage: python -I checkpoint5a_tables.py --repo <worktree> [--audit-out docs/AUDIT.md] [--tests "..."]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

METRICS = [("csi", "CSI", 3), ("hr", "HR", 3), ("far", "FAR", 3), ("bias", "B", 2), ("gss", "GSS", 3)]
GROUPS = [("a", "Table 12 ablations (Strymonas; CN on rows under D6)", ["strymonas_abl_cnoff_q", "strymonas_abl_qoff_cn"]),
          ("b", "S2 variant: Strymonas v1, pre-audit Kerkini source", ["strymonas_v1_prefix_src"]),
          ("c", "R2 anchor sweeps", ["mandra_r2_95", "mandra_r2_140", "mandra_r2_255", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510"]),
          ("d", "The eight C2 runs (relabelled curve numbers) and the Pineios audit rows", ["mandra_cn_a15", "mandra_cn_a58", "mandra_cn_b_default", "mandra_cn_d_amc3", "mandra_cn_d_amc3_manning080",
                                                                                           "pineios_cn_on", "pineios_raw_imerg", "valencia_raw_imerg", "pineios_timevarying_q", "pineios_qinf5"]),
          ("e", "Strymonas lead-in sensitivity (7 forcing days simulated)", ["strymonas_leadin7d"])]
CANON = {"strymonas": "strymonas_enhanced_postD6", "mandra": "mandra_enhanced", "pineios": "pineios_enhanced", "valencia": "valencia_enhanced_164"}


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def strict(v):
    return v["validation"]["strict_threshold_sweep"]["h>0.10m"]


def fz(v):
    return v["validation"]["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"]


def f(x, nd):
    return "—" if x is None else f"{x:.{nd}f}"


def wet_km2(v):
    s = strict(v); A = v["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
    return (s["tp"] + s["fp"]) * A


def aoi_tp(v, token):
    for a in v["validation"]["per_aoi_canonical_and_r1"]:
        if token in a["aoi_file"]:
            return a["strict"]["tp"], a["strict"]["csi"]
    return None, None


def factor_from_log(work: Path):
    lf = work / "pipeline_v14.log"
    if not lf.exists():
        return None
    m = re.findall(r"scaling factor = ([0-9.]+)x", lf.read_text(errors="replace"))
    return float(m[-1]) if m else None


def run_rows(res: Path, run: str, rec: dict):
    """One row block for a run: returns (header, rows, summary)."""
    v14 = J(res / f"{run}_v14_newmask.json")
    v13p = J(res / f"{run}_v13_publishedmask.json"); v13n = J(res / f"{run}_v13_newmask.json")
    ps = rec.get("published_strict")
    rows = []
    if not v14:
        return ["| metric | | | v1.4 | |", "|---|---|---|---|---|"], [f"| {run} | run not finished | | | |"], None
    c = strict(v14)
    if v13p and v13n:
        a, b = strict(v13p), strict(v13n)
        for key, name, nd in METRICS:
            rows.append(f"| {name} | {a[key]:.{nd}f} | {b[key]:.{nd}f} | **{c[key]:.{nd}f}** | {c[key] - a[key]:+.{nd}f} (mask {b[key] - a[key]:+.{nd}f}) |")
        rows.append(f"| TP / FP / FN | {a['tp']} / {a['fp']} / {a['fn']} | {b['tp']} / {b['fp']} / {b['fn']} | {c['tp']} / {c['fp']} / {c['fn']} | |")
        rows.append(f"| fuzzy r=1 CSI | {fz(v13p):.3f} | {fz(v13n):.3f} | {fz(v14):.3f} | {fz(v14) - fz(v13p):+.3f} |")
        rows.append(f"| modelled wet in eval km² | {wet_km2(v13p):.1f} | {wet_km2(v13n):.1f} | {wet_km2(v14):.1f} | |")
        pc = rec.get("published_record_check") or {}
        rows.append(f"| published record reproduced | {pc.get('identical_tp_fp_fn_tn')} ({Path(str(pc.get('published_json', ''))).name}) | | | |")
        return (["| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |", "|---|---|---|---|---|"], rows,
                {"pub": a, "mask": b, "v14": c})
    if ps:                                     # published numbers exist (CSV / S1 JSON) but no output survives to rescore
        for key, name, nd in METRICS:
            if key in ps:
                rows.append(f"| {name} | {ps[key]:.{nd}f} | — (no output survives) | **{c[key]:.{nd}f}** | {c[key] - ps[key]:+.{nd}f} |")
        rows.append(f"| TP / FP / FN | {ps.get('tp', '—')} / {ps.get('fp', '—')} / {ps.get('fn', '—')} | | {c['tp']} / {c['fp']} / {c['fn']} | |")
        rows.append(f"| modelled wet in eval km² | | | {wet_km2(v14):.1f} | |")
        return (["| metric | published (" + Path(str(ps.get("_source", ""))).name + ") | v1.3 rescored, new mask | v1.4, new mask | Δ |", "|---|---|---|---|---|"], rows, {"pub": ps, "v14": c})
    for key, name, nd in METRICS:
        rows.append(f"| {name} | | | **{c[key]:.{nd}f}** | |")
    rows.append(f"| TP / FP / FN | | | {c['tp']} / {c['fp']} / {c['fn']} | |")
    rows.append(f"| modelled wet in eval km² | | | {wet_km2(v14):.1f} | |")
    return (["| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |", "|---|---|---|---|---|"], rows, {"v14": c})


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--audit-out", type=Path)
    ap.add_argument("--tests", default="")
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = ["# Checkpoint 5a — Phase 3 under harness v1.4 (+ D6 where curve numbers are on): ablations, S2 variant, R2 sweeps, the eight C2 runs, Pineios audit rows, lead-in sensitivity", "",
         f"Generated {now} by `checkpoint5a_tables.py` from `reproduction/v14_rerun/results/*.json`. Scores at h > 0.10 m, strict; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. "
         "Run configs: `configs/<run>.yaml` (= the committed example + harness_version v1.4 + the overrides stated in each header).", ""]
    audit = [f"### GO Phases 3–5 — Phase 3 records; block generated {now} by `reproduction/v14_rerun/scripts/checkpoint5a_tables.py`", "",
             "**Decisions (Papaioannou, 2026-10-19, GO Phases 3–5):** Checkpoint 4b accepted, D6 closed, the Strymonas v1.4 + D6 row is canonical; Phase 3 a–e, Phase 4 a–e, Phase 5 a–d, then AUDIT consolidation, tag v1.4.0, Checkpoint 5b. Standing: new defect → report only; v1.3 beside v1.4; numbers only from JSON.", ""]
    canon = {ev: J(res / f"{run}_v14_newmask.json") for ev, run in CANON.items()}
    for gid, title, runs in GROUPS:
        L += [f"## Group {gid} — {title}", ""]
        for run in runs:
            rec = J(res / f"{run}_record.json")
            if not rec or not rec.get("end_utc"):
                L += [f"### {run}", "", "pending (run not finished)", ""]; continue
            L += [f"### {run} — {rec.get('label', '')}", ""]
            notes = []
            cfgn = rec.get("config_note", {}).get("changes", [])
            ov = [x for x in cfgn if x.startswith("overrides") or x.startswith("paths.manning")]
            if ov:
                notes.append("config: " + "; ".join(ov))
            if rec.get("frozen_config_check"):
                notes.append(f"frozen author config `{Path(rec['frozen_config_check']['frozen']).name}` identical outside env/paths: {rec['frozen_config_check']['identical_outside_env_paths']}")
            if rec.get("cn_realised"):
                cr = rec["cn_realised"]
                notes.append(f"curve numbers realised: raster clip mean {cr.get('raster_clip_mean_cn')}, active cells {cr.get('active_mean_cn')}, msk = 1 {cr.get('msk1_mean_cn')} (S mean {cr.get('active_S_mm_mean')} mm)")
            if rec.get("post_build"):
                q = J(res / f"{run}_rebuild_q.json")
                if q:
                    notes.append("discharge rebuilt from GloFAS (nearest cell at the injection point, hourly linear, src on the lowest-zb cell within ±" + str(q["ncells"]) + " cells): " +
                                 ", ".join(f"{x['name']} peak {x['daily_peak_m3s']:.2f} m³/s (shift {x['shift_m'][0]:+.0f}/{x['shift_m'][1]:+.0f} m)" for x in q["sources"]) +
                                 f"; combined peak {q['combined_hourly_peak_m3s']:.1f} m³/s; pipeline file was constant {q['pipeline_dis_constant_value']} m³/s at every source")
            if rec.get("inp_patch"):
                notes.append(f"sfincs.inp patch after the build: {rec['inp_patch']}")
            if rec.get("seed", {}).get("raw_imerg_as_forcing"):
                notes.append("forcing: " + rec["seed"]["raw_imerg_as_forcing"])
            fac = factor_from_log(Path(rec["work"]))
            if fac is not None:
                notes.append(f"R2 scaling factor realised at run time: ×{fac:.3f}" + (f" (published ×{rec['published_strict']['multiplier']:.3f})" if rec.get("published_strict", {}).get("multiplier") else ""))
            if rec.get("published_text"):
                pt = dict(rec["published_text"]); src = pt.pop("source", "")
                notes.append(f"published (text): {src} → " + ", ".join(f"{k} {v}" for k, v in pt.items()))
            if rec.get("published_note"):
                notes.append(rec["published_note"])
            if rec.get("resumed"):
                notes.append("validation/records regenerated with --resume after the stream crashed at the validation step (model output untouched)")
            for n in notes:
                L.append(f"- {n}")
            hdr, rows, sm = run_rows(res, run, rec)
            L += [""] + hdr + rows
            v14 = J(res / f"{run}_v14_newmask.json")
            ev = rec["event"]
            if v14 and canon.get(ev) and run not in CANON.values():
                cc = strict(canon[ev]); c = strict(v14)
                L.append(f"| vs the v1.4 canonical ({CANON[ev]}) | | | CSI {cc['csi']:.3f} → {c['csi']:.3f} ({c['csi'] - cc['csi']:+.3f}); HR {cc['hr']:.3f} → {c['hr']:.3f}; B {cc['bias']:.2f} → {c['bias']:.2f}; wet {wet_km2(canon[ev]):.1f} → {wet_km2(v14):.1f} km² | |")
            tmj = J(R / "phase4" / "time_matched" / f"{run}_v14.json")
            if v14 and run == "strymonas_leadin7d" and tmj and tmj.get("window"):
                w = tmj["window"]
                L.append(f"| hmax restricted to the canonical window {w['t0'][:10]} → {w['t1'][:10]} (time_matched_scores.py --window) | | | CSI {w['union']['csi']:.3f} HR {w['union']['hr']:.3f} FAR {w['union']['far']:.3f} B {w['union']['bias']:.2f} | |")
            if v14 and ev == "mandra" and run.startswith("mandra_cn"):
                tp01, csi01 = aoi_tp(v14, "01MANDRA")
                L.append(f"| 01MANDRA (S1 column) | TP {rec.get('published_text', {}).get('tp_01mandra', '—')} | | TP {tp01}, CSI {f(csi01, 3)} | |")
            st = {s["step"]: s for s in rec.get("steps", [])}
            L.append(f"| SFINCS wall-clock s (published) | | | {rec.get('sfincs_total_time_s')} ({rec.get('published_wallclock_s')}) | |")
            L.append("")
            if sm:
                pb = dict(sm.get("pub") or {})
                if pb and "bias" not in pb and all(k in pb for k in ("tp", "fp", "fn")):
                    pb["bias"] = (pb["tp"] + pb["fp"]) / (pb["tp"] + pb["fn"]) if (pb["tp"] + pb["fn"]) else float("nan")
                audit.append(f"- {run} ({rec.get('label', '')}): " + (f"v1.3 published CSI {pb['csi']:.4f} HR {pb['hr']:.4f} FAR {pb['far']:.4f} B {pb.get('bias', float('nan')):.3f}" if pb and "hr" in pb else "no published number") +
                             (f"; v1.3 new mask CSI {sm['mask']['csi']:.4f}" if sm.get("mask") else "") +
                             f"; **v1.4 new mask CSI {sm['v14']['csi']:.4f} HR {sm['v14']['hr']:.4f} FAR {sm['v14']['far']:.4f} B {sm['v14']['bias']:.3f} GSS {sm['v14']['gss']:.4f}** (TP/FP/FN {sm['v14']['tp']}/{sm['v14']['fp']}/{sm['v14']['fn']}); "
                             + (f"curve numbers realised (active) {rec['cn_realised'].get('active_mean_cn')}; " if rec.get("cn_realised") else "")
                             + f"SFINCS {rec.get('sfincs_total_time_s')} s; record `results/{run}_record.json`.")
    L += ["## D7 — new defect, report only (no fix without the author's go)", "",
          "`skill/scripts/prep_q_at_outlets.py` samples GloFAS with `sel(latitude=slice(lat + 0.1, lat − 0.1))`; the Pineios GloFAS file has an ASCENDING latitude axis "
          "(39.11 → 40.21), so the slice is empty for every source and the script falls back to the domain-mean discharge: `q_outlet.csv` = 11.589 m³/s at all four "
          "sources and every hour (the published canonical run, the Phase-1 v1.4 run and every pipeline Pineios run of Phase 3 carry this constant; the Strymonas, "
          "Valencia and Emilia files are descending and sample correctly; Crete has R3 off). The supplement's S2 Pineios row already states that the v1 discharge "
          "was constant (\"an ingestion placeholder\") and that the time-varying audit returns identical metrics; the v1.4 audit row (pineios_timevarying_q) is the "
          "time-varying counterpart under v1.4, built outside the pipeline by `rebuild_pineios_q.py` (the CODE-8 audit method). Fix candidate for the author: "
          "make the sampler order-agnostic (boolean coordinate masks) and warn instead of silently falling back.", ""]
    if a.tests:
        L += [f"Tests: {a.tests}.", ""]; audit.append(f"- Tests: {a.tests}.")
    (R / "CHECKPOINT5a.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
