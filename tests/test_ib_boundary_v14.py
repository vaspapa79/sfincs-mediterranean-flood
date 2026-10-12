"""CODE-12 D2 integration test — the inverse barometer at the SFINCS water-level boundary.

A uniform 25-hPa depression (p = 101325 - 2500 Pa) over a synthetic flat coastal domain (GLO-30-like
sea plane at 0 m, every edge cell msk = 2) must raise the boundary water level by
(pavbnd - p) / (rhow g) = 2500 / (1024 x 9.81) = +0.249 m under harness v1.4 (bnd points + bzs = 0 m +
pavbnd = 101325 Pa), while the published v1.3 setup (pavbnd = 1, no bnd points) leaves it at 0 m.

Needs hydromt.exe + sfincs.exe from skill/machine.local.yaml (skipped when absent). Runs the real
pipeline path: build_model.render_build_yml -> `hydromt build sfincs` -> build_model.inject_waterlevel_bnd
-> sfincs.exe. ~1-2 min.  Run: python -m unittest tests.test_ib_boundary_v14 -v
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

RHOW, G = 1024.0, 9.81
P_REF, P_SYNTH = 101325.0, 101325.0 - 2500.0
EXPECTED_M = (P_REF - P_SYNTH) / (RHOW * G)          # 0.2489 m
BBOX = (23.0, 35.0, 23.1, 35.09)                      # ~9.1 x 10.0 km -> 91 x 100 cells at 100 m


def _env():
    ov = _load_machine_override()
    env = dict(ov.get("env") or {})
    ok = all(env.get(k) and Path(env[k]).exists() for k in ("hydromt", "sfincs_exe"))
    return env if ok else None


def _cfg(version: str, work: Path) -> EventCfg:
    raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-02"},
           "window": {"spinup_days": 1, "pre_event_days": 1, "post_event_days": 0},   # tref 12-31, tstart 01-01, tstop 01-03
           "bbox": {"west": BBOX[0], "south": BBOX[1], "east": BBOX[2], "north": BBOX[3]},
           "crs": {"epsg": 32634},
           "grid": {"res": 100, "zmin": -2, "zmax": 250},
           "paths": {"work_dir": str(work), "deliverable_dir": str(work / "deliverable"),
                     "manning_lookup": str(REPO / "skill" / "manning_lookup.csv")},
           "rain_source": "era5_hourly",
           "coastal_bc": {"enabled": True, "pavbnd": 1},
           "wind_pressure": {"enabled": True},
           "harness_version": version}
    return EventCfg(raw=raw, config_path=Path("synth.yaml"))


def _write_synthetic_inputs(data: Path) -> Path:
    """dep = 0 m plane, landuse = 80 (water), ERA5-like file with p = 98825 Pa, no wind, no rain."""
    import pandas as pd
    import rasterio
    import xarray as xr
    from rasterio.transform import from_origin
    data.mkdir(parents=True, exist_ok=True)
    w, s, e, n = BBOX
    res = 0.0005                                                          # ~50 m
    ny, nx = int(round((n - s + 0.02) / res)), int(round((e - w + 0.02) / res))
    tr = from_origin(w - 0.01, n + 0.01, res, res)
    for name, val, dtype in (("dep.tif", 0.0, "float32"), ("landuse.tif", 80, "uint8")):
        with rasterio.open(data / name, "w", driver="GTiff", height=ny, width=nx, count=1, dtype=dtype,
                           crs="EPSG:4326", transform=tr, nodata=(-9999 if dtype == "float32" else 0)) as dst:
            dst.write(np.full((ny, nx), val, dtype=dtype), 1)
    time = pd.date_range("2016-12-31 00:00", "2017-01-03 00:00", freq="1h")
    lat = np.arange(n + 0.5, s - 0.5, -0.25); lon = np.arange(w - 0.5, e + 0.5, 0.25)
    shape = (time.size, lat.size, lon.size)
    ds = xr.Dataset({"precip": (("time", "latitude", "longitude"), np.zeros(shape, "float32"), {"units": "mm/h"}),
                     "wind10_u": (("time", "latitude", "longitude"), np.zeros(shape, "float32"), {"units": "m s**-1"}),
                     "wind10_v": (("time", "latitude", "longitude"), np.zeros(shape, "float32"), {"units": "m s**-1"}),
                     "press_msl": (("time", "latitude", "longitude"), np.full(shape, P_SYNTH, "float32"), {"units": "Pa"})},
                    coords={"time": time, "latitude": lat, "longitude": lon})
    ds.to_netcdf(data / "era5_synth.nc")
    cat = (data / "data_catalog.yml")
    cat.write_text(f"""meta:
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

era5_hourly:
  data_type: RasterDataset
  driver: netcdf
  path: era5_synth.nc
  crs: 4326
""", encoding="utf-8")
    return cat


def _build_and_run(cfg: EventCfg, env: dict, catalog: Path, model: Path) -> dict:
    import xarray as xr
    yml = model.parent / f"sfincs_build_{cfg.harness_version}.yml"
    yml.write_text(build_model.render_build_yml(cfg), encoding="utf-8")
    model.mkdir(parents=True, exist_ok=True)
    res = subprocess.run([env["hydromt"], "build", "sfincs", str(model), "-i", str(yml), "-d", str(catalog), "--fo"],
                         capture_output=True, text=True)
    (model.parent / f"hydromt_{cfg.harness_version}.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"hydromt build failed:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
    n_bnd = build_model.inject_waterlevel_bnd(cfg, model)
    run = subprocess.run([env["sfincs_exe"]], cwd=str(model), capture_output=True, text=True)
    (model.parent / f"sfincs_{cfg.harness_version}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    ds = xr.open_dataset(model / "sfincs_map.nc")
    msk = ds["msk"].values
    zs_last = ds["zs"].isel(time=-1).values
    inp = (model / "sfincs.inp").read_text()
    return {"n_bnd": n_bnd, "msk2": int((msk == 2).sum()), "zs_bnd": zs_last[msk == 2], "zs_int": zs_last[msk == 1],
            "has_bndfile": "bndfile" in inp, "pavbnd_line": [ln for ln in inp.splitlines() if ln.startswith("pavbnd")],
            "log": run.stdout, "n_times": int(ds.sizes["time"])}


class InverseBarometerAtTheBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _env()
        if cls.env is None:
            raise unittest.SkipTest("hydromt.exe / sfincs.exe not available (skill/machine.local.yaml)")
        cls.work = Path(tempfile.mkdtemp(prefix="ib_v14_"))
        cls.catalog = _write_synthetic_inputs(cls.work / "data")

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KEEP_IB_TEST_DIR"):
            print("kept", cls.work)
        else:
            shutil.rmtree(cls.work, ignore_errors=True)

    def test_v14_boundary_rises_by_the_inverse_barometer(self):
        out = _build_and_run(_cfg("v1.4", self.work), self.env, self.catalog, self.work / "model_v14")
        self.assertGreaterEqual(out["n_bnd"], 1)
        self.assertTrue(out["has_bndfile"])
        self.assertEqual(out["pavbnd_line"], ["pavbnd               = 101325"])
        self.assertGreater(out["msk2"], 0)
        zs = out["zs_bnd"][np.isfinite(out["zs_bnd"])]
        self.assertGreater(zs.size, 0, "boundary cells never wet")
        self.assertAlmostEqual(float(np.nanmean(zs)), EXPECTED_M, delta=0.01, msg=f"mean boundary zs {np.nanmean(zs):.4f}")
        self.assertLess(float(np.nanmax(np.abs(zs - EXPECTED_M))), 0.02)
        zi = out["zs_int"][np.isfinite(out["zs_int"])]
        self.assertGreater(float(np.nanmean(zi)), 0.2, "interior did not fill from the raised boundary")

    def test_v13_boundary_stays_at_zero(self):
        """The published setup: pavbnd = 1 (treated as off by SFINCS) and no bnd points."""
        out = _build_and_run(_cfg("v1.3", self.work), self.env, self.catalog, self.work / "model_v13")
        self.assertEqual(out["n_bnd"], 0)
        self.assertFalse(out["has_bndfile"])
        self.assertEqual(out["pavbnd_line"], ["pavbnd               = 1"])
        self.assertIn("Boundary cells found in mask without boundary points", out["log"])
        zs = out["zs_bnd"][np.isfinite(out["zs_bnd"])]
        self.assertTrue(zs.size == 0 or float(np.nanmax(np.abs(zs))) < 0.005, f"max |zs| {np.nanmax(np.abs(zs)) if zs.size else 'nan'}")


if __name__ == "__main__":
    unittest.main()
