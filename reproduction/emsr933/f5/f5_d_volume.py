"""F5-d: rainfall depth actually written to the SFINCS precipitation forcing of the as-run models.

Facts only. Reads (read-only, never writes to them):
  * <model>/sfincs.inp               -> tref/tstart/tstop, netamprfile, grid (x0,y0,dx,dy,mmax,nmax,epsg)
  * <model>/precip_2d.nc             -> the netamprfile SFINCS read (variable 'Precipitation', mm/h)
  * <model>/sfincs_map.nc            -> 'msk', 'x', 'y' only (active-cell weights); it holds no rainfall variable
  * <data>/imerg_<slug>.nc           -> bias-corrected IMERG fed to hydromt (mm/h, 30-min stamps, lat/lon 0.1 deg)
  * <data>/imerg_<slug>.raw.nc       -> raw IMERG backup written by bias_correct_imerg.py
Writes F5_d.json and F5_d.md next to this script. No model is run.

Integration rules (all totals in mm, rate in mm/h, dt from the file's time axis):
  pc_fwd : piecewise-constant, rate at stamp t holds over [t, t+dt)  -> sum(rate_i * dt) over T0 <= t_i <  T1
           (this is the SFINCS convention, amprblock=1, and the IMERG convention: stamp = start of the 30-min slot)
  trap   : trapezoidal over stamps T0 <= t_i <= T1                   -> sum((r_i + r_i+1)/2 * dt)
  incl   : inclusive-stamp sum, T0 <= t_i <= T1, times dt            -> the rule used by bias_correct_imerg.py
Region means are means of the per-step spatial mean over the selected cells (nanmean), then integrated.

Run:
  set GDAL_DATA=C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/Library/share/gdal
  C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/python.exe -I f5_d_volume.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hashlib
import json
import os
import re
from datetime import datetime

import netCDF4
import numpy as np
from pyproj import CRS, Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "F5_d.json")
OUT_MD = os.path.join(HERE, "F5_d.md")

IMPL = r"D:\ELKAK\implementation"
NHESS = r"D:\ELKAK\ELKAK2\NHESS"
VAL_RUN = os.path.join(NHESS, "runs", "valencia_emsr773")
VAL_164 = os.path.join(NHESS, "R1_verification", "task_valencia_anchor", "rerun_v164")

RUNS = [
    dict(
        key="pineios_enhanced",
        event="Pineios / Storm Daniel (EMSR692), enhanced",
        model_dir=os.path.join(IMPL, "pineios_sfincs_enhanced", "model_author_ref"),
        duplicate_model_dirs=[os.path.join(IMPL, "pineios_sfincs_enhanced", "model")],
        imerg_bc=os.path.join(IMPL, "pineios_sfincs_enhanced", "data", "imerg_pineios.nc"),
        imerg_raw=os.path.join(IMPL, "pineios_sfincs_enhanced", "data", "imerg_pineios.raw.nc"),
        window=("2023-09-04T00:00:00", "2023-09-08T00:00:00"),
        bbox=(22.0, 39.4, 22.95, 40.0),
        targets_mm={"configured_400": 400.0, "manuscript_380": 380.0},
    ),
    dict(
        key="mandra_enhanced",
        event="Mandra (EMSR257), enhanced",
        model_dir=os.path.join(IMPL, "mandra_sfincs_enhanced", "model_author_ref"),
        duplicate_model_dirs=[os.path.join(IMPL, "mandra_sfincs_enhanced", "model")],
        imerg_bc=os.path.join(IMPL, "mandra_sfincs_enhanced", "data", "imerg_mandra.nc"),
        imerg_raw=os.path.join(IMPL, "mandra_sfincs_enhanced", "data", "imerg_mandra.raw.nc"),
        window=("2017-11-14T00:00:00", "2017-11-16T00:00:00"),
        bbox=(23.40, 38.05, 23.55, 38.15),
        targets_mm={"configured_200": 200.0},
    ),
    dict(
        key="valencia_350_asrun",
        event="Valencia (EMSR773), as-run 350-mm anchor",
        model_dir=os.path.join(VAL_RUN, "model"),
        duplicate_model_dirs=[],
        imerg_bc=os.path.join(VAL_RUN, "data", "imerg_valencia.nc"),
        imerg_raw=os.path.join(VAL_RUN, "data", "imerg_valencia.raw.nc"),
        window=("2024-10-29T00:00:00", "2024-10-30T00:00:00"),
        bbox=(-0.75, 39.33, -0.30, 39.55),
        targets_mm={"run_target_350": 350.0, "cited_164": 164.0},
    ),
    dict(
        key="valencia_164_rerun",
        event="Valencia (EMSR773), 164-mm re-run (rerun_v164)",
        model_dir=os.path.join(VAL_164, "model"),
        duplicate_model_dirs=[],
        # rerun_v164 has no data/ folder and no IMERG nc of its own (checked: only model/); the only IMERG
        # inputs on disk for Valencia are those of the 350-mm run folder.
        imerg_bc=os.path.join(VAL_RUN, "data", "imerg_valencia.nc"),
        imerg_raw=os.path.join(VAL_RUN, "data", "imerg_valencia.raw.nc"),
        imerg_note="rerun_v164/ holds no data/ folder and no imerg nc; the 350-mm run's imerg_valencia.nc "
                   "(x4.143 -> 350 mm) and imerg_valencia.raw.nc are the only IMERG inputs on disk for Valencia.",
        window=("2024-10-29T00:00:00", "2024-10-30T00:00:00"),
        bbox=(-0.75, 39.33, -0.30, 39.55),
        targets_mm={"run_target_164": 164.0, "old_target_350": 350.0},
        compare_precip_with=os.path.join(VAL_RUN, "model", "precip_2d.nc"),
    ),
]

FILES_READ = []
MISSING = []


# ----------------------------------------------------------------------------- helpers
def fileinfo(path, hash_limit_bytes=20_000_000):
    d = {"path": path, "exists": os.path.exists(path)}
    if d["exists"]:
        st = os.stat(path)
        d["size_bytes"] = st.st_size
        d["mtime"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
        if st.st_size <= hash_limit_bytes:
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            d["sha256"] = h.hexdigest()
    if path not in [f["path"] for f in FILES_READ]:
        FILES_READ.append(d)
    if not d["exists"]:
        MISSING.append(path)
    return d


def f(x, nd=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def parse_inp(path):
    out = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def sfincs_time(s):
    return np.datetime64(datetime.strptime(s, "%Y%m%d %H%M%S").isoformat(), "ns")


def decode_times(var, calendar=None):
    attrs = {k: var.getncattr(k) for k in var.ncattrs()}
    units = str(attrs.get("units") or attrs.get("Units"))
    cal = calendar or str(attrs.get("calendar", "standard"))
    vals = np.asarray(var[:], dtype="float64")
    try:
        dts = netCDF4.num2date(vals, units, cal)
    except Exception:
        units = str(attrs.get("Units", units)).replace(" UTC", "")
        dts = netCDF4.num2date(vals, units, cal)
    iso = [d.isoformat() for d in np.atleast_1d(dts)]
    return iso, units, cal


def to_dt64(iso_list):
    return np.array(iso_list, dtype="datetime64[ns]")


def uniform_dt_hours(times):
    d = np.unique(np.diff(times))
    return float(d[0] / np.timedelta64(1, "h")), [float(x / np.timedelta64(1, "m")) for x in d]


def time_summary(times):
    dt_h, steps_min = uniform_dt_hours(times)
    return dict(first=str(times[0])[:19], last=str(times[-1])[:19], count=int(times.size),
                step_minutes=steps_min[0] if len(steps_min) == 1 else steps_min, uniform=len(steps_min) == 1,
                span_hours=float((times[-1] - times[0]) / np.timedelta64(1, "h")))


def window_totals(times, series, t0, t1):
    """series: spatial-mean rate (mm/h) per stamp."""
    dt_h, _ = uniform_dt_hours(times)
    fwd = (times >= t0) & (times < t1)
    incl = (times >= t0) & (times <= t1)
    idx = np.where(incl)[0]
    out = dict(T0=str(t0)[:19], T1=str(t1)[:19], dt_hours=dt_h,
               file_covers_window=bool(times.min() <= t0 and times.max() >= t1),
               n_stamps_pc_fwd=int(fwd.sum()), total_pc_fwd_mm=float(np.nansum(series[fwd]) * dt_h),
               n_stamps_incl=int(incl.sum()), total_incl_mm=float(np.nansum(series[incl]) * dt_h))
    if idx.size >= 2:
        s = series[idx]
        out["n_intervals_trap"] = int(idx.size - 1)
        out["total_trap_mm"] = float(np.nansum((s[:-1] + s[1:]) / 2.0) * dt_h)
    else:
        out["n_intervals_trap"] = 0
        out["total_trap_mm"] = None
    return out


def whole_file_totals(times, series):
    dt_h, _ = uniform_dt_hours(times)
    return dict(n_stamps=int(times.size), dt_hours=dt_h,
                total_pc_fwd_mm=float(np.nansum(series) * dt_h),
                total_trap_mm=float(np.nansum((series[:-1] + series[1:]) / 2.0) * dt_h))


def region_series(data, mask):
    sub = data[:, mask]
    with np.errstate(all="ignore"):
        ser = np.nanmean(sub, axis=1)
    return ser, int(mask.sum()), int(np.isnan(sub).sum())


def parse_bias_attr(s):
    m = re.search(r"scaling ([\d.]+)x applied to event window (\S+ \S+) to (\S+ \S+) so watershed bbox "
                  r"\(([^)]*)\) 24-h total matches ([\d.]+) mm", str(s))
    if not m:
        return None
    return dict(factor=float(m.group(1)), window_start=m.group(2).replace(" ", "T"),
                window_end=m.group(3).replace(" ", "T"),
                bbox=[float(x) for x in m.group(4).split(",")], target_mm=float(m.group(5)))


def runs_of(values, stamps, nd=3):
    """Compress a per-frame sequence into runs of equal (rounded) value."""
    runs = []
    cur = None
    for v, t in zip(values, stamps):
        key = None if (v is None or not np.isfinite(v)) else round(float(v), nd)
        if cur is not None and cur["value"] == key:
            cur["end"] = str(t)[:19]
            cur["n_frames"] += 1
        else:
            cur = dict(value=key, start=str(t)[:19], end=str(t)[:19], n_frames=1)
            runs.append(cur)
    return runs


# ----------------------------------------------------------------------------- readers
def read_model_precip(path, inp):
    info = fileinfo(path)
    ds = netCDF4.Dataset(path, "r")
    var_name = "Precipitation" if "Precipitation" in ds.variables else next(
        n for n, v in ds.variables.items() if v.ndim == 3)
    v = ds.variables[var_name]
    iso, tunits, tcal = decode_times(ds.variables["time"])
    times = to_dt64(iso)
    x = np.asarray(ds.variables["x"][:], dtype="float64")
    y = np.asarray(ds.variables["y"][:], dtype="float64")
    data = np.asarray(v[:], dtype="float64")
    if np.ma.isMaskedArray(v[:]):
        data = np.asarray(np.ma.filled(v[:], np.nan), dtype="float64")
    crs = None
    if "spatial_ref" in ds.variables:
        sr = ds.variables["spatial_ref"]
        wkt = sr.getncattr("crs_wkt") if "crs_wkt" in sr.ncattrs() else sr.getncattr("spatial_ref")
        crs = CRS.from_wkt(wkt)
    if crs is None:
        crs = CRS.from_epsg(int(inp["epsg"]))
    gattrs = {k: str(ds.getncattr(k)) for k in ds.ncattrs()}
    vattrs = {k: str(v.getncattr(k)) for k in v.ncattrs()}
    vdims, vshape = list(v.dimensions), list(v.shape)
    ds.close()
    tr = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
    X, Y = np.meshgrid(x, y)
    lon2d, lat2d = tr.transform(X, Y)
    return dict(
        file=info, var_name=var_name, units=vattrs.get("units"), long_name=vattrs.get("long_name"),
        global_attrs=gattrs, dims=vdims, shape=vshape,
        crs_name=crs.name, epsg=crs.to_epsg(), coordinate_names=["time", "y", "x"], projected=crs.is_projected,
        x_first=float(x[0]), x_last=float(x[-1]), dx_m=float(x[1] - x[0]),
        y_first=float(y[0]), y_last=float(y[-1]), dy_m=float(y[1] - y[0]),
        lonlat_extent_of_cell_centres=dict(lon_min=float(lon2d.min()), lon_max=float(lon2d.max()),
                                           lat_min=float(lat2d.min()), lat_max=float(lat2d.max())),
        time_units=tunits, time_calendar=tcal, time=time_summary(times),
        n_nan=int(np.isnan(data).sum()), n_negative=int((data < 0).sum()),
        max_rate_mm_h=float(np.nanmax(data)), last_frame_max_mm_h=float(np.nanmax(data[-1])),
        _times=times, _x=x, _y=y, _data=data, _crs=crs, _tr=tr, _lon2d=lon2d, _lat2d=lat2d,
    )


def read_imerg(path):
    info = fileinfo(path)
    if not info["exists"]:
        return None
    ds = netCDF4.Dataset(path, "r")
    v = ds.variables["precip"]
    tv = ds.variables["time"]
    iso_file, tunits, tcal = decode_times(tv)
    extra = {}
    if tcal.lower() not in ("standard", "gregorian", "proleptic_gregorian"):
        iso_std, _, _ = decode_times(tv, calendar="standard")
        extra["time_decoded_with_file_calendar_first_last"] = [iso_file[0], iso_file[-1]]
        extra["time_decoded_as_standard_first_last"] = [iso_std[0], iso_std[-1]]
        extra["note"] = (f"file declares calendar='{tcal}'; stamps used here are decoded with the standard "
                         f"(Gregorian) calendar, which matches the bias-corrected file's stamps")
        iso = iso_std
    else:
        iso = iso_file
    times = to_dt64(iso)
    lon = np.asarray(ds.variables["longitude"][:])
    lat = np.asarray(ds.variables["latitude"][:])
    raw = v[:]
    data = np.asarray(np.ma.filled(raw, np.nan), dtype="float64") if np.ma.isMaskedArray(raw) \
        else np.asarray(raw, dtype="float64")
    gattrs = {k: str(ds.getncattr(k)) for k in ds.ncattrs()}
    vattrs = {k: str(v.getncattr(k)).replace("\n", " ").strip() for k in v.ncattrs()}
    vdims, vshape = list(v.dimensions), list(v.shape)
    ds.close()
    kw = ("bias", "scale", "target", "factor", "source")
    keyword_attrs = {f"global:{k}": val for k, val in gattrs.items() if any(w in k.lower() or w in val.lower() for w in kw)}
    keyword_attrs.update({f"precip:{k}": val for k, val in vattrs.items() if any(w in k.lower() or w in val.lower() for w in kw)})
    return dict(
        file=info, var_name="precip", units=vattrs.get("units"), units_attr_Units=vattrs.get("Units"),
        long_name=vattrs.get("long_name"), dims=vdims, shape=vshape,
        coordinate_names=["time", "latitude", "longitude"], projected=False, crs="EPSG:4326 (lat/lon, 0.1 deg)",
        lon_first=float(lon[0]), lon_last=float(lon[-1]), lat_first=float(lat[0]), lat_last=float(lat[-1]),
        lon_centres=[round(float(a), 4) for a in lon], lat_centres=[round(float(a), 4) for a in lat],
        time_units=tunits, time_calendar_attr=tcal, time=time_summary(times), time_decoding=extra,
        global_attrs=gattrs, keyword_attrs=keyword_attrs,
        bias_correction_parsed=parse_bias_attr(gattrs.get("bias_correction")),
        n_nan=int(np.isnan(data).sum()), n_negative=int((data < 0).sum()), max_rate_mm_h=float(np.nanmax(data)),
        _times=times, _lon=lon, _lat=lat, _data=data,
    )


def read_msk(map_path, inp):
    info = fileinfo(map_path, hash_limit_bytes=0)
    if not info["exists"]:
        return None
    ds = netCDF4.Dataset(map_path, "r")
    msk = np.asarray(np.ma.filled(ds.variables["msk"][:], 0))
    xm = np.asarray(np.ma.filled(ds.variables["x"][:], np.nan), dtype="float64")
    ym = np.asarray(np.ma.filled(ds.variables["y"][:], np.nan), dtype="float64")
    ds.close()
    act = msk > 0
    return dict(file=info, n_cells=int(msk.size), n_active=int(act.sum()),
                msk_values=sorted(int(u) for u in np.unique(msk)), _x=xm[act], _y=ym[act])


# ----------------------------------------------------------------------------- analysis
def analyse_run(cfg):
    R = dict(key=cfg["key"], event=cfg["event"], model_dir=cfg["model_dir"])
    inp_path = os.path.join(cfg["model_dir"], "sfincs.inp")
    R["sfincs_inp"] = fileinfo(inp_path)
    if not os.path.exists(inp_path):
        R["error"] = f"missing {inp_path}"
        return R
    inp = parse_inp(inp_path)
    precip_key = next((k for k in ("netamprfile", "amprfile", "precipfile") if k in inp), None)
    R["inp"] = dict(tref=inp.get("tref"), tstart=inp.get("tstart"), tstop=inp.get("tstop"),
                    precip_keyword=precip_key, precip_file=inp.get(precip_key) if precip_key else None,
                    dtwnd=inp.get("dtwnd"), epsg=inp.get("epsg"), x0=inp.get("x0"), y0=inp.get("y0"),
                    dx=inp.get("dx"), dy=inp.get("dy"), mmax=inp.get("mmax"), nmax=inp.get("nmax"),
                    other_precip_keywords_present=[k for k in ("amprfile", "precipfile", "spwfile") if k in inp])
    tstart, tstop = sfincs_time(inp["tstart"]), sfincs_time(inp["tstop"])
    if precip_key is None:
        R["error"] = "no precipitation keyword in sfincs.inp"
        return R
    precip_path = os.path.join(cfg["model_dir"], inp[precip_key])
    if not os.path.exists(precip_path):
        fileinfo(precip_path)
        R["error"] = f"missing {precip_path}"
        return R
    M = read_model_precip(precip_path, inp)
    R["model_precip"] = {k: v for k, v in M.items() if not k.startswith("_")}

    # duplicate model folders (same event): are their precip_2d.nc arrays identical?
    dups = []
    for d in cfg.get("duplicate_model_dirs", []):
        p = os.path.join(d, "precip_2d.nc")
        fi = fileinfo(p)
        if fi["exists"]:
            ds = netCDF4.Dataset(p, "r")
            arr = np.asarray(ds.variables["Precipitation"][:], dtype="float64")
            t2 = to_dt64(decode_times(ds.variables["time"])[0])
            ds.close()
            dups.append(dict(path=p, same_shape=arr.shape == M["_data"].shape,
                             arrays_identical=bool(arr.shape == M["_data"].shape and np.array_equal(arr, M["_data"])),
                             max_abs_diff_mm_h=float(np.max(np.abs(arr - M["_data"]))) if arr.shape == M["_data"].shape else None,
                             times_identical=bool(np.array_equal(t2, M["_times"]))))
        else:
            dups.append(dict(path=p, exists=False))
    R["duplicate_model_folders"] = dups

    t0, t1 = np.datetime64(cfg["window"][0], "ns"), np.datetime64(cfg["window"][1], "ns")
    minlon, minlat, maxlon, maxlat = cfg["bbox"]
    R["event_window_utc"] = [cfg["window"][0], cfg["window"][1]]
    R["bbox_lonlat"] = list(cfg["bbox"])

    # --- model regions
    x0, y0 = float(inp["x0"]), float(inp["y0"])
    dx, dy = float(inp["dx"]), float(inp["dy"])
    mmax, nmax = int(inp["mmax"]), int(inp["nmax"])
    X, Y = np.meshgrid(M["_x"], M["_y"])
    lon2d, lat2d = M["_lon2d"], M["_lat2d"]
    m_all = np.ones(X.shape, bool)
    m_bbox = (lon2d >= minlon) & (lon2d <= maxlon) & (lat2d >= minlat) & (lat2d <= maxlat)
    m_rect = (X >= x0) & (X <= x0 + mmax * dx) & (Y >= y0) & (Y <= y0 + nmax * dy)
    bx, by = Transformer.from_crs(CRS.from_epsg(4326), M["_crs"], always_xy=True).transform(
        [minlon, maxlon, maxlon, minlon], [minlat, minlat, maxlat, maxlat])
    R["bbox_in_model_crs_corners_xy"] = [[round(float(a), 1), round(float(b), 1)] for a, b in zip(bx, by)]
    R["bbox_cell_selection_rule_model"] = ("precip_2d cell centres inverse-projected to lon/lat (pyproj, EPSG:%s -> 4326); "
                                           "centre inside bbox, inclusive" % M["epsg"])

    msk = read_msk(os.path.join(cfg["model_dir"], "sfincs_map.nc"), inp)
    weights = None
    if msk is not None:
        ix = np.rint((msk["_x"] - M["_x"][0]) / M["dx_m"]).astype(int)
        iy = np.rint((msk["_y"] - M["_y"][0]) / M["dy_m"]).astype(int)
        ok = (ix >= 0) & (ix < M["_x"].size) & (iy >= 0) & (iy < M["_y"].size)
        weights = np.zeros(X.shape)
        np.add.at(weights, (iy[ok], ix[ok]), 1.0)
        msk["n_active_mapped_into_precip_grid"] = int(ok.sum())
        msk["n_precip_cells_with_active_weight"] = int((weights > 0).sum())
        R["active_mask"] = {k: v for k, v in msk.items() if not k.startswith("_")}
        R["active_mask"]["rule"] = ("each active SFINCS cell (msk>0 in sfincs_map.nc) assigned to the precip_2d cell "
                                    "whose centre is nearest; weight = number of active cells per precip_2d cell")

    def model_block(mask, label, w=None):
        if w is None:
            ser, n, nnan = region_series(M["_data"], mask)
        else:
            ser = (M["_data"] * w[None]).sum(axis=(1, 2)) / w.sum()
            n, nnan = int((w > 0).sum()), 0
        return dict(region=label, n_cells=n, n_nan_values=nnan,
                    event_window=window_totals(M["_times"], ser, t0, t1),
                    whole_file=whole_file_totals(M["_times"], ser),
                    peak_region_mean_rate_mm_h=float(np.nanmax(ser)),
                    peak_region_mean_rate_time=str(M["_times"][int(np.nanargmax(ser))])[:19])

    R["model_totals"] = dict(
        domain_all_cells=model_block(m_all, "all precip_2d cells"),
        bbox=model_block(m_bbox, "cells with centre in lon/lat bbox"),
        sfincs_grid_rectangle=model_block(m_rect, "cells with centre inside the SFINCS grid rectangle (x0,y0,mmax*dx,nmax*dy)"),
    )
    if weights is not None and weights.sum() > 0:
        R["model_totals"]["active_cell_weighted"] = model_block(None, "weighted by active SFINCS cells per precip_2d cell", weights)

    # --- IMERG files
    R["imerg"] = {}
    if cfg.get("imerg_note"):
        R["imerg_note"] = cfg["imerg_note"]
    imerg_sets = {}
    for tag in ("imerg_bc", "imerg_raw"):
        I = read_imerg(cfg[tag])
        if I is None:
            R["imerg"][tag] = dict(file=dict(path=cfg[tag], exists=False))
            continue
        imerg_sets[tag] = I
        lon32, lat32 = I["_lon"].astype(np.float32), I["_lat"].astype(np.float32)
        LON32, LAT32 = np.meshgrid(lon32, lat32)
        i_bbox = ((LON32 >= np.float32(minlon)) & (LON32 <= np.float32(maxlon))
                  & (LAT32 >= np.float32(minlat)) & (LAT32 <= np.float32(maxlat)))
        LON64, LAT64 = np.meshgrid(I["_lon"].astype("float64"), I["_lat"].astype("float64"))
        tol = 1e-4
        i_bbox64 = ((LON64 >= minlon - tol) & (LON64 <= maxlon + tol) & (LAT64 >= minlat - tol) & (LAT64 <= maxlat + tol))
        xi, yi = Transformer.from_crs(CRS.from_epsg(4326), M["_crs"], always_xy=True).transform(LON64, LAT64)
        i_rect = (xi >= x0) & (xi <= x0 + mmax * dx) & (yi >= y0) & (yi <= y0 + nmax * dy)
        i_all = np.ones(LON64.shape, bool)

        def imerg_block(mask, label):
            ser, n, nnan = region_series(I["_data"], mask)
            blk = dict(region=label, n_cells=n, n_nan_values=nnan,
                       event_window=window_totals(I["_times"], ser, t0, t1),
                       model_time_span=window_totals(I["_times"], ser, tstart, tstop),
                       whole_file=whole_file_totals(I["_times"], ser),
                       peak_region_mean_rate_mm_h=float(np.nanmax(ser)),
                       peak_region_mean_rate_time=str(I["_times"][int(np.nanargmax(ser))])[:19])
            return blk

        bias = I["bias_correction_parsed"] or (imerg_sets.get("imerg_bc") or {}).get("bias_correction_parsed")
        out = {k: v for k, v in I.items() if not k.startswith("_")}
        out["bbox_cell_selection_rule"] = ("cell centres compared in float32 against float32 bbox bounds, inclusive "
                                           "(replicates bias_correct_imerg.py's xarray comparison)")
        out["bbox_cells_selected"] = dict(n=int(i_bbox.sum()),
                                          lon_centres=[round(float(a), 3) for a in I["_lon"][i_bbox.any(axis=0)]],
                                          lat_centres=[round(float(a), 3) for a in I["_lat"][i_bbox.any(axis=1)]],
                                          n_with_float64_tolerance_1e_4=int(i_bbox64.sum()))
        out["totals"] = dict(domain_all_cells=imerg_block(i_all, "all IMERG cells in file"),
                             bbox=imerg_block(i_bbox, "IMERG cells with centre in bbox (float32 rule)"),
                             sfincs_grid_rectangle=imerg_block(i_rect, "IMERG cells whose centre projects inside the SFINCS grid rectangle"))
        if bias:
            bw0, bw1 = np.datetime64(bias["window_start"], "ns"), np.datetime64(bias["window_end"], "ns")
            ser_b, _, _ = region_series(I["_data"], i_bbox)
            out["bias_window_bbox"] = window_totals(I["_times"], ser_b, bw0, bw1)
            out["bias_window_bbox"]["note"] = "window and bbox as stated in imerg_<slug>.nc:bias_correction; 'total_incl_mm' is the script's rule"
        R["imerg"][tag] = out

    # model totals over the bias window (bbox mean), for the ratio to the target that was imposed there
    bias_bc = (imerg_sets.get("imerg_bc") or {}).get("bias_correction_parsed")
    if bias_bc:
        bw0, bw1 = np.datetime64(bias_bc["window_start"], "ns"), np.datetime64(bias_bc["window_end"], "ns")
        ser_m, _, _ = region_series(M["_data"], m_bbox)
        R["model_totals"]["bbox"]["bias_window"] = window_totals(M["_times"], ser_m, bw0, bw1)
        R["model_totals"]["bbox"]["bias_window"]["note"] = "same stamps as the IMERG bias window, applied to the model file's time axis"
        if weights is not None:
            ser_w = (M["_data"] * weights[None]).sum(axis=(1, 2)) / weights.sum()
            R["model_totals"]["active_cell_weighted"]["bias_window"] = window_totals(M["_times"], ser_w, bw0, bw1)
        R["bias_correction_as_recorded"] = bias_bc

    # --- pointwise correspondence model vs IMERG (nearest IMERG cell for each precip_2d cell centre)
    R["pointwise_check"] = {}
    for tag, I in imerg_sets.items():
        lons, lats = I["_lon"].astype("float64"), I["_lat"].astype("float64")
        ilon = np.abs(lon2d[..., None] - lons[None, None, :]).argmin(-1)
        ilat = np.abs(lat2d[..., None] - lats[None, None, :]).argmin(-1)
        inside = (np.abs(lon2d - lons[ilon]) <= 0.05 + 1e-3) & (np.abs(lat2d - lats[ilat]) <= 0.05 + 1e-3)
        Rs = I["_data"][:, ilat, ilon]
        tindex = {int(t.astype("int64")): j for j, t in enumerate(I["_times"])}
        dt_ns = M["_times"][1] - M["_times"][0]
        outside = ~inside
        res = dict(n_precip2d_cells_inside_imerg_extent=int(inside.sum()), n_precip2d_cells_total=int(inside.size),
                   n_precip2d_cells_outside_imerg_extent=int(outside.sum()),
                   max_rate_in_cells_outside_imerg_extent_mm_h=float(np.nanmax(M["_data"][:, outside])) if outside.any() else None,
                   rule="precip_2d cell centre -> lon/lat -> nearest IMERG cell centre (<= 0.05 deg); ratio = model / IMERG where IMERG > 1e-6 mm/h")
        ring = np.zeros(inside.shape, bool)
        ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
        ring_in = ring[inside]  # per selected cell: on the outer ring of the precip_2d grid?
        for shift in (0, 1):
            j = np.array([tindex.get(int((t + shift * dt_ns).astype("int64")), -1) for t in M["_times"]])
            ok = j >= 0
            Mv = M["_data"][ok][:, inside]
            Iv = Rs[j[ok]][:, inside]
            valid = np.isfinite(Iv) & np.isfinite(Mv) & (Iv > 1e-6)
            ratio = Mv[valid] / Iv[valid]
            tol = 1e-3 * np.maximum(1.0, Iv[valid])
            is2x = np.abs(Mv[valid] - 2 * Iv[valid]) <= tol
            ring_v = np.broadcast_to(ring_in[None, :], Mv.shape)[valid]
            n_int = int((~ring_v).sum())
            extra = {}
            if shift == 1 and ratio.size:
                # which precip_2d cells produce the non-2x pairs, how close their centres lie to an IMERG cell
                # edge, and whether their value equals 2x an ADJACENT IMERG cell (i.e. hydromt/GDAL nearest-index
                # assigned an edge-straddling centre to the neighbouring IMERG cell)
                full = np.zeros(Mv.shape, bool)
                full[valid] = ~is2x
                iy_sel, ix_sel = np.where(inside)
                bad_cells = np.where(full.any(axis=0))[0]
                dist_edge = np.minimum(0.05 - np.abs(lon2d - lons[ilon]), 0.05 - np.abs(lat2d - lats[ilat]))
                dist_bad = [float(dist_edge[iy_sel[c], ix_sel[c]]) for c in bad_cells]
                n_adj = 0
                for k, c in zip(*np.where(full)):
                    a, b = ilat[iy_sel[c], ix_sel[c]], ilon[iy_sel[c], ix_sel[c]]
                    neigh = I["_data"][j[ok][k], max(a - 1, 0):a + 2, max(b - 1, 0):b + 2].ravel()
                    if np.any(np.abs(Mv[k, c] - 2 * neigh) <= 1e-3 * np.maximum(1.0, 2 * neigh)):
                        n_adj += 1
                msum = float(Mv[valid].sum())
                extra = dict(n_cells_with_non_2x_pairs=int(len(bad_cells)),
                             n_non_2x_pairs_with_model_zero=int((Mv[valid][~is2x] <= 1e-6).sum()),
                             non_2x_cells_distance_to_imerg_cell_edge_deg=(dict(min=f(min(dist_bad), 4), max=f(max(dist_bad), 4)) if dist_bad else None),
                             n_non_2x_pairs_equal_2x_adjacent_imerg_cell=int(n_adj),
                             sum_model_over_sum_2x_imerg_all_pairs=f(msum / float((2 * Iv[valid]).sum()), 4) if Iv[valid].sum() > 0 else None,
                             depth_share_of_non_2x_pairs=f(float(Mv[valid][~is2x].sum()) / msum, 4) if msum > 0 else None)
            blk = dict(alignment=f"model stamp t <-> IMERG stamp t + {shift * 30} min", **extra,
                       n_model_frames_matched=int(ok.sum()), n_cell_time_pairs=int(valid.sum()),
                       ratio_median=f(np.median(ratio)) if ratio.size else None,
                       ratio_min=f(ratio.min()) if ratio.size else None, ratio_max=f(ratio.max()) if ratio.size else None,
                       frac_pairs_model_equals_2x_imerg=f(np.mean(is2x), 4) if ratio.size else None,
                       frac_pairs_model_equals_1x_imerg=f(np.mean(np.abs(Mv[valid] - Iv[valid]) <= tol), 4) if ratio.size else None,
                       n_pairs_not_2x=int((~is2x).sum()),
                       n_pairs_not_2x_on_outer_ring_of_precip2d_grid=int((~is2x & ring_v).sum()),
                       n_interior_pairs=n_int,
                       frac_interior_pairs_model_equals_2x_imerg=f(np.mean(is2x[~ring_v]), 4) if n_int else None)
            if shift == 1:
                per_frame = []
                for k in range(Mv.shape[0]):
                    v = valid[k]
                    per_frame.append(float(np.median(Mv[k][v] / Iv[k][v])) if v.sum() > 0 else np.nan)
                blk["per_frame_median_ratio_runs"] = runs_of(per_frame, M["_times"][ok])
            res[f"shift_{shift}"] = blk
        R["pointwise_check"][tag] = res

    # --- Valencia 164 vs 350 precip_2d
    if cfg.get("compare_precip_with"):
        p = cfg["compare_precip_with"]
        fileinfo(p)
        ds = netCDF4.Dataset(p, "r")
        other = np.asarray(ds.variables["Precipitation"][:], dtype="float64")
        ds.close()
        with np.errstate(all="ignore"):
            rr = np.where(other > 0, M["_data"] / other, np.nan)
        pf = [float(np.nanmedian(rr[k])) if np.isfinite(rr[k]).any() else np.nan for k in range(rr.shape[0])]
        R["precip2d_vs_350mm_run"] = dict(other_file=p, same_shape=other.shape == M["_data"].shape,
                                          per_frame_median_ratio_runs=runs_of(pf, M["_times"], 4),
                                          max_abs_diff_mm_h=float(np.nanmax(np.abs(M["_data"] - other))))

    # --- ratios
    ratios = {}
    mt = R["model_totals"]
    for reg in ("domain_all_cells", "bbox", "sfincs_grid_rectangle"):
        for tag in imerg_sets:
            it = R["imerg"][tag]["totals"][reg]
            for rule in ("total_pc_fwd_mm", "total_trap_mm"):
                num, den = mt[reg]["event_window"][rule], it["event_window"][rule]
                ratios[f"model/{tag} | event window | {reg} | {rule}"] = f(num / den) if den else None
            num, den = mt[reg]["whole_file"]["total_pc_fwd_mm"], it["model_time_span"]["total_pc_fwd_mm"]
            ratios[f"model/{tag} | model time span [tstart,tstop) | {reg} | total_pc_fwd_mm"] = f(num / den) if den else None
    for tname, tval in cfg["targets_mm"].items():
        ratios[f"model bbox event-window pc_fwd / target {tname}"] = f(mt["bbox"]["event_window"]["total_pc_fwd_mm"] / tval)
        ratios[f"model bbox event-window trap / target {tname}"] = f(mt["bbox"]["event_window"]["total_trap_mm"] / tval)
        ratios[f"model domain event-window pc_fwd / target {tname}"] = f(mt["domain_all_cells"]["event_window"]["total_pc_fwd_mm"] / tval)
        if "active_cell_weighted" in mt:
            ratios[f"model active-weighted event-window pc_fwd / target {tname}"] = f(mt["active_cell_weighted"]["event_window"]["total_pc_fwd_mm"] / tval)
        if "bias_window" in mt["bbox"]:
            ratios[f"model bbox bias-window pc_fwd / target {tname}"] = f(mt["bbox"]["bias_window"]["total_pc_fwd_mm"] / tval)
            ratios[f"model bbox bias-window incl / target {tname}"] = f(mt["bbox"]["bias_window"]["total_incl_mm"] / tval)
        for tag in imerg_sets:
            bwb = R["imerg"][tag].get("bias_window_bbox")
            if bwb:
                ratios[f"{tag} bbox bias-window incl (script rule) / target {tname}"] = f(bwb["total_incl_mm"] / tval)
    R["ratios"] = ratios
    R["targets_mm"] = cfg["targets_mm"]
    return R


# ----------------------------------------------------------------------------- markdown
def md_report(results):
    by_key = {R["key"]: R for R in results}
    groups = [("Pineios / Storm Daniel (EMSR692), enhanced", ["pineios_enhanced"], ["model precip_2d (written)"]),
              ("Mandra (EMSR257), enhanced", ["mandra_enhanced"], ["model precip_2d (written)"]),
              ("Valencia (EMSR773): as-run 350-mm anchor and 164-mm re-run (rerun_v164)",
               ["valencia_350_asrun", "valencia_164_rerun"], ["350-mm run precip_2d", "164-mm re-run precip_2d"])]
    L = []
    L.append("# F5-d: rainfall depth written to the SFINCS forcing (as-run models) - facts only")
    L.append("")
    L.append("Source: `f5_d_volume.py` -> `F5_d.json` (every number below is copied from the JSON; ratios to 3 decimals). Totals in mm as spatial means over the stated cells. "
             "`pc` = piecewise-constant forward sum(rate x dt) over stamps T0 <= t < T1 (SFINCS amprblock=1; an IMERG stamp is the start of its 30-min slot); "
             "`trap` = trapezoidal over T0 <= t <= T1; `incl` = inclusive-stamp sum x dt (the bias_correct_imerg.py rule). dt = 0.5 h (30-min stamps) in every file.")
    L.append("Model files: variable `Precipitation`(time,y,x), units mm/h, projected UTM grid (hydromt nearest-index resample of IMERG, ~9.5-10 km cells); IMERG files: `precip`(time,latitude,longitude), mm/h, 0.1 deg lat/lon. "
             "Every build's hydromt.log records `setup_precip_forcing_from_grid.cumulative_input: True, time_label: right` (hydromt_sfincs 1.2.2) for this mm/h input, which divides the rate by 0.5 h and shifts the series one frame earlier. "
             "sfincs_map.nc has storecumprcp=0 and no rainfall variable; sfincs.log prints no rainfall total; `precip_2d.nc` is the only on-disk record of the rain SFINCS read.")
    L.append("")

    def tot(blk, key="event_window"):
        e = blk[key]
        tr = e.get("total_trap_mm")
        return f"{e['total_pc_fwd_mm']:.2f} pc / {tr:.2f} trap" if tr is not None else f"{e['total_pc_fwd_mm']:.2f} pc"

    def runs_text(runs):
        multi = [x for x in runs if x["value"] is not None and abs(x["value"] - 2.0) > 1e-9 and x["n_frames"] >= 2]
        singles = [x for x in runs if x["value"] is not None and abs(x["value"] - 2.0) > 1e-9 and x["n_frames"] == 1]
        n2 = sum(x["n_frames"] for x in runs if x["value"] is not None and abs(x["value"] - 2.0) <= 1e-9)
        nn = sum(x["n_frames"] for x in runs if x["value"] is None)
        s = "; ".join(f"**{x['value']}** for {x['n_frames']} frames {x['start'][5:16]}..{x['end'][5:16]}" for x in multi)
        s += f"; 2.0 for {n2} frames; {nn} frames with no raw rain (undefined)"
        if singles:
            s += "; single frames: " + ", ".join(f"{x['value']}@{x['start'][5:16]}" for x in singles)
        return s

    for title, keys, labels in groups:
        runs = [by_key[k] for k in keys if k in by_key]
        if not runs or any("error" in R for R in runs):
            L.append(f"## {title}: ERROR " + "; ".join(R.get("error", "") for R in runs))
            continue
        first = runs[0]
        bc, raw = first["imerg"]["imerg_bc"], first["imerg"]["imerg_raw"]
        inp = first["inp"]
        same_inp = len({R["sfincs_inp"].get("sha256") for R in runs}) == 1
        L.append(f"## {title}")
        L.append(f"`sfincs.inp`{' (byte-identical in both model folders)' if len(runs) > 1 and same_inp else ''}: tref {inp['tref']}, tstart {inp['tstart']}, tstop {inp['tstop']}, "
                 f"`{inp['precip_keyword']} = {inp['precip_file']}`, dtwnd {inp['dtwnd']}, EPSG {inp['epsg']}. "
                 f"Event window {first['event_window_utc'][0][:16]} -> {first['event_window_utc'][1][:16]} UTC; bbox (lon/lat) {first['bbox_lonlat']}.")
        L.append("")
        L.append("| quantity | " + " | ".join(labels) + " | IMERG bias-corrected | IMERG raw |")
        L.append("|---|" + "---|" * (len(runs) + 2))
        mps = [R["model_precip"] for R in runs]
        mts = [R["model_totals"] for R in runs]
        row = lambda name, mcells, bcc, rawc: L.append(f"| {name} | " + " | ".join(mcells) + f" | {bcc} | {rawc} |")
        row("grid", [f"{mp['shape'][1]}x{mp['shape'][2]} cells, {mp['dx_m']:.1f} m, {mp['crs_name']}" for mp in mps],
            f"{bc['shape'][1]}x{bc['shape'][2]} cells, 0.1 deg", f"{raw['shape'][1]}x{raw['shape'][2]} cells, 0.1 deg")
        row("time: first / last / step / count", [f"{mp['time']['first']} / {mp['time']['last']} / {mp['time']['step_minutes']:.0f} min / {mp['time']['count']}" for mp in mps],
            f"{bc['time']['first']} / {bc['time']['last']} / {bc['time']['step_minutes']:.0f} min / {bc['time']['count']}",
            f"{raw['time']['first']} / {raw['time']['last']} / {raw['time']['step_minutes']:.0f} min / {raw['time']['count']} (calendar attr `{raw['time_calendar_attr']}`, decoded as standard)")
        for reg, name in (("domain_all_cells", "event window, domain mean (all cells)"), ("bbox", "event window, bbox mean"),
                          ("sfincs_grid_rectangle", "event window, mean over SFINCS grid rectangle")):
            row(f"{name} [n cells]", [f"{tot(mt[reg])} [{mt[reg]['n_cells']}]" for mt in mts],
                f"{tot(bc['totals'][reg])} [{bc['totals'][reg]['n_cells']}]", f"{tot(raw['totals'][reg])} [{raw['totals'][reg]['n_cells']}]")
        if all("active_cell_weighted" in mt for mt in mts):
            row(f"event window, active-cell-weighted mean (msk>0: {first['active_mask']['n_active']} cells)", [tot(mt["active_cell_weighted"]) for mt in mts], "-", "-")
        row("whole file, domain mean (n stamps)", [f"{tot(mt['domain_all_cells'], 'whole_file')} ({mp['time']['count']})" for mt, mp in zip(mts, mps)],
            f"{tot(bc['totals']['domain_all_cells'], 'whole_file')} ({bc['time']['count']})", f"{tot(raw['totals']['domain_all_cells'], 'whole_file')} ({raw['time']['count']})")
        row("whole file, bbox mean", [tot(mt["bbox"], "whole_file") for mt in mts], tot(bc["totals"]["bbox"], "whole_file"), tot(raw["totals"]["bbox"], "whole_file"))
        if "bias_window" in first["model_totals"]["bbox"]:
            b = first["bias_correction_as_recorded"]
            row(f"bias window per attr {b['window_start'][5:16]} -> {b['window_end'][5:16]}, bbox mean, incl rule (n stamps)",
                [f"{mt['bbox']['bias_window']['total_incl_mm']:.2f} ({mt['bbox']['bias_window']['n_stamps_incl']})" for mt in mts],
                f"{bc['bias_window_bbox']['total_incl_mm']:.2f} ({bc['bias_window_bbox']['n_stamps_incl']}); attr: x{b['factor']} -> {b['target_mm']:g} mm",
                f"{raw['bias_window_bbox']['total_incl_mm']:.2f}")
        L.append("")
        for R, lbl in zip(runs, labels):
            r, mt = R["ratios"], R["model_totals"]
            s = (f"Ratios, {lbl} (event window, pc): model/IMERG-bc domain **{r['model/imerg_bc | event window | domain_all_cells | total_pc_fwd_mm']}**, "
                 f"bbox **{r['model/imerg_bc | event window | bbox | total_pc_fwd_mm']}**, grid-rect {r['model/imerg_bc | event window | sfincs_grid_rectangle | total_pc_fwd_mm']}; "
                 f"model/IMERG-raw domain **{r['model/imerg_raw | event window | domain_all_cells | total_pc_fwd_mm']}**, bbox **{r['model/imerg_raw | event window | bbox | total_pc_fwd_mm']}**.")
            for k, tval in R["targets_mm"].items():
                s += (f" Model bbox / {tval:g} mm: **{r[f'model bbox event-window pc_fwd / target {k}']}** (trap {r[f'model bbox event-window trap / target {k}']})"
                      + (f", active-weighted / {tval:g}: {r[f'model active-weighted event-window pc_fwd / target {k}']}" if "active_cell_weighted" in mt else "")
                      + (f", bias-window incl / {tval:g}: {r[f'model bbox bias-window incl / target {k}']} (IMERG-bc: {r[f'imerg_bc bbox bias-window incl (script rule) / target {k}']})" if "bias_window" in mt["bbox"] else "") + ";")
            L.append(s)
        for R, lbl in zip(runs, labels):
            pc = R["pointwise_check"]["imerg_bc"]
            s1, s0 = pc["shift_1"], pc["shift_0"]
            db = s1.get("non_2x_cells_distance_to_imerg_cell_edge_deg")
            if s1["n_pairs_not_2x"] == 0:
                tail = "no exceptions"
            else:
                few = s1["n_cells_with_non_2x_pairs"] < pc["n_precip2d_cells_inside_imerg_extent"]
                tail = (f"the {s1['n_pairs_not_2x']} others come from {s1['n_cells_with_non_2x_pairs']} cells"
                        + (f" whose centre lies {db['min']}-{db['max']} deg from an IMERG cell edge" if (db and few) else "")
                        + f": {s1['n_non_2x_pairs_equal_2x_adjacent_imerg_cell']} equal 2 x an adjacent IMERG cell (zero-valued neighbours included), "
                        f"{s1['n_non_2x_pairs_with_model_zero']} have model = 0, {s1['n_pairs_not_2x_on_outer_ring_of_precip2d_grid']} lie on the grid's outer ring (overlapping counts); "
                        f"depth share of these pairs {(s1['depth_share_of_non_2x_pairs'] or 0)*100:.2f}%")
            L.append(f"Pointwise, {lbl} (nearest IMERG cell; {pc['n_precip2d_cells_inside_imerg_extent']}/{pc['n_precip2d_cells_total']} precip_2d cells inside the IMERG extent"
                     + (f", the {pc['n_precip2d_cells_outside_imerg_extent']} outside hold max {pc['max_rate_in_cells_outside_imerg_extent_mm_h']} mm/h" if pc['n_precip2d_cells_outside_imerg_extent'] else "")
                     + f"): model(t) = 2 x IMERG-bc(t+30 min) for **{s1['frac_pairs_model_equals_2x_imerg']*100:.2f}%** of {s1['n_cell_time_pairs']} cell-time pairs; {tail}; "
                     f"sum(model)/sum(2 x IMERG-bc) over all pairs = **{s1['sum_model_over_sum_2x_imerg_all_pairs']}**; without the 30-min shift only {s0['frac_pairs_model_equals_2x_imerg']*100:.2f}% match. "
                     f"Last model frame max {R['model_precip']['last_frame_max_mm_h']:.3f} mm/h.")
            L.append(f"Model / raw-IMERG per-frame median factor, {lbl} (shift +30 min): " + runs_text(R["pointwise_check"]["imerg_raw"]["shift_1"]["per_frame_median_ratio_runs"]) + ".")
        for R in runs:
            if R.get("precip2d_vs_350mm_run"):
                v = R["precip2d_vs_350mm_run"]
                ch = [x for x in v["per_frame_median_ratio_runs"] if x["value"] is not None and abs(x["value"] - 1.0) > 1e-9]
                L.append("164-mm re-run precip_2d / 350-mm run precip_2d, per-frame median ratio: " + "; ".join(
                    f"**{x['value']}** for {x['n_frames']} frames {x['start'][5:16]}..{x['end'][5:16]}" for x in ch) + "; 1.0 on every other frame with rain.")
            if R.get("imerg_note"):
                L.append(f"Note: {R['imerg_note']}")
            dup = [d for d in R.get("duplicate_model_folders", []) if d.get("exists", True)]
            if dup:
                L.append("Duplicate model folder: " + "; ".join(f"`{d['path']}` Precipitation array identical to model_author_ref = {d['arrays_identical']}" for d in dup) + ".")
        L.append("")
    L.append("## Files read (all opened read-only; size, sha256 prefix)")
    bydir = {}
    for fi in FILES_READ:
        bydir.setdefault(os.path.dirname(fi["path"]), []).append(fi)
    for d, fis in bydir.items():
        L.append(f"- `{d}\\`: " + ", ".join(
            f"{os.path.basename(fi['path'])} ({fi['size_bytes']} B{', ' + fi['sha256'][:12] if fi.get('sha256') else ''})" if fi.get("exists") else f"{os.path.basename(fi['path'])} (MISSING)"
            for fi in fis))
    L.append("- Also read (text, grep only, outside this script): `hydromt.log` and `sfincs.log` in each of the four model folders listed above "
             "(setup_precip_forcing_from_grid.* lines; process list), and `D:\\ELKAK\\.claude\\skills\\sfincs-flood-reproduction\\scripts\\bias_correct_imerg.py` (the rule for `incl`). "
             "sfincs_map.nc was read for `msk`, `x`, `y` only.")
    if MISSING:
        L.append("Missing files: " + "; ".join(MISSING))
    return "\n".join(L) + "\n"


def main():
    results = []
    for cfg in RUNS:
        print(f"--- {cfg['event']}")
        results.append(analyse_run(cfg))
    out = dict(generated=datetime.now().isoformat(timespec="seconds"), script=os.path.abspath(__file__),
               python=sys.version.split()[0], numpy=np.__version__, netCDF4=netCDF4.__version__,
               files_read=FILES_READ, missing_files=MISSING, runs=results)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    md = md_report(results)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    print(f"wrote {OUT_JSON}\nwrote {OUT_MD}")


if __name__ == "__main__":
    main()
