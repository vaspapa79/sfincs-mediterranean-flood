# EMSR933 Crete — Stage 0 report (preflight · EMS snapshot · data availability)

Session 2026-10-09 (UTC). Branch `emsr933-crete`, linked worktree
`sfincs-mediterranean-floods/.worktrees/emsr933-crete`, base `origin/main` = **v1.3.0 `ccd423a`**
(`--no-track`; the dirty `main` checkout at the repo root was not touched). Every value below is copied
from the files named in brackets; nothing is retyped from the task text.

## 0a Preflight — PASS
- `skill/scripts/run_pipeline.py --check` (worktree copy, `skill/machine.local.yaml` override copied from
  the main checkout, gitignored): all tool paths and credential files resolve.
- Extended check `scripts/preflight_stage0.py` → [`preflight_stage0.json`](preflight_stage0.json) /
  [`.log`](preflight_stage0.log): `numpy.dot(eye3,eye3).sum()` = 3.0; `libblas` build `8_h0adab6e_openblas`;
  hydromt 0.10.1, hydromt_sfincs 1.2.2, numpy 2.4.6, GDAL 3.12.2 (rasterio 1.4.4 / pyogrio 0.12.1),
  xarray 2026.4.0, earthaccess 0.17.0, cdsapi 0.7.7; `sfincs.exe` (v2.3.0 mt_Faber) + 9 co-located DLLs;
  CDS **and** EWDS personal-access-token verification HTTP 200 with the one `~/.cdsapirc` key; Earthdata
  `earthaccess.login(strategy="netrc")` authenticated; both `_common` import paths import (worktree
  `skill/scripts` and `D:/ELKAK/.claude/skills/sfincs-flood-reproduction/scripts`); `SFINCS_SKILL_DIR` unset.
  The JSON/log contain no secrets (redacted before writing).

## 0b EMS snapshot — provisional truth cut-off **2026-10-09T12:47:20Z**
Script `scripts/ems_snapshot.py` (API fetch + download of every product with `statusCode F` and a
`downloadPath`; zip-slip-safe extraction into a new empty directory) and `scripts/ems_package_metadata.py`
(per-package metadata from the in-package `source_v1` table).
- Raw API bytes: [`ems_api_snapshot_20261009T124720Z.json`](ems_api_snapshot_20261009T124720Z.json)
  (31 606 B, sha256 `0aa29458ad5eae8449a0b28d4ab386a4104e180b9f05ca5f0cb919f2077f6b94`; identical bytes
  from `mapping.` and `rapidmapping.emergency.copernicus.eu`, so the pipeline's `base_url` still works).
- Parsed + download record: [`ems_snapshot_20261009T124720Z_manifest.json`](ems_snapshot_20261009T124720Z_manifest.json)
  (zip sha256, member list, per-layer feature counts/fields/areas);
  AOI × product table: [`ems_snapshot_20261009T124720Z.md`](ems_snapshot_20261009T124720Z.md);
  per-product metadata: [`ems_snapshot_20261009T124720Z_products.md`](ems_snapshot_20261009T124720Z_products.md)
  / [`.csv`](ems_snapshot_20261009T124720Z_products.csv).
- Packages (untrusted downloads, kept outside the repo):
  `D:/ELKAK/implementation/emsr933_crete/ems_snapshots/20261009T124720Z/{zips,extracted}/`.
- Activation record (JSON): `eventTime 2026-10-01T07:00:00`, `activationTime 2026-10-04T11:02:00`,
  `closed false`, Flood / Flash flood, activator GSCP (Greece); 8 AOIs. Matches the task metadata.

Released at the cut-off — 6 packages, 5 AOIs (from `_products.md`; areas = union in EPSG:32634):

| AOI | product (id) | post-event source (`source_v1`) | acquired UTC | obs km² | notes |
|---|---|---|---|---|---|
| 01 Kastelli | DEL_MONIT01 (2962) | Legion optical 1.2 m | 2026-10-06 10:47 | 0.242 | trace 0.1438 / flooded 0.0982; notAnalysed 45.298 km² |
| 03 Tzermiado | DEL (2955) | Sentinel-1 SAR 20 m | 2026-10-04 16:22 | 3.2192 | flooded area only |
| 03 Tzermiado | DEL_MONIT02 (2959) | GeoEye-1 optical 2 m | 2026-10-08 09:02 | 3.7807 | trace 1.2533 / flooded 2.5274; has maximumFloodExtentA |
| 04 Agios Ioannis | DEL_MONIT01 (2957) | WorldView-3 optical 1.6 m | 2026-10-06 10:46 | 0.0325 | all "Flood trace" |
| 06 Agios Nikolaos | DEL_MONIT01 (2960) | Legion optical 2 m | 2026-10-08 08:55 | 0.0593 | trace 0.0575; includes 6-Mass Movement (mudflow) 0.0017 |
| 07 Omalos | DEL_MONIT01 (2964) | Legion optical 1.6 m | 2026-10-06 10:45 | 0.0506 | flooded area; notAnalysed 30.047 km² |

Not released: AOI02 Irakleio (DEL N, MONIT01 N), AOI05 Anogeia (DEL N, MONIT01 N), AOI08 Monastiraki
(DEL N, MONIT01 N) — all "Because of remote sensing limitations"; AOI03 DEL_MONIT01 N ("no change of
situation detected"); **AOI03 GRA status I**, expected 2026-10-09T21:00 (Legion VHR1, 09:32 UTC). The
first-pass Sentinel-1 DEL of 4 Oct was not produced for AOI01/02/05/06/07 (remote-sensing limitations);
only Tzermiado has a SAR delineation.

## 0c Input-data availability, 27 Sep – 7 Oct 2026
[`data_availability_summary.md`](data_availability_summary.md) (generated from
[`data_availability_20261009T125144Z.json`](data_availability_20261009T125144Z.json) and
[`era5t_probe_20261009T125219Z.json`](era5t_probe_20261009T125219Z.json)). In short:
- IMERG **Late** V07 (`GPM_3IMERGHHL`): 528/528 half-hourly granules, 48 per day, all `V07C`
  (`3B-HHR-L.MS.MRG.3IMERG.<YYYYMMDD>-S<hhmmss>-E<hhmmss>.<mmmm>.V07C.HDF5`). IMERG **Final**: 0 granules.
- ERA5 single levels (CDS): requestable **only through 2026-10-03** (catalogue extent ends 2026-10-03T00:00);
  one-point probe shows every step 27 Sep–3 Oct is `expver 0005` (**ERA5T**); 4–7 Oct not yet published.
- GloFAS v4 historical (EWDS): `intermediate` 27 Sep–**6 Oct**; `consolidated` and v5: nothing for Sep–Oct 2026.
  The pipeline's request vocabulary (`hyear/hmonth/hday`, `river_discharge_in_the_last_24_hours`) is
  **rejected (HTTP 422)**; current inputs are `year/month/day`, `timespan`, variable
  `average_river_discharge_in_the_last_24_hours`.
- Copernicus DEM GLO-30: 8 tiles N34–N35 × E023–E026 all HTTP 200; ESA WorldCover 2021 v200: tiles
  N33E021, N33E024 HTTP 200.

## Findings that need action or a decision
- **F1 — ERA5 not yet available for 4–7 Oct.** Under R the baseline rain and R6 wind/MSLP come from ERA5, so
  Stage 2 cannot start before CDS publishes the post-event days (ERA5T lag ≈ 5 d → ≈ 12–13 Oct). No
  rule-conformant workaround; the wait goes into the timing log as data latency.
  ERA5T handling: the current CDS netCDF carries `expver` as a 1-D variable along `valid_time` (probe
  file), not the old two-member dimension — there is no NaN half to drop, and `prep_inputs.py` already
  renames `valid_time`→`time` and drops `expver`/`number`. The declared deviation therefore reduces to
  *recording* which steps were `0005` (a log line + netCDF attribute in `prep_inputs.py`, Stage 2).
- **F2 — harness pattern gap (needs a code fix + regression).** The AOI03 first delineation is a
  `DEL_PRODUCT` package (`EMSR933_AOI03_DEL_PRODUCT_observedEventA_v1.shp`); none of the six shapefile
  patterns in `skill/scripts/download_ems.py` and `validation/validate_event_v2.py::_select_obs_shps`
  (`*DEL_MONIT*…`, `*GRA_PRODUCT*…`, legacy `DELINEATION`/`GRADING`) matches it, so the 4-Oct Sentinel-1
  delineation of Tzermiado would be silently dropped. Fix = add `*DEL_PRODUCT*observedEventA*.shp` and
  count `DEL_PRODUCT` in the DEL tier. EMSR773/EMSR664 packages are all `DEL_MONIT`/`GRA_MONIT`, so their
  numbers cannot move; the regression re-run is still owed (rule 5).
- **F3 — GloFAS vocabulary (only if R3 triggers in Stage 1).** `download_glofas.py` must move to the current
  EWDS inputs and to `product_type intermediate` for 2026; `prep_inputs.py` renames `dis24`, so the new
  variable name must be checked. Product version to be recorded (declared deviation).
- **F4 — IMERG Late switch (declared deviation).** `download_imerg.py` searches `GPM_3IMERGHH` only; add
  `rain_source.product: late|final` (Late → `GPM_3IMERGHHL`) without changing Final-run behaviour; the
  hard-coded "IMERG Final V07" attributes must follow the switch.
- **F5 — inherited harness defects; DECISION before Stage 2/3.** In v1.3.0 the build template feeds the
  precipitation grid to hydromt_sfincs `setup_precip_forcing_from_grid` with its defaults
  (`cumulative_input=True`, `time_label='right'` — confirmed in this env), so half-hourly IMERG in mm/h is
  applied **doubled** and 30 min early (factor 2.000 measured 2026-09-30 on the three Greek enhanced runs;
  hourly ERA5 unaffected); there is no `tspinup` (`zsini 0`; `spinup_days` only shifts `tref`), and the
  coastal boundary has `pavbnd` but no water-level forcing (`bnd/bzs` absent → 0 m). EMSR773/EMSR664 were
  run this way. Options: (a) run EMSR933 with the harness exactly as published — comparable to the two
  held-out events, inherits the ×2 rain; (b) fix the IMERG handling for this run — physically right, but
  then Crete is not scored by the same harness as the five published events unless they are re-run. R is
  silent on implementation → not mine to pick. **DECISION FOR PAPAIOANNOU / DvS.**
- **F6 — truth-content caveats for Stage 4 reporting (no harness change).** `observedEventA` mixes
  "Flood trace" and "Flooded area" notation and, in Agios Nikolaos, a 6-Mass Movement polygon; the harness
  unions every `observedEventA` feature regardless of `notation`/`event_type` — the same treatment the
  published held-out events received (checked 2026-10-09 on the stored packages: EMSR773 AOI01 MONIT02,
  AOI06 MONIT01 and AOI14 GRA_MONIT01 carry "Flood trace" rows, EMSR664 AOI01 MONIT01–03 carry "Previous
  flooded area" rows, all alongside "Flooded area"); `notAnalysed`
  areas of 45.3 km² (Kastelli) and 30.0 km² (Omalos) lie inside AOIs and are not excluded from the
  evaluation mask; AOIs 02/05/08 ship no package, hence no `areaOfInterestA` polygon, hence drop out of the
  evaluation universe; four of five scored AOIs have 0.03–0.24 km² observed-wet → CSI will be unstable;
  obs-wet km² must be reported per AOI.
- **F7 — timing.** activationTime 2026-10-04T11:02Z → task received 2026-10-09T12:35:48Z (idle 5 d 1.6 h,
  before the task was issued) → Stage 0 records complete 2026-10-09T12:54Z (see `timing.md`).

## F2 / F4 implemented — regression result (Stage 1, 2026-10-09; record `regression_f2f4.json`)
Approved at Checkpoint 0. TDD: `tests/test_select_obs_shps.py`, `tests/test_rain_source_product.py`
(14 tests, RED observed → GREEN). **Design change forced by a new fact:** the canonical EMSR664 8-AOI truth
directory (`R1_verification/task_emilia_aoi/data/ems_polygons`) *does* contain `EMSR664_AOI01_DEL_PRODUCT_v1`
(observedEventA, 1153 features), so an unconditional DEL_PRODUCT pattern would have changed the published
report (`n_obs_shp` 13 → 14). Inclusion is therefore an explicit per-event switch `ems.include_del_product`
(default off = published behaviour; EMSR933 sets it true) in both `download_ems.py` (merge) and
`validate_event_v2._select_obs_shps` (truth union). F4: `rain_source: {name: imerg_half_hourly, product: late}`;
the string form stays Final and string-for-string identical (`IMERG_PRODUCTS` in `download_imerg.py`,
`EventCfg.imerg_product`).

Regression (`scripts/regression_f2f4.py`, switch off, worktree validator):
- Valencia EMSR773 (164-mm canonical, `_scoring/v164`): full validation block **IDENTICAL** to
  `_scoring/score_v164.json`; condensed values **IDENTICAL** to `reports/valencia_emsr773_metrics.json`
  (n_ems_shps 5, CSI@0.10 0.093878).
- Emilia-Romagna EMSR664 (canonical model + 8-AOI truth via junctions): condensed values **IDENTICAL** to
  `reports/emilia_emsr664_metrics.json`; contingency **IDENTICAL** to `_scoring/emilia_rescore.json`
  (n_ems_shps 13, CSI@0.10 0.240386).
- DIAGNOSTIC only (never canonical): Emilia with `include_del_product: true` → n_ems_shps 14, observed-wet
  592.605 km² **unchanged**, CSI 0.24038585 / HR 0.92060901 **unchanged** — the DEL_PRODUCT polygons are
  geometrically contained in the published union (they coincide with the MONIT01 "Previous flooded area"
  layer, 1153 features each). The published Emilia truth is complete; only a shapefile count would differ.
- F6 check: the EMSR773 and EMSR664 packages (runs/ and the 8-AOI set) contain **no** `notAnalysedA` layer,
  so the Crete notAnalysed exclusion (Stage 4, also as a per-event switch) cannot touch them.

## Next (Stage 1, no model runs) — after the go
Catchment delineation per AOI from GLO-30, sea-cell test (R5), closed-polje sinks (Tzermiado, Omalos),
a-priori meteorology classification (R2 both ways, R4 AMC-III), Δx logic recovery from the EMSR773/EMSR664
records (`Box 1 does not fix Δx`), UTM 34N distortion at 26.4 E, rule ledger + the two YAMLs, `prep_inputs.py`
schema validation only.
