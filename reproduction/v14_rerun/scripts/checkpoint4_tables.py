"""Checkpoint 4 (GO-C Phase 1) — tables and the AUDIT block, generated from the JSON records; nothing retyped.

Inputs (reproduction/v14_rerun/results/): <run>_v13_publishedmask.json, <run>_v13_newmask.json, <run>_v14_newmask.json,
<run>_record.json, <run>_v13_fa_share.json (enhanced runs); masks/<event>_exclusion.json; v14_harness D5 records.
Outputs: reproduction/v14_rerun/CHECKPOINT4.md and (with --audit-out) a block appended to docs/AUDIT.md.
Usage: python -I checkpoint4_tables.py --repo <worktree> --d5-commit <hash> --d5-utc <UTC> --mask-commit <hash>
       --mask-utc <UTC> [--audit-out docs/AUDIT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

RUNS = [("strymonas", "strymonas_baseline", "strymonas_enhanced", "Strymonas EMSR122 (v3 canonical)"),
        ("mandra", "mandra_baseline", "mandra_enhanced", "Mandra EMSR257"),
        ("pineios", "pineios_baseline_gridmatched", "pineios_enhanced", "Pineios EMSR692 (baseline = grid-matched)")]
METRICS = [("csi", "CSI", 3), ("hr", "HR", 3), ("far", "FAR", 3), ("bias", "B", 2), ("gss", "GSS", 3)]


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def strict(v, key="h>0.10m"):
    return v["validation"]["strict_threshold_sweep"][key]


D4_LABEL = {"strymonas_enhanced": "Strymonas v3 enhanced (2c)", "strymonas_baseline": "Strymonas baseline (1e)",
            "mandra_enhanced": "Mandra enhanced (2b)", "mandra_baseline": "Mandra baseline (1d)",
            "pineios_enhanced": "Pineios enhanced (2a)", "pineios_baseline_gridmatched": "Pineios grid-matched baseline (1c)"}
D6_AFFECTED = {"strymonas_enhanced"}          # Phase-1 runs with curve-number infiltration (D6_CN_SINK.md)


def bnd_points(work: Path):
    import re
    p = work / "pipeline_v14.log"
    if not p.exists():
        return None
    m = re.findall(r"injected water-level boundary: (\d+) bnd points", p.read_text(encoding="utf-8", errors="replace"))
    return int(m[-1]) if m else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--d5-commit", required=True); ap.add_argument("--d5-utc", required=True)
    ap.add_argument("--mask-commit", required=True); ap.add_argument("--mask-utc", required=True)
    ap.add_argument("--audit-out", type=Path)
    ap.add_argument("--tests", default="", help="measured test-suite result, e.g. '82 green (python -m unittest discover -s tests, 290 s)'")
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; masks = R / "masks"
    H = a.repo / "reproduction" / "v14_harness"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d5 = J(H / "D5_synthetic_results.json"); sl = J(H / "pineios_slice_d5_result.json")
    d4j = J(H / "D4_check.json"); d6e = J(H / "D6_strymonas_sink_cells.json")
    L = [f"# Checkpoint 4 — Phase 1 of the harness-v1.4 re-run (generated {now} by `checkpoint4_tables.py`)", "",
         f"Commits: D5 `{a.d5_commit}` ({a.d5_utc}); evaluation-mask exclusion `{a.mask_commit}` ({a.mask_utc}). Scores at h > 0.10 m, strict, "
         "evaluation universe = msk > 0 ∩ AOI union (published) or minus the exclusion (new mask = WorldCover 80 at the cell centre ∪ v1.4 open sea, removed from model and truth).", ""]
    audit = [f"### GO-C Phase 1 — harness v1.4 re-run of Strymonas, Mandra, Pineios (baselines + canonical enhanced); D5 commit `{a.d5_commit}` ({a.d5_utc}), "
             f"evaluation-mask commit `{a.mask_commit}` ({a.mask_utc}); block generated {now} by `reproduction/v14_rerun/scripts/checkpoint4_tables.py`", "",
             "**GO-C decisions (Papaioannou, 2026-10-19), recorded:** (1) option (c) — harness v1.4 for every run: D1 IMERG rate/label, D2 coastal IB (bnd/bzs, pavbnd 101325 Pa), "
             "D4 (open sea inactive, coastal msk=2 ring, every cell starts dry), D5 meteo-grid alignment; D3 text-only. (2) D5 implemented in v1.4 (one function for netamp/netamuamv/netampr). "
             "(3) evaluation mask, all events: exclude WorldCover class 80 ∪ the v1.4 open-sea mask, same rule both sides; the observed-flood area removed is reported. "
             "(4) no simulated lead-in; ONE labelled sensitivity (Strymonas v3, 7-day lead-in simulated) in Phase 3. (5) the eight orphan runs recreated under v1.4 (Phase 3); Strymonas baseline re-run from the committed example. "
             "(6) Crete: rule_ledger.md §8. Execution: Phase 1 → Checkpoint 4 → stop; Phases 2–5 on the author's go. v1.3 numbers are kept beside v1.4 below.", ""]
    if d5 and sl:
        g = d5["linear_pressure_gradient"]; p = d5["rain_pulse_footprint"]
        line = (f"- D5 proof (`reproduction/v14_harness/D5_synthetic_results.json` {g['utc']}, `pineios_slice_d5_result.json` {sl['utc']}): (i) linear pressure gradient, boundary zs vs (101325 − p)/(ρg) at the cell "
                f"centres — aligned RMSE {g['aligned']['rmse']:.4f} m (max {g['aligned']['max']:.4f}), unaligned control RMSE {g['unaligned']['rmse']:.4f} m (meteo cell {abs(g['meteo_cell_m'][0]) / 1000:.1f} km); "
                f"(iii) 30-min IMERG pulse on one cell — aligned centroid offset {p['aligned']['centroid_offset_m'][0]:+.1f}/{p['aligned']['centroid_offset_m'][1]:+.1f} m, relative RMSE {p['aligned']['rel_rmse']:.5f}, "
                f"share inside the written footprint {p['aligned']['frac_inside_model']:.3f} (expected {p['aligned']['frac_inside_expected']:.3f}); unaligned {p['unaligned']['centroid_offset_m'][0]:+.0f}/{p['unaligned']['centroid_offset_m'][1]:+.0f} m "
                f"(half of the {p['meteo_cell_m'][0] / 1000:.1f}-km cell east and south), share {p['unaligned']['frac_inside_model']:.3f}; (ii) one-day Pineios slice with aligned grids: modelled − expected (bilinear at the true centres) "
                f"mean {sl['after_bilinear']['mean_diff_m']:+.5f} m, RMSE {sl['after_bilinear']['rmse_m']:.5f} m, max {sl['after_bilinear']['max_abs_m']:.5f} m, r {sl['after_bilinear']['corr']:.4f}, fit slope {sl['after_bilinear']['fit_slope']:.4f} "
                f"(CODE-12 before: mean {sl['before_nearest_CODE12']['diff_mean_m']:+.4f}, RMSE {sl['before_nearest_CODE12']['diff_rmse_m']:.4f}, r {sl['before_nearest_CODE12']['corr_modelled_vs_expected']:.4f}) — the IB-shortfall item is closed, explained by D5.")
        L += ["## D5 proof", line.lstrip("- "), ""]; audit.append(line)
    d6s, d6e, sd = J(H / "D6_cn_sink_check.json"), J(H / "D6_strymonas_sink_cells.json"), J(R / "strymonas_v14_diagnosis.json")
    if d6s and d6e and sd:
        r0, r1 = d6s["runs"]["storecumprcp_0"], d6s["runs"]["storecumprcp_1"]
        m13, m14 = d6e["models"]["v13_published"], d6e["models"]["v14"]
        ex = sd.get("experiments", {})
        line = (f"- **D6 (new, report only; `reproduction/v14_harness/D6_CN_SINK.md`)**: SFINCS v2.3.0 curve-number infiltration ('cna', the `setup_cn_infiltration` route) adds the infiltration increment to `cuminf` "
                f"only when `storecumprcp = 1` (`sfincs_infiltration.f90:107`; default 0, `sfincs_input.f90:219,439-441`) while `cumprcp` always accumulates (`sfincs_meteo.f90:1266`) and the volume has no floor "
                f"(`sfincs_continuity.f90:~535`): past Ia = 0.2 S a cell removes the whole cumulative infiltration every time step — an unbounded sink for rain and inflow. Synthetic closed plain (`D6_cn_sink_check.json` {d6s['utc']}; CN {d6s['cn']}, "
                f"{d6s['rain_mm']:.0f} mm rain + {d6s['source']['q_m3s']:.0f} m³/s for 12 h): end volume {r0['volume_end_m3']:.0f} m³ with storecumprcp 0 vs {r1['volume_end_m3']:.0f} m³ with 1 (expected {r1['expected_end_m3_correct_scs']:.0f}; ratio {r1['ratio_end_to_expected']:.4f}). "
                f"Strymonas v3 enhanced (`D6_strymonas_sink_cells.json` {d6e['utc']}, inputs only): cells past Ia by the end {m13['sink_km2_end']} km² ({m13['sink_share_end']:.1%}) with the published rain vs {m14['sink_km2_end']} km² ({m14['sink_share_end']:.1%}) with the v1.4 rain; "
                f"Serres-plain window {m13['window']['sink_share_end']:.1%} vs {m14['window']['sink_share_end']:.1%}. Water on land, peak/end (`strymonas_v14_diagnosis.json` {sd['utc']}): published {sd['runs']['v1.3']['V_land_max_Mm3']}/{sd['runs']['v1.3']['V_land_zb_gt_0_daily_Mm3'][-1]} Mm³, "
                f"v1.4 {sd['runs']['v1.4']['V_land_max_Mm3']}/{sd['runs']['v1.4']['V_land_zb_gt_0_daily_Mm3'][-1]} Mm³ for {sd['discharge_Mm3']['simulated_week']} Mm³ of discharge in the simulated week; isolation runs on copies: "
                + "; ".join(f"{k} {v['V_land_max']}/{v['V_land_end']}" for k, v in ex.items())
                + ". The v1.4 Strymonas enhanced score below still contains the sink and is not a valid v1.4 number; the fix (v1.4 `storecumprcp = 1` with CN) awaits the author's decision.")
        L += ["## D6 — curve-number sink (report only)", line.lstrip("- "), ""]; audit.append(line)
    # ---- per-event tables
    audit.append("- Phase-1 scores (h > 0.10 m strict; `reproduction/v14_rerun/results/<run>_{v13_publishedmask,v13_newmask,v14_newmask}.json`):")
    for ev, base, enh, title in RUNS:
        L += [f"## {title}", ""]
        exj = J(masks / f"{ev}_exclusion.json")
        if exj:
            L.append(f"Exclusion (`masks/{ev}_exclusion.tif`, {exj['utc']}): open sea {exj['open_sea_cells']} cells ({exj['open_sea_km2']} km²; v1.4 build vs published gis symmetric difference "
                     f"{exj.get('open_sea_gis_vs_tif_symmetric_difference_cells', 'n/a')} cells), WC80 {exj['wc80_cells']} ({exj['wc80_km2']} km², of which land {exj['wc80_land_cells']}), union {exj['union_cells']} ({exj['union_km2']} km²) on the whole grid.")
            L.append("")
        L += ["| run | metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 new − v1.3 published) | of which mask | of which harness |", "|---|---|---|---|---|---|---|---|"]
        for run in (base, enh):
            v13p, v13n, v14n = J(res / f"{run}_v13_publishedmask.json"), J(res / f"{run}_v13_newmask.json"), J(res / f"{run}_v14_newmask.json")
            if not (v13p and v13n and v14n):
                L.append(f"| {run} | — | missing: {', '.join(k for k, v in (('v13 published', v13p), ('v13 new mask', v13n), ('v14', v14n)) if not v)} | | | | | |"); continue
            s13p, s13n, s14 = strict(v13p), strict(v13n), strict(v14n)
            for key, name, nd in METRICS:
                x, y, z = s13p[key], s13n[key], s14[key]
                L.append(f"| {run} | {name} | {x:.{nd}f} | {y:.{nd}f} | {z:.{nd}f} | {z - x:+.{nd}f} | {y - x:+.{nd}f} | {z - y:+.{nd}f} |")
            A = v14n["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
            L.append(f"| {run} | TP / FP / FN cells | {s13p['tp']} / {s13p['fp']} / {s13p['fn']} | {s13n['tp']} / {s13n['fp']} / {s13n['fn']} | {s14['tp']} / {s14['fp']} / {s14['fn']} | | | |")
            L.append(f"| {run} | eval km² / observed km² | {v13p['validation']['evaluation_area_km2']:.1f} / {v13p['validation']['observed_wet_km2_strict']:.1f} | "
                     f"{v13n['validation']['evaluation_area_km2']:.1f} / {v13n['validation']['observed_wet_km2_strict']:.1f} | {v14n['validation']['evaluation_area_km2']:.1f} / {v14n['validation']['observed_wet_km2_strict']:.1f} | | | |")
            L.append(f"| {run} | modelled wet in eval km² | {(s13p['tp'] + s13p['fp']) * A:.1f} | {(s13n['tp'] + s13n['fp']) * A:.1f} | {(s14['tp'] + s14['fp']) * A:.1f} | | | |")
            fz = lambda v: v["validation"]["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"]  # noqa: E731
            L.append(f"| {run} | fuzzy r=1 CSI | {fz(v13p):.3f} | {fz(v13n):.3f} | {fz(v14n):.3f} | {fz(v14n) - fz(v13p):+.3f} | {fz(v13n) - fz(v13p):+.3f} | {fz(v14n) - fz(v13n):+.3f} |")
            ex = v13n["validation"].get("evaluation_mask_exclusion", {})
            rec = J(res / f"{run}_record.json") or {}
            cp = rec.get("coastal_prep") or {}
            d4 = next((e["A1"] for e in (d4j or {}).get("events", []) if e["label"] == D4_LABEL.get(run)), {})
            L.append(f"| {run} | excluded in eval / observed removed | — | {ex.get('excluded_cells', 'n/a')} cells ({ex.get('excluded_km2', float('nan')):.1f} km²) / {ex.get('observed_wet_excluded_cells', 'n/a')} cells ({ex.get('observed_wet_excluded_km2', float('nan')):.2f} km²) | same mask | | | |")
            L.append(f"| {run} | active cells / msk=2 / bnd points | {d4.get('active', 'n/a')} / {d4.get('msk2', 'n/a')} / 0 | | {cp.get('n_active_after_expected', 'n/a')} / ring {cp.get('n_ring', 'n/a')} / {bnd_points(Path(rec.get('work', '.')))} | | | |")
            L.append(f"| {run} | SFINCS wall-clock s | {rec.get('published_wallclock_s', 'n/a')} (published) | | {rec.get('sfincs_total_time_s', 'n/a')} | | | |")
            if run in D6_AFFECTED:
                L.append(f"| {run} | **D6** | sink on {d6e['models']['v13_published']['sink_share_end']:.0%} of the area | (same output) | sink on {d6e['models']['v14']['sink_share_end']:.0%} — **not a valid v1.4 number** | | | |" if d6e else f"| {run} | **D6** | affected | | affected | | | |")
            audit.append(f"  - {run}: v1.3 published CSI {s13p['csi']:.4f} HR {s13p['hr']:.4f} FAR {s13p['far']:.4f} B {s13p['bias']:.3f} GSS {s13p['gss']:.4f} (TP/FP/FN {s13p['tp']}/{s13p['fp']}/{s13p['fn']}, eval {v13p['validation']['evaluation_area_km2']:.2f} km², observed {v13p['validation']['observed_wet_km2_strict']:.2f} km²); "
                         f"v1.3 rescored with the new mask CSI {s13n['csi']:.4f} HR {s13n['hr']:.4f} FAR {s13n['far']:.4f} B {s13n['bias']:.3f} GSS {s13n['gss']:.4f} (TP/FP/FN {s13n['tp']}/{s13n['fp']}/{s13n['fn']}; excluded {ex.get('excluded_cells')} cells = {ex.get('excluded_km2', 0):.2f} km², observed removed {ex.get('observed_wet_excluded_cells')} cells = {ex.get('observed_wet_excluded_km2', 0):.3f} km²); "
                         f"**v1.4 with the new mask CSI {s14['csi']:.4f} HR {s14['hr']:.4f} FAR {s14['far']:.4f} B {s14['bias']:.3f} GSS {s14['gss']:.4f}** (TP/FP/FN {s14['tp']}/{s14['fp']}/{s14['fn']}, eval {v14n['validation']['evaluation_area_km2']:.2f} km², observed {v14n['validation']['observed_wet_km2_strict']:.2f} km²); "
                         f"Δ(v1.4 new − v1.3 published) CSI {s14['csi'] - s13p['csi']:+.4f} HR {s14['hr'] - s13p['hr']:+.4f} FAR {s14['far'] - s13p['far']:+.4f} (mask alone {s13n['csi'] - s13p['csi']:+.4f} CSI); fuzzy r=1 CSI {fz(v13p):.4f} → {fz(v14n):.4f}; "
                         f"v1.4 build: active {cp.get('n_active_after_expected')} (open sea removed {cp.get('n_exclude')} cells, ring {cp.get('n_ring')}), SFINCS {rec.get('sfincs_total_time_s')} s (published {rec.get('published_wallclock_s')} s); run record `results/{run}_record.json`"
                         + (". **D6: curve-number sink present in both the published and the v1.4 run — the v1.4 value is not a valid v1.4 number (D6_CN_SINK.md).**" if run in D6_AFFECTED else "."))
        L.append("")
        fa = J(res / f"{enh}_v13_fa_share.json")
        if fa:
            c = fa["categories"]
            L.append(f"False alarms of the published v1.3 enhanced run ({fa['fa_cells']} cells, {fa['fa_km2']} km², published mask, h > 0.10 m): on open sea {c['open_sea']['fa_cells']} ({c['open_sea']['share_of_fa']:.1%}), "
                     f"on WC80 {c['wc80']['fa_cells']} ({c['wc80']['share_of_fa']:.1%}; land part {c['wc80_land']['fa_cells']}), on inland zb < 0 {c['inland_zb_lt_0']['fa_cells']} ({c['inland_zb_lt_0']['share_of_fa']:.1%}); union of the three {c['union_all_three']['fa_cells']} ({c['union_all_three']['share_of_fa']:.1%}). "
                     f"Observed cells inside WC80 ∪ open sea: {c['union_open_sea_wc80']['observed_cells_in_eval']} (TP there {c['union_open_sea_wc80']['tp_cells']}).")
            L.append("")
            audit.append(f"  - {enh} false alarms (`results/{enh}_v13_fa_share.json`): {fa['fa_cells']} FA cells; open sea {c['open_sea']['share_of_fa']:.4f}, WC80 {c['wc80']['share_of_fa']:.4f}, inland zb<0 {c['inland_zb_lt_0']['share_of_fa']:.4f}, union {c['union_all_three']['share_of_fa']:.4f}.")
    L.append(f"Quick-look PNGs: `reproduction/v14_rerun/quicklook/<run>_v14_hmax.png`. Timing: `reproduction/emsr933/timing.md`.")
    L.append("The 'v1.3 as published' column re-scores the published outputs with the unchanged validator; for all six runs the contingency tables are identical to the committed records "
             "(reproduction/val_json/{strymonas_v3,strymonas_base,mandra_enh,mandra_base,pineios_enh}.json, grid_matched_baseline/baseline_rescore.json).")
    if a.tests:
        L.append(f"Tests: {a.tests}.")
        audit.append(f"- Tests at the Phase-1 records commit: {a.tests}.")
    audit.append("- Crete decisions written into `reproduction/emsr933/rule_ledger.md` §8 before any Crete run (R2 on canonical with the DEM windward-slope widths, GAP-1 A, GAP-2 2500 m, window 7/3/4, scoring tiers, "
                 "three labelled sensitivities incl. the anchor sweep 224/336/447.8/582 mm and the karst bracket qinf = 0.513 × 447.8 mm / 120 h = 1.914 mm/h from Steiakakis 2018; sources in `karst_recharge_sources.md`).")
    (R / "CHECKPOINT4.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
