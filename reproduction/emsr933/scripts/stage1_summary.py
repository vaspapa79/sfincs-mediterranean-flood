"""CODE-10 Stage 1 — generate the docs/AUDIT.md §8 Stage-1 block from the JSON records (no retyping).

Sources (all in reproduction/emsr933/): stage1_yaml_validation.json, stage1_terrain.json,
stage1_depressions.json, regression_f2f4.json, f5/F5_abc.json, f5/F5_d.json, f5/F5_e.json, f5/F5_f.json,
ems_snapshot_*_products.csv. Usage:
  python -I stage1_summary.py --dir <reproduction/emsr933> --commit <hash> --audit-out <file>
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--audit-out", required=True, type=Path)
    a = ap.parse_args()
    d = a.dir
    val = J(d / "stage1_yaml_validation.json")
    ter = J(d / "stage1_terrain.json")
    dep = J(d / "stage1_depressions.json")
    reg = J(d / "regression_f2f4.json")
    abc = J(d / "f5/F5_abc.json")
    f5d = J(d / "f5/F5_d.json")
    f5e = J(d / "f5/F5_e.json")
    f5f = J(d / "f5/F5_f.json")
    prod = list(csv.DictReader(sorted(d.glob("ems_snapshot_*_products.csv"))[-1].open(encoding="utf-8")))

    enh = val["configs"]["emsr933_crete_enhanced.yaml"]
    base = val["configs"]["emsr933_crete.yaml"]
    B = [f"### EMSR933 Crete — Stage 1 (rule ledger, no model runs; commit `{a.commit}`, records in `reproduction/emsr933/`)",
         f"- Harness changes approved at Checkpoint 0 (F2/F4): `ems.include_del_product` switch (default off) and "
         f"`rain_source.product: late|final`; regression `regression_f2f4.json` ({reg['utc']}): Valencia full block vs "
         f"`_scoring/score_v164.json` **{reg['events']['valencia_emsr773']['full_block_vs_score_v164']}**, condensed vs reports "
         f"**{reg['events']['valencia_emsr773']['condensed_vs_reports_json']}** (CSI@0.10 {reg['events']['valencia_emsr773']['csi_0p10']:.6f}); "
         f"Emilia condensed vs reports **{reg['events']['emilia_emsr664']['condensed_vs_reports_json']}**, contingency vs rescore "
         f"**{reg['events']['emilia_emsr664']['contingency_vs_emilia_rescore']}** (CSI@0.10 {reg['events']['emilia_emsr664']['csi_0p10']:.6f}). "
         f"Diagnostic (not canonical) Emilia with the switch on: n_ems_shps {reg['diagnostic_emilia_include_del_product']['n_ems_shps']}, "
         f"observed-wet km² {reg['diagnostic_emilia_include_del_product']['observed_wet_km2_strict']}, CSI {[round(x, 8) for x in reg['diagnostic_emilia_include_del_product']['csi_0p10']]}.",
         f"- Rule outputs (`stage1_yaml_validation.json`, {val['utc']}): enhanced = rain_source `{enh['rain_source']}` product `{enh['imerg_product']}` (R1, Late deviation); "
         f"R2 bias enabled `{enh['rain_bias_correct']['enabled']}` (DECISION pending; R2-on variant `emsr933_crete_enhanced_R2on.yaml`); "
         f"R3 upstream_q `{enh['upstream_q']['enabled']}`; R4 infiltration `{enh['infiltration_enabled']}` (amc {enh['infiltration_amc']}); "
         f"R5 coastal `{enh['coastal_bc']['enabled']}` pavbnd {enh['coastal_bc']['pavbnd']}; R6 wind/MSLP `{enh['wind_pressure']['enabled']}`; "
         f"window {enh['window']} → tref {enh['tref']}, tstart {enh['tstart']}, tstop {enh['tstop']}; bbox {enh['bbox']}; EPSG {enh['epsg']}; "
         f"grid res {enh['grid']['res']} m (GAP-1, provisional), subgrid {enh['grid']['subgrid_pixels']}, z_max {enh['grid']['zmax']} m (GAP-2, provisional); "
         f"baseline rain_source `{base['rain_source']}`; truth switches {enh['ems_switches']}; preflight rc {enh['preflight_rc']}/{base['preflight_rc']}.",
         f"- Terrain (`stage1_terrain.json`, {ter['utc']}; GLO-30 decimated ×{ter['grid']['decimation']}, {ter['grid']['shape']} cells, land {ter['land_km2']} km²). Per AOI: "
         + "; ".join(f"AOI{x['number']:02d} {x['name']} obs {x['observed_wet_cutoff']['km2_union'] if x['observed_wet_cutoff'] else '—'} km²"
                     + (f" ({int(x['observed_wet_cutoff']['cells_at_dx']['100'])} cells @100 m)" if x['observed_wet_cutoff'] else "")
                     + f", largest stream {x['largest_stream_inside']['uparea_km2']} km², sea cells {x['sea_cells_in_box']}, inlets ≥120 km² {x['n_inlets_ge_R3']}"
                     for x in ter["aois"]) + ".",
         "- Candidate domains (`stage1_terrain.json` → `domains`): "
         + "; ".join(f"{k}: bbox {v['bbox_WSEN']}, {v['size_km_utm34'][0]}×{v['size_km_utm34'][1]} km, land {v['land_km2']} km², sea {v['contains_sea']}, "
                     f"cells @50/100/150 {v['cells_total_at_dx']['50']}/{v['cells_total_at_dx']['100']}/{v['cells_total_at_dx']['150']} "
                     f"(land {v['cells_land_at_dx']['50']}/{v['cells_land_at_dx']['100']}/{v['cells_land_at_dx']['150']}), inflow ≥120 km² crossing edge {v['n_inflow_ge_120km2']}, "
                     f"k {min(s[0] for s in v['utm34_scale_corners'].values())}–{max(s[0] for s in v['utm34_scale_corners'].values())}"
                     for k, v in ter["domains"].items()) + "."]
    for ao in dep["aois"]:
        if ao["number"] in (3, 7) and ao["largest_components"]:
            c = ao["largest_components"][0]
            B.append(f"- Closed depression AOI{ao['number']:02d} {ao['name']} (`stage1_depressions.json`, largest component): area {c['area_km2']} km², "
                     f"floor {c['floor_m']} m, spill {c['spill_level_m']} m, max depth {c['max_depth_m']} m, volume below spill {c['volume_below_spill_Mm3']} Mm³, "
                     f"internal catchment {c['internal_catchment_km2']} km², centroid {c['centroid_lonlat']}.")
    rel = [p for p in prod if p["released"] == "True"]
    B.append("- Truth at the cut-off (`ems_snapshot_*_products.csv`): " + "; ".join(
        f"AOI{p['aoi']} {p['product']} id {p['product_id']} {p['post_sensor']} obs {p['obs_km2_union']} km² ({p['obs_km2_by_notation']})" for p in rel) + ".")
    # F5
    cb = abc["cases"]["b_halfhourly_default_dataarray"]; cc = abc["cases"]["c_hourly_default_dataarray"]
    cp = abc["cases"]["p_halfhourly_pulse_default_dataarray"]; cx = abc["cases"]["x_halfhourly_rate_left_dataarray"]
    cph = abc["cases"]["p_hourly_pulse_default_dataarray"]
    pf = [v for v in (cp.get("ratio_out_i_over_in_i_plus_1") or []) if v is not None]
    B.append(f"- F5 (a–c) (`f5/F5_abc.json` → `cases`): half-hourly 4×10 mm/h with the pipeline defaults → written {cb['output_domain_mean_mm_per_h']} mm/h, "
             f"total {cb['total_piecewise_constant_mm']} mm (factor {cb['factor_piecewise_constant_vs_input_total']} vs 20 mm); half-hourly pulse: factor "
             f"{pf[0] if pf else None}, offset {cp.get('centre_of_mass_offset_min_out_minus_in')} min; hourly 2×10 mm/h → {cc['output_domain_mean_mm_per_h']} mm/h, "
             f"hourly pulse offset {cph.get('centre_of_mass_offset_min_out_minus_in')} min; `cumulative_input=False, time_label=left` → {cx['output_domain_mean_mm_per_h']} mm/h, total {cx['total_piecewise_constant_mm']} mm.")
    rows = []
    for r in f5d["runs"]:
        ew = r["model_totals"]["bbox"]["event_window"]
        tot = next((v for k, v in ew.items() if k.startswith("total_pc")), None)
        rat = {k.split("/ target ")[-1]: v for k, v in r["ratios"].items() if k.startswith("model bbox event-window pc_fwd / target")}
        rows.append(f"{r['key']}: written bbox event-window {tot} mm, written/target {rat}, recorded factor {r['bias_correction_as_recorded'].get('factor')} → {r['bias_correction_as_recorded'].get('target_mm')} mm")
    B.append("- F5 (d) (`f5/F5_d.json` → `runs[].model_totals.bbox.event_window`, `ratios`): " + "; ".join(rows) + ".")
    rows = []
    for k, r in f5e["runs"].items():
        c = r["comparison"]
        rows.append(f"{k}: msk2 cells {r['bnd_msk2']['n_cells']}, bzs file {r['waterlevel_boundary_file_exists']}, MSLP min at boundary {c['t_mslp_min_bnd_mean']}, "
                    f"expected IB rel. first {c['expected_IB_rel_first_m']} m, pavbnd acted {c['pavbnd_acted_at_boundary_per_data']}")
    B.append("- F5 (e) (`f5/F5_e.json` → `runs[].comparison`): " + "; ".join(rows) + ".")
    rows = []
    for k, e in f5f["events"].items():
        ip = e.get("inp_parsed", {}); raw = e.get("inp", {}) if isinstance(e.get("inp"), dict) else {}; dv = e.get("derived", {})
        picks = {kk: vv for kk, vv in dv.items() if kk in ("gap_days_tstart_minus_tref", "days_simulated_before_event_date_tstart_to_eventdate",
                                                            "days_forcing_window_not_simulated_tref_to_tstart", "stated_spinup_days")}
        rows.append(f"{k}: tspinup {raw.get('tspinup', ip.get('tspinup'))}, tstart {ip.get('tstart')}, tstop {ip.get('tstop')}, {picks}")
    B.append("- F5 (f) (`f5/F5_f.json` → `events[].inp_parsed`, `derived`): " + "; ".join(rows) + ".")
    r2 = val["configs"].get("emsr933_crete_enhanced_R2on.yaml")
    if r2 and (d / "noa_stations/stations_daily.csv").exists():
        rows = list(csv.DictReader((d / "noa_stations/stations_daily.csv").open(encoding="utf-8")))
        tzr = [r for r in rows if r["station_slug"] == "tzermiado"]
        tz = [(r["date"], float(r["rain_mm"])) for r in tzr if "2026-09-30" <= r["date"] <= "2026-10-04"]
        las = next(c for ao in dep["aois"] if ao["number"] == 3 for c in ao["largest_components"][:1])
        B.append(f"- R2-on variant (`emsr933_crete_enhanced_R2on.yaml`, labelled, not canonical; `stage1_yaml_validation.json`): "
                 f"rain_bias_correct {r2['rain_bias_correct']}; anchor station `tzermiado` (NOA/meteo.gr, {tzr[0]['station_name']}, "
                 f"{tzr[0]['elev_m']} m) daily {tz} → sum {round(sum(v for _, v in tz), 1)} mm (`noa_stations/stations_daily.csv`, source "
                 f"{tzr[0]['source_url']}, accessed {tzr[0]['accessed_utc']}); watershed = Lasithi polje closed catchment "
                 f"{las['internal_catchment_km2']} km², bbox {las['catchment_bbox_WSEN']} (`stage1_depressions.json`).")
    B.append("- Decisions pending (Checkpoint 1): R2 raw vs anchored; GAP-1 Δx/domain (A 100 m island / B 150 m island / C 50 m per cluster / C′ 100 m per cluster); "
             "GAP-2 z_max; F5 harness option (a)/(b)/(c); window 7/3/4 d and island-wide domain confirmation.")
    a.audit_out.write_text("\n".join(B) + "\n", encoding="utf-8")
    print("\n".join(B))
    return 0


if __name__ == "__main__":
    sys.exit(main())
