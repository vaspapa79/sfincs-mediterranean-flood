# F5 — precipitation-forcing conversion in `setup_precip_forcing_from_grid` (facts only)

Env: hydromt 0.10.1, hydromt_sfincs 1.2.2, xarray 2026.4.0 (`sfincs-viz`). Script `f5_abc_synthetic.py` → `F5_abc.json` (all numbers below are from it). Worktree = `D:\ELKAK\sfincs-mediterranean-floods\.worktrees\emsr933-crete`; `IMPL` = `D:\ELKAK\implementation\mandra_sfincs_enhanced` (opened read-only). Pipeline files below carry the mtime recorded in the JSON (`download_imerg.py` was modified during this check: 147 lines, 2026-10-09 13:24 UTC; the other four 12:40 UTC).

## (a) Code path
1. `skill/scripts/build_model.py:111` reads `skill/templates/sfincs_build.yml.tmpl`; `:113` renders it with `"rain_dataset": cfg.rain_source` (`:131`); `:134` writes `sfincs_build.yml`; `:152-154` command `hydromt build sfincs <model_dir> -i sfincs_build.yml -d data_catalog.yml --fo -vv`; `:158` `subprocess.run`.
2. `skill/templates/sfincs_build.yml.tmpl:49-51`: `setup_precip_forcing_from_grid:` / `precip: $rain_dataset` / `aggregate: false` — no `cumulative_input` or `time_label` key, so the method defaults apply.
3. `hydromt/cli/main.py:169` `def build(...)` → `:215` `MODELS.load(model)(root=..., mode=...)` → `:224` `mod.build(region, opt=opt)`.
4. `hydromt/models/model_api.py:190` `Model.build` → `:246` `self._run_log_method(method, **kwargs)` per yml section → `:166` `_run_log_method`: `:169` `getattr(self, method)`, `:187` logs every parameter incl. defaults (`setup_precip_forcing_from_grid.cumulative_input: True` etc.), `:188` `return func(*args, **kwargs)`; `:250` `self.write()`.
5. `hydromt_sfincs/sfincs.py:2306-2427` `SfincsModel.setup_precip_forcing_from_grid(self, precip, dst_res=None, cumulative_input=True, time_label="right", aggregate=False, **kwargs)` (defaults `:2310-2312`):
   - `:2373-2379` `self.data_catalog.get_rasterdataset(precip, bbox=self.bbox, buffer=2, time_tuple=self.get_model_time(), variables=["precip"])`; time slice in `hydromt/data_adapter/rasterdataset.py:573` `ds.sel({"time": slice(*time_tuple)})` (tstart..tstop inclusive; `get_model_time` at `sfincs.py:3825`).
   - `:2382` `time_interval = da_to_timedelta(precip).total_seconds()` ← `hydromt/workflows/forcing.py:778-780` `return pd.to_timedelta(np.diff(da.time).mean())` (import `sfincs.py:22`).
   - `:2385-2387` `dtwnd = self.config.get("dtwnd", 1800)`; lowered only `if dtwnd > time_interval` (1800 s input → unchanged).
   - `:2393` `if cumulative_input:` → `:2395` `precip = precip / (time_interval / 3600)` → `:2396` `if time_label == "right":` → `:2399` `precip = precip.shift(time=-1, fill_value=0)` (value of stamp i+1 moved to stamp i; last stamp set to 0).
   - `:2416` `precip.raster.reproject(dst_crs=self.crs, ...)` (`nearest_index`), `:2420` rename `precip_2d`, `:2427` `self.set_forcing(...)`.
6. Write: `sfincs.py:3365` `write_forcing` → `:3439` time encoding `minutes since <tref>`; `:3458` default `netamprfile = precip_2d.nc`; `:3469` `ds.to_netcdf`; `_FORCING_NET["precip_2d"] = ("netampr", {"Precipitation": "precip_2d"})` (`sfincs.py:64`) → variable name `Precipitation`.

Docstring, verbatim (installed 1.2.2): `cumulative_input: bool, optional` — "Option to indicate whether the input precipitation is cumulative in mm (True, default) or a precipitation rate in mm/hr (False). When cumulative, the data is converted to mm/hr by dividing by the time interval of the input dataset." `time_label: literal, optional` — "Label to prescribe whether the accumulation period of the precipitation is starting (left) or ending (right) at the validity date and time. This is only relevant if cumulative_input=True." Summary (`:2317-2318`): "SFINCS requires the mean precipitation rate in mm/hr over the upcoming interval. It will use the rate at the start of this interval and keep it constant throughout."

IMERG writer `skill/scripts/download_imerg.py`: `:107-108` `xr.open_mfdataset(..., group="Grid", combine="nested", concat_dim="time")` — the granule `time` coordinate is passed through unchanged (no shift; `time_bnds` not used); `:127` rename lat/lon → latitude/longitude; `:128` `pr.attrs["units"] = "mm/h"`; `:137` `temporal_resolution = "30 min"`; `:138` `to_netcdf`. `bias_correct_imerg.py:100` `dt_h` from the stamp difference (0.5 h), `:110` totals = Σ(rate)·dt_h (treats values as rates); `:151` units `mm/h`; `:164-167` rewrites time as `minutes since 2017-01-01 00:00:00`, proleptic_gregorian. ERA5 `prep_inputs.py:46-47` `tp*1000` labelled `mm/h`; `:49` renamed `precip`.

Real files (IMPL, read-only):

| file | variable / units attr | n_time | first 4 stamps | step |
|---|---|---|---|---|
| `data/imerg_mandra.nc` | `precip` "mm/h"; global attr "Multiplicative scaling 8.551x applied to event window 2017-11-14 00:00 to 2017-11-15 23:30 ... 200.0 mm" | 289 | 2017-11-12 00:00, 00:30, 01:00, 01:30 | 1800 s |
| `data/imerg_mandra.raw.nc` | `precip` units "mm/h", IMERG `Units` "mm/hr"; calendar julian | 289 | same | 1800 s |
| `data/imerg_hdf5/3B-HHR.MS.MRG.3IMERG.20171112-S000000-E002959.0000.V07B.HDF5` | `precipitation` "mm/hr" | 1 | time = 2017-11-12 00:00:00, `time_bnds` = [00:00:00, 00:30:00] → stamp = START of the 30-min window (2nd granule: 00:30, bnds [00:30, 01:00]) | — |
| `data/era5_mandra.nc` | `precip` "mm/h", `GRIB_stepType` "accum", `GRIB_units` "m" | 168 | 2017-11-12 00:00, 01:00, 02:00, 03:00 | 3600 s |
| `model/precip_2d.nc` (as-run) | `Precipitation` "mm/h" | 241 | 2017-11-13 00:00, 00:30, 01:00, 01:30 (last 2017-11-18 00:00) | 1800 s |

As-run build (`model/hydromt.log`): `setup_precip_forcing_from_grid.cumulative_input: True`, `.time_label: right`, `.aggregate: False`; `model/sfincs.inp`: `dtwnd = 1800.0`, `netamprfile = precip_2d.nc`, tstart `20171113 000000`, tstop `20171118 000000`.
As-run `precip_2d.nc` vs `imerg_mandra.nc` (IMERG cell nearest to each of the 48 forcing cells; 240 stamps): max |P2d(t) - 2·IMERG(t+30 min)| = 0.0, fraction within 1e-3 = 1.0; max |P2d(t) - IMERG(t)| = 175.64 mm/h, fraction within 1e-3 = 0.6349; last stamp 2017-11-18 00:00 max = 0.0 (fill) while IMERG there = 0.45 mm/h; IMERG at the dropped first stamp = 0.24 mm/h. Depth over the sim window (Σ·0.5 h, cell mean): P2d 456.24 mm vs IMERG 228.13 mm, ratio 1.99989 (per cell 1.99909–2.0). Watershed bbox (23.4, 38.05, 23.55, 38.15), event window 2017-11-14 00:00 – 11-15 23:30: IMERG 4-cell mean 200.0 mm (= the bias-correction target); on the same nearest cells as the 3 forcing cells inside it: IMERG 257.49 mm vs P2d 514.98 mm (ratio 2.0); full sim window 360.53 vs 721.05 mm (ratio 2.0).

## (b), (c), extra — synthetic runs through the same method
Setup: `SfincsModel(root, mode="w+")`, `setup_config(tref=tstart=20170101 000000, tstop=...)`, `setup_grid(x0=700000, y0=4200000, dx=dy=1000, nmax=mmax=5, rotation=0, epsg=32634)`; input DataArray `precip` (time, latitude, longitude), 0.1° EPSG:4326 grid, attr units "mm/h"; then `setup_precip_forcing_from_grid(precip=..., aggregate=False, **kw)` + `write_forcing()`. The direct DataArray was accepted (`data_catalog.py:1269`). Output in every case: `precip_2d.nc`, variable `Precipitation`, units attr "mm/h", time encoding `minutes since 2017-01-01`, output stamps identical to the input stamps, spatially uniform, `dtwnd` stays 1800.0. Totals: "pc" = Σ value_i·Δt (rate held constant over the step after its stamp — the SFINCS rule quoted above); "trapz" = Σ (v_i+v_{i+1})/2·Δt over the stamps.

| case | input (mm/h) | kwargs | output values at the input stamps | total pc / trapz (mm) | factor vs input total | time offset |
|---|---|---|---|---|---|---|
| (b) half-hourly, DataArray | 00:00, 00:30, 01:00, 01:30 @ 10 (20 mm) | defaults | 20, 20, 20, 0 | 30.0 / 25.0 | 1.5 / 1.25; out(i)/in(i+1) = 2.0, 2.0, 2.0 | out(i) = 2·in(i+1): -30 min |
| (b) via netCDF + catalog entry (`driver: netcdf, crs: 4326`) | same | defaults | 20, 20, 20, 0 | 30.0 / 25.0 | same | same |
| (b) via `hydromt build sfincs` CLI (yml as in template) | same | template form | 20, 20, 20, 0 | 30.0 / 25.0 | `identical_to_dataarray_case` = true; log: `cumulative_input: True`, `time_label: right` | same |
| (c) hourly (ERA5 form) | 00:00, 01:00 @ 10 (20 mm) | defaults | 10, 0 | 10.0 / 5.0 | 0.5 / 0.25; out(0)/in(1) = 1.0 (magnitude unchanged) | -60 min |
| extra: half-hourly | same as (b) | `cumulative_input=False, time_label="left"` | 10, 10, 10, 10 | 20.0 / 15.0 | 1.0 / 0.75 | 0 |
| pulse half-hourly (8 stamps 00:00–03:30, 10 only at 01:00; 5 mm) | | defaults | 20 at 00:30, else 0 | 10.0 / 10.0 | 2.0 | -30 min |
| pulse hourly (4 stamps 00:00–03:00, 10 only at 01:00; 10 mm) | | defaults | 10 at 00:00, else 0 | 10.0 / 5.0 | 1.0 | -60 min |
| pulse half-hourly | as pulse half-hourly | `cumulative_input=False, time_label="left"` | 10 at 01:00, else 0 | 5.0 / 5.0 | 1.0 | 0 |

Expected for a correct pass-through of the (b) input: 20 mm total, 0 offset. In (b)/(c) the uniform totals also carry the end-of-series effect of `shift(time=-1, fill_value=0)` (last stamp → 0); the pulse rows isolate factor and offset.

Not verified here: whether ERA5 hourly `tp` at stamp T is the accumulation over [T-1 h, T] (the file only shows `GRIB_stepType = accum`); only the pipeline's labelling (`mm/h`) and the resulting conversion factor (1.0) and shift (-60 min) were measured.

Files: `f5_abc_synthetic.py`, `F5_abc.json`, `F5_abc.md`, `tmp_synthetic/` (8 scratch models + `synth_halfhourly.nc`, `data_catalog.yml`, `sfincs_build_synth.yml`).
