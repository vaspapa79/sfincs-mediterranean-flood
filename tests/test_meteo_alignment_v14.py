"""GO-C decision 2 / D5 — meteo-grid alignment of harness v1.4.

SFINCS v2.3.0 reads the first x/y of a netamp / netamuamv / netampr file as the LOWER-LEFT CORNER of the first
cell and places every value half a cell further along each axis (sfincs_ncinput.F90:382-385, 496-500, 606-610;
sfincs_meteo.f90:806-807, 977-978, 1109-1110: xll = x(1) + dx/2, yul = y(1) + (nrows-1)*dy + dy/2, rows flipped on
read, dy signed). hydromt_sfincs writes cell CENTRES, so every NetCDF meteo field was applied (+dx/2, +dy/2) off —
east and, for the north-up files hydromt writes (dy < 0), south. v1.4 shifts the written coordinates by
(-dx/2, -dy/2) after the build, in one function for the three files (build_model.align_meteo_grids), so that
SFINCS's centres coincide with the true centres. v1.3 is untouched.

Unit tests need netCDF4 only; the two SFINCS tests need hydromt.exe + sfincs.exe (skill/machine.local.yaml):
  (i)   linear pressure gradient -> boundary zs = (101325 - p)/(rho g) at the cell centres, RMSE ~ 0;
  (iii) a 30-min rain pulse on one IMERG cell lands on that cell's footprint.
Run: python -m unittest tests.test_meteo_alignment_v14 -v
"""
from __future__ import annotations

import os
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

from _common import EventCfg, _load_machine_override  # noqa: E402
import build_model  # noqa: E402

RHOW, G, P_REF = 1024.0, 9.81, 101325.0
CATALOG_TMPL = """meta:
  version: 1
  hydromt_version: ">=0.10"
  root: {root}

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

era5_hourly:
  data_type: RasterDataset
  driver: netcdf
  path: era5_synth.nc
  crs: 4326

imerg_half_hourly:
  data_type: RasterDataset
  driver: netcdf
  path: imerg_synth.nc
  crs: 4326
"""


# ----------------------------------------------------------------------------------------------- unit tests
class CornerAlignedCoords(unittest.TestCase):
    """The pure coordinate rule: write x - dx/2, y - dy/2 (dy signed)."""

    def test_shift_is_minus_half_cell_along_each_axis(self):
        x, y = build_model.corner_aligned_coords([0.0, 10.0, 20.0], [100.0, 90.0, 80.0])
        np.testing.assert_allclose(x, [-5.0, 5.0, 15.0])
        np.testing.assert_allclose(y, [105.0, 95.0, 85.0])          # north-up file: shifted north

    def test_ascending_y_is_shifted_south(self):
        _, y = build_model.corner_aligned_coords([0.0, 10.0], [80.0, 90.0, 100.0])
        np.testing.assert_allclose(y, [75.0, 85.0, 95.0])

    def test_sfincs_read_rule_recovers_the_original_centres(self):
        """Emulates sfincs_ncinput.F90:496-500 + sfincs_meteo.f90:977-978 on the written coordinates."""
        x0 = 555_000.0 + 23_774.0 * np.arange(6)
        y0 = 4_444_000.0 - 23_774.0 * np.arange(5)                       # descending, as hydromt writes
        xw, yw = build_model.corner_aligned_coords(x0, y0)
        dx, dy = xw[1] - xw[0], yw[1] - yw[0]
        xll = xw[0] + 0.5 * dx
        np.testing.assert_allclose(xll + dx * np.arange(6), x0)         # column ix sits at xll + (ix-1) dx
        yul = yw[0] + (yw.size - 1) * dy + 0.5 * dy
        # internal row iy (rows flipped on read) = file row n+1-iy, located at yul - (iy-1) dy
        for iy in range(1, yw.size + 1):
            self.assertAlmostEqual(yul - (iy - 1) * dy, y0[yw.size - iy], places=6)


def _write_hydromt_like(path: Path, var: str, data, x, y, units: str, tref: str = "2017-01-01"):
    """A NetCDF file shaped like hydromt_sfincs' precip_2d / press_2d / wind_2d output."""
    import netCDF4
    data = np.asarray(data, dtype="float32")
    with netCDF4.Dataset(path, "w") as nc:
        nc.createDimension("time", data.shape[0]); nc.createDimension("y", len(y)); nc.createDimension("x", len(x))
        t = nc.createVariable("time", "f8", ("time",)); t[:] = np.arange(data.shape[0]) * 60.0
        t.units = f"minutes since {tref}"; t.calendar = "proleptic_gregorian"
        vx = nc.createVariable("x", "f8", ("x",)); vx[:] = x; vx.axis = "X"; vx.units = "metre"
        vy = nc.createVariable("y", "f8", ("y",)); vy[:] = y; vy.axis = "Y"; vy.units = "metre"
        sr = nc.createVariable("spatial_ref", "i8", ()); sr.crs_wkt = "EPSG:32634"
        v = nc.createVariable(var, "f4", ("time", "y", "x"), fill_value=np.nan); v[:] = data
        v.units = units; v.coordinates = "spatial_ref"
        nc.units = units


def _read(path: Path):
    import netCDF4
    with netCDF4.Dataset(path) as nc:
        var = [v for v in nc.variables if nc[v].ndim == 3][0]
        return {"x": nc["x"][:].filled(np.nan), "y": nc["y"][:].filled(np.nan), "time": nc["time"][:].filled(np.nan),
                "time_units": nc["time"].units, "data": nc[var][:].filled(np.nan), "var": var,
                "var_attrs": {a: nc[var].getncattr(a) for a in nc[var].ncattrs()},
                "global": {a: nc.getncattr(a) for a in nc.ncattrs()}}


class AlignMeteoGridFile(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="d5_file_"))
        self.x = 500_000.0 + 1000.0 * np.arange(4)
        self.y = 4_000_000.0 - 1000.0 * np.arange(3)
        self.data = np.random.default_rng(1).normal(101000, 300, (2, 3, 4))
        self.f = self.d / "press_2d.nc"
        _write_hydromt_like(self.f, "barometric_pressure", self.data, self.x, self.y, "Pa")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_coordinates_shift_and_data_do_not_change(self):
        rep = build_model.align_meteo_grid_file(self.f)
        r = _read(self.f)
        np.testing.assert_allclose(r["x"], self.x - 500.0)
        np.testing.assert_allclose(r["y"], self.y + 500.0)
        np.testing.assert_allclose(r["data"], self.data.astype("float32"))
        self.assertTrue(rep["applied"]); self.assertEqual((rep["x_shift"], rep["y_shift"]), (-500.0, 500.0))

    def test_time_axis_and_attributes_are_preserved(self):
        before = _read(self.f)
        build_model.align_meteo_grid_file(self.f)
        after = _read(self.f)
        np.testing.assert_array_equal(after["time"], before["time"])
        self.assertEqual(after["time_units"], before["time_units"])
        self.assertEqual(after["var"], "barometric_pressure")
        strip = lambda d: {k: v for k, v in d.items() if k != "_FillValue"}  # noqa: E731  (nan != nan)
        self.assertEqual(strip(after["var_attrs"]), strip(before["var_attrs"]))
        self.assertTrue(np.isnan(after["var_attrs"]["_FillValue"]) and np.isnan(before["var_attrs"]["_FillValue"]))

    def test_is_idempotent(self):
        build_model.align_meteo_grid_file(self.f)
        rep = build_model.align_meteo_grid_file(self.f)
        self.assertFalse(rep["applied"])
        np.testing.assert_allclose(_read(self.f)["x"], self.x - 500.0)      # not shifted twice

    def test_records_the_shift_in_the_global_attributes(self):
        build_model.align_meteo_grid_file(self.f)
        g = _read(self.f)["global"]
        self.assertEqual(int(g[build_model.ALIGN_ATTR]), 1)
        self.assertEqual((float(g["x_shift_m"]), float(g["y_shift_m"])), (-500.0, 500.0))
        self.assertIn("sfincs_meteo.f90", g["sfincs_corner_alignment_note"])


def _raw(version, work, **kw) -> dict:
    raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-02"},
           "window": {"spinup_days": 1, "pre_event_days": 1, "post_event_days": 0},
           "bbox": {"west": 23.0, "south": 35.0, "east": 23.1, "north": 35.09}, "crs": {"epsg": 32634},
           "grid": {"res": 100, "zmin": -2, "zmax": 250},
           "paths": {"work_dir": str(work), "deliverable_dir": str(work / "d"),
                     "manning_lookup": str(REPO / "skill" / "manning_lookup.csv")},
           "rain_source": "era5_hourly", "coastal_bc": {"enabled": True, "pavbnd": 1},
           "wind_pressure": {"enabled": True}, "harness_version": version}
    raw.update(kw)
    return raw


def _cfg(version, work, **kw) -> EventCfg:
    return EventCfg(raw=_raw(version, work, **kw), config_path=Path("synth.yaml"))


class AlignMeteoGrids(unittest.TestCase):
    """The model-directory entry point: v1.4 aligns every file named in sfincs.inp, v1.3 touches nothing."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="d5_model_"))
        x = 500_000.0 + 1000.0 * np.arange(4); y = 4_000_000.0 - 1000.0 * np.arange(3)
        _write_hydromt_like(self.d / "precip_2d.nc", "Precipitation", np.ones((2, 3, 4)), x, y, "mm/h")
        _write_hydromt_like(self.d / "press_2d.nc", "barometric_pressure", np.ones((2, 3, 4)), x, y, "Pa")
        (self.d / "sfincs.inp").write_text("tref = 20170101 000000\nnetamprfile = precip_2d.nc\n"
                                           "netampfile = press_2d.nc\nnetamuamvfile = wind_2d.nc\n")
        self.bytes_before = {f: (self.d / f).read_bytes() for f in ("precip_2d.nc", "press_2d.nc")}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_v13_is_a_no_op(self):
        self.assertEqual(build_model.align_meteo_grids(_cfg("v1.3", self.d), self.d), [])
        for f, b in self.bytes_before.items():
            self.assertEqual((self.d / f).read_bytes(), b, f)

    def test_v14_aligns_every_present_file_named_in_sfincs_inp(self):
        reps = build_model.align_meteo_grids(_cfg("v1.4", self.d), self.d)
        self.assertEqual(sorted(r["key"] for r in reps), ["netampfile", "netamprfile"])   # wind file absent -> skipped
        self.assertTrue(all(r["applied"] for r in reps))
        for f in ("precip_2d.nc", "press_2d.nc"):
            np.testing.assert_allclose(_read(self.d / f)["x"], 500_000.0 + 1000.0 * np.arange(4) - 500.0)

    def test_v14_without_meteo_files_does_nothing(self):
        (self.d / "sfincs.inp").write_text("tref = 20170101 000000\n")
        self.assertEqual(build_model.align_meteo_grids(_cfg("v1.4", self.d), self.d), [])


# ----------------------------------------------------------------------------------------------- SFINCS tests
def _env():
    env = dict((_load_machine_override().get("env") or {}))
    return env if all(env.get(k) and Path(env[k]).exists() for k in ("hydromt", "sfincs_exe")) else None


def _write_rasters(data: Path, bbox, dep_val: float, lulc_val: int):
    import rasterio
    from rasterio.transform import from_origin
    w, s, e, n = bbox
    res = 0.0005
    ny, nx = int(round((n - s + 0.02) / res)), int(round((e - w + 0.02) / res))
    tr = from_origin(w - 0.01, n + 0.01, res, res)
    for name, val, dtype, nod in (("dep.tif", dep_val, "float32", -9999.0), ("landuse.tif", lulc_val, "uint8", 0)):
        with rasterio.open(data / name, "w", driver="GTiff", height=ny, width=nx, count=1, dtype=dtype,
                           crs="EPSG:4326", transform=tr, nodata=nod) as dst:
            dst.write(np.full((ny, nx), val, dtype=dtype), 1)


def _write_gradient_inputs(data: Path, bbox) -> Path:
    """0-m plane everywhere (every edge cell becomes msk = 2), no rain/wind, pressure linear in lon and lat."""
    import pandas as pd
    import xarray as xr
    data.mkdir(parents=True, exist_ok=True)
    w, s, e, n = bbox
    _write_rasters(data, bbox, 0.0, 80)
    time = pd.date_range("2016-12-31 00:00", "2017-01-03 00:00", freq="1h")
    lat = np.arange(n + 0.5, s - 0.5, -0.25); lon = np.arange(w - 0.5, e + 0.5, 0.25)
    # p falls to the east and RISES to the north: the gradient points NW, i.e. along the SE half-cell shift SFINCS
    # applies to an unaligned file (a gradient perpendicular to that diagonal would hide the error).
    A = B = 4000.0                                                       # Pa per degree
    p2d = (P_REF - 2500.0) - A * (lon[None, :] - 0.5 * (w + e)) + B * (lat[:, None] - 0.5 * (s + n))
    shape = (time.size, lat.size, lon.size)
    ds = xr.Dataset({"precip": (("time", "latitude", "longitude"), np.zeros(shape, "float32"), {"units": "mm/h"}),
                     "wind10_u": (("time", "latitude", "longitude"), np.zeros(shape, "float32")),
                     "wind10_v": (("time", "latitude", "longitude"), np.zeros(shape, "float32")),
                     "press_msl": (("time", "latitude", "longitude"), np.broadcast_to(p2d, shape).astype("float32"), {"units": "Pa"})},
                    coords={"time": time, "latitude": lat, "longitude": lon})
    ds.to_netcdf(data / "era5_synth.nc")
    (data / "data_catalog.yml").write_text(CATALOG_TMPL.format(root=data.as_posix()), encoding="utf-8")
    return data / "data_catalog.yml"


def _write_pulse_inputs(data: Path, bbox) -> Path:
    """Flat land (10 m, grass), IMERG-like 0.1-deg half-hourly rates: 20 mm/h for 00:30-01:00 on ONE cell."""
    import pandas as pd
    import xarray as xr
    data.mkdir(parents=True, exist_ok=True)
    w, s, e, n = bbox
    _write_rasters(data, bbox, 10.0, 30)
    lon = np.round(np.arange(w - 0.25, e + 0.25, 0.1) + 0.05, 3)
    lat = np.round(np.arange(s - 0.25, n + 0.25, 0.1) + 0.05, 3)
    time = pd.date_range("2017-01-01 00:00", "2017-01-02 00:00", freq="30min")
    data3 = np.zeros((time.size, lat.size, lon.size), "float32")
    j = int(np.argmin(np.abs(lat - 0.5 * (s + n)))); i = int(np.argmin(np.abs(lon - 0.5 * (w + e))))
    data3[1, j, i] = 20.0                                                 # stamp 00:30 = interval start (IMERG)
    ds = xr.Dataset({"precip": (("time", "latitude", "longitude"), data3, {"units": "mm/h"})},
                    coords={"time": time, "latitude": lat, "longitude": lon})
    ds.to_netcdf(data / "imerg_synth.nc")
    (data / "data_catalog.yml").write_text(CATALOG_TMPL.format(root=data.as_posix()), encoding="utf-8")
    return data / "data_catalog.yml"


def _dump_metrics(name: str, metrics: dict):
    """Optional record of the SFINCS test metrics (D5_METRICS_JSON=<path>), for the AUDIT block."""
    import datetime as _dt
    import json
    out = os.environ.get("D5_METRICS_JSON")
    if not out:
        return
    p = Path(out)
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    rec[name] = {"utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **metrics}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2, default=float), encoding="utf-8")


def _hydromt_build(cfg, env, catalog, model: Path):
    yml = model.parent / f"sfincs_build_{model.name}.yml"
    yml.write_text(build_model.render_build_yml(cfg), encoding="utf-8")
    model.mkdir(parents=True, exist_ok=True)
    res = subprocess.run([env["hydromt"], "build", "sfincs", str(model), "-i", str(yml), "-d", str(catalog), "--fo"],
                         capture_output=True, text=True)
    (model.parent / f"hydromt_{model.name}.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"hydromt build failed:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")


def _run_sfincs(env, model: Path):
    run = subprocess.run([env["sfincs_exe"]], cwd=str(model), capture_output=True, text=True)
    (model.parent / f"sfincs_{model.name}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    import xarray as xr
    return xr.open_dataset(model / "sfincs_map.nc")


def _set_inp(model: Path, **kv):
    lines = [ln for ln in (model / "sfincs.inp").read_text().splitlines() if ln.split("=")[0].strip() not in kv]
    lines += [f"{k:<20} = {v}" for k, v in kv.items()]
    (model / "sfincs.inp").write_text("\n".join(lines) + "\n")


def _bilinear_at(nc_path: Path, var: str, xs, ys, time=None):
    """The written grid, bilinearly interpolated at the TRUE model cell centres (file coordinates = centres)."""
    import xarray as xr
    da = xr.open_dataset(nc_path)[var]
    if time is not None:
        da = da.isel(time=time)
    return da.interp(x=xr.DataArray(xs, dims="pt"), y=xr.DataArray(ys, dims="pt"), method="linear").values


class LinearPressureGradient(unittest.TestCase):
    """(i): with a pressure field linear in both directions, the boundary level must equal
    (101325 - p)/(rho g) with p read at the cell centres of the written press_2d.nc. The half-cell shift of
    the unaligned file is the control (it must fail the same assertion)."""
    BBOX = (23.0, 35.0, 23.1, 35.09)

    @classmethod
    def setUpClass(cls):
        cls.env = _env()
        if cls.env is None:
            raise unittest.SkipTest("hydromt.exe / sfincs.exe not available (skill/machine.local.yaml)")
        cls.work = Path(tempfile.mkdtemp(prefix="d5_grad_"))
        cat = _write_gradient_inputs(cls.work / "data", cls.BBOX)
        cfg = _cfg("v1.4", cls.work)
        built = cls.work / "built"
        _hydromt_build(cfg, cls.env, cat, built)
        build_model.inject_waterlevel_bnd(cfg, built)
        cls.unaligned = cls.work / "unaligned"; shutil.copytree(built, cls.unaligned)
        cls.aligned = cls.work / "aligned"; shutil.copytree(built, cls.aligned)
        cls.reps = build_model.align_meteo_grids(cfg, cls.aligned)
        cls.err = {}
        for name, model in (("unaligned", cls.unaligned), ("aligned", cls.aligned)):
            ds = _run_sfincs(cls.env, model)
            msk = ds["msk"].values; zs = ds["zs"].isel(time=-1).values
            rows, cols = np.where(msk == 2)
            xs = ds["x"].values[rows, cols]; ys = ds["y"].values[rows, cols]
            p = _bilinear_at(built / "press_2d.nc", "barometric_pressure", xs, ys, time=-1)   # true centres
            exp = (P_REF - p) / (RHOW * G); mod = zs[rows, cols]
            ok = np.isfinite(mod) & np.isfinite(exp)
            d = mod[ok] - exp[ok]
            cls.err[name] = {"rmse": float(np.sqrt(np.mean(d ** 2))), "max": float(np.abs(d).max()),
                             "mean": float(d.mean()), "n": int(ok.sum()), "exp_range": [float(exp[ok].min()), float(exp[ok].max())]}
        _dump_metrics("linear_pressure_gradient", {"meteo_cell_m": [cls.reps[0]["dx"], cls.reps[0]["dy"]], **cls.err})

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KEEP_D5_TEST_DIR"):
            print("kept", cls.work)
        else:
            shutil.rmtree(cls.work, ignore_errors=True)

    def test_all_three_meteo_files_were_aligned(self):
        self.assertEqual(sorted(r["key"] for r in self.reps), ["netampfile", "netamprfile", "netamuamvfile"])

    def test_aligned_boundary_matches_the_inverse_barometer_at_the_cell_centres(self):
        e = self.err["aligned"]
        self.assertGreater(e["n"], 100)
        self.assertGreater(e["exp_range"][1] - e["exp_range"][0], 0.02, "gradient too weak to be a test")
        self.assertLess(e["rmse"], 0.002, e)
        self.assertLess(e["max"], 0.005, e)

    def test_unaligned_control_shows_the_half_cell_error(self):
        self.assertGreater(self.err["unaligned"]["rmse"], 0.02, self.err["unaligned"])


class RainPulseFootprint(unittest.TestCase):
    """(iii): the cumulative rain SFINCS deposits from a 30-min pulse on one IMERG cell must follow the written
    grid interpolated at the true cell centres (centroid on the cell, 56 % of the volume inside its footprint for
    the bilinear tent); unaligned it lands half a cell to the south-east."""
    BBOX = (23.0, 35.0, 23.4, 35.33)

    @classmethod
    def setUpClass(cls):
        cls.env = _env()
        if cls.env is None:
            raise unittest.SkipTest("hydromt.exe / sfincs.exe not available (skill/machine.local.yaml)")
        cls.work = Path(tempfile.mkdtemp(prefix="d5_pulse_"))
        cat = _write_pulse_inputs(cls.work / "data", cls.BBOX)
        cfg = _cfg("v1.4", cls.work, bbox={"west": cls.BBOX[0], "south": cls.BBOX[1], "east": cls.BBOX[2], "north": cls.BBOX[3]},
                   window={"spinup_days": 0, "pre_event_days": 1, "post_event_days": 0}, grid={"res": 150, "zmin": -2, "zmax": 250},
                   rain_source="imerg_half_hourly", coastal_bc={"enabled": False, "pavbnd": 1}, wind_pressure={"enabled": False})
        built = cls.work / "built"
        _hydromt_build(cfg, cls.env, cat, built)
        _set_inp(built, tstop="20170101 030000", dtmaxout=10800, storecumprcp=1, dtout=3600)
        cls.unaligned = cls.work / "unaligned"; shutil.copytree(built, cls.unaligned)
        cls.aligned = cls.work / "aligned"; shutil.copytree(built, cls.aligned)
        build_model.align_meteo_grids(cfg, cls.aligned)
        import xarray as xr
        wr = xr.open_dataset(built / "precip_2d.nc")["Precipitation"]
        cls.cell = (float(abs(wr.x[1] - wr.x[0])), float(abs(wr.y[1] - wr.y[0])))
        peak = wr.max("time"); cls.footprint = peak.where(peak > 0).stack(c=("y", "x")).dropna("c")   # written pulse cells
        cls.res = {}
        for name, model in (("unaligned", cls.unaligned), ("aligned", cls.aligned)):
            ds = _run_sfincs(cls.env, model)
            cum = ds["cumprcp"].isel(timemax=-1).values; cum = np.where(np.isfinite(cum), cum, 0.0)   # m
            x2, y2 = ds["x"].values, ds["y"].values
            rate = _bilinear_at(built / "precip_2d.nc", "Precipitation", x2.ravel(), y2.ravel(), time=1).reshape(x2.shape)
            exp = np.nan_to_num(rate) * 0.5 / 1000.0                                                     # 20 mm/h x 0.5 h
            inside = np.zeros(x2.shape, bool)
            for cx, cy in zip(cls.footprint.x.values, cls.footprint.y.values):
                inside |= (np.abs(x2 - cx) <= cls.cell[0] / 2) & (np.abs(y2 - cy) <= cls.cell[1] / 2)
            def centroid(f):
                return (float((f * x2).sum() / f.sum()), float((f * y2).sum() / f.sum()))
            cls.res[name] = {"total_mm_model": float(cum.sum() * 1000 / cum.size), "rel_rmse": float(np.sqrt(np.mean((cum - exp) ** 2)) / exp.max()),
                             "frac_inside_model": float(cum[inside].sum() / cum.sum()), "frac_inside_expected": float(exp[inside].sum() / exp.sum()),
                             "centroid_offset_m": tuple(np.subtract(centroid(cum), centroid(exp))), "n_footprint_cells": int(cls.footprint.size)}
        _dump_metrics("rain_pulse_footprint", {"meteo_cell_m": list(cls.cell), **cls.res})

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KEEP_D5_TEST_DIR"):
            print("kept", cls.work)
        else:
            shutil.rmtree(cls.work, ignore_errors=True)

    def test_aligned_pulse_lands_on_the_written_footprint(self):
        r = self.res["aligned"]
        self.assertLess(r["rel_rmse"], 0.03, r)
        self.assertAlmostEqual(r["frac_inside_model"], r["frac_inside_expected"], delta=0.02, msg=r)
        self.assertLess(float(np.hypot(*r["centroid_offset_m"])), 300.0, r)              # within two model cells

    def test_unaligned_control_lands_half_a_cell_south_east(self):
        r = self.res["unaligned"]
        dxo, dyo = r["centroid_offset_m"]
        self.assertGreater(dxo, 0.3 * self.cell[0], r); self.assertLess(dyo, -0.3 * self.cell[1], r)
        self.assertGreater(r["rel_rmse"], 0.2, r)
        self.assertLess(r["frac_inside_model"], r["frac_inside_expected"] - 0.15, r)


if __name__ == "__main__":
    unittest.main()
