# Re-run manifest — every SFINCS run behind NHESS R5 (CODE-12 Part B, planning only)

Status: **planning only — no run has been executed.** Option (c) (fix the harness and re-run every published
event) is Papaioannou's decision; nothing here starts before "GO-C". Harness to use: **v1.4** (commit
`513ce5ab73bbf4ef41e091cf3c49c3b836f2cd8b`, 2026-10-12T10:12:15Z; `harness_version: v1.4` has to be added
to each YAML at run time — the committed example YAMLs still default to v1.3 so that they keep reproducing
the published records).

Source of every fact: the read-only inventory `INVENTORY_2026-10-12.md` (families 1–7 + gaps; each cell cites
its file). Manuscript = `ELKAK2/NHESS/Final_sub/NHESS_manuscript_R5_clean.docx` (+ supplement R5). Wall-clock
= the `Total time` line of each run's `sfincs.log` (seconds, previous machine state); where an author run and a
2026-06-19 re-run on this machine both exist, the re-run time is used for the estimate. "Re-download" answers
whether any forcing input is missing on disk for a pipeline re-run from the YAML.

What v1.4 changes for every row: IMERG written ×1 (was ×2) and on time (was −30 min) — Strymonas/Emilia raw
IMERG included; ERA5 unchanged; inverse-barometer boundary active (bnd + bzs = 0 m + pavbnd = 101325 Pa) in
every run with `coastal_bc.enabled` (all enhanced runs; baselines stay without wind/IB). D3 (tspinup = 0,
spin-up window not simulated) is **not** changed by v1.4 (A3 report only).

## 1. SFINCS runs

| # | run (inventory id) | YAML / as-run source | feeds in R5 | prev. wall-clock (s) | re-download? | v1.4 notes |
|---|---|---|---|---|---|---|
| 1 | Strymonas v3 enhanced, canonical (2c) | `skill/examples/emsr122_strymonas_enhanced.yaml` = `configs/as_run/emsr122_sfincs_v3/` (kerkini src fix) | Tables 7, 8 (v3), 9, 10, 11, 12 row 2, 14; Figs 7, 10; §4.3.2, §5, §7; Suppl. Tables S2, S3 | 125.1 author / **109.2** re-run | no (`implementation/emsr122_sfincs_v3/data` complete; raw IMERG = `imerg_strymonas.nc`) | IMERG ×1 + IB boundary |
| 2 | Strymonas baseline (1e) | `skill/examples/emsr122_strymonas.yaml` = `configs/as_run/emsr122_sfincs/` | Table 12 row 1, Table 10 Δ, Table 8 baseline column; §4.3.2, §5 | **256.5** | no, but the data dir uses slug `emsr122` (`era5_emsr122.nc`) — run with `SFINCS_WORK_DIR` on a copy/junction of the v3 data dir | ERA5 unchanged (identical forcing; re-run only for a same-harness baseline) |
| 3 | Mandra v1 enhanced, canonical (2b) | `skill/examples/emsr257_mandra_enhanced.yaml` = `configs/as_run/mandra_sfincs_enhanced/` (R2 200 mm) | Tables 5, 6, 9, 10, 11, 14; Figs 5, 6, 10, 11b; §4.2.2, §7; Suppl. S1 final row, S2, S3 | 869.7 author / **1097.8** re-run | no (`mandra_sfincs_enhanced/data` complete incl. `.raw.nc`) | IMERG ×1 (bias factor re-derived from `.raw.nc`, same 200 mm target) + IB |
| 4 | Mandra baseline (1d) | `skill/examples/emsr257_mandra.yaml` = `configs/as_run/mandra_sfincs/` | Table 10 Δ; §4.2.2, §4.3.2, §5; Fig 6 ERA5 curve | **546.6** | no | ERA5 unchanged |
| 5 | Pineios v1 enhanced, canonical (2a) | `skill/examples/emsr692_pineios_enhanced.yaml` = `configs/as_run/pineios_sfincs_enhanced/` (R2 400 mm, 4 GloFAS points) | Tables 3, 4, 9, 10, 11, 14; Figs 3, 4, 10, 11a; Abstract; §4.1.2, §7; Suppl. S2, S3 | 1269.8 author / **1456.2** re-run | no (`pineios_sfincs_enhanced/data` complete) | IMERG ×1 + IB; the pipeline writes `sfincs.dis` from `q_outlet.csv` (time-varying) — see row 14 |
| 6 | Pineios grid-matched baseline (1c) | `reproduction/grid_matched_baseline/work/sfincs_build.yml` (ERA5, 150 m, 7-d window, no Q, CN off) — no example YAML; recreate from `emsr692_pineios.yaml` with `spinup_days: 7`, enhanced bbox/zmax | Table 10 Pineios Δ + caption; Abstract; §5, §5.3 | **1006.4** | no (reads `pineios_sfincs_enhanced/data`) | ERA5 unchanged |
| 7 | Emilia-Romagna enhanced (2f) | `skill/examples/emsr664_emilia_romagna_enhanced.yaml` = `ELKAK2/NHESS/runs/emilia_emsr664/` | §4.5.2; Fig 9; Tables 9, 10, 13, 14; §5.4; Suppl. S3.1, S4 | **754.7** | no for forcing; EMS truth: the 8-AOI set lives in `R1_verification/task_emilia_aoi/data/ems_polygons/` (run dir holds AOI01 only) — copy, do not re-download | raw IMERG ×1 + IB |
| 8 | Valencia R2-anchored 164 mm (2e) | `skill/examples/emsr773_valencia_enhanced.yaml` (target 164 mm) — the R5 numbers came from `rerun_v164/model` (350-mm run × 0.4686), not from a pipeline run | §4.4.2; Fig 8; Tables 9, 10, 13, 14; §5.3, §5.4, §7, §8 | **2230.7** (v164) / 1706.7 (350-mm pipeline run) | no (`runs/valencia_emsr773/data` complete; `imerg_valencia.nc` is at ×4.14 but `bias_correct_imerg.py` regenerates from `.raw.nc`) | first pipeline-native 164-mm run; IMERG ×1 + IB |
| 9 | Strymonas CN-off + Q (3b) | `D:/ELKAK/reproduction/ablation_configs/abl_cnoff.yaml` via `scripts/run_ablation.sh` | Table 12 row 3; §5.2, §6.2 | 232.5 author / **275.9** re-run | no (junction/hardlink seed from the v3 data dir) | IMERG ×1 + IB |
| 10 | Strymonas CN-on + Q-off (3c) | `abl_qoff.yaml` via `run_ablation.sh` | Table 12 row 4; §5.2, §6.2 | **110.8** | no | IMERG ×1 + IB |
| 11 | Mandra R2 sweep 95 / 140 / 255 mm (4a; 200 = row 3) | `scripts/bias_sweep.py` (targets hard-coded) on `emsr257_mandra_enhanced.yaml` | §5.2 sweep sentence; `docs/bias_sensitivity/mandra.csv`, plots | **798.5** (255-mm run; ×3) | no | 3 runs; the factors change because the ×2 is gone |
| 12 | Pineios R2 sweep 220 / 295 / 510 mm (4b; 400 = row 5) | `scripts/bias_sweep.py` on `emsr692_pineios_enhanced.yaml` | §5.2 sweep sentence; `docs/bias_sensitivity/pineios.csv`, plots | **1371.7** (510-mm run; ×3) | no | 3 runs |
| 13 | Strymonas v1 enhanced, pre-fix src (2d) | `configs/as_run/emsr122_sfincs_enhanced/` (kerkini src {23.2, 41.08}; not in the examples any more) | Table 8 "Enhanced v1" column; §4.3.2, §5; Suppl. Table S2 Strymonas v1 row | **219.6** | no | needed only if the v1 column / S2 row stay in the paper |
| 14 | Pineios v3 time-varying-Q audit (5a) | = row 5 inp + `sfincs.dis` rebuilt from the GloFAS series (no YAML of its own) | §4.1.1, §5.2 ("peak 118 m³ s⁻¹"); Suppl. Table S2 Pineios v3 row | 2116.0 | no | **decision needed**: the v1.4 pipeline run of row 5 already writes the time series from `q_outlet.csv`; a separate run is only needed if the S2 "v1 vs v3" contrast must be kept |
| 15 | Pineios v4 constant infiltration qinf = 5 mm h⁻¹ (5b) | = row 5 + `qinf = 5.0` in `sfincs.inp` (post-build patch) | §5.2 | **1012.6** | no (uses the row-5 build) | |
| 16 | Mandra v3 mask restriction, 213 km² (5c) | = row 3 + edited `sfincs.msk` (`sfincs.msk.orig`) | Suppl. Table S2 Mandra v3 row; §5 | **1906.7** | no | |
| 17 | Mandra SCS-CN sweep (5d) — 4 rows + Manning test | `emsr257_mandra_enhanced.yaml` + `infiltration.enabled: true` with HSG-A/B/D × AMC lookups; **no model dir survives** | Suppl. Table S1 rows 1–4 + S1 prose; §6.2 | n/a (≈ row 3: 1097.8 × 5) | no (`cn_raster.tif` regenerated by `prep_cn_raster.py`) | 5 runs to be recreated |
| 18 | Pineios CN-on ("~38 km²") (5e) | `emsr692_pineios_enhanced.yaml` + `infiltration.enabled: true`; **no model dir** | §4.1.2 (ii), §6.2 | n/a (≈ 1456) | no | |
| 19 | Pineios raw IMERG ("below 40 km²") (5e) | `emsr692_pineios_enhanced.yaml` + `rain_bias_correct.enabled: false`; **no model dir** | §5 | n/a (≈ 1456) | no | |
| 20 | Valencia raw IMERG (2e‴) | `emsr773_valencia_enhanced.yaml` + `rain_bias_correct.enabled: false`; **no model dir** (metrics in `S1_EMSR773_valencia_raw_IMERG_metrics.json`) | §4.4.2, §5.3 ("CSI = 0.105"); Suppl. S3.1 (S1 JSON) | n/a (≈ 1707) | no | |

Not in scope of R5 (listed for completeness): Pineios original 100-m baseline (1a, prose only), wide baseline (1b,
nothing), Valencia 350/175-mm runs (superseded), the 18 SCS-CN toy runs (`reproduction/cn_diagnostic`, no R5
number). **EMSR933 Crete** (CODE-10 Stages 2–3) runs under v1.4 after GO-C as a separate task.

## 2. Post-processing-only products (no SFINCS run; regenerate from the new outputs)

| product | script | inputs | feeds |
|---|---|---|---|
| per-run validation JSON (strict sweep, fuzzy r = 0…3, one-sided fuzzy, per-AOI) | `validation/validate_event_v2.py --config <yaml> --out-json` (+ `scripts/validate_existing.py`, `table_numbers.py`) | `model/sfincs_map.nc`, `data/ems_polygons`, YAML | Tables 3–10, 14; Fig 11 |
| cross-event aggregate | `validation/aggregate_metrics_v2.py` | per-event JSONs | Tables 9–10 |
| SEDI / PSS / CSI* / B* | `validation/skill_scores.py` (`tests/test_skill_scores.py` hard-codes the five contingency tables → must be updated) | contingency tables at h > 0.10 m | Table 14, Table 13, §4.4.2, §5.4 |
| grid-matched baseline Δ | `reproduction/grid_matched_baseline/score_baseline.py`, `make_report.py` | rows 5 + 6 outputs | Table 10 Pineios Δ |
| evaluation-mask sensitivity (AOI ± 1 km) | `manuscript/paper_submission_v5/_mask_sensitivity.py` (author-machine root hard-coded) | rows 1, 3, 5 outputs | Suppl. Table S3 / §7 "Table 18" sentence |
| truth-polygon uncertainty (± 20 m, acquisition offsets) | `validation/truth_uncertainty.py` | rows 1, 3, 5 outputs | §7 "± 0.012 / ± 0.003 / ± 0.041", §3.6 |
| bias-sweep CSV / plots / spatial fields | `scripts/bias_sweep.py` (post-run part) | rows 11–12 + 3, 5 | §5.2 sentence, `docs/bias_sensitivity/*` |
| Strymonas Δ adjudication, Emilia 8-AOI rescoring + depth forensics, Valencia ledger | `R1_verification/task2_strymonas_delta/`, `task_emilia_aoi/`, `task6_emilia_depth/`, `task5_valencia_ledger/` | rows 1, 2, 13, 7, 8 | Tables 8, 10, 13, 14; §4.4.2, §4.5.2 |
| figures f03/05/07/08/09 (QC maps), f04/f06 (rain series), f10 (skill summary), f11 (threshold/fuzzy sweeps) | `R1_verification/task7_figures/regen_qc_figure.py` + `make_hillshade_basemap.py`; `paper_submission_v5/_make_{pineios,mandra}_rain.py`; `_make_figures.py` (f10/f11 values are **embedded in the script**, not read from JSON) | rows 1, 3, 5, 7, 8 outputs; `imerg_<slug>.{raw.,}nc`, `era5_<slug>.nc` | Figs 3–11 |

## 3. Compute estimate (sequential, previous wall-clock on this machine where available)

| block | runs | Σ previous SFINCS wall-clock |
|---|---|---|
| canonical enhanced (rows 1, 3, 5, 7, 8) | 5 | 109.2 + 1097.8 + 1456.2 + 754.7 + 2230.7 = **5 648.6 s** (1.57 h) |
| baselines (rows 2, 4, 6) | 3 | 256.5 + 546.6 + 1006.4 = **1 809.5 s** (0.50 h) |
| Table 12 ablations (rows 9, 10) | 2 | 275.9 + 110.8 = **386.7 s** (0.11 h) |
| R2 sweeps (rows 11, 12) | 6 | 3 × 798.5 + 3 × 1371.7 = **6 510.6 s** (1.81 h) |
| audit / S2 variants (rows 13, 15, 16; row 14 if separate) | 3 (+1) | 219.6 + 1012.6 + 1906.7 = **3 138.9 s** (0.87 h) (+ 2116.0 s) |
| runs without surviving model dirs (rows 17–20) | 8 | 5 × 1097.8 + 2 × 1456.2 + 1706.7 = **10 108.1 s** (2.81 h) |
| **total** | **27 (+1)** | **27 602 s ≈ 7.7 h** (≈ 8.3 h with row 14) |

Add per run: hydromt build 0.5–1.5 min (Valencia/Emilia ≈ 1.3 min; ≈ 0.5 h in total), validation 1–3 min
(Pineios EMS polygons 3 GB; ≈ 1 h in total), figure/report regeneration ≈ 1 h → **≈ 10 h sequential**. The runs
are independent; two or three SFINCS processes in parallel roughly halve the wall-clock (not measured).
Uncertainty on the estimate: under v1.4 the IB boundary wets the whole GLO-30 sea plane (0 m cells), which
adds wet cells and may shorten the time step; the IMERG ×1 reduces inland flooding. Direction of the net change
unknown until the first run (row 1, 2 min) is done.

## 4. Proposed order

1. **Strymonas pair** (rows 1 + 2, ≈ 6 min): cheapest end-to-end check of the v1.4 harness on a published event;
   validate both; this fixes the magnitude of the D1/D2 effect before anything expensive runs.
2. **Mandra pair** (rows 3 + 4), then **Pineios pair** (rows 5 + 6) — development events, Tables 3–11.
3. **Emilia** (row 7), then **Valencia 164 mm** (row 8, the first pipeline-native 164-mm run) — held-out events,
   Tables 13–14. → After 1–3 every headline table (3–11, 13, 14) and Figs 3–10 can be regenerated (post-processing
   block: validation JSONs, aggregate, skill_scores + its tests, grid-matched Δ, Emilia 8-AOI rescoring, figures).
4. **Table 12 ablations** (rows 9–10).
5. **S2 / §5.2 variants** (rows 13, 15, 16; row 14 only if the S2 contrast is kept).
6. **R2 sweeps** (rows 11–12) → §5.2 sentence + `docs/bias_sensitivity`.
7. **Recreated sensitivity runs** (rows 17–20) — lowest priority: Papaioannou may prefer to drop the S1 CN rows and
   the "~38 km²" / "below 40 km²" / "0.105" statements instead of recreating runs that have no surviving record.
8. Post-processing block 2: mask sensitivity (S3), truth uncertainty (§7, §3.6), f10/f11 values (edit the scripts).

## 6. CODE-13 clean-up (2026-10-19)

### C1 — Strymonas baseline: which folder produced the published numbers

The published baseline numbers (Table 12 row 1, Table 8 baseline column, Table 10 Δ: CSI 0.204 / HR 0.377 / FAR 0.692)
come from **`D:/ELKAK/implementation/emsr122_sfincs/model`** (`sfincs_map.nc` 2026-05-22 10:08): both
`reproduction/val_json/strymonas_base.json` (2026-06-19, evaluation area 1222.6725 km², observed wet 106.5825 km²)
and `manuscript/paper_submission_v2/data/exp/strymonas_baseline_recheck.json` (`model_dir … emsr122_sfincs\model`)
score that folder and give 0.2039 / 0.3766 / 0.6921. Its data folder and the frozen record
`configs/as_run/emsr122_sfincs/data_catalog.yml` use the slug **`emsr122`** (`era5_emsr122.nc`,
`glofas_emsr122_clean.nc`), i.e. the run came from an earlier YAML with `event.slug: emsr122`; the committed example
`emsr122_strymonas.yaml` (slug `strymonas`) is otherwise identical (bbox [22.8, 40.6, 24.0, 41.4], 150 m, zmax 250,
tref 2015-03-27 → tstart 03-28 → tstop 04-04). Manifest fix (row 2): re-run from the committed example with
`SFINCS_WORK_DIR` on a new work dir seeded from `emsr122_sfincs/data` (junctions for `copdem30/`, `esa_worldcover/`,
`ems_polygons/`, `era5_extracted/`; `era5_emsr122.nc` copied as `era5_strymonas.nc`, `glofas_emsr122_clean.nc` as
`glofas_strymonas_clean.nc`) — no download; the slug only names the files.

### C2 — the eight runs without a surviving model directory

| # | run | exact sentence / table cell it feeds | configuration recoverable? | proposal |
|---|---|---|---|---|
| 1 | Mandra CN "HSG-A AMC-II (CN = 15 test)" | Suppl. Table S1 row 1: `HSG-A AMC-II (CN = 15 test) \| 42 \| 0.77 \| 0 \| 0.031 \| 0.032 \| 0.42`; §6.2 "TP = 0 at 01MANDRA for CN ∈ [15,95]" | approximately: a lookup with the pervious classes at CN 15 (mean realised CN 42 means built-up/water kept at 99/—); the exact lookup is not recorded | recreate with a uniform CN = 15 lookup for the pervious classes and relabel the row, or merge rows 1–3 into one "any CN ≤ 80" row (the three rows are identical to the millimetre) |
| 2 | Mandra CN "HSG-A AMC-II (CN ≈ 58 test)" | Table S1 row 2: `… \| 65 \| 0.77 \| 0 \| 0.031 \| 0.032 \| 0.42` | approximately (as row 1, CN 58) | as row 1 |
| 3 | Mandra CN "HSG-B AMC-II (default lookup)" | Table S1 row 3: `… \| 80 \| 0.77 \| 0 \| 0.031 \| 0.032 \| 0.42`; S1 prose "An initial enhanced run with standard HSG-B / AMC-II curve numbers yielded CSI = 0.031 with zero true positives in the central 01MANDRA area" | **exactly**: `emsr257_mandra_enhanced.yaml` + `infiltration: {enabled: true, hsg: B, amc: 2}` (pipeline default lookup) | recreate (supports contribution (iii)) |
| 4 | Mandra CN "HSG-D AMC-III (post-fire, saturated)" | Table S1 row 4: `… \| 97 \| 111 \| 0 \| 0.010 \| 0.036 \| 0.99`; S1 prose "for CN ≥ 97 (S ≤ 8 mm) the flood relocates eastward into the Aspropyrgos–Elefsina plain" | **exactly**: `infiltration: {enabled: true, hsg: D, amc: 3}` | recreate |
| 5 | Mandra Manning test (built-up n 0.012 → 0.080) | S1 prose "Raising the built-up Manning coefficient from n = 0.012 to 0.080 … produced no measurable change in per-area true positives or in total wet area (115.8 vs. 110.8 km² at CN = 97)" | **exactly**: row-4 configuration with a copy of `manning_lookup.csv` whose class-50 value is 0.080 (`paths.manning_lookup`) | recreate with row 4 (one extra run) |
| 6 | Pineios CN-on | §4.1.2 "(ii) SCS-CN disabled: a CN-enabled run (HSG-B, AMC-II, basin-mean CN ≈ 77) absorbed essentially all the rainfall and collapsed the flood to ~38 km² (against 1519 km² observed)"; §6.2 "The same recurs on Pineios (CN-on collapses the flood to ~38 km²)" | **exactly**: `emsr692_pineios_enhanced.yaml` + `infiltration.enabled: true` (the YAML documents this 2026-05-27 test) | recreate |
| 7 | Pineios raw IMERG | §5 "raw IMERG recovers only 141 mm and bounds the flood below 40 km²" (the 141 mm is a forcing statistic, Fig. 4) | **exactly**: `emsr692_pineios_enhanced.yaml` + `rain_bias_correct.enabled: false` | recreate (or drop the "below 40 km²" clause and keep the 141 mm, which needs no run) |
| 8 | Valencia raw IMERG | §4.4.2 "The uncorrected raw-IMERG run scores CSI = 0.105 (a sensitivity point; its full contingency table is archived with the released pipeline)"; §5.3 "raw-IMERG run scores CSI = 0.105"; Suppl. S3.1 "The uncorrected raw-IMERG Valencia sensitivity run (CSI = 0.105) is archived with the released pipeline" | **exactly**: `emsr773_valencia_enhanced.yaml` + `rain_bias_correct.enabled: false` (the contingency table is `S1_EMSR773_valencia_raw_IMERG_metrics.json`) | recreate |

Rows 3–8 are exactly recoverable from the committed YAMLs (6 runs); rows 1–2 only approximately. Proposal as stated by
the author: recreate the Supplement S1 curve-number rows (3, 4, and 1–2 relabelled or merged), recreate 5–8; nothing
has to be dropped for lack of configuration.

### C3 — baselines and the revised compute estimate (D4)

D4 changes every v1.4 run, baselines included: the open sea becomes inactive (Part A: 888 km² Pineios, 120 km² Mandra,
505 km² Strymonas, 2 252 km² Valencia, 1 682 km² Emilia, 22 224 km² Crete), the boundary moves from the grid perimeter
to the coastal ring, and every cell starts dry (zsini −9999 instead of 0 — Valencia and Emilia previously started
with 88.6 and 286.9 Mm³ of water in land cells with zb < 0). Rows 2, 4 and 6 (the three baselines) are therefore
**mandatory**, not optional same-harness re-runs; their ERA5 forcing is unchanged (D1 affects IMERG only).

Active cells v1.3 → v1.4 (Part A (i) removed, one-cell ring kept): Pineios 262 465 → ≈ 223 k; Mandra 162 335 → ≈ 114 k;
Strymonas 207 374 → ≈ 185 k; Valencia 521 427 → ≈ 296 k; Emilia 300 965 → ≈ 226 k; Crete 3 067 497 → **859 727**
(measured, `buildqc_v14/rebuild_v14.json`: prep 6.6 s, hydromt build 208.6 s, sub-grid 545 MB instead of 1 950 MB,
13 858 msk = 2 cells, 160 bnd points). The removed sea cells were dry in v1.3 (cheap per step), so the published
wall-clocks of Section 3 stay the planning figure for the five events (Valencia may drop by up to ~30 %); the IB now
wets the coastal ring only. Crete (not in the R5 total): scaling Pineios' 1 456 s for 262 k cells × 8 d to 860 k cells
× 8 d gives ≈ 4 800 s ≈ 1.3 h per run (≈ 4.7 h with the sea active), i.e. ≈ 4 h for baseline + enhanced + R2on, plus
≈ 4 min build each — to be measured on the first Crete run.

## 5. Manuscript residues to fix in the same pass (facts from the inventory, not new findings)

Table 9 Valencia B/GSS (12.15/0.021) and Emilia B/GSS (4.98/0.055), Table 13 "3202 / 443" and Table 14 B* values still
carry the superseded 350-mm / Forlì-only numbers; §4.1.2 still says there is no grid-matched Pineios baseline although
Table 10 prints its Δ; the Strymonas v1→v3 stale items listed in AUDIT.md §3 (CODE-2).

## 7. GO-C status (2026-10-19; Papaioannou's decisions in docs/AUDIT.md §9 and reproduction/emsr933/rule_ledger.md §8)

Harness v1.4 = D1 + D2 + D4 + D5 (commits `513ce5a`, `561e8a0`, `8ccabb0`), evaluation mask = AOI ∩ active minus
(WorldCover 80 ∪ v1.4 open sea), both sides (commit `c6f39fa`). **Phase 1 executed** (rows 1–6) by
`scripts/phase1.py`: each run in `D:/ELKAK/implementation/v14/<run>/` with its data seeded from the published data
directory (junctions for DEM/WorldCover/EMS/ERA5-extracted, copies of the per-event files; the published directories
are only read), its config in `configs/<run>.yaml` (= the example + `harness_version: v1.4` + the local work dir; row 6
derived from the Pineios enhanced example with every enhanced block off — its v1.3 rendering equals the frozen
`grid_matched_baseline/work/sfincs_build.yml`), and its records in `results/` (`<run>_v14_newmask.json`,
`<run>_v13_publishedmask.json` = the published output re-scored (identical to the committed validation JSONs),
`<run>_v13_newmask.json` = the published output with the new mask, `<run>_record.json` = timings, coastal prep, exclusion;
`<enhanced>_v13_fa_share.json`), masks in `masks/<event>_exclusion.{tif,json}`, quick-looks in `quicklook/`.
Tables: `CHECKPOINT4.md` (generated by `scripts/checkpoint4_tables.py`).

**New defect D6 (report only; `../v14_harness/D6_CN_SINK.md`)**: SFINCS curve-number infiltration without
`storecumprcp = 1` is an unbounded sink. Rows using CN: 1 (Phase 1 — its v1.4 result is not a valid v1.4 number), 10,
13, 17, 18. Fix decision pending; until then rows 10, 13, 17, 18 should not be run.

Phases 2–5 wait for the author's go (GO-C execution order).
