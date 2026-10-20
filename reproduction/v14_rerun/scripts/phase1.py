"""Harness-v1.4 re-run orchestrator — Phase 1 (GO-C, 2026-10-19: Strymonas, Mandra, Pineios baselines + canonical enhanced),
Phase 2 (GO-D6: Valencia 164 mm, Emilia 8-AOI, Strymonas post-D6) and Phase 3 (GO Phases 3-5: ablations, S2 variant,
R2 sweeps, the eight C2 runs, the Pineios audit rows, the Strymonas lead-in sensitivity). Entries carry a `phase` tag.

Per run, in order:
  1. run config = the committed example YAML + `harness_version: v1.4` + a local work dir
     (`D:/ELKAK/implementation/v14/<run>`); written to reproduction/v14_rerun/configs/<run>.yaml as the record.
     The Pineios grid-matched baseline has no example: it is derived from emsr692_pineios_enhanced.yaml with every
     enhanced block disabled and ERA5 rain, and its v1.3 rendering is checked against the frozen record
     D:/ELKAK/reproduction/grid_matched_baseline/work/sfincs_build.yml.
  2. data dir seeded from the published run's data dir — directory junctions for the static inputs (DEM, WorldCover,
     EMS polygons, extracted ERA5/GloFAS) and copies of the small per-event files (raw GloFAS, IMERG + .raw.nc,
     ERA5 raw zip is NOT copied so prep_inputs does not extract into the junction). No download. The published
     directories are never written to.
  3. pipeline steps 06 (IMERG: already present -> skip; 06b bias correction re-derived from .raw.nc), 07 prep_inputs,
     08 prep_cn_raster, 09 prep_q_at_outlets, 10 build_model (v1.4: D4 prep + hydromt + D5 alignment + D2 bnd),
     11 run_sfincs; each timed.
  4. after the build: the event's exclusion GeoTIFF (v1.4 open_sea_mask.tif ∪ WorldCover 80) via
     validation/eval_exclusion.py, cross-checked against the published model's gis (symmetric difference recorded);
     the published v1.3 output is re-scored in the background (published mask and new mask) while SFINCS runs.
  5. after SFINCS: v1.4 output scored with the new mask; quick-look PNG; timing JSON.
Phase-3 hooks per entry: `overrides` (deep-merged into the example YAML), `seed_raw_imerg` (imerg_<slug>.raw.nc becomes the
forcing file), `manning_class50` (copy of skill/manning_lookup.csv with the built-up value replaced), `inp_patch`
(key = value set in sfincs.inp after the build, first occurrence replaced), `post_build` (rebuild_pineios_q), `published_json`
+ `published_kind` (val | exp | s1 | csv | emilia), `published_text` (numbers that exist only in the manuscript text).
Usage: python -I phase1.py --repo <worktree> [--runs strymonas_enhanced,...] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

V14_ROOT = Path("D:/ELKAK/implementation/v14")
IMPL = Path("D:/ELKAK/implementation")
NHESS = Path("D:/ELKAK/ELKAK2/NHESS")
JUNCTION_DIRS = ("copdem30", "esa_worldcover", "ems_polygons", "era5_extracted", "glofas_extracted")

RUNS = [
    {"run": "strymonas_enhanced", "event": "strymonas", "kind": "enhanced", "example": "emsr122_strymonas_enhanced.yaml",
     "seed_data": IMPL / "emsr122_sfincs_v3" / "data", "seed_slug": "strymonas",
     "published_work": IMPL / "emsr122_sfincs_v3", "published_model": IMPL / "emsr122_sfincs_v3" / "model",
     "manifest_row": 1, "published_wallclock_s": 109.2},
    {"run": "strymonas_baseline", "event": "strymonas", "kind": "baseline", "example": "emsr122_strymonas.yaml",
     "seed_data": IMPL / "emsr122_sfincs" / "data", "seed_slug": "emsr122",
     "published_work": IMPL / "emsr122_sfincs", "published_model": IMPL / "emsr122_sfincs" / "model",
     "manifest_row": 2, "published_wallclock_s": 256.5},
    {"run": "mandra_enhanced", "event": "mandra", "kind": "enhanced", "example": "emsr257_mandra_enhanced.yaml",
     "seed_data": IMPL / "mandra_sfincs_enhanced" / "data", "seed_slug": "mandra",
     "published_work": IMPL / "mandra_sfincs_enhanced", "published_model": IMPL / "mandra_sfincs_enhanced" / "model",
     "manifest_row": 3, "published_wallclock_s": 1097.8},
    {"run": "mandra_baseline", "event": "mandra", "kind": "baseline", "example": "emsr257_mandra.yaml",
     "seed_data": IMPL / "mandra_sfincs" / "data", "seed_slug": "mandra",
     "published_work": IMPL / "mandra_sfincs", "published_model": IMPL / "mandra_sfincs" / "model",
     "manifest_row": 4, "published_wallclock_s": 546.6},
    {"run": "pineios_enhanced", "event": "pineios", "kind": "enhanced", "example": "emsr692_pineios_enhanced.yaml",
     "seed_data": IMPL / "pineios_sfincs_enhanced" / "data", "seed_slug": "pineios",
     "published_work": IMPL / "pineios_sfincs_enhanced", "published_model": IMPL / "pineios_sfincs_enhanced" / "model",
     "manifest_row": 5, "published_wallclock_s": 1456.2},
    {"run": "pineios_baseline_gridmatched", "event": "pineios", "kind": "baseline", "example": "emsr692_pineios_enhanced.yaml",
     "derive_gridmatched_baseline": True,
     "seed_data": IMPL / "pineios_sfincs_enhanced" / "data", "seed_slug": "pineios",
     "published_work": None, "published_data": IMPL / "pineios_sfincs_enhanced" / "data",
     "published_model": Path("D:/ELKAK/reproduction/grid_matched_baseline/model"),
     "published_build_yml": Path("D:/ELKAK/reproduction/grid_matched_baseline/work/sfincs_build.yml"),
     "manifest_row": 6, "published_wallclock_s": 1006.4},
    # ---- Phase 2 (GO-D6 + Phase 2, 2026-10-19): held-out events, CN off in both
    {"run": "valencia_enhanced_164", "event": "valencia", "kind": "enhanced", "example": "emsr773_valencia_enhanced.yaml",
     "seed_data": NHESS / "runs" / "valencia_emsr773" / "data", "seed_slug": "valencia",
     # published = rerun_v164/model (precip of the 350-mm run x 0.4686, PROVENANCE.md), scored from _scoring/v164 (data + model links)
     "published_work": NHESS / "R1_verification" / "task_valencia_anchor" / "_scoring" / "v164",
     "published_model": NHESS / "R1_verification" / "task_valencia_anchor" / "rerun_v164" / "model",
     "published_gis": NHESS / "runs" / "valencia_emsr773" / "model" / "gis",
     "published_json": NHESS / "R1_verification" / "task_valencia_anchor" / "_scoring" / "score_v164.json",
     "manifest_row": 8, "published_wallclock_s": 2230.7},
    {"run": "emilia_enhanced_8aoi", "event": "emilia", "kind": "enhanced", "example": "emsr664_emilia_romagna_enhanced.yaml",
     "seed_data": NHESS / "runs" / "emilia_emsr664" / "data", "seed_slug": "emilia_romagna",
     # the run dir holds AOI01 only; the 8-AOI truth (12 product folders) lives in task_emilia_aoi (EMILIA_8AOI_RESCORE.md)
     "ems_override": NHESS / "R1_verification" / "task_emilia_aoi" / "data" / "ems_polygons",
     "published_work": None, "published_data": NHESS / "R1_verification" / "task_emilia_aoi" / "data",
     "published_model": NHESS / "runs" / "emilia_emsr664" / "model",
     "published_json": NHESS / "R1_verification" / "task_emilia_aoi" / "_scoring" / "emilia_rescore.json",
     "manifest_row": 7, "published_wallclock_s": 754.7},
    # ---- Checkpoint 4b: Strymonas v3 enhanced re-run under v1.4 + D6 (the Phase-1 pre-D6 run and records are kept)
    {"run": "strymonas_enhanced_postD6", "event": "strymonas", "kind": "enhanced", "example": "emsr122_strymonas_enhanced.yaml",
     "seed_data": IMPL / "emsr122_sfincs_v3" / "data", "seed_slug": "strymonas",
     "published_work": IMPL / "emsr122_sfincs_v3", "published_model": IMPL / "emsr122_sfincs_v3" / "model",
     "reuse_v13_from": "strymonas_enhanced", "requires_d6": True,
     "manifest_row": 1, "published_wallclock_s": 109.2},
]

# ---------------------------------------------------------------- Phase 3 (GO Phases 3-5, 2026-10-19)
EXP = Path("D:/ELKAK/manuscript/paper_submission_v2/data/exp")          # author scoring JSONs (top-level strict_threshold_sweep)
BSW = Path("D:/ELKAK/reproduction/bias_sweep")                           # R2 sweeps: only the last target of each event survives
BIAS_CSV = Path("D:/ELKAK/sfincs-mediterranean-floods/docs/bias_sensitivity")   # published sweep CSVs (main checkout; not on this branch)
STRY = dict(event="strymonas", kind="enhanced", example="emsr122_strymonas_enhanced.yaml", seed_data=IMPL / "emsr122_sfincs_v3" / "data", seed_slug="strymonas")
MAND = dict(event="mandra", kind="enhanced", example="emsr257_mandra_enhanced.yaml", seed_data=IMPL / "mandra_sfincs_enhanced" / "data", seed_slug="mandra")
PINE = dict(event="pineios", kind="enhanced", example="emsr692_pineios_enhanced.yaml", seed_data=IMPL / "pineios_sfincs_enhanced" / "data", seed_slug="pineios")
CN_PERVIOUS = (10, 20, 30, 40, 60, 90, 95, 100)                        # WorldCover classes given the test value; built-up 50 (88) and water/snow (99) kept


def cn_uniform(cn: int) -> dict:
    return {**{c: cn for c in CN_PERVIOUS}, 50: 88, 70: 99, 80: 99}


# TR-55 (USDA-NRCS 1986) Table 2-2, hydrologic soil group D: woods fair 79, brush fair 77, pasture fair 84, row crops SR good 89,
# industrial districts 93 (B = 88 as in the example lookup), fallow bare soil 94, herbaceous fair 89 -> 90 for 90/95, moss 85; water/snow 99 kept.
CN_HSG_D = {10: 79, 20: 77, 30: 84, 40: 89, 50: 93, 60: 94, 70: 99, 80: 99, 90: 90, 95: 90, 100: 85}
S1 = "NHESS supplement R5, Table S1 (Configuration | mean CN | Total wet km2 | TP (01MANDRA) | CSI | HR | FAR)"
P3 = {"phase": 3}
RUNS += [
    # ---- a. Table-12 ablations (MANIFEST rows 9, 10)
    {**STRY, **P3, "run": "strymonas_abl_cnoff_q", "group": "a", "label": "Table 12 row 3: CN off + Q", "overrides": {"infiltration": {"enabled": False}},
     "published_work": None, "published_data": IMPL / "emsr122_sfincs_v3" / "data", "published_model": IMPL / "emsr122_sfincs_v4" / "model",
     "published_json": EXP / "strymonas_v4_cnoff_qon.json", "published_kind": "exp", "frozen_config": Path("D:/ELKAK/reproduction/ablation_configs/abl_cnoff.yaml"),
     "manifest_row": 9, "published_wallclock_s": 232.5},
    {**STRY, **P3, "run": "strymonas_abl_qoff_cn", "group": "a", "label": "Table 12 row 4: CN on + Q off", "overrides": {"upstream_q": {"enabled": False}},
     "published_work": Path("D:/ELKAK/reproduction/repro_abl/qoff"), "published_model": Path("D:/ELKAK/reproduction/repro_abl/qoff/model"),
     "published_json": EXP / "strymonas_v4_qoff.json", "published_kind": "exp", "frozen_config": Path("D:/ELKAK/reproduction/ablation_configs/abl_qoff.yaml"),
     "published_note": "the printed Q-off output did not survive (inventory 3a); the 2026-06-19 re-run repro_abl/qoff reproduced the printed numbers (inventory 3c)",
     "manifest_row": 10, "published_wallclock_s": 110.8},
    # ---- b. S2 variant: Strymonas v1, pre-audit Kerkini source (MANIFEST row 13)
    {**STRY, **P3, "run": "strymonas_v1_prefix_src", "group": "b", "label": "Table 8 'Enhanced v1' / S2 Strymonas v1: pre-fix kerkini_outlet {23.2, 41.08}",
     "overrides": {"upstream_q": {"src_points": [{"name": "kerkini_outlet", "lon": 23.2, "lat": 41.08}, {"name": "angitis", "lon": 23.92, "lat": 41.0}]}},
     "published_work": IMPL / "emsr122_sfincs_enhanced", "published_model": IMPL / "emsr122_sfincs_enhanced" / "model",
     "published_json": Path("D:/ELKAK/reproduction/val_json/strymonas_v1.json"), "published_kind": "val", "manifest_row": 13, "published_wallclock_s": 219.6},
    # ---- c. R2 anchor sweeps (MANIFEST rows 11, 12); published numbers = docs/bias_sensitivity/<event>.csv; only the 255 / 510 mm outputs survive
    *[{**MAND, **P3, "run": f"mandra_r2_{t}", "group": "c", "label": f"R2 sweep Mandra target {t} mm", "overrides": {"rain_bias_correct": {"target_mm": t}},
       "published_csv": BIAS_CSV / "mandra.csv", "csv_target": t, "published_kind": "csv",
       "published_work": (BSW / "mandra" if t == 255 else None), "published_model": (BSW / "mandra" / "model" if t == 255 else None),
       "manifest_row": 11, "published_wallclock_s": (798.5 if t == 255 else None)} for t in (95, 140, 255)],
    *[{**PINE, **P3, "run": f"pineios_r2_{t}", "group": "c", "label": f"R2 sweep Pineios target {t} mm", "overrides": {"rain_bias_correct": {"target_mm": t}},
       "published_csv": BIAS_CSV / "pineios.csv", "csv_target": t, "published_kind": "csv",
       "published_work": (BSW / "pineios" if t == 510 else None), "published_model": (BSW / "pineios" / "model" if t == 510 else None),
       "manifest_row": 12, "published_wallclock_s": (1371.7 if t == 510 else None)} for t in (220, 295, 510)],
    # ---- d. the eight C2 runs (MANIFEST rows 17-20) — no model output survives; published numbers are text (quoted with their source)
    {**MAND, **P3, "run": "mandra_cn_a15", "group": "d", "c2_row": 1, "label": "S1 row 1: HSG-A AMC-II (CN = 15 test) — pervious classes CN 15",
     "overrides": {"infiltration": {"enabled": True, "hsg": "A", "amc": 2, "cn_lookup": cn_uniform(15)}},
     "published_model": None, "published_text": {"source": S1 + " row 1", "mean_cn": 42, "total_wet_km2": 0.77, "tp_01mandra": 0, "csi": 0.031, "hr": 0.032, "far": 0.42}, "manifest_row": 17},
    {**MAND, **P3, "run": "mandra_cn_a58", "group": "d", "c2_row": 2, "label": "S1 row 2: HSG-A AMC-II (CN = 58 test) — pervious classes CN 58",
     "overrides": {"infiltration": {"enabled": True, "hsg": "A", "amc": 2, "cn_lookup": cn_uniform(58)}},
     "published_model": None, "published_text": {"source": S1 + " row 2", "mean_cn": 65, "total_wet_km2": 0.77, "tp_01mandra": 0, "csi": 0.031, "hr": 0.032, "far": 0.42}, "manifest_row": 17},
    {**MAND, **P3, "run": "mandra_cn_b_default", "group": "d", "c2_row": 3, "label": "S1 row 3: HSG-B AMC-II (default lookup)",
     "overrides": {"infiltration": {"enabled": True}},
     "published_model": None, "published_text": {"source": S1 + " row 3", "mean_cn": 80, "total_wet_km2": 0.77, "tp_01mandra": 0, "csi": 0.031, "hr": 0.032, "far": 0.42}, "manifest_row": 17},
    {**MAND, **P3, "run": "mandra_cn_d_amc3", "group": "d", "c2_row": 4, "label": "S1 row 4: HSG-D AMC-III (post-fire, saturated) — TR-55 HSG-D lookup, AMC III",
     "overrides": {"infiltration": {"enabled": True, "hsg": "D", "amc": 3, "cn_lookup": CN_HSG_D}},
     "published_model": None, "published_text": {"source": S1 + " row 4", "mean_cn": 97, "total_wet_km2": 111, "tp_01mandra": 0, "csi": 0.010, "hr": 0.036, "far": 0.99}, "manifest_row": 17},
    {**MAND, **P3, "run": "mandra_cn_d_amc3_manning080", "group": "d", "c2_row": 5, "label": "S1 prose: Manning test, built-up n 0.012 -> 0.080 at the HSG-D AMC-III configuration",
     "overrides": {"infiltration": {"enabled": True, "hsg": "D", "amc": 3, "cn_lookup": CN_HSG_D}}, "manning_class50": 0.080,
     "published_model": None, "published_text": {"source": "NHESS supplement R5, S1 prose: no measurable change in per-area true positives or in total wet area (115.8 vs. 110.8 km2 at CN = 97)",
                                                 "total_wet_km2_n080": 115.8, "total_wet_km2_n012": 110.8}, "manifest_row": 17},
    {**PINE, **P3, "run": "pineios_cn_on", "group": "d", "c2_row": 6, "label": "§4.1.2 (ii) / §6.2: Pineios CN-on (HSG-B, AMC-II)", "overrides": {"infiltration": {"enabled": True}},
     "published_model": None, "published_text": {"source": "NHESS manuscript R5 §4.1.2 (ii): collapsed the flood to ~38 km2 (against 1519 km2 observed)", "modelled_wet_km2": 38, "observed_km2": 1519}, "manifest_row": 18},
    {**PINE, **P3, "run": "pineios_raw_imerg", "group": "d", "c2_row": 7, "label": "§5: Pineios raw IMERG (no R2)", "overrides": {"rain_bias_correct": {"enabled": False}}, "seed_raw_imerg": True,
     "published_model": None, "published_text": {"source": "NHESS manuscript R5 §5: raw IMERG recovers only 141 mm and bounds the flood below 40 km2", "watershed_mean_mm": 141, "modelled_wet_km2_upper": 40}, "manifest_row": 19},
    {"event": "valencia", "kind": "enhanced", "example": "emsr773_valencia_enhanced.yaml", "seed_data": NHESS / "runs" / "valencia_emsr773" / "data", "seed_slug": "valencia", **P3,
     "run": "valencia_raw_imerg", "group": "d", "c2_row": 8, "label": "§4.4.2 / §5.3 / S3.1: Valencia raw IMERG (no R2)", "overrides": {"rain_bias_correct": {"enabled": False}}, "seed_raw_imerg": True,
     "published_model": None, "published_gis": NHESS / "runs" / "valencia_emsr773" / "model" / "gis",
     "published_json": NHESS / "R1_verification" / "task8_cleanup" / "supplement" / "S1_EMSR773_valencia_raw_IMERG_metrics.json", "published_kind": "s1",
     "published_text": {"source": "NHESS manuscript R5 §4.4.2: The uncorrected raw-IMERG run scores CSI = 0.105", "csi": 0.105}, "manifest_row": 20},
    # ---- d'. Pineios audit rows (MANIFEST rows 14, 15): the audit's time-varying GloFAS discharge (nearest cell, hourly linear, src on the lowest-zb cell)
    {**PINE, **P3, "run": "pineios_timevarying_q", "group": "d", "label": "S2 Pineios v3 / §4.1.1: time-varying GloFAS Q audit (dis + src rebuilt after the build)", "post_build": "rebuild_pineios_q",
     "published_work": IMPL / "pineios_sfincs_v3", "published_model": IMPL / "pineios_sfincs_v3" / "model", "published_json": EXP / "pineios_v3_recheck.json", "published_kind": "exp",
     "manifest_row": 14, "published_wallclock_s": 2116.0},
    {**PINE, **P3, "run": "pineios_qinf5", "group": "d", "label": "§5.2: constant infiltration qinf = 5 mm/h on the time-varying-Q build (as the published v4 run)", "post_build": "rebuild_pineios_q", "inp_patch": {"qinf": "5.0"},
     "published_work": None, "published_data": IMPL / "pineios_sfincs_enhanced" / "data", "published_model": IMPL / "pineios_sfincs_v4" / "model", "published_json": EXP / "pineios_v4_qinf5.json", "published_kind": "exp",
     "manifest_row": 15, "published_wallclock_s": 1012.6},
    # ---- e. Strymonas lead-in sensitivity (GO-C decision 4): tstart = tref, the 7 forcing lead-in days simulated; CN on (D6); labelled, never canonical
    {**STRY, **P3, "run": "strymonas_leadin7d", "group": "e", "label": "sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN on",
     "overrides": {"window": {"spinup_days": 0, "pre_event_days": 10, "post_event_days": 3}}, "published_model": None, "compare_to": "strymonas_enhanced_postD6", "manifest_row": None},
]

# ---------------------------------------------------------------- Phase 5 (Crete, EMSR933; rule_ledger.md §8). No published number exists for any row.
CRETE_SEED = IMPL / "emsr933_crete" / "data"      # ERA5(T) + DEM + WorldCover (+ imerg_crete.nc copied from emsr933_crete_enhanced/data, ems_polygons = Stage-5 freeze)
CRE = dict(event="crete", seed_data=CRETE_SEED, seed_slug="crete", published_model=None, manifest_row=None, phase=5)
RUNS += [
    {**CRE, "run": "crete_baseline", "kind": "baseline", "example": "emsr933_crete.yaml", "group": "stage2", "label": "Stage 2 baseline: ERA5(T) rain-on-grid, no wind/IB, R2 off"},
    {**CRE, "run": "crete_canonical_r2on", "kind": "enhanced", "example": "emsr933_crete_enhanced_R2on.yaml", "group": "stage3",
     "label": "Stage 3 canonical: IMERG Late, R2 on (anchor 447.8 mm Tzermiado, factor computed at run time), wind/IB, R3/R4 off"},
    {**CRE, "run": "crete_sens_r2off", "kind": "enhanced", "example": "emsr933_crete_enhanced.yaml", "group": "sens_a", "label": "sensitivity (a): R2 off — raw IMERG Late", "compare_to": "crete_canonical_r2on"},
    *[{**CRE, "run": f"crete_sens_anchor_{t}", "kind": "enhanced", "example": "emsr933_crete_enhanced_R2on.yaml", "group": "sens_b",
       "label": f"sensitivity (b): anchor sweep target {t} mm", "overrides": {"rain_bias_correct": {"target_mm": t}}, "compare_to": "crete_canonical_r2on"} for t in (224, 336, 582)],
    {**CRE, "run": "crete_sens_karst_q1914", "kind": "enhanced", "example": "emsr933_crete_enhanced_R2on.yaml", "group": "sens_c",
     "label": "sensitivity (c): karst bracket, constant infiltration qinf = 1.914 mm/h (0.513 x 447.8 mm / 120 h, Steiakakis 2018)", "inp_patch": {"qinf": "1.914"}, "compare_to": "crete_canonical_r2on"},
]

# ---------------------------------------------------------------- Phase 6 (CODE-14, 2026-10-20): harness v1.4.1 = D7 GloFAS sampler fix.
# Re-runs of every run the D7 scope check found affected (reproduction/v14_rerun/code14/d7_scope.md): the pipeline Pineios runs,
# whose sfincs.dis carried the domain-mean constant 11.589 m3/s. Same frozen configs, same seeds; records beside the v1.4.0 ones
# (run name + "_v141"); the v1.3 re-scoring columns are reused from the base run (same published output).
V141_BASES = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5"]
PINEIOS_SRC_POINTS = [{"name": "pineios_trikala", "lon": 21.77, "lat": 39.56, "src_lon": 21.86, "src_lat": 39.56},
                      {"name": "pineios_kalambaka", "lon": 21.63, "lat": 39.70, "src_lon": 21.86, "src_lat": 39.70},
                      {"name": "titarisios", "lon": 22.42, "lat": 39.71},
                      {"name": "enipeas", "lon": 22.39, "lat": 39.30, "src_lon": 22.39, "src_lat": 39.33}]


def _v141(base: dict) -> dict:
    r = {k: v for k, v in base.items() if k != "post_build"}      # qinf5: the v1.4.1 build carries the GloFAS series itself (no rebuild)
    r.update({"run": f"{base['run']}_v141", "base_run": base["run"], "harness_tag": "v1.4.1", "phase": 6, "group": "v141",
              "label": f"v1.4.1 (D7 sampler fix) re-run of {base['run']}: " + (base.get("label") or "canonical enhanced"),
              "reuse_v13_from": (base["run"] if base.get("published_model") else None)})
    return r


RUNS += [_v141(next(r for r in RUNS if r["run"] == b)) for b in V141_BASES]
# D8 diagnostic (never canonical; the frozen config stands until the author decides): the Titarisios sampling point sits one
# 0.1-deg GloFAS cell from the Pineios main stem, so the +-0.1 deg window resolves to the main stem (1128.8 m3/s peak). Sampling
# the Titarisios' own last cell (22.24, 39.71; 42.8 m3/s) with a one-cell window; the injection point is unchanged.
RUNS += [{**_v141(next(r for r in RUNS if r["run"] == "pineios_enhanced")), "run": "pineios_enhanced_v141_d8titarisios", "group": "d8",
          "label": "D8 diagnostic (never canonical): Titarisios GloFAS sampling point moved to the Titarisios' last cell (22.24, 39.71), one-cell window; injection point and everything else as the v1.4.1 canonical",
          "overrides": {"upstream_q": {"src_points": [dict(sp, lon=22.24, lat=39.71, window_deg=0.05, src_lon=22.42, src_lat=39.71) if sp["name"] == "titarisios" else dict(sp) for sp in PINEIOS_SRC_POINTS]}},
          "published_work": None, "published_model": None, "published_json": None, "published_kind": None, "reuse_v13_from": None,
          "compare_to": "pineios_enhanced_v141", "manifest_row": None, "published_wallclock_s": None}]

# ---------------------------------------------------------------- Phase 7 (CODE-15, 2026-10-20): harness v1.4.2 = D8 source-point resolution
# (per-point GloFAS windows / cells, extended request area, build-time snap, duplicate-cell hard error). The resolved points come from the
# ledger reproduction/v14_rerun/code15/source_points_v142.json (single source); every run whose injected series or cells change is
# re-run: the Pineios lineage, Emilia, Valencia (canonical + raw IMERG) and the four Strymonas runs (their sources are snapped).
LEDGER_V142 = Path(__file__).resolve().parents[1] / "code15" / "source_points_v142.json"
PINEIOS_GLOFAS_EXT = V14_ROOT / "_seed" / "pineios" / "data" / "glofas_pineios.nc"        # lattice re-downloaded with the v1.4 request area (B(2))
V142_BASES = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5", "pineios_timevarying_q",
              "emilia_enhanced_8aoi", "valencia_enhanced_164", "valencia_raw_imerg",
              "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_leadin7d", "strymonas_v1_prefix_src"]


def _ledger_points(event: str) -> list[dict]:
    led = json.loads(LEDGER_V142.read_text(encoding="utf-8"))
    return [dict(sp) for sp in led["events"][event]["src_points"]]


def _v142(base: dict) -> dict:
    r = {k: v for k, v in base.items() if k != "post_build"}      # the v1.4.2 build carries the GloFAS series itself (no audit rebuild)
    ov = dict(base.get("overrides") or {})
    if base["run"] != "strymonas_v1_prefix_src":                    # the pre-fix Kerkini variant keeps its own (historical) points, snapped
        ov = {**ov, "upstream_q": {**(ov.get("upstream_q") or {}), "src_points": _ledger_points(base["event"])}}
    r.update({"run": f"{base['run']}_v142", "base_run": base["run"], "harness_tag": "v1.4.2", "phase": 7, "group": "v142", "overrides": ov,
              "label": f"v1.4.2 (D8 source-point resolution) re-run of {base['run']}: " + (base.get("label") or "canonical enhanced"),
              "reuse_v13_from": (base["run"] if base.get("published_model") else None),
              "compare_to": (f"{base['run']}_v141" if base["run"] in V141_BASES else base["run"])})
    if base["event"] == "pineios":
        r["seed_glofas"] = PINEIOS_GLOFAS_EXT
    return r


RUNS += [_v142(next(r for r in RUNS if r["run"] == b)) for b in V142_BASES]


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str):
    print(f"[{utc()}] {msg}", flush=True)


def junction(link: Path, target: Path):
    import _winapi
    if link.exists() or link.is_symlink():
        return "exists"
    _winapi.CreateJunction(str(target), str(link))
    return "created"


LEAF_KEYS = ("cn_lookup", "src_points")   # replaced wholesale, never merged key by key


def deep_update(d: dict, u: dict) -> dict:
    import copy
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict) and k not in LEAF_KEYS:
            d[k] = deep_update(d[k], v)
        else:
            d[k] = copy.deepcopy(v)
    return d


def _norm_frozen(o):
    """Frozen ablation YAMLs carry cp1252-decoded UTF-8 (em dashes); compare semantics, not bytes."""
    if isinstance(o, dict):
        return {k: _norm_frozen(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_norm_frozen(v) for v in o]
    if isinstance(o, str):
        try:
            return o.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return o
    return o


def set_inp_key(inp: Path, key: str, value: str) -> str:
    """Set key = value in sfincs.inp: the FIRST occurrence is replaced (SFINCS reads the first), else appended."""
    lines = inp.read_text().splitlines()
    for i, ln in enumerate(lines):
        if ln.split("=")[0].strip() == key:
            lines[i] = f"{key:<20} = {value}"
            inp.write_text("\n".join(lines) + "\n")
            return "replaced"
    lines.append(f"{key:<20} = {value}")
    inp.write_text("\n".join(lines) + "\n")
    return "appended"


def write_manning_lookup(repo: Path, work: Path, class50: float) -> Path:
    src = repo / "skill" / "manning_lookup.csv"
    out = work / f"manning_lookup_builtup_{class50:.3f}.csv"
    rows = [ln for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [f"50,{class50:.3f}" if ln.split(",")[0].strip() == "50" else ln for ln in rows]
    work.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return out


def cn_realised(model: Path, data: Path) -> dict:
    """Mean curve number of the run: CN raster clip (the mean prep_cn_raster prints), active cells, msk = 1 cells (from sfincs.scs, S in inch)."""
    import numpy as np
    import rasterio
    import xarray as xr
    from hydromt_sfincs import utils
    out = {}
    tif = data / "cn_raster.tif"
    if tif.exists():
        with rasterio.open(tif) as r:
            cn = r.read(1).astype(float)
        out["raster_clip_mean_cn"] = round(float(cn[cn > 0].mean()), 1)
    scs = model / "sfincs.scs"
    if scs.exists() and (model / "sfincs_map.nc").exists():
        ds = xr.open_dataset(model / "sfincs_map.nc"); msk = ds["msk"].values; ds.close()
        ind = utils.read_binary_map_index(model / "sfincs.ind")
        S = utils.read_binary_map(scs, ind, msk.shape, mv=np.nan, dtype="f4").astype(float)
        cnm = 1000.0 / (10.0 + S)
        out["active_mean_cn"] = round(float(np.nanmean(cnm[msk > 0])), 1)
        out["msk1_mean_cn"] = round(float(np.nanmean(cnm[msk == 1])), 1)
        out["active_S_mm_mean"] = round(float(np.nanmean(S[msk > 0]) * 25.4), 1)
    return out


# ------------------------------------------------------------------------------------------- 1. run configs
def make_config(repo: Path, r: dict, out_dir: Path) -> tuple[Path, dict]:
    import yaml
    src = repo / "skill" / "examples" / r["example"]
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    note = {"derived_from": f"skill/examples/{r['example']}", "changes": []}
    raw["harness_version"] = "v1.4"; note["changes"].append("harness_version: v1.4")
    work = V14_ROOT / r["run"]
    raw["paths"]["work_dir"] = str(work).replace("\\", "/")
    raw["paths"]["deliverable_dir"] = str(work / "deliverable").replace("\\", "/")
    raw["paths"]["zip_dir"] = str(work).replace("\\", "/")
    note["changes"].append(f"paths.work_dir/deliverable_dir/zip_dir -> {work}")
    if r.get("derive_gridmatched_baseline"):
        raw["rain_source"] = "era5_hourly"
        for blk in ("coastal_bc", "wind_pressure", "rain_bias_correct", "infiltration", "upstream_q"):
            if blk in raw:
                raw[blk]["enabled"] = False
        raw["event"]["name"] = "Pineios"; raw["event"]["slug"] = "pineios"
        note["changes"].append("grid-matched baseline (MANIFEST row 6): rain_source era5_hourly; coastal_bc, wind_pressure, "
                               "rain_bias_correct, infiltration, upstream_q disabled; window/bbox/grid of the enhanced run kept")
    if r.get("overrides"):
        deep_update(raw, r["overrides"])
        note["changes"].append("overrides: " + json.dumps(r["overrides"], default=str))
    if r.get("manning_class50") is not None:
        ml = write_manning_lookup(repo, work, float(r["manning_class50"]))
        raw["paths"]["manning_lookup"] = str(ml).replace("\\", "/")
        note["changes"].append(f"paths.manning_lookup -> {ml.name} (class 50 built-up n = {r['manning_class50']})")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{r['run']}.yaml"
    ph = r.get("phase", 1)
    tag = {1: "Phase 1 (GO-C, 2026-10-19)", 2: "Phase 2 (GO-D6, 2026-10-19)", 3: "Phase 3 (GO Phases 3-5, 2026-10-19)",
           5: "Phase 5 Crete EMSR933 (GO Phases 3-5, 2026-10-19; rule_ledger.md §8)",
           6: f"Phase 6 (CODE-14, 2026-10-20): harness {r.get('harness_tag', 'v1.4.1')} re-run of {r.get('base_run')} (D7 GloFAS sampler fix)",
           7: f"Phase 7 (CODE-15, 2026-10-20): harness {r.get('harness_tag', 'v1.4.2')} re-run of {r.get('base_run')} (D8 source-point resolution: ledger code15/source_points_v142.json, build-time snap)"}.get(ph, f"Phase {ph}")
    header = (f"# Harness v1.4 re-run config — {tag}. Generated by reproduction/v14_rerun/scripts/phase1.py\n"
              f"# from {note['derived_from']}: " + "; ".join(note["changes"]) + "\n")
    out.write_text(header + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return out, note


def check_gridmatched_render(repo: Path, cfg_path: Path, record: Path) -> dict:
    """The derived baseline must render (under v1.3) the frozen grid-matched build file."""
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import load_config
    import build_model
    cfg = load_config(["--config", str(cfg_path)])
    cfg.raw["harness_version"] = "v1.3"
    norm = lambda s: re.sub(r"reclass_table: .*", "reclass_table: X", s).strip()  # noqa: E731
    mine = norm(build_model.render_build_yml(cfg)); rec = norm(record.read_text(encoding="utf-8"))
    cfg.raw["harness_version"] = "v1.4"
    return {"record": str(record), "identical_under_v13": mine == rec,
            "diff_lines": [] if mine == rec else [ln for ln in mine.splitlines() if ln not in rec.splitlines()] + ["--- record ---"] + [ln for ln in rec.splitlines() if ln not in mine.splitlines()]}


# ------------------------------------------------------------------------------------------- 2. seeding
def seed(r: dict, work: Path, slug: str) -> dict:
    data = work / "data"; data.mkdir(parents=True, exist_ok=True)
    src = r["seed_data"]; s0 = r["seed_slug"]
    rep = {"from": str(src), "junctions": {}, "copied": [], "skipped": []}
    for d in JUNCTION_DIRS:
        target = r["ems_override"] if (d == "ems_polygons" and r.get("ems_override")) else src / d
        if target.exists():
            rep["junctions"][d] = junction(data / d, target) + ("" if target == src / d else f" -> {target}")
    files = {f"glofas_{s0}.nc": f"glofas_{slug}.nc", f"imerg_{s0}.nc": f"imerg_{slug}.nc", f"imerg_{s0}.raw.nc": f"imerg_{slug}.raw.nc",
             f"era5_{s0}.nc": f"era5_{slug}.nc"}
    if r.get("seed_glofas"):
        sg = Path(r["seed_glofas"])
        if not sg.exists():
            raise SystemExit(f"{r['run']}: extended GloFAS seed {sg} missing (run download_glofas_openmeteo.py with the v1.4 request area first)")
        shutil.copy2(sg, data / f"glofas_{slug}.nc"); rep["copied"].append(f"{sg} -> glofas_{slug}.nc (v1.4.2 extended request area)")
        for stale in (data / f"glofas_{slug}_clean.nc",):
            if stale.exists():
                stale.unlink()
    for a, b in files.items():
        if (src / a).exists():
            if not (data / b).exists():
                shutil.copy2(src / a, data / b); rep["copied"].append(f"{a} -> {b}")
            else:
                rep["skipped"].append(b)
    if r.get("seed_raw_imerg"):
        raw_nc, nc = data / f"imerg_{slug}.raw.nc", data / f"imerg_{slug}.nc"
        if not raw_nc.exists():
            raise SystemExit(f"{r['run']}: raw IMERG {raw_nc} missing")
        shutil.copy2(raw_nc, nc)
        rep["raw_imerg_as_forcing"] = f"{raw_nc.name} -> {nc.name} (rain_bias_correct disabled; the D1 rate/label convention is applied at build time)"
    return rep


# ------------------------------------------------------------------------------------------- 3. pipeline
def run_step(py: str, repo: Path, cfg: Path, step: int, logf: Path, env: dict) -> dict:
    t0 = time.time(); u0 = utc()
    with open(logf, "a", encoding="utf-8") as fh:
        fh.write(f"\n##### step {step:02d} start {u0}\n"); fh.flush()
        res = subprocess.run([py, str(repo / "skill" / "scripts" / "run_pipeline.py"), "--config", str(cfg), "--only", str(step)],
                             stdout=fh, stderr=subprocess.STDOUT, env=env)
    rec = {"step": step, "start_utc": u0, "end_utc": utc(), "wall_s": round(time.time() - t0, 1), "exit": res.returncode}
    if res.returncode != 0:
        raise RuntimeError(f"step {step} failed (exit {res.returncode}); see {logf}")
    return rec


def steps_from_log(logf: Path) -> list[dict]:
    """Step start/end UTC from the '##### step NN start <utc>' markers of pipeline_v14.log (for --resume records)."""
    import datetime as _dt
    if not logf.exists():
        return []
    marks = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"##### step (\d+) start (\S+)", logf.read_text(errors="replace"))]
    out = []
    for i, (st, t0) in enumerate(marks):
        t1 = marks[i + 1][1] if i + 1 < len(marks) else None
        wall = None
        if t1:
            wall = (_dt.datetime.strptime(t1, "%Y-%m-%dT%H:%M:%SZ") - _dt.datetime.strptime(t0, "%Y-%m-%dT%H:%M:%SZ")).total_seconds()
        out.append({"step": st, "start_utc": t0, "end_utc": t1, "wall_s": wall, "from_log": True})
    return out


def sfincs_total_time(model: Path):
    for name in ("sfincs_log.txt", "sfincs.log"):
        p = model / name
        if p.exists():
            m = re.search(r"Total time\s*:\s*([0-9.]+)", p.read_text(errors="replace"))
            if m:
                return float(m.group(1))
    return None


# ------------------------------------------------------------------------------------------- 4. exclusion + scoring
def make_exclusion(py: str, repo: Path, r: dict, work: Path, masks: Path, env: dict) -> dict:
    out = masks / f"{r['event']}_exclusion.tif"; js = masks / f"{r['event']}_exclusion.json"
    sea_tif = work / "open_sea_mask.tif"
    wc = work / "data" / "esa_worldcover" / "esa_worldcover_2021.vrt"
    if out.exists():
        # second run of the same event: the build's open-sea mask must equal the one already used
        import rasterio
        import numpy as np
        with rasterio.open(sea_tif) as a:
            sea = a.read(1) == 1
        prev = json.loads(js.read_text(encoding="utf-8"))
        with rasterio.open(prev["open_sea_source"]) as b:
            sea_prev = b.read(1) == 1
        same = sea.shape == sea_prev.shape and bool((sea == sea_prev).all())
        diff = int((sea ^ sea_prev).sum()) if sea.shape == sea_prev.shape else -1
        return {"reused": str(out), "open_sea_identical_to_first_build": same, "symmetric_difference_cells": diff}
    gis = r.get("published_gis") or ((r["published_model"] / "gis") if r.get("published_model") else (work / "model" / "gis"))
    cmd = [py, "-I", str(repo / "validation" / "eval_exclusion.py"), "--open-sea-tif", str(sea_tif), "--gis", str(gis),
           "--worldcover", str(wc), "--out", str(out), "--out-json", str(js), "--allow-diff"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        raise RuntimeError("eval_exclusion failed:\n" + res.stdout[-2000:] + res.stderr[-2000:])
    return json.loads(js.read_text(encoding="utf-8"))


def validate_cmd(py: str, repo: Path, cfg: Path, out_json: Path, exclusion: Path | None, work_override: Path | None, env: dict):
    e = dict(env)
    if work_override:
        e["SFINCS_WORK_DIR"] = str(work_override)
    cmd = [py, str(repo / "validation" / "validate_event_v2.py"), "--config", str(cfg), "--out-json", str(out_json)]
    if exclusion:
        cmd += ["--exclusion-tif", str(exclusion)]
    return cmd, e


def published_work_for(r: dict, scratch: Path) -> Path:
    """Work dir whose data/ and model/ are the published ones (junctions for the grid-matched baseline)."""
    if r.get("published_work"):
        return r["published_work"]
    w = scratch / r["run"]; w.mkdir(parents=True, exist_ok=True)
    junction(w / "data", r["published_data"]); junction(w / "model", r["published_model"])
    return w


def published_strict(repo: Path, r: dict) -> dict | None:
    """The published h > 0.10 m record of a run in one shape: val (validation JSON), exp (author scoring JSON), s1 (supplement
    metrics file), csv (bias-sweep CSV row), emilia (full_8aoi). None when only text exists."""
    kind = r.get("published_kind")
    if kind == "csv":
        import csv
        with open(Path(r["published_csv"]), newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if float(row["target_mm"]) == float(r["csv_target"]):
                    return {"_source": f"{r['published_csv']} target {r['csv_target']}", **{k: float(row[k]) for k in ("csi", "hr", "far", "bias", "gss")},
                            "multiplier": (None if row["multiplier"] == "nan" else float(row["multiplier"]))}
        return None
    if not r.get("published_json"):
        return None
    pj = json.loads(Path(r["published_json"]).read_text(encoding="utf-8"))
    if kind == "exp":
        h = pj["strict_threshold_sweep"]["h>0.10m"]
    elif kind == "s1":
        h = pj["ems"]["metrics_by_threshold"]["h>0.10m"]
    elif kind == "emilia" or ("validation" not in pj and "full_8aoi" in pj):
        h = pj["full_8aoi"]["h>0.10m"]
    else:
        h = pj["validation"]["strict_threshold_sweep"]["h>0.10m"]
    out = {"_source": str(r["published_json"])}
    out.update({k: h[k] for k in ("tp", "fp", "fn", "tn", "csi", "hr", "far", "bias", "gss") if k in h})
    return out


# ------------------------------------------------------------------------------------------- main
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true", help="skip steps 06-11 when model/sfincs_map.nc exists (validation/records only)")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import _load_machine_override
    ov = _load_machine_override()
    py = ov["env"]["python"]
    env = dict(os.environ); env["GDAL_DATA"] = ov["env"].get("gdal_data", env.get("GDAL_DATA", ""))
    env["PYTHONIOENCODING"] = "utf-8"
    out_root = repo / "reproduction" / "v14_rerun"
    cfg_dir, res_dir, masks, ql = out_root / "configs", out_root / "results", out_root / "masks", out_root / "quicklook"
    for d in (cfg_dir, res_dir, masks, ql):
        d.mkdir(parents=True, exist_ok=True)
    scratch = V14_ROOT / "_rescoring"
    sel = [x for x in a.runs.split(",") if x]
    for r in RUNS:
        if sel and r["run"] not in sel:
            continue
        run = r["run"]; work = V14_ROOT / run
        rec_path = res_dir / f"{run}_record.json"
        rec = {"run": run, "event": r["event"], "kind": r["kind"], "phase": r.get("phase", 1), "group": r.get("group"), "label": r.get("label"),
               "c2_row": r.get("c2_row"), "manifest_row": r["manifest_row"], "work": str(work),
               "published_model": (str(r["published_model"]) if r.get("published_model") else None), "published_wallclock_s": r.get("published_wallclock_s"),
               "published_text": r.get("published_text"), "published_note": r.get("published_note"), "compare_to": r.get("compare_to"),
               "harness_tag": r.get("harness_tag", "v1.4.0"), "base_run": r.get("base_run"),
               "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip(),
               "start_utc": utc(), "steps": []}
        log(f"=== {run} ===")
        cfg_path, note = make_config(repo, r, cfg_dir); rec["config"] = str(cfg_path.relative_to(repo)); rec["config_note"] = note
        if r.get("derive_gridmatched_baseline"):
            rec["gridmatched_render_check"] = check_gridmatched_render(repo, cfg_path, r["published_build_yml"])
            log(f"grid-matched render check: {rec['gridmatched_render_check']['identical_under_v13']}")
        from _common import load_config
        cfg = load_config(["--config", str(cfg_path)])
        if r.get("requires_d6") or cfg.infiltration["enabled"]:
            import build_model
            if "storecumprcp" not in build_model.render_build_yml(cfg):
                raise SystemExit(f"{run}: harness D6 (storecumprcp with curve numbers) is not implemented in build_model — refusing to run")
            rec["d6_rendered"] = True
        if r.get("frozen_config"):
            import yaml
            fz = _norm_frozen(yaml.safe_load(Path(r["frozen_config"]).read_text(encoding="utf-8"))); mine = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            for d_ in (fz, mine):
                d_.setdefault("rain_bias_correct", {"enabled": False})
                if not d_["rain_bias_correct"].get("enabled"):
                    d_["rain_bias_correct"] = {"enabled": False}
            diff = {k: (fz.get(k), mine.get(k)) for k in set(fz) | set(mine) if k not in ("env", "paths", "harness_version") and fz.get(k) != mine.get(k)}
            rec["frozen_config_check"] = {"frozen": str(r["frozen_config"]), "identical_outside_env_paths": not diff, "differences": json.dumps(diff, default=str)[:2000]}
            log(f"frozen-config check vs {Path(r['frozen_config']).name}: identical outside env/paths = {not diff}")
        rec["seed"] = seed(r, work, cfg.event_slug)
        log(f"seeded {work}: junctions {rec['seed']['junctions']}, copied {rec['seed']['copied']}")
        if a.dry_run:
            rec_path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
            continue
        logf = work / "pipeline_v14.log"
        bg = []
        resumed = a.resume and (work / "model" / "sfincs_map.nc").exists()
        if resumed:
            rec["resumed"] = True
            rec["steps"] = steps_from_log(logf)
            log(f"resume: model output exists, steps 06-11 skipped (timings from {logf.name})")
        for step in ((10, 11) if resumed else (6, 7, 8, 9, 10, 11)):
            if not resumed:
                st = run_step(py, repo, cfg_path, step, logf, env)
                rec["steps"].append(st)
                log(f"step {step:02d} done in {st['wall_s']} s")
            if step == 10:
                prep = work / "coastal_prep.json"
                rec["coastal_prep"] = json.loads(prep.read_text(encoding="utf-8")) if prep.exists() else None
                rec["exclusion"] = make_exclusion(py, repo, r, work, masks, env)
                log(f"exclusion: {rec['exclusion']}")
                excl = masks / f"{r['event']}_exclusion.tif"
                if r.get("post_build") == "rebuild_pineios_q" and resumed:
                    rec["post_build"] = {"hook": "rebuild_pineios_q", "json": f"results/{run}_rebuild_q.json", "resumed": True}
                elif r.get("post_build") == "rebuild_pineios_q":
                    qj = res_dir / f"{run}_rebuild_q.json"
                    pb = subprocess.run([py, "-I", str(repo / "reproduction" / "v14_rerun" / "scripts" / "rebuild_pineios_q.py"), "--config", str(cfg_path),
                                         "--model", str(work / "model"), "--out-json", str(qj), "--repo", str(repo)], capture_output=True, text=True, env=env)
                    if pb.returncode != 0:
                        raise RuntimeError("rebuild_pineios_q failed:\n" + pb.stdout[-2000:] + pb.stderr[-2000:])
                    rec["post_build"] = {"hook": "rebuild_pineios_q", "json": f"results/{run}_rebuild_q.json"}
                    log(f"post-build: discharge rebuilt ({qj.name})")
                if r.get("inp_patch") and not resumed:
                    rec["inp_patch"] = {k: set_inp_key(work / "model" / "sfincs.inp", k, str(v)) for k, v in r["inp_patch"].items()}
                    log(f"inp patch: {rec['inp_patch']}")
                if not r.get("published_model"):
                    rec["rescoring_v13_skipped"] = "no published output survives for this configuration"
                    continue
                pw = published_work_for(r, scratch)
                ex_yaml = repo / "skill" / "examples" / r["example"]
                if r.get("derive_gridmatched_baseline"):
                    # the published grid-matched baseline has no v1.3 example: score it with the derived config
                    # (window/bbox/EMS identical to the enhanced example), v1.3 semantics do not enter the validator
                    ex_yaml = cfg_path
                if r.get("reuse_v13_from"):
                    rec["rescoring_v13_reused_from"] = r["reuse_v13_from"]
                    log(f"v1.3 columns reused from {r['reuse_v13_from']} (same published output)")
                    continue
                for tag, ex in (("v13_publishedmask", None), ("v13_newmask", excl)):
                    oj = res_dir / f"{run}_{tag}.json"
                    cmd, e = validate_cmd(py, repo, ex_yaml, oj, ex, pw, env)
                    lf = open(res_dir / f"{run}_{tag}.log", "w", encoding="utf-8")
                    bg.append((tag, subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=e), lf, time.time()))
                log("v1.3 re-scoring started in the background (published mask + new mask)")
        model = work / "model"
        rec["sfincs_total_time_s"] = sfincs_total_time(model)
        qc = work / "data" / "q_outlet_cells.json"
        if qc.exists():
            rec["q_outlet_cells"] = json.loads(qc.read_text(encoding="utf-8"))      # v1.4.1 sampler provenance (cell per source)
        sn = model / "sfincs_src_snap.json"
        if sn.exists():
            rec["src_snap"] = json.loads(sn.read_text(encoding="utf-8"))            # v1.4.2 injection cells (build-time snap)
        if cfg.infiltration["enabled"]:
            rec["cn_realised"] = cn_realised(model, work / "data")
            log(f"curve numbers realised: {rec['cn_realised']}")
        excl = masks / f"{r['event']}_exclusion.tif"
        t0 = time.time()
        cmd, e = validate_cmd(py, repo, cfg_path, res_dir / f"{run}_v14_newmask.json", excl, None, env)
        with open(res_dir / f"{run}_v14_newmask.log", "w", encoding="utf-8") as lf:
            res = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=e)
        rec["validation_v14"] = {"exit": res.returncode, "wall_s": round(time.time() - t0, 1), "json": f"results/{run}_v14_newmask.json"}
        log(f"v1.4 validation done ({rec['validation_v14']['wall_s']} s, exit {res.returncode})")
        rec["rescoring_v13"] = {}
        for tag, p, lf, t0 in bg:
            rc = p.wait(); lf.close()
            rec["rescoring_v13"][tag] = {"exit": rc, "wall_s": round(time.time() - t0, 1), "json": f"results/{run}_{tag}.json"}
        log(f"v1.3 re-scoring finished: {rec['rescoring_v13']}")
        ps = published_strict(repo, r)
        if ps:
            rec["published_strict"] = ps
        if ps and (res_dir / f"{run}_v13_publishedmask.json").exists():
            ms = json.loads((res_dir / f"{run}_v13_publishedmask.json").read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"]
            if all(k in ps for k in ("tp", "fp", "fn", "tn")):
                same = all(ms[k] == ps[k] for k in ("tp", "fp", "fn", "tn"))
            else:
                same = all(abs(ms[k] - ps[k]) < 5e-5 for k in ("csi", "hr", "far", "bias", "gss") if k in ps)
            rec["published_record_check"] = {"published_json": ps.get("_source"), "identical_tp_fp_fn_tn": same,
                                             "published": {k: ps[k] for k in ("tp", "fp", "fn", "tn", "csi") if k in ps},
                                             "rescored": {k: ms[k] for k in ("tp", "fp", "fn", "tn", "csi")}}
            log(f"published-record check: {same}")
        qcmd = [py, "-I", str(repo / "reproduction" / "v14_rerun" / "scripts" / "quicklook.py"), "--repo", str(repo), "--config", str(cfg_path),
                "--out", str(ql / f"{run}_v14_hmax.png"), "--metrics", str(res_dir / f"{run}_v14_newmask.json"), "--exclusion-tif", str(excl),
                "--title", f"{run} — harness v1.4, new evaluation mask"]
        q = subprocess.run(qcmd, capture_output=True, text=True, env=env)
        rec["quicklook"] = {"exit": q.returncode, "png": f"quicklook/{run}_v14_hmax.png", "err": q.stderr[-500:] if q.returncode else ""}
        rec["end_utc"] = utc()
        rec_path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
        log(f"record written: {rec_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
