# Review archive — SFINCS hindcasts of six Mediterranean flood events, release v1.4.2

This archive is an anonymised copy, for peer review, of the code and records behind the manuscript. Its base is the
repository tree at release v1.4.2 (no version-control metadata), with the current versions of the per-event
configurations, the Crete rule ledger, the validation records behind every table, the table and figure scripts, the
tables and figures themselves, the audit trail and the release notes copied on top. Start with `README.md` (what
v1.4.2 is, the runs of record, how to reproduce one event) and `CHANGELOG.md` (defects D1–D9 of the earlier release,
the runs each affected, the fix commit and the tests that guard it).

## Contents

| Path | What it holds |
|---|---|
| `skill/` | the pipeline: `scripts/run_pipeline.py` and its 16 steps, one YAML per event and configuration in `examples/`, templates, the Manning lookup |
| `validation/` | the strict and fuzzy contingency validators, the evaluation-mask builder, the cross-event aggregators |
| `reproduction/v14_rerun/` | every v1.4.x run: realised configurations (`configs/`), validation JSON and run records (`results/`), the evaluation exclusion masks (`masks/`), diagnostics (`phase4/`, `phase5/`), the defect records (`code14/`–`code17/`), `NUMBER_MAP.md` |
| `reproduction/emsr933/` | the Crete prospective run: EMS snapshots, rule ledger, truth freeze, timing log |
| `reproduction/r6/` | manuscript tables (`tables/`, `TABLES_MANIFEST.md`), figures (`figures/`, `FIGURES_MANIFEST.md`), reference list (`refs.bib`, `refs_datacite.bib`) and the generating scripts |
| `docs/` | `AUDIT.md` (audit trail), the frozen activation rule and its freeze evidence, reproducibility and validation notes |
| `configs/as_run/`, `reports/` | release-v1.3.0 build records and metric files (superseded; kept as released) |
| `tests/` | unit and regression tests (`python -m unittest discover -s tests`) |

Not in the archive: the model outputs (`sfincs_map.nc`, tens of GB), the downloaded inputs, the NOA/meteo.gr station
files (licence), credentials, caches, the author metadata file and the authors' anonymity-check tooling.

## Environment

- conda environment from `environment.yml` (`conda env create -f environment.yml`): HydroMT 0.10.1, HydroMT-SFINCS 1.2.2,
  rasterio, pyogrio, xarray, with the OpenBLAS pin (`libblas=*=*openblas`, required on Windows);
- the SFINCS executable v2.3.0, release `mt_Faber_release_2025.02` (Deltares freeware, a separate download);
- credentials for two input services: a `~/.cdsapirc` for the Copernicus Climate Data Store (ERA5; the same key serves the
  Early Warning Data Store for GloFAS) and a `~/.netrc` entry for NASA Earthdata (IMERG). The Copernicus DEM, ESA
  WorldCover and the EMS flood packages are downloaded without credentials.

Verify the environment with `python -c "import numpy as np; print(np.dot(np.eye(3),np.eye(3)).sum())"` (must print `3.0`).

## Rebuild and score one event from the archive: Mandra, run of record `mandra_enhanced`

1. Point the pipeline at your machine. Copy `skill/machine.local.example.yaml` to `skill/machine.local.yaml` and set the tool
   paths (python, hydromt, SFINCS executable, GDAL); or set `SFINCS_PYTHON`, `SFINCS_HYDROMT`, `SFINCS_EXE`,
   `SFINCS_WORK_DIR`. The committed YAMLs are never edited; the paths recorded in them are provenance.
2. Preflight check (tools, credentials, import paths):

       python skill/scripts/run_pipeline.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --check

3. Download the inputs (steps 01–06 of the pipeline; GloFAS, step 03, exits at once because Mandra injects no upstream
   discharge):

       python skill/scripts/run_pipeline.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --only 1,2,3,4,5,6

   This fetches the EMS packages of EMSR257 (01), ERA5 wind, pressure and rain (02, CDS), the Copernicus DEM GLO-30
   tiles (04, AWS Open Data), ESA WorldCover 2021 (05) and GPM IMERG Final V07 half-hourly files (06, Earthdata).
4. Prepare the forcing and build and run the model (steps 07–11: input preparation with the R2 bias correction, the
   curve-number raster, discharge points, the HydroMT build with the v1.4 coastal set-up and grid alignment, SFINCS):

       python skill/scripts/run_pipeline.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --only 7,8,9,10,11

5. Score the result on the v1.4 evaluation universe (AOI ∩ active cells minus permanent water and open sea, the mask
   committed in `reproduction/v14_rerun/masks/`):

       python validation/validate_event_v2.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --exclusion-tif reproduction/v14_rerun/masks/mandra_exclusion.tif --out-json mandra_enhanced_check.json

6. Compare `mandra_enhanced_check.json` with the record `reproduction/v14_rerun/results/mandra_enhanced_v14_newmask.json`
   (strict contingency at h_max > 0.10 m: `validation.strict_threshold_sweep["h>0.10m"]`). The SFINCS solver is
   deterministic; inputs downloaded afresh can differ from the archived ones where a provider has reprocessed a product
   (`docs/REPRODUCIBILITY.md`).

The other runs of record (`pineios_enhanced_v142`, `strymonas_enhanced_postD6_v142`, `valencia_enhanced_164_v142`,
`emilia_enhanced_8aoi_v142`, `crete_canonical_r2on`) follow the same steps with their configuration file; Pineios,
Strymonas, Valencia and Emilia-Romagna also download GloFAS v4 discharge (step 03, EWDS). Recorded wall-clock times of
every run are in `reproduction/emsr933/timing.md`.

## Checking the recorded numbers without running the model

- `reproduction/r6/tables/` (T2–T6, S1–S10): every cell is read from a record listed in `reproduction/r6/TABLES_MANIFEST.md`;
  `python -I reproduction/r6/scripts/r6_tables.py --repo .` regenerates them (Table S4 also needs the earlier manuscript's
  supplement text, which is not in the archive; that table is kept as generated).
- `reproduction/v14_rerun/NUMBER_MAP.md`: every number of the earlier release set against v1.4.x.
- `docs/AUDIT.md`: the audit trail of the defects and of every re-run block.
- `python -m unittest discover -s tests`: tests that need the executables or the model outputs skip themselves when those
  are absent.

## What was changed for anonymity

| Placeholder | Replaces |
|---|---|
| `[author]` | author names, initials and account names |
| `[institution]` | the affiliation |
| `[e-mail withheld]`, `[ORCID withheld]` | the authors' contact details |
| `[repository withheld for review]` | the public repository address |
| `[DOI withheld for review]` | the authors' archive identifiers |
| `[grant withheld]`, `[funder withheld]` | the funding statement |

Absolute as-run paths were made relative to the project root (`implementation/<run>/...`, `<conda>/...`, `~/...`); they
describe where the runs were made and are not inputs. The licence holder reads "Anonymous authors (review copy)". The
bibliographic records of the cited works (`refs.bib`, `refs_datacite.bib`) were left as the registries returned them.
Nothing else was changed, and every number is as recorded.
