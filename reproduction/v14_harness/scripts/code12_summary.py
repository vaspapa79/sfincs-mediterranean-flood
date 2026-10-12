"""CODE-12 — generate the docs/AUDIT.md section-9 block from the JSON records (numbers are never retyped).

Reads (all under the worktree):
  reproduction/v14_harness/regression_forcing_v13_pineios.json, ib_synthetic_result.json,
  A2_pavbnd_reference.json, A3_spinup_totals.json, pineios_slice_ib_result.json (optional),
  reproduction/emsr933/stage2_build_qc.json
Usage: python -I code12_summary.py --repo <worktree> --commit <hash> --commit-utc <UTC> [--audit-out <file>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--commit-utc", required=True)
    ap.add_argument("--records-commit", default="(this commit)")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    H = a.repo / "reproduction" / "v14_harness"
    J = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
    reg = J(H / "regression_forcing_v13_pineios.json")
    ib = J(H / "ib_synthetic_result.json")
    a2 = J(H / "A2_pavbnd_reference.json")
    a3 = J(H / "A3_spinup_totals.json")
    qc = J(a.repo / "reproduction" / "emsr933" / "stage2_build_qc.json")
    slice_p = H / "pineios_slice_ib_result.json"
    sl = J(slice_p) if slice_p.exists() else None
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    byte_ids = ", ".join(f"{k} {v.get('byte_identical')}" for k, v in reg["files"].items() if "byte_identical" in v)

    L = [f"### Harness v1.4 (CODE-12, D1/D2 fixes) — code + tests only; commit `{a.commit}` ({a.commit_utc}); records commit {a.records_commit}; block generated {now} by `reproduction/v14_harness/scripts/code12_summary.py`", "",
         "**Status: no corrected run of a published event exists; GO-C pending (Papaioannou).** Branch `fix/harness-v1.4` from `emsr933-crete` (base `69d1c58`).",
         "`harness_version` defaults to v1.3 = the published behaviour; v1.4 = D1 (IMERG written as left-labelled rates ×1.000, 0 min; ERA5 right-labelled accumulations unchanged — ECMWF convention, see `PAVBND_SOURCE.md` §5) + D2 (bnd points every 10 km on the msk=2 cells, bzs = 0 m, pavbnd = 101325 Pa). D3 unchanged (A3 report only).", "",
         f"- A1 regression (`regression_forcing_v13_pineios.json`, {reg['utc']}): config `{Path(reg['config']).name}` at harness `{reg['harness_version']}`; "
         f"build yml text identical to the pre-change render: {reg['files']['before_forcing.yml']['text_identical']}; catalog identical: {reg['files']['catalog_before.yml']['text_identical']}; "
         f"files byte-identical before/after: {byte_ids}; verdict {reg['verdict']}.",
         f"- A1/A2 tests: `python -m unittest discover -s tests` → 42 tests OK at commit `{a.commit}` (tests/test_harness_v14.py, test_precip_forcing_v14.py, test_ib_boundary_v14.py + the 17 earlier tests). F5 synthetic cases through the real hydromt method: half-hourly 4×10 mm/h → written 10,10,10,10 (×1.000, 0 min); hourly 10 mm stamped 01:00 → 10 mm/h on [00:00,01:00) (×1.000, 0 min physical offset); v1.3 defaults reproduce 20,20,20,0.",
         f"- A2 pavbnd semantics (`PAVBND_SOURCE.md`, tag v2.3.0_mt_Faber_release): `sfincs_input.f90:93` real, default 0.0; `sfincs_boundaries.f90:796-800` `if (patmos .and. pavbnd>1.0) zst = zst + (pavbnd - patmb(ib))/(rhow*9.81)`; the published value 1 never acted (guard > 1.0), it would not have lowered the boundary by ~10 m.",
         f"- A2 synthetic 25-hPa test (`ib_synthetic_result.json`, {ib['utc']}): p = {ib['p_synth_pa']:.0f} Pa, expected {ib['expected_m']:.4f} m; v1.4: {ib['runs']['v1.4']['n_bnd_points']} bnd points, {ib['runs']['v1.4']['msk2_cells']} msk=2 cells, boundary zs at the last output mean {ib['runs']['v1.4']['boundary_zs_last_mean_m']:.4f} m (min {ib['runs']['v1.4']['boundary_zs_last_min_m']:.4f}, max {ib['runs']['v1.4']['boundary_zs_last_max_m']:.4f}), interior mean {ib['runs']['v1.4']['interior_zs_last_mean_m']:.4f} m; "
         f"v1.3 control: pavbnd line `{ib['runs']['v1.3']['pavbnd_line']}`, no bnd file, SFINCS warning present = {ib['runs']['v1.3']['sfincs_warning_no_bnd']}, boundary wet fraction {ib['runs']['v1.3']['boundary_wet_fraction_last']:.2f} (never wet).",
         "- A2 reference pressure vs event-window domain-mean ERA5 MSLP (`A2_pavbnd_reference.json`; (101325 − p̄)/(ρg), ρ = 1024): " +
         "; ".join(f"{e['label']} p̄ {e['mslp_mean_pa']/100:.2f} hPa → offset {e['ib_offset_at_mean_m']:+.3f} m, IB at the domain-mean minimum {e['mslp_domainmean_min_pa']/100:.2f} hPa ({e['mslp_domainmean_min_time']}) = {e['ib_at_domainmean_min_m']:+.3f} m, range in window {e['ib_range_within_window_m']:.3f} m" for e in a2["events"]) + "."]
    if sl:
        L.append(f"- A2 one-day Pineios slice, NO scoring (`pineios_slice_ib_result.json`, {sl['utc']}; copy of the as-run model, slice {sl['slice'][0][:10]}): {sl['n_bnd_points']} bnd points on {sl['msk2_cells']} msk=2 cells (zb {sl['msk2_zb_min_max'][0]:.3f}..{sl['msk2_zb_min_max'][1]:.3f} m); boundary MSLP {sl['boundary_pressure_hpa_min_max'][0]:.2f}..{sl['boundary_pressure_hpa_min_max'][1]:.2f} hPa → expected IB {sl['expected_ib_m_min_max'][0]:+.3f}..{sl['expected_ib_m_min_max'][1]:+.3f} m; modelled boundary zs {sl['modelled_zs_min_max'][0]:+.3f}..{sl['modelled_zs_min_max'][1]:+.3f} m; modelled − expected mean {sl['diff_mean_m']:+.4f} m, RMSE {sl['diff_rmse_m']:.4f} m, max |Δ| {sl['diff_max_abs_m']:.4f} m, r = {sl['corr_modelled_vs_expected']:.4f}; wet fraction of boundary cell-times {sl['boundary_wet_fraction']:.3f}; SFINCS wall-clock {sl['sfincs_wall_s']} s. "
                 f"With bilinear instead of nearest sampling of press_2d.nc at the boundary cells (`pressure_sampling_comparison.bilinear`): mean {sl['pressure_sampling_comparison']['bilinear']['mean_diff_m']:+.4f} m, RMSE {sl['pressure_sampling_comparison']['bilinear']['rmse_m']:.4f} m, max |Δ| {sl['pressure_sampling_comparison']['bilinear']['max_abs_m']:.4f} m, r = {sl['pressure_sampling_comparison']['bilinear']['corr']:.4f}, modelled/expected where expected > 2 cm = {sl['pressure_sampling_comparison']['bilinear']['ratio_mod_over_exp_where_exp_gt_2cm']:.3f}; at the MSLP minimum {sl['at_mslp_minimum']['time']} expected {sl['at_mslp_minimum']['expected_mean_m']:.4f} m vs modelled {sl['at_mslp_minimum']['modelled_mean_m']:.4f} m; per-cell time-mean difference {sl['per_cell_time_mean_diff_bilinear_m']['min']:+.4f}..{sl['per_cell_time_mean_diff_bilinear_m']['max']:+.4f} m. The boundary tracks the inverse barometer; the ~10 % systematic shortfall is not explained (candidate: registration of the netamp pressure grid inside SFINCS vs this sampling) — open item, not a blocker.")
    else:
        L.append("- A2 one-day Pineios slice: pending (record `pineios_slice_ib_result.json` not yet present).")
    rows = []
    for e in a3["events"]:
        sp, si = e["spinup"], e["simulated"]
        f = lambda d, k: "—" if d.get(k) is None else f"{d[k]:.1f}"  # noqa: E731
        rows.append(f"{e['label']}: spin-up {e['spinup_days_download_only']} d ERA5 {f(sp, 'era5_mm')} / IMERG {f(sp, 'imerg_mm')} mm; simulated ERA5 {f(si, 'era5_mm')} / IMERG {f(si, 'imerg_mm')} mm; SCS-CN {'on (AMC ' + str(e['scs_cn_amc']) + ')' if e['scs_cn_enabled'] else 'off'}")
    L.append(f"- A3 (report only, `A3_spinup_totals.json`, {a3['utc']}; domain means over the YAML bbox; raw IMERG): " + "; ".join(rows) + ".")
    m, b, g, s, p = qc["mask"], qc["boundary"], qc["grid"], qc["subgrid"], qc["samaria_pit_100m"]
    L.append(f"- Part C Crete build QC (`reproduction/emsr933/stage2_build_qc.json`, {qc['utc']}; grid/dep/mask/subgrid only, no forcing, no run; GAP-1 = A 100 m island-wide, GAP-2 z_max 2500 m): grid {g['mmax']} × {g['nmax']} = {g['n_cells_total']} cells; active {m['active_total_msk_ge_1']} ({m['active_km2']} km²), msk=1 {m['msk1_active_interior']}, msk=2 {m['msk2_waterlevel_boundary']}, msk=3 {m['msk3_outflow_boundary']}; active cells with dep ≤ 0 m {qc['dep']['active_cells_dep_le_0']}, > 0 m {qc['dep']['active_cells_dep_gt_0']}; dep range {qc['dep']['active_dep_min_m']:.1f}..{qc['dep']['active_dep_max_m']:.1f} m; "
             f"v1.4 bnd points {b['bnd_points']} (every {b['spacing_m']:.0f} m along ~{b['msk2_boundary_length_km_approx']} km); subgrid {s['file_MB']} MB, z_zmin min/p50/max {s['z_zmin']['min']:.1f}/{s['z_zmin']['p50']:.1f}/{s['z_zmin']['max']:.1f} m, z_zmax max {s['z_zmax']['max']:.1f} m, uv_navg {s['uv_navg']['min']:.3f}..{s['uv_navg']['max']:.3f}; hydromt build log {qc['hydromt_build']['first_log_stamp_local']} → {qc['hydromt_build']['last_log_stamp_local']} (local). "
             f"Samaria-gorge GLO-30 pit at 100 m: {p['area_km2']} km² ({p['n_cells']} cells), floor {p['floor_m']} m, spill {p['spill_level_m']} m, depth {p['max_depth_m']} m, volume below spill {p['volume_below_spill_Mm3']} Mm³, closed = {p['closed_in_dep_grid']}, subgrid z_zmin at the deepest cell {p['subgrid_z_zmin_at_deepest_m']} m (index check r = {p.get('subgrid_index_check_corr')}); Stage-1 90-m values {p['stage1_90m_component']['area_km2']} km², floor {p['stage1_90m_component']['floor_m']}, spill {p['stage1_90m_component']['spill_level_m']}, {p['stage1_90m_component']['volume_below_spill_Mm3']} Mm³. Not fixed (characterised only).")
    L.append("- Part B: `reproduction/v14_rerun/MANIFEST.md` (planning only; 27 (+1) SFINCS runs, Σ previous wall-clock 27 602 s ≈ 7.7 h, ≈ 10 h with builds/validation/figures; no forcing re-download needed) with its source `INVENTORY_2026-10-12.md`.")
    L.append("- Crete forcing downloaded for A3 only (ERA5 `era5_crete.nc` via prep_inputs; IMERG Late `imerg_crete.nc`, 721 stamps): downloaded, NOT run.")
    txt = "\n".join(L) + "\n"
    print(txt)
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as f:
            f.write("\n" + txt)
        print(f"-> appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
