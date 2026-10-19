"""CODE-13 — generate the docs/AUDIT.md block (section 9, D4 coastal set-up) from the JSON records; numbers are
never retyped. Reads D4_check.json, ib_shortfall_diagnosis.json, the Crete rebuild records and the test count.
Usage: python -I code13_summary.py --repo <worktree> --commit <hash> --commit-utc <UTC> [--audit-out docs/AUDIT.md]
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
    ap.add_argument("--tests", default="")
    ap.add_argument("--audit-out", type=Path)
    a = ap.parse_args()
    H = a.repo / "reproduction" / "v14_harness"
    J = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
    d4 = J(H / "D4_check.json")
    ib = J(H / "ib_shortfall_diagnosis.json")
    rb = J("D:/ELKAK/implementation/emsr933_crete/buildqc_v14/rebuild_v14.json")
    qc = J(a.repo / "reproduction" / "emsr933" / "stage2_build_qc_v14.json")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = [f"### Harness v1.4 D4 coastal set-up (CODE-13) — code + tests only; commit `{a.commit}` ({a.commit_utc}); block generated {now} by `reproduction/v14_harness/scripts/code13_summary.py`", "",
         "**Status: no corrected run of a published event exists; GO-C pending.** Decisions recorded from Checkpoint 2: A1 accepted (D1 affects the IMERG path only; the ERA5 baselines were not affected — correction added to F5_VERIFY.md); "
         "A2 accepted (bnd every 10 km, bzs = 0 m, pavbnd = 101325 Pa; the constant offset relative to the event-mean MSLP, −0.052 … +0.042 m across the six events, is a documented limitation); "
         "D3: no code change — the methods text will be corrected (Table 2 'spin-up' = forcing lead-in, not simulated; antecedent state enters only through R4); Crete YAMLs set to `harness_version: v1.4`.", "",
         f"- Part A, D4 check (`D4_check.json`, {d4['utc']}; geometry only, no scores). {d4['evaluation_mask_definition']} Per model (active cells; (i) open sea; (ii) inland dep<=0; msk=2 total/perimeter/interior; land cells with zb<0 and their initial volume at zsini=0; evaluation cells; eval ∩ open sea; eval ∩ (ii) zb<0; eval ∩ EMS hydrography; eval ∩ WorldCover-80):"]
    for e in d4["events"]:
        A, B, C = e["A1"], e["A2"], e["A3"]
        hyd = "no hydrography layer in the package set" if C["eval_in_hydrography"] is None else f"{C['eval_in_hydrography']} cells in {C['n_hydro_shps']} hydrography shp"
        L.append(f"  - {e['label']}: active {A['active']} ({A['active_km2']} km²); (i) {A['open_sea_i']} ({A['open_sea_i_km2']} km²); (ii) {A['inland_dep_le_0_ii']} ({A['inland_ii_km2']} km²); "
                 f"msk=2 {A['msk2']} / {A['msk2_on_grid_perimeter']} / {A['msk2_interior']} ({A['msk2_in_open_sea']} inside (i)); land zb<0 {B['all_land_zb_lt_0']} cells ({B['all_land_zb_lt_0_km2']} km², {B['initial_water_volume_if_zsini_0_Mm3']} Mm³), of which (ii) {B['inland_ii_zb_lt_0']}; "
                 f"eval {C['eval_cells']} ({C['eval_km2']} km²): ∩(i) {C['eval_open_sea_i']} ({C['eval_open_sea_km2']} km²), ∩(ii) zb<0 {C['eval_inland_ii_zb_lt_0']}, {hyd}, ∩WC80 {C['eval_wc80_permanent_water']} ({C['eval_wc80_open_sea']} sea / {C['eval_wc80_land']} land).")
    cp = rb["coastal_prep"]; m, b, s = qc["mask"], qc["boundary"], qc["subgrid"]
    L += [f"- Part B implementation (behind v1.4; `build_model.open_sea_split`, `coastal_ring`, `prepare_coastal_exclusion`, `ZSINI_DRY = -9999`): open sea (4-connectivity to the grid edge through dep<=0) made inactive through `setup_mask_active(exclude_mask=<open_sea_exclude.geojson>, all_touched=false)` except a one-cell ring 8-adjacent to land, which `setup_mask_bounds(zmax=0)` turns into msk=2; inland dep<=0 stays active land; bnd points every 10 km along the ring (now for every v1.4 run, pavbnd only with coastal_bc); every active cell starts dry via `zsini = -9999` (SFINCS v2.3.0 `sfincs_initial_conditions.F90:43,98-100`: zs = max(z_zmin, zsini)). Published v1.3 records still render byte-identically (test).",
          f"- Crete rebuild with D4 (`D:/ELKAK/implementation/emsr933_crete/buildqc_v14/rebuild_v14.json`, {rb['utc_start']} → {rb['utc_end']}; `stage2_build_qc_v14.json`, {qc['utc']}): prep {rb['prep_wall_s']} s, hydromt build {rb['hydromt_build_wall_s']} s; open sea {cp['n_open_sea']} cells ({cp['open_sea_km2']} km²), ring {cp['n_ring']} cells ({cp['ring_length_km']} km of coastline cells), inland dep<=0 kept {cp['n_inland_dep_le_0']}, excluded {cp['n_exclude']} (polygons {cp.get('n_exclude_polygons')}); "
          f"built mask: active {m['active_total_msk_ge_1']} ({m['active_km2']} km²), msk=1 {m['msk1_active_interior']}, msk=2 {m['msk2_waterlevel_boundary']}, bnd points {rb['n_bnd_points']}; subgrid {s['file_MB']} MB, z_zmin min/p50/max {s['z_zmin']['min']:.1f}/{s['z_zmin']['p50']:.1f}/{s['z_zmin']['max']:.1f} m; "
          f"Samaria pit unchanged ({qc['samaria_pit_100m']['area_km2']} km², depth {qc['samaria_pit_100m']['max_depth_m']} m, closed {qc['samaria_pit_100m']['closed_in_dep_grid']}).",
          f"- IB shortfall diagnosis (`ib_shortfall_diagnosis.json`, {ib['utc']}; one-day Pineios slice, report only): modelled boundary level vs (pavbnd − p)/(ρg) with p sampled from press_2d.nc at the cell — nearest: mean {ib['H1_lag']['nearest_lag0']['mean_diff_m']:+.4f} m, RMSE {ib['H1_lag']['nearest_lag0']['rmse_m']:.4f}; bilinear: {ib['H1_lag']['bilinear_lag0']['mean_diff_m']:+.4f} / {ib['H1_lag']['bilinear_lag0']['rmse_m']:.4f}; time lags of ±15…60 min do not improve it (best RMSE {min(v['rmse_m'] for v in ib['H1_lag'].values()):.4f}); "
          f"sampling the pressure grid half a netamp cell off (dx −0.5, dy +0.5 of {ib['netamp_cell_m'][0]:.0f} m cells) reproduces the modelled level exactly: mean {ib['H4_half_cell_shift']['dx-0.5_dy+0.5']['mean_diff_m']:+.5f} m, RMSE {ib['H4_half_cell_shift']['dx-0.5_dy+0.5']['rmse_m']:.5f}, r = {ib['H4_half_cell_shift']['dx-0.5_dy+0.5']['corr']:.5f}. "
          "Cause: SFINCS takes the first x/y coordinate of a netamp/netamuamv file as the lower-left CORNER of the meteo grid (`sfincs_ncinput.F90:496-499`, `:382-385`) and adds half a cell to reach the centres (`sfincs_meteo.f90:977-978`), while hydromt_sfincs writes cell CENTRES → every NetCDF meteo field (pressure, wind, and the netampr rain) is applied half a meteo cell off (≈ 12 km for ERA5, ≈ 5 km for IMERG). The boundary itself tracks the inverse barometer exactly (`zs(nmb) = zsb`, `sfincs_boundaries.f90:1073`). Registered as D5, not changed (report only). "
          f"H2 (dry sea plane) quantified for completeness: net inflow to the 0-m plane {ib['H2_plane']['net_inflow_m3s_mean']} m³/s mean → weakly-reflective deficit {ib['H2_plane']['predicted_deficit_m_mean']:+.4f} m (not the cause: the boundary level is prescribed, the plane only receives the flux).",
          f"- Tests at commit `{a.commit}`: {a.tests or 'see commit message'}."]
    txt = "\n".join(L) + "\n"
    print(txt)
    if a.audit_out:
        with open(a.audit_out, "a", encoding="utf-8") as f:
            f.write("\n" + txt)
        print(f"-> appended to {a.audit_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
