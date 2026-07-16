# sfincs-mediterranean-floods

Reproduction code, per-event configurations and validation harness for the manuscript:

> **A configuration-driven enhanced-forcing framework for reduced-complexity flood-inundation
> modelling: cross-scale SFINCS evaluation under a frozen a-priori rule across five Mediterranean
> events.** 

A single **SFINCS** instance, built from one YAML per event over public-domain inputs (Copernicus
DEM, ESA WorldCover, GPM IMERG, ERA5, GloFAS-v4), is evaluated under a **frozen a-priori activation
rule** that maps catchment and event properties to a configuration *before any run is scored*. The
rule is established on three Greek development events — **Mandra** (EMSR257, 2017), **Strymonas**
(EMSR122, 2015) and **Pineios / Storm Daniel** (EMSR692, 2023), spanning **three orders of magnitude**
in catchment area — and applied **blind** to two non-Greek held-out events, the **2024 Valencia
DANA** (EMSR773) and the **2023 Emilia-Romagna flood** (EMSR664). Every reproduction is validated
pixel-wise against **Copernicus EMS** rapid-mapping flood polygons; the repo reproduces every
numerical result in the manuscript from public inputs.

**Headline results.**
- *Flagship* — the Storm-Daniel / Pineios catastrophe reproduces at **CSI = 0.456, HR = 0.947**
  (peak-threshold CSI 0.515) over a 4642 km² mask — the upper range of continental-scale benchmarks.
  Strymonas v3 = 0.183 / 0.328; Mandra = 0.106 / 0.873.
- *Held-out (blind frozen rule)* — Emilia-Romagna **CSI = 0.185** (≈ Strymonas, same multi-catchment
  archetype); Valencia **CSI = 0.082, HR = 0.996** (≈ Mandra, over-prediction-limited).
- *Bias-insensitive skill* — Valencia's **SEDI = 0.625** sits beside the flagship Pineios (0.636):
  the frozen rule locates the extreme flood correctly out of sample, so the low strict CSI is a
  metric artefact of over-prediction, not a skill deficit.

## Repository layout
```
skill/          the sfincs-flood-reproduction pipeline (scripts/ driver + 16 steps, examples/ YAMLs,
                templates/, references/, manning_lookup.csv)
validation/     strict + fuzzy contingency validators, cross-event aggregators, audit diagnostics
configs/as_run/ realised HydroMT build + data-catalog files as run (record only; absolute paths)
environment.yml conda env spec
```

## Requirements
| Component | Version / source |
|---|---|
| conda env | `sfincs-viz` (`conda env create -f environment.yml`) |
| HydroMT / HydroMT-SFINCS | **0.10.1 / 1.2.2** (pinned; results depend on these) |
| SFINCS binary | **v2.3.0**, release `mt_Faber_release_2025.02` — [Deltares freeware](https://download.deltares.nl/sfincs) (separate download) |
| Credentials | `~/.cdsapirc` (CDS + EWDS: ERA5/GloFAS), `~/.netrc` (NASA Earthdata: IMERG) |

The `libblas=*=*openblas` pin is mandatory (guards a numpy.dot crash on Windows). Verify:
`python -c "import numpy as np; print(np.dot(np.eye(3),np.eye(3)).sum())"` → must print `3.0`.

## Quickstart
```bash
conda activate sfincs-viz
cp skill/machine.local.example.yaml skill/machine.local.yaml      # edit env/paths for your machine
python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml --check   # preflight
python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml           # full pipeline
python validation/validate_event_v2.py --config skill/examples/emsr692_pineios_enhanced.yaml         # → per-event JSON
python validation/aggregate_metrics_v2.py                                                            # → cross-event table
```
Baseline = drop `_enhanced`. The `configs/as_run/` files carry absolute author-machine paths and are a
record only — drive reproduction from `skill/examples/`.

## Data & code availability
- **GitHub:** https://github.com/vaspapa79/sfincs-mediterranean-flood
- **Zenodo:** https://doi.org/10.5281/zenodo.20523154
- Licence: **MIT** (see [LICENSE](LICENSE)). Cite via [CITATION.cff](CITATION.cff).
