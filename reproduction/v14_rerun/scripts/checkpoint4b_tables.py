"""Checkpoint 4b (GO-D6 + Phase 2, 2026-10-19) — tables and the AUDIT block from the JSON records; nothing retyped.

Inputs: reproduction/v14_rerun/results/*.json (Strymonas pre-D6 and post-D6, Valencia, Emilia), strymonas_postD6_balance.json,
reproduction/v14_harness/{D6_test_metrics.json, D6_invariance_mandra.json}. Output: reproduction/v14_rerun/CHECKPOINT4b.md
and (with --audit-out) a block appended to docs/AUDIT.md.
Usage: python -I checkpoint4b_tables.py --repo <worktree> --d6-commit <hash> --d6-utc <UTC> --bbox-commit <hash> --bbox-utc <UTC>
       [--tests "..."] [--audit-out docs/AUDIT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

METRICS = [("csi", "CSI", 3), ("hr", "HR", 3), ("far", "FAR", 3), ("bias", "B", 2), ("gss", "GSS", 3)]


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def strict(v):
    return v["validation"]["strict_threshold_sweep"]["h>0.10m"]


def fz(v):
    return v["validation"]["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"]


def event_table(res: Path, run: str, v13_from: str | None = None, extra_col: tuple | None = None):
    """Rows of the four-column table (+ optional extra v1.4 column, e.g. the pre-D6 run)."""
    src13 = v13_from or run
    v13p, v13n, v14 = J(res / f"{src13}_v13_publishedmask.json"), J(res / f"{src13}_v13_newmask.json"), J(res / f"{run}_v14_newmask.json")
    if not (v13p and v13n and v14):
        return [f"| {run} | missing records | | | | | | |"], None
    xh = ""
    xv = None
    if extra_col:
        xv = J(res / f"{extra_col[0]}_v14_newmask.json")
        xh = f" {extra_col[1]} |"
    a, b, c = strict(v13p), strict(v13n), strict(v14)
    hdr = ["| metric | v1.3 as published | v1.3 rescored, new mask |" + xh + " v1.4, new mask | Δ (v1.4 − v1.3 published) | of which mask | of which harness |",
           "|---|---|---|" + ("---|" if extra_col else "") + "---|---|---|---|"]
    rows = []
    for key, name, nd in METRICS:
        x, y, z = a[key], b[key], c[key]
        xe = f" {strict(xv)[key]:.{nd}f} |" if xv else ""
        rows.append(f"| {name} | {x:.{nd}f} | {y:.{nd}f} |{xe} **{z:.{nd}f}** | {z - x:+.{nd}f} | {y - x:+.{nd}f} | {z - y:+.{nd}f} |")
    A = v14["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
    xe = f" {strict(xv)['tp']} / {strict(xv)['fp']} / {strict(xv)['fn']} |" if xv else ""
    rows.append(f"| TP / FP / FN cells | {a['tp']} / {a['fp']} / {a['fn']} | {b['tp']} / {b['fp']} / {b['fn']} |{xe} {c['tp']} / {c['fp']} / {c['fn']} | | | |")
    xe = f" {fz(xv):.3f} |" if xv else ""
    rows.append(f"| fuzzy r=1 CSI | {fz(v13p):.3f} | {fz(v13n):.3f} |{xe} {fz(v14):.3f} | {fz(v14) - fz(v13p):+.3f} | {fz(v13n) - fz(v13p):+.3f} | {fz(v14) - fz(v13n):+.3f} |")
    xe = f" {(strict(xv)['tp'] + strict(xv)['fp']) * A:.1f} |" if xv else ""
    rows.append(f"| modelled wet in eval km² | {(a['tp'] + a['fp']) * A:.1f} | {(b['tp'] + b['fp']) * A:.1f} |{xe} {(c['tp'] + c['fp']) * A:.1f} | | | |")
    rows.append(f"| eval km² / observed km² | {v13p['validation']['evaluation_area_km2']:.1f} / {v13p['validation']['observed_wet_km2_strict']:.1f} | "
                f"{v13n['validation']['evaluation_area_km2']:.1f} / {v13n['validation']['observed_wet_km2_strict']:.1f} |" + (" |" if xv else "") +
                f" {v14['validation']['evaluation_area_km2']:.1f} / {v14['validation']['observed_wet_km2_strict']:.1f} | | | |")
    ex = v13n["validation"].get("evaluation_mask_exclusion", {})
    rows.append(f"| excluded in eval / observed removed | — | {ex.get('excluded_cells')} cells ({ex.get('excluded_km2', 0):.1f} km²) / "
                f"{ex.get('observed_wet_excluded_cells')} cells ({ex.get('observed_wet_excluded_km2', 0):.2f} km²) |" + (" |" if xv else "") + " same mask | | | |")
    summary = {"pub": a, "mask": b, "v14": c, "fz": (fz(v13p), fz(v13n), fz(v14)), "ex": ex,
               "eval_obs": (v13p["validation"]["evaluation_area_km2"], v13p["validation"]["observed_wet_km2_strict"],
                            v14["validation"]["evaluation_area_km2"], v14["validation"]["observed_wet_km2_strict"])}
    return hdr + rows, summary


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--d6-commit", required=True); ap.add_argument("--d6-utc", required=True)
    ap.add_argument("--bbox-commit", required=True); ap.add_argument("--bbox-utc", required=True)
    ap.add_argument("--tests", default="")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; H = a.repo / "reproduction" / "v14_harness"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tm, inv, bal = J(H / "D6_test_metrics.json"), J(H / "D6_invariance_mandra.json"), J(R / "strymonas_postD6_balance.json")
    L = [f"# Checkpoint 4b — D6 adopted; Strymonas enhanced re-run under v1.4 + D6; Phase 2 (Valencia 164 mm, Emilia 8-AOI)", "",
         f"Generated {now} by `checkpoint4b_tables.py`. Commits: D6 `{a.d6_commit}` ({a.d6_utc}); bias-box CLI fix `{a.bbox_commit}` ({a.bbox_utc}). "
         "Scores at h > 0.10 m, strict; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides.", ""]
    audit = [f"### GO-D6 + Phase 2 — D6 commit `{a.d6_commit}` ({a.d6_utc}); bias-box CLI fix `{a.bbox_commit}` ({a.bbox_utc}); block generated {now} by `reproduction/v14_rerun/scripts/checkpoint4b_tables.py`", "",
             "**Decisions (Papaioannou, 2026-10-19, GO-D6 + Phase 2):** D6 adopted — v1.4 writes `storecumprcp = 1` whenever curve-number infiltration is on, tests first; provenance + private reproducer for Deltares "
             "(no public issue); Strymonas v3 enhanced re-run under v1.4 + D6 → Checkpoint 4b; Phase 2 (Valencia 164 mm, Emilia 8-AOI) in parallel. The Phase-1 Strymonas-enhanced v1.4 row stays, labelled pre-D6, invalid. Phases 3–5 wait.", ""]
    # ---- D6 tests
    L.append("## D6 tests")
    if tm:
        mb, bd, ni = tm.get("closed_plain_mass_balance", {}), tm.get("multi_day_bounds", {}), tm.get("non_cn_invariance", {})
        line = (f"- D6 tests (`tests/test_d6_cn_bookkeeping.py`, metrics `reproduction/v14_harness/D6_test_metrics.json`): (i) closed CN-76 plain, 30 mm rain + 20 m³/s for 12 h through the v1.4 pipeline path: "
                f"end volume / expected = {mb['v1.4']['ratio']:.5f} ({mb['v1.4']['volume_end_m3']:.0f} of {mb['v1.4']['expected_m3']:.0f} m³; tolerance 0.1 %); v1.3 control {mb['v1.3']['ratio']:.4f}. "
                f"(ii) 180 mm in three daily bursts (rain {bd['rain_end_m'] * 1000:.1f} mm = {bd['rain_end_m'] / bd['S_m']:.2f} S, {bd['n_cells']} cells × {bd['n_times']} hourly maps): max F = I − Ia = {bd['F_max_m'] * 1000:.2f} mm ≤ S = {bd['S_m'] * 1000:.2f} mm; "
                f"smallest hourly increment of cumulative infiltration {bd['min_increment_m'] * 1000:+.4f} mm (monotone); max(cuminf − cumprcp) {bd['max_cuminf_minus_cumprcp_m'] * 1000:+.4f} mm; max |cuminf − SCS curve| {bd['max_abs_dev_from_scs_m'] * 1000:.4f} mm. "
                f"(iii) without curve numbers the flag leaves zs and zsmax bit-identical — synthetic: {ni.get('zs', {}).get('bit_identical')} / {ni.get('zsmax', {}).get('bit_identical')}")
        if inv:
            r = inv["reference_vs_with_flag"]
            line += (f"; Mandra enhanced v1.4 event (`D6_invariance_mandra.json`, {inv['utc_end']}, reference infiltration type '{inv['reference_infiltration_type']}'): zs bit-identical {r['zs']['bit_identical']} "
                     f"(max diff {r['zs']['max_abs_diff_m']} m), zsmax {r['zsmax']['bit_identical']}; the flag only adds {', '.join(r['extra_vars_in_b'])} to the map file")
        line += "."
        L += [line.lstrip("- "), ""]; audit.append(line)
    if a.tests:
        L += [f"Tests: {a.tests}.", ""]; audit.append(f"- Tests at the D6 commit: {a.tests}.")
    prov = ("- D6 provenance (`reproduction/v14_harness/D6_CN_SINK.md` §1, §6): verbatim v2.3.0 source lines; upstream, SFINCS lists the issue in its known issues since 2026-04-02 (`e394b7f02e`) with the same workaround, "
            "the v2.4.0 Galibier release (2026-06-15) still carries it although its notes say fixed, and `main` forces the flag for 'cna'/'cnb' since `360c1592ee` (2026-07-15); no release contains the fix yet. "
            "`reproducer_D6.md` drafted for a private note to Deltares (not sent, no public issue).")
    L += [prov.lstrip("- "), ""]; audit.append(prov)
    # ---- Strymonas
    L += ["## Strymonas v3 enhanced (curve numbers on): pre-D6 kept, v1.4 + D6 added", ""]
    rows, sm = event_table(res, "strymonas_enhanced_postD6", v13_from="strymonas_enhanced", extra_col=("strymonas_enhanced", "v1.4 pre-D6, invalid"))
    L += rows + [""]
    if bal:
        b = bal["budget_Mm3"]; sc = bal["sink_check"]
        L.append(f"Sink check (`strymonas_postD6_balance.json`, {bal['utc']}): cells whose cumulative infiltration exceeds the SCS abstraction or the cumulative rain by > 0.1 mm: {sc['cells_with_cuminf_above_scs_or_rain_by_0p1mm']} "
                 f"({sc['share']:.2%}); max excess {sc['max_excess_mm']:.4f} mm. Cells past Ia: {sc['cells_past_Ia']} ({sc['share_past_Ia']:.1%}) — they now produce runoff instead of swallowing water.")
        L.append(f"Water balance {bal['window_utc'][0][:10]} → {bal['window_utc'][1][:10]} (sub-grid volumes, Mm³): rain {b['rain']}, infiltration {b['infiltration']}, rain runoff {b['rain_runoff']}; "
                 f"discharge in {b['discharge_in']} (Kerkini / Angitis {b['discharge_per_source']}); storage at the end {b['storage_end']} (max {b['storage_max']} at {b['storage_max_time'][:16]}), "
                 f"of which in the floodplain window {bal['storage_end_in_window_Mm3']}; net outflow through the coastal boundary {b['boundary_net_outflow']}. Daily storage: {bal['storage_daily_Mm3']}.")
        L.append("")
        inflow = b["discharge_in"] + b["rain_runoff"]
        days = list(bal["storage_daily_Mm3"].values())
        L += ["**Physical reading.** " +
              f"With the sink gone, the modelled Strymonas flood is discharge-driven, not rain-driven. In the simulated week the two GloFAS inflows deliver {b['discharge_in']:.1f} Mm³ "
              f"(Kerkini outlet {b['discharge_per_source'][0]:.1f}, Angitis {b['discharge_per_source'][1]:.1f}). The domain receives only {b['rain']:.1f} Mm³ of rain ({bal['rain_mm_mean']:.1f} mm on average; most of the event rain falls "
              f"in the 7-day forcing lead-in, which is not simulated), and the curve number absorbs {b['infiltration']:.1f} Mm³ of it, leaving {b['rain_runoff']:.1f} Mm³ of rain runoff, "
              f"{100 * b['rain_runoff'] / inflow:.1f} % of what reaches the surface. Of those {inflow:.1f} Mm³, {b['storage_end']:.1f} Mm³ ({100 * b['storage_end'] / inflow:.0f} %) are still on the land at the end, "
              f"{bal['storage_end_in_window_Mm3']:.1f} Mm³ of them in the Serres floodplain window, and storage still grows by {days[-1] - days[-2]:.1f} Mm³ on the last day; "
              f"the remaining {b['boundary_net_outflow']:.1f} Mm³ ({100 * b['boundary_net_outflow'] / inflow:.0f} %) leave through the Amfipoli gorge to the Strymonian Gulf. "
              "The plain fills like a reservoir faster than the gorge drains it, which is why the run reaches a high hit rate together with a frequency bias well above 1. "
              "In the published run the same discharge disappeared in the 41 % of the domain that the curve-number sink had made absorbing (D6_CN_SINK.md).", ""]
    if sm:
        audit.append(f"- strymonas_enhanced_postD6 (v1.4 + D6): CSI {sm['v14']['csi']:.4f} HR {sm['v14']['hr']:.4f} FAR {sm['v14']['far']:.4f} B {sm['v14']['bias']:.3f} GSS {sm['v14']['gss']:.4f} "
                     f"(TP/FP/FN {sm['v14']['tp']}/{sm['v14']['fp']}/{sm['v14']['fn']}); v1.3 published {sm['pub']['csi']:.4f}, v1.3 new mask {sm['mask']['csi']:.4f}; "
                     f"Δ(v1.4+D6 − v1.3 published) CSI {sm['v14']['csi'] - sm['pub']['csi']:+.4f} HR {sm['v14']['hr'] - sm['pub']['hr']:+.4f} FAR {sm['v14']['far'] - sm['pub']['far']:+.4f}. "
                     + (f"Sink cells {bal['sink_check']['cells_with_cuminf_above_scs_or_rain_by_0p1mm']} ({bal['sink_check']['share']:.2%}); balance (Mm³): rain {bal['budget_Mm3']['rain']}, infiltration {bal['budget_Mm3']['infiltration']}, "
                        f"discharge {bal['budget_Mm3']['discharge_in']}, storage end {bal['budget_Mm3']['storage_end']}, net outflow {bal['budget_Mm3']['boundary_net_outflow']}." if bal else ""))
    # ---- Phase 2
    for run, title, pub in (("valencia_enhanced_164", "Valencia EMSR773, R2 anchored to 164 mm", "R1_verification/task_valencia_anchor/_scoring/score_v164.json"),
                            ("emilia_enhanced_8aoi", "Emilia-Romagna EMSR664, 8-AOI truth", "R1_verification/task_emilia_aoi/_scoring/emilia_rescore.json (full_8aoi)")):
        L += [f"## {title}", ""]
        rec = J(res / f"{run}_record.json") or {}
        exj = J(R / "masks" / f"{rec.get('event', run.split('_')[0])}_exclusion.json")
        if exj:
            L.append(f"Exclusion (`masks/{rec.get('event')}_exclusion.tif`): open sea {exj['open_sea_cells']} cells ({exj['open_sea_km2']} km²; vs the published grid's sea {exj.get('open_sea_gis_vs_tif_symmetric_difference_cells')} cells differ), "
                     f"WorldCover 80 {exj['wc80_cells']} ({exj['wc80_km2']} km², land part {exj['wc80_land_cells']}), union {exj['union_cells']} cells.")
        pc = rec.get("published_record_check") or {}
        L.append(f"Published record check: re-scoring the published output reproduces `{pub}` exactly: {pc.get('identical_tp_fp_fn_tn')} (TP/FP/FN/TN {pc.get('rescored', {}).get('tp')}/{pc.get('rescored', {}).get('fp')}/{pc.get('rescored', {}).get('fn')}/{pc.get('rescored', {}).get('tn')}).")
        L.append("")
        rows, sm = event_table(res, run)
        L += rows
        cp = rec.get("coastal_prep") or {}
        st = {s["step"]: s for s in rec.get("steps", [])}
        L.append(f"| active cells v1.4 / ring / SFINCS s | | | {cp.get('n_active_after_expected')} / {cp.get('n_ring')} / {rec.get('sfincs_total_time_s')} (published {rec.get('published_wallclock_s')}) | | | |")
        L.append("")
        fa = J(res / f"{run}_v13_fa_share.json")
        if fa:
            c = fa["categories"]
            L.append(f"False alarms of the published run ({fa['fa_cells']} cells, {fa['fa_km2']} km²): open sea {c['open_sea']['share_of_fa']:.1%}, WorldCover 80 {c['wc80']['share_of_fa']:.1%} (land part {c['wc80_land']['share_of_fa']:.1%}), "
                     f"inland zb < 0 {c['inland_zb_lt_0']['share_of_fa']:.1%}; union {c['union_all_three']['share_of_fa']:.1%}.")
            L.append("")
        if sm:
            audit.append(f"- {run}: v1.3 published CSI {sm['pub']['csi']:.4f} HR {sm['pub']['hr']:.4f} FAR {sm['pub']['far']:.4f} B {sm['pub']['bias']:.3f} GSS {sm['pub']['gss']:.4f} (TP/FP/FN {sm['pub']['tp']}/{sm['pub']['fp']}/{sm['pub']['fn']}; identical to `{pub}`: {pc.get('identical_tp_fp_fn_tn')}); "
                         f"v1.3 new mask CSI {sm['mask']['csi']:.4f} HR {sm['mask']['hr']:.4f} FAR {sm['mask']['far']:.4f} B {sm['mask']['bias']:.3f} (observed removed {sm['ex'].get('observed_wet_excluded_km2', 0):.2f} km²); "
                         f"**v1.4 new mask CSI {sm['v14']['csi']:.4f} HR {sm['v14']['hr']:.4f} FAR {sm['v14']['far']:.4f} B {sm['v14']['bias']:.3f} GSS {sm['v14']['gss']:.4f}** (TP/FP/FN {sm['v14']['tp']}/{sm['v14']['fp']}/{sm['v14']['fn']}); "
                         f"Δ CSI {sm['v14']['csi'] - sm['pub']['csi']:+.4f} (mask {sm['mask']['csi'] - sm['pub']['csi']:+.4f}); SFINCS {rec.get('sfincs_total_time_s')} s; record `results/{run}_record.json`"
                         + (f"; published false alarms on open sea/WC80/inland zb<0: {fa['categories']['union_all_three']['share_of_fa']:.4f}." if fa else "."))
    L.append("Quick-looks: `reproduction/v14_rerun/quicklook/{strymonas_enhanced_postD6,valencia_enhanced_164,emilia_enhanced_8aoi}_v14_hmax.png`.")
    (R / "CHECKPOINT4b.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
