"""F5-f: audit of how the "spin-up" / antecedent period is implemented in the
as-run SFINCS runs (Pineios EMSR692, Strymonas EMSR122 v3, Mandra EMSR257,
Valencia EMSR773, Emilia-Romagna EMSR664).

FACTS ONLY. Read-only on every input. Writes F5_f.json and F5_f.md next to
this file. Nothing is re-run.

Usage (sfincs-viz env, GDAL_DATA set):
    python f5_f_spinup.py [--manual-txt PATH_TO_PDFTOTEXT_DUMP]

What it reads
  * sfincs.inp of each run (time keywords, zsini, forcing-file keywords)
  * the forcing files referenced by netamprfile / netampfile / netamuamvfile /
    srcfile / disfile (time axis: first, last, step, count)
  * sfincs_map.nc output time axes (first output time == start of integration)
  * hydromt.log of each build ("Slicing time dim" evidence per forcing)
  * the raw downloads in <run>/data (imerg_*.nc, era5_*.nc, glofas_*_clean.nc,
    q_outlet.csv) -> what was downloaded for tref..tstop
  * the repo YAMLs (window block, event.date) through the repo's own
    EventCfg (skill/scripts/_common.py) -> tref / tstart / tstop
  * code / manuscript / deliverable lines, located by anchor substring and
    reported with the line number found (robust to edits of the live worktree)
  * the SFINCS v2.3.0 manual PDF via `pdftotext -layout` (optional; a recorded
    copy of the quotes is used, and flagged, when pdftotext is unavailable)
"""
from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.dont_write_bytecode = True  # never write __pycache__ into the read-only repo

import argparse
import datetime as dt
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import yaml

HERE = Path(__file__).resolve().parent                 # .../reproduction/emsr933/f5
REPO = HERE.parents[2]                                 # .../.worktrees/emsr933-crete
SKILL = REPO / "skill"
sys.path.insert(0, str(SKILL / "scripts"))
from _common import EventCfg  # noqa: E402  (the repo's own tref/tstart/tstop logic)

PY_SITE = Path(sys.executable).parent / "Lib" / "site-packages"
MANUAL_PDF = Path("D:/ELKAK/implementation/SFINCS_bin/"
                  "SFINCS_v2.3.0_mt_Faber_release_manual_report.pdf")
MANUSCRIPT_TXT = Path("D:/ELKAK/manuscript/text/paper_v5_text.txt")
BUNDLES = Path("D:/ELKAK/deliverables/bundles")

FILES_READ: dict[str, dict] = {}


def s(p) -> str:
    return str(p).replace("\\", "/")


def reg(p: Path) -> Path:
    """Register a file as read (path, size, mtime) and return it."""
    p = Path(p)
    if s(p) not in FILES_READ:
        st = p.stat()
        FILES_READ[s(p)] = {"bytes": st.st_size,
                            "mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}
    return p


# ---------------------------------------------------------------------------
# Event table
# ---------------------------------------------------------------------------
EVENTS = [
    dict(key="pineios", label="Pineios EMSR692 enh.", slug="pineios",
         model="D:/ELKAK/implementation/pineios_sfincs_enhanced/model_author_ref",
         data="D:/ELKAK/implementation/pineios_sfincs_enhanced/data",
         yaml=SKILL / "examples" / "emsr692_pineios_enhanced.yaml",
         stated_spinup_days=7, stated_in="manuscript v5", bundle="deliverable_daniel_emsr692_enhanced"),
    dict(key="strymonas", label="Strymonas EMSR122 v3", slug="strymonas",
         model="D:/ELKAK/implementation/emsr122_sfincs_v3/model_author_ref",
         data="D:/ELKAK/implementation/emsr122_sfincs_v3/data",
         yaml=SKILL / "examples" / "emsr122_strymonas_enhanced.yaml",
         stated_spinup_days=7, stated_in="manuscript v5", bundle="deliverable_strymonas_emsr122_enhanced"),
    dict(key="mandra", label="Mandra EMSR257 enh.", slug="mandra",
         model="D:/ELKAK/implementation/mandra_sfincs_enhanced/model_author_ref",
         data="D:/ELKAK/implementation/mandra_sfincs_enhanced/data",
         yaml=SKILL / "examples" / "emsr257_mandra_enhanced.yaml",
         stated_spinup_days=1, stated_in="manuscript v5", bundle="deliverable_mandra_emsr257_enhanced"),
    dict(key="valencia", label="Valencia EMSR773", slug="valencia",
         model="D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/model",
         data="D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/data",
         yaml=SKILL / "examples" / "emsr773_valencia_enhanced.yaml",
         stated_spinup_days=3, stated_in="held-out YAML", bundle=None,
         deliverable="D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/deliverable"),
    dict(key="emilia", label="Emilia-Romagna EMSR664", slug="emilia_romagna",
         model="D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/model",
         data="D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/data",
         yaml=SKILL / "examples" / "emsr664_emilia_romagna_enhanced.yaml",
         stated_spinup_days=14, stated_in="held-out YAML", bundle=None,
         deliverable="D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/deliverable"),
]

TIME_KEYS = ["tref", "tstart", "tstop", "tspinup", "spinup_meteo", "t0out", "dtout",
             "dthisout", "dtmaxout", "dtrstout", "trstout", "dtwnd", "dtmax", "zsini",
             "inifile", "rstfile", "bzsfile", "bndfile", "netamprfile", "netampfile",
             "netamuamvfile", "srcfile", "disfile", "scsfile", "qinf"]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def iso(t) -> str | None:
    return None if t is None else pd.Timestamp(t).strftime("%Y-%m-%d %H:%M")


def days(td) -> float:
    return round(pd.Timedelta(td).total_seconds() / 86400.0, 4)


def _lines(path: Path) -> list[str]:
    # split on "\n" only, so line numbers equal `sed -n` / `grep -n` numbering
    # (str.splitlines() would also split on form feeds = PDF page breaks)
    return reg(path).read_text(encoding="utf-8", errors="replace").split("\n")


def grep_lines(path: Path, pattern: str, max_hits: int = 10) -> dict:
    txt = _lines(path)
    hits = {str(i + 1): ln.rstrip() for i, ln in enumerate(txt) if re.search(pattern, ln)}
    return {"file": s(path), "pattern": pattern, "hits": dict(list(hits.items())[:max_hits]), "n_hits": len(hits)}


def grep_block(path: Path, anchor: str, n_after: int = 0, n_before: int = 0, after: str | None = None) -> dict:
    """First line matching regex `anchor` (searching from the first line matching
    `after`, if given) plus context lines, keyed by 1-based line number."""
    txt = _lines(path)
    start = 0
    if after is not None:
        start = next((i for i, ln in enumerate(txt) if re.search(after, ln)), 0)
    hit = next((i for i in range(start, len(txt)) if re.search(anchor, txt[i])), None)
    if hit is None:
        return {"file": s(path), "anchor": anchor, "found": False, "line": None, "lines": {}}
    lo, hi = max(0, hit - n_before), min(len(txt), hit + n_after + 1)
    return {"file": s(path), "anchor": anchor, "found": True, "line": hit + 1,
            "lines": {str(i + 1): txt[i].rstrip() for i in range(lo, hi)}}


def pick(block: dict, substr: str) -> tuple[str, str]:
    """(line_no, text) of the first line in a grep_block result containing substr."""
    for k, v in block.get("lines", {}).items():
        if substr in v:
            return k, v.strip()
    return "?", f"<{substr!r} not found>"


def parse_inp(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in _lines(path):
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_sfincs_time(v: str) -> dt.datetime:
    return dt.datetime.strptime(v.strip(), "%Y%m%d %H%M%S")


_UNIT = {"seconds": "s", "second": "s", "minutes": "m", "minute": "m",
         "hours": "h", "hour": "h", "days": "D", "day": "D"}


def decode_cf_time(values: np.ndarray, units: str) -> pd.DatetimeIndex:
    """Decode '<unit> since <origin>' with pandas label arithmetic. Identical to
    the cftime labels for 1980-2025 under julian / proleptic_gregorian /
    standard calendars, because all three share the same leap years there."""
    m = re.match(r"^\s*(\w+)\s+since\s+(.+?)\s*$", units)
    if not m:
        raise ValueError(f"unparseable time units: {units!r}")
    unit, origin = m.group(1).lower(), m.group(2).replace(" UTC", "")
    o = pd.Timestamp(origin)
    if o.tzinfo is not None:
        o = o.tz_convert(None)
    return o + pd.to_timedelta(np.asarray(values, dtype="float64"), unit=_UNIT[unit])


def nc_time_axis(path: Path, varname: str = "time") -> dict:
    """Time-axis facts of one netCDF + whether xarray's DEFAULT decoding yields
    numpy datetime64 (the condition hydromt's _slice_temporal_dimension needs)."""
    path = reg(path)
    with xr.open_dataset(path, decode_times=False) as ds:
        t = ds[varname]
        units = t.attrs.get("units") or t.encoding.get("units")
        cal = t.attrs.get("calendar") or t.encoding.get("calendar")
        raw_dtype, vals = str(t.dtype), t.values
        tt = decode_cf_time(vals, units)
    with xr.open_dataset(path, decode_times=True) as ds2:
        default_dtype = str(ds2[varname].dtype)
    steps = np.unique(np.diff(tt.values)).astype("timedelta64[m]").astype(int).tolist() if tt.size > 1 else []
    return {"file": s(path), "n": int(tt.size), "first": iso(tt[0]), "last": iso(tt[-1]),
            "step_min": steps if len(steps) > 1 else (steps[0] if steps else None),
            "units": units, "calendar": cal, "raw_dtype": raw_dtype,
            "xarray_default_dtype": default_dtype,
            "xarray_default_decodes_to_datetime64": default_dtype.startswith("datetime64"),
            "_times": tt}


def precip_totals(path: Path, varname: str, tstart, tstop, times: pd.DatetimeIndex) -> dict:
    """Domain-mean accumulated precipitation [mm] before tstart and within
    [tstart, tstop) for a (time, y, x) rate field in mm/h (constant per step)."""
    with xr.open_dataset(reg(path), decode_times=False) as ds:
        arr = ds[varname].values.astype("float64")
    step_h = float(np.median(np.diff(times.values)) / np.timedelta64(1, "h"))
    before = times < pd.Timestamp(tstart)
    within = (times >= pd.Timestamp(tstart)) & (times < pd.Timestamp(tstop))
    series = np.nanmean(arr, axis=tuple(range(1, arr.ndim)))  # domain-mean rate per step
    return {"var": varname, "step_h": step_h,
            "domain_mean_mm_before_tstart": round(float(np.nansum(series[before]) * step_h), 2),
            "n_steps_before_tstart": int(before.sum()),
            "domain_mean_mm_tstart_to_tstop": round(float(np.nansum(series[within]) * step_h), 2),
            "n_steps_tstart_to_tstop": int(within.sum())}


def dis_info(path: Path, tref: dt.datetime, tstart: dt.datetime) -> dict:
    rows = [ln.split() for ln in _lines(path) if ln.strip()]
    sec = np.array([float(r[0]) for r in rows])
    t = pd.Timestamp(tref) + pd.to_timedelta(sec, unit="s")
    steps = np.unique(np.diff(sec)).tolist()
    return {"file": s(path), "n_rows": len(rows), "n_sources": len(rows[0]) - 1,
            "time_unit": "seconds since tref (sfincs.inp)",
            "first_s": float(sec[0]), "last_s": float(sec[-1]), "first": iso(t[0]), "last": iso(t[-1]),
            "step_s": steps if len(steps) > 1 else steps[0],
            "n_rows_before_tstart": int((t < pd.Timestamp(tstart)).sum())}


def hydromt_log_slicing(path: Path) -> dict:
    """Which forcing blocks of the hydromt build show a 'Slicing time dim' line."""
    cur, out, imerg_src = None, {}, None
    for line in _lines(path):
        m = re.search(r"setup_(precip|wind|pressure)_forcing_from_grid\.\w+:", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, None)
        m2 = re.search(r"Slicing time dim \((.+)\)", line)
        if m2 and cur:
            out[cur] = m2.group(1)
        m3 = re.search(r"Reading imerg_half_hourly netcdf data from (.+)$", line)
        if m3:
            imerg_src = m3.group(1).strip()
        if "Writing model data" in line:
            cur = None
    return {"file": s(path), "sliced": {k: v is not None for k, v in out.items()},
            "slicing_tuples": out, "imerg_source_as_run": imerg_src}


# ---------------------------------------------------------------------------
# SFINCS manual (v2.3.0 mt Faber) keyword definitions
# ---------------------------------------------------------------------------
MANUAL_QUOTES = {  # key -> (anchor substring, extra lines after anchor)
    "time_management": ("The required model runtime can be specified by setting a reference date (tref)", 0),
    "tref": ("Reference date in `yyyymmdd HHMMSS'", 0),
    "tstart": ("Start date in `yyyymmdd HHMMSS'", 0),
    "tstop": ("Stop date in `yyyymmdd HHMMSS'", 0),
    "tspinup": ("Duration of spinup period after tstart, where the water level variation", 2),
    "spinup_meteo": ("Option to also apply spinup to the meteo forcing", 0),
    "zsini": ("Initial water level in entire domain - where above bed level", 0),
    "dis_time_ref": ("the discharge time-series are specified per input location. Times are specified in seconds", 1),
    "rain_time_ref": ("Rain input in mm/hr, times are specified in seconds with respect to SFINCS' internal reference time", 1),
    "restart_spinup": ("In order to run SFINCS without spinup of water levels in a subsequent simulation", 1),
}
# Recorded 2026-10-09 from `pdftotext -layout` (poppler/xpdf 4.00, Git-for-Windows) of MANUAL_PDF,
# "\n"-split line numbers. Used only when pdftotext is unavailable.
RECORDED_MANUAL = {
    "time_management": "L1749: The required model runtime can be specified by setting a reference date (tref), start date (tstart) and stop date (tstop).",
    "tref": "L3467: Reference date in `yyyymmdd HHMMSS'  (default 20000101 000000)",
    "tstart": "L3475: Start date in `yyyymmdd HHMMSS'  (default 20000101 000000)",
    "tstop": "L3483: Stop date in `yyyymmdd HHMMSS'  (default 20000101 000000)",
    "tspinup": "L3314-3316: Duration of spinup period after tstart, where the water level variation at the boundary is dampened, between values in the `bzsfile' input and the value of `zsini' (even if using rstfile as initial condition)  [units s, default 0]",
    "spinup_meteo": "L3333: Option to also apply spinup to the meteo forcing, default is off (0)",
    "zsini": "L2965: Initial water level in entire domain - where above bed level.  [m above reference level, default 0]",
    "dis_time_ref": "L2020-2021: Then in the file `sfincs.dis' the discharge time-series are specified per input location. Times are specified in seconds with respect to SFINCS' internal reference time `tref', as specified in sfincs.inp.",
    "rain_time_ref": "L2290-2291: Rain input in mm/hr, times are specified in seconds with respect to SFINCS' internal reference time `tref', as specified in sfincs.inp.",
    "restart_spinup": "L1723-1724: In order to run SFINCS without spinup of water levels in a subsequent simulation, the waterlevels at the final time step of the former can be saved as binary-file ...",
}


def manual_quotes(manual_txt: str | None) -> dict:
    out = {"pdf": s(MANUAL_PDF), "pdf_exists": MANUAL_PDF.exists(), "pdftotext": shutil.which("pdftotext"),
           "method": None, "quotes": {}}
    txt_path, tmp = None, None
    if manual_txt and Path(manual_txt).is_file():
        txt_path, out["method"] = Path(manual_txt), f"pdftotext dump supplied: {manual_txt}"
    elif MANUAL_PDF.exists() and out["pdftotext"]:
        tmp = HERE / "_manual_extract.tmp.txt"
        subprocess.run([out["pdftotext"], "-layout", str(MANUAL_PDF), str(tmp)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        txt_path, out["method"] = tmp, "pdftotext -layout run in this session (temp file deleted)"
        reg(MANUAL_PDF)
    if txt_path is None:
        out["method"] = "pdftotext unavailable -> RECORDED quotes (2026-10-09), NOT re-verified in this run"
        out["quotes"] = dict(RECORDED_MANUAL)
        return out
    lines = txt_path.read_text(encoding="utf-8", errors="replace").split("\n")
    for key, (anchor, extra) in MANUAL_QUOTES.items():
        hit = next((i for i, ln in enumerate(lines) if anchor in ln), None)
        if hit is None:
            out["quotes"][key] = {"found": False, "recorded": RECORDED_MANUAL[key]}
            continue
        block = " ".join(ln.strip() for ln in lines[hit:hit + 1 + extra])
        out["quotes"][key] = {"found": True, "line": hit + 1, "text": re.sub(r"\s+", " ", block)}
    if tmp is not None and tmp.exists():
        tmp.unlink()
    return out


# ---------------------------------------------------------------------------
# Per-event audit
# ---------------------------------------------------------------------------
def audit_event(ev: dict) -> dict:
    model, data = Path(ev["model"]), Path(ev["data"])
    res: dict = {"label": ev["label"], "model_dir": s(model), "data_dir": s(data)}

    # --- YAML -> repo EventCfg ------------------------------------------------
    ypath = reg(Path(ev["yaml"]))
    cfg = EventCfg(raw=yaml.safe_load(ypath.read_text(encoding="utf-8")), config_path=ypath)
    w = cfg.window
    res["yaml"] = {"file": s(ypath), "event_date": cfg.event_date.isoformat(),
                   "spinup_days": w["spinup_days"], "pre_event_days": w["pre_event_days"],
                   "post_event_days": w["post_event_days"],
                   "EventCfg.tref": iso(cfg.tref), "EventCfg.tstart": iso(cfg.tstart), "EventCfg.tstop": iso(cfg.tstop),
                   "rain_bias_correct_enabled": cfg.rain_bias_correct["enabled"],
                   "infiltration_enabled": cfg.infiltration["enabled"],
                   "upstream_q_enabled": cfg.upstream_q["enabled"]}

    # --- sfincs.inp -----------------------------------------------------------
    inp = parse_inp(model / "sfincs.inp")
    tref, tstart, tstop = (parse_sfincs_time(inp[k]) for k in ("tref", "tstart", "tstop"))
    res["inp"] = {"file": s(model / "sfincs.inp"), **{k: inp.get(k, "absent") for k in TIME_KEYS}}
    res["inp_parsed"] = {"tref": iso(tref), "tstart": iso(tstart), "tstop": iso(tstop),
                         "tspinup_s": float(inp["tspinup"]) if "tspinup" in inp else None,
                         "zsini_m": float(inp["zsini"]) if "zsini" in inp else None,
                         "dtout_s": float(inp["dtout"]) if "dtout" in inp else None}
    res["inp_matches_EventCfg"] = {"tref": tref == cfg.tref, "tstart": tstart == cfg.tstart, "tstop": tstop == cfg.tstop}
    sb = model.parent / "sfincs_build.yml"  # rendered template, run folder = parent of model dir
    if sb.exists():
        res["sfincs_build_yml"] = grep_lines(sb, r"^\s*(tref|tstart|tstop|zsini):")

    ev_date = dt.datetime.combine(cfg.event_date, dt.time())
    res["derived"] = {
        "sim_duration_days_tstop_minus_tstart": days(tstop - tstart),
        "gap_days_tstart_minus_tref": days(tstart - tref),
        "days_simulated_before_event_date_tstart_to_eventdate": days(ev_date - tstart),
        "days_simulated_after_event_date_eventdate_to_tstop": days(tstop - ev_date),
        "days_forcing_window_not_simulated_tref_to_tstart": days(tstart - tref),
        "antecedent_tref_to_tstart_inside_[tstart,tstop]": bool(tref >= tstart),
        "stated_spinup_days": ev["stated_spinup_days"], "stated_in": ev["stated_in"],
        "stated_equals_spinup_days_yaml": ev["stated_spinup_days"] == w["spinup_days"],
        "stated_equals_gap_tstart_minus_tref": float(ev["stated_spinup_days"]) == days(tstart - tref),
    }

    # --- forcing files referenced by sfincs.inp --------------------------------
    forc: dict = {}
    for kw, var in (("netamprfile", "Precipitation"), ("netampfile", "barometric_pressure"),
                    ("netamuamvfile", "eastward_wind")):
        if kw not in inp:
            forc[kw] = "absent"
            continue
        info = nc_time_axis(model / inp[kw])
        times = info.pop("_times")
        info["steps_before_tstart"] = int((times < pd.Timestamp(tstart)).sum())
        info["forcing_exists_before_tstart"] = bool(info["steps_before_tstart"] > 0)
        info["covers_tstart_to_tstop"] = bool(times[0] <= pd.Timestamp(tstart) and times[-1] >= pd.Timestamp(tstop))
        if kw == "netamprfile":
            info["totals"] = precip_totals(model / inp[kw], var, tstart, tstop, times)
        forc[kw] = info
    if "disfile" in inp:
        forc["disfile"] = dis_info(model / inp["disfile"], tref, tstart)
        forc["disfile"]["forcing_exists_before_tstart"] = forc["disfile"]["n_rows_before_tstart"] > 0
        forc["srcfile"] = {"file": s(model / inp["srcfile"]),
                           "n_points": len([ln for ln in _lines(model / inp["srcfile"]) if ln.strip()])}
    else:
        forc["disfile"], forc["srcfile"] = "absent", "absent"
    forc["bzsfile"] = inp.get("bzsfile", "absent")
    res["forcing_in_model_dir"] = forc

    # --- SFINCS output time axes (start of integration) ------------------------
    mp = model / "sfincs_map.nc"
    if mp.exists():
        t_out = nc_time_axis(mp, "time"); t_out.pop("_times")
        tm_out = nc_time_axis(mp, "timemax"); tm_out.pop("_times")
        res["sfincs_map_nc"] = {"time": t_out, "timemax": tm_out,
                                "first_output_equals_tstart": t_out["first"] == iso(tstart),
                                "last_output_equals_tstop": t_out["last"] == iso(tstop)}

    # --- hydromt build log ----------------------------------------------------
    hl = model / "hydromt.log"
    if hl.exists():
        res["hydromt_log"] = hydromt_log_slicing(hl)

    # --- raw downloads in data/ -----------------------------------------------
    slug, dl = ev["slug"], {}
    for name in (f"imerg_{slug}.nc", f"imerg_{slug}.raw.nc", f"era5_{slug}.nc", f"glofas_{slug}_clean.nc"):
        p = data / name
        if not p.exists():
            dl[name] = "absent"
            continue
        info = nc_time_axis(p)
        times = info.pop("_times")
        info["steps_before_tstart"] = int((times < pd.Timestamp(tstart)).sum())
        info["steps_in_[tref,tstart)"] = int(((times >= pd.Timestamp(tref)) & (times < pd.Timestamp(tstart))).sum())
        info["first_equals_tref"] = info["first"] == iso(tref)
        info["last_equals_tstop"] = info["last"] == iso(tstop)
        if name == f"imerg_{slug}.nc":
            info["totals"] = precip_totals(p, "precip", tstart, tstop, times)
        dl[name] = info
    q = data / "q_outlet.csv"
    if q.exists():
        df = pd.read_csv(reg(q), index_col=0, parse_dates=True)
        dl["q_outlet.csv"] = {"file": s(q), "n": int(len(df)), "first": iso(df.index[0]), "last": iso(df.index[-1]),
                              "n_cols": int(df.shape[1]), "first_equals_tref": iso(df.index[0]) == iso(tref)}
    else:
        dl["q_outlet.csv"] = "absent"
    res["raw_downloads"] = dl

    # --- deliverable docs wording ----------------------------------------------
    docs = {}
    ddir = BUNDLES / ev["bundle"] if ev.get("bundle") else Path(ev["deliverable"])
    for rel, pat in (("README.md", r"Simulation window"), ("4_docs/results.md", r"Spin-up|Simulation window"),
                     ("4_docs/methodology.md", r"`tref`")):
        if (ddir / rel).exists():
            docs[rel] = grep_lines(ddir / rel, pat, 4)
    res["deliverable_docs"] = docs
    return res


# ---------------------------------------------------------------------------
# Code / manuscript quotes (anchor-located, reported with the line number found)
# ---------------------------------------------------------------------------
def code_quotes() -> dict:
    hs = Path(importlib.util.find_spec("hydromt_sfincs").origin).parent
    hm = Path(importlib.util.find_spec("hydromt").origin).parent
    sc = SKILL / "scripts"
    return {
        "_common.window_defaults": grep_block(sc / "_common.py", r'"spinup_days": int\(w\.get\("spinup_days"', 2),
        "_common.tref": grep_block(sc / "_common.py", r"def tref\(self\)", 3),
        "_common.tstart": grep_block(sc / "_common.py", r"def tstart\(self\)", 3),
        "_common.tstop": grep_block(sc / "_common.py", r"def tstop\(self\)", 6),
        "template.setup_config": grep_block(SKILL / "templates" / "sfincs_build.yml.tmpl", r"^setup_config:", 3),
        "template.zsini": grep_block(SKILL / "templates" / "sfincs_build.yml.tmpl", r"^\s*zsini:", 0),
        "build_model.render": grep_block(sc / "build_model.py", r'"tref": cfg\.tref\.strftime', 2),
        "build_model.dis_from_tref": grep_block(sc / "build_model.py", r"tref = cfg\.tref", 4),
        "prep_q.hours_tref_tstop": grep_block(sc / "prep_q_at_outlets.py", r"pd\.date_range\(cfg\.tref, cfg\.tstop", 0),
        "download_imerg.window": grep_block(sc / "download_imerg.py", r"t0 = cfg\.tref\.isoformat\(\)", 1),
        "download_era5.window": grep_block(sc / "download_era5.py", r"cur = cfg\.tref", 1),
        "download_glofas.window": grep_block(sc / "download_glofas.py", r"cfg\.tref\.year", 1),
        "package_deliverable.spinup_fields": grep_block(sc / "package_deliverable.py", r'"tref": cfg\.tref\.strftime', 5),
        "bias_correct_imerg.time_reencode": grep_block(sc / "bias_correct_imerg.py", r"calendar=julian", 1, n_before=1),
        "bias_correct_imerg.encoding": grep_block(sc / "bias_correct_imerg.py", r'"calendar": "proleptic_gregorian"', 0, n_before=1),
        "hydromt_sfincs.get_model_time": grep_block(hs / "sfincs.py", r"def get_model_time\(self\)", 4),
        "hydromt_sfincs.precip_time_tuple": grep_block(hs / "sfincs.py", r"time_tuple=self\.get_model_time\(\)", 0, n_before=4,
                                                       after=r"def setup_precip_forcing_from_grid"),
        "hydromt_sfincs.precip_cumulative": grep_block(hs / "sfincs.py", r"precip = precip / \(time_interval / 3600\)", 0, n_before=2,
                                                       after=r"def setup_precip_forcing_from_grid"),
        "hydromt_sfincs.tspinup_default": grep_block(hs / "sfincs_input.py", r"self\.tspinup = 0\.0", 0),
        "hydromt.slice_condition": grep_block(hm / "data_adapter" / "rasterdataset.py", r"def _slice_temporal_dimension", 13),
        "hydromt_sfincs.dir": s(hs), "hydromt.dir": s(hm),
    }


def manuscript_quotes() -> dict:
    if not MANUSCRIPT_TXT.exists():
        return {"file": s(MANUSCRIPT_TXT), "missing": True, "hits": {}}
    return grep_lines(MANUSCRIPT_TXT, r"Spin-up \(d\)|uses an antecedent spin-up|7-day spin-up|1-day spin-up", 8)


# ---------------------------------------------------------------------------
# Markdown report (every value copied from the JSON)
# ---------------------------------------------------------------------------
def fmt_axis(a) -> str:
    if not isinstance(a, dict):
        return str(a)
    return f"{a['first']} → {a['last']} (n={a['n']}, Δ={a['step_min']} min)"


def _imerg(e):
    return next(v for k, v in e["raw_downloads"].items() if k.startswith("imerg_") and not k.endswith(".raw.nc"))


def _dl(e, prefix):
    return next((v for k, v in e["raw_downloads"].items() if k.startswith(prefix)), "absent")


def _doc(e):
    d = e["deliverable_docs"].get("README.md")
    if not d or not d["hits"]:
        return "n/a"
    ln, txt = next(iter(d["hits"].items()))
    return f"L{ln}: " + re.sub(r"\*\*", "", txt).replace("- Simulation window: ", "")


def write_md(J: dict, out: Path) -> None:
    E, C, M = J["events"], J["code_quotes"], J["manual"]["quotes"]
    keys = [e["key"] for e in EVENTS]

    def row(name, fn):
        return f"| {name} | " + " | ".join(str(fn(E[k])) for k in keys) + " |"

    def yn(b):
        return "Y" if b else "N"

    pr = lambda e: e["forcing_in_model_dir"]["netamprfile"]  # noqa: E731
    wp = lambda e: (fmt_axis(e["forcing_in_model_dir"]["netamuamvfile"])  # noqa: E731
                    if fmt_axis(e["forcing_in_model_dir"]["netamuamvfile"]) == fmt_axis(e["forcing_in_model_dir"]["netampfile"])
                    else f"wind {fmt_axis(e['forcing_in_model_dir']['netamuamvfile'])}; press {fmt_axis(e['forcing_in_model_dir']['netampfile'])}")
    dis = lambda d: "absent" if d == "absent" else f"{d['first']} → {d['last']}, {d['n_rows']} rows ({d['n_sources']} src), {d['n_rows_before_tstart']} rows < tstart"  # noqa: E731
    qo = lambda q: "absent" if q == "absent" else f"{q['first']} → {q['last']} ({q['n']})"  # noqa: E731
    cum_ln, cum_txt = pick(C["hydromt_sfincs.precip_cumulative"], "precip = precip /")

    L = ["# F5-f — Spin-up / antecedent period as implemented in the as-run SFINCS runs (facts only)",
         f"Generated {J['generated']} by `f5_f_spinup.py` from the files listed at the end; every value below is copied from `F5_f.json`. "
         "Nothing was re-run. Dates are UTC `YYYY-MM-DD HH:MM`; `absent` = keyword/file not present.", "",
         "| quantity | " + " | ".join(E[k]["label"] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    L.append(row("event.date (YAML)", lambda e: e["yaml"]["event_date"]))
    L.append(row("YAML spinup / pre / post (d)", lambda e: f"{e['yaml']['spinup_days']} / {e['yaml']['pre_event_days']} / {e['yaml']['post_event_days']}"))
    L.append(row("sfincs.inp tref", lambda e: e["inp_parsed"]["tref"]))
    L.append(row("sfincs.inp tstart", lambda e: e["inp_parsed"]["tstart"]))
    L.append(row("sfincs.inp tstop · inp==EventCfg(tref/tstart/tstop)", lambda e: f"{e['inp_parsed']['tstop']} · " + "/".join(yn(v) for v in e["inp_matches_EventCfg"].values())))
    L.append(row("sfincs.inp tspinup / spinup_meteo / inifile / rstfile / bzsfile", lambda e: f"{e['inp']['tspinup']} (present) / {e['inp']['spinup_meteo']} / {e['inp']['inifile']} / {e['inp']['rstfile']} / {e['inp']['bzsfile']}"))
    L.append(row("sfincs.inp zsini / dtout / dtmaxout / dtwnd", lambda e: f"{e['inp']['zsini']} / {e['inp']['dtout']} / {e['inp']['dtmaxout']} / {e['inp']['dtwnd']}"))
    L.append(row("tstop − tstart (d, simulated)", lambda e: e["derived"]["sim_duration_days_tstop_minus_tstart"]))
    L.append(row("tstart − tref (d) = forcing downloaded, not simulated", lambda e: e["derived"]["gap_days_tstart_minus_tref"]))
    L.append(row("simulated before event.date: tstart→event (d)", lambda e: e["derived"]["days_simulated_before_event_date_tstart_to_eventdate"]))
    L.append(row("stated spin-up (d) [source] · == tstart−tref", lambda e: f"{e['derived']['stated_spinup_days']} [{e['derived']['stated_in']}] · {yn(e['derived']['stated_equals_gap_tstart_minus_tref'])}"))
    L.append(row("antecedent [tref,tstart) inside [tstart,tstop]", lambda e: yn(e["derived"]["antecedent_tref_to_tstart_inside_[tstart,tstop]"])))
    L.append(row("sfincs_map.nc output time axis · first == tstart", lambda e: f"{fmt_axis(e['sfincs_map_nc']['time'])} · {yn(e['sfincs_map_nc']['first_output_equals_tstart'])}"))
    L.append(row("precip_2d.nc time axis", lambda e: fmt_axis(pr(e))))
    L.append(row("precip_2d.nc time units / calendar", lambda e: f"{pr(e)['units']} / {pr(e)['calendar']}"))
    L.append(row("precip_2d.nc steps before tstart · domain-mean mm before tstart / in [tstart,tstop]", lambda e: f"{pr(e)['steps_before_tstart']} · {pr(e)['totals']['domain_mean_mm_before_tstart']} / {pr(e)['totals']['domain_mean_mm_tstart_to_tstop']}"))
    L.append(row("hydromt.log 'Slicing time dim' precip / wind / press", lambda e: " / ".join(yn(e["hydromt_log"]["sliced"].get(k)) for k in ("precip", "wind", "pressure"))))
    L.append(row("wind_2d.nc = press_2d.nc time axis", wp))
    L.append(row("sfincs.dis (s since tref): first→last, rows, rows<tstart", lambda e: dis(e["forcing_in_model_dir"]["disfile"])))
    L.append(row("data/imerg_<slug>.nc time axis (download)", lambda e: fmt_axis(_imerg(e))))
    L.append(row("imerg time units / xarray default → datetime64", lambda e: f"{_imerg(e)['units']} / {'Y' if _imerg(e)['xarray_default_decodes_to_datetime64'] else 'N (cftime, calendar=' + str(_imerg(e)['calendar']) + ')'}"))
    L.append(row("imerg domain-mean mm in [tref,tstart) / [tstart,tstop]", lambda e: f"{_imerg(e)['totals']['domain_mean_mm_before_tstart']} / {_imerg(e)['totals']['domain_mean_mm_tstart_to_tstop']}"))
    L.append(row("data/era5_<slug>.nc time axis (download)", lambda e: fmt_axis(_dl(e, "era5"))))
    L.append(row("data/glofas_<slug>_clean.nc time axis (download)", lambda e: fmt_axis(_dl(e, "glofas"))))
    L.append(row("data/q_outlet.csv first→last (n)", lambda e: qo(e["raw_downloads"]["q_outlet.csv"])))
    L.append(row("deliverable README 'Simulation window' line", _doc))
    L.append(f"Note: precip_2d.nc holds the IMERG mm/h field divided by its 0.5-h step (hydromt `cumulative_input=True`, "
             f"`hydromt_sfincs/sfincs.py:{cum_ln}` `{cum_txt}`) on the model grid, hence ≈2× the imerg_*.nc totals (download bbox incl. buffer); separate finding, outside F5-f.")
    L.append("")
    tr_ln, tr_txt = pick(C["_common.tref"], "d = self.event_date")
    ts_ln, ts_txt = pick(C["_common.tstart"], "d = self.event_date")
    tp_ln, tp_txt = pick(C["_common.tstop"], "d = self.event_date")
    tc = C["template.setup_config"]; tz = C["template.zsini"]
    L.append("## Where `spinup_days` ends up (repo code; line numbers as found in the live worktree at run time)")
    L.append(f"- `skill/scripts/_common.py:{tr_ln}` `{tr_txt}` → **tref only**; `:{ts_ln}` `{ts_txt}` → tstart has no spinup term; `:{tp_ln}` `{tp_txt}`.")
    L.append(f"- `skill/templates/sfincs_build.yml.tmpl:{tc['line']}-{tc['line']+3},{tz['line']}` " + ", ".join(f"`{v.strip()}`" for v in list(tc["lines"].values())[1:4]) +
             f", `{pick(tz, 'zsini')[1]}`; rendered by `build_model.py:{C['build_model.render']['line']}`. The pipeline sets no `tspinup`; hydromt_sfincs writes its default "
             f"`sfincs_input.py:{C['hydromt_sfincs.tspinup_default']['line']}` `{pick(C['hydromt_sfincs.tspinup_default'], 'tspinup')[1]}`.")
    L.append(f"- Downloads span tref→tstop: `download_imerg.py:{C['download_imerg.window']['line']}` `{pick(C['download_imerg.window'], 'cfg.tref')[1]}`, "
             f"`download_era5.py:{C['download_era5.window']['line']}` `{pick(C['download_era5.window'], 'cfg.tref')[1]}`, `download_glofas.py:{C['download_glofas.window']['line']}`; "
             f"`prep_q_at_outlets.py:{C['prep_q.hours_tref_tstop']['line']}` `{pick(C['prep_q.hours_tref_tstop'], 'date_range')[1]}`; "
             f"`build_model.py:{pick(C['build_model.dis_from_tref'], '- tref)')[0]}` `{pick(C['build_model.dis_from_tref'], '- tref)')[1]}` (sfincs.dis rows start at tref).")
    L.append(f"- hydromt_sfincs `sfincs.py:{C['hydromt_sfincs.get_model_time']['line']}` `get_model_time()` returns (tstart, tstop); `setup_precip_forcing_from_grid` passes "
             f"`time_tuple=self.get_model_time()` (`sfincs.py:{C['hydromt_sfincs.precip_time_tuple']['line']}`; wind/pressure likewise). hydromt `rasterdataset.py:{C['hydromt.slice_condition']['line']}` "
             f"`_slice_temporal_dimension` slices only if `np.issubdtype(ds[\"time\"].dtype, np.datetime64)`; the IMERG files kept with GPM `calendar: julian` decode to cftime objects → no slice "
             f"(Strymonas, Emilia: precip_2d.nc starts at tref). `bias_correct_imerg.py:{C['bias_correct_imerg.time_reencode']['line']}` re-encodes time as proleptic_gregorian "
             f"(`:{C['bias_correct_imerg.encoding']['line']}`) → Pineios/Mandra/Valencia precip sliced to tstart.")
    L.append("")
    L.append(f"## SFINCS behaviour relied on (manual v2.3.0 mt Faber; {J['manual']['method']}; L = `\\n`-split line of the pdftotext dump)")
    for k in ("time_management", "tref", "tstart", "tstop", "tspinup", "spinup_meteo", "zsini", "dis_time_ref", "rain_time_ref"):
        q = M[k]
        L.append(f"- `{k}`: " + (f"L{q['line']}: {q['text']}" if isinstance(q, dict) and q.get("found") else str(q)))
    L.append("- Forcing stamped before tstart exists in: precip_2d.nc (Strymonas 336 steps, Emilia 672 steps; 0 elsewhere), sfincs.dis (all four Q runs: rows from tref) and every raw download. "
             "SFINCS cannot use it: the manual defines the runtime as tstart→tstop and `tspinup` as a period *after* tstart; locally, all five `sfincs_map.nc` start their `time` axis at tstart (not tref) and end at tstop. "
             "No explicit manual sentence 'forcing before tstart is ignored' was found; this follows from the runtime definition above.")
    L.append("")
    L.append("## Manuscript wording (verbatim lines, `D:/ELKAK/manuscript/text/paper_v5_text.txt`)")
    for ln, txt in J["manuscript"]["hits"].items():
        L.append(f"- `:{ln}` " + (txt if len(txt) < 260 else txt[:257] + "..."))
    L.append("")
    L.append(f"## Files read ({len(J['files_read'])})")
    groups: dict[str, list[str]] = {}
    prefixes = [s(PY_SITE), s(REPO), "D:/ELKAK/ELKAK2/NHESS/runs", "D:/ELKAK/deliverables/bundles",
                "D:/ELKAK/implementation", "D:/ELKAK/manuscript"]
    for f in J["files_read"]:
        pre = next((p for p in prefixes if f.startswith(p + "/")), None)
        if pre is None:
            groups.setdefault("other", []).append(f)
        else:
            groups.setdefault(pre + "/", []).append(f[len(pre) + 1:])
    for top, names in groups.items():
        L.append(f"- `{top}`: " + ", ".join(sorted(names)))
    out.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual-txt", default=None, help="optional pdftotext -layout dump of the SFINCS manual")
    args = ap.parse_args()

    J: dict = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
               "python": sys.executable, "xarray": xr.__version__, "pandas": pd.__version__,
               "repo_worktree": s(REPO),
               "sfincs_behaviour_relied_on": (
                   "SFINCS integrates from tstart to tstop (manual 'Time management': model runtime = tref/tstart/tstop; "
                   "tspinup is a damping period AFTER tstart). Forcing stamped before tstart (times are seconds/minutes since "
                   "tref) lies outside the integration window and is not simulated. Local evidence: sfincs_map.nc first "
                   "output time == tstart for all five runs."),
               "events": {}}
    for ev in EVENTS:
        print(f"[audit] {ev['label']}", flush=True)
        J["events"][ev["key"]] = audit_event(ev)
        J["events"][ev["key"]]["key"] = ev["key"]
    print("[audit] code / manuscript / manual quotes", flush=True)
    J["code_quotes"] = code_quotes()
    J["manuscript"] = manuscript_quotes()
    J["manual"] = manual_quotes(args.manual_txt)
    J["files_read"] = dict(sorted(FILES_READ.items()))
    J["quote_anchors_not_found"] = [k for k, v in J["code_quotes"].items() if isinstance(v, dict) and not v.get("found", True)]

    out_json, out_md = HERE / "F5_f.json", HERE / "F5_f.md"
    out_json.write_text(json.dumps(J, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    write_md(J, out_md)
    n = len(out_md.read_text(encoding="utf-8").split("\n")) - 1
    print(f"wrote: {out_json}\nwrote: {out_md}  ({n} lines)")
    if J["quote_anchors_not_found"]:
        print("WARNING anchors not found:", J["quote_anchors_not_found"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
