"""CODE-16 A1/A2 (2026-10-21) — the number-freeze close-out record, written from the JSON records only (nothing typed).

Decisions (DvS, 21 Oct 2026; Papaioannou informed): Checkpoint 7 resolutions (1)-(4) accepted and the ledger
code15/source_points_v142.json is final; the D9 residual items are documented, not fixed (the number freeze stands); the pending
NUMBER_MAP entry (§4.1.1 'peak 118 / ~135') is resolved by replacement; pineios_timevarying_q_v142 has the canonical
configuration and is relabelled 'repeat of the canonical configuration (determinism check)'. CODE-16 A2 also declares the Crete
IMERG Final re-run as the follow-up of the declared R1 deviation.

Writes: the block appended to docs/AUDIT.md (A1), the same block plus the Crete follow-up as the new §9 'Number freeze' of
reproduction/emsr933/rule_ledger.md (A2; the former §9 'Files written at Stage 1' becomes §10), one line in
reproduction/emsr933/timing.md, and code16/freeze_closeout.json (the structured content).
Usage: python -I code16_freeze_closeout.py --repo <worktree> [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

RESOLUTIONS = [  # (number, event, point, what the accepted resolution is) — the facts are read from the ledger notes
    (1, "pineios", "pineios_kalambaka"),
    (2, "valencia", "magro"),
    (3, "emilia", "senio"),
    (4, "emilia", "savio"),
]


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    R = repo / "reproduction" / "v14_rerun"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger = J(R / "code15" / "source_points_v142.json")
    scope = J(R / "code15" / "d8_scope.json")
    d9 = J(R / "code16" / "d9_residuals.json")
    dv15 = J(R / "code15" / "d_volumes_v142.json")
    dv16 = J(R / "code16" / "d_volumes_code16.json")
    d7 = J(R / "code14" / "d7_scope.json")
    strict = lambda run: J(R / "results" / f"{run}_v14_newmask.json")["validation"]["strict_threshold_sweep"]["h>0.10m"]  # noqa: E731
    recs = sorted(R.glob("results/*_v142_record.json"))
    starts = sorted((J(p)["start_utc"], p.name[: -len("_record.json")]) for p in recs)
    first_start, first_run = starts[0]
    first_runs = [r for t, r in starts if t == first_start]
    cfgtxt = lambda run: [ln for ln in (R / "configs" / f"{run}.yaml").read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#") and not any(k in ln for k in ("work_dir", "deliverable_dir", "zip_dir"))]  # noqa: E731
    cfg_same = cfgtxt("pineios_timevarying_q_v142") == cfgtxt("pineios_enhanced_v142")
    note = lambda ev, name: next(n for n in ledger["events"][ev]["notes"] if n["name"] == name)  # noqa: E731
    point = lambda ev, name: next(p for p in ledger["events"][ev]["src_points"] if p["name"] == name)  # noqa: E731
    spoint = lambda ev, name: next(q for e in scope["events"] if e["event"] == ev for q in e["points"] if q["name"] == name)  # noqa: E731

    # ---- (1) the accepted resolutions, from the ledger notes
    res_lines = []
    for k, ev, name in RESOLUTIONS:
        n = note(ev, name); p = point(ev, name); g = n["glofas"]
        win = p.get("window_deg", 0.1)
        inj = f"injected at ({p.get('src_lon', p['lon'])}, {p.get('src_lat', p['lat'])})" if p.get("inject", True) else "**not injected** (inject: false)"
        res_lines.append(f"({k}) **{name}** ({ev}): sampled at ({p['lon']}, {p['lat']}, ±{win}°) → GloFAS cell {tuple(g['network_cell'])}, {g['uparea_km2']:.1f} km², file peak {g['peak_file_m3s']:.1f} m³/s; {inj}. "
                         f"Ledger: {n['change']}")

    # ---- (2) D9 list
    by_id = {it["id"]: it for it in d9["items"]}
    pv = dv15["runs"]["pineios_enhanced_v142"]; pk = {c["name"]: c for c in pv["injected"]["sources"]}
    ev16 = dv16["runs"]["emilia_enhanced_8aoi_v142"]; ek = {c["name"]: c for c in ev16["injected"]["sources"]}
    vv16 = dv16["runs"]["valencia_enhanced_164_v142"]; vk = {c["name"]: c for c in vv16["injected"]["sources"]}
    tit = spoint("pineios", "titarisios"); tit_drain = ((tit.get("injection_cell") or {}).get("drains_to") or {}).get("first_referenced_river_on_path")
    kal = spoint("pineios", "pineios_kalambaka"); kal_dem = (kal.get("injection_cell") or {}).get("dem_m")
    jn = note("valencia", "jucar") if any(n["name"] == "jucar" for n in ledger["events"]["valencia"]["notes"]) else None
    jg = spoint("valencia", "jucar")["glofas_rule_cell"]; mg = note("valencia", "magro")["glofas"]
    lat = by_id["D9-7"]; lst = lat["lattice_shift_test"]; sh = lst["shifts"]
    nest = ledger["events"]["valencia"].get("nested_injected_cells")
    cons = {
        "D9-1": f"the Pineios inflow (injected peak {pk['pineios_trikala']['peak_m3s']:.1f} m³/s, {pk['pineios_trikala']['volume_m3'] / 1e6:.1f} Mm³) enters a floodplain cell {by_id['D9-1']['offset_km']:.2f} km from the Pineios channel and reaches it overland, so part of the inundation between the two is source-location dependent.",
        "D9-2": f"the Titarisios inflow (injected peak {pk['titarisios']['peak_m3s']:.1f} m³/s, {pk['titarisios']['volume_m3'] / 1e6:.1f} Mm³) enters {by_id['D9-2']['offset_km']:.2f} km from the Titarisios channel, on ground that drains to the {', '.join(tit_drain) if tit_drain else '?'}: the lower Titarisios carries no upstream inflow in the model.",
        "D9-3": f"the Ronco inflow (injected peak {ek['ronco']['peak_m3s']:.1f} m³/s, {ek['ronco']['volume_m3'] / 1e6:.1f} Mm³) enters {by_id['D9-3']['offset_km']:.2f} km from the Ronco channel and reaches it overland.",
        "D9-4": f"the Montone inflow (injected peak {ek['montone']['peak_m3s']:.1f} m³/s, {ek['montone']['volume_m3'] / 1e6:.1f} Mm³) enters a valley-floor cell {by_id['D9-4']['offset_km']:.2f} km from the Montone channel; the channel is {by_id['D9-4']['offset_from_yaml_point_km']:.2f} km from the YAML point, " + ("outside" if by_id['D9-4']['offset_from_yaml_point_km'] > 1.0 else "inside") + " the 1 km snap radius.",
        "D9-5": f"the Júcar is sampled at its mouth reach ({jg['uparea_km2']:.1f} km², file peak {jg['peak_file_m3s']:.1f} m³/s), downstream of the Magro confluence; the Magro is injected separately ({mg['uparea_km2']:.1f} km², {vk['magro']['volume_m3'] / 1e6:.1f} Mm³), so its flow is counted twice — bounded by {100 * vk['magro']['volume_m3'] / vv16['injected']['total_volume_m3']:.1f} % of the Valencia injected total ({vv16['injected']['total_volume_m3'] / 1e6:.1f} Mm³). Ledger nesting: {nest}.",
        "D9-6": f"sampled only (file peak {note('pineios', 'pineios_kalambaka')['glofas']['peak_file_m3s']:.1f} m³/s, {note('pineios', 'pineios_kalambaka')['glofas']['uparea_km2']:.1f} km²): its flow is contained in the Trikala series (nested); the YAML injection point lies on an inactive mountainside (DEM {kal_dem} m), outside the model's active grid, so no channel distance is defined.",
        "D9-7": f"the frozen Pineios Open-Meteo series are those of the static-map cell one 0.05° column ({lat['offset_km']:.2f} km at {lat['at_lat']}° N) east of the labelled coordinates (shift test: {sh['rows+0_cols+1']['river_points_on_small_cells']} of {lst['n_river_points']} river points on small cells and {sh['rows+0_cols+1']['dry_points_on_river_cells']} of {lst['n_dry_points']} dry points on river cells with the +1-column mapping, against {sh['rows+0_cols+0']['river_points_on_small_cells']} and {sh['rows+0_cols+0']['dry_points_on_river_cells']} with the containing cell); the series are unchanged, only their river attribution shifts.",
    }
    names = {"D9-1": "Trikala injection", "D9-2": "Titarisios injection", "D9-3": "Ronco injection", "D9-4": "Montone injection", "D9-5": "Júcar sampling (Magro nested)", "D9-6": "Kalambaka source", "D9-7": "Pineios lattice offset"}
    d9_rows = []
    for iid in ("D9-1", "D9-2", "D9-3", "D9-4", "D9-5", "D9-6", "D9-7"):
        it = by_id[iid]
        ic = it.get("snapped_injection_cell") or it.get("unsnapped_injection_point")
        cell = ((f"z_b {ic['zb_m']} m, D8 {ic['d8_uparea_km2']} km² (snapped)" if "snapped_injection_cell" in it else
                 f"YAML point outside the active grid (z_b {'n/a' if ic['zb_m'] is None else ic['zb_m']}), DEM-D8 {ic['d8_uparea_km2']} km²; not injected") if ic else "—")
        off = f"{it['offset_km']:.2f}" if it.get("offset_km") is not None else "n/a"
        d9_rows.append(f"| {iid} | {names[iid]} ({it['event']}) | {off} | {cell} | {cons[iid]} |")

    # ---- (3) the pending-entry resolution (same values as the NUMBER_MAP v1.4.2 cell)
    inj = pv["injected"]; r0 = next(r for r in d7["runs"] if r["run"] == "pineios_enhanced")
    v140 = dv16["runs"]["pineios_enhanced"]; v141 = dv16["runs"]["pineios_enhanced_v141"]
    q141 = next(c["peak_m3s"] for c in v141["injected"]["sources"] if c["name"] == "titarisios")
    c140, c141, ctv, c142 = strict("pineios_enhanced"), strict("pineios_enhanced_v141"), strict("pineios_timevarying_q_v142"), strict("pineios_enhanced_v142")
    same = all(ctv[k] == c142[k] for k in ("tp", "fp", "fn", "tn"))
    pend = (f"§4.1.1 'peak 118 m³ s⁻¹ at Enipeas' / '~135 m³ s⁻¹ coincident' is **resolved by replacement**: the v1.4.2 injected peaks Trikala {pk['pineios_trikala']['peak_m3s']:.1f}, Titarisios {pk['titarisios']['peak_m3s']:.1f}, "
            f"Enipeas {pk['enipeas']['peak_m3s']:.1f} m³/s (combined {inj['combined_peak_m3s']:.1f} m³/s); {inj['total_volume_m3'] / 1e6:.1f} Mm³ injected = {100 * pv['injected_over_rain']:.1f} % of "
            f"{pv['rain_on_active_domain']['rain_volume_m3'] / 1e6:.0f} Mm³ rain on the active domain; the inflow bracket from the release history — v1.4.0 canonical, constant {r0['glofas_domain_mean_m3s']:.3f} m³/s at "
            f"{len(r0['points'])} points ({v140['injected']['total_volume_m3'] / 1e6:.1f} Mm³ = {100 * v140['injected_over_rain']:.1f} % of rain): CSI {c140['csi']:.3f}; v1.4.1 canonical, main stem at the Titarisios point "
            f"(peak {q141:.1f} m³/s; {v141['injected']['total_volume_m3'] / 1e6:.1f} Mm³ = {100 * v141['injected_over_rain']:.1f} % of rain): CSI {c141['csi']:.3f}. "
            f"`pineios_timevarying_q_v142` has the canonical configuration (run config identical to the canonical's outside comments and paths: {cfg_same}; contingency table identical to the canonical's: {same}) and is relabelled everywhere "
            f"**'repeat of the canonical configuration (determinism check)'** (CSI {ctv['csi']:.3f}), not an independent time-varying audit. NUMBER_MAP.md regenerated: 0 entries pending.")
    srcs = ("code15/source_points_v142.json (utc), results/*_v142_record.json (start_utc), code16/d9_residuals.json, code15/d_volumes_v142.json, code16/d_volumes_code16.json, code14/d7_scope.json, "
            "code15/d8_scope.json, results/{pineios_enhanced,pineios_enhanced_v141,pineios_enhanced_v142,pineios_timevarying_q_v142}_v14_newmask.json")
    head = (f"### Number freeze close-out (CODE-16) — author's decisions DvS 2026-10-21 (Papaioannou informed); generated {now} by `reproduction/v14_rerun/scripts/code16_freeze_closeout.py` from {srcs}")
    block = [head, "",
             f"**1. Checkpoint 7 resolutions (1)–(4) accepted; the ledger `code15/source_points_v142.json` is final.** Ledger resolved **{ledger['utc']}**; first v1.4.2 run started **{first_start}** ({', '.join(f'`{r}`' for r in first_runs)} — the earliest start_utc of the {len(recs)} v1.4.2 records).", ""]
    block += [f"- {x}" for x in res_lines] + [""]
    block += ["**2. D9 residual items — documented, not fixed; the number freeze stands** (`code16/d9_residuals.json`, `scripts/d9_residuals.py`; offset = distance from the snapped injection cell to the nearest model cell on the named river's channel: "
              f"cells in the 0.05° footprints of the river's GloFAS v4 cells within {d9['method']['search_km']:.0f} km whose D8 upstream area is ≥ {d9['method']['channel_fraction_of_footprint_max_d8']} × the footprint maximum; footprints crossed by a larger river are skipped). "
              "These measured offsets supersede the rounded prose values of Checkpoint 7.", "",
              "| item | what | offset km | injection cell | consequence |", "|---|---|---|---|---|"] + d9_rows + [""]
    block += [f"**3. Pending NUMBER_MAP entry.** {pend}", ""]
    follow = ["**4. Crete (EMSR933) IMERG Final re-run — declared follow-up of the R1 data-latency deviation.** Configuration: the canonical run `crete_canonical_r2on` unchanged (R2 on, anchor and window as in §8) "
              "except the R1 product: IMERG Final Run V07 (GPM_3IMERGHH) in place of the Late Run V07 (GPM_3IMERGHHL) — `rain_source.product: final`. It is reported as a labelled sensitivity beside the "
              "Late-run canonical and does not replace it (the prospective test is the Late-run configuration as frozen before any score). It runs when the Final Run covers 27 Sep – 7 Oct 2026 "
              "(GES DISC latency, ≈ late January 2027); this declaration is the decision the number freeze requires for that run.", ""]
    audit_block = block + ["The Crete IMERG Final follow-up is declared in `reproduction/emsr933/rule_ledger.md` §9.", ""]
    ledger_block = ["## 9. Number freeze (CODE-16, 2026-10-21)", "", f"(Same block as `docs/AUDIT.md` 'Number freeze close-out (CODE-16)'; generated {now}.)", ""] + block[2:] + follow
    out = {"utc": now, "generator": "reproduction/v14_rerun/scripts/code16_freeze_closeout.py", "ledger_utc": ledger["utc"], "first_v142_run": {"run": first_run, "start_utc": first_start, "n_records": len(recs)},
           "resolutions": res_lines, "d9_rows": d9_rows, "pending_resolution": pend, "timevarying_v142_identical_contingency": same, "timevarying_v142_identical_config": cfg_same, "first_v142_runs": first_runs, "crete_followup": follow[0]}
    if a.dry_run:
        print("\n".join(ledger_block)); return 0
    (R / "code16").mkdir(exist_ok=True)
    (R / "code16" / "freeze_closeout.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    audit = repo / "docs" / "AUDIT.md"
    txt = audit.read_text(encoding="utf-8")
    assert "Number freeze close-out (CODE-16)" not in txt, "AUDIT block already present"
    audit.write_text(txt.rstrip("\n") + "\n\n" + "\n".join(audit_block) + "\n", encoding="utf-8")
    led = repo / "reproduction" / "emsr933" / "rule_ledger.md"
    lt = led.read_text(encoding="utf-8")
    assert "## 9. Files written at Stage 1" in lt and "## 9. Number freeze" not in lt
    lt = lt.replace("## 9. Files written at Stage 1", "\n".join(ledger_block) + "\n## 10. Files written at Stage 1")
    led.write_text(lt, encoding="utf-8")
    tm = repo / "reproduction" / "emsr933" / "timing.md"
    tm.write_text(tm.read_text(encoding="utf-8").rstrip("\n") + "\n" + f"- {now} — CODE-16 A (number-freeze close-out): AUDIT block + rule_ledger.md §9 (Checkpoint 7 resolutions accepted, D9 measured and documented, §4.1.1 entry resolved by replacement, determinism-check relabel, Crete IMERG Final follow-up declared); NUMBER_MAP.md 0 pending; committed as 'code16: freeze close-out'.\n", encoding="utf-8")
    print("AUDIT block appended; ledger §9 inserted (old §9 -> §10); timing line appended; code16/freeze_closeout.json written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
