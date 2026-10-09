"""F5-e: did the inverse-barometer (IB) sea-level response occur at the SFINCS open boundary?

Facts-only diagnostic over EXISTING runs (nothing is re-run). All inputs are opened read-only.
Outputs (written next to this script): F5_e.json, F5_e.md

Usage (sfincs-viz env):
  set GDAL_DATA=C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/Library/share/gdal
  python f5_e_ib.py

Conventions verified in the data (see JSON key `nan_is_dry_check`): the SFINCS map variable `zs`
is NaN where a cell is dry (at the first output time the finite msk==1 cells are exactly the
cells with zb < 0, zsini = 0). `zsmax` (daily maximum, tracked every internal time step) is NaN
where a cell was never wet in that window.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
import re
import json
import glob
import hashlib
import warnings
import datetime as dt

import numpy as np
import xarray as xr
from scipy import ndimage

warnings.filterwarnings("ignore", category=RuntimeWarning)   # nanmean of all-NaN slices is expected here

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "F5_e.json")
OUT_MD = os.path.join(HERE, "F5_e.md")

RHO = 1025.0          # kg m-3 (task specification; sfincs.inp uses rhow = 1024)
G = 9.81              # m s-2
P_REF_HPA = 1013.25   # standard atmosphere
RUNS = [
    {
        "key": "pineios_emsr692_enhanced",
        "label": "Run 1: Pineios / Storm Daniel (EMSR692) enhanced, model_author_ref",
        "folder": r"D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref",
        "log": "sfincs_log.txt",
    },
    {
        "key": "valencia_emsr773_asrun",
        "label": "Run 2a: Valencia (EMSR773) as-run, NHESS/runs/valencia_emsr773/model",
        "folder": r"D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model",
        "log": "sfincs_log.txt",
    },
    {
        "key": "valencia_emsr773_rerun_v164",
        "label": "Run 2b: Valencia (EMSR773) 164-mm re-run, R1_verification/task_valencia_anchor/rerun_v164/model",
        "folder": r"D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model",
        "log": "sfincs_stdout.txt",
    },
]
INP_KEYS = ["bndfile", "bzsfile", "bzifile", "netbndbzsbzifile", "pavbnd", "baro", "gapres",
            "netampfile", "netamuamvfile", "netamprfile", "tref", "tstart", "tstop", "zsini",
            "rhow", "tspinup", "dtout", "epsg"]
FILES_READ = {}   # path -> {size, md5}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def note_file(path):
    path = os.path.abspath(path)
    if path not in FILES_READ:
        FILES_READ[path] = {"size_bytes": os.path.getsize(path), "md5": md5(path)}
    return path


def _round(x, nd):
    if x is None:
        return None
    x = float(x)
    return None if np.isnan(x) else round(x, nd)


def f3(x):
    return _round(x, 3)


def f2(x):
    return _round(x, 2)


def f4(x):
    return _round(x, 4)


def tstr(t):
    return str(np.datetime_as_string(np.datetime64(t), unit="m"))


def parse_inp(path):
    note_file(path)
    kv = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip()
    return kv


def series_stats(z, time):
    """Stats of a (nt, ncell) water-level array that may contain NaN (= dry)."""
    nt, nc = z.shape
    finite = ~np.isnan(z)
    n_fin_t = finite.sum(axis=1)                 # wet cells per output time
    ever_wet = finite.any(axis=0)
    out = {
        "n_cells": int(nc),
        "n_cells_ever_wet_(finite_zs)": int(ever_wet.sum()),
        "n_cells_never_wet_(zs_NaN_at_all_times)": int((~ever_wet).sum()),
        "n_output_times": int(nt),
        "n_output_times_with_all_cells_NaN": int((n_fin_t == 0).sum()),
        "wet_cells_at_first_time": int(n_fin_t[0]),
        "wet_cells_max_over_time": int(n_fin_t.max()),
    }
    if ever_wet.any():
        mean_series = np.nanmean(z, axis=1)      # mean over wet cells; NaN when none wet
        ok = ~np.isnan(mean_series)
        idx = np.where(ok)[0]
        imin = int(idx[np.argmin(mean_series[ok])])
        imax = int(idx[np.argmax(mean_series[ok])])
        out["zs_wet_cell_mean_series_m"] = {
            "first": f4(mean_series[0]), "t_first": tstr(time[0]),
            "min": f4(mean_series[imin]), "t_min": tstr(time[imin]),
            "max": f4(mean_series[imax]), "t_max": tstr(time[imax]),
            "note": "argmin/argmax return the earliest time when the series is constant",
        }
        # deviation from each cell's first finite value
        first_val = np.array([z[finite[:, c], c][0] if finite[:, c].any() else np.nan for c in range(nc)])
        dev = z - first_val[None, :]
        absdev = np.abs(dev)
        rng = np.nanmax(z, axis=0) - np.nanmin(z, axis=0)
        rng_f = np.where(np.isnan(rng), -1.0, rng)
        ic = int(np.argmax(rng_f))
        zc = z[:, ic]
        fin_c = ~np.isnan(zc)
        out["max_excursion_cell_index"] = ic
        out["max_excursion_cell"] = {
            "zs_first_finite": f4(first_val[ic]), "t_first_finite": tstr(time[int(np.where(fin_c)[0][0])]),
            "zs_min": f4(np.nanmin(zc)), "t_min": tstr(time[int(np.nanargmin(np.where(fin_c, zc, np.inf)))]),
            "zs_max": f4(np.nanmax(zc)), "t_max": tstr(time[int(np.nanargmax(np.where(fin_c, zc, -np.inf)))]),
            "range_m": f4(rng[ic]), "n_times_wet": int(fin_c.sum()),
        }
        out["abs_max_zs_any_cell_any_time_m"] = f4(np.nanmax(np.abs(z)))
        out["max_abs_dev_from_first_finite_m"] = f4(np.nanmax(absdev))
        out["n_cells_with_dev_gt_1cm"] = int(np.sum(np.nanmax(absdev, axis=0) > 0.01))
        out["ever_differs_from_initial_by_gt_1cm"] = bool(np.nanmax(absdev) > 0.01)
        out["all_finite_values_exactly_zero"] = bool(np.all(z[finite] == 0.0))
        out["_mean_series"] = mean_series
    else:
        out["zs_wet_cell_mean_series_m"] = None
        out["max_excursion_cell"] = None
        out["ever_differs_from_initial_by_gt_1cm"] = None
        out["_mean_series"] = np.full(nt, np.nan)
    return out


def analyse_run(run):
    folder = run["folder"]
    res = {"label": run["label"], "folder": folder, "missing": []}

    # ---- 1. sfincs.inp keywords ---------------------------------------------------------
    inp_path = os.path.join(folder, "sfincs.inp")
    if not os.path.isfile(inp_path):
        res["missing"].append(inp_path)
        return res
    kv = parse_inp(inp_path)
    res["inp"] = {k: kv.get(k) for k in INP_KEYS}          # None => keyword absent
    res["inp_present_keys"] = [k for k in INP_KEYS if k in kv]
    res["inp_absent_keys"] = [k for k in INP_KEYS if k not in kv]
    bnd_like = []
    for pat in ("*.bnd", "*.bzs", "*.bzi", "*bnd*.nc", "*bzs*.nc"):
        bnd_like += [os.path.basename(p) for p in glob.glob(os.path.join(folder, pat))]
    res["waterlevel_boundary_files_in_folder"] = sorted(set(bnd_like))
    res["waterlevel_boundary_file_exists"] = bool(bnd_like) or any(
        kv.get(k) for k in ("bndfile", "bzsfile", "bzifile", "netbndbzsbzifile"))
    res["folder_listing"] = sorted(os.listdir(folder))

    log_path = os.path.join(folder, run["log"])
    if os.path.isfile(log_path):
        note_file(log_path)
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip("\n") for l in f]
        res["log_boundary_lines"] = [l.strip() for l in lines if re.search(r"[Bb]oundary", l)]
        res["log_processes"] = [l.strip() for l in lines if re.match(r"\s*(Atmospheric pressure|Wind|Precipitation)\s*:", l)]
        res["log_active_points"] = [l.strip() for l in lines if "Number of active" in l]
    else:
        res["missing"].append(log_path)

    # ---- 2. sfincs_map.nc: mask, zb, zs at boundary cells ---------------------------------
    map_path = os.path.join(folder, "sfincs_map.nc")
    if not os.path.isfile(map_path):
        res["missing"].append(map_path)
        return res
    note_file(map_path)
    ds = xr.open_dataset(map_path, chunks={"time": 1})
    ia = ds["inp"].attrs
    res["map_inp_attrs"] = {k: (ia[k].item() if hasattr(ia[k], "item") else ia[k])
                            for k in ("bndfile", "bzsfile", "bzifile", "netbndbzsbzifile", "netampfile",
                                      "pavbnd", "baro", "gapres", "bndtype", "zsini", "rhow", "tspinup",
                                      "tref", "tstart", "tstop", "epsg") if k in ia}
    msk = ds["msk"].values
    zb = ds["zb"].values
    X = ds["x"].values
    Y = ds["y"].values
    time = ds["time"].values
    nt = len(time)
    res["time"] = {"n": int(nt), "first": tstr(time[0]), "last": tstr(time[-1]),
                   "step_s": float((time[1] - time[0]) / np.timedelta64(1, "s"))}
    counts = {f"msk{v}": int(np.sum(msk == v)) for v in (0, 1, 2, 3)}
    counts["n_cells_total"] = int(msk.size)
    counts["active_1_2_3"] = counts["msk1"] + counts["msk2"] + counts["msk3"]
    res["mask_counts"] = counts
    edge = np.zeros(msk.shape, bool)
    edge[0, :] = edge[-1, :] = True
    edge[:, 0] = edge[:, -1] = True

    sel = {}
    for v in (2, 3):
        idx = np.argwhere(msk == v)
        if len(idx):
            sel[v] = (idx[:, 0], idx[:, 1])
    # first interior row: msk==1 cells 8-connected to a msk==2 cell
    adj = ndimage.binary_dilation(msk == 2, structure=np.ones((3, 3), bool)) & (msk == 1)
    idx = np.argwhere(adj)
    sel["adj"] = (idx[:, 0], idx[:, 1]) if len(idx) else None
    # interior sea cells
    idx = np.argwhere((msk == 1) & (zb < 0))
    sel["sea"] = (idx[:, 0], idx[:, 1]) if len(idx) else None

    series = {k: np.full((nt, len(sel[k][0])), np.nan) for k in sel if sel[k] is not None}
    zs_var = ds["zs"]
    nan_check = None
    for it in range(nt):
        sl = zs_var.isel(time=it).values            # one (n, m) slice, ~1-3 MB
        for k in series:
            series[k][it] = sl[sel[k]]
        if it == 0:
            fin1 = ~np.isnan(sl) & (msk == 1)
            nan_check = {
                "rule": "zs is NaN where the cell is dry: at the first output time (zsini=0) the finite msk==1 cells "
                        "must be exactly the msk==1 cells with zb<0",
                "finite_msk1_cells_at_t0": int(fin1.sum()),
                "msk1_cells_with_zb_lt_0": int(((msk == 1) & (zb < 0)).sum()),
                "sets_identical": bool(np.array_equal(fin1, (msk == 1) & (zb < 0))),
                "finite_msk1_zs_at_t0_abs_max_m": f4(np.nanmax(np.abs(sl[fin1]))) if fin1.any() else None,
            }
    zsmax = ds["zsmax"].values                          # (timemax, n, m)
    tmax = ds["timemax"].values
    ds.close()
    res["nan_is_dry_check"] = nan_check

    def zsmax_stats(ni, mi):
        v = zsmax[:, ni, mi]
        fin = ~np.isnan(v)
        return {"n_windows": int(v.shape[0]), "windows_end": [tstr(t) for t in tmax],
                "n_cell_windows": int(v.size), "n_finite": int(fin.sum()),
                "min": f4(v[fin].min()) if fin.any() else None, "max": f4(v[fin].max()) if fin.any() else None}

    def block(k, with_coords=True):
        ni, mi = sel[k]
        st = series_stats(series[k], time)
        zb_c = zb[ni, mi]
        st["zb_m"] = {"min": f3(zb_c.min()), "mean": f3(zb_c.mean()), "max": f3(zb_c.max())}
        st["n_cells_zb_lt_0"] = int((zb_c < 0).sum())
        st["n_cells_zb_eq_0"] = int((zb_c == 0).sum())
        st["n_cells_on_outer_grid_edge"] = int(edge[ni, mi].sum())
        st["x_range"] = [f2(X[ni, mi].min()), f2(X[ni, mi].max())]
        st["y_range"] = [f2(Y[ni, mi].min()), f2(Y[ni, mi].max())]
        st["zsmax_at_cells"] = zsmax_stats(ni, mi)
        if st.get("max_excursion_cell") is not None:
            ic = st.pop("max_excursion_cell_index")
            st["max_excursion_cell"].update({"n": int(ni[ic]), "m": int(mi[ic]), "x": f2(X[ni[ic], mi[ic]]),
                                             "y": f2(Y[ni[ic], mi[ic]]), "zb": f3(zb_c[ic])})
            st["_ic"] = ic
        return st

    res["bnd_msk2"] = block(2) if 2 in sel else None
    res["bnd_msk3"] = block(3) if 3 in sel else None
    res["adjacent_msk1_first_interior_row"] = block("adj") if sel["adj"] is not None else None
    res["interior_sea_msk1_zb_lt_0"] = block("sea") if sel["sea"] is not None else None

    # ---- 3. pressure forcing ---------------------------------------------------------------
    pfile = kv.get("netampfile")
    ppath = os.path.join(folder, pfile) if pfile else None
    if not ppath or not os.path.isfile(ppath):
        res["missing"].append(ppath or "netampfile keyword")
        return res
    note_file(ppath)
    dp = xr.open_dataset(ppath)
    pvar = [v for v in dp.data_vars if v != "spatial_ref"][0]
    P = dp[pvar].values.astype(np.float64)          # (time, y, x) in Pa
    ptime = dp["time"].values
    px = dp["x"].values
    py = dp["y"].values
    units = dp[pvar].attrs.get("units", dp.attrs.get("units"))
    wkt = dp["spatial_ref"].attrs.get("crs_wkt", "")
    grib = {k: dp.attrs.get(k) for k in ("GRIB_gridType", "GRIB_iDirectionIncrementInDegrees",
                                         "GRIB_latitudeOfFirstGridPointInDegrees", "GRIB_latitudeOfLastGridPointInDegrees",
                                         "GRIB_longitudeOfFirstGridPointInDegrees", "GRIB_longitudeOfLastGridPointInDegrees",
                                         "GRIB_dataType", "GRIB_shortName")}
    try:
        from pyproj import CRS
        p_epsg = CRS.from_wkt(wkt).to_epsg()
    except Exception:
        p_epsg = None
    dp.close()
    model_epsg = int(kv.get("epsg"))
    if units != "Pa":
        raise RuntimeError(f"unexpected pressure units {units}")
    P_h = P / 100.0
    same_time_axis = (len(ptime) == nt) and bool(np.all(ptime == time))
    dom_min = np.nanmin(P_h.reshape(len(ptime), -1), axis=1)
    k = int(np.nanargmin(dom_min))
    iy, ix = np.unravel_index(int(np.nanargmin(P_h[k])), P_h[k].shape)
    gapres_h = float(kv.get("gapres", "101200")) / 100.0

    def ib(p_min_h, p_ref_h):
        return f3(-(p_min_h - p_ref_h) * 100.0 / (RHO * G))

    def nn_series(ni, mi):
        xc, yc = X[ni, mi].astype(np.float64), Y[ni, mi].astype(np.float64)
        jx = np.abs(px[None, :] - xc[:, None]).argmin(axis=1)
        jy = np.abs(py[None, :] - yc[:, None]).argmin(axis=1)
        d = np.hypot(px[jx] - xc, py[jy] - yc)
        return P_h[:, jy, jx], jx, jy, d

    bnd_mean_p, kb = None, None
    if 2 in sel:
        pb, jx, jy, d = nn_series(*sel[2])
        bnd_mean_p = pb.mean(axis=1)
        kb = int(np.nanargmin(bnd_mean_p))
        nn = {"method": "nearest forcing-grid node to each msk==2 cell centre; both datasets are in the same "
                        "projected CRS (forcing file stored by HydroMT in the model EPSG), so no reprojection was needed",
              "forcing_epsg_from_wkt": p_epsg, "model_epsg": model_epsg,
              "n_forcing_nodes_used": int(len(set(zip(jx.tolist(), jy.tolist())))),
              "nn_distance_m": {"min": f2(d.min()), "max": f2(d.max())}}
    res["pressure"] = {
        "file": ppath, "variable": pvar, "units": units, "grib_source_attrs": grib,
        "grid": {"nx": int(len(px)), "ny": int(len(py)), "epsg": p_epsg,
                 "dx_m": f2(np.mean(np.diff(px))), "dy_m": f2(np.mean(np.diff(py))),
                 "x_range": [f2(px.min()), f2(px.max())], "y_range": [f2(py.min()), f2(py.max())]},
        "time": {"n": int(len(ptime)), "first": tstr(ptime[0]), "last": tstr(ptime[-1]),
                 "identical_to_map_time_axis": same_time_axis},
        "nan_count": int(np.sum(np.isnan(P))),
        "domain_min_series_hPa": {
            "p_first": f2(dom_min[0]), "p_min": f2(dom_min[k]), "t_min": tstr(ptime[k]),
            "x_at_min": f2(px[ix]), "y_at_min": f2(py[iy]), "p_max": f2(np.nanmax(dom_min)),
            "expected_IB_m": {"rel_first": ib(dom_min[k], dom_min[0]),
                              "rel_1013.25": ib(dom_min[k], P_REF_HPA),
                              "rel_gapres": ib(dom_min[k], gapres_h)},
        },
        "bnd_mean_series_hPa": None if bnd_mean_p is None else {
            "matching": nn,
            "p_first": f2(bnd_mean_p[0]), "p_min": f2(bnd_mean_p[kb]), "t_min": tstr(ptime[kb]),
            "p_max": f2(np.nanmax(bnd_mean_p)),
            "expected_IB_m": {"rel_first": ib(bnd_mean_p[kb], bnd_mean_p[0]),
                              "rel_1013.25": ib(bnd_mean_p[kb], P_REF_HPA),
                              "rel_gapres": ib(bnd_mean_p[kb], gapres_h)},
        },
        "constants": {"rho_kg_m3": RHO, "g_m_s2": G, "p_ref_hPa": P_REF_HPA, "gapres_hPa": gapres_h,
                      "note": "sfincs.inp rhow=1024 (model) vs rho=1025 used here as specified"},
    }

    # ---- 4./5. comparison at the MSLP minimum (boundary, first interior row, interior sea) --
    if kb is not None:
        it = int(np.argmin(np.abs(time - ptime[kb])))
        exp_first = res["pressure"]["bnd_mean_series_hPa"]["expected_IB_m"]["rel_first"]
        exp_1013 = res["pressure"]["bnd_mean_series_hPa"]["expected_IB_m"]["rel_1013.25"]
        cmp_ = {"t_mslp_min_bnd_mean": tstr(ptime[kb]), "map_time_used": tstr(time[it]),
                "expected_IB_rel_first_m": exp_first, "expected_IB_rel_1013.25_m": exp_1013}
        for k2, name in (("2", "bnd_msk2"), ("adj", "adjacent_msk1_first_interior_row"), ("sea", "interior_sea_msk1_zb_lt_0")):
            key = 2 if k2 == "2" else k2
            blk = res.get(name)
            if blk is None or key not in series:
                continue
            z = series[key]
            ms = blk["_mean_series"]
            ic = blk.get("_ic")
            fin_t = ~np.isnan(z[it])
            z0 = z[0]
            dz = z[it] - z0
            okd = ~np.isnan(dz)
            # local expected IB (nearest forcing node) relative to the first forcing step
            ploc, _, _, _ = nn_series(*sel[key])
            exp_loc = -(ploc[kb] - ploc[0]) * 100.0 / (RHO * G)
            entry = {
                "n_cells": int(z.shape[1]), "wet_cells_at_t": int(fin_t.sum()), "wet_cells_at_t0": int((~np.isnan(z0)).sum()),
                "cells_wet_at_both_t0_and_t": int(okd.sum()),
                "zs_wet_mean_at_t_m": f3(ms[it]),
                "zs_at_t_cellwise_m": {"min": f3(np.nanmin(z[it])) if fin_t.any() else None,
                                       "max": f3(np.nanmax(z[it])) if fin_t.any() else None},
                "observed_dzs_wet_mean_at_t_m": f3(ms[it] - ms[0]) if not (np.isnan(ms[it]) or np.isnan(ms[0])) else None,
                "observed_dzs_cellwise_m": {"mean": f3(np.nanmean(dz)) if okd.any() else None,
                                            "min": f3(np.nanmin(dz)) if okd.any() else None,
                                            "max": f3(np.nanmax(dz)) if okd.any() else None,
                                            "n_abs_gt_1cm": int(np.sum(np.abs(dz[okd]) > 0.01))},
                "observed_dzs_wet_mean_min_over_run_m": f3(np.nanmin(ms - ms[0])) if not np.isnan(ms[0]) else None,
                "observed_dzs_wet_mean_max_over_run_m": f3(np.nanmax(ms - ms[0])) if not np.isnan(ms[0]) else None,
                "expected_local_IB_rel_first_m": {"mean": f3(exp_loc.mean()), "min": f3(exp_loc.min()), "max": f3(exp_loc.max())},
            }
            if ic is not None:
                entry["observed_dzs_max_excursion_cell_at_t_m"] = f3(z[it, ic] - z0[ic]) if not (np.isnan(z[it, ic]) or np.isnan(z0[ic])) else None
            if np.any(~np.isnan(ms)):
                imx = int(np.nanargmax(ms))
                entry["at_time_of_wet_mean_max"] = {
                    "t": tstr(time[imx]), "zs_wet_mean_m": f3(ms[imx]),
                    "hours_after_mslp_min": float((time[imx] - ptime[kb]) / np.timedelta64(1, "h")),
                    "p_bnd_mean_hPa": f2(bnd_mean_p[imx]),
                    "expected_IB_rel_first_m": ib(bnd_mean_p[imx], bnd_mean_p[0]),
                }
            cmp_[name] = entry
        # 6-hourly checkpoints: boundary-mean MSLP vs water levels next to / inside the boundary
        ms_adj = res["adjacent_msk1_first_interior_row"]["_mean_series"] if res.get("adjacent_msk1_first_interior_row") else None
        ms_sea = res["interior_sea_msk1_zb_lt_0"]["_mean_series"] if res.get("interior_sea_msk1_zb_lt_0") else None
        cps = []
        for jt in range(0, nt, 6):
            cps.append({"t": tstr(time[jt]), "p_bnd_mean_hPa": f2(bnd_mean_p[jt]),
                        "expected_IB_rel_first_m": ib(bnd_mean_p[jt], bnd_mean_p[0]),
                        "zs_first_interior_row_wet_mean_m": f3(ms_adj[jt]) if ms_adj is not None else None,
                        "wet_cells_first_interior_row": int((~np.isnan(series["adj"][jt])).sum()) if "adj" in series else None,
                        "zs_interior_sea_wet_mean_m": f3(ms_sea[jt]) if ms_sea is not None else None})
        cmp_["checkpoints_6h"] = cps
        b = res["bnd_msk2"]
        if b is not None:
            if b["n_cells_ever_wet_(finite_zs)"] == 0:
                acted = False
                evidence = (f"all {b['n_cells']} msk==2 cells have zb = {b['zb_m']['max']} m and zs = NaN (dry) at all "
                            f"{b['n_output_times']} hourly outputs; zsmax NaN in all {b['zsmax_at_cells']['n_cell_windows']} "
                            f"cell-windows (never wet within any dtmaxout = 86400 s window). The imposed boundary level therefore never "
                            f"exceeded {b['zb_m']['max']} m, while the IB expected at the MSLP minimum is {exp_first} m "
                            f"(rel. first step) / {exp_1013} m (rel. 1013.25 hPa).")
            else:
                mx = b["max_abs_dev_from_first_finite_m"]
                acted = bool(mx is not None and mx > 0.01)
                evidence = (f"{b['n_cells_ever_wet_(finite_zs)']} of {b['n_cells']} msk==2 cells are wet; their zs is "
                            f"{'exactly 0.0' if b['all_finite_values_exactly_zero'] else 'not all zero'} at every output time "
                            f"(max |dzs| from initial {mx} m); zsmax at the wet cells min {b['zsmax_at_cells']['min']} / max "
                            f"{b['zsmax_at_cells']['max']} m over every dtmaxout = 86400 s window, versus expected IB {exp_first} m "
                            f"(rel. first) / {exp_1013} m (rel. 1013.25 hPa).")
            cmp_["pavbnd_acted_at_boundary_per_data"] = acted
            cmp_["evidence"] = evidence
        res["comparison"] = cmp_
    for name in ("bnd_msk2", "bnd_msk3", "adjacent_msk1_first_interior_row", "interior_sea_msk1_zb_lt_0"):
        if res.get(name):
            res[name].pop("_mean_series", None)
            res[name].pop("_ic", None)
    mmax, nmax, dx, dy = int(kv["mmax"]), int(kv["nmax"]), float(kv["dx"]), float(kv["dy"])
    x0, y0 = float(kv["x0"]), float(kv["y0"])
    res["model_grid_extent_m"] = {"x": [x0, x0 + mmax * dx], "y": [y0, y0 + nmax * dy], "mmax": mmax, "nmax": nmax, "dx": dx, "dy": dy}
    return res


def build_md(J):
    L = []
    L.append("# F5-e: inverse-barometer response at the SFINCS open boundary (facts only)")
    L.append(f"Generated {J['generated_utc']} by `f5_e_ib.py` from existing outputs; no model was re-run. "
             f"IB = -dp/(rho g), rho = {J['constants']['rho_kg_m3']} kg/m3, g = {J['constants']['g_m_s2']} m/s2; "
             f"references: first forcing step, {J['constants']['p_ref_hPa']} hPa, gapres from sfincs.inp. "
             "SFINCS writes `zs` = NaN where a cell is dry (verified per run, row 'NaN = dry check'). "
             "Every number below is copied from `F5_e.json`.")
    for key, r in J["runs"].items():
        L.append("")
        L.append(f"## {r['label']}")
        if r.get("missing"):
            L.append(f"Missing: {r['missing']}")
        if "inp" not in r or "pressure" not in r:
            continue
        inp = r["inp"]
        L.append("| Item | Value |")
        L.append("|---|---|")
        kw = ", ".join(f"{k}={inp[k]}" for k in ("baro", "pavbnd", "gapres", "zsini", "rhow", "tspinup", "tref", "tstart",
                                                 "tstop", "epsg", "netampfile", "netamuamvfile", "netamprfile") if inp.get(k) is not None)
        L.append(f"| sfincs.inp keywords present | {kw} |")
        L.append(f"| sfincs.inp keywords ABSENT | {', '.join(r['inp_absent_keys'])} |")
        m = r["map_inp_attrs"]
        L.append(f"| water-level boundary file (bnd/bzs/bzi) | exists in folder: {r['waterlevel_boundary_file_exists']} "
                 f"(matching files: {r['waterlevel_boundary_files_in_folder'] or 'none'}); sfincs_map.nc `inp` attrs: "
                 f"bndfile={m.get('bndfile')}, bzsfile={m.get('bzsfile')}, bzifile={m.get('bzifile')}, "
                 f"netbndbzsbzifile={m.get('netbndbzsbzifile')}, bndtype={m.get('bndtype')}, pavbnd={m.get('pavbnd')}, baro={m.get('baro')} |")
        L.append(f"| SFINCS run log | {' / '.join(r.get('log_boundary_lines', []))}; {'; '.join(r.get('log_processes', []))} |")
        c = r["mask_counts"]
        L.append(f"| mask counts | msk=1: {c['msk1']}, msk=2: {c['msk2']}, msk=3: {c['msk3']}, msk=0: {c['msk0']} "
                 f"(active {c['active_1_2_3']} of {c['n_cells_total']}) |")
        t = r["time"]
        nc_ = r["nan_is_dry_check"]
        L.append(f"| map output / NaN = dry check | {t['n']} steps, {t['first']} to {t['last']}, step {t['step_s']} s; at t0 finite msk=1 cells = "
                 f"{nc_['finite_msk1_cells_at_t0']}, msk=1 cells with zb<0 = {nc_['msk1_cells_with_zb_lt_0']}, identical sets: {nc_['sets_identical']} |")
        b = r["bnd_msk2"]
        if b:
            zm = b["zsmax_at_cells"]
            L.append(f"| msk=2 cells: zb (m), wet/dry | zb min {b['zb_m']['min']}, mean {b['zb_m']['mean']}, max {b['zb_m']['max']} "
                     f"({b['n_cells_zb_lt_0']} cells zb<0, {b['n_cells_zb_eq_0']} cells zb=0; {b['n_cells_on_outer_grid_edge']} on outer grid edge); "
                     f"cells ever wet (finite zs): {b['n_cells_ever_wet_(finite_zs)']}, never wet: {b['n_cells_never_wet_(zs_NaN_at_all_times)']}; "
                     f"output times with all msk=2 NaN: {b['n_output_times_with_all_cells_NaN']} of {b['n_output_times']} |")
            L.append(f"| msk=2 zsmax (maximum over each dtmaxout = 86400 s window, {zm['n_windows']} windows) | finite {zm['n_finite']} of "
                     f"{zm['n_cell_windows']} cell-windows; min {zm['min']}, max {zm['max']} m |")
            s = b["zs_wet_cell_mean_series_m"]
            if s:
                e = b["max_excursion_cell"]
                L.append(f"| zs at wet msk=2 cells (m) | mean: first {s['first']} ({s['t_first']}), min {s['min']} ({s['t_min']}), max {s['max']} ({s['t_max']}); "
                         f"largest-excursion cell n={e['n']}, m={e['m']}, x={e['x']}, y={e['y']}, zb={e['zb']}: first {e['zs_first_finite']}, "
                         f"min {e['zs_min']} ({e['t_min']}), max {e['zs_max']} ({e['t_max']}), range {e['range_m']}; "
                         f"max abs dev from initial {b['max_abs_dev_from_first_finite_m']} m; differs > 1 cm: {b['ever_differs_from_initial_by_gt_1cm']}; "
                         f"all finite values exactly 0: {b['all_finite_values_exactly_zero']} |")
            else:
                L.append("| zs at msk=2 cells (m) | NaN at every cell and every output time (no wet boundary cell at any output hour); "
                         "first/min/max/time-of-min/max undefined; deviation from initial undefined (upper bound: level <= zb at all times) |")
        else:
            L.append("| msk=2 cells | none |")
        if r.get("bnd_msk3"):
            b3 = r["bnd_msk3"]
            L.append(f"| msk=3 cells | {b3['n_cells']} cells; ever wet {b3['n_cells_ever_wet_(finite_zs)']} |")
        p = r["pressure"]; dm = p["domain_min_series_hPa"]; bm = p["bnd_mean_series_hPa"]; g = p["grib_source_attrs"]; ge = r["model_grid_extent_m"]
        L.append(f"| MSLP forcing file | {os.path.basename(p['file'])}: `{p['variable']}` [{p['units']}], {p['grid']['nx']}x{p['grid']['ny']} nodes, "
                 f"EPSG {p['grid']['epsg']} (model EPSG {inp.get('epsg')}), dx {p['grid']['dx_m']} m, dy {p['grid']['dy_m']} m, "
                 f"source {g.get('GRIB_shortName')} {g.get('GRIB_gridType')} {g.get('GRIB_iDirectionIncrementInDegrees')} deg; "
                 f"{p['time']['n']} steps, time axis identical to map: {p['time']['identical_to_map_time_axis']}, NaNs {p['nan_count']}; "
                 f"forcing nodes span x {p['grid']['x_range'][0]}-{p['grid']['x_range'][1]}, y {p['grid']['y_range'][0]}-{p['grid']['y_range'][1]} m "
                 f"vs model grid x {ge['x'][0]}-{ge['x'][1]}, y {ge['y'][0]}-{ge['y'][1]} m ('domain minimum' below = over the forcing nodes) |")
        L.append(f"| MSLP domain minimum (hPa) | first {dm['p_first']} -> min {dm['p_min']} at {dm['t_min']} (x={dm['x_at_min']}, y={dm['y_at_min']}), "
                 f"max {dm['p_max']}; expected IB {dm['expected_IB_m']['rel_first']} m rel. first, {dm['expected_IB_m']['rel_1013.25']} m rel. 1013.25, "
                 f"{dm['expected_IB_m']['rel_gapres']} m rel. gapres {p['constants']['gapres_hPa']} |")
        if bm:
            L.append(f"| MSLP mean at msk=2 locations (hPa) | first {bm['p_first']} -> min {bm['p_min']} at {bm['t_min']}, max {bm['p_max']} "
                     f"({bm['matching']['n_forcing_nodes_used']} forcing nodes, nearest-node distance {bm['matching']['nn_distance_m']['min']}-"
                     f"{bm['matching']['nn_distance_m']['max']} m, same CRS); expected IB {bm['expected_IB_m']['rel_first']} m rel. first, "
                     f"{bm['expected_IB_m']['rel_1013.25']} m rel. 1013.25, {bm['expected_IB_m']['rel_gapres']} m rel. gapres |")
        cm = r.get("comparison")
        if cm:
            cb = cm.get("bnd_msk2")
            if cb:
                L.append(f"| observed dzs at msk=2 at MSLP min ({cm['t_mslp_min_bnd_mean']}) | wet cells at t: {cb['wet_cells_at_t']} of {cb['n_cells']}; "
                         f"dzs wet-cell mean {cb['observed_dzs_wet_mean_at_t_m']} m, cellwise mean/min/max {cb['observed_dzs_cellwise_m']['mean']}/"
                         f"{cb['observed_dzs_cellwise_m']['min']}/{cb['observed_dzs_cellwise_m']['max']} m, largest-excursion cell "
                         f"{cb.get('observed_dzs_max_excursion_cell_at_t_m')} m; run-wide mean dzs range [{cb['observed_dzs_wet_mean_min_over_run_m']}, "
                         f"{cb['observed_dzs_wet_mean_max_over_run_m']}] m; expected {cm['expected_IB_rel_first_m']} m (rel. first) / "
                         f"{cm['expected_IB_rel_1013.25_m']} m (rel. 1013.25) |")
            ca = cm.get("adjacent_msk1_first_interior_row")
            if ca:
                a = r["adjacent_msk1_first_interior_row"]; sa = a["zs_wet_cell_mean_series_m"]
                L.append(f"| first interior row (msk=1 cells touching msk=2) | {a['n_cells']} cells, zb {a['zb_m']['min']}..{a['zb_m']['max']} m; "
                         f"wet at t0 {ca['wet_cells_at_t0']}, at MSLP min {ca['wet_cells_at_t']}; zs at MSLP min: wet-mean {ca['zs_wet_mean_at_t_m']} m, "
                         f"cellwise {ca['zs_at_t_cellwise_m']['min']}..{ca['zs_at_t_cellwise_m']['max']} m; dzs vs t0 (cells wet at both) mean/min/max "
                         f"{ca['observed_dzs_cellwise_m']['mean']}/{ca['observed_dzs_cellwise_m']['min']}/{ca['observed_dzs_cellwise_m']['max']} m "
                         f"({ca['observed_dzs_cellwise_m']['n_abs_gt_1cm']} cells > 1 cm); wet-mean zs series min {sa['min']} ({sa['t_min']}), "
                         f"max {sa['max']} ({sa['t_max']}) m; expected local IB rel. first mean {ca['expected_local_IB_rel_first_m']['mean']} m |")
            cs = cm.get("interior_sea_msk1_zb_lt_0")
            if cs:
                sidx = r["interior_sea_msk1_zb_lt_0"]; ss = sidx["zs_wet_cell_mean_series_m"]
                L.append(f"| interior sea cells (msk=1 & zb<0) at MSLP min | {sidx['n_cells']} cells, zb {sidx['zb_m']['min']}..{sidx['zb_m']['max']} m, "
                         f"wet at t: {cs['wet_cells_at_t']}; dzs wet-mean {cs['observed_dzs_wet_mean_at_t_m']} m, cellwise mean/min/max "
                         f"{cs['observed_dzs_cellwise_m']['mean']}/{cs['observed_dzs_cellwise_m']['min']}/{cs['observed_dzs_cellwise_m']['max']} m "
                         f"({cs['observed_dzs_cellwise_m']['n_abs_gt_1cm']} cells > 1 cm); expected local IB rel. first mean "
                         f"{cs['expected_local_IB_rel_first_m']['mean']} m (min {cs['expected_local_IB_rel_first_m']['min']}, max "
                         f"{cs['expected_local_IB_rel_first_m']['max']}); wet-mean zs series first {ss['first']}, min {ss['min']} ({ss['t_min']}), "
                         f"max {ss['max']} ({ss['t_max']}) m, i.e. {cs['at_time_of_wet_mean_max']['hours_after_mslp_min']:+.1f} h relative to the MSLP min, "
                         f"when boundary MSLP was {cs['at_time_of_wet_mean_max']['p_bnd_mean_hPa']} hPa (expected IB {cs['at_time_of_wet_mean_max']['expected_IB_rel_first_m']} m) |")
            cps = cm.get("checkpoints_6h", [])
            pick = [c for i, c in enumerate(cps) if i in (2, 4, 6, 8)]
            L.append("| 6-hourly checkpoints (t: boundary MSLP hPa / expected IB m / first-row wet-mean zs m (wet cells) / interior-sea wet-mean zs m) | "
                     + "; ".join(f"{c['t']}: {c['p_bnd_mean_hPa']} / {c['expected_IB_rel_first_m']} / {c['zs_first_interior_row_wet_mean_m']} "
                                 f"({c['wet_cells_first_interior_row']}) / {c['zs_interior_sea_wet_mean_m']}" for c in pick)
                     + " (full list in JSON) |")
            L.append(f"| pavbnd acted at the boundary (per data)? | {cm.get('pavbnd_acted_at_boundary_per_data')}: {cm.get('evidence')} |")
        if key == "valencia_emsr773_rerun_v164":
            fr = J["files_read"]
            same = [os.path.basename(a) for a in fr for b in fr
                    if a != b and "rerun_v164" in a and "runs\\valencia_emsr773" in b
                    and os.path.basename(a) == os.path.basename(b) and fr[a]["md5"] == fr[b]["md5"]]
            L.append(f"| identity with Run 2a (md5) | byte-identical files: {same}; sfincs_map.nc differs "
                     f"({fr[[a for a in fr if 'rerun_v164' in a and a.endswith('sfincs_map.nc')][0]]['size_bytes']} vs "
                     f"{fr[[a for a in fr if 'runs' + chr(92) + 'valencia_emsr773' in a and a.endswith('sfincs_map.nc')][0]]['size_bytes']} bytes) |")
    L.append("")
    L.append("## Files read (read-only; sizes and md5 in F5_e.json)")
    for pth in J["files_read"]:
        L.append(f"- `{pth}`")
    L.append("- Inspected manually before scripting (no numbers taken from them): "
             + ", ".join(f"`{e}`" for e in J.get("files_inspected_manually", [])))
    return "\n".join(L) + "\n"


def main():
    J = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "script": os.path.abspath(__file__),
        "constants": {"rho_kg_m3": RHO, "g_m_s2": G, "p_ref_hPa": P_REF_HPA},
        "runs": {},
    }
    for run in RUNS:
        print(f"--- {run['key']}")
        J["runs"][run["key"]] = analyse_run(run)
    J["files_read"] = FILES_READ
    J["files_inspected_manually"] = [
        r"D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\hydromt.log",
        r"D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\sfincs.src",
        r"D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\hydromt.log",
        r"D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\sfincs.src",
        r"D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\sfincs.src",
    ]
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(J, f, indent=1, ensure_ascii=False)
    with open(OUT_JSON, "r", encoding="utf-8") as f:
        J2 = json.load(f)                       # MD is rendered from the JSON as written
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(build_md(J2))
    print("wrote", OUT_JSON)
    print("wrote", OUT_MD)


if __name__ == "__main__":
    main()
