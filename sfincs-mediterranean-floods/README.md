# SFINCS flood reproduction — three Mediterranean archetypes

Reproduction code, configurations and validation harness for the manuscript:

> **Enhanced-forcing SFINCS reproduction of three Mediterranean flood
> archetypes, validated against Copernicus EMS.** *(submitted to* Natural Hazards*).*

This repository reproduces **every numerical result in the manuscript from
public-domain inputs**. It contains the end-to-end `sfincs-flood-reproduction`
pipeline (forcing + topography + land-use + Copernicus EMS download →
HydroMT-SFINCS build → SFINCS run → QC figure + animation + deliverable
bundle), the per-event YAML configurations, the strict and fuzzy
contingency validators, the cross-event aggregators, and the deep
input-audit diagnostics described in Appendix B of the paper.

The pipeline is **rain-on-grid** with optional enhanced-forcing terms
(gauge-anchored IMERG bias correction, ERA5 wind/MSLP, inverse-barometer
coastal boundary, SCS curve-number infiltration, and GloFAS-v4 upstream
discharge), each activated per event through the YAML config.

---

## Repository layout

```
sfincs-mediterranean-floods/
├── skill/                     # the sfincs-flood-reproduction pipeline
│   ├── SKILL.md               #   pipeline overview and step-by-step guide
│   ├── scripts/               #   16 ordered steps + run_pipeline.py driver
│   ├── examples/              #   per-event YAML configs (baseline + enhanced)
│   ├── templates/             #   HydroMT build / data-catalog / docs templates
│   ├── references/            #   config schema, EMS catalogue, env setup, troubleshooting
│   └── manning_lookup.csv     #   ESA WorldCover class → Manning n
├── validation/                # EMS validation + audit harness (paper §3, App. B)
│   ├── validate_event.py      #   strict pixel-wise CSI/HR/FAR/B → per-event JSON
│   ├── validate_event_v2.py   #   strict + fuzzy (r∈{0,1,2,3}) + depth-threshold sweep
│   ├── aggregate_metrics.py   #   cross-event table builder
│   ├── aggregate_metrics_v2.py#   cross-event table builder (fuzzy/extended)
│   ├── deep_audit.py          #   per-run parameter / src / mask / EMS-CRS audit
│   └── spatial_audit.py       #   hmax recompute + EMS rasterisation + contingency
└── configs/as_run/            # exact HydroMT build + data-catalog files as run
    ├── mandra_sfincs{,_enhanced}/
    ├── emsr122_sfincs{,_enhanced}/     # Strymonas
    ├── pineios_sfincs{,_enhanced}/     # Storm Daniel
    └── strymonas_forecast{,_v2}/       # prospective ECMWF demonstration
```

> **Note on `configs/as_run/`.** These are the realised HydroMT files from the
> machine the paper was produced on, so the `data_catalog.yml` paths are
> absolute and machine-specific. They are provided as an exact record of what
> was run. For a clean reproduction, drive the pipeline from `skill/examples/`
> — `prep_inputs.py` regenerates a local `data_catalog.yml` for your machine.

---

## Requirements

| Component | Version / source |
|---|---|
| SFINCS binary | v2.3.0, release `mt_Faber_release_2025.02` — [Deltares freeware](https://download.deltares.nl/sfincs) |
| HydroMT / HydroMT-SFINCS | v0.10.1 / v1.2.2 (conda-forge) |
| Python | 3.11 (conda-forge) |
| Other deps | xarray, rasterio, pyogrio, shapely, geopandas, cdsapi, earthaccess, PyYAML, matplotlib, imageio-ffmpeg |

Create the environment:

```bash
conda env create -f environment.yml      # creates the `sfincs-viz` env
conda activate sfincs-viz
```

Then download the SFINCS binary from Deltares and note its path; set the tool
paths either via the `env:` block in your event YAML or with the
`--python` flag to `run_pipeline.py` (see `skill/references/environment_setup.md`).

### Credentials (free accounts, read from your home directory)

| Input | Account | Credential file |
|---|---|---|
| ERA5 hourly single-levels | [Copernicus CDS](https://cds.climate.copernicus.eu) | `~/.cdsapirc` |
| GloFAS-v4 reanalysis | [Copernicus EWDS](https://ewds.climate.copernicus.eu) | `~/.cdsapirc` (same key) |
| GPM IMERG Final V07 | [NASA Earthdata](https://urs.earthdata.nasa.gov) | `earthaccess` login (`~/.netrc`) |
| Copernicus DEM GLO-30 | AWS Open Data | none |
| ESA WorldCover v200 | AWS Open Data | none |
| Copernicus EMS polygons | Copernicus EMS (public) | none |

A GloFAS [Open-Meteo](https://open-meteo.com) fallback (`download_glofas_openmeteo.py`,
no account) is used for the Pineios run.

---

## Quick start — reproduce one event

Each event is driven by a single YAML config. The driver sequences all 16
steps with resumable, script-level caching:

```bash
# Flagship: Storm Daniel / Pineios (EMSR692), enhanced forcing
python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml

# Strymonas transboundary flood (EMSR122), enhanced forcing
python skill/scripts/run_pipeline.py --config skill/examples/emsr122_strymonas_enhanced.yaml

# Mandra convective flash flood (EMSR257), enhanced forcing
python skill/scripts/run_pipeline.py --config skill/examples/emsr257_mandra_enhanced.yaml
```

Re-run a subset of steps (e.g. only re-build + re-run + re-validate after a
config edit):

```bash
python skill/scripts/run_pipeline.py --config <event>.yaml --only 10,11,13
```

Replace `_enhanced` with the baseline config (e.g. `emsr692_pineios.yaml`) to
reproduce the baseline ERA5 rain-on-grid run that each enhanced result is
compared against.

A full run downloads ~0.5–1 GB per event and completes in ~10 min per event
on a 16-thread CPU once the inputs are cached.

---

## Validation and cross-event tables

After a run, the model directory holds `sfincs_map.nc`. Reproduce the
pixel-wise contingency metrics (active-mask ∩ EMS AOI union, `hmax > 0.10` m):

```bash
# strict + fuzzy (r=0..3) + depth-threshold sweep -> per-event JSON report
python validation/validate_event_v2.py --config skill/examples/emsr692_pineios_enhanced.yaml

# build the cross-event summary tables from the per-event JSON reports
python validation/aggregate_metrics_v2.py
```

The deep input audit of Appendix B (boundary masks, Manning lookup,
curve-number raster, upstream-Q src coordinates/series, EMS CRS) and the
v1↔v3 src-correction re-run are reproduced with:

```bash
python validation/deep_audit.py
python validation/spatial_audit.py
```

### Headline results (enhanced forcing, `hmax > 0.10` m vs Copernicus EMS)

| Event | CSI | HR | Notes |
|---|---|---|---|
| Pineios / Storm Daniel (EMSR692) | **0.456** | **0.947** | peak-threshold CSI 0.515; B = 2.0; GSS = 0.20 |
| Strymonas (EMSR122, v3 src fix) | 0.183 | 0.328 | 02BALTOTOPI recovered from 0 → HR 0.432; B = 1.11 |
| Mandra (EMSR257) | 0.106 | 0.873 | fuzzy r=2: CSI 0.205, HR 0.986; B = 8.1 (over-prediction) |

See the manuscript for the full per-AOI tables, strict-vs-fuzzy contingency,
and the calibration-status disclosures (e.g. the event-window IMERG
bias-correction factors).

---

## Citing this work

If you use this code, please cite the manuscript (see `CITATION.cff`). The
repository is released under the MIT licence (`LICENSE`) and is archived at
Zenodo (DOI assigned on first stable release).

## Acknowledgements

This work was supported by ECHO under Grant Agreement No. 101225575
(Horizon Europe lump sum). SFINCS is developed by Deltares; HydroMT-SFINCS
by Deltares and contributors. Input data are provided by the Copernicus
Climate Data Store, Copernicus EMS, NASA GES-DISC, and the ESA/AWS Open Data
programmes.
