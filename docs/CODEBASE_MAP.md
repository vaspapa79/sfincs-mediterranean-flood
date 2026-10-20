# CODEBASE_MAP — sfincs-mediterranean-floods

A reading map of the repo: what each part does, how data flows, and where the entry points are.
Companion to `VALIDATION_FINDINGS.md`. Produced from a read-only Phase-0 review (2026-06-12).

## What this repo is
Reproduction code + configs + validation harness for the manuscript *"Enhanced-forcing SFINCS
reproduction of three Mediterranean flood archetypes, validated against Copernicus EMS"*
(→ *Natural Hazards*). Three events, each with a **baseline** (ERA5 rain-on-grid) and an
**enhanced** (added forcing) run, validated pixel-wise against Copernicus EMS flood polygons.

| Event | EMS | Archetype | Grid | Enhanced forcing used |
|---|---|---|---|---|
| Pineios / Storm Daniel | EMSR692 | large fluvial | 150 m | IMERG(bias-corr) + wind/MSLP + inverse-barometer + GloFAS-Q (4 pts) |
| Strymonas | EMSR122 | transboundary fluvial | 150 m | + SCS curve-number infiltration + GloFAS-Q (2 pts); **headline = v3 src-fix** |
| Mandra | EMSR257 | convective flash | 50 m | IMERG + wind/MSLP + inverse-barometer (no CN, no GloFAS) |

## Top-level layout
```
sfincs-mediterranean-floods/
├── skill/                 # the reproduction pipeline (entry point)
│   ├── SKILL.md           #   step guide (NOTE: stale — see D1 in FINDINGS)
│   ├── scripts/           #   16 ordered steps + run_pipeline.py driver + _common.py, _anim_common.py
│   ├── examples/          #   per-event YAML configs (baseline + _enhanced)
│   ├── templates/         #   $-placeholder HydroMT build / data-catalog / docs templates
│   ├── references/        #   config_schema, ems_catalog, environment_setup, troubleshooting
│   └── manning_lookup.csv #   ESA WorldCover class → Manning n (the portable, bundled copy)
├── validation/            # EMS contingency metrics + audits (paper §3, App. B)
├── configs/as_run/        # frozen rendered build/catalog files from the author machine
│                          #   (absolute paths — RECORD ONLY, not runnable; see R1/R6)
├── environment.yml        # conda env `sfincs-viz` (note the libblas=*=*openblas pin)
├── README.md  CITATION.cff  LICENSE (MIT)  .gitignore
└── docs/                  # this review (VALIDATION_FINDINGS.md, CODEBASE_MAP.md)
```
Heavy/binary inputs (DEM/WorldCover GeoTIFFs, ERA5/GloFAS/IMERG netCDFs, `model/`, `deliverable*/`,
SFINCS exe+DLLs) are **git-ignored and regenerated** — not committed.

## The pipeline (`skill/scripts/`)
**Entry point:** `run_pipeline.py --config skill/examples/<event>[_enhanced].yaml` — sequences all
steps as `subprocess.run([python, step, --config cfg])`, fail-fast on first non-zero. Manual resume via
`--only 10,11,13` / `--skip 5,6`. Per-script caching = each step self-skips if its output already exists.
**Config hub:** `_common.py` (`EventCfg`: time window, bbox, tile lists, paths, and all optional
enhanced-forcing blocks). **Viz helpers:** `_anim_common.py` (`open_sfincs`, per-frame stats, polygon loaders).

DAG (order 01→16):
```
download_ems(01) ───────────────────────────────────────────────┐
download_era5(02) ─► prep_inputs(07) ─┐                          │
download_glofas(03)─►(clean)──────────►├─► build_model(10) ─► run_sfincs(11) ─► fetch_basemap(12)
download_dem(04) ─► copdem30.vrt ─────┤      ▲                                        │
download_worldcover(05)► wc.vrt ─┬────┘      │                          ┌─────────────┼─────────────┐
                                 └► prep_cn_raster(08) ─► cn.tif ───────┤        qc_alignment(13)    │
download_imerg(06) ─► imerg.nc ──────────────►(rain) ─┘                make_animation(14)  make_mp4(15)
prep_q_at_outlets(09) ─► q_outlet.csv ─► build_model(10, inject src/dis)              package_deliverable(16)
```
- 01 EMS polygons (S3 or rapidmapping API) · 02 ERA5 (CDS) · 03 GloFAS (EWDS) or `download_glofas_openmeteo.py`
  (no-auth fallback) · 04 CopDEM30 +VRT · 05 ESA WorldCover +VRT · 06 IMERG (only if `rain_source: imerg_half_hourly`)
  · `bias_correct_imerg.py` (aux, gauge-anchored `--target-mm`) · 07 clean ERA5/GloFAS + write `data_catalog.yml`
  · 08 SCS-CN raster (if `infiltration.enabled`) · 09 sample GloFAS at src (if `upstream_q.enabled`)
  · 10 render `sfincs_build.yml` + `hydromt build` + inject Q · 11 run SFINCS → `sfincs_map.nc`
  · 12 basemap · 13 QC PNG · 14 HTML animation · 15 MP4 · 16 deliverable zips.

## Configs (`skill/examples/` vs `configs/as_run/`)
- **examples/** = human-authored, the intended reproduction inputs. Baseline `<event>.yaml` = ERA5
  rain-on-grid; `<event>_enhanced.yaml` toggles forcing blocks: `rain_source`, `wind_pressure.enabled`,
  `coastal_bc.enabled`(+`pavbnd:1`), `infiltration.enabled` (Strymonas only), `upstream_q.enabled`
  (Pineios/Strymonas). Shared: `crs.epsg 32634`, `grid` (res 150 m; 50 m Mandra; subgrid 4), `window`.
- **templates/** = `string.Template` files rendered per-machine by `prep_inputs.py`/`build_model.py`.
- **configs/as_run/** = the realised, rendered files from the paper machine — **frozen records with
  absolute `C:/Users/vaspapa/…` paths; not runnable as-is** (drive reproduction from `examples/`).
  ⚠ `emsr122_sfincs_v3` (the Strymonas headline) is **absent** here — see R2.

## Validation harness (`validation/`)
| Script | Role | Output |
|---|---|---|
| `validate_event.py` (v1) | strict contingency at h>{0.05,0.10,0.25,0.50} m, universe = active-mask ∩ AOI-union; CSI/HR/FAR/F1/ACC; forcing+run sanity; optional baseline delta | `<slug>_metrics.json/.md` |
| `validate_event_v2.py` | strict + fuzzy r∈{0,1,2,3} + best-CSI threshold + per-AOI; adds B, GSS, F2, HSS | `<slug>_metrics_v2.json` |
| `aggregate_metrics.py` (v1) | cross-event table from v1 JSON | `cross_event_metrics.{json,md,tex}` |
| `aggregate_metrics_v2.py` | **headline cross-event table** (source of the README numbers) | `cross_event_metrics_v2.{json,tex,md}` |
| `deep_audit.py` | per-run input dump (inp, manning, cn, src/dis, msk, EMS CRS) | stdout/report |
| `spatial_audit.py` | independent hmax + EMS rasterise + contingency recompute | report |

Metric formulas were checked and are **mathematically correct** (CSI=TP/(TP+FP+FN); HR=TP/(TP+FN);
FAR=FP/(TP+FP); B=(TP+FP)/(TP+FN); GSS/ETS; F1/F2/HSS). The reproducibility risk is **not** the
formulas but: the y-orientation flip assumption (V1), NaN propagation in the v2 aggregator (V2), the
mislabeled both-sided "asymmetric" fuzzy (V3), and hardcoded paths in the audit scripts (R1).

## How to reproduce (intended, once portability fixed)
1. `conda env create -f environment.yml` (gives `sfincs-viz`, applies the OpenBLAS pin) → activate.
2. Download the SFINCS binary (Deltares, tag `v2.3.0 mt_Faber_release_2025.02`); set its path in the
   YAML `env:` block. Provide credentials: `~/.cdsapirc` (CDS + EWDS), Earthdata `~/.netrc`.
3. `python skill/scripts/run_pipeline.py --config skill/examples/emsr692_pineios_enhanced.yaml`
   (repeat for `emsr122_strymonas_enhanced`, `emsr257_mandra_enhanced`; drop `_enhanced` for baselines).
4. `python validation/validate_event_v2.py --config <event>.yaml` then `python validation/aggregate_metrics_v2.py`.
> On the new machine, apply R1–R10 from `VALIDATION_FINDINGS.md` first, or the run halts on hardcoded paths.

## Related, outside the repo (in `D:\ELKAK\`)
`implementation/` (the original working runs incl. real `sfincs_map.nc` outputs — useful to verify V1),
`deliverable_*` (per-event output bundles), `paper_v2` / `paper_submission_v2..v5` (manuscript; **v5 is
the live submission**), `documents/emsr692/{methodology,reproducibility}.md` (older notes; see D2/R1).
