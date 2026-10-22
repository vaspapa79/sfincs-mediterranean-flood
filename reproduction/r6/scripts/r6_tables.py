"""CODE-16 B (2026-10-21) — the manuscript tables (main text T2–T6, supplement S1–S11) from the JSON records, nothing typed.
CODE-19 (2026-10-22): baseline rows in S1 and S3, the S4 lead-in label, the new S11 (Manning lookup).

Every cell is read programmatically from the records listed per table in TABLES_MANIFEST.md (paths relative to the repository
unless absolute). Unless a table says otherwise: strict scores at h_max > 0.10 m on the v1.4 evaluation universe (AOI ∩ active
minus WorldCover 80 ∪ open sea, both sides) for the canonical run of record per event (v1.4.2 where re-run, else v1.4.0); Crete =
the Tzermiado tier-1 block (reproduction/emsr933/rule_ledger.md §8 item 3; no all-AOI union score). Formats: scores 3 decimals,
B 2, km² 1, cells 0. Earlier-release columns are labelled 'release v1.3.0'.

Usage: python -I r6_tables.py --repo <worktree> --r5-dir <dir with supplement_R5_tables.json> [--out-dir <repo>/reproduction/r6]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

NA = "—"
EVENTS = [  # key, label, canonical run of record, baseline run, held-out
    ("pineios", "Pineios (EMSR692)", "pineios_enhanced_v142", "pineios_baseline_gridmatched", False),
    ("mandra", "Mandra (EMSR257)", "mandra_enhanced", "mandra_baseline", False),
    ("strymonas", "Strymonas (EMSR122)", "strymonas_enhanced_postD6_v142", "strymonas_baseline", False),
    ("valencia", "Valencia (EMSR773)", "valencia_enhanced_164_v142", None, True),
    ("emilia", "Emilia-Romagna (EMSR664)", "emilia_enhanced_8aoi_v142", None, True),
    ("crete", "Crete (EMSR933), Tzermiado tier 1", "crete_canonical_r2on", "crete_baseline", True),
]
THRS = ("h>0.05m", "h>0.10m", "h>0.25m", "h>0.50m")


# ----------------------------------------------------------------------------------------------------------------- formatting
def _num(x):
    """Numbers stored as text in some records (CSV-derived JSON) are formatted like numbers; other text passes through."""
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return x
    return x


def _fmt(spec):
    def f(x):
        x = _num(x)
        if x is None:
            return NA
        if isinstance(x, str):
            return x
        if isinstance(x, float) and math.isnan(x):
            return NA
        return format(int(round(x)), "d") if spec == "int" else format(x, spec)
    return f


f3 = _fmt(".3f")


f2 = _fmt(".2f")


f1 = _fmt(".1f")


f0 = _fmt("int")


s3 = _fmt("+.3f")


s2 = _fmt("+.2f")


fg = _fmt("g")


def bracket(new: str, old: str | None) -> str:
    return new if old in (None, NA) else f"{new} [{old}]"


# ----------------------------------------------------------------------------------------------------------------- context
class Ctx:
    def __init__(self, repo: Path, r5_dir: Path | None):
        self.repo = repo
        self.R = repo / "reproduction" / "v14_rerun"
        self.r5_dir = r5_dir
        self.reads: set[str] = set()
        self._j: dict = {}
        sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(repo / "validation"))
        from _common import load_config
        self._load_config = load_config

    def rel(self, p: Path) -> str:
        p = Path(p)
        try:
            return p.resolve().relative_to(self.repo).as_posix()
        except ValueError:
            return p.as_posix()

    def j(self, p: Path | str, required: bool = True):
        p = Path(p) if Path(p).is_absolute() else self.repo / p
        if p not in self._j:
            if not p.exists():
                if required:
                    raise FileNotFoundError(p)
                return None
            self._j[p] = json.loads(p.read_text(encoding="utf-8"))
        self.reads.add(self.rel(p))
        return self._j[p]

    def res(self, run: str, kind: str = "v14_newmask", required: bool = True):
        return self.j(self.R / "results" / f"{run}_{kind}.json", required)

    def cfg(self, run: str):
        p = self.R / "configs" / f"{run}.yaml"
        self.reads.add(self.rel(p))
        return self._load_config(["--config", str(p)])

    def note(self, path: str):
        self.reads.add(path)


def strict(ctx: Ctx, run: str, thr: str = "h>0.10m"):
    v = ctx.res(run)
    return v["validation"]["strict_threshold_sweep"][thr]


def cell_km2(ctx: Ctx, run: str) -> float:
    v = ctx.res(run)["validation"]
    s = v["strict_threshold_sweep"]["h>0.10m"]
    return v["evaluation_area_km2"] / (s["tp"] + s["fp"] + s["fn"] + s["tn"])


def base_of(run: str) -> str:
    return re.sub(r"_v14[12]$", "", run)


def release_base(run: str) -> str:
    """The release v1.3.0 run a v1.4 run re-runs: strip the v1.4.x suffix and the post-D6 label (strymonas_enhanced_postD6 = strymonas_enhanced)."""
    return re.sub(r"_postD6$", "", base_of(run))


def crete_aoi_names(ctx) -> dict:
    snap = ctx.j(ctx.repo / "reproduction" / "emsr933" / "ems_api_snapshot_20261019T133437Z.json")["results"][0]
    return {f"{int(a['number']):02d}": a["name"] for a in snap["aois"]}


def run_label(ctx, run: str) -> str:
    """The run record's label, without the v1.4.x re-run prefix."""
    lab = (ctx.res(run, "record", required=False) or {}).get("label") or run
    m = re.match(r"v1\.4\.[12] \([^)]*\) re-run of [\w]+: (.*)$", lab)
    lab = m.group(1) if m else lab
    return re.sub(r"^S1 (row \d+|prose): ", "", lab)


def tier1(ctx: Ctx, run: str) -> dict:
    return ctx.j(ctx.R / "phase5" / f"{run}_tiers.json")["aois"]["03"]


def rain_json(ctx: Ctx, run: str):
    for p in (ctx.R / "phase4" / "rain" / f"{run}_v14.json", ctx.R / "code16" / "rain" / f"{run}_v14.json"):
        if p.exists():
            return ctx.j(p)
    return None


def r2_factor(ctx: Ctx, run: str):
    cfg = ctx.cfg(run)
    r2 = cfg.raw.get("rain_bias_correct") or {}
    if not r2.get("enabled"):
        return "R2 off"
    rj = rain_json(ctx, run)
    if rj and rj.get("r2_realised") and rj["r2_realised"].get("factor") is not None:
        return f"×{rj['r2_realised']['factor']:.3f}"
    return "not recorded"


def release_v13_csi(ctx: Ctx, run: str, r5_s1: dict | None = None):
    """release v1.3.0 CSI: the run's record published_strict, else <base>_v13_publishedmask.json, else the R5 Table S1 row."""
    rec = ctx.res(run, "record", required=False) or {}
    ps = rec.get("published_strict")
    if ps and ps.get("csi") is not None:
        return f3(ps["csi"]), "record published_strict"
    v = ctx.res(release_base(run), "v13_publishedmask", required=False)
    if v:
        return f3(v["validation"]["strict_threshold_sweep"]["h>0.10m"]["csi"]), "v13_publishedmask"
    if r5_s1 and run in r5_s1:
        return r5_s1[run], "R5 Table S1"
    return NA, None


def leadin_label(w: dict, w0: dict) -> str:
    """S4 label of the Strymonas lead-in sensitivity (CODE-19 C3): the simulated lead-in is the extra pre-event days over the
    canonical window; both windows are read from the run configs."""
    extra = int(w["pre_event_days"]) - int(w0["pre_event_days"])
    return f"{extra}-day lead-in simulated ({int(w['pre_event_days'])} d before the event day; canonical {int(w0['pre_event_days'])} d)"


# ESA WorldCover v200 legend (Zanaga et al. 2022, product user manual): class code -> name
WORLDCOVER_CLASSES = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland", 50: "Built-up", 60: "Bare / sparse vegetation",
                      70: "Snow and ice", 80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss and lichen"}


def manning_rows(repo: Path) -> list:
    """(WorldCover class code, class name, Manning n) read from the pipeline's lookup `skill/manning_lookup.csv` — the file
    `prep_inputs.py` copies into every build (CODE-19 C4). Nothing is typed: the file holds the code and n only."""
    rows = []
    with open(repo / "skill" / "manning_lookup.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            code = int(r["landuse"])
            rows.append((code, WORLDCOVER_CLASSES.get(code, "code not in the WorldCover legend"), float(r["N"])))
    return rows


def baseline_label(key: str, label: str) -> str:
    return label + (" — grid-matched ERA5 baseline" if key == "pineios" else " — ERA5T baseline" if key == "crete" else " — ERA5 baseline")


def baseline_sweep_rows(ctx: "Ctx") -> list:
    """S1 rows of the ERA5 (Crete: ERA5T) baselines, same columns as the enhanced rows (CODE-19 C1): events.<run>.baseline_v14.sweep
    of the cross-event JSON (Crete = the tier-1 block, as the enhanced row)."""
    c = ce(ctx); rows = []
    for key, label, run, base, _h in EVENTS:
        if base is None:
            continue
        sw = c["events"][run]["baseline_v14"]["sweep"]
        for t in THRS:
            x = sw[t]
            rows.append([baseline_label(key, label), base, "h_max > " + t[2:-1] + " m", f0(x["tp"]), f0(x["fp"]), f0(x["fn"]), f3(x["csi"]), f3(x["hr"]), f3(x["far"]), f2(x["bias"])])
    return rows


# ----------------------------------------------------------------------------------------------------------------- output
class Writer:
    def __init__(self, ctx: Ctx, out_dir: Path):
        self.ctx = ctx; self.out = out_dir / "tables"; self.out.mkdir(parents=True, exist_ok=True); self.manifest = []

    def begin(self):
        self.ctx.reads = set()

    def emit(self, tid: str, title: str, header: list, rows: list, notes: list, extra: list | None = None):
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        md = [f"# {tid} — {title}", "", f"Generated {now} by `reproduction/r6/scripts/r6_tables.py`; every cell read from the records listed in `reproduction/r6/TABLES_MANIFEST.md`.", ""]
        md += [n for n in notes] + [""]
        md += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        md += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
        with open(self.out / f"{tid}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh); w.writerow(header); w.writerows(rows)
        n_rows = len(rows)
        for sub_id, sub_title, sub_header, sub_rows, sub_notes in (extra or []):
            md += ["", f"## {sub_title}", ""] + list(sub_notes) + ([""] if sub_notes else []) + ["| " + " | ".join(sub_header) + " |", "|" + "---|" * len(sub_header)]
            md += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in sub_rows]
            with open(self.out / f"{sub_id}.csv", "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh); w.writerow(sub_header); w.writerows(sub_rows)
            n_rows += len(sub_rows)
        (self.out / f"{tid}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        self.manifest.append({"table": tid, "title": title, "rows": n_rows, "files": [f"tables/{tid}.md", f"tables/{tid}.csv"] + [f"tables/{e[0]}.csv" for e in (extra or [])],
                              "sources": sorted(self.ctx.reads), "generated_utc": now})
        print(f"{tid}: {n_rows} rows, {len(self.ctx.reads)} sources", flush=True)


# ----------------------------------------------------------------------------------------------------------------- main text
def t2(ctx: Ctx, W: Writer):
    import pyproj
    import xarray as xr
    W.begin()
    geod = pyproj.Geod(ellps="WGS84")
    cols = {}; diffs = []
    for key, label, run, _b, _h in EVENTS:
        cfg = ctx.cfg(run); rec = ctx.res(run, "record"); g = cfg.raw["grid"]; w = cfg.window
        model = cfg.paths["model_dir"]
        n_act = rec["coastal_prep"]["n_active_after_expected"]
        with xr.open_dataset(model / "sfincs_map.nc") as ds:
            n_msk = int((ds["msk"].values > 0).sum())
        ctx.note((model / "sfincs_map.nc").as_posix())
        if n_msk != n_act:   # report the grid SFINCS ran; keep the build record's expectation beside it
            diffs.append(f"{label}: msk > 0 in sfincs_map.nc {n_msk} vs coastal_prep.n_active_after_expected {n_act} (difference {n_msk - n_act:+d})")
        bnd = model / "sfincs.bnd"
        n_bnd = sum(1 for ln in bnd.read_text(encoding="utf-8").splitlines() if ln.strip()) if bnd.exists() else 0
        ctx.note(bnd.as_posix())
        r2 = cfg.raw.get("rain_bias_correct") or {}
        if r2.get("enabled"):
            wb = r2["watershed_bbox"]; wb = [float(x) for x in (wb.split(",") if isinstance(wb, str) else wb)]
            area = abs(geod.polygon_area_perimeter([wb[0], wb[2], wb[2], wb[0]], [wb[1], wb[1], wb[3], wb[3]])[0]) / 1e6
            r2a, r2t = f1(area), f1(float(r2["target_mm"]))
        else:
            r2a, r2t = "R2 off", "R2 off"
        cols[label] = [fg(g["res"]), fg(g["subgrid_pixels"]), f1(g["res"] / g["subgrid_pixels"]), f0(n_msk), fg(g["zmax"]), f0(n_bnd),
                       f0(w["spinup_days"]), f0(w["pre_event_days"]), f0(w["post_event_days"]), f0((cfg.tstop - cfg.tstart).total_seconds() / 86400),
                       r2a, r2t, f0(rec["sfincs_total_time_s"])]
    names = ["Δx (m)", "subgrid pixels n_sub", "effective Δx = Δx / n_sub (m)", "active cells (msk ≥ 1)", "z ceiling z_max of the active mask (m)",
             "water-level boundary points", "forcing lead-in (d, not simulated)", "simulated pre-event (d)", "simulated post-event (d, after the event day)",
             "simulated window tstart–tstop (d)", "R2 bias window (km²)", "R2 anchor (mm)", "SFINCS wall-clock, canonical run (s)"]
    header = ["quantity"] + [c.replace(", Tzermiado tier 1", "") for c in cols]
    rows = [[n] + [cols[c][i] for c in cols] for i, n in enumerate(names)]
    W.emit("T2", "Grid and window per event (canonical run of record)", header, rows,
           ["Sources: the run configs (`reproduction/v14_rerun/configs/<run>.yaml`, YAML + `load_config` window), the model output (active cells = msk > 0 in `sfincs_map.nc`, compared with the run record's "
            "`coastal_prep.n_active_after_expected`), the run records (SFINCS wall-clock `sfincs_total_time_s`) and the model's `sfincs.bnd`. R2 bias window = geodesic area (WGS84) of `rain_bias_correct.watershed_bbox`. "
            "The simulated window spans pre-event days + the event day + post-event days."] + ([f"Active-cell check: {'; '.join(diffs)}."] if diffs else ["Active-cell check: the msk > 0 count equals the build record's expectation for every event."]))


def ce(ctx: Ctx):
    return ctx.j(ctx.R / "phase4" / "cross_event_v14_v142.json")


def t3(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    for key, label, run, _b, _h in EVENTS:
        e = c["events"][run]["enhanced_v14"]; s = e["strict"]
        rows.append([label, run, f3(s["csi"]), f3(s["hr"]), f3(s["far"]), f2(s["bias"]), f3(s["gss"]), f3(e["fuzzy_r1"]["csi"]), f1(e["eval_km2"]), f1(e["obs_km2"])])
    W.emit("T3", "Cross-event skill, strict and fuzzy (r = 1)", ["event", "run of record", "CSI", "HR", "FAR", "B", "GSS", "fuzzy r=1 CSI", "universe km²", "observed km²"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` events.<run>.enhanced_v14 (strict, fuzzy_r1, eval_km2, obs_km2); Crete = the tier-1 block of `phase5/crete_canonical_r2on_tiers.json`. "
            "Observed km² = the validator's rasterisation (all_touched, as for every event)."])


def t4(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    for key, label, run, base, _h in EVENTS:
        if base is None:
            continue
        ev = c["events"][run]; b = ev["baseline_v14"]["strict"]; n = ev["enhanced_v14"]["strict"]
        lab = label + (" — grid-matched baseline" if key == "pineios" else " — ERA5T baseline" if key == "crete" else "")
        rows.append([lab, base, run] + [f3(b["csi"]), f3(b["hr"]), f3(b["far"]), f2(b["bias"])] + [f3(n["csi"]), f3(n["hr"]), f3(n["far"]), f2(n["bias"])] +
                    [s3(n["csi"] - b["csi"]), s3(n["hr"] - b["hr"]), s3(n["far"] - b["far"]), s2(n["bias"] - b["bias"])])
    W.emit("T4", "Enhanced minus baseline (same harness, same universe)", ["event", "baseline run", "enhanced run", "base CSI", "base HR", "base FAR", "base B", "enh. CSI", "enh. HR", "enh. FAR", "enh. B", "Δ CSI", "Δ HR", "Δ FAR", "Δ B"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` events.<run>.baseline_v14 / enhanced_v14 strict; Δ = enhanced − baseline. Baselines are ERA5 rain-on-grid without wind/IB/Q (Crete: ERA5T)."])


def rules_realised(cfg, rj=None) -> list:
    raw = cfg.raw
    rs = raw.get("rain_source")
    r1 = (rs.get("name") if isinstance(rs, dict) else str(rs))
    srcs = (rj or {}).get("sources") or {}
    src = ((srcs.get("imerg_raw") or {}).get("file_attrs") or {}).get("source") or ((srcs.get("imerg") or {}).get("file_attrs") or {}).get("source")
    r1 = f"{r1}: {src}" if src else r1
    r2 = raw.get("rain_bias_correct") or {}
    q = raw.get("upstream_q") or {}
    n_inj = sum(1 for p in (q.get("src_points") or []) if p.get("inject", True))
    inf = raw.get("infiltration") or {}
    inf_s = "off" if not inf.get("enabled") else ("on (" + ", ".join(f"{k} {inf[k]}" for k in ("type", "hsg", "amc", "qinf") if k in inf) + ")")
    return [r1, ("on" if r2.get("enabled") else "off"), (f"on ({n_inj} injected points)" if q.get("enabled") else "off"), inf_s,
            ("on" if (raw.get("coastal_bc") or {}).get("enabled") else "off"), ("on" if (raw.get("wind_pressure") or {}).get("enabled") else "off")]


def t5(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    for key, label, run, _b, held in EVENTS:
        if not held:
            continue
        cfg = ctx.cfg(run); e = c["events"][run]["enhanced_v14"]; s = e["strict"]; cs = e["csi_star"]
        r2 = cfg.raw.get("rain_bias_correct") or {}
        rows.append([label, run] + rules_realised(cfg, rain_json(ctx, run)) + [r2_factor(ctx, run), (f1(float(r2["target_mm"])) if r2.get("enabled") else "R2 off"),
                     f3(s["csi"]), f3(s["hr"]), f3(s["far"]), f2(s["bias"]), f3(s["gss"]), f"{f3(cs['csi'])} ({cs['threshold']})", f1(e["obs_km2"]), f1(e["eval_km2"])])
    W.emit("T5", "Held-out events: the rule as realised and the skill", ["event", "run of record", "R1 precipitation", "R2 bias factor", "R3 upstream Q", "R4 SCS-CN", "R5 coastal IB", "R6 wind + MSLP",
                                                                          "R2 factor (realised)", "R2 anchor (mm)", "CSI", "HR", "FAR", "B", "GSS", "CSI* (threshold)", "observed km²", "universe km²"], rows,
           ["R1–R6 as realised = the run config's blocks (`rain_source` with the product recorded in the IMERG file the run read, `rain_bias_correct`, `upstream_q` with the number of injected points, `infiltration`, `coastal_bc`, `wind_pressure`). "
            "R2 factor = `r2_realised.factor` of the run's rain diagnostics (`phase4/rain/<run>_v14.json`). Skill from `phase4/cross_event_v14_v142.json`; CSI* = the best CSI over the threshold sweep."])


def t6(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    for key, label, run, _b, _h in EVENTS:
        ev = c["events"][run]; e = ev["enhanced_v14"]; s = e["strict"]; k = e["skill"]; cs = e["csi_star"]
        o = ev.get("enhanced_v13_published")
        os_, ok, oc = (o["strict"], o["skill"], o["csi_star"]) if o else (None, None, None)
        rows.append([label, run, bracket(f3(s["csi"]), f3(os_["csi"]) if o else None), bracket(f3(k["sedi"]), f3(ok["sedi"]) if o else None),
                     bracket(f3(k["pss"]), f3(ok["pss"]) if o else None), bracket(f3(k["pofd"]), f3(ok["pofd"]) if o else None),
                     bracket(f2(s["bias"]), f2(os_["bias"]) if o else None), bracket(f"{f3(cs['csi'])} ({cs['threshold']})", f"{f3(oc['csi'])} ({oc['threshold']})" if o else None),
                     bracket(f2(cs["bias"]), f2(oc["bias"]) if o else None)])
    W.emit("T6", "Base-rate-robust skill", ["event", "run of record", "CSI", "SEDI", "PSS", "POFD", "B", "CSI* (threshold)", "B*"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` events.<run>.enhanced_v14 (strict, skill = `validation/skill_scores.py` on the strict contingency, csi_star = the best CSI over the sweep and its bias); "
            "release v1.3.0 values in brackets (`enhanced_v13_published`: the release v1.3.0 model on the release v1.3.0 mask) where they exist."])


# ----------------------------------------------------------------------------------------------------------------- supplement
def tab_s1(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    for key, label, run, _b, _h in EVENTS:
        sw = c["events"][run]["enhanced_v14"]["sweep"]
        for t in THRS:
            x = sw[t]
            rows.append([label, run, "h_max > " + t[2:-1] + " m", f0(x["tp"]), f0(x["fp"]), f0(x["fn"]), f3(x["csi"]), f3(x["hr"]), f3(x["far"]), f2(x["bias"])])
    rows += baseline_sweep_rows(ctx)
    W.emit("S1", "Threshold sweeps", ["event", "run", "threshold", "TP", "FP", "FN", "CSI", "HR", "FAR", "B"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` events.<run>.enhanced_v14.sweep (runs of record) and events.<run>.baseline_v14.sweep (the ERA5 "
            "rain-on-grid baselines; Pineios grid-matched; Crete ERA5T) — strict contingency per depth threshold, cells, on the same v1.4 universe as the "
            "enhanced run (Crete: the tier-1 block). Baseline rows added for the revision (CODE-19 C1); their fuzzy, one-sided, buffer and "
            "time-matched scores are the baseline rows of S3."])


def aoi_tokens(ctx: Ctx, run: str) -> list:
    cfg = ctx.cfg(run)
    d = cfg.paths["data_dir"] / "ems_polygons"
    files = sorted(p.name for p in d.rglob("*.shp") if re.search(r"area_?of_?interest", p.name, re.I))
    toks = []
    for f in files:
        m = re.search(r"_(AOI\d\d)_", f) or re.search(r"_(\d\d[A-Z]+)_", f)
        if m and m.group(1) not in toks:
            toks.append(m.group(1))
    return toks


S2_HEADER = ["event", "run", "AOI", "AOI file (product)", "active km²", "observed km²", "modelled km² (h_max > 0.10 m)", "TP", "CSI", "HR", "FAR", "fuzzy r=1 CSI"]
S2_DIGEST_HEADER = ["AOI", "observed km²", "modelled km² (h_max > 0.10 m)", "CSI", "HR", "FAR", "fuzzy r=1 CSI"]


def s2_baseline_digest(header: list, rows: list, run: str = "strymonas_baseline") -> list:
    """CODE-20 B2: the per-area rows of one run (default the Strymonas ERA5 baseline) reduced to the digest columns of the
    supplement's S2 digest; every cell is the S2 cell itself (no re-formatting)."""
    i = {h: k for k, h in enumerate(header)}
    return [[r[i[c]] for c in S2_DIGEST_HEADER] for r in rows if r[i["run"]] == run]


def tab_s2(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    plan = [("Pineios (EMSR692)", ["pineios_enhanced_v142"]), ("Mandra (EMSR257)", ["mandra_enhanced"]),
            ("Strymonas (EMSR122)", ["strymonas_baseline", "strymonas_v1_prefix_src_v142", "strymonas_enhanced_postD6_v142"]),
            ("Valencia (EMSR773)", ["valencia_enhanced_164_v142"]), ("Emilia-Romagna (EMSR664)", ["emilia_enhanced_8aoi_v142"])]
    for label, runs in plan:
        for run in runs:
            per = ctx.res(run)["validation"]["per_aoi_canonical_and_r1"]
            for tok in aoi_tokens(ctx, run):
                a = next((x for x in per if f"_{tok}_" in x["aoi_file"]), None)
                if a is None:
                    rows.append([label, run, tok, "—", "no active cell (outside the model domain)", NA, NA, NA, NA, NA, NA, NA]); continue
                st = a["strict"]
                ck = a["active_km2"] / (st["tp"] + st["fp"] + st["fn"] + st["tn"])
                rows.append([label, run, tok, a["aoi_file"], f1(a["active_km2"]), f1(a["ems_wet_km2_strict"]), f1((st["tp"] + st["fp"]) * ck), f0(st["tp"]), f3(st["csi"]), f3(st["hr"]), f3(st["far"]), f3(a["fuzzy_r1"]["csi"])])
    tj = ctx.j(ctx.R / "phase5" / "crete_canonical_r2on_tiers.json"); names = crete_aoi_names(ctx)
    for code in sorted(set(tj["aois"]) | set(names)):
        a = tj["aois"].get(code)
        tier = a["tier"] if a else 3
        if a is None or tier == 3:
            rows.append(["Crete (EMSR933)", "crete_canonical_r2on", f"AOI{code} {names.get(code, '')} (tier 3)".replace("  ", " "), "—", "no product released", NA, NA, NA, NA, NA, NA, NA]); continue
        if tier == 1:
            st = a["strict_threshold_sweep"]["h>0.10m"]
            rows.append(["Crete (EMSR933)", "crete_canonical_r2on", f"AOI{code} {a['name']} (tier 1, scored)", "; ".join(a["aoi_files"]), f1(a["universe_km2"]), f1(a["observed_km2"]), f1(a["modelled_km2_h_gt_0p10"]),
                         f0(st["tp"]), f3(st["csi"]), f3(st["hr"]), f3(st["far"]), f3(a["fuzzy_at_h_gt_0p10m"]["r=1"]["csi"])])
        else:
            rows.append(["Crete (EMSR933)", "crete_canonical_r2on", f"AOI{code} {a['name']} (tier 2: km² only)", "; ".join(a["aoi_files"]), f1(a["universe_km2"]), f1(a["observed_km2"]),
                         f1(a["modelled_km2_h_gt_0p10"]), NA, NA, NA, NA, NA])
    W.emit("S2", "Per-AOI skill", S2_HEADER, rows,
           ["Source: `results/<run>_v14_newmask.json` validation.per_aoi_canonical_and_r1 (each AOI scored on its own polygon ∩ the v1.4 universe). An AOI with several product versions is reported "
            "with the first AOI file of the validator's list, as in the R5 per-AOI tables; AOIs are listed from the event's AOI files, and one whose polygon holds no active cell is marked. "
            "Modelled km² = (TP + FP) × cell area inside the AOI universe. Crete AOI names from the EMS API snapshot of 2026-10-19T13:34:37Z. "
            "Crete: `phase5/crete_canonical_r2on_tiers.json` (tier 1 scored; tier 2 observed vs modelled km² at h_max > 0.10 m only; tier 3 no product)."],
           extra=[("S2_baseline_digest", "Strymonas ERA5-baseline per-area rows in the digest columns (CODE-20 B2)", S2_DIGEST_HEADER, s2_baseline_digest(S2_HEADER, rows),
                   ["The rows of this table for run `strymonas_baseline` (01STRYMONAS, 02BALTOTOPI, 03ACHINOS, 04MAVROTHALASSA), reduced to the columns of the supplement's S2 digest; "
                    "cells identical to the rows above."])])


def tab_s3(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []
    ct = ctx.j(ctx.R / "code16" / "crete_tier1_diagnostics.json")["runs"]["crete_canonical_r2on"]
    for key, label, run, _b, _h in EVENTS:
        ev = c["events"][run]; e = ev["enhanced_v14"]
        if key == "crete":
            tb = {b: ct["truth_buffer"][b]["csi"] for b in ("-20", "0", "20")}
            tm = {"full": ct["time_matched"]["full"]["csi"], "to_earliest": ct["time_matched"]["to_earliest"]["csi"], "to_latest": ct["time_matched"]["to_latest"]["csi"]}
        else:
            tb = ev["enhanced_truth_buffer"]; tm = ev["enhanced_time_matched"]
        rows.append([label, run] + [f3(e["fuzzy"][r]) for r in ("0", "1", "2", "3")] + [f3(e["fuzzy_model_oriented_r1"]), f3(e["fuzzy_obs_oriented_r1"])] +
                    [f3(tb["-20"]), f3(tb["0"]), f3(tb["20"])] + [f3(tm["full"]), f3(tm["to_earliest"]), f3(tm["to_latest"])])
    # baseline rows (CODE-19 C1): fuzzy / one-sided from baseline_v14, buffer and time-matched from the baseline_* blocks; Crete baseline
    # tier-1 diagnostics from code19/crete_tier1_diagnostics_baseline.json (the cross-event Crete baseline blocks are all-AOI union)
    cb = ctx.j(ctx.R / "code19" / "crete_tier1_diagnostics_baseline.json", required=False)
    for key, label, run, base, _h in EVENTS:
        if base is None:
            continue
        ev = c["events"][run]; b = ev["baseline_v14"]
        if key == "crete":
            cbr = (cb or {}).get("runs", {}).get(base)
            tb = {k: cbr["truth_buffer"][k]["csi"] for k in ("-20", "0", "20")} if cbr else {"-20": None, "0": None, "20": None}
            tm = {k: cbr["time_matched"][k]["csi"] for k in ("full", "to_earliest", "to_latest")} if cbr else {"full": None, "to_earliest": None, "to_latest": None}
        else:
            tb = ev["baseline_truth_buffer"]; tm = ev["baseline_time_matched"]
        rows.append([baseline_label(key, label), base] + [f3(b["fuzzy"][r]) for r in ("0", "1", "2", "3")] + [f3(b["fuzzy_model_oriented_r1"]), f3(b["fuzzy_obs_oriented_r1"])] +
                    [f3(tb["-20"]), f3(tb["0"]), f3(tb["20"])] + [f3(tm["full"]), f3(tm["to_earliest"]), f3(tm["to_latest"])])
    W.emit("S3", "Fuzzy and reference uncertainty", ["event", "run", "fuzzy r=0", "r=1", "r=2", "r=3", "model-oriented r=1", "obs-oriented r=1", "truth −20 m", "truth 0 m", "truth +20 m",
                                                     "time-matched: full window", "h_max to earliest acquisition", "h_max to latest acquisition"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` (fuzzy, one-sided fuzzy, enhanced_/baseline_truth_buffer, enhanced_/baseline_time_matched; files `phase4/truth_buffer/`, `phase4/time_matched/`). "
            "Crete: the tier-1 block — truth buffer and time-matched from `code16/crete_tier1_diagnostics.json` (canonical) and `code19/crete_tier1_diagnostics_baseline.json` (ERA5T baseline); "
            "the Phase-4 Crete diagnostics were computed on the all-AOI union, which §8-3 excludes. Baseline rows (ERA5 rain-on-grid; Pineios grid-matched; Crete ERA5T) added for the revision (CODE-19 C1). "
            "Fuzzy r = dilation radius in cells (both sides); one-sided: model-oriented dilates the observation, observation-oriented dilates the model."])


def sens_row(ctx: Ctx, group: str, label: str, run: str, r5_s1=None, extra: str = "", crete: bool = False):
    if crete:
        a = tier1(ctx, run); st = a["strict_threshold_sweep"]["h>0.10m"]; wet = a["modelled_km2_h_gt_0p10"]
    else:
        st = strict(ctx, run); wet = (st["tp"] + st["fp"]) * cell_km2(ctx, run)
    rel, _src = release_v13_csi(ctx, run, r5_s1)
    return [group, label, run, f3(st["csi"]), f3(st["hr"]), f3(st["far"]), f2(st["bias"]), f3(st["gss"]), f1(wet), r2_factor(ctx, run), rel, extra]


def r5_table_s1(ctx: Ctx) -> dict:
    """release v1.3.0 CSI of the Mandra CN rows from the parsed R5 supplement Table S1 (rows matched by HSG/AMC label)."""
    if not ctx.r5_dir:
        return {}
    p = ctx.r5_dir / "supplement_R5_tables.json"
    if not p.exists():
        return {}
    t = next(t for t in json.loads(p.read_text(encoding="utf-8")) if t["id"] == "Table S1")
    ctx.note("<--r5-dir>/supplement_R5_tables.json (Table S1, parsed from NHESS_supplement_R5_clean.docx by scripts/extract_docx.py; outside the repository)")
    hdr = t["rows"][0]; ci = hdr.index("CSI")
    m = {"mandra_cn_a15": "CN = 15", "mandra_cn_a58": "CN ≈ 58", "mandra_cn_b_default": "default lookup", "mandra_cn_d_amc3": "HSG-D AMC-III"}
    out = {}
    for run, tok in m.items():
        r = next((r for r in t["rows"][1:] if tok in r[0]), None)
        if r:
            out[run] = f"{r[ci]} (R5 Table S1)"
    return out


def tab_s4(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    r5s1 = r5_table_s1(ctx)
    dv = ctx.j(ctx.R / "code16" / "d_volumes_code16.json")["runs"]

    def anchor(run):
        r2 = ctx.cfg(run).raw.get("rain_bias_correct") or {}
        return f"{float(r2['target_mm']):g} mm" if r2.get("enabled") else "off"

    def mean_cn(run):
        cr = (ctx.res(run, "record") or {}).get("cn_realised") or {}
        return f"mean CN (active cells) {f1(cr.get('active_mean_cn'))}" if cr else ""

    def qinf(run):
        inp = {k.strip(): v.strip() for k, v in (ln.split("=", 1) for ln in (ctx.cfg(run).paths["model_dir"] / "sfincs.inp").read_text(encoding="utf-8").splitlines() if "=" in ln)}
        ctx.note((ctx.cfg(run).paths["model_dir"] / "sfincs.inp").as_posix())
        return float(inp.get("qinf", "nan"))

    # Pineios
    for run in ("pineios_r2_220_v142", "pineios_r2_295_v142", "pineios_enhanced_v142", "pineios_r2_510_v142"):
        rows.append(sens_row(ctx, "Pineios", f"R2 anchor {anchor(run)}" + (" (canonical)" if run == "pineios_enhanced_v142" else ""), run))
    rows.append(sens_row(ctx, "Pineios", "raw IMERG (R2 off)", "pineios_raw_imerg_v142"))
    rows.append(sens_row(ctx, "Pineios", "SCS-CN on", "pineios_cn_on_v142", extra=mean_cn("pineios_cn_on_v142")))
    rows.append(sens_row(ctx, "Pineios", f"constant infiltration qinf = {qinf('pineios_qinf5_v142'):g} mm/h", "pineios_qinf5_v142"))
    rows.append(sens_row(ctx, "Pineios", "repeat of the canonical configuration (determinism check)", "pineios_timevarying_q_v142"))
    for run, lab in (("pineios_enhanced", "inflow bracket: v1.4.0 canonical (constant inflow, D7)"), ("pineios_enhanced_v141", "inflow bracket: v1.4.1 canonical (main-stem inflow at the Titarisios point, D8)")):
        d = dv[run]
        rows.append(sens_row(ctx, "Pineios", lab, run, extra=f"injected {f1(d['injected']['total_volume_m3'] / 1e6)} Mm³ = {f1(100 * d['injected_over_rain'])} % of rain"))
    d = dv["pineios_enhanced_v142"]
    rows[2][-1] = f"injected {f1(d['injected']['total_volume_m3'] / 1e6)} Mm³ = {f1(100 * d['injected_over_rain'])} % of rain"
    # Mandra
    for run in ("mandra_r2_95", "mandra_r2_140", "mandra_enhanced", "mandra_r2_255"):
        rows.append(sens_row(ctx, "Mandra", f"R2 anchor {anchor(run)}" + (" (canonical)" if run == "mandra_enhanced" else ""), run))
    for run in ("mandra_cn_a15", "mandra_cn_a58", "mandra_cn_b_default", "mandra_cn_d_amc3"):
        inf = ctx.cfg(run).raw.get("infiltration") or {}
        a = next((x for x in ctx.res(run)["validation"]["per_aoi_canonical_and_r1"] if "01MANDRA" in x["aoi_file"]), None)
        rows.append(sens_row(ctx, "Mandra", run_label(ctx, run), run, r5s1, extra=f"{mean_cn(run)}; TP at 01MANDRA {f0(a['strict']['tp']) if a else NA}"))
    rows.append(sens_row(ctx, "Mandra", run_label(ctx, "mandra_cn_d_amc3_manning080"), "mandra_cn_d_amc3_manning080", extra=mean_cn("mandra_cn_d_amc3_manning080")))
    # Strymonas
    for run, lab in (("strymonas_baseline", "baseline (ERA5, no Q)"), ("strymonas_enhanced_postD6_v142", "CN on + Q (canonical)"), ("strymonas_abl_cnoff_q_v142", "CN off + Q"),
                     ("strymonas_abl_qoff_cn", "CN on + Q off"), ("strymonas_v1_prefix_src_v142", "v1 source (pre-fix Kerkini point)")):
        rows.append(sens_row(ctx, "Strymonas", lab, run))
    w, w0 = ctx.cfg("strymonas_leadin7d_v142").window, ctx.cfg("strymonas_enhanced_postD6_v142").window
    rows.append(sens_row(ctx, "Strymonas", leadin_label(w, w0), "strymonas_leadin7d_v142"))   # CODE-19 C3 wording
    # Valencia
    rows.append(sens_row(ctx, "Valencia", "raw IMERG (R2 off)", "valencia_raw_imerg_v142"))
    # Crete (tier-1 block)
    rows.append(sens_row(ctx, "Crete (tier 1)", "R2 off (raw IMERG Late)", "crete_sens_r2off", crete=True))
    for run in ("crete_sens_anchor_224", "crete_sens_anchor_336", "crete_canonical_r2on", "crete_sens_anchor_582"):
        rows.append(sens_row(ctx, "Crete (tier 1)", f"R2 anchor {anchor(run)}" + (" (canonical)" if run == "crete_canonical_r2on" else ""), run, crete=True))
    rows.append(sens_row(ctx, "Crete (tier 1)", f"karst bracket: constant infiltration qinf = {qinf('crete_sens_karst_q1914'):g} mm/h", "crete_sens_karst_q1914", crete=True))
    W.emit("S4", "Sensitivity runs (labelled, never canonical unless marked)", ["group", "configuration", "run", "CSI", "HR", "FAR", "B", "GSS", "modelled wet km²", "R2 factor", "release v1.3.0 CSI", "notes"], rows,
           ["Scores: `results/<run>_v14_newmask.json` (strict, h_max > 0.10 m); modelled wet km² = (TP + FP) × cell area inside the universe; Crete rows = the tier-1 block (`phase5/<run>_tiers.json`). "
            "R2 factor = `r2_realised.factor` of the run's rain diagnostics (`phase4/rain/` or `code16/rain/`). release v1.3.0 CSI = the record's `published_strict` or `<run>_v13_publishedmask.json`; "
            "for the Mandra CN rows the R5 supplement Table S1 value. Labels: anchors and windows from the run configs, qinf from sfincs.inp, the Mandra CN / Manning rows from the run records' labels. "
            "Injected volumes: `code16/d_volumes_code16.json` (simulated window; rain on the active domain)."])


def tab_s5(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    led = ctx.j(ctx.R / "code15" / "source_points_v142.json")
    dv = ctx.j(ctx.R / "code16" / "d_volumes_code16.json")["runs"]
    d9 = ctx.j(ctx.R / "code16" / "d9_residuals.json")
    d9_by = {it["point"]: it for it in d9["items"] if it.get("point")}
    runs = {"pineios": "pineios_enhanced_v142", "strymonas": "strymonas_enhanced_postD6_v142", "valencia": "valencia_enhanced_164_v142", "emilia": "emilia_enhanced_8aoi_v142"}
    summary = []
    for ev, run in runs.items():
        e = led["events"][ev]; notes = {n["name"]: n for n in e["notes"]}; inj = {c["name"]: c for c in dv[run]["injected"]["sources"]}
        samp = {p["name"]: p for p in dv[run]["sampled_points"]}
        for p in e["src_points"]:
            n = notes.get(p["name"], {}); g = n.get("glofas", {}); c = inj.get(p["name"]); sn = (c or {}).get("snap") or {}
            win = p.get("window_deg", 0.1)
            change = n.get("change", "")
            kinds = [k for k, pat in (("not injected", "inject: false"), ("sampling point moved", "sampling point moved"), ("one-cell window", "one-cell window"),
                                      ("injection moved", "injection moved")) if pat in change]
            short = "none" if change.startswith("none") else ("; ".join(kinds) if kinds else change)
            dd = d9_by.get(p["name"])
            d9s = (f"{dd['id']}" + (f" ({dd['offset_km']:.2f} km)" if dd.get("offset_km") is not None else "")) if dd else NA
            rows.append([ev, p["name"], f"({p['lon']}, {p['lat']}, ±{win:g}°)", n.get("named_river", NA), f1(g.get("uparea_km2")),
                         f1(c["peak_m3s"] if c else samp.get(p["name"], {}).get("column_peak_m3s")), (f1(c["volume_m3"] / 1e6) if c else "not injected"),
                         (f"z_b {f2(sn.get('zb_m'))} m, {f0(sn.get('distance_m'))} m, D8 {f1(sn.get('uparea_km2'))} km²" if sn else NA),
                         str(p.get("inject", True)), short, d9s, change])
        r = dv[run]
        summary.append([ev, run, f0(len(r["injected"]["sources"])), f1(r["injected"]["total_volume_m3"] / 1e6), f1(r["rain_on_active_domain"]["rain_volume_m3"] / 1e6),
                        f1(r["rain_on_active_domain"]["active_area_km2"]), f1(100 * r["injected_over_rain"]), f1(r["injected"]["combined_peak_m3s"])])
    W.emit("S5", "Source points of the v1.4.2 ledger", ["event", "point", "sampling cell (lon, lat, window)", "river", "upstream km² (GloFAS v4)", "injected peak m³/s", "injected volume Mm³",
                                                         "injection cell (z_b, snap distance, D8 km²)", "inject", "change vs frozen", "D9 residual", "ledger note (full text)"], rows,
           [f"Sources: the ledger `code15/source_points_v142.json` (resolved {led['utc']}; sampling coordinates, rivers, GloFAS v4 upstream areas, changes), the injected series and snapped cells "
            "`code16/d_volumes_code16.json` (sfincs.dis columns over the simulated window; model/sfincs_src_snap.json), the D9 items `code16/d9_residuals.json`. A point that is not injected shows its sampled peak. "
            "'change vs frozen' classifies the ledger note by its wording; the full note is the last column."],
           extra=[("S5_injected_vs_rain", "Injected volume against rain on the active domain (simulated window)", ["event", "run", "injected sources", "injected Mm³", "rain Mm³", "active km²", "injected / rain %", "combined peak m³/s"],
                   summary, ["Source: `code16/d_volumes_code16.json` (scripts/d_volumes_v142.py --out-stem d_volumes_code16)."])])


CENTRE_LABEL = "AOI-union, truth burned by cell centre (re-scoring sensitivity, no SFINCS run)"


def burning_rows(ctx: Ctx, strict_ref: dict) -> tuple[dict, list]:
    """CODE-17 B5: per run of record, the centre-point-burning row of the main S6 table (keyed by run) and the rows of the
    S6_burning sub-table (observed-wet cells / km² any-touched vs cell centre, inflation, strict scores both ways), read from
    code17/c6_alltouched_inflation.json; the any-touched contingency is asserted against T3's (strict_ref[run])."""
    c6 = ctx.j(ctx.R / "code17" / "c6_alltouched_inflation.json")
    main, sub = {}, []

    def row(label, run, aoi_tag, u, scored=True):
        st = u.get("strict_h_gt_0p10") if scored else None
        if st:
            at = st["any_touched"]
            assert all(int(at[k]) == int(strict_ref[run][k]) for k in ("tp", "fp", "fn", "tn")), f"S6 burning: any-touched contingency of {run} != T3"
            ce_ = st["centre"]
            main[run] = [label, run, CENTRE_LABEL, f1(u["universe_km2"]), f3(ce_["csi"]), f3(ce_["hr"]), f2(ce_["bias"])]
        sub.append([label, run + (f" {aoi_tag}" if aoi_tag else ""), f1(u["universe_km2"]), f0(u["cells_any_touched"]), f1(u["observed_km2_any_touched"]),
                    f0(u["cells_centre"]), f1(u["observed_km2_centre"]), f1(u["inflation_pct"])] +
                   ([f3(st["any_touched"]["csi"]), f3(st["centre"]["csi"]), f3(st["any_touched"]["hr"]), f3(st["centre"]["hr"]),
                     f3(st["any_touched"]["far"]), f3(st["centre"]["far"]), f2(st["any_touched"]["bias"]), f2(st["centre"]["bias"])] if st else [NA] * 8))
    labels = {key: label for key, label, _run, _b, _h in EVENTS}
    for e in c6["events"]:
        if e["event"] != "crete":
            row(labels[e["event"]], e["run"], "", e["v14_universe"])
        else:
            for code, u in sorted(e["aois"].items()):
                row(labels["crete"], e["run"], f"AOI{code} (tier {u['tier']})", u, scored=(u["tier"] == 1))
    return main, sub


def tab_s6(ctx: Ctx, W: Writer):
    W.begin(); rows = []; c = ce(ctx)
    strict_ref = {run: c["events"][run]["enhanced_v14"]["strict"] for run in c["events"]}
    centre_rows, burn_rows = burning_rows(ctx, strict_ref)
    t = ctx.j(ctx.R / "code14" / "table_s3_v14_v142.json")
    for ev in t["events"]:
        run = ev["run"]; e = strict_ref[run]
        for i, v in enumerate(ev["variants"]):
            if i == 1:
                assert all(v[k] == e[k] for k in ("tp", "fp", "fn", "tn")), f"S6 AOI-union variant of {run} does not reproduce T3"
            rows.append([ev["label"], run, v["name"], f1(v["area_km2"]), f3(v["csi"]), f3(v["hr"]), f2(v["bias"])])
        rows.append(centre_rows[run])
    ct = ctx.j(ctx.R / "code16" / "crete_tier1_diagnostics.json")["runs"]["crete_canonical_r2on"]
    e = strict_ref["crete_canonical_r2on"]
    rows.append(["Crete (EMSR933)", "crete_canonical_r2on", "Active mask (no AOI)", "not defined", NA, NA, NA])
    for i, v in enumerate(ct["universe_variants"]):
        if i == 0:
            assert all(v[k] == e[k] for k in ("tp", "fp", "fn", "tn")), "S6 Crete AOI03 variant does not reproduce T3"
        rows.append(["Crete (EMSR933)", "crete_canonical_r2on", v["name"], f1(v["area_km2"]), f3(v["csi"]), f3(v["hr"]), f2(v["bias"])])
    rows.append(centre_rows["crete_canonical_r2on"][:2] + [centre_rows["crete_canonical_r2on"][2].replace("AOI-union", "AOI03 (tier-1 universe)")] + centre_rows["crete_canonical_r2on"][3:])
    W.emit("S6", "Evaluation-universe sensitivity", ["event", "run of record", "universe", "area km²", "CSI", "HR", "B"], rows,
           ["Source: `code14/table_s3_v14_v142.json` (scripts/table_s3_v14.py --run-suffix _v142: the canonical runs of record; active mask only / AOI union / AOI union ± 1 km, the v1.4 exclusion removed on "
            "both sides; the AOI-union row reproduces T3 exactly — checked here on the contingency counts). Crete: `code16/crete_tier1_diagnostics.json` (AOI03 = the tier-1 universe, ± 1 km); the active-mask-only "
            "variant is not defined for Crete (truth only inside the AOIs; §8-3 scores the tier-1 block only).",
            "Truth burned by cell centre: `code17/c6_alltouched_inflation.json` (scripts/c6_alltouched_inflation.py). The validator burns the EMS polygons with rasterio all_touched = True (a cell is observed-wet "
            "when a polygon touches it); the sensitivity marks a cell only when its centre lies inside a polygon, on the same grid and universe (the universe itself is unchanged). A re-scoring of the run of record's "
            "h_max > 0.10 m, no SFINCS run; the any-touched contingency reproduces T3 (asserted)."],
           extra=[("S6_burning", "Observed-wet cells by rasterisation rule and the strict scores (h_max > 0.10 m) with each truth",
                   ["event", "run of record", "universe km²", "observed cells, any-touched", "observed km², any-touched", "observed cells, cell centre", "observed km², cell centre", "inflation %",
                    "CSI any-touched", "CSI centre", "HR any-touched", "HR centre", "FAR any-touched", "FAR centre", "B any-touched", "B centre"], burn_rows,
                   ["inflation % = any-touched cells / centre cells − 1. Crete tier-2 AOIs: cells and km² only (rule_ledger.md §8 item 3: no score outside the tier-1 block)."])])


def tab_s7(ctx: Ctx, W: Writer):
    W.begin(); c = ce(ctx); rows = []; diag = []
    plan = [(label, run, "enhanced") for key, label, run, _b, _h in EVENTS if key != "crete"] + \
           [(label + " — baseline", base, "baseline") for key, label, run, base, _h in EVENTS if base and key != "crete"]
    run_of = {base: run for key, label, run, base, _h in EVENTS if base}
    for label, run, kind in plan:
        ev = c["events"][run_of.get(run, run)]
        a, b, n = (ev.get(f"{kind}_v13_published") or {}).get("strict"), (ev.get(f"{kind}_v13_newmask") or {}).get("strict"), ev[f"{kind}_v14"]["strict"]
        rec = ctx.res(run, "record", required=False) or {}
        tag = rec.get("harness_tag") or "v1.4.0"
        for m, fmt, dfmt in (("csi", f3, s3), ("hr", f3, s3), ("far", f3, s3), ("bias", f2, s2), ("gss", f3, s3)):
            rows.append([label, run, tag, m.upper() if m != "bias" else "B", fmt(a[m]) if a else NA, fmt(b[m]) if b else NA, fmt(n[m]),
                         dfmt(b[m] - a[m]) if (a and b) else NA, dfmt(n[m] - b[m]) if b else NA])
    d1 = ctx.j(ctx.R / "code16" / "d1_rain_written.json")["runs"]
    d6_pub = ctx.j(ctx.repo / "reproduction" / "v14_harness" / "D6_strymonas_sink_cells.json")["models"]
    d6_new = ctx.j(ctx.R / "code16" / "strymonas_enhanced_postD6_v142_balance.json")
    for key, label, run, _b, _h in EVENTS:
        if key == "crete":
            continue
        fa = ctx.res(release_base(run), "v13_fa_share", required=False)
        share = fa["categories"]["union_open_sea_wc80"]["share_of_fa"] if fa else None
        fa_txt = (f"{f3(share)} ({f1(fa['categories']['union_open_sea_wc80']['fa_km2'])} of {f1(fa['fa_km2'])} km²)" if fa else NA)
        ev_name = label.split(" (")[0].replace("Emilia-Romagna", "Emilia-R.")
        r13 = next((r for r in d1 if r["event"] == ev_name and r["release"] == "release v1.3.0"), None)
        r14 = next((r for r in d1 if r["event"] == ev_name and r["release"] != "release v1.3.0"), None)
        d1_txt = f"{f3(r13['written_over_intended'])} → {f3(r14['written_over_intended'])} ({r14['release']})" if (r13 and r14) else NA
        cn_on = bool((ctx.cfg(run).raw.get("infiltration") or {}).get("enabled"))
        d6_txt = (f"{f3(d6_pub['v13_published']['sink_share_end'])} → {f3(d6_new['sink_check']['share'])}" if cn_on else "CN off")
        diag.append([label, run, fa_txt, d1_txt, d6_txt])
    W.emit("S7", "Release v1.3.0 → v1.4.2: universe and physics", ["run", "run id", "harness of record", "metric", "release v1.3.0", "release v1.3.0 re-scored on the v1.4 universe", "run of record (v1.4.x)", "Δ universe", "Δ physics"], rows,
           ["Source: `phase4/cross_event_v14_v142.json` (`<kind>_v13_published` = the release v1.3.0 model on its own mask, `<kind>_v13_newmask` = the same model re-scored on the v1.4 universe, `<kind>_v14` = the run of record). "
            "Δ universe = re-scored − release v1.3.0; Δ physics = run of record − re-scored. Harness of record from the run record (`harness_tag`, v1.4.0 when absent)."],
           extra=[("S7_diagnostics", "Release v1.3.0 diagnostics: false alarms on excluded cells, rain written vs intended (D1), curve-number sink (D6)",
                   ["event", "run of record", "share of release v1.3.0 false alarms on the excluded cells (WorldCover 80 ∪ open sea)", "rain written / intended (D1): release v1.3.0 → run of record", "D6 sink share: release v1.3.0 → run of record"],
                   diag, ["False alarms: `results/<run>_v13_fa_share.json` categories.union_open_sea_wc80 (exact cell counts on the release v1.3.0 mask). D1: `code16/d1_rain_written.json` (precip_2d.nc vs the IMERG file the pipeline read, "
                          "simulated window, cell-matched). D6 (CN-on runs only): release v1.3.0 = `reproduction/v14_harness/D6_strymonas_sink_cells.json` models.v13_published.sink_share_end (active cells whose cumulative "
                          "rain exceeds 0.2 S while storecumprcp = 0); run of record = `code16/strymonas_enhanced_postD6_v142_balance.json` sink_check.share (cells whose cumulative infiltration exceeds the SCS value or the rain by 0.1 mm)."])])


def tab_s8(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    tj = ctx.j(ctx.R / "phase5" / "crete_canonical_r2on_tiers.json"); names = crete_aoi_names(ctx)
    for code in sorted(set(tj["aois"]) | set(names)):
        a = tj["aois"].get(code)
        if a is None or a["tier"] == 3:
            rows.append([f"AOI{code}", (a or {}).get("name") or names.get(code, NA), "3", "excluded: no product released", NA, NA, NA, NA, NA, NA]); continue
        if a["tier"] == 1:
            st = a["strict_threshold_sweep"]["h>0.10m"]
            rows.append([f"AOI{code}", a["name"], "1", "scored", f1(a["universe_km2"]), f1(a["observed_km2"]), f1(a["modelled_km2_h_gt_0p10"]), f3(st["csi"]), f3(st["hr"]), f2(st["bias"])])
        else:
            rows.append([f"AOI{code}", a["name"], "2", "km² only", f1(a["universe_km2"]), f1(a["observed_km2"]), f1(a["modelled_km2_h_gt_0p10"]), NA, NA, NA])
    sens = []
    for run in ("crete_baseline", "crete_canonical_r2on", "crete_sens_r2off", "crete_sens_anchor_224", "crete_sens_anchor_336", "crete_sens_anchor_582", "crete_sens_karst_q1914"):
        a = tier1(ctx, run); st = a["strict_threshold_sweep"]["h>0.10m"]; cs = a.get("csi_star") or {}
        rec = ctx.res(run, "record")
        sens.append([run, rec.get("label", NA), f3(st["csi"]), f3(st["hr"]), f3(st["far"]), f2(st["bias"]), f3(st["gss"]), (f"{f3(cs.get('csi'))} ({cs.get('threshold')})" if cs else NA),
                     f1(a["modelled_km2_h_gt_0p10"]), r2_factor(ctx, run)])
    W.emit("S8", "Crete (EMSR933): tiers and sensitivities", ["AOI", "name", "tier", "status", "universe km²", "observed km²", "modelled km² (h_max > 0.10 m)", "CSI", "HR", "B"], rows,
           ["Tiers (`reproduction/emsr933/rule_ledger.md` §8 item 3, fixed before any run): `phase5/crete_canonical_r2on_tiers.json` (canonical run). Observed km² = the validator's rasterisation (all_touched).",
            "The per-station comparison with the NOA/meteo.gr gauges is not reproduced here: the station values are not committed (meteo.gr terms of use; decision of 21 Oct 2026). "
            "The R2 anchor (447.8 mm, Tzermiado, five local days 30 Sep – 4 Oct 2026) is the one station total the configuration carries."],
           extra=[("S8_sensitivities", "Crete runs on the tier-1 block (Tzermiado)", ["run", "label (run record)", "CSI", "HR", "FAR", "B", "GSS", "CSI* (threshold)", "modelled km²", "R2 factor"], sens,
                   ["Source: `phase5/<run>_tiers.json` aois['03'] and `results/<run>_record.json`; R2 factor from `phase4/rain/<run>_v14.json`."])])


def git(ctx: Ctx, *args) -> str:
    return subprocess.run(["git", "-C", str(ctx.repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def tab_s9(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    em = ctx.repo / "reproduction" / "emsr933"
    snap = ctx.j(em / "ems_api_snapshot_20261009T124720Z.json")["results"][0]
    fz = ctx.j(em / "stage5_truth_freeze.json")
    cfg = ctx.cfg("crete_canonical_r2on")
    tm = (em / "timing.md").read_text(encoding="utf-8"); ctx.note("reproduction/emsr933/timing.md")
    led = (em / "rule_ledger.md").read_text(encoding="utf-8"); ctx.note("reproduction/emsr933/rule_ledger.md")
    act = dt.datetime.fromisoformat(snap["activationTime"]).replace(tzinfo=dt.timezone.utc)
    r2 = cfg.raw["rain_bias_correct"]
    rows.append(["event time (EMS)", snap["eventTime"] + "Z", "EMS API snapshot 2026-10-09T12:47:20Z: eventTime"])
    rows.append(["rain anchor window end (event end, NOA local days; UTC)", str(r2["event_end"]), "run config rain_bias_correct.event_end"])
    rows.append(["EMS activation", snap["activationTime"] + "Z", "EMS API snapshot: activationTime"])
    acqs, dels = [], []
    for p in fz["packages"]:
        m_ = re.search(r"(\d\d)/(\d\d)/(\d{4}) T(\d\d:\d\d:\d\d)Z", p.get("post_sensor") or "")
        t = p.get("post_acq_utc") or (f"{m_.group(3)}-{m_.group(2)}-{m_.group(1)}T{m_.group(4)}Z" if m_ else None)
        if t:
            acqs.append((t, p["aoi"], p["product"], (p.get("post_sensor") or "").split(" ")[0]))
        if p.get("delivered"):
            dels.append((p["delivered"], p["aoi"], p["product"]))
    if acqs:
        t0 = min(acqs)
        rows.append(["first post-event acquisition among the released products", t0[0], f"stage5_truth_freeze.json packages (AOI {t0[1]} {t0[2]}, {t0[3]})"])
    if dels:
        t0 = min(dels)
        rows.append(["first product delivered", t0[0][:19] + "Z", f"stage5_truth_freeze.json packages[].delivered (AOI {t0[1]} {t0[2]})"])
    m = re.search(r"\| 0 Preflight[^|]*\| ([0-9T:\-]+Z) \|", tm)
    rows.append(["CODE-10 issued (first API snapshot 2026-10-09T12:47:20Z)", m.group(1) if m else NA, "timing.md Stage 0 start"])
    m = re.search(r"\| 1 Rule ledger[^|]*\| [0-9T:\-]+Z \| ([0-9T:\-x]+Z) \|", tm)
    rows.append(["rule applied: rule ledger + YAMLs (Stage 1, no run)", m.group(1) if m else NA, "timing.md Stage 1 end"])
    m = re.search(r"## 8\. Decisions recorded \(GO-C[^)]*\) — written ([0-9T:\-]+Z)", led)
    rows.append(["rule decisions recorded (ledger §8, before any Crete run)", m.group(1) if m else NA, "rule_ledger.md §8 heading"])
    starts = re.findall(r"\| (CODE-1[2-5][^|]*|GO-[^|]*) \| ([0-9T:\-]+Z) \| ([0-9T:\-x≈ ]+Z?) \|", tm)
    if starts:
        rows.append(["harness audit start (CODE-12)", starts[0][1], f"timing.md row '{starts[0][0][:40]}…'"])
        rows.append(["harness audit end (before the Crete runs)", starts[-1][2], f"timing.md row '{starts[-1][0][:40]}…' (as recorded)"])
    pr = re.findall(r"\| (\d{4}-\d\d-\d\dT[0-9:]+Z) \| (\d{4}-\d\d-\d\d) \| \d+ \|", tm)
    tstop_day = (cfg.tstop - dt.timedelta(seconds=1)).date().isoformat()
    first_ok = next((p for p in pr if p[1] >= tstop_day), None)
    rows.append([f"ERA5T available through the last simulated day ({tstop_day})", first_ok[0] if first_ok else NA, "timing.md data-latency probe (first probe with ERA5 last requestable day ≥ that day)"])
    runs = ("crete_baseline", "crete_canonical_r2on", "crete_sens_r2off", "crete_sens_anchor_224", "crete_sens_anchor_336", "crete_sens_anchor_582", "crete_sens_karst_q1914")
    for run in runs:
        rec = ctx.res(run, "record")
        rows.append([f"run {run}: start → end (SFINCS s)", f"{rec['start_utc']} → {rec['end_utc']} ({f0(rec['sfincs_total_time_s'])} s)", f"results/{run}_record.json"])
    rec = ctx.res("crete_canonical_r2on", "record")
    end = dt.datetime.fromisoformat(rec["end_utc"].replace("Z", "+00:00"))
    rows.append(["validated canonical hindcast (run record end, validation included)", rec["end_utc"], "results/crete_canonical_r2on_record.json end_utc"])
    rows.append(["activation → validated canonical (d)", f"{(end - act).total_seconds() / 86400:.2f}", "difference of the two rows above"])
    W.emit("S9", "Timing of the prospective run (EMSR933 Crete)", ["milestone", "UTC / value", "source"], rows,
           ["Sources: the EMS API snapshot of the provisional cut-off, `reproduction/emsr933/stage5_truth_freeze.json`, the canonical run config, `reproduction/emsr933/timing.md` (stage table, latency probe), "
            "`reproduction/emsr933/rule_ledger.md` §8 heading and the Crete run records. Values are copied as recorded (times recorded to the minute keep their 'x' placeholders)."])


def tab_s10(ctx: Ctx, W: Writer):
    W.begin(); rows = []
    audit = (ctx.repo / "docs" / "AUDIT.md").read_text(encoding="utf-8"); ctx.note("docs/AUDIT.md")
    tests = {p.name: p.read_text(encoding="utf-8") for p in sorted((ctx.repo / "tests").glob("test_*.py"))}
    skill = {p.name: p.read_text(encoding="utf-8") for p in sorted((ctx.repo / "skill" / "scripts").glob("*.py"))}
    ctx.note("tests/test_*.py"); ctx.note("skill/scripts/*.py")
    sym = {
        "D1": re.search(r"\(D1 ([^;]+);", audit), "D2": re.search(r"; D2 ([^;]+);", audit), "D3": re.search(r"; D3 ([^)]+)\)", audit),
        "D4": re.search(r"D4 \((open sea inactive[^)]+)\)", audit), "D5": re.search(r"D5 (meteo-grid alignment)", audit),
        "D6": re.search(r"curve-number infiltration[^—]+— (an unbounded sink[^.]*)\.", audit), "D7": re.search(r"— D7 ([^;]+);", audit),
        "D8": re.search(r"— D8 ([^;]+);", audit),
    }
    fix = {
        "D1": re.search(r"CODE-12, D1/D2 fixes\) — code \+ tests only; commit `([0-9a-f]{40})`", audit), "D2": re.search(r"CODE-12, D1/D2 fixes\) — code \+ tests only; commit `([0-9a-f]{40})`", audit),
        "D3": None, "D4": re.search(r"D4 coastal set-up \(CODE-13\) — code \+ tests only; commit `([0-9a-f]{40})`", audit),
        "D5": re.search(r"D5 commit `([0-9a-f]{40})`", audit), "D6": re.search(r"D6 commit `([0-9a-f]{40})`", audit),
        "D7": re.search(r"D7 GloFAS point sampling; fix commit `([0-9a-f]{40})`", audit), "D8": re.search(r"D8 source-point resolution; fix commit `([0-9a-f]{40})`", audit),
    }
    cls_text = {"D3": re.search(r"D3: (no code change — the methods text will be corrected)", audit), "D8": re.search(r"D8 — new finding, report only \((configuration, not code)\)", audit)}
    # runs affected: the release v1.3.0 runs behind R5 = the run records with a manifest row (MANIFEST.md §1; one run per record,
    # strymonas_enhanced_postD6 is the post-D6 re-run of row 1 and counts once), by the defect's condition on the config / build record
    recs = {}
    for p in sorted((ctx.R / "results").glob("*_record.json")):
        run = p.name[: -len("_record.json")]
        if run != base_of(run) or run.endswith("_postD6"):
            continue
        r = ctx.j(p)
        if r.get("manifest_row") is not None:
            recs[run] = r
    bases = sorted(recs)
    cfgs = {b: ctx.cfg(b) for b in bases}
    def is_imerg(c):
        rs = c.raw.get("rain_source"); return "imerg" in (rs.get("name", "") if isinstance(rs, dict) else str(rs)).lower()
    open_sea = {b: ((recs[b].get("coastal_prep") or {}).get("n_open_sea") or 0) > 0 for b in bases}
    cond = {"D1": is_imerg, "D2": lambda c: bool((c.raw.get("coastal_bc") or {}).get("enabled")), "D3": None, "D4": "open_sea",
            "D5": lambda c: True, "D6": lambda c: bool((c.raw.get("infiltration") or {}).get("enabled")), "D7": lambda c: bool((c.raw.get("upstream_q") or {}).get("enabled")),
            "D8": lambda c: bool((c.raw.get("upstream_q") or {}).get("enabled"))}
    tag_order = ["v1.4.0", "v1.4.1", "v1.4.2"]
    for d in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
        sm = sym[d].group(1).strip() if sym[d] else "not found in AUDIT.md"
        if d == "D4":
            sm = "coastal set-up; fixed by: " + sm
        h = fix[d].group(1) if fix[d] else None
        short = git(ctx, "rev-parse", "--short", h) if h else "—"
        tags = git(ctx, "tag", "--contains", h).split() if h else []
        tag = next((t for t in tag_order if t in tags), "—")
        klass = (cls_text[d].group(1) if d in cls_text and cls_text[d] else "code (harness)")
        if h:
            changed = [ln for ln in git(ctx, "show", "--stat", "--format=", h).splitlines() if "|" in ln and ln.strip().split("|")[0].strip().startswith(("skill/", "validation/"))]
            files = sorted({Path(ln.split("|")[0].strip()).name for ln in changed})
            klass += f"; fix commit touches: {', '.join(files)}" if files else ""
        aff = [b for b in bases if open_sea[b]] if cond[d] == "open_sea" else [b for b, c in cfgs.items() if cond[d] and cond[d](c)]
        aff_txt = (f"{len(aff)} of {len(bases)} release runs" + (f": {', '.join(aff)}" if len(aff) <= 8 else "")) if cond[d] else "none (methods text only)"
        guards = []
        for n, t in tests.items():      # test classes whose body names the defect; a file naming it only at module level is listed as a whole
            starts = [(m_.start(), m_.group(1)) for m_ in re.finditer(r"^class (\w+)\(", t, re.M)]
            head = t[: starts[0][0]] if starts else t
            hit = [name for k, (pos, name) in enumerate(starts) if re.search(rf"\b{d}\b", t[pos: starts[k + 1][0] if k + 1 < len(starts) else len(t)])]
            if hit:
                guards += [f"{n}::{h}" for h in hit]
            elif re.search(rf"\b{d}\b", head):
                guards.append(n)
        custom = {m_.group(1) for t in skill.values() for m_ in re.finditer(r"^class (\w+Error)\(", t, re.M)}
        checks = []
        for n, t in skill.items():      # custom error classes defined or raised within 8 lines after a line naming the defect
            lines = t.splitlines()
            for i, ln in enumerate(lines):
                if re.search(rf"\b{d}\b", ln):
                    for ln2 in lines[i:i + 8]:
                        m_ = re.search(r"class (\w+Error)\b|raise (\w+Error)\b", ln2)
                        if m_ and (m_.group(1) or m_.group(2)) in custom:
                            checks.append(f"{n}:{m_.group(1) or m_.group(2)}")
        checks = sorted(set(checks))
        rows.append([d, klass, sm, aff_txt, short, tag, ("tests: " + ", ".join(sorted(set(guards))) if guards else "no test naming it") + (f"; build-time errors: {', '.join(checks)}" if checks else "")])
    W.emit("S10", "Release history D1–D8", ["defect", "class (and files changed by the fix)", "symptom / definition (AUDIT.md)", "runs affected (release v1.3.0 runs behind R5, by config)", "fix commit", "tag",
                                            "guard (test files / build-time checks naming the defect)"], rows,
           ["Every cell is extracted at generation time: symptoms and fix commits by regex from `docs/AUDIT.md`, short hashes and the first tag containing the fix from git, files changed from `git show --stat`, "
            "runs affected = the release v1.3.0 runs behind R5 (run records with a manifest row) meeting the defect's condition (D1 IMERG forcing; D2 coastal_bc on; D4 open-sea cells removed by the v1.4 build; "
            "D5 every gridded-meteo run; D6 infiltration on; D7/D8 upstream_q on), guards = test classes / test functions whose name line or docstring names the defect, and error classes raised within 8 lines of a "
            "line naming it in `skill/scripts/` (custom error classes only)." , f"Release runs counted ({len(bases)}): {', '.join(bases)}."])


def tab_s11(ctx: Ctx, W: Writer):
    """CODE-19 C4 — the Manning lookup of the pipeline (WorldCover class -> n), with the check that every canonical run used the same file."""
    W.begin()
    p = ctx.repo / "skill" / "manning_lookup.csv"; ctx.note("skill/manning_lookup.csv")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    same, differ = [], []
    for key, label, run, _b, _h in EVENTS:
        q = ctx.cfg(run).paths["work_dir"] / "manning_lookup.csv"; ctx.note(q.as_posix())
        (same if q.exists() and hashlib.sha256(q.read_bytes()).hexdigest() == sha else differ).append(run)
    rows = [[f0(code), name, f"{n:.3f}"] for code, name, n in manning_rows(ctx.repo)]
    g = ctx.cfg(EVENTS[0][2]).raw["grid"]
    W.emit("S11", "Manning roughness lookup (ESA WorldCover class → n)", ["WorldCover class code", "class name", "Manning n (s m^-1/3)"], rows,
           [f"Source: `skill/manning_lookup.csv` (SHA-256 {sha[:16]}…), the file `skill/scripts/prep_inputs.py` copies into every build; the copy in the work directory of every "
            f"canonical run is byte-identical ({', '.join(same)})" + (f"; differs or missing for {', '.join(differ)}" if differ else "") + ". Class names: ESA WorldCover v200 legend (Zanaga et al. 2022). "
            "The lookup file holds the class code and n only — it records no per-class source; the manuscript cites Sanz-Ramos et al. (2021), Arcement and Schneider (1989) and Engman (1986) "
            f"collectively for the lookup, and the per-class attribution is not recorded in the repository. Grid-level defaults of the configs (used where the lookup leaves a cell unassigned): "
            f"manning_land {g.get('manning_land', 0.04)}, manning_sea {g.get('manning_sea', 0.02)} (`skill/scripts/_common.py`)."])


def manifest(W: Writer, out_dir: Path):
    L = ["# TABLES_MANIFEST — CODE-16 B", "", f"Generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} by `reproduction/r6/scripts/r6_tables.py`. "
         "One row per table: files, row count, every record the generator read (paths relative to the repository unless absolute), generated-at UTC.", "",
         "| table | title | rows | files | sources | generated (UTC) |", "|---|---|---|---|---|---|"]
    for m in W.manifest:
        L.append(f"| {m['table']} | {m['title']} | {m['rows']} | {', '.join(m['files'])} | {'<br>'.join(f'`{s}`' for s in m['sources'])} | {m['generated_utc']} |")
    (out_dir / "TABLES_MANIFEST.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out_dir / "tables" / "tables_manifest.json").write_text(json.dumps(W.manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--r5-dir", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--only", default="", help="comma list of table ids (debugging)")
    a = ap.parse_args()
    repo = a.repo.resolve()
    out = a.out_dir or (repo / "reproduction" / "r6")
    ctx = Ctx(repo, a.r5_dir); W = Writer(ctx, out)
    todo = [("T2", t2), ("T3", t3), ("T4", t4), ("T5", t5), ("T6", t6), ("S1", tab_s1), ("S2", tab_s2), ("S3", tab_s3), ("S4", tab_s4), ("S5", tab_s5), ("S6", tab_s6), ("S7", tab_s7), ("S8", tab_s8), ("S9", tab_s9), ("S10", tab_s10),
            ("S11", tab_s11)]
    only = {x for x in a.only.split(",") if x}
    for tid, fn in todo:
        if only and tid not in only:
            continue
        fn(ctx, W)
    if not only:
        manifest(W, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
