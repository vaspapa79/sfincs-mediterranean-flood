"""D6 (GO-D6, 2026-10-19) — curve-number bookkeeping in harness v1.4: `storecumprcp = 1` whenever curve-number
infiltration is on.

SFINCS v2.3.0 'cna' infiltration (the hydromt setup_cn_infiltration route, scsfile) computes the cumulative SCS
abstraction I(P) from the cumulative rain P and applies qinfmap = (I - cuminf)/dt, but adds qinfmap*dt to cuminf only
when store_cumulative_precipitation is on (sfincs_infiltration.f90:87-112; storecumprcp default 0,
sfincs_input.f90:219, 439-441). With the default, every step past Ia = 0.2 S removes the whole I again and the volume
has no floor (sfincs_continuity.f90:~535): an unbounded sink for rain and for river water (D6_CN_SINK.md).

  RenderD6                     v1.4 + CN -> storecumprcp: 1 in setup_config; v1.4 without CN and v1.3 untouched.
  ClosedPlainMassBalance  (i)  closed synthetic plain, CN 76, 30 mm rain + 20 m3/s source for 12 h: v1.4 conserves
                               rain runoff + source volume within 0.1 %; the v1.3 control loses it (the defect).
  MultiDayInfiltrationBounds (ii) 180 mm in three daily bursts: per-cell cumulative infiltration monotone, never above
                               the cumulative rain, on the SCS curve, and the continuing abstraction F = I - Ia <= S.
  NonCNInvariance        (iii) synthetic, CN off: the flag leaves the water-level fields bit-identical (the event
                               version on Mandra enhanced is reproduction/v14_harness/scripts/d6_invariance_event.py).

The SFINCS classes need hydromt.exe + sfincs.exe (skill/machine.local.yaml) and are skipped otherwise.
Run: python -m unittest tests.test_d6_cn_bookkeeping -v
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
os.environ.setdefault("GDAL_DATA", str(Path(sys.executable).parent / "Library" / "share" / "gdal"))

from _common import EventCfg, _load_machine_override, load_config  # noqa: E402
import build_model  # noqa: E402

BBOX = (23.0, 35.0, 23.1, 35.09)            # ~9.1 x 10.0 km
CN = 76
S_M = (1000.0 / CN - 10.0) * 0.0254         # 0.08021 m (hydromt rounds S in inch to 3 decimals: 3.158 in)
IA_M = 0.2 * S_M


def scs_runoff(p, s):
    p = np.asarray(p, dtype=float)
    ia = 0.2 * s
    return np.where(p > ia, (p - ia) ** 2 / (p + 0.8 * s), 0.0)


def _raw(version, work, cn=True, window=(0, 0, 1)) -> dict:
    return {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-01"},
            "window": {"spinup_days": window[0], "pre_event_days": window[1], "post_event_days": window[2]},
            "bbox": {"west": BBOX[0], "south": BBOX[1], "east": BBOX[2], "north": BBOX[3]},
            "crs": {"epsg": 32634}, "grid": {"res": 100, "zmin": -2, "zmax": 250},
            "paths": {"work_dir": str(work), "deliverable_dir": str(work / "d"),
                      "manning_lookup": str(REPO / "skill" / "manning_lookup.csv")},
            "rain_source": "era5_hourly", "infiltration": {"enabled": cn}, "harness_version": version}


def _cfg(version="v1.4", work=Path("D:/tmp/synth"), **kw) -> EventCfg:
    return EventCfg(raw=_raw(version, work, **kw), config_path=Path("synth.yaml"))


def _setup_config_block(yml: str) -> str:
    return yml.split("setup_config:")[1].split("setup_grid_from_region:")[0]


class RenderD6(unittest.TestCase):
    def test_v14_with_curve_numbers_writes_storecumprcp(self):
        y = build_model.render_build_yml(_cfg("v1.4", cn=True))
        self.assertIn("  storecumprcp: 1\n", _setup_config_block(y))
        self.assertEqual(y.count("storecumprcp"), 1)

    def test_v14_without_curve_numbers_does_not(self):
        self.assertNotIn("storecumprcp", build_model.render_build_yml(_cfg("v1.4", cn=False)))

    def test_v13_is_unchanged_even_with_curve_numbers(self):
        self.assertNotIn("storecumprcp", build_model.render_build_yml(_cfg("v1.3", cn=True)))

    def test_published_cn_record_still_reproduced(self):
        cfg = load_config(["--config", str(REPO / "skill" / "examples" / "emsr122_strymonas_enhanced.yaml")])
        norm = lambda s: re.sub(r"reclass_table: .*", "reclass_table: X", s)  # noqa: E731
        self.assertEqual(norm(build_model.render_build_yml(cfg)),
                         norm((REPO / "configs" / "as_run" / "emsr122_sfincs_v3" / "sfincs_build.yml").read_text()))


# ------------------------------------------------------------------------------------------------ SFINCS helpers
def _env():
    env = dict((_load_machine_override().get("env") or {}))
    return env if all(env.get(k) and Path(env[k]).exists() for k in ("hydromt", "sfincs_exe")) else None


def _write_inputs(data: Path, rain_by_hour: dict, ndays: int) -> Path:
    """2-m plain (no sea, no boundary), WorldCover 40, CN 76, ERA5-like hourly rain {hour since 2017-01-01: mm}."""
    import pandas as pd
    import rasterio
    import xarray as xr
    from rasterio.transform import from_origin
    data.mkdir(parents=True, exist_ok=True)
    w, s, e, n = BBOX
    res = 0.0005
    ny, nx = int(round((n - s + 0.02) / res)), int(round((e - w + 0.02) / res))
    tr = from_origin(w - 0.01, n + 0.01, res, res)
    for name, val, dtype, nod in (("dep.tif", 2.0, "float32", -9999.0), ("landuse.tif", 40, "uint8", 0), ("cn.tif", CN, "uint8", 0)):
        with rasterio.open(data / name, "w", driver="GTiff", height=ny, width=nx, count=1, dtype=dtype, crs="EPSG:4326",
                           transform=tr, nodata=nod) as dst:
            dst.write(np.full((ny, nx), val, dtype=dtype), 1)
    time = pd.date_range("2016-12-31 00:00", pd.Timestamp("2017-01-01") + pd.Timedelta(days=ndays + 1), freq="1h")
    lat = np.arange(n + 0.5, s - 0.5, -0.25); lon = np.arange(w - 0.5, e + 0.5, 0.25)
    pr = np.zeros((time.size, lat.size, lon.size), "float32")
    t0 = pd.Timestamp("2017-01-01")
    for hour, mm in rain_by_hour.items():          # ERA5: accumulation over the hour ENDING at the stamp
        pr[time == t0 + pd.Timedelta(hours=hour + 1)] = mm
    xr.Dataset({"precip": (("time", "latitude", "longitude"), pr, {"units": "mm/h"})},
               coords={"time": time, "latitude": lat, "longitude": lon}).to_netcdf(data / "era5_synth.nc")
    (data / "data_catalog.yml").write_text(f"""meta:
  version: 1
  hydromt_version: ">=0.10"
  root: {data.as_posix()}

copdem30:
  data_type: RasterDataset
  driver: raster
  path: dep.tif
  crs: 4326
  rename:
    Band1: elevtn
    band_1: elevtn

esa_worldcover_2021:
  data_type: RasterDataset
  driver: raster
  path: landuse.tif
  crs: 4326
  rename:
    Band1: landuse
    band_1: landuse

cn_raster:
  data_type: RasterDataset
  driver: raster
  path: cn.tif
  crs: 4326
  rename:
    Band1: cn
    band_1: cn

era5_hourly:
  data_type: RasterDataset
  driver: netcdf
  path: era5_synth.nc
  crs: 4326
""", encoding="utf-8")
    return data / "data_catalog.yml"


def _build(cfg, env, catalog, model: Path) -> str:
    """Pipeline path of build_model.main() for a domain without open sea: render -> hydromt -> D5 -> D2 (no-op)."""
    yml = model.parent / f"sfincs_build_{model.name}.yml"
    yml.write_text(build_model.render_build_yml(cfg), encoding="utf-8")
    model.mkdir(parents=True, exist_ok=True)
    res = subprocess.run([env["hydromt"], "build", "sfincs", str(model), "-i", str(yml), "-d", str(catalog), "--fo"],
                         capture_output=True, text=True)
    (model.parent / f"hydromt_{model.name}.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"hydromt build failed:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
    build_model.align_meteo_grids(cfg, model)
    build_model.inject_waterlevel_bnd(cfg, model)
    return (model / "sfincs.inp").read_text()


def _add_inp(model: Path, text: str):
    inp = model / "sfincs.inp"
    inp.write_text(inp.read_text().rstrip() + "\n" + text.strip() + "\n")


def _set_inp(model: Path, key: str, value):
    """Replace (or add) one sfincs.inp key — SFINCS reads the FIRST occurrence, so appending a duplicate is ignored."""
    inp = model / "sfincs.inp"
    lines = [ln for ln in inp.read_text().splitlines() if ln.split("=")[0].strip() != key]
    inp.write_text(chr(10).join(lines + [f"{key:<20} = {value}"]) + chr(10))


def _add_source(model: Path, q_m3s: float, t0_h: float, t1_h: float, tend_s: float):
    inp = (model / "sfincs.inp").read_text()
    get = lambda k: float([ln.split("=")[1] for ln in inp.splitlines() if ln.split("=")[0].strip() == k][0])  # noqa: E731
    x0, y0, mmax, nmax = get("x0"), get("y0"), int(get("mmax")), int(get("nmax"))
    (model / "sfincs.src").write_text(f"{x0 + 100.0 * (mmax // 2 + 0.5):.2f} {y0 + 100.0 * (nmax // 2 + 0.5):.2f}\n")
    t = [0.0, t0_h * 3600 - 1, t0_h * 3600, t1_h * 3600, t1_h * 3600 + 1, tend_s]
    q = [0.0, 0.0, q_m3s, q_m3s, 0.0, 0.0]
    (model / "sfincs.dis").write_text("".join(f"{ti:.0f} {qi:.3f}\n" for ti, qi in zip(t, q)))
    _add_inp(model, "srcfile = sfincs.src\ndisfile = sfincs.dis")


def _run(env, model: Path):
    import xarray as xr
    r = subprocess.run([env["sfincs_exe"]], cwd=str(model), capture_output=True, text=True)
    (model / "sfincs_run.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"SFINCS failed in {model}:\n{r.stdout[-2000:]}")
    return xr.open_dataset(model / "sfincs_map.nc")


def _dump_metrics(name: str, metrics: dict):
    """Optional record of the SFINCS test metrics (D6_METRICS_JSON=<path>), for the AUDIT block."""
    import datetime as _dt
    import json
    out = os.environ.get("D6_METRICS_JSON")
    if not out:
        return
    p = Path(out)
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    rec[name] = {"utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **metrics}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2, default=float), encoding="utf-8")


def _volume_end_m3(ds) -> tuple:
    zb = ds["zb"].values; msk = ds["msk"].values; zs = ds["zs"].isel(time=-1).values
    h = np.where(np.isfinite(zs), np.maximum(zs - zb, 0.0), 0.0); h[msk == 0] = 0.0
    return float(h.sum() * 1e4), float((msk > 0).sum() * 1e4)


class _Work(unittest.TestCase):
    PREFIX = "d6_"

    @classmethod
    def _start(cls):
        cls.env = _env()
        if cls.env is None:
            raise unittest.SkipTest("hydromt.exe / sfincs.exe not available (skill/machine.local.yaml)")
        cls.work = Path(tempfile.mkdtemp(prefix=cls.PREFIX))

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KEEP_D6_TEST_DIR"):
            print("kept", cls.work)
        else:
            shutil.rmtree(cls.work, ignore_errors=True)


class ClosedPlainMassBalance(_Work):
    """(i) 30 mm in 3 h on a closed CN-76 plain, then 20 m3/s for 12 h; 24-h run."""
    PREFIX = "d6_mass_"
    RAIN = {h: 10.0 for h in (1, 2, 3)}
    Q, T0, T1 = 20.0, 6.0, 18.0

    @classmethod
    def setUpClass(cls):
        cls._start()
        cat = _write_inputs(cls.work / "data", cls.RAIN, ndays=1)
        cls.out = {}
        for version in ("v1.4", "v1.3"):
            cfg = _cfg(version, cls.work, cn=True)
            model = cls.work / f"model_{version}"
            cls.out[version] = {"inp": _build(cfg, cls.env, cat, model)}
            _add_source(model, cls.Q, cls.T0, cls.T1, 86400.0)
            ds = _run(cls.env, model)
            v, area = _volume_end_m3(ds)
            expected = float(scs_runoff(sum(cls.RAIN.values()) / 1000.0, S_M)) * area + cls.Q * (cls.T1 - cls.T0) * 3600
            cls.out[version].update({"volume_end_m3": v, "expected_m3": expected, "ratio": v / expected})
            ds.close()
        _dump_metrics("closed_plain_mass_balance", {v: {k: x for k, x in o.items() if k != "inp"} for v, o in cls.out.items()})

    def test_v14_writes_the_flag_into_sfincs_inp(self):
        self.assertRegex(self.out["v1.4"]["inp"], r"(?m)^storecumprcp\s*=\s*1\s*$")
        self.assertRegex(self.out["v1.4"]["inp"], r"(?m)^scsfile\s*=")

    def test_v14_conserves_rain_runoff_plus_source_within_0p1_percent(self):
        o = self.out["v1.4"]
        self.assertGreater(o["expected_m3"], 8e5)
        self.assertLessEqual(abs(o["ratio"] - 1.0), 0.001, o)

    def test_v13_control_loses_the_water(self):
        """Documents the defect that v1.4 removes (published behaviour)."""
        self.assertNotIn("storecumprcp", self.out["v1.3"]["inp"])
        self.assertLess(self.out["v1.3"]["ratio"], 0.01, self.out["v1.3"])


class MultiDayInfiltrationBounds(_Work):
    """(ii) 40 mm (4 h) on day 1, 60 mm (6 h) on day 2, 80 mm (8 h) on day 3: 180 mm = 2.2 S; hourly cumulative maps."""
    PREFIX = "d6_bounds_"
    RAIN = {**{h: 10.0 for h in range(2, 6)}, **{24 + h: 10.0 for h in range(2, 8)}, **{48 + h: 10.0 for h in range(2, 10)}}

    @classmethod
    def setUpClass(cls):
        cls._start()
        cat = _write_inputs(cls.work / "data", cls.RAIN, ndays=3)
        cfg = _cfg("v1.4", cls.work, cn=True, window=(0, 0, 3))
        model = cls.work / "model"
        _build(cfg, cls.env, cat, model)
        _set_inp(model, "dtmaxout", 3600)
        ds = _run(cls.env, model)
        msk = ds["msk"].values > 0
        cls.cuminf = ds["cuminf"].values[:, msk]        # (timemax, cells) [m]
        cls.cumprcp = ds["cumprcp"].values[:, msk]
        ds.close()
        F = cls.cuminf - np.minimum(cls.cumprcp, IA_M)
        expected = cls.cumprcp - scs_runoff(cls.cumprcp, S_M)
        _dump_metrics("multi_day_bounds", {"S_m": S_M, "rain_end_m": float(np.nanmax(cls.cumprcp[-1])), "n_cells": int(msk.sum()),
                                           "n_times": int(cls.cuminf.shape[0]), "F_max_m": float(np.nanmax(F)),
                                           "min_increment_m": float(np.nanmin(np.diff(cls.cuminf, axis=0))),
                                           "max_cuminf_minus_cumprcp_m": float(np.nanmax(cls.cuminf - cls.cumprcp)),
                                           "max_abs_dev_from_scs_m": float(np.nanmax(np.abs(cls.cuminf - expected)))})

    def test_maps_are_hourly(self):
        self.assertGreaterEqual(self.cuminf.shape[0], 72)

    def test_rain_reaches_the_asymptotic_regime(self):
        self.assertGreater(float(np.nanmin(self.cumprcp[-1])), 2.0 * S_M)

    def test_cumulative_infiltration_is_monotone(self):
        self.assertTrue(np.all(np.diff(self.cuminf, axis=0) >= -1e-7))

    def test_infiltration_never_exceeds_rain(self):
        self.assertTrue(np.all(self.cuminf <= self.cumprcp + 1e-7))

    def test_continuing_abstraction_is_bounded_by_S(self):
        F = self.cuminf - np.minimum(self.cumprcp, IA_M)           # SCS: I = Ia + F, F <= S
        self.assertLessEqual(float(np.nanmax(F)), S_M + 1e-6)
        self.assertGreater(float(np.nanmax(F)), 0.5 * S_M)          # the bound is approached, not trivially met

    def test_cumulative_infiltration_follows_the_scs_curve(self):
        expected = self.cumprcp - scs_runoff(self.cumprcp, S_M)
        self.assertLess(float(np.nanmax(np.abs(self.cuminf - expected))), 1e-4)


class NonCNInvariance(_Work):
    """(iii) synthetic: CN off, 30 mm + source; the same build run with and without storecumprcp = 1."""
    PREFIX = "d6_inv_"

    @classmethod
    def setUpClass(cls):
        cls._start()
        cat = _write_inputs(cls.work / "data", ClosedPlainMassBalance.RAIN, ndays=1)
        cfg = _cfg("v1.4", cls.work, cn=False)
        base = cls.work / "built"
        cls.inp = _build(cfg, cls.env, cat, base)
        _add_source(base, 20.0, 6.0, 18.0, 86400.0)
        cls.ds = {}
        for name, extra in (("without", ""), ("with", "storecumprcp = 1")):
            m = cls.work / name
            shutil.copytree(base, m)
            if extra:
                _add_inp(m, extra)
            cls.ds[name] = _run(cls.env, m)
        _dump_metrics("non_cn_invariance", {v: {"bit_identical": bool(np.array_equal(cls.ds["without"][v].values, cls.ds["with"][v].values, equal_nan=True)),
                                                 "max_abs_diff_m": float(np.nanmax(np.abs(cls.ds["without"][v].values - cls.ds["with"][v].values)))}
                                            for v in ("zs", "zsmax")})

    @classmethod
    def tearDownClass(cls):
        for d in getattr(cls, "ds", {}).values():
            d.close()
        super().tearDownClass()

    def test_build_has_no_flag_and_no_infiltration(self):
        self.assertNotIn("storecumprcp", self.inp)
        self.assertNotIn("scsfile", self.inp)

    def test_water_levels_are_bit_identical(self):
        for v in ("zs", "zsmax"):
            self.assertTrue(np.array_equal(self.ds["without"][v].values, self.ds["with"][v].values, equal_nan=True), v)

    def test_flag_only_adds_bookkeeping_output(self):
        self.assertIn("cumprcp", self.ds["with"].data_vars)
        self.assertNotIn("cumprcp", self.ds["without"].data_vars)


if __name__ == "__main__":
    unittest.main()
