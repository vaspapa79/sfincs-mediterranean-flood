"""Checkpoint 5b (GO Phases 3-5, 2026-10-19) — cross-event table + sensitivity tables + NUMBER_MAP pointer + figure list +
Crete summary + timing, from the JSON records; nothing retyped. Also the consolidated AUDIT.md block (--audit-out).

Inputs: reproduction/v14_rerun/{results,phase4,phase5}/*.json, phase4/cross_event_v14.md, NUMBER_MAP.md, reproduction/emsr933/
stage5_truth_freeze.json. Usage: python -I checkpoint5b_tables.py --repo <worktree> [--tag v1.4.0 --tag-commit <hash>] [--tests "..."] [--audit-out docs/AUDIT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

METRICS = [("csi", "CSI", 3), ("hr", "HR", 3), ("far", "FAR", 3), ("bias", "B", 2), ("gss", "GSS", 3)]
ACTIVATION_UTC = "2026-10-04T11:02:00"     # EMSR933 activationTime (API)
EVENT_UTC = "2026-10-01T07:00:00"


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def strict(v):
    return v["validation"]["strict_threshold_sweep"]["h>0.10m"]


def wet(v):
    s = strict(v); A = v["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
    return (s["tp"] + s["fp"]) * A


def f(x, nd=3):
    return "—" if x is None or x != x else f"{x:.{nd}f}"


def r2_factor(rec):
    """Realised R2 scaling factor from the run's pipeline log (bias_correct_imerg.py prints 'scaling factor = Xx')."""
    import re
    if not rec or not rec.get("work"):
        return None
    lf = Path(rec["work"]) / "pipeline_v14.log"
    if not lf.exists():
        return None
    m = re.findall(r"scaling factor = ([0-9.]+)x", lf.read_text(errors="replace"))
    return float(m[-1]) if m else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tag", default=""); ap.add_argument("--tag-commit", default="")
    ap.add_argument("--tests", default="")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; P4 = R / "phase4"; P5 = R / "phase5"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = ["# Checkpoint 5b — harness v1.4 consolidated: cross-event tables, sensitivities, NUMBER_MAP, figures, Crete, timing", "",
         f"Generated {now} by `checkpoint5b_tables.py`." + (f" Tag `{a.tag}` = commit `{a.tag_commit}`." if a.tag else "") + " Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside. Crete = Tzermiado tier-1 block.", ""]
    audit = [f"### Harness v1.4 — consolidated results (GO Phases 3–5); block generated {now} by `reproduction/v14_rerun/scripts/checkpoint5b_tables.py`" + (f"; tag `{a.tag}` = `{a.tag_commit}`" if a.tag else ""), ""]
    # ---- 1. cross-event tables (embed the generated markdown)
    ce_md = P4 / "cross_event_v14.md"
    if ce_md.exists():
        body = ce_md.read_text(encoding="utf-8").splitlines()
        L += ["## 1. Cross-event tables (Tables 9 / 10 / 13 / 14 equivalents; `phase4/cross_event_v14.{json,md}`)", ""] + [ln for ln in body if not ln.startswith("# ")] + [""]
        ce = J(P4 / "cross_event_v14.json")
        for run, e in ce["events"].items():
            v, p = e.get("enhanced_v14"), e.get("enhanced_v13_published")
            if v:
                s, k = v["strict"], v["skill"]
                audit.append(f"- {e['label']} ({run}): **v1.4 CSI {s['csi']:.4f} HR {s['hr']:.4f} FAR {s['far']:.4f} B {s['bias']:.3f} GSS {s['gss']:.4f}**, SEDI {k['sedi']:.4f} PSS {k['pss']:.4f}, "
                             f"CSI* {f((v.get('csi_star') or {}).get('csi'), 4)} at {(v.get('csi_star') or {}).get('threshold')}, fuzzy r=1 {v['fuzzy_r1']['csi']:.4f}; eval {v['eval_km2']:.1f} km², observed {v['obs_km2']:.1f} km²"
                             + (f"; v1.3 published CSI {p['strict']['csi']:.4f} HR {p['strict']['hr']:.4f} B {p['strict']['bias']:.3f}" if p else "; no published number (held-out prospective event)")
                             + (f"; baseline v1.4 CSI {e['baseline_v14']['strict']['csi']:.4f} (Δ {e['delta_v14']['csi']:+.4f})" if e.get("baseline_v14") else "") + f"; sources `{e['sources']}`.")
    else:
        L += ["## 1. Cross-event tables", "", "pending (run phase4.py)", ""]
    # ---- 2. sensitivity tables: Phase-3 groups c/d/e + Crete sensitivities
    L += ["## 2. Sensitivity tables (v1.4; labelled, never canonical)", ""]
    groups = [("R2 anchor sweeps (Mandra 95/140/200/255 mm; Pineios 220/295/400/510 mm)", ["mandra_r2_95", "mandra_r2_140", "mandra_enhanced", "mandra_r2_255", "pineios_r2_220", "pineios_r2_295", "pineios_enhanced", "pineios_r2_510"], "published_strict"),
              ("Pineios audit rows", ["pineios_enhanced", "pineios_timevarying_q", "pineios_qinf5", "pineios_cn_on", "pineios_raw_imerg"], None),
              ("Mandra curve-number rows (S1) + Manning test", ["mandra_enhanced", "mandra_cn_a15", "mandra_cn_a58", "mandra_cn_b_default", "mandra_cn_d_amc3", "mandra_cn_d_amc3_manning080"], None),
              ("Strymonas: ablations, v1 source, lead-in", ["strymonas_baseline", "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_abl_qoff_cn", "strymonas_v1_prefix_src", "strymonas_leadin7d"], None),
              ("Valencia raw IMERG", ["valencia_enhanced_164", "valencia_raw_imerg"], None),
              ("Crete sensitivities (tier-1 Tzermiado block)", ["crete_baseline", "crete_canonical_r2on", "crete_sens_r2off", "crete_sens_anchor_224", "crete_sens_anchor_336", "crete_sens_anchor_582", "crete_sens_karst_q1914"], "crete")]
    for title, runs, mode in groups:
        L += [f"### {title}", "", "| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for run in runs:
            rec = J(res / f"{run}_record.json")
            if mode == "crete":
                t = J(P5 / f"{run}_tiers.json")
                if not (rec and t):
                    L.append(f"| {run} | pending | | | | | | | | | | |"); continue
                b = t["aois"].get("03", {})
                s = (b.get("strict_threshold_sweep") or {}).get("h>0.10m")
                fac = r2_factor(rec)
                L.append(f"| {run} | {rec.get('label', '')[:70]} | {f(s and s['csi'])} | {f(s and s['hr'])} | {f(s and s['far'])} | {f(s and s['bias'], 2)} | {f(s and s['gss'])} | {f(b.get('modelled_km2_h_gt_0p10'), 2)} (obs {f(b.get('observed_km2'), 2)}) | — | — | {f(fac, 3) if fac else '—'} | {rec.get('sfincs_total_time_s')} |")
                continue
            v = J(res / f"{run}_v14_newmask.json")
            if not (rec and v):
                L.append(f"| {run} | pending | | | | | | | | | | |"); continue
            s = strict(v); ps = (rec.get("published_strict") or {}).get("csi")
            pub = f(ps) if ps is not None else ("text: " + ", ".join(f"{k} {vv}" for k, vv in (rec.get("published_text") or {}).items() if k != "source")[:60] if rec.get("published_text") else "—")
            cn = (rec.get("cn_realised") or {}).get("active_mean_cn", "—")
            fac = f(r2_factor(rec)) if r2_factor(rec) else "—"
            L.append(f"| {run} | {rec.get('label', '')[:70]} | {s['csi']:.3f} | {s['hr']:.3f} | {s['far']:.3f} | {s['bias']:.2f} | {s['gss']:.3f} | {wet(v):.1f} | {pub} | {cn} | {fac} | {rec.get('sfincs_total_time_s')} |")
        L.append("")
    # ---- 3. NUMBER_MAP
    nm = R / "NUMBER_MAP.md"
    if nm.exists():
        rows = [ln for ln in nm.read_text(encoding="utf-8").splitlines() if ln.startswith("| ") and not ln.startswith("| location")]
        pend = sum(1 for ln in rows if "pending" in ln)
        L += ["## 3. NUMBER_MAP.md", "", f"`reproduction/v14_rerun/NUMBER_MAP.md`: {len(rows)} entries (table rows, figure captions, sentences), {pend} still pending. Every entry: location → R5 value → v1.4 value → source JSON → text lines.", ""]
        audit.append(f"- NUMBER_MAP.md: {len(rows)} entries, {pend} pending (`reproduction/v14_rerun/NUMBER_MAP.md`).")
    # ---- 4. figures
    figs = sorted((P4 / "figures").glob("*.png")) if (P4 / "figures").exists() else []
    L += ["## 4. Figures regenerated (PNG + CSV data behind each, `phase4/figures/`)", ""] + [f"- `{p.name}` (+ `{p.with_suffix('.csv').name}`)" if p.with_suffix(".csv").exists() else f"- `{p.name}` (data: the rain series CSV / cross_event JSON)" for p in figs] + [""]
    # ---- 5. Crete summary
    tf = J(a.repo / "reproduction" / "emsr933" / "stage5_truth_freeze.json")
    L += ["## 5. Crete EMSR933 (rule_ledger.md §8; truth frozen at the post-closure snapshot)", ""]
    if tf:
        L.append(f"Truth: snapshot {tf['snapshot_utc']} (activation closed {tf['activation_closed']}), {tf['released_packages']} released packages, AOIs without product {tf['aois_without_product']}; "
                 "tier 1 = AOI03 Tzermiado (DEL S1 4 Oct 16:22 UTC ∪ DEL_MONIT02 GeoEye 8 Oct 09:02; the GRA released after the cut-off is dropped by the delineation-first rule); tier 2 = 01/04/06/07 km² only; tier 3 = 02/05/08 excluded; no union score.")
    for run in ("crete_baseline", "crete_canonical_r2on"):
        t = J(P5 / f"{run}_tiers.json"); rec = J(res / f"{run}_record.json")
        if not t:
            L.append(f"- {run}: pending"); continue
        b = t["aois"]["03"]; sw = b["strict_threshold_sweep"]
        L.append(f"- **{run}** (SFINCS {rec.get('sfincs_total_time_s')} s, end {rec.get('end_utc')}): Tzermiado " + "; ".join(f"{k}: CSI {c['csi']:.3f} HR {c['hr']:.3f} FAR {c['far']:.3f} B {c['bias']:.2f}" for k, c in sw.items())
                 + f"; CSI* {b['csi_star']['csi']:.3f} at {b['csi_star']['threshold']} (B* {b['csi_star']['bias']:.2f}); SEDI {sw['h>0.10m']['skill']['sedi']:.3f} PSS {sw['h>0.10m']['skill']['pss']:.3f}; fuzzy r=1 {b['fuzzy_at_h_gt_0p10m']['r=1']['csi']:.3f}; "
                 f"observed {b['observed_km2']:.2f} km², modelled {b['modelled_km2_h_gt_0p10']:.2f} km² of {b['universe_km2']:.1f} km²; peak hmax {f(b['peak_hmax_m'], 1)} m.")
        L.append("  tier 2 (observed vs modelled km² at h > 0.10 m): " + "; ".join(f"AOI{c} {r['name']} {r.get('observed_km2', 0):.3f} vs {r.get('modelled_km2_h_gt_0p10', 0):.3f}" for c, r in t["aois"].items() if r.get("tier") == 2))
        audit.append(f"- Crete {run}: Tzermiado (tier 1) CSI {sw['h>0.10m']['csi']:.4f} HR {sw['h>0.10m']['hr']:.4f} FAR {sw['h>0.10m']['far']:.4f} B {sw['h>0.10m']['bias']:.3f} GSS {sw['h>0.10m']['gss']:.4f}; CSI* {b['csi_star']['csi']:.4f} at {b['csi_star']['threshold']}; "
                     f"SEDI {sw['h>0.10m']['skill']['sedi']:.4f} PSS {sw['h>0.10m']['skill']['pss']:.4f}; observed {b['observed_km2']:.3f} km², modelled {b['modelled_km2_h_gt_0p10']:.3f} km²; tier 2: "
                     + "; ".join(f"AOI{c} {r.get('observed_km2', 0):.3f}/{r.get('modelled_km2_h_gt_0p10', 0):.3f} km²" for c, r in t["aois"].items() if r.get("tier") == 2) + f"; SFINCS {rec.get('sfincs_total_time_s')} s; `phase5/{run}_tiers.json`.")
    rn = J(P5 / "crete_rain_vs_noa.json")
    if rn:
        L.append(f"- rainfall vs NOA stations (`phase5/crete_rain_vs_noa.json`, window {rn['window_utc'][0][:16]} → {rn['window_utc'][1][:16]}): " + "; ".join(f"{s['station']} NOA {s['noa_total_mm']:.0f} / raw IMERG {s['imerg_raw_mm']:.0f} / R2 {s['imerg_r2_mm']:.0f} / ERA5 {s['era5_mm']:.0f} mm" for s in rn["stations"]))
    L.append("")
    # ---- 6. timing
    recs = {p.stem.replace("_record", ""): J(p) for p in sorted(res.glob("*_record.json"))}
    phase3 = [(k, v) for k, v in recs.items() if v and v.get("phase") == 3]
    crete = [(k, v) for k, v in recs.items() if v and v.get("phase") == 5]
    L += ["## 6. Timing (from the run records; `reproduction/emsr933/timing.md` has the event log)", "", "| run | start UTC | end UTC | SFINCS s | published SFINCS s |", "|---|---|---|---|---|"]
    for k, v in phase3 + crete:
        L.append(f"| {k} | {v.get('start_utc')} | {v.get('end_utc')} | {v.get('sfincs_total_time_s')} | {v.get('published_wallclock_s')} |")
    can = recs.get("crete_canonical_r2on")
    if can and can.get("end_utc"):
        t_val = dt.datetime.strptime(can["end_utc"], "%Y-%m-%dT%H:%M:%SZ")
        act = dt.datetime.fromisoformat(ACTIVATION_UTC); ev = dt.datetime.fromisoformat(EVENT_UTC)
        L += ["", f"Activation → validated canonical hindcast: {ACTIVATION_UTC}Z → {can['end_utc']} = **{(t_val - act).total_seconds() / 86400:.2f} days** ({(t_val - ev).total_seconds() / 86400:.2f} days after the event time {EVENT_UTC}Z); "
              "the interval includes the harness-v1.4 rebuild (CODE-12/13, GO-C, GO-D6) and the wait for ERA5T; see timing.md."]
        audit.append(f"- Crete activation-to-validated-hindcast interval: {(t_val - act).total_seconds() / 86400:.2f} days ({ACTIVATION_UTC}Z → {can['end_utc']}).")
    if a.tests:
        L += ["", f"Tests: {a.tests}."]; audit.append(f"- Tests: {a.tests}.")
    (R / "CHECKPOINT5b.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
