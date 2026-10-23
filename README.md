# sfincs-mediterranean-flood

A configuration-driven SFINCS / HydroMT-SFINCS pipeline that hindcasts Mediterranean flood events from public global
inputs (Copernicus DEM GLO-30, ESA WorldCover, GPM IMERG, ERA5, GloFAS v4) and scores every hindcast pixel by pixel
against Copernicus Emergency Management Service (EMS) rapid-mapping flood polygons. One YAML file per event and
configuration drives the whole chain: downloads, forcing preparation, HydroMT build, SFINCS run and validation.

## What v1.4.2 is

v1.4.2 is the current release of the pipeline (the "harness") together with the records of every run made with it.

- **Harness.** The v1.4.x releases fix eight defects found in release v1.3.0 (D1–D8: IMERG rate and time label,
  inactive inverse-barometer boundary, spin-up description, coastal set-up, meteo-grid alignment, curve-number sink,
  GloFAS point sampling, source-point resolution). They also add the evaluation mask, which excludes WorldCover class 80
  (permanent water) and open sea from scoring. [CHANGELOG.md](CHANGELOG.md) gives one line per defect: the runs it
  affected, the fix commit and the tests that guard it. Every number of release v1.3.0 is superseded.
- **Events.** Six Copernicus EMS activations:
  - Strymonas (EMSR122, 2015)
  - Mandra (EMSR257, 2017)
  - Emilia-Romagna (EMSR664, 2023)
  - Pineios / Storm Daniel (EMSR692, 2023)
  - Valencia (EMSR773, 2024)
  - Crete (EMSR933, 2026)

  The enhanced configurations are the output of a frozen a-priori activation rule; the rule text is in
  [docs/frozen_rule_R.md](docs/frozen_rule_R.md) and the evidence of its freeze in
  [docs/FREEZE_EVIDENCE.md](docs/FREEZE_EVIDENCE.md). Crete is the first event that happened after the rule was frozen.
  Its configuration was written from the rule before any model run and without reference to the EMS extents; that
  record is in [reproduction/emsr933/](reproduction/emsr933/).
- **Runs of record.** All are scored at h > 0.10 m on the AOI ∩ active cells, minus WorldCover 80 and open sea:

  | event | run |
  |---|---|
  | Pineios | `pineios_enhanced_v142` |
  | Mandra | `mandra_enhanced` |
  | Strymonas | `strymonas_enhanced_postD6_v142` |
  | Valencia | `valencia_enhanced_164_v142` |
  | Emilia-Romagna | `emilia_enhanced_8aoi_v142` |
  | Crete | `crete_canonical_r2on` (Tzermiado tier-1 block) |

  Their numbers are frozen: see the "Number freeze" section, §9 of
  [reproduction/emsr933/rule_ledger.md](reproduction/emsr933/rule_ledger.md), and [docs/AUDIT.md](docs/AUDIT.md).

## Requirements

| Component | Version / source |
|---|---|
| conda env | `sfincs-viz` from [environment.yml](environment.yml) (`conda env create -f environment.yml`) |
| HydroMT / HydroMT-SFINCS | 0.10.1 / 1.2.2 (pinned; results depend on them) |
| SFINCS | v2.3.0, release `mt_Faber_release_2025.02`, Deltares freeware ([download](https://download.deltares.nl/sfincs)), installed separately |
| Credentials | `~/.cdsapirc` for the Copernicus CDS and EWDS (ERA5, GloFAS); `~/.netrc` for NASA Earthdata (IMERG) |

The `libblas=*=*openblas` pin in `environment.yml` is required on Windows. To check it, run
`python -c "import numpy as np; print(np.dot(np.eye(3),np.eye(3)).sum())"`; it must print `3.0`.

## Reproduce one event from its YAML

Each v1.4.x run has its realised configuration in `reproduction/v14_rerun/configs/<run>.yaml`. That file is the event's
example YAML from `skill/examples/`, plus `harness_version: v1.4` and the run's work directory. The steps below use
Mandra (run of record `mandra_enhanced`); for another event, substitute its run name.

1. **Point the configuration at your machine.** Copy `skill/machine.local.example.yaml` to `skill/machine.local.yaml`
   and set the tool paths (python, hydromt, SFINCS executable, GDAL). Alternatively, set the environment variables
   `SFINCS_PYTHON`, `SFINCS_HYDROMT`, `SFINCS_EXE`, `SFINCS_WORK_DIR`, and so on. The committed YAMLs are never edited.
2. **Preflight check:**
   `python skill/scripts/run_pipeline.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --check`
3. **Full pipeline** (downloads, forcing, HydroMT build, SFINCS):
   `python skill/scripts/run_pipeline.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml`
4. **Score with the v1.4 evaluation mask** (committed in `reproduction/v14_rerun/masks/`):
   `python validation/validate_event_v2.py --config reproduction/v14_rerun/configs/mandra_enhanced.yaml --exclusion-tif reproduction/v14_rerun/masks/mandra_exclusion.tif --out-json mandra_enhanced_check.json`
5. **Compare** the output with the record `reproduction/v14_rerun/results/mandra_enhanced_v14_newmask.json`.

Some runs list `overrides`, `inp_patch` or `post_build` hooks in their record (`results/<run>_record.json`). Those
runs were driven by `reproduction/v14_rerun/scripts/phase1.py`, which seeds the work directory from earlier downloads;
its paths are those of the machine the runs were made on. The SFINCS solver is deterministic. Inputs downloaded afresh
can differ from the archived ones where a provider has reprocessed its product; see
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Where the records are

| Path | Content |
|---|---|
| [docs/AUDIT.md](docs/AUDIT.md) | audit trail: defects D1–D8, every re-run block, the number freeze |
| [CHANGELOG.md](CHANGELOG.md) | releases, one line per defect |
| [reproduction/v14_rerun/](reproduction/v14_rerun/) | the v1.4.x re-runs: `configs/` (realised YAMLs), `results/` (validation JSON and run records), `masks/` (evaluation exclusion masks), `phase4/` and `phase5/` (diagnostics, Crete tiers), `code14/`–`code16/`, the checkpoints, and `NUMBER_MAP.md` (every number, release v1.3.0 against v1.4.x) |
| [reproduction/v14_harness/](reproduction/v14_harness/) | checks made while the v1.4 harness was written |
| [reproduction/emsr933/](reproduction/emsr933/) | Crete: rule ledger, EMS snapshots, truth freeze, timing log |
| [reproduction/r6/](reproduction/r6/) | tables, figures and reference list generated from the records (`TABLES_MANIFEST.md`, `FIGURES_MANIFEST.md`) |
| [reports/](reports/) | release-v1.3.0 per-event metric JSONs (superseded; kept as released) |
| [configs/as_run/](configs/as_run/) | release-v1.3.0 build records (absolute paths; record only) |
| [tests/](tests/) | unit and regression tests: `python -m unittest discover -s tests` |

## Repository layout

```
skill/          the pipeline: scripts/ (driver run_pipeline.py and its steps), examples/ (one YAML per event and
                configuration), templates/, references/, manning_lookup.csv, machine.local.example.yaml
validation/     contingency validators (strict and fuzzy), evaluation-mask builder, cross-event aggregators
reproduction/   run records (see above)
docs/           audit trail, frozen rule and freeze evidence, reproducibility and validation notes
environment.yml conda environment
```

## Citation and licence

MIT, see [LICENSE](LICENSE). To cite the software, use [CITATION.cff](CITATION.cff). All versions are archived on
Zenodo under the concept DOI [10.5281/zenodo.20523154](https://doi.org/10.5281/zenodo.20523154).
