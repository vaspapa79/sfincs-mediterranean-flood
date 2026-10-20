"""Checkpoint 6 (CODE-14, 2026-10-20) — A scope table, B tests + hash, C four-column deltas (v1.3 / v1.4.0 / v1.4.1 / Δ), D results
(Table S3, MANIFEST row 16), E finding, F plan; from the JSON records, nothing retyped. Also the AUDIT.md block (--audit-out).

Inputs: reproduction/v14_rerun/{results,code14,phase4}/*.json, code14/E_d5_provenance.md, code14/F_branch_plan.md (narrative sections
written by hand: issue numbers, commit hashes, plan — no model numbers in them).
Usage: python -I checkpoint6_tables.py --repo <worktree> [--tag v1.4.1 --tag-commit <hash>] [--fix-commit <hash>] [--tests "..."] [--audit-out docs/AUDIT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

V141_BASES = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5"]
D8 = "pineios_enhanced_v141_d8titarisios"
ROW16 = "mandra_v3_maskrestrict"
M = [("csi", "CSI", 3), ("hr", "HR", 3), ("far", "FAR", 3), ("bias", "B", 2), ("gss", "GSS", 3)]


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def strict(v):
    return v["validation"]["strict_threshold_sweep"]["h>0.10m"] if v else None


def f(x, nd=3, sign=False):
    if x is None or x != x:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def wet(v):
    s = strict(v); A = v["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
    return (s["tp"] + s["fp"]) * A


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tag", default=""); ap.add_argument("--tag-commit", default=""); ap.add_argument("--fix-commit", default="")
    ap.add_argument("--tests", default="")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; C14 = R / "code14"; P4 = R / "phase4"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = ["# Checkpoint 6 — CODE-14: D7 scope + fix (harness v1.4.1), re-runs, Table S3 + row 16, D5 provenance, branch plan", "",
         f"Generated {now} by `checkpoint6_tables.py`." + (f" Fix commit `{a.fix_commit}`." if a.fix_commit else "") + (f" Tag `{a.tag}` = commit `{a.tag_commit}`." if a.tag else "")
         + " Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside. "
           "**Read first: the v1.4.1 Pineios rows use the frozen configuration under the fixed sampler, which injects the Pineios main stem at the Titarisios point (D8, 1128.8 m³/s peak); "
           "they are the faithful output of the frozen config, not a recommended canonical until the author decides D8 (the labelled diagnostic row shows the alternative).**", ""]
    audit = [f"### Harness v1.4.1 (CODE-14) — results; block generated {now} by `reproduction/v14_rerun/scripts/checkpoint6_tables.py`" + (f"; tag `{a.tag}` = `{a.tag_commit}`" if a.tag else "") + (f"; fix commit `{a.fix_commit}`" if a.fix_commit else ""), ""]
    # ---- A
    sc = J(C14 / "d7_scope.json")
    L += ["## A. D7 scope (no runs; `code14/d7_scope.{json,md}`, `scripts/d7_scope.py`)", ""]
    if sc:
        groups = {}
        for r in sc["runs"]:
            key = tuple((p["name"], p["written_is"], p["written"]["min"], p["written"]["max"], round(p["written"]["mean"], 2)) for p in r["points"])
            groups.setdefault(key, {"runs": [], "points": r["points"], "order": r["glofas_latitude_order"]})["runs"].append(r["run"])
        L += ["| runs (identical sfincs.dis) | GloFAS axis | point | written min / max / mean (m³/s) | what was written | nearest cell @ named point: peak (cell) | window-max cell (the sampler's rule): peak (cell) |", "|---|---|---|---|---|---|---|"]
        for key, g in groups.items():
            first = True
            for p in g["points"]:
                cp = p.get("candidate_peaks_in_simulated_window_m3s", {})
                nk = cp.get("nearest cell @ named point, step-filled"); wk = cp.get("window-max series, step-filled (the sampler, order-agnostic)")
                wm = p.get("window_max") or {}
                L.append(f"| {', '.join(g['runs']) if first else ''} | {g['order'] if first else ''} | {p['name']} | {p['written']['min']:.2f} / {p['written']['max']:.2f} / {p['written']['mean']:.2f} | {p['written_is']} | "
                         f"{f(nk, 2)} {tuple(p['nearest_named']['cell'])} | {f(wk, 2)} {tuple(wm.get('cell', ())) if wm else 'EMPTY'} |")
                first = False
        n_aff = sum(1 for r in sc["runs"] if any(p["written"]["constant"] for p in r["points"]))
        L += ["", f"Affected (constant fallback written): {n_aff} of {len(sc['runs'])} R3-on model directories — every pipeline Pineios run (published canonical, published R2-510 sweep, v1.4.0 `pineios_enhanced`, `pineios_r2_220/295/510`, `pineios_cn_on`, `pineios_raw_imerg`). "
              "The published v3/v4 and v1.4.0 `pineios_timevarying_q` / `pineios_qinf5` carry the audit rebuild. Strymonas (5), Valencia (2), Emilia (1): the sampler's window-max series (correct). Crete: R3 off.", ""]
        audit.append(f"- A scope (`code14/d7_scope.json`): {n_aff} of {len(sc['runs'])} R3-on model directories carry the 11.589 m³/s constant (all pipeline Pineios runs); the rest sample correctly or carry the audit rebuild.")
    # ---- B
    rg = J(C14 / "d7_sampler_regression.json")
    L += ["## B. D7 fix — harness v1.4.1 (`skill/scripts/prep_q_at_outlets.py`, `tests/test_prep_q_sampler.py`)", ""]
    if rg:
        same = [r["run"] for r in rg["runs"] if r["q_outlet_csv_identical"] and r["sfincs_dis_identical"]]
        diff = [r for r in rg["runs"] if not r["q_outlet_csv_identical"]]
        pk = diff[0] if diff else None
        L += [f"- Window-max cell rule kept, coordinate masks instead of the label slice (order-agnostic, inclusive, 1e-4° edge tolerance), `NoChannelError` instead of the domain-mean fallback, duplicate-cell report, optional per-point `window_deg`, `q_outlet_cells.json` provenance.",
              f"- Real-data regression (`code14/d7_sampler_regression.json`): byte-identical `q_outlet.csv` and `sfincs.dis` for {len(same)} runs ({', '.join(same)}); "
              + (f"the Pineios runs get column peaks {' / '.join(f'{x:.2f}' for x in pk['v141_column_peaks'])} m³/s (combined hourly peak {pk['v141_combined_hourly_peak_m3s']:.1f}) in place of the constant." if pk else ""),
              f"- Fix commit `{a.fix_commit}`; tests: {a.tests or 'see AUDIT.md'}.", ""]
        audit.append(f"- B fix: byte-identical discharge files for {len(same)} correctly-sampled runs; Pineios column peaks {' / '.join(f'{x:.2f}' for x in pk['v141_column_peaks']) if pk else '—'} m³/s; fix commit `{a.fix_commit}`; tests {a.tests}.")
    # ---- C
    L += ["## C. v1.4.1 re-runs of the affected runs — four columns (v1.3 published / v1.4.0 / v1.4.1 / Δ = v1.4.1 − v1.4.0)", "",
          "| run | label | CSI v1.3 publ. | CSI v1.4.0 | CSI v1.4.1 | ΔCSI | HR v1.4.0 → v1.4.1 (Δ) | FAR v1.4.0 → v1.4.1 (Δ) | B v1.4.0 → v1.4.1 (Δ) | GSS v1.4.0 → v1.4.1 | TP/FP/FN v1.4.1 | wet km² v1.4.0 → v1.4.1 | SFINCS s v1.4.1 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    pending = []
    for b in V141_BASES:
        r0, r1 = J(res / f"{b}_record.json"), J(res / f"{b}_v141_record.json")
        v0, v1 = J(res / f"{b}_v14_newmask.json"), J(res / f"{b}_v141_v14_newmask.json")
        s0, s1 = strict(v0), strict(v1)
        pub = ((r0 or {}).get("published_strict") or {}).get("csi")
        if pub is None:                                   # Phase-1 records: the published number sits in the record check / the v1.3 re-scoring
            pub = (((r0 or {}).get("published_record_check") or {}).get("published") or {}).get("csi")
        if pub is None:
            sp_ = strict(J(res / f"{b}_v13_publishedmask.json")); pub = sp_["csi"] if sp_ else None
        if not (s0 and s1):
            L.append(f"| {b}_v141 | {(r1 or r0 or {}).get('label', '')[:60]} | {f(pub)} | {f(s0 and s0['csi'])} | pending | | | | | | | | |"); pending.append(b); continue
        d = {k: s1[k] - s0[k] for k, _, _ in M}
        L.append(f"| {b}_v141 | {(r0 or {}).get('label', 'canonical enhanced')[:60]} | {f(pub)} | {s0['csi']:.3f} | **{s1['csi']:.3f}** | {d['csi']:+.3f} | {s0['hr']:.3f} → {s1['hr']:.3f} ({d['hr']:+.3f}) | "
                 f"{s0['far']:.3f} → {s1['far']:.3f} ({d['far']:+.3f}) | {s0['bias']:.2f} → {s1['bias']:.2f} ({d['bias']:+.2f}) | {s0['gss']:.3f} → {s1['gss']:.3f} | {s1['tp']}/{s1['fp']}/{s1['fn']} | "
                 f"{wet(v0):.0f} → {wet(v1):.0f} | {(r1 or {}).get('sfincs_total_time_s')} |")
        audit.append(f"- {b}: v1.3 published CSI {f(pub, 4)}; v1.4.0 CSI {s0['csi']:.4f} HR {s0['hr']:.4f} FAR {s0['far']:.4f} B {s0['bias']:.3f} GSS {s0['gss']:.4f}; **v1.4.1 CSI {s1['csi']:.4f} HR {s1['hr']:.4f} FAR {s1['far']:.4f} B {s1['bias']:.3f} GSS {s1['gss']:.4f}** "
                     f"(TP/FP/FN {s1['tp']}/{s1['fp']}/{s1['fn']}); Δ(v1.4.1 − v1.4.0) CSI {d['csi']:+.4f} HR {d['hr']:+.4f} FAR {d['far']:+.4f} B {d['bias']:+.3f}; SFINCS {(r1 or {}).get('sfincs_total_time_s')} s; records `results/{b}_v141_*.json`.")
    # D8 diagnostic row
    rd, vd = J(res / f"{D8}_record.json"), J(res / f"{D8}_v14_newmask.json")
    v1c = J(res / "pineios_enhanced_v141_v14_newmask.json"); s1c = strict(v1c); sd = strict(vd)
    if sd and s1c:
        dd = {k: sd[k] - s1c[k] for k, _, _ in M}
        q = ((rd or {}).get("q_outlet_cells") or {}).get("points", [])
        tit = next((p for p in q if p["name"] == "titarisios"), {})
        L += ["", f"D8 diagnostic (never canonical) `{D8}`: Titarisios sampled at {tuple(tit.get('cell_lonlat', ()))} (window ±{tit.get('window_half_deg')}°, column peak {tit.get('column_peak_m3s')} m³/s) instead of the main-stem cell: "
              f"CSI {sd['csi']:.3f} HR {sd['hr']:.3f} FAR {sd['far']:.3f} B {sd['bias']:.2f} GSS {sd['gss']:.3f} (TP/FP/FN {sd['tp']}/{sd['fp']}/{sd['fn']}); vs the v1.4.1 canonical Δ CSI {dd['csi']:+.3f} HR {dd['hr']:+.3f} FAR {dd['far']:+.3f} B {dd['bias']:+.2f}; "
              f"wet {wet(vd):.0f} km² vs {wet(v1c):.0f}; SFINCS {(rd or {}).get('sfincs_total_time_s')} s."]
        audit.append(f"- D8 diagnostic {D8} (never canonical): Titarisios cell {tuple(tit.get('cell_lonlat', ()))}, peak {tit.get('column_peak_m3s')} m³/s; CSI {sd['csi']:.4f} HR {sd['hr']:.4f} FAR {sd['far']:.4f} B {sd['bias']:.3f} GSS {sd['gss']:.4f}; Δ vs v1.4.1 canonical CSI {dd['csi']:+.4f}.")
    else:
        L += ["", f"D8 diagnostic `{D8}`: pending."]
    ce = J(P4 / "cross_event_v14_v141.md")
    if ce:
        L += ["", "### Cross-event tables with the v1.4.1 Pineios canonical (`phase4/cross_event_v14_v141.{json,md}`; other events unchanged)", ""] + [ln for ln in (P4 / "cross_event_v14_v141.md").read_text(encoding="utf-8").splitlines() if not ln.startswith("# ")]
    L.append("")
    # ---- D
    L += ["## D. Loose ends", ""]
    s3 = J(C14 / "table_s3_v14.json")
    if s3:
        L += ["### Table S3 equivalent — evaluation-mask sensitivity, v1.4 mask as the reference (`code14/table_s3_v14.{json,md}`)", "",
              "| Event | mask | area km² | CSI | HR | FAR | B | GSS | published S3 CSI (v1.3 mask) |", "|---|---|---|---|---|---|---|---|---|"]
        pubS3 = {"Pineios": [0.347, 0.456, 0.440, 0.471], "Mandra": [0.031, 0.106, 0.071, 0.149], "Strymonas": [0.157, 0.183, 0.182, 0.185]}   # supplement Table S3 (R5 text), for the eye only
        for ev in s3["events"]:
            short = ev["label"].split(" (")[0]
            for i, v in enumerate(ev["variants"]):
                L.append(f"| {ev['label'] if i == 0 else ''} | {v['name']} | {v['area_km2']:.0f} | {v['csi']:.3f} | {v['hr']:.3f} | {v['far']:.3f} | {v['bias']:.2f} | {v['gss']:.3f} | {pubS3[short][i] if short in pubS3 else '—'} |")
            audit.append(f"- Table S3 {short}: " + "; ".join(f"{v['name']} {v['area_km2']:.0f} km² CSI {v['csi']:.4f} HR {v['hr']:.4f} B {v['bias']:.3f}" for v in ev["variants"]) + f" (`code14/table_s3_v14.json`).")
        L.append("")
    r16, v16 = J(res / f"{ROW16}_record.json"), J(res / f"{ROW16}_v14_newmask.json")
    p16, n16 = J(res / f"{ROW16}_v13_publishedmask.json"), J(res / f"{ROW16}_v13_newmask.json")
    L += ["### MANIFEST row 16 — Mandra v3 post-hoc mask restriction, recreated on the v1.4 build (`scripts/mandra_v3_maskrestrict_v14.py`)", ""]
    if r16 and v16:
        s16, sp, sn = strict(v16), strict(p16), strict(n16)
        me = r16["mask_edit"]; pt = r16["published_text"]
        v0 = strict(J(res / "mandra_enhanced_v14_newmask.json"))
        L += [f"- Mask edit: {me['published_v3_deactivated_cells']} cells deactivated by the published v3 edit; v1.4 active {me['v14_active_before']} → {me['v14_active_after']} cells ({me['active_km2_before']:.1f} → {me['active_km2_after']:.1f} km²; "
              f"boundary cells {me['v14_boundary_cells_before']} → {me['v14_boundary_cells_after']}); index file kept.",
              "", "| column | CSI | HR | FAR | B | GSS | TP/FP/FN |", "|---|---|---|---|---|---|---|",
              f"| v1.3 published (S2 text) | {pt['csi']} | {pt['hr']} | — | {pt['bias']} | — | — |",
              f"| v1.3 output re-scored, published mask | {f(sp and sp['csi'])} | {f(sp and sp['hr'])} | {f(sp and sp['far'])} | {f(sp and sp['bias'], 2)} | {f(sp and sp['gss'])} | {sp['tp'] if sp else '—'}/{sp['fp'] if sp else '—'}/{sp['fn'] if sp else '—'} |",
              f"| v1.3 output re-scored, new mask | {f(sn and sn['csi'])} | {f(sn and sn['hr'])} | {f(sn and sn['far'])} | {f(sn and sn['bias'], 2)} | {f(sn and sn['gss'])} | {sn['tp'] if sn else '—'}/{sn['fp'] if sn else '—'}/{sn['fn'] if sn else '—'} |",
              f"| v1.4 canonical Mandra (unrestricted, for reference) | {f(v0['csi'])} | {f(v0['hr'])} | {f(v0['far'])} | {f(v0['bias'], 2)} | {f(v0['gss'])} | {v0['tp']}/{v0['fp']}/{v0['fn']} |",
              f"| **v1.4.1 build + published mask edit** | **{s16['csi']:.3f}** | {s16['hr']:.3f} | {s16['far']:.3f} | {s16['bias']:.2f} | {s16['gss']:.3f} | {s16['tp']}/{s16['fp']}/{s16['fn']} |",
              "", f"SFINCS {r16.get('sfincs_total_time_s')} s (published 1906.7 s); published-text check (CSI/HR at 3 dp on the re-scored published mask): {r16.get('published_record_check', {}).get('csi_matches_text_3dp')} / {r16.get('published_record_check', {}).get('hr_matches_text_3dp')}.", ""]
        audit.append(f"- MANIFEST row 16 (Mandra v3 mask restriction on the v1.4 build): v1.3 published text CSI {pt['csi']} HR {pt['hr']} B {pt['bias']}; v1.3 output re-scored published mask CSI {f(sp and sp['csi'], 4)}, new mask {f(sn and sn['csi'], 4)}; "
                     f"**v1.4.1 CSI {s16['csi']:.4f} HR {s16['hr']:.4f} FAR {s16['far']:.4f} B {s16['bias']:.3f} GSS {s16['gss']:.4f}** (TP/FP/FN {s16['tp']}/{s16['fp']}/{s16['fn']}); v1.4 unrestricted canonical CSI {v0['csi']:.4f}; active {me['active_km2_before']:.1f} → {me['active_km2_after']:.1f} km²; SFINCS {r16.get('sfincs_total_time_s')} s; `results/{ROW16}_*.json`.")
    else:
        L += ["pending", ""]
    # ---- E, F (narrative files)
    for sec, fn in (("## E. D5 provenance (meteo-grid corner vs centre)", "E_d5_provenance.md"), ("## F. Branch reconciliation plan (no push)", "F_branch_plan.md")):
        p = C14 / fn
        L += [sec, ""] + ([ln for ln in p.read_text(encoding="utf-8").splitlines()] if p.exists() else ["pending"]) + [""]
        if p.exists():
            audit.append(f"- {sec[3:]}: see `reproduction/v14_rerun/code14/{fn}` (reproduced in CHECKPOINT6.md).")
    # ---- figures + NUMBER_MAP + timing
    figs = sorted((P4 / "figures").glob("*v141*.png")) + sorted((P4 / "figures").glob(f"*{ROW16}*.png"))
    L += ["## Figures (v1.4.1 products beside the v1.4.0 ones, `phase4/figures/`)", ""] + [f"- `{p.name}`" for p in figs] + ([] if figs else ["none yet"]) + [""]
    nm = R / "NUMBER_MAP.md"
    if nm.exists():
        rows = [ln for ln in nm.read_text(encoding="utf-8").splitlines() if ln.startswith("| ") and not ln.startswith("| location")]
        hdr = next((ln for ln in nm.read_text(encoding="utf-8").splitlines() if ln.startswith("| location")), "")
        n141 = sum(1 for ln in rows if "| = v1.4.0 |" not in ln and "new (v1.4.1)" in hdr)
        L += ["## NUMBER_MAP.md", "", f"`reproduction/v14_rerun/NUMBER_MAP.md`: {len(rows)} entries" + (f"; v1.4.1 column present, {n141} entries differ from v1.4.0" if "v1.4.1" in hdr else "") + f"; {sum(1 for ln in rows if 'pending' in ln)} pending.", ""]
        audit.append(f"- NUMBER_MAP.md: {len(rows)} entries" + (f", {n141} differ under v1.4.1" if "v1.4.1" in hdr else "") + ".")
    recs = {p.stem.replace("_record", ""): J(p) for p in sorted(res.glob("*_record.json"))}
    L += ["## Timing (phase-6 records)", "", "| run | start UTC | end UTC | SFINCS s | published SFINCS s |", "|---|---|---|---|---|"]
    for k, v in recs.items():
        if v and v.get("phase") == 6:
            L.append(f"| {k} | {v.get('start_utc')} | {v.get('end_utc')} | {v.get('sfincs_total_time_s')} | {v.get('published_wallclock_s')} |")
    if a.tests:
        L += ["", f"Tests: {a.tests}."]; audit.append(f"- Tests: {a.tests}.")
    if pending:
        L += ["", f"Pending v1.4.1 re-runs: {', '.join(pending)}."]
    (R / "CHECKPOINT6.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
