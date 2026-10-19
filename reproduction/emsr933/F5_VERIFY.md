# F5_VERIFY — state of the v1.3.0 harness that EMSR933 would inherit (facts only)

> **Correction (CODE-13, 2026-10-19, after Checkpoint 2 review).** Defect D1 affects the **IMERG path only**.
> The hourly ERA5 path reported in (c) below (×1.0, −60 min) is the *correct* conversion, not a defect: ECMWF
> documents ERA5 `tp` as the accumulation over the hour **ending** at the validity time, and SFINCS holds each
> rate from its stamp forward (`amprblock = 1`), so hydromt's `time_label='right'` relabelling puts the hour on
> its physical interval. The ERA5 baselines were therefore **not** affected by D1; harness v1.4 keeps
> `cumulative_input=True, time_label=right` for ERA5 and writes IMERG with `cumulative_input=False,
> time_label=left` (see `reproduction/v14_harness/PAVBND_SOURCE.md` §5 and `tests/test_precip_forcing_v14.py`).

Requested at Checkpoint 0 (decision 5). Four independent read-only analyses, each with a reproducible
script and a JSON holding every number: `f5/F5_abc.{md,json}` (`f5_abc_synthetic.py`), `f5/F5_d.*`
(`f5_d_volume.py`), `f5/F5_e.*` (`f5_e_ib.py`), `f5/F5_f.*` (`f5_f_spinup.py`). Environment: conda
`sfincs-viz`, hydromt 0.10.1, hydromt_sfincs 1.2.2, xarray 2026.4.0. No model was re-run; nothing under
`implementation/` or `ELKAK2/` was modified. Every number below is copied from those files. Options
(a)/(b)/(c) at the end are listed, not ranked — the decision is Papaioannou's.

## (a) Where IMERG enters with `cumulative_input=True`, and what the flag means
Code path (worktree = v1.3.0 + F2/F4; line numbers as recorded in `F5_abc.json`):
1. `skill/scripts/build_model.py:111-134` renders `skill/templates/sfincs_build.yml.tmpl` with
   `rain_dataset = cfg.rain_source`; `:152-158` runs `hydromt build sfincs <model> -i sfincs_build.yml -d data_catalog.yml --fo -vv`.
2. `skill/templates/sfincs_build.yml.tmpl:49-51` — `setup_precip_forcing_from_grid: / precip: $rain_dataset / aggregate: false`;
   **no `cumulative_input` or `time_label` key**, so the method defaults apply.
3. `hydromt/cli/main.py:169→224` → `hydromt/models/model_api.py:190,246,166-188` (`_run_log_method` logs every parameter,
   incl. defaults — the as-run `hydromt.log` of every event records `setup_precip_forcing_from_grid.cumulative_input: True`,
   `time_label: right`).
4. `hydromt_sfincs/sfincs.py:2306-2427` `SfincsModel.setup_precip_forcing_from_grid(self, precip, dst_res=None,
   cumulative_input=True, time_label="right", aggregate=False)`: `:2382` `time_interval = da_to_timedelta(precip)`
   (mean stamp spacing, `hydromt/workflows/forcing.py:778-780`); `:2393-2399` `if cumulative_input: precip = precip /
   (time_interval/3600)`; `if time_label == "right": precip = precip.shift(time=-1, fill_value=0)`;
   `:2416-2427` reproject (nearest) and `set_forcing`; written by `write_forcing` (`:3365-3469`) as `precip_2d.nc`,
   variable `Precipitation`, `minutes since <tref>`.
   Docstring (installed 1.2.2, verbatim): *cumulative_input* — "Option to indicate whether the input precipitation is
   cumulative in mm (True, default) or a precipitation rate in mm/hr (False). When cumulative, the data is converted
   to mm/hr by dividing by the time interval of the input dataset." *time_label* — "Label to prescribe whether the
   accumulation period of the precipitation is starting (left) or ending (right) at the validity date and time. This
   is only relevant if cumulative_input=True." Summary (`:2317-2318`): "SFINCS requires the mean precipitation rate in
   mm/hr over the upcoming interval. It will use the rate at the start of this interval and keep it constant throughout."
5. IMERG writer `skill/scripts/download_imerg.py`: the granule `time` coordinate is passed through unchanged and is the
   **start** of the 30-min window (HDF5 `time_bnds` [00:00, 00:30]); `units = "mm/h"` (IMERG native `mm/hr`).
   `bias_correct_imerg.py:100-110` treats the values as rates (Σ rate · 0.5 h). ERA5: `prep_inputs.py:46-49` `tp×1000`
   labelled `mm/h`, hourly stamps (`GRIB_stepType = accum`).
Consequence of 4+5 for the half-hourly rate field: value ÷ 0.5 h (×2) and one-stamp shift (−30 min); for hourly
input: value ÷ 1 h (×1) and −60 min.

## (b) Synthetic test through the same method (`f5_abc_synthetic.py`, 5×5 cells, 1 km, EPSG:32634)
| case | input | kwargs | written `Precipitation` at the input stamps | total (Σ rate·Δt) | factor / offset |
|---|---|---|---|---|---|
| (b) half-hourly, DataArray | 00:00, 00:30, 01:00, 01:30 @ 10 mm/h (= 20 mm) | defaults | 20, 20, 20, 0 mm/h | 30.0 mm (25.0 trapezoid) | out(i) = 2·in(i+1): **×2.0, −30 min** |
| (b) via netCDF + data-catalog entry | same | defaults | 20, 20, 20, 0 | 30.0 | same |
| (b) via `hydromt build sfincs` CLI (template form) | same | template | 20, 20, 20, 0 | 30.0 | `identical_to_dataarray_case = true` |
| half-hourly pulse (10 mm/h only at 01:00 = 5 mm) | 8 stamps | defaults | 20 at 00:30, else 0 | 10.0 mm | **×2.0, −30 min** |
| half-hourly, `cumulative_input=False, time_label="left"` | as (b) | | 10, 10, 10, 10 | 20.0 mm | ×1.0, 0 min (pulse: 5.0 mm, ×1.0, 0 min) |
Expected for a correct pass-through of (b): 20 mm, no offset. The uniform rows also carry the end-of-series effect of
`shift(time=-1, fill_value=0)` (last stamp → 0); the pulse rows isolate factor and offset.

## (c) Same check on the hourly (ERA5-type) path
| hourly 00:00, 01:00 @ 10 mm/h (= 20 mm) | defaults | 10, 0 | 10.0 mm | magnitude **×1.0**, **−60 min** (pulse: ×1.0 at −60 min) |
|---|---|---|---|---|
Magnitude factor 1.0 for hourly input. The −60 min shift moves the value to the stamp before it; ECMWF documents ERA5
hourly `tp` at validity time T as the accumulation over the hour ending at T, under which convention the shift places
the rate on the interval it belongs to — this convention was not re-verified from the files here (only `GRIB_stepType =
accum` is recorded in `era5_<slug>.nc`).

## (d) Rainfall depth actually written to the as-run models (`F5_d.md`; mm, spatial means; Σ rate·0.5 h)
| run (folder) | window / region | written `precip_2d.nc` | IMERG bias-corr. | IMERG raw | written ÷ intended |
|---|---|---|---|---|---|
| Pineios enh. (`model_author_ref`) | 04–08 Sep 2023, bbox 22.0/39.4/22.95/40.0 | **783.12** | 398.27 | 146.18 | **1.958** vs 400 mm; **2.061** vs 380 mm |
| Pineios enh. | same window, all forcing cells | 746.90 | 376.40 | 138.15 | written/IMERG-bc 1.984 |
| Mandra enh. (`model_author_ref`) | 14–16 Nov 2017, bbox 23.40/38.05/23.55/38.15 | **447.74** (1 forcing cell) | 200.00 (4 cells) | 23.39 | **2.239** vs 200 mm (grid-rectangle ratio written/IMERG-bc 2.009) |
| Valencia 350-mm as-run (`runs/.../model`) | 29–30 Oct 2024, bbox −0.75/39.33/−0.30/39.55 | **677.50** | 350.00 | 84.48 | **1.936** vs 350 mm; 4.131 vs 164 mm |
| Valencia 164-mm re-run (`rerun_v164/model`) | same | **317.46** | (350-run frames × 0.4686) | 84.48 | **1.936** vs 164 mm |
Pointwise identity `written(t) = 2 × IMERG-bc(t + 30 min)`: 100.00 % of 3667 cell-times (Mandra), 97.90 % of 30469
(Pineios; exceptions are 4 edge-straddling cells equal to 2× the adjacent IMERG cell, Σ ratio 1.0006), 95.13 % of
10919 (Valencia-350; zero-filled outer ring, Σ ratio 0.9901). The IMERG-bc bbox totals over each file's bias window
reproduce 400.00 / 200.00 / 350.00 exactly (the stated targets); `model/` and `model_author_ref/` precipitation
arrays are identical for Pineios and Mandra. `sfincs_map.nc` stores no rainfall variable (`storecumprcp = 0`).

## (e) Inverse barometer at the open boundary (`F5_e.md`)
- All three runs (Pineios, Valencia as-run, Valencia 164): `sfincs.inp` has `baro = 1`, `pavbnd = 1`, `gapres = 101200.0`,
  `zsini = 0`, `rhow = 1024.0`, `tspinup = 0.0`, `netampfile = press_2d.nc`; **no `bndfile` / `bzsfile` / `bzifile` /
  `netbndbzsbzifile`** (absent from `sfincs.inp`, no such file in the folders, `sfincs_map.nc` attrs `bndfile = none`).
  Every SFINCS log: *"Warning! Boundary cells found in mask without boundary points from bnd file. Setting water level at
  0.0 m at mask boundary cells."* and *"Atmospheric pressure : yes"*.
- Pineios: 650 msk = 2 cells, all zb = 0.000 m, **never wet** (zs NaN at all 193 hourly outputs; `zsmax` NaN in all 5200
  cell-windows). Boundary-mean MSLP 1018.01 → **1007.76 hPa at 2023-09-05 03:00**; expected IB **+0.102 m** (rel. first
  step) / +0.055 m (rel. 1013.25 hPa). Observed boundary rise: none (level ≤ 0.000 m throughout). First interior row
  (654 cells, zb = 0): wet-mean zs 0.020 m at the MSLP minimum, series max 0.0316 m.
- Valencia (both runs, `press_2d.nc` and `sfincs.inp` byte-identical): 1233 msk = 2 cells; the 21 with zb < 0 are wet and
  hold **zs = 0.000 m at every one of 121 outputs**; boundary-mean MSLP min **1012.43 hPa (2024-10-30 03:00)**, expected
  IB +0.028 m (rel. first) / +0.008 m (rel. 1013.25). Observed Δzs = 0.000 m.
- Interior cells with zb < 0 did rise — Pineios 131 cells +0.864 m mean at the MSLP minimum (series max 1.171 m at
  2023-09-07 13:00, +58 h after the minimum, boundary MSLP back at 1018.11 hPa); Valencia 12207 cells +2.523 m (as-run)
  / +1.712 m (164 re-run) — i.e. runoff ponding, not a pressure response (expected local IB 0.10 / 0.024 m).
- **`pavbnd = 1` did not act at the boundary in any run**: with no water-level forcing the boundary stays at 0.0 m.
  Side fact: the `sfincs_map.nc` `inp` attribute block records `tspinup = 604800` (Pineios) / `259200` (Valencia)
  = tstart − tref, while `sfincs.inp` carries `tspinup = 0.0`; the meaning of this echo was not established.

## (f) Spin-up / antecedent period (`F5_f.md`, five events)
| | Pineios | Strymonas v3 | Mandra | Valencia | Emilia-Romagna |
|---|---|---|---|---|---|
| YAML spinup / pre / post (d) | 7 / 3 / 4 | 7 / 3 / 3 | 1 / 2 / 2 | 3 / 2 / 2 | 14 / 3 / 4 |
| `sfincs.inp` tref → tstart → tstop | 08-27 → 09-03 → 09-11 (2023) | 03-21 → 03-28 → 04-04 (2015) | 11-12 → 11-13 → 11-18 (2017) | 10-24 → 10-27 → 11-01 (2024) | 04-30 → 05-14 → 05-22 (2023) |
| `tspinup` / `zsini` | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 |
| simulated (tstop − tstart, d) | 8 | 7 | 5 | 5 | 8 |
| simulated before event.date (d) | 3 | 3 | 2 | 2 | 3 |
| stated spin-up = tstart − tref (d) | 7 | 7 | 1 | 3 | 14 |
| antecedent [tref, tstart) simulated? | no | no | no | no | no |
Mechanism: `_common.py:223` puts `spinup_days` into **tref only** (`tref = date − pre − spinup`), `:229` `tstart = date − pre`;
the template sets `tref/tstart/tstop` and `zsini: 0`, no `tspinup`; hydromt_sfincs writes its default `tspinup = 0.0`
(`sfincs_input.py:26`). SFINCS integrates from tstart (manual v2.3.0: runtime = tref/tstart/tstop; `tspinup` is "Duration
of spinup period **after** tstart" for boundary-level damping); every `sfincs_map.nc` time axis starts at tstart. The
"spin-up" of Table 2 is therefore the length of the forcing download window, not simulated time; the antecedent
rainfall it was meant to supply never enters the model. The simulated pre-event time is `pre_event_days`.
Second-order facts from the same audit: `sfincs.dis` rows and all raw downloads start at tref; for Strymonas and
Emilia the IMERG files kept GPM `calendar: julian`, xarray decodes `cftime` objects and hydromt does not time-slice
(`rasterdataset.py:561`), so their `precip_2d.nc` carries 336 / 672 pre-tstart frames (unused by SFINCS); the
bias-corrected events are re-encoded `proleptic_gregorian` and sliced to [tstart, tstop].

## Relevance to EMSR933 (facts, no choice made)
With the harness as published, the EMSR933 enhanced run would receive IMERG Late at **2 ×** the retrieved rate, 30 min
early; `tspinup = 0` with the 7-day antecedent window not simulated; the coastal IB boundary fixed at 0 m. The
development and held-out numbers in `docs/AUDIT.md` were all produced under these same conditions. A raw-IMERG Crete
run would also keep the `julian` calendar (no slicing; harmless). Options recorded for the author:
(a) run EMSR933 with the harness exactly as published (same harness as the five events, inherits the above);
(b) correct the IMERG handling (`cumulative_input=False, time_label=left` — synthetic result: 20 mm / 0 min), add
`tspinup`/true spin-up and an IB water-level forcing for EMSR933 only (then EMSR933 is not scored by the same harness);
(c) correct and re-run all events (new release; every published number changes).
