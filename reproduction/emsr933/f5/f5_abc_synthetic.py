"""F5 - precipitation-forcing conversion check for the SFINCS/HydroMT pipeline.

Facts only.  Three parts, all written to F5_abc.json next to this script:

  a) code-path facts collected with `inspect` from the installed hydromt /
     hydromt_sfincs, the pipeline scripts/template (line numbers found by text
     search), and READ-ONLY facts from the real Mandra enhanced run
     (D:/ELKAK/implementation/mandra_sfincs_enhanced: imerg_mandra.nc,
     imerg_mandra.raw.nc, first IMERG HDF5 granule, era5_mandra.nc,
     model/precip_2d.nc, model/sfincs.inp, model/hydromt.log).
  b) synthetic half-hourly 10 mm/h input (4 stamps, 2 h) through
     SfincsModel.setup_precip_forcing_from_grid(precip=..., aggregate=False)
     with the pipeline's (default) kwargs - via a direct DataArray, via a
     netCDF + data-catalog entry, and via the `hydromt build sfincs` CLI.
  c) the same with hourly stamps (ERA5 case), plus the extra variant
     cumulative_input=False, time_label='left', plus two single-step pulse
     cases that isolate factor and time offset without edge effects.

Run:
  set GDAL_DATA=<env>/Library/share/gdal
  <env>/python.exe f5_abc_synthetic.py

Nothing is written outside this script's folder (f5/).  The implementation
folder is only opened for reading.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os

os.environ.setdefault(
    "GDAL_DATA",
    "C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/Library/share/gdal",
)

import glob
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pyproj
import xarray as xr

import hydromt
import hydromt_sfincs
from hydromt.cli.main import build as cli_build
from hydromt.data_adapter.rasterdataset import RasterDatasetAdapter
from hydromt.models.model_api import Model
from hydromt.workflows.forcing import da_to_timedelta
from hydromt_sfincs import SfincsModel

F5 = Path(__file__).resolve().parent
TMP = F5 / "tmp_synthetic"
TMP.mkdir(parents=True, exist_ok=True)
WT = F5.parents[2]  # worktree root: .../sfincs-mediterranean-floods/.worktrees/emsr933-crete
IMPL = Path("D:/ELKAK/implementation/mandra_sfincs_enhanced")  # READ-ONLY
HYDROMT_EXE = Path(sys.executable).parent / "Scripts" / "hydromt.exe"

OUT = {"meta": {}, "a_code_path": {}, "a_real_files": {}, "a_asrun_model": {}, "cases": {}}


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (np.datetime64, pd.Timestamp)):
        return str(pd.Timestamp(o))
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    if isinstance(o, Path):
        return str(o)
    if o is None or isinstance(o, (bool, int, str)):
        return o
    return str(o)


def find_lines(path: Path, patterns):
    """Return {pattern: [line numbers]} for literal substrings in a text file."""
    text = path.read_text(encoding="utf-8").splitlines()
    res = {
        "_file_n_lines": len(text),
        "_file_mtime_utc": pd.Timestamp(path.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M:%S") + " UTC",
    }
    for pat in patterns:
        res[pat] = [i + 1 for i, l in enumerate(text) if pat in l]
    return res


# --------------------------------------------------------------------------
# (a) code path facts
# --------------------------------------------------------------------------
OUT["meta"] = {
    "python": sys.executable,
    "hydromt_version": hydromt.__version__,
    "hydromt_sfincs_version": hydromt_sfincs.__version__,
    "xarray_version": xr.__version__,
    "numpy_version": np.__version__,
    "pandas_version": pd.__version__,
    "hydromt_exe": str(HYDROMT_EXE),
    "hydromt_exe_exists": HYDROMT_EXE.exists(),
    "worktree": str(WT),
}

f = SfincsModel.setup_precip_forcing_from_grid
src_lines, start = inspect.getsourcelines(f)
sig = inspect.signature(f)
doc = inspect.getdoc(f).splitlines()


def doc_block(doc_lines, header_startswith):
    """Return the parameter block (header line + indented continuation lines)."""
    out = []
    grab = False
    for l in doc_lines:
        if l.startswith(header_startswith):
            grab = True
            out.append(l)
            continue
        if grab:
            if l.startswith("    ") and l.strip():
                out.append(l)
            else:
                break
    return out


key_markers = (
    "def setup_precip_forcing_from_grid",
    "cumulative_input: bool = True",
    'time_label: Literal["left", "right"] = "right"',
    "aggregate: bool = False",
    "precip = self.data_catalog.get_rasterdataset(",
    "time_tuple=self.get_model_time()",
    "time_interval = da_to_timedelta(precip).total_seconds()",
    'dtwnd = self.config.get("dtwnd", 1800)',
    "if dtwnd > time_interval:",
    'self.set_config("dtwnd", time_interval)',
    "if cumulative_input:",
    "precip = precip / (time_interval / 3600)",
    'if time_label == "right":',
    "precip = precip.shift(time=-1, fill_value=0)",
    "precip_out = precip.raster.reproject(",
    'precip_out = precip_out.rename("precip_2d")',
    'self.set_forcing(precip_out, name="precip_2d")',
)
OUT["a_code_path"]["setup_precip_forcing_from_grid"] = {
    "file": inspect.getsourcefile(f),
    "def_line": start,
    "end_line": start + len(src_lines) - 1,
    "signature_defaults": {
        k: repr(v.default)
        for k, v in sig.parameters.items()
        if v.default is not inspect._empty
    },
    "key_lines": {
        str(start + i): l.rstrip()
        for i, l in enumerate(src_lines)
        if any(m in l for m in key_markers)
    },
    "docstring_summary_lines_2_3": [
        l for l in doc if l.startswith("SFINCS requires") or l.startswith("It will use the rate")
    ],
    "docstring_cumulative_input": doc_block(doc, "cumulative_input: bool, optional"),
    "docstring_time_label": doc_block(doc, "time_label: literal, optional"),
}
_sp = OUT["a_code_path"]["setup_precip_forcing_from_grid"]
_sp["docstring_summary_line_numbers"] = [
    start + i
    for i, l in enumerate(src_lines)
    if l.strip().startswith("SFINCS requires") or l.strip().startswith("It will use the rate")
]
_i0 = next(i for i, l in enumerate(src_lines) if "precip = self.data_catalog.get_rasterdataset(" in l)
_i1 = next(i for i in range(_i0, len(src_lines)) if src_lines[i].strip() == ")")
_sp["get_rasterdataset_call_lines_first_last"] = [start + _i0, start + _i1]

dl, dstart = inspect.getsourcelines(da_to_timedelta)
OUT["a_code_path"]["da_to_timedelta"] = {
    "file": inspect.getsourcefile(da_to_timedelta),
    "def_line": dstart,
    "end_line": dstart + len(dl) - 1,
    "source": [l.rstrip() for l in dl],
    "import_line_in_sfincs_py": find_lines(
        Path(inspect.getsourcefile(f)), ["from hydromt.workflows.forcing import da_to_timedelta"]
    ),
}

from hydromt.data_catalog import DataCatalog

cl, cstart = inspect.getsourcelines(DataCatalog.get_rasterdataset)
OUT["a_code_path"]["data_catalog_get_rasterdataset"] = {
    "file": inspect.getsourcefile(DataCatalog.get_rasterdataset),
    "def_line": cstart,
    "dataarray_branch_line": [cstart + i for i, l in enumerate(cl) if "elif isinstance(data_like, (xr.DataArray, xr.Dataset)):" in l],
    "slice_data_call_line": [cstart + i for i, l in enumerate(cl) if "data_like = RasterDatasetAdapter._slice_data(" in l],
}

cli_fn = inspect.unwrap(cli_build.callback)  # click.pass_context wraps the real function
bl, bstart = inspect.getsourcelines(cli_fn)  # bstart = first decorator line of the block
OUT["a_code_path"]["hydromt_cli_build"] = {
    "file": inspect.getsourcefile(cli_fn),
    "block_first_line": bstart,
    "def_line": [bstart + i for i, l in enumerate(bl) if l.startswith("def build(")],
    "mod_build_call_line": [
        bstart + i for i, l in enumerate(bl) if "mod.build(region, opt=opt)" in l
    ],
    "model_load_line": [bstart + i for i, l in enumerate(bl) if "MODELS.load(model)(" in l],
}
ml, mstart = inspect.getsourcelines(Model.build)
rl, rstart = inspect.getsourcelines(Model._run_log_method)
OUT["a_code_path"]["model_api"] = {
    "file": inspect.getsourcefile(Model.build),
    "build_def_line": mstart,
    "build_loop_line": [mstart + i for i, l in enumerate(ml) if "self._run_log_method(method, **kwargs)" in l],
    "build_write_line": [mstart + i for i, l in enumerate(ml) if "self.write()" in l],
    "_run_log_method_def_line": rstart,
    "_run_log_method_getattr_line": [rstart + i for i, l in enumerate(rl) if "getattr(self, method)" in l],
    "_run_log_method_log_line": [rstart + i for i, l in enumerate(rl) if 'self.logger.info(f"{method}.{k}: {v}")' in l],
    "_run_log_method_call_line": [rstart + i for i, l in enumerate(rl) if "return func(*args, **kwargs)" in l],
}
sl, sstart = inspect.getsourcelines(RasterDatasetAdapter._slice_temporal_dimension)
OUT["a_code_path"]["rasterdataset_time_slice"] = {
    "file": inspect.getsourcefile(RasterDatasetAdapter._slice_temporal_dimension),
    "def_line": sstart,
    "sel_line": [sstart + i for i, l in enumerate(sl) if 'ds.sel({"time": slice(*time_tuple)})' in l],
}
wl, wstart = inspect.getsourcelines(SfincsModel.write_forcing)
OUT["a_code_path"]["write_forcing"] = {
    "file": inspect.getsourcefile(SfincsModel.write_forcing),
    "def_line": wstart,
    "encoding_line": [wstart + i for i, l in enumerate(wl) if 'time={"units": f"minutes since {tref_str}"' in l],
    "default_filename_line": [wstart + i for i, l in enumerate(wl) if 'self.set_config(f"{fname}file", f"{name}.nc")' in l],
    "to_netcdf_line": [wstart + i for i, l in enumerate(wl) if "ds.to_netcdf(fn, encoding=encoding)" in l],
    "_FORCING_NET_precip_2d": repr(SfincsModel._FORCING_NET["precip_2d"]),
    "_FORCING_NET_line": find_lines(Path(inspect.getsourcefile(f)), ['"precip_2d": ("netampr", {"Precipitation": "precip_2d"}),']),
}
gl, gstart = inspect.getsourcelines(SfincsModel.get_model_time)
OUT["a_code_path"]["get_model_time"] = {"file": inspect.getsourcefile(SfincsModel.get_model_time), "def_line": gstart}

# pipeline files (worktree)
OUT["a_code_path"]["pipeline"] = {
    "build_model.py": {
        "file": str(WT / "skill/scripts/build_model.py"),
        "lines": find_lines(
            WT / "skill/scripts/build_model.py",
            [
                'tmpl = (SKILL_DIR / "templates" / "sfincs_build.yml.tmpl").read_text()',
                "rendered = string.Template(tmpl).substitute({",
                '"rain_dataset": cfg.rain_source,',
                'yml_path.write_text(rendered, encoding="utf-8")',
                'str(hydromt), "build", "sfincs", str(model_dir),',
                '"-d", str(work / "data_catalog.yml"),',
                "res = subprocess.run(cmd, cwd=str(work))",
            ],
        ),
    },
    "sfincs_build.yml.tmpl": {
        "file": str(WT / "skill/templates/sfincs_build.yml.tmpl"),
        "lines": find_lines(
            WT / "skill/templates/sfincs_build.yml.tmpl",
            ["setup_precip_forcing_from_grid:", "precip: $rain_dataset", "aggregate: false"],
        ),
    },
    "download_imerg.py": {
        "file": str(WT / "skill/scripts/download_imerg.py"),
        "lines": find_lines(
            WT / "skill/scripts/download_imerg.py",
            [
                'ds = xr.open_mfdataset([str(f) for f in local_files], group="Grid",',
                'combine="nested", concat_dim="time",',
                'pr = pr.rename({"lat": "latitude", "lon": "longitude"})',
                'pr.attrs["units"] = "mm/h"',
                'out_ds.attrs["temporal_resolution"] = "30 min"',
                'out_ds.to_netcdf(out, engine="h5netcdf")',
            ],
        ),
    },
    "bias_correct_imerg.py": {
        "file": str(WT / "skill/scripts/bias_correct_imerg.py"),
        "lines": find_lines(
            WT / "skill/scripts/bias_correct_imerg.py",
            [
                'dt_h = float((times_np[1] - times_np[0]) / np.timedelta64(1, "h"))',
                "current_total = float(np.nansum(p_ws_mean[in_event]) * dt_h)",
                'ds_out["precip"].attrs["units"] = "mm/h"',
                'encoding = {"time": {"units": "minutes since 2017-01-01 00:00:00",',
                'ds_out.to_netcdf(imerg_path, engine="h5netcdf", mode="w", encoding=encoding)',
            ],
        ),
    },
    "prep_inputs.py": {
        "file": str(WT / "skill/scripts/prep_inputs.py"),
        "lines": find_lines(
            WT / "skill/scripts/prep_inputs.py",
            [
                'ds["tp"] = ds["tp"] * 1000.0',
                'ds["tp"].attrs.update({"units": "mm/h", "long_name": "Total precipitation"})',
                '"tp": "precip", "msl": "press_msl", "u10": "wind10_u", "v10": "wind10_v"',
            ],
        ),
    },
}


# --------------------------------------------------------------------------
# (a) real-file facts (READ-ONLY)
# --------------------------------------------------------------------------
def nc_facts(path: Path, engine=None, nfirst=4):
    try:
        ds = xr.open_dataset(path, engine=engine, decode_times=True)
    except Exception as e:  # era5 file is NETCDF3 -> h5netcdf cannot open it
        ds = xr.open_dataset(path, decode_times=True)
    t = ds["time"].values
    res = {
        "path": str(path),
        "exists": path.exists(),
        "dims": {k: int(v) for k, v in ds.sizes.items()},
        "data_vars": {v: {"dims": list(ds[v].dims), "attrs": jsonable(dict(ds[v].attrs))} for v in ds.data_vars},
        "time_dtype": str(t.dtype),
        "n_time": int(len(t)),
        "time_first": [str(x) for x in t[:nfirst]],
        "time_last": str(t[-1]),
        "time_encoding": {k: jsonable(ds["time"].encoding.get(k)) for k in ("units", "calendar", "dtype")},
        "time_attrs": jsonable(dict(ds["time"].attrs)),
        "global_attrs": jsonable(dict(ds.attrs)),
    }
    try:
        tt = pd.to_datetime([pd.Timestamp(str(x)) for x in t])
        steps = np.unique(np.diff(tt.values).astype("timedelta64[s]").astype(int))
        res["time_step_unique_s"] = steps.tolist()
    except Exception as e:
        res["time_step_unique_s"] = f"n/a ({e})"
    ds.close()
    return res


OUT["a_real_files"]["imerg_mandra.nc"] = nc_facts(IMPL / "data/imerg_mandra.nc", engine="h5netcdf")
OUT["a_real_files"]["imerg_mandra.raw.nc"] = nc_facts(IMPL / "data/imerg_mandra.raw.nc", engine="h5netcdf")
OUT["a_real_files"]["era5_mandra.nc"] = nc_facts(IMPL / "data/era5_mandra.nc")
OUT["a_real_files"]["model_precip_2d.nc"] = nc_facts(IMPL / "model/precip_2d.nc", engine="h5netcdf")
# strip the very long GRIB attrs of the era5 file down to the relevant ones
e5 = OUT["a_real_files"]["era5_mandra.nc"]
e5["data_vars"] = {
    v: {"dims": d["dims"], "attrs": {k: d["attrs"][k] for k in ("units", "long_name", "GRIB_stepType", "GRIB_units", "GRIB_shortName") if k in d["attrs"]}}
    for v, d in e5["data_vars"].items()
}
e5["global_attrs"] = {k: e5["global_attrs"][k] for k in ("Conventions", "institution") if k in e5["global_attrs"]}

granules = sorted(glob.glob(str(IMPL / "data/imerg_hdf5/*.HDF5")))
g_facts = {"n_granules": len(granules), "first_two": []}
for gpath in granules[:2]:
    raw = xr.open_dataset(gpath, group="Grid", engine="h5netcdf", decode_times=False)
    dec = xr.open_dataset(gpath, group="Grid", engine="h5netcdf", decode_times=True)
    g_facts["first_two"].append(
        {
            "file": Path(gpath).name,
            "time_raw": jsonable(raw["time"].values),
            "time_units": raw["time"].attrs.get("units"),
            "time_bnds_raw": jsonable(raw["time_bnds"].values) if "time_bnds" in raw else None,
            "time_decoded": [str(x) for x in dec["time"].values],
            "time_bnds_decoded": [[str(x) for x in row] for row in dec["time_bnds"].values] if "time_bnds" in dec else None,
            "precipitation_units_attr": dec["precipitation"].attrs.get("units"),
            "precipitation_Units_attr": dec["precipitation"].attrs.get("Units"),
        }
    )
    raw.close()
    dec.close()
OUT["a_real_files"]["imerg_hdf5_granules"] = g_facts

# as-run model: sfincs.inp and hydromt.log
inp = (IMPL / "model/sfincs.inp").read_text().splitlines()
OUT["a_asrun_model"]["sfincs.inp"] = {
    "path": str(IMPL / "model/sfincs.inp"),
    "lines": [l for l in inp if l.split("=")[0].strip() in ("tref", "tstart", "tstop", "dtwnd", "netamprfile", "netampfile", "netamuamvfile")],
}
log = (IMPL / "model/hydromt.log").read_text(encoding="utf-8", errors="replace").splitlines()
OUT["a_asrun_model"]["hydromt.log"] = {
    "path": str(IMPL / "model/hydromt.log"),
    "setup_precip_lines": [l for l in log if "setup_precip_forcing_from_grid." in l],
    "dtwnd_lines": [l for l in log if "dtwnd" in l],
}

# as-run comparison: model/precip_2d.nc vs data/imerg_mandra.nc at the nearest IMERG cell
im = xr.open_dataset(IMPL / "data/imerg_mandra.nc", engine="h5netcdf")["precip"].load()
p2 = xr.open_dataset(IMPL / "model/precip_2d.nc", engine="h5netcdf")["Precipitation"].load()
tr = pyproj.Transformer.from_crs(32634, 4326, always_xy=True)
xx, yy = np.meshgrid(p2["x"].values, p2["y"].values)
lon, lat = tr.transform(xx, yy)
ilat = np.abs(im["latitude"].values[None, None, :] - lat[:, :, None]).argmin(-1)
ilon = np.abs(im["longitude"].values[None, None, :] - lon[:, :, None]).argmin(-1)
near = im.values[:, ilat, ilon]  # (t_im, ny, nx)
t_im = pd.to_datetime(im["time"].values)
t_p2 = pd.to_datetime(p2["time"].values)
pos = {t: i for i, t in enumerate(t_im)}
idx0 = np.array([pos[t] for t in t_p2])
idx1 = np.array([pos.get(t + pd.Timedelta(minutes=30), -1) for t in t_p2])
valid1 = idx1 >= 0
P = p2.values
d_lag0_x1 = P - near[idx0]
d_lag30_x2 = P[valid1] - 2.0 * near[idx1[valid1]]
d_lag30_x1 = P[valid1] - near[idx1[valid1]]
tol = 1e-3
cmp = {
    "description": "P2d[t, cell] compared with IMERG value at the IMERG cell nearest to the cell centre (nearest-centre lookup), "
    "at the same stamp (lag0) and at stamp t+30min (lag30), with factor 1 or 2",
    "n_p2d_cells": int(P.shape[1] * P.shape[2]),
    "n_stamps_compared_lag30": int(valid1.sum()),
    "max_abs_diff_lag0_x1": float(np.nanmax(np.abs(d_lag0_x1))),
    "max_abs_diff_lag30_x1": float(np.nanmax(np.abs(d_lag30_x1))),
    "max_abs_diff_lag30_x2": float(np.nanmax(np.abs(d_lag30_x2))),
    "frac_within_tol_lag0_x1": float(np.mean(np.abs(d_lag0_x1) <= tol)),
    "frac_within_tol_lag30_x2": float(np.mean(np.abs(d_lag30_x2) <= tol)),
    "tol": tol,
    "p2d_last_stamp": str(t_p2[-1]),
    "p2d_last_stamp_max_value": float(np.nanmax(P[-1])),
    "imerg_value_at_last_p2d_stamp_max": float(np.nanmax(near[idx0[-1]])),
    "imerg_value_at_first_p2d_stamp_max": float(np.nanmax(near[idx0[0]])),
}
# totals over the simulation window (all 241 p2d stamps), per matched cell pair
sum_p2 = np.nansum(P, axis=0) * 0.5
sum_im_same_window = np.nansum(near[idx0], axis=0) * 0.5
cmp["sim_window"] = {
    "window": [str(t_p2[0]), str(t_p2[-1])],
    "dt_h_used": 0.5,
    "p2d_depth_mm_cellmean": float(sum_p2.mean()),
    "imerg_nearest_depth_mm_cellmean_same_stamps": float(sum_im_same_window.mean()),
    "ratio_cellmean": float(sum_p2.mean() / sum_im_same_window.mean()),
    "ratio_per_cell_min": float((sum_p2 / sum_im_same_window).min()),
    "ratio_per_cell_max": float((sum_p2 / sum_im_same_window).max()),
}
# bias-correction event window, watershed bbox from the file's own attribute
ws = (23.4, 38.05, 23.55, 38.15)
ev0, ev1 = pd.Timestamp("2017-11-14 00:00"), pd.Timestamp("2017-11-15 23:30")
ws_lat = (im["latitude"].values >= ws[1]) & (im["latitude"].values <= ws[3])
ws_lon = (im["longitude"].values >= ws[0]) & (im["longitude"].values <= ws[2])
im_ev = (t_im >= ev0) & (t_im <= ev1)
im_ws_series = im.values[:, ws_lat, :][:, :, ws_lon].reshape(len(t_im), -1).mean(axis=1)
# p2d cells whose nearest IMERG cell is a watershed cell
ws_cells = np.zeros(P.shape[1:], dtype=bool)
for j in range(P.shape[1]):
    for i in range(P.shape[2]):
        ws_cells[j, i] = ws_lat[ilat[j, i]] and ws_lon[ilon[j, i]]
p2_ev_nom = (t_p2 >= ev0) & (t_p2 <= ev1)
p2_ev_shift = (t_p2 >= ev0 - pd.Timedelta(minutes=30)) & (t_p2 <= ev1 - pd.Timedelta(minutes=30))
p2_ws_series = P[:, ws_cells].mean(axis=1) if ws_cells.any() else None
# IMERG series on exactly the same nearest cells (same weights) as the selected p2d cells
near_ws_series = near[:, ws_cells].mean(axis=1) if ws_cells.any() else None
im_sim = (t_im >= t_p2[0]) & (t_im <= t_p2[-1])
cmp["event_window_watershed"] = {
    "watershed_bbox_lon_lat": list(ws),
    "event_window_from_file_attr": [str(ev0), str(ev1)],
    "n_imerg_ws_cells": int(ws_lat.sum() * ws_lon.sum()),
    "n_p2d_cells_nearest_in_ws": int(ws_cells.sum()),
    "imerg_ws_4cells_mean_depth_mm_event_window": float(np.nansum(im_ws_series[im_ev]) * 0.5),
    "imerg_same_nearest_cells_mean_depth_mm_event_window": float(np.nansum(near_ws_series[im_ev]) * 0.5) if near_ws_series is not None else None,
    "p2d_ws_mean_depth_mm_nominal_window": float(np.nansum(p2_ws_series[p2_ev_nom]) * 0.5) if p2_ws_series is not None else None,
    "p2d_ws_mean_depth_mm_window_shifted_minus30min": float(np.nansum(p2_ws_series[p2_ev_shift]) * 0.5) if p2_ws_series is not None else None,
    "ratio_p2d_shifted_window_over_imerg_same_cells_event_window": float(
        (np.nansum(p2_ws_series[p2_ev_shift]) * 0.5) / (np.nansum(near_ws_series[im_ev]) * 0.5)
    ) if p2_ws_series is not None else None,
    "imerg_ws_4cells_mean_depth_mm_full_sim_window": float(np.nansum(im_ws_series[im_sim]) * 0.5),
    "imerg_same_nearest_cells_mean_depth_mm_full_sim_window": float(np.nansum(near_ws_series[im_sim]) * 0.5) if near_ws_series is not None else None,
    "p2d_ws_mean_depth_mm_full_sim_window": float(np.nansum(p2_ws_series) * 0.5) if p2_ws_series is not None else None,
    "ratio_p2d_over_imerg_same_cells_full_sim_window": float(
        np.nansum(p2_ws_series) / np.nansum(near_ws_series[im_sim])
    ) if p2_ws_series is not None else None,
}
OUT["a_asrun_model"]["precip_2d_vs_imerg"] = cmp


# --------------------------------------------------------------------------
# synthetic cases
# --------------------------------------------------------------------------
X0, Y0, DX, DY, NMAX, MMAX, EPSG = 700000.0, 4200000.0, 1000.0, 1000.0, 5, 5, 32634
LAT = np.round(np.arange(37.0, 39.0001, 0.1), 3)
LON = np.round(np.arange(22.5, 24.5001, 0.1), 3)
OUT["synthetic_setup"] = {
    "model_grid": {"x0": X0, "y0": Y0, "dx": DX, "dy": DY, "nmax": NMAX, "mmax": MMAX, "rotation": 0, "epsg": EPSG},
    "model_mode": "w+",
    "tref_tstart": "20170101 000000",
    "input_crs_epsg": 4326,
    "input_dims": ["time", "latitude", "longitude"],
    "input_lat_range": [float(LAT[0]), float(LAT[-1])],
    "input_lon_range": [float(LON[0]), float(LON[-1])],
    "input_step_deg": 0.1,
    "input_units_attr": "mm/h",
    "catalog_entry_form": {"data_type": "RasterDataset", "driver": "netcdf", "crs": 4326},
}


def make_da(stamps, values):
    data = np.zeros((len(stamps), LAT.size, LON.size), dtype="float32")
    for i, v in enumerate(values):
        data[i] = v
    da = xr.DataArray(
        data,
        dims=("time", "latitude", "longitude"),
        coords={"time": pd.to_datetime(stamps), "latitude": LAT, "longitude": LON},
        name="precip",
        attrs={"units": "mm/h"},
    )
    da.raster.set_crs(4326)
    return da


def new_model(root: Path, tref, tstart, tstop, data_libs=None):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    mod = SfincsModel(root=str(root), mode="w+", data_libs=data_libs or [])
    mod.setup_config(tref=tref, tstart=tstart, tstop=tstop)
    mod.setup_grid(x0=X0, y0=Y0, dx=DX, dy=DY, nmax=NMAX, mmax=MMAX, rotation=0, epsg=EPSG)
    return mod


def read_back(root: Path, stamps_in, values_in, tstart, tstop):
    fn = root / "precip_2d.nc"
    ds = xr.open_dataset(fn, engine="h5netcdf", decode_times=True)
    var = [v for v in ds.data_vars][0]
    da = ds[var].load()
    t_out = pd.to_datetime(da["time"].values)
    vals = da.values.reshape(len(t_out), -1)
    mean = np.nanmean(vals, axis=1)
    t_in = pd.to_datetime(stamps_in)
    vin = np.asarray(values_in, dtype=float)
    dt_in_h = float((t_in[1] - t_in[0]).total_seconds() / 3600.0)
    dt_out_h = float((t_out[1] - t_out[0]).total_seconds() / 3600.0) if len(t_out) > 1 else dt_in_h
    pc = float(np.nansum(mean) * dt_out_h)  # piecewise constant: value held over the step after its stamp
    trap = float(np.nansum((mean[:-1] + mean[1:]) / 2.0) * dt_out_h) if len(mean) > 1 else None
    tot_in = float(vin.sum() * dt_in_h)
    same = [float(mean[i] / vin[i]) if vin[i] != 0 else None for i in range(min(len(mean), len(vin)))]
    shifted = [float(mean[i] / vin[i + 1]) if vin[i + 1] != 0 else None for i in range(min(len(mean), len(vin)) - 1)]
    # time offset: compare centre of mass of input and output pulses (only meaningful for pulse inputs)
    com_in = (t_in.values.astype("datetime64[s]").astype(np.int64) * vin).sum() / vin.sum()
    com_out = (t_out.values.astype("datetime64[s]").astype(np.int64) * mean).sum() / mean.sum() if mean.sum() > 0 else np.nan
    res = {
        "netampr_file": str(fn),
        "variable_name": var,
        "variable_attrs": jsonable(dict(da.attrs)),
        "dataset_attrs": jsonable(dict(ds.attrs)),
        "time_encoding_units": ds["time"].encoding.get("units"),
        "shape_time_y_x": list(da.shape),
        "input_stamps": [str(t) for t in t_in],
        "input_values_mm_per_h": vin.tolist(),
        "input_dt_h": dt_in_h,
        "input_total_depth_mm": tot_in,
        "output_stamps": [str(t) for t in t_out],
        "output_stamps_equal_input_stamps": [str(t) for t in t_out] == [str(t) for t in t_in],
        "output_domain_mean_mm_per_h": [float(v) for v in mean],
        "output_domain_min_mm_per_h": [float(v) for v in np.nanmin(vals, axis=1)],
        "output_domain_max_mm_per_h": [float(v) for v in np.nanmax(vals, axis=1)],
        "output_dt_h": dt_out_h,
        "total_piecewise_constant_mm": pc,
        "total_trapezoid_mm": trap,
        "factor_piecewise_constant_vs_input_total": pc / tot_in,
        "factor_trapezoid_vs_input_total": (trap / tot_in) if trap is not None else None,
        "ratio_out_i_over_in_i": same,
        "ratio_out_i_over_in_i_plus_1": shifted,
        "last_output_value": float(mean[-1]),
        "centre_of_mass_offset_min_out_minus_in": float((com_out - com_in) / 60.0) if not np.isnan(com_out) else None,
        "model_window": [tstart, tstop],
    }
    ds.close()
    return res


def api_case(name, stamps, values, tstop, precip_input, data_libs=None, **kw):
    tref = tstart = "20170101 000000"
    root = TMP / name
    mod = new_model(root, tref, tstart, tstop, data_libs=data_libs)
    if callable(precip_input):
        precip_input = precip_input()
    err = None
    try:
        mod.setup_precip_forcing_from_grid(precip=precip_input, aggregate=False, **kw)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    res = {"name": name, "kwargs_passed": {"aggregate": False, **{k: repr(v) for k, v in kw.items()}}, "error": err}
    if err is None:
        res["config_dtwnd_after_call"] = mod.config.get("dtwnd")
        mod.write_forcing()
        try:
            mod.write_config()
            inp_lines = (root / "sfincs.inp").read_text().splitlines()
            res["sfincs_inp_lines"] = [l for l in inp_lines if l.split("=")[0].strip() in ("tref", "tstart", "tstop", "dtwnd", "netamprfile")]
        except Exception as e:
            res["write_config_error"] = f"{type(e).__name__}: {e}"
        res.update(read_back(root, stamps, values, tstart, tstop))
    print(f"[{name}] error={err} total_pc={res.get('total_piecewise_constant_mm')} means={res.get('output_domain_mean_mm_per_h')}")
    return res


HH = ["2017-01-01 00:00", "2017-01-01 00:30", "2017-01-01 01:00", "2017-01-01 01:30"]
HR = ["2017-01-01 00:00", "2017-01-01 01:00"]

# (b) half-hourly, defaults, direct DataArray
OUT["cases"]["b_halfhourly_default_dataarray"] = api_case(
    "b_halfhourly_default_dataarray", HH, [10, 10, 10, 10], "20170101 020000", lambda: make_da(HH, [10, 10, 10, 10])
)

# (b) half-hourly, defaults, via netCDF + data catalog (pipeline-like entry)
nc_hh = TMP / "synth_halfhourly.nc"
make_da(HH, [10, 10, 10, 10]).to_dataset(name="precip").to_netcdf(nc_hh)
cat_yml = TMP / "data_catalog.yml"
cat_yml.write_text(
    "meta:\n  version: 1\n  hydromt_version: \">=0.10\"\n"
    f"  root: {TMP.as_posix()}\n\n"
    "imerg_synth:\n  data_type: RasterDataset\n  driver: netcdf\n  path: synth_halfhourly.nc\n  crs: 4326\n"
    "  meta:\n    category: meteo\n",
    encoding="utf-8",
)
OUT["cases"]["b_halfhourly_default_catalog"] = api_case(
    "b_halfhourly_default_catalog", HH, [10, 10, 10, 10], "20170101 020000", "imerg_synth", data_libs=[str(cat_yml)]
)

# (b) half-hourly, defaults, via the hydromt CLI exactly like the pipeline template
cli_root = TMP / "b_halfhourly_default_cli"
if cli_root.exists():
    shutil.rmtree(cli_root)
cli_root.mkdir(parents=True)
cli_yml = TMP / "sfincs_build_synth.yml"
cli_yml.write_text(
    "setup_config:\n  tref: 20170101 000000\n  tstart: 20170101 000000\n  tstop: 20170101 020000\n\n"
    f"setup_grid:\n  x0: {X0}\n  y0: {Y0}\n  dx: {DX}\n  dy: {DY}\n  nmax: {NMAX}\n  mmax: {MMAX}\n  rotation: 0\n  epsg: {EPSG}\n\n"
    "setup_precip_forcing_from_grid:\n  precip: imerg_synth\n  aggregate: false\n",
    encoding="utf-8",
)
cmd = [str(HYDROMT_EXE), "build", "sfincs", str(cli_root), "-i", str(cli_yml), "-d", str(cat_yml), "--fo", "-vv"]
cli_res = {"name": "b_halfhourly_default_cli", "command": " ".join(cmd)}
try:
    p = subprocess.run(cmd, cwd=str(TMP), capture_output=True, text=True, timeout=600)
    cli_res["returncode"] = p.returncode
    cli_res["stderr_tail"] = p.stderr[-1500:]
    if (cli_root / "precip_2d.nc").exists():
        cli_res.update(read_back(cli_root, HH, [10, 10, 10, 10], "20170101 000000", "20170101 020000"))
        log_lines = (cli_root / "hydromt.log").read_text(encoding="utf-8", errors="replace").splitlines()
        cli_res["hydromt_log_setup_precip_lines"] = [l.split(" - ", 3)[-1] for l in log_lines if "setup_precip_forcing_from_grid." in l]
        cli_res["sfincs_inp_lines"] = [l for l in (cli_root / "sfincs.inp").read_text().splitlines() if l.split("=")[0].strip() in ("dtwnd", "netamprfile")]
        a = OUT["cases"]["b_halfhourly_default_dataarray"]
        cli_res["identical_to_dataarray_case"] = bool(
            cli_res["output_stamps"] == a["output_stamps"]
            and np.allclose(cli_res["output_domain_mean_mm_per_h"], a["output_domain_mean_mm_per_h"])
            and np.allclose(cli_res["output_domain_min_mm_per_h"], a["output_domain_min_mm_per_h"])
            and np.allclose(cli_res["output_domain_max_mm_per_h"], a["output_domain_max_mm_per_h"])
        )
    else:
        cli_res["error"] = "precip_2d.nc not produced"
except Exception as e:
    cli_res["error"] = f"{type(e).__name__}: {e}"
print(f"[b_halfhourly_default_cli] rc={cli_res.get('returncode')} total_pc={cli_res.get('total_piecewise_constant_mm')} identical={cli_res.get('identical_to_dataarray_case')}")
OUT["cases"]["b_halfhourly_default_cli"] = cli_res

# (c) hourly, defaults (ERA5 case)
OUT["cases"]["c_hourly_default_dataarray"] = api_case(
    "c_hourly_default_dataarray", HR, [10, 10], "20170101 020000", lambda: make_da(HR, [10, 10])
)

# extra: half-hourly, cumulative_input=False, time_label='left'
OUT["cases"]["x_halfhourly_rate_left_dataarray"] = api_case(
    "x_halfhourly_rate_left_dataarray", HH, [10, 10, 10, 10], "20170101 020000", lambda: make_da(HH, [10, 10, 10, 10]),
    cumulative_input=False, time_label="left",
)

# supplementary pulses (isolate factor and offset without the end-of-series edge effect)
HH8 = [str(t) for t in pd.date_range("2017-01-01 00:00", periods=8, freq="30min")]
pulse8 = [0, 0, 10, 0, 0, 0, 0, 0]  # 10 mm/h only at 01:00
OUT["cases"]["p_halfhourly_pulse_default_dataarray"] = api_case(
    "p_halfhourly_pulse_default_dataarray", HH8, pulse8, "20170101 040000", lambda: make_da(HH8, pulse8)
)
HR4 = [str(t) for t in pd.date_range("2017-01-01 00:00", periods=4, freq="60min")]
pulse4 = [0, 10, 0, 0]  # 10 mm/h only at 01:00
OUT["cases"]["p_hourly_pulse_default_dataarray"] = api_case(
    "p_hourly_pulse_default_dataarray", HR4, pulse4, "20170101 040000", lambda: make_da(HR4, pulse4)
)
OUT["cases"]["p_halfhourly_pulse_rate_left_dataarray"] = api_case(
    "p_halfhourly_pulse_rate_left_dataarray", HH8, pulse8, "20170101 040000", lambda: make_da(HH8, pulse8),
    cumulative_input=False, time_label="left",
)

out_json = F5 / "F5_abc.json"
out_json.write_text(json.dumps(jsonable(OUT), indent=2), encoding="utf-8")
print(f"wrote {out_json}")
