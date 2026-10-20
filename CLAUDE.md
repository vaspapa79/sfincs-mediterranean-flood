# CLAUDE.md — sfincs-mediterranean-floods

Lean, loaded every session. The **full auditable record is [docs/AUDIT.md](docs/AUDIT.md)**;
ground-truth numbers live in [docs/_sources/VALIDATION_SUMMARY_for_review.md](docs/_sources/VALIDATION_SUMMARY_for_review.md)
and the per-event JSON reports.

## Scope
Enhanced-forcing **SFINCS** reproduction of three Greek flood archetypes — **Mandra**
(EMSR257, 2017 convective urban), **Strymonas** (EMSR122, 2015 transboundary), **Pineios /
Storm Daniel** (EMSR692, 2023 synoptic-catastrophic) — each built from one per-event YAML over
public-domain inputs (Copernicus DEM, ESA WorldCover, GPM IMERG, ERA5, GloFAS-v4) and validated
pixel-wise against **Copernicus EMS** rapid-mapping flood polygons. Manuscript: *Enhanced-forcing
SFINCS reproduction of three Mediterranean flood archetypes, validated against Copernicus EMS*
(Natural Hazards, in review).

## Repository map
```
skill/                     the sfincs-flood-reproduction pipeline
  scripts/                   16 ordered steps + run_pipeline.py driver + _common.py
  examples/                  6 per-event YAMLs: <event>.yaml (baseline) / <event>_enhanced.yaml
  templates/                 HydroMT build / data-catalog / docs templates
  references/                config_schema, ems_catalog, environment_setup, troubleshooting
  manning_lookup.csv         ESA WorldCover class → Manning n
  machine.local.example.yaml per-machine env/paths override template (copy → machine.local.yaml)
  SKILL.md                   pipeline narrative (NOTE: says "13 steps" — stale; real count is 16)
validation/                EMS validation + audit harness (paper §3, App. B)
  validate_event_v2.py       strict + fuzzy (r∈{0,1,2,3}) + depth-threshold sweep → per-event JSON
  aggregate_metrics_v2.py    cross-event table builder (fuzzy/extended)
  validate_event.py / aggregate_metrics.py   v1 strict-only variants
  deep_audit.py / spatial_audit.py           per-run param/src/mask audit + independent recompute
configs/as_run/            realised HydroMT build + data-catalog files as run (absolute paths;
                           record only — drive reproduction from skill/examples/)
docs/                      AUDIT.md, VALIDATION_FINDINGS.md, CODEBASE_MAP.md, _sources/
environment.yml            conda env spec (pins below)
README.md  CITATION.cff  LICENSE (MIT)
```

## Pinned environment — reproducibility depends on these EXACT versions
Results are **only reproducible** under:
- conda env **`sfincs-viz`** (`conda env create -f environment.yml`)
- **HydroMT 0.10.1**, **HydroMT-SFINCS 1.2.2**, Python 3.11
- **SFINCS binary v2.3.0**, release **`mt_Faber_release_2025.02`** (Deltares freeware; separate download, exe + DLLs co-located)
- mandatory `libblas=*=*openblas` pin (guards a numpy.dot MKL crash on Windows). Verify:
  `python -c "import numpy as np; print(np.dot(np.eye(3),np.eye(3)).sum())"` → must print `3.0`.
- numpy is **unpinned** in environment.yml; the reproduction used numpy 2.4.6. A different numpy may
  shift a headline by ≤0.001 (observed on Strymonas v3: 0.183→0.182). TODO(author): pin numpy.

## How to reproduce
Pipeline = one Python driver consuming one per-event YAML (steps **prep→CN→Q→build→SFINCS**, then validation).
```bash
conda activate sfincs-viz
cp skill/machine.local.example.yaml skill/machine.local.yaml   # then edit env/paths for your machine
python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml --check   # preflight: tools+creds
python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml           # full run (16 steps)
python validation/validate_event_v2.py --config skill/examples/emsr692_pineios_enhanced.yaml         # → per-event JSON
python validation/aggregate_metrics_v2.py                                                            # → cross-event table
```
Baseline = drop `_enhanced`. `--only 7,8,9,10,11` re-runs build+sim from cached downloads.
Credentials: `~/.cdsapirc` (CDS+EWDS, ERA5/GloFAS), `~/.netrc` (NASA Earthdata, IMERG via `earthaccess`).
The IMERG gauge-anchored bias factor is captured in-config (R5 fix): the enhanced YAMLs carry a
`rain_bias_correct` block (target_mm, watershed_bbox, event window) that `run_pipeline.py` applies as
step **06b** via `bias_correct_imerg.py`, between IMERG download and prep — Pineios ×2.725 (400 mm),
Mandra ×8.551 (200 mm), Strymonas disabled. TODO(author): the validators import `_common`/`_anim_common`
from a sibling `.claude/skills/sfincs-flood-reproduction/scripts` path (finding R11), so a clean checkout
of this repo alone does not import — confirm/repoint before release.

## Canonical results (strict, hmax > 0.10 m) — VERIFIED, reproduced from the codebase
| Event (canonical run) | CSI | HR | FAR | B | GSS |
|---|---|---|---|---|---|
| Pineios EMSR692 (v1 enhanced) | **0.456** | **0.947** | 0.532 | 2.02 | 0.201 |
| Strymonas EMSR122 (v3) | **0.183** | **0.328** | 0.706 | 1.11 | 0.136 |
| Mandra EMSR257 (v1 enhanced) | **0.106** | **0.873** | 0.892 | 8.11 | 0.028 |
Pineios peak-threshold CSI = 0.515 @ hmax > 0.50 m. Full record (fuzzy r1, peak, baselines, ablations)
in **docs/AUDIT.md** and the per-event JSON reports.

## Metric definitions
- **strict** = `hmax > 0.10 m` on `(msk > 0) ∩ (union of EMS AOIs)`; `hmax = max_t[zs − zb]⁺`.
- **fuzzy** = **symmetric** r-cell dilation of **both** model and observed fields, r ∈ {0,1,2,3}
  (r=1 ≈ 50 m Mandra / 150 m Strymonas·Pineios). This is the headline fuzzy. The validator also emits
  two **true one-sided** sweeps (V3 fix): model-oriented (dilate OBS only → tolerant FAR) and
  obs-oriented (dilate MODEL only → tolerant HR). Canonical one-sided table: docs/fuzzy_onesided.md.
  Symmetric overstates CSI vs the one-sided decomposition — see docs/AUDIT.md.
- CSI/HR/FAR/B/GSS/F1/F2 per manuscript Eqs (2)–(9).

## Canonical run per event and WHY (selected by the Appendix-B audit, NOT by score)
- **Pineios v1** — the time-varying-GloFAS-Q audit re-run returned identical headline metrics
  (flood is rainfall-dominated), so the original v1 run stands.
- **Strymonas v3** — the Kerkini source-snap fix (zb 171 m upland → 12 m channel) materially changes
  the result (CSI 0.170→0.183, HR 0.210→0.328), so v3 is canonical.
- **Mandra v1** — the audit re-run under a restricted mask left the metrics worse, so the original v1 stands.

## AUDIT GUARDRAILS (do not violate)
1. **Never silently change a value marked verified** in VALIDATION_SUMMARY / docs/AUDIT.md. If a re-run
   differs, **STOP and flag both values + the environment diff** — do not overwrite.
2. **Always distinguish codebase-reproducible from not** (docs/AUDIT.md lists which tables are which —
   Table 11 external benchmarks, Table 13 forecast, Appendices A/B are NOT codebase-verified).
3. **Preserve the Strymonas framing**: enhanced forcing does **NOT** beat baseline on strict CSI
   (ΔCSI = −0.021, ΔHR = −0.049). Its value is **DIAGNOSTIC** (source-snap audit + balanced water
   budget), not a headline gain. The HR/bias recovery is vs the broken **v1**, not vs baseline. Do not
   let edits re-inflate this into a "gain over baseline".
4. **Keep the IMERG bias correction labelled event-calibrated** (Mandra ×8.55, Pineios ×2.73) — a
   **hindcast**, not a blind forecast; skill is conditioned on the observed rainfall total.

## Pointers
- Full audit + changelog + open items → [docs/AUDIT.md](docs/AUDIT.md)
- Ground truth → [docs/_sources/VALIDATION_SUMMARY_for_review.md](docs/_sources/VALIDATION_SUMMARY_for_review.md)
- Manuscript → [docs/_sources/paper_NaturalHazards_submission_CORRECTED.docx](docs/_sources/paper_NaturalHazards_submission_CORRECTED.docx)
- v4→v5 change history → [docs/_sources/RESPONSE_TO_REVIEWS_v5.md](docs/_sources/RESPONSE_TO_REVIEWS_v5.md)
- Reproducibility/correctness findings (R/V/C/D) → [docs/VALIDATION_FINDINGS.md](docs/VALIDATION_FINDINGS.md)
