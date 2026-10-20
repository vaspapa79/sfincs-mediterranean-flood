# VALIDATION_FINDINGS — sfincs-mediterranean-floods

Canonical record of the Phase-0 static review (mapping + code review, **no reproduction
yet**) of the SFINCS Mediterranean-floods reproduction repo, ahead of a full re-run on a
**fresh Windows machine** and manuscript review for *Natural Hazards*.

- Method: read-only review of `skill/` (pipeline), `validation/` (metrics + audits),
  `configs/as_run/`, `environment.yml`, repo docs, plus cross-check against the manuscript
  (`paper_v2`/`paper_submission_v*`) and `documents/emsr692/{methodology,reproducibility}.md`.
- Date: 2026-06-12. Reviewer machine: `dvalsamis` (author machine was `vaspapa`).
- **Good news up front:** manuscript↔code numerical consistency is **excellent** — every
  headline value matches the committed JSON and the v2 manuscript to the decimal
  (Pineios/EMSR692 CSI 0.456 / HR 0.947; Strymonas/EMSR122 v3 CSI 0.183 / HR 0.328;
  Mandra/EMSR257 CSI 0.106 / HR 0.873). No number, EMS code, event name or threshold
  discrepancy was found. The issues below are reproducibility, correctness-robustness, and
  documentation — not wrong results.

Severity: **HIGH** = blocks a clean first reproduction on the new machine, or could silently
corrupt a headline number. **MED** = real gap, won't necessarily halt a run. **LOW** = polish.
🆕 = must be fixed/decided before submission.

---

## A. Reproducibility & portability (the new-machine priority)

- **R1 (HIGH)** — Hardcoded author-machine paths are pervasive. `run_pipeline.py:60` defaults
  `--python` to `C:/Users/vaspapa/.../envs/sfincs-viz/python.exe`; **every** `skill/examples/*.yaml`
  hardcodes `env.{python,hydromt,sfincs_exe,gdal_data,gdalbuildvrt}` and `paths.{work_dir,
  deliverable_dir,zip_dir}` under `C:/Users/vaspapa/`; `validation/deep_audit.py:35`,
  `validation/spatial_audit.py:28,32`, `validation/validate_event_v2.py:44-45` (GDAL_DATA), and
  `documents/emsr692/reproducibility.md` + `skill/references/environment_setup.md` (throughout)
  all assume user `vaspapa` + `Desktop\ELKAK\`. None resolve on the new box.
  *Fix:* move `env:`/`paths:` to a single machine-local override (env vars / `%USERPROFILE%` /
  one override file); default `--python` to `sys.executable`; add a **preflight `--check`** that
  validates `python, hydromt, sfincs_exe, gdalbuildvrt, gdal_data, ~/.cdsapirc, ~/.netrc` exist
  *before* step 01 (currently a wrong tool path only fails at step 10–11, after hours of downloads).
- **R2 (HIGH)** — **Strymonas v3 (the canonical headline run) has no committed as-run config.**
  The paper's Strymonas headline (CSI 0.183, from the relocated Kerkini `src` cell, zb 171 m→12 m)
  is run `emsr122_sfincs_v3`; `configs/as_run/` ships only `emsr122_sfincs{,_enhanced}` and
  `grep v3` returns nothing. The single most important corrected number is **not reproducible from
  the repo**.
  *Recovered 2026-06-12 from `implementation/emsr122_sfincs_v3/model/` (`sfincs.src.orig` vs
  `sfincs.src`):* the fix relocated **src point 1 (kerkini)** from `(684806, 4549970)` to
  `(701692, 4544737)` UTM34N; point 2 (angitis `745591/4542865`) unchanged. **The committed example
  still carries the BROKEN coord** — `skill/examples/emsr122_strymonas_enhanced.yaml:69`
  `kerkini_outlet {lon 23.2, lat 41.08}` converts to exactly the `.orig` point `(684806,4549970)`,
  so the repo as-committed reproduces the *un-fixed* Strymonas, **not** the headline 0.183.
  **Exact fix:** set `kerkini_outlet` to **`{lon: 23.3991, lat: 41.0289}`** (UTM 701692/4544737).
  Build params (`sfincs.inp`): 690x611 @150 m, x0 650467 / y0 4495912, EPSG 32634, tref 20150321 /
  tstart 20150328 / tstop 20150404, `pavbnd 1`, `scsfile` on. Also commit a
  `configs/as_run/emsr122_sfincs_v3/` record (the two src coords + `sfincs.inp` excerpt).
- **R3 (HIGH)** — SFINCS binary acquisition is manual + off-repo. The exe + DLL set
  (`hdf5.dll, netcdf.dll, libifcoremd.dll, libiomp5md.dll, libmmd.dll`) must co-locate; the only
  on-disk source (`implementation/SFINCS.zip`) lives on the old machine. *Fix:* document the exact
  Deltares release tag (`v2.3.0 mt_Faber_release_2025.02`), download URL, and DLL manifest as a
  checklist item.
- **R4 (HIGH)** — Earthdata/IMERG credential setup is named but undocumented. IMERG is the headline
  forcing for **all** enhanced runs; `download_imerg.py` relies on `earthaccess` + `~/.netrc`, but
  no doc shows the login command/file format. *Fix:* add an explicit `earthaccess login` step.
- **R5 (MED)** — IMERG bias-correction factor is not captured in any config. `bias_correct_imerg.py`
  applies a gauge-anchored scaling via `--target-mm` CLI (Pineios ×2.73 / target 400 mm; Mandra
  ×8.55 / 200 mm) — values live only in prose/CLI history, so rainfall totals aren't deterministically
  reproducible. *Fix:* add a `rain_bias_correct: {enabled, target_mm, watershed_bbox}` block to the
  enhanced YAMLs, read by `run_pipeline.py`.
  **✅ FIXED (2026-06-22):** added `rain_bias_correct` (enabled, target_mm, watershed_bbox,
  event_start, event_end) to `emsr692_pineios_enhanced.yaml` (400 mm / `22.0,39.4,22.95,40.0` /
  2023-09-04→08, ×2.725) and `emsr257_mandra_enhanced.yaml` (200 mm / `23.40,38.05,23.55,38.15` /
  2017-11-14→15, ×8.551); explicit `enabled:false` on Strymonas (Kerkini-Q-driven, raw IMERG).
  Values recovered verbatim from each `imerg_<slug>.nc:bias_correction` attribute. `_common.py`
  exposes `EventCfg.rain_bias_correct`; `run_pipeline.py` runs it as **step 06b** (after
  download_imerg, before prep) via `bias_correct_imerg.py` — idempotent, no-op when absent/disabled.
  Verified: generated CLI matches the historical invocation byte-for-byte; preflight passes.
- **R6 (MED)** — Pineios **baseline** build references `…/Pineios/Computational_grid.shp`
  (`configs/as_run/pineios_sfincs/sfincs_build.yml:18-20`), a shapefile **not in the repo** and not
  covered by `.gitignore` (just never committed); also `res:100` vs the example's `res:150`.
  *Fix:* commit the shapefile or switch this build to the bbox-based `sfincs_build_wide.yml`; document
  the res discrepancy.
- **R7 (MED)** — `numpy` is unpinned (only `libblas=*=*openblas` is pinned). A 2026+ `conda env create`
  may reintroduce the very `numpy.dot` MKL regression the BLAS pin guards against, or drift from the
  paper's numbers. *Fix:* pin `numpy` (+ key scientific deps) to the versions used for the paper.
- **R8 (MED)** — `skill/references/{environment_setup,troubleshooting}.md` point to
  `feedback_windows_blas.md`, which is **not in the repo** (the author's private `~/.claude` memory).
  *Fix:* inline the BLAS-bug explanation into `troubleshooting.md`.
- **R9 (MED)** — `download_dem.py:37-38` / `download_worldcover.py:35-36` print `FAILED` and continue
  on a per-tile HTTP error, then build the VRT from whatever landed → a silently holey DEM/landcover
  mosaic, no error. *Fix:* abort non-zero if any required tile is missing.
- **R10 (MED)** — `download_era5.py:34-38` warns then proceeds with `years[0]` for a multi-year window
  → a New-Year-straddling event silently drops the second year. *Fix:* split into per-year requests.
- **R11 (MED)** — The validators import the pipeline helpers from a **sibling `.claude` skill**, not the
  repo's own `skill/`. `validate_event.py:46` sets `SKILL_DIR = parents[2] / ".claude" / "skills" /
  "sfincs-flood-reproduction"` and imports `_common`/`_anim_common` from there. A clean checkout of the
  repo **alone** (without `D:\ELKAK\.claude\skills\sfincs-flood-reproduction\scripts` beside it) fails to
  import. (Related: `configs/as_run/*/sfincs_build.yml` `reclass_table` also points at a `.claude/skills/…`
  path.) *Fix:* import from the repo's own `skill/scripts` (`parents[1] / "skill" / "scripts"`), or document
  that the `.claude` skill must be present alongside the repo.

## B. Validation correctness (could affect/undermine a headline number — verify on re-run)

- **V1 (LOW — VERIFIED non-bug, 2026-06-12)** — `_rasterise_polys_to_grid` does an unconditional
  `out[::-1,:]` flip assuming ascending-y. **Checked against four real outputs** (Strymonas v3,
  Pineios, Mandra v3, Strymonas enhanced via `e:\tools\v1_orientation_check.py`): **all store y
  ascending** (`y[1]>y[0]`), so the flip is **correct** and the headline CSI is *not* affected.
  Residual risk is latent only: a future grid with descending y would silently break.
  *Fix (nice-to-have):* derive the flip from `sign(y[1]-y[0])`, or assert ascending-y in `open_sfincs`.
- **V2 (HIGH)** — `aggregate_metrics_v2.py` (the source of the README headline table) is NaN-unsafe:
  `:.3f` is applied directly (no `_f()` guard like v1), and `best_thr` is `None` whenever every
  threshold gives NaN CSI, so `f"{best_thr:.2f}"` (L39) raises `TypeError` and aborts the whole
  headline table; NaN GSS/B (e.g. Mandra over-prediction) prints `"nan"` into the `.tex`/`.md`.
  *Fix:* route v2 formatting through a NaN-safe formatter; guard `best_thr is None`.
  **✅ FIXED (2026-06-22):** added `_f()` (mirrors v1's NaN/None guard) and routed every `.tex`/`.md`
  cell through it; `best_thr = val.get(...)` with an `if best_thr is None` guard before the
  `f"h>{best_thr:.2f}m"` lookup. Regression-tested against the docs/AUDIT.md headline values: non-NaN
  `.md`/`.tex` output is **byte-identical** before/after; the all-NaN-CSI case now renders `—` instead
  of raising `TypeError`. No non-NaN value altered.
- **V3 (MED) 🆕** — The "asymmetric fuzzy (Wing et al. 2017)" block (`validate_event_v2.py:226-236`)
  **dilates both** model and obs — byte-identical to the symmetric fuzzy (L220-224), so
  `fuzzy_asym == fuzzy` always. The paper's one-sided early-warning convention is **not implemented**,
  and dilating both sides systematically overstates fuzzy CSI (e.g. Mandra "fuzzy r=2 CSI 0.205").
  *Fix:* implement true one-sided neighbourhood matching, then re-derive the fuzzy rows; or correct
  the manuscript's description. **Reviewer-exposed — decide before submission.**
  **✅ FIXED (2026-06-22, code) — manuscript wording still TODO(author):** replaced the duplicate
  block in `validate_event_v2.py` with two genuine one-sided sweeps — **model-oriented** (dilate OBS
  only → tolerant FAR/precision, keys `fuzzy_model_oriented_dilate_obs_at_h_gt_0p10m`) and
  **obs-oriented** (dilate MODEL only → tolerant HR/recall, `fuzzy_obs_oriented_dilate_model_…`);
  symmetric block kept for comparison; r=0 reduces to strict in every direction. Re-scored the 3
  canonical runs from stored `sfincs_map.nc` (no SFINCS re-run) via `validation/score_fuzzy_onesided.py`
  → `docs/fuzzy_onesided.{json,md}`. **Strict anchors preserved exactly** (Pineios 0.456/0.947,
  Strymonas-v3 0.183/0.328 [scored vs `model_author_ref/`], Mandra 0.106/0.873). Confirms the
  overstatement: Mandra symmetric fuzzy r=2 CSI 0.205 / HR 0.986 splits into obs-oriented HR 0.994 but
  CSI **0.086** (false alarms unforgiven) vs model-oriented CSI 0.207 / HR 0.748. The manuscript §3.5
  text + Table fuzzy rows should adopt the one-sided columns (or keep symmetric with an explicit
  both-sided caveat) — author call.
- **V4 (LOW)** — Polygons burned with `all_touched=True` (all scripts) enlarge observed/AOI extent by
  ~½ cell per boundary; a real area bias on thin riverine floods (Strymonas/Pineios). Defensible but
  should be disclosed in methods.
  **✅ QUANTIFIED for disclosure (2026-06-23, B3):** `all_touched=True` vs `=False` observed-extent
  inflation — Pineios **+17.7%** (1519 vs 1290 km²), Strymonas **+52.2%** (107 vs 70 km²), Mandra
  **+81.8%** (8.99 vs 4.94 km²); AOI-mask inflation is negligible (+0.3 / +0.6 / +1.4%). Largest for
  the small/fragmented GRADING extents. Full numbers in `docs/truth_uncertainty.md §(c)` — drop the
  table into Methods. Affects all runs identically; slightly favours HR over FAR.
- **V5 (LOW)** — `hmax` NaN handling: cells with valid `zsmax` but NaN `zb` (DEM nodata inside the
  active mask) yield NaN depth → silently dropped from TP/FP rather than flagged. Low probability.

## C. Manuscript / metadata consistency (before submission)

- **C1 (LOW — RECONCILED 2026-06-12) 🆕** — Manuscript is at **v5** (`paper_submission_v5/`).
  `RESPONSE_TO_REVIEWS_v5.md` shows v4→v5 added **only** a literature-comparison Table 11, four
  references (Sadana2025, Bellos2022, Capolongo2019, He2024) and three positioning paragraphs —
  **no headline number changed.** v5 Table 11 reaffirms the repo values exactly: Pineios 0.456
  (peak 0.515), Strymonas 0.183, Mandra 0.106 (fuzzy 0.205). So the repo README headline +
  CITATION stay consistent with the live submission — nothing to change there. (The v5 literature
  additions are manuscript-only; they don't need to live in the repo. Main text is now 13 tables /
  48 refs.) Note `~$per_NaturalHazards_submission.docx` in v5 is a stray Word lock file — delete it.
- **C2 (MED) 🆕** — Grant number disagreement. README Acknowledgements cite ECHO GA **101225575**;
  the manuscript `11_acknowledgements.tex` has **no grant number**; `CITATION.cff` has no funding
  field. *Fix:* decide whether 101225575 belongs in the paper, then make all three agree.
- **C3 (LOW)** — Pineios HR printed as `0.947` (README + per-event table) but `0.95` (abstract / §4
  intro); copy-edit will flag the rounding mismatch.
- **C4 (LOW) 🆕** — Zenodo DOI is still a placeholder ("assigned on first stable release") in README
  §Citing and `10_data_code_availability.tex`; `CITATION.cff` has no `doi:`/`version:`. To be minted
  at the v1.0.0 release (Phase 3) and back-filled.
- **C5 (LOW)** — Only Papaioannou has an ORCID in `CITATION.cff`; *Natural Hazards* encourages ORCIDs.

## D. Documentation drift (mislead a reproducer/reviewer)

- **D1 (MED)** — Step-count + scope drift across three docs: README says **16 steps**, `SKILL.md`
  says **13** (and "rain-on-grid only — no upstream Q in the default workflow"), actual non-underscore
  scripts = **19**. The enhanced pipeline the paper reports (GloFAS-Q injection, CN, IMERG) is **not**
  in SKILL.md's numbered list. *Fix:* regenerate SKILL.md's step list from `STEPS`; state the enhanced
  steps explicitly.
- **D2 (MED)** — `documents/emsr692/methodology.md` documents a **stale** model (100 m, lower-reach
  Pineios, 77 233 cells, "no upstream discharge boundary") that **contradicts** the paper's 150 m
  wide-Thessaly domain (262 465 cells) **with** GloFAS-Q. *Fix:* mark superseded or update to the
  enhanced config. (The paper's real methods, `sections/03_data_and_methods.tex`, are not contradicted.)
- **D3 (LOW)** — `config_schema.md` omits the enhanced-only top-level keys actually parsed
  (`rain_source, coastal_bc, wind_pressure, infiltration, upstream_q`). *Fix:* add them.
- **D4 (LOW)** — `make_mp4.py:155` hardcodes the SFINCS version string in the caption;
  `package_deliverable.py:119` hardcodes EMS provenance ("16 vector products…") regardless of backend;
  `package_deliverable.py:218` zip-suffix detection hardcodes `(_enhanced,_v3,_v4,_v5)`. Cosmetic.

---

## Phase plan (where this fits)

0. **Map + static review — THIS DOCUMENT (done, this machine).**
1. Reproduction on the new machine: fix R1–R10 first, then `run_pipeline.py` per event, re-run
   `validate_event_v2.py` + `aggregate_metrics_v2.py`, confirm the three headline CSI/HR. Verify **V1**
   against a real `sfincs_map.nc` on day one.
2. Manuscript review against **v5** (claims ↔ reproduced numbers; resolve V3, C1–C3).
3. Publish: GitHub `vaspapa79/sfincs-mediterranean-floods` + Zenodo **v1.0.0** (mint DOI, back-fill C4).

## Independent-reproduction priorities (cannot be confirmed without a re-run)
All three headline CSI/HR (the generating `sfincs_map.nc` is git-ignored), the Strymonas v3 src-fix
deltas (CSI 0.170→0.183, peak depth 12.2→5.6 m — see R2), the IMERG bias factors (R5), and the
per-AOI tables. These are the Phase-1 checklist.
