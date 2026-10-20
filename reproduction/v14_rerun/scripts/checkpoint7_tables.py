"""Checkpoint 7 (CODE-15, 2026-10-20) — A scope table (D8 source points), B tests + hash, C four-column deltas
(v1.3 / v1.4.1 / v1.4.2 / Δ) for every v1.4.2 re-run, D volumes, E branch reconciliation; from the JSON records, nothing
retyped. Also the AUDIT.md results block (--audit-out).

Inputs: reproduction/v14_rerun/{results,code15,phase4}/*.json; code15/E_branch_done.md (narrative: git steps and hashes).
Usage: python -I checkpoint7_tables.py --repo <worktree> [--tag v1.4.2 --tag-commit <hash>] [--fix-commit <hash>] [--tests "..."] [--audit-out docs/AUDIT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

V142_BASES = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5", "pineios_timevarying_q",
              "emilia_enhanced_8aoi", "valencia_enhanced_164", "valencia_raw_imerg",
              "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_leadin7d", "strymonas_v1_prefix_src"]
V141_BASES = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5"]
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


def published_csi(res: Path, base: str):
    r0 = J(res / f"{base}_record.json") or {}
    pub = (r0.get("published_strict") or {}).get("csi")
    if pub is None:
        pub = ((r0.get("published_record_check") or {}).get("published") or {}).get("csi")
    if pub is None:
        for src in (base, "strymonas_enhanced" if base == "strymonas_enhanced_postD6" else None):
            if src:
                sp_ = strict(J(res / f"{src}_v13_publishedmask.json"))
                if sp_:
                    pub = sp_["csi"]; break
    if pub is None and base.startswith("strymonas_v1_prefix"):
        pub = ((r0.get("published_text") or {}).get("csi"))
    return pub


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tag", default=""); ap.add_argument("--tag-commit", default=""); ap.add_argument("--fix-commit", default="")
    ap.add_argument("--tests", default="")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; C15 = R / "code15"; P4 = R / "phase4"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = ["# Checkpoint 7 — CODE-15: D8 source-point resolution (harness v1.4.2), final re-runs, volumes, branch reconciliation — the number freeze", "",
         f"Generated {now} by `checkpoint7_tables.py`." + (f" Fix commit `{a.fix_commit}`." if a.fix_commit else "") + (f" Tag `{a.tag}` = commit `{a.tag_commit}`." if a.tag else "")
         + " Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside; "
           "the v1.4.1 column is the v1.4.1 re-run where one exists, otherwise the v1.4.0 record (identical sampling for those runs).", ""]
    audit = [f"### Harness v1.4.2 (CODE-15) — results; block generated {now} by `reproduction/v14_rerun/scripts/checkpoint7_tables.py`" + (f"; tag `{a.tag}` = `{a.tag_commit}`" if a.tag else "") + (f"; fix commit `{a.fix_commit}`" if a.fix_commit else ""), ""]
    # ---- A
    sc = J(C15 / "d8_scope.json"); led = J(C15 / "source_points_v142.json")
    L += ["## A. D8 source-point scope (no runs; `code15/d8_scope.{json,md}`, `scripts/d8_scope.py`; river membership from the GloFAS v4 static maps)", ""]
    if sc:
        L += ["| event | point | YAML (sampling; injection) | ±0.1° rule cell → network cell, river [km²], peak | injection cell z_b / msk | lowest-z_b active channel cell within 1 km | flags |", "|---|---|---|---|---|---|---|"]
        n_flag = 0
        for ev in sc["events"]:
            for P in ev["points"]:
                g = P["glofas_rule_cell"]; inj = P["injection_cell"]; lz = P["lowest_zb_active_channel_within_1km"]; y = P["yaml"]
                n_flag += int(bool(P["flags"]))
                L.append(f"| {ev['event']} | {P['name']} | ({y['lon']}, {y['lat']}); ({y['src_lon']}, {y['src_lat']}) | ({g['file_coord'][0]}, {g['file_coord'][1]}) → ({g['network_cell'][0]}, {g['network_cell'][1]}), {', '.join(g['rivers']) or '—'} [{g['uparea_km2']}], {g['peak_in_window_m3s']} | "
                         f"{inj['zb_m'] if inj['zb_m'] is not None else 'inactive (DEM ' + str(inj['dem_m']) + ')'} / {inj['msk']} | " + (f"({lz['cell_lonlat'][0]}, {lz['cell_lonlat'][1]}) z_b {lz['zb_m']}, {lz['distance_m']} m, D8 {lz['uparea_km2']} km²" if lz else "none") + f" | {'; '.join(x.split(':')[0] for x in P['flags']) if P['flags'] else '—'} |")
        pin = next((e for e in sc["events"] if e["event"] == "pineios"), {})
        sh = (pin.get("lattice_shift_test") or {})
        L += ["", f"{n_flag} of {sum(len(e['points']) for e in sc['events'])} points carry at least one flag (full text in `code15/d8_scope.md`). "
              + (f"Pineios lattice offset test: best shift `{sh.get('best_shift')}` ({sh.get('shifts', {}).get(sh.get('best_shift', ''), {})}) against the containing cell {sh.get('shifts', {}).get('rows+0_cols+0', {})}." if sh else ""), ""]
        audit.append(f"- A scope (`code15/d8_scope.json`): {n_flag} of {sum(len(e['points']) for e in sc['events'])} named points flagged; Open-Meteo lattice of the frozen Pineios file offset by one 0.05° cell in longitude (best shift {sh.get('best_shift')}).")
    if led:
        L += ["### Resolved v1.4.2 source points (`code15/source_points_v142.{json,md}`, resolved " + led["utc"] + "; the single source of the v1.4.2 configs)", "",
              "| event | point | sampling (lon, lat, ±window) | injection (lon, lat) | inject | network cell, river, km², peak | change |", "|---|---|---|---|---|---|---|"]
        for ev, d in led["events"].items():
            for q, n in zip(d["src_points"], d["notes"]):
                g = n["glofas"]
                L.append(f"| {ev} | {q['name']} | ({q['lon']}, {q['lat']}, ±{q.get('window_deg', 0.1)}°) | ({q.get('src_lon', q['lon'])}, {q.get('src_lat', q['lat'])}) | {q.get('inject', True)} | ({g['network_cell'][0]}, {g['network_cell'][1]}), {n['named_river']}, {g['uparea_km2']}, {g['peak_file_m3s']} | {n['change'][:160]}{'…' if len(n['change']) > 160 else ''} |")
            if d.get("nested_injected_cells"):
                L.append(f"| {ev} | | | | | nested injected cells: {', '.join(d['nested_injected_cells'])} | left as is (reported) |")
        L.append("")
    # ---- B
    L += ["## B. D8 fix — harness v1.4.2 (`skill/scripts/{prep_q_at_outlets,build_model,download_glofas,download_glofas_openmeteo,glofas_area,source_snap}.py`)", "",
          "- (1) per-point windows / cells (`window_deg`, `inject`) from the ledger; (2) request area covering every sampling window (`glofas_area.request_area`, lattice anchored, explicit point count), Pineios lattice re-downloaded "
          "(every frozen cell identical, Kalambaka window unclipped); (3) build-time snap `source_snap.snap_source` (lowest-z_b active channel cell within 1 km, channel = D8 upstream area ≥ ½ the largest within the radius; "
          "no active cell = hard error; `model/sfincs_src_snap.json`); (4) `DuplicateCellError` under harness v1.4. v1.3 unchanged.",
          f"- Fix commit `{a.fix_commit}`; tests: {a.tests or 'see AUDIT.md'}.", ""]
    audit.append(f"- B fix commit `{a.fix_commit}`; tests {a.tests}.")
    # ---- C
    L += ["## C. v1.4.2 re-runs — four columns (v1.3 published / v1.4.1 / v1.4.2 / Δ = v1.4.2 − v1.4.1)", "",
          "| run | event | CSI v1.3 publ. | CSI v1.4.1 (src) | CSI v1.4.2 | ΔCSI | HR v1.4.1 → v1.4.2 (Δ) | FAR (Δ) | B (Δ) | GSS v1.4.1 → v1.4.2 | TP/FP/FN v1.4.2 | wet km² v1.4.1 → v1.4.2 | SFINCS s v1.4.2 | injected peaks m³/s (v1.4.2) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    pending = []
    for b in V142_BASES:
        prev = f"{b}_v141" if b in V141_BASES else b
        r1, r2 = J(res / f"{prev}_record.json"), J(res / f"{b}_v142_record.json")
        v1, v2 = J(res / f"{prev}_v14_newmask.json"), J(res / f"{b}_v142_v14_newmask.json")
        s1, s2 = strict(v1), strict(v2)
        pub = published_csi(res, b)
        ev = (r2 or r1 or {}).get("event", "")
        if not (s1 and s2):
            L.append(f"| {b}_v142 | {ev} | {f(pub)} | {f(s1 and s1['csi'])} ({prev}) | pending | | | | | | | | | |"); pending.append(b); continue
        d = {k: s2[k] - s1[k] for k, _, _ in M}
        snap = (r2 or {}).get("src_snap") or {}
        qc = ((r2 or {}).get("q_outlet_cells") or {}).get("points", [])
        peaks = ", ".join(f"{p['name']} {p['column_peak_m3s']:.1f}" + ("" if p.get("inject", True) else " (not injected)") for p in qc)
        L.append(f"| {b}_v142 | {ev} | {f(pub)} | {s1['csi']:.3f} ({prev}) | **{s2['csi']:.3f}** | {d['csi']:+.3f} | {s1['hr']:.3f} → {s2['hr']:.3f} ({d['hr']:+.3f}) | {s1['far']:.3f} → {s2['far']:.3f} ({d['far']:+.3f}) | "
                 f"{s1['bias']:.2f} → {s2['bias']:.2f} ({d['bias']:+.2f}) | {s1['gss']:.3f} → {s2['gss']:.3f} | {s2['tp']}/{s2['fp']}/{s2['fn']} | {wet(v1):.0f} → {wet(v2):.0f} | {(r2 or {}).get('sfincs_total_time_s')} | {peaks} |")
        audit.append(f"- {b}: v1.3 published CSI {f(pub, 4)}; {prev} CSI {s1['csi']:.4f} HR {s1['hr']:.4f} FAR {s1['far']:.4f} B {s1['bias']:.3f} GSS {s1['gss']:.4f}; **v1.4.2 CSI {s2['csi']:.4f} HR {s2['hr']:.4f} FAR {s2['far']:.4f} B {s2['bias']:.3f} GSS {s2['gss']:.4f}** "
                     f"(TP/FP/FN {s2['tp']}/{s2['fp']}/{s2['fn']}); Δ(v1.4.2 − {prev}) CSI {d['csi']:+.4f} HR {d['hr']:+.4f} FAR {d['far']:+.4f} B {d['bias']:+.3f}; SFINCS {(r2 or {}).get('sfincs_total_time_s')} s; sources {peaks}; records `results/{b}_v142_*.json`.")
    # identical-config check: pineios_timevarying_q_v142 vs pineios_enhanced_v142
    va, vb = strict(J(res / "pineios_enhanced_v142_v14_newmask.json")), strict(J(res / "pineios_timevarying_q_v142_v14_newmask.json"))
    if va and vb:
        same = all(va[k] == vb[k] for k in ("tp", "fp", "fn", "tn"))
        L += ["", f"Determinism check: `pineios_timevarying_q_v142` has the same configuration as `pineios_enhanced_v142` (the audit rebuild hook is superseded by the pipeline's own series); identical TP/FP/FN/TN: **{same}**."]
        audit.append(f"- pineios_timevarying_q_v142 vs pineios_enhanced_v142 (same configuration): identical contingency table {same}.")
    ce_md = P4 / "cross_event_v14_v142.md"
    if ce_md.exists():
        L += ["", "### Cross-event tables with the v1.4.2 canonical runs (`phase4/cross_event_v14_v142.{json,md}`)", ""] + [ln for ln in ce_md.read_text(encoding="utf-8").splitlines() if not ln.startswith("# ")]
    L.append("")
    # ---- D
    L += ["## D. Injected discharge vs rain / observed flood volumes (`code15/d_volumes_v142.{json,md}`)", ""]
    dv = J(C15 / "d_volumes_v142.json")
    if dv:
        dmd = (C15 / "d_volumes_v142.md").read_text(encoding="utf-8").splitlines()
        L += [ln for ln in dmd if not ln.startswith("# ")] + [""]
        for run, ev in dv["runs"].items():
            inj = ev["injected"]; rain = ev["rain_on_active_domain"]
            audit.append(f"- D {run}: injected peaks " + ", ".join(f"{c['name']} {c['peak_m3s']:.2f}" for c in inj["sources"]) + f" m³/s; total injected {inj['total_volume_m3'] / 1e6:.3f} × 10⁶ m³ over {inj['window'][0]}..{inj['window'][1]}; "
                         f"rain on the active domain ({rain['active_area_km2']:.1f} km²) {rain['rain_volume_m3'] / 1e6:.2f} × 10⁶ m³ (mean {rain['mean_depth_over_active_mm']:.1f} mm); injected/rain {100 * ev['injected_over_rain']:.2f} %"
                         + (f"; observed area {ev['observed_flood_proxy']['observed_area_km2']:.2f} km², modelled volume inside it {ev['observed_flood_proxy']['modelled_volume_inside_observed_extent_m3'] / 1e6:.2f} × 10⁶ m³, injected/that {100 * ev['injected_over_proxies']['modelled_volume_inside_observed_extent_m3']:.1f} %" if "observed_flood_proxy" in ev else "") + ".")
    else:
        L += ["pending", ""]
    # ---- E
    p = C15 / "E_branch_done.md"
    L += ["## E. Branch reconciliation (F_branch_plan.md executed; no push)", ""] + (p.read_text(encoding="utf-8").splitlines() if p.exists() else ["pending"]) + [""]
    if p.exists():
        audit.append("- E branch reconciliation: see `reproduction/v14_rerun/code15/E_branch_done.md` (reproduced in CHECKPOINT7.md).")
    # ---- figures, NUMBER_MAP, timing
    figs = sorted((P4 / "figures").glob("*v142*.png"))
    L += ["## Figures (v1.4.2 products beside the earlier ones, `phase4/figures/`)", ""] + [f"- `{x.name}`" for x in figs] + ([] if figs else ["none yet"]) + [""]
    nm = R / "NUMBER_MAP.md"
    if nm.exists():
        lines = nm.read_text(encoding="utf-8").splitlines()
        rows = [ln for ln in lines if ln.startswith("| ") and not ln.startswith("| location")]
        hdr = next((ln for ln in lines if ln.startswith("| location")), "")
        n142 = sum(1 for ln in rows if "| = v1.4.1 |" not in ln) if "v1.4.2" in hdr else None
        L += ["## NUMBER_MAP.md", "", f"`reproduction/v14_rerun/NUMBER_MAP.md`: {len(rows)} entries" + (f"; v1.4.2 column present, {n142} entries differ from v1.4.1" if n142 is not None else "") + f"; {sum(1 for ln in rows if 'pending' in ln)} pending.", ""]
        audit.append(f"- NUMBER_MAP.md: {len(rows)} entries" + (f", {n142} differ under v1.4.2" if n142 is not None else "") + ".")
    recs = {x.stem.replace("_record", ""): J(x) for x in sorted(res.glob("*_v142_record.json"))}
    L += ["## Timing (phase-7 records)", "", "| run | start UTC | end UTC | SFINCS s | published SFINCS s |", "|---|---|---|---|---|"]
    for k, v in recs.items():
        if v and v.get("phase") == 7:
            L.append(f"| {k} | {v.get('start_utc')} | {v.get('end_utc')} | {v.get('sfincs_total_time_s')} | {v.get('published_wallclock_s')} |")
    if a.tests:
        L += ["", f"Tests: {a.tests}."]; audit.append(f"- Tests: {a.tests}.")
    if pending:
        L += ["", f"Pending v1.4.2 re-runs: {', '.join(pending)}."]
    (R / "CHECKPOINT7.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(audit) + "\n")
        print(f"\nAUDIT block appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
