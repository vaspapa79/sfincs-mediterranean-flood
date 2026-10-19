"""CODE-13 D4 — coastal set-up of harness v1.4 (behind `harness_version: v1.4`; v1.3 untouched).

(1) open-sea cells (active, dep <= 0, connected to the grid edge through dep <= 0 cells) become inactive
    except a one-cell ring adjacent to land, which setup_mask_bounds turns into msk = 2 (msk = 2 wherever
    z <= 0 AT THE COAST); inland dep <= 0 cells stay active land;
(2) bnd points every BND_SPACING_M along that ring (existing waterlevel_bnd_points);
(3) every active cell starts dry regardless of zb: SFINCS sets zs = max(z_zmin, zsini) at t0
    (sfincs_initial_conditions.F90:43,98-100), so zsini = -9999 gives zs = bed level everywhere;
(4) is a reporting item (evaluation-mask options), not code.

Run: python -m unittest tests.test_coastal_setup_v14 -v  (the SFINCS strip test needs hydromt.exe + sfincs.exe)
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
P_SYNTH = 101325.0 - 2500.0
EXPECTED_M = 2500.0 / (RHOW * G)
BBOX = (23.0, 35.0, 23.1, 35.09)            # ~9.1 x 10.0 km


def _raw(version, work, rain_source="era5_hourly", coastal=True) -> dict:
    return {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-02"},
            "window": {"spinup_days": 1, "pre_event_days": 1, "post_event_days": 0},
            "bbox": {"west": BBOX[0], "south": BBOX[1], "east": BBOX[2], "north": BBOX[3]},
            "crs": {"epsg": 32634}, "grid": {"res": 100, "zmin": -2, "zmax": 250},
            "paths": {"work_dir": str(work), "deliverable_dir": str(work / "d"),
                      "manning_lookup": str(REPO / "skill" / "manning_lookup.csv")},
            "rain_source": rain_source, "coastal_bc": {"enabled": coastal, "pavbnd": 1},
            "wind_pressure": {"enabled": True}, "harness_version": version}


def _cfg(version="v1.4", work=Path("D:/tmp/synth"), **kw) -> EventCfg:
    return EventCfg(raw=_raw(version, work, **kw), config_path=Path("synth.yaml"))


class OpenSeaSplit(unittest.TestCase):
    """Pure array logic: (i) open sea vs (ii) inland dep <= 0, and the coastal ring."""

    def _case(self):
        dep = np.full((8, 10), 5.0)
        dep[:, 6:] = 0.0                  # open sea on the east, touching the edge
        dep[3, 1] = -1.0                  # inland pit (not connected)
        dep[0, 2] = 0.0                   # a dep<=0 cell on the north edge, not connected to the sea by dep<=0 cells
        active = np.ones_like(dep, dtype=bool)
        return dep, active

    def test_open_sea_is_edge_connected_and_inland_is_not(self):
        dep, active = self._case()
        sea, open_sea, inland = build_model.open_sea_split(active, dep)
        self.assertEqual(int(open_sea.sum()), 8 * 4 + 1)       # the east block plus the lone north-edge cell
        self.assertTrue(open_sea[0, 2]); self.assertFalse(open_sea[3, 1]); self.assertTrue(inland[3, 1])
        self.assertEqual(int(inland.sum()), 1)

    def test_diagonal_only_contact_does_not_connect(self):
        dep = np.full((6, 6), 5.0); dep[:, 4:] = 0.0; dep[2, 3] = 0.0; dep[1, 2] = 0.0    # (1,2) touches (2,3) only diagonally
        active = np.ones_like(dep, dtype=bool)
        _, open_sea, inland = build_model.open_sea_split(active, dep)
        self.assertTrue(open_sea[2, 3]); self.assertFalse(open_sea[1, 2]); self.assertTrue(inland[1, 2])

    def test_inactive_cells_are_ignored(self):
        dep, active = self._case(); active[:, 6:] = False
        _, open_sea, inland = build_model.open_sea_split(active, dep)
        self.assertEqual(int(open_sea.sum()), 1)               # only the north-edge cell remains

    def test_coastal_ring_is_one_cell_wide_and_touches_land(self):
        dep, active = self._case()
        _, open_sea, _ = build_model.open_sea_split(active, dep)
        ring, exclude = build_model.coastal_ring(open_sea, active)
        self.assertEqual(int(ring.sum()), 8 + 1)               # column 6 (8 cells) + the north-edge cell (its neighbours are land)
        self.assertTrue(ring[:, 6].all()); self.assertFalse(ring[:, 7].any())
        self.assertEqual(int(exclude.sum()), 8 * 3)             # columns 7-9
        self.assertFalse((ring & exclude).any())

    def test_no_sea_gives_empty_masks(self):
        dep = np.full((5, 5), 3.0); active = np.ones_like(dep, dtype=bool)
        _, open_sea, inland = build_model.open_sea_split(active, dep)
        ring, exclude = build_model.coastal_ring(open_sea, active)
        self.assertEqual(int(open_sea.sum() + inland.sum() + ring.sum() + exclude.sum()), 0)


class BuildYmlCoastal(unittest.TestCase):
    def test_v13_keeps_zsini_zero_and_no_exclusion(self):
        y = build_model.render_build_yml(_cfg("v1.3"))
        self.assertIn("  zsini: 0\n", y); self.assertNotIn("exclude_mask", y); self.assertNotIn("all_touched", y)

    def test_v14_starts_every_cell_dry(self):
        y = build_model.render_build_yml(_cfg("v1.4"))
        self.assertIn("  zsini: -9999\n", y); self.assertNotIn("zsini: 0\n", y)

    def test_v14_exclusion_file_enters_setup_mask_active_only(self):
        y = build_model.render_build_yml(_cfg("v1.4"), exclude_mask="D:/x/open_sea_exclude.geojson")
        block = y.split("setup_mask_active:")[1].split("setup_mask_bounds:")[0]
        self.assertIn("  exclude_mask: D:/x/open_sea_exclude.geojson\n", block)
        self.assertIn("  all_touched: false\n", block)
        self.assertNotIn("exclude_mask", y.split("setup_mask_bounds:")[1])

    def test_v14_without_open_sea_renders_no_exclusion(self):
        y = build_model.render_build_yml(_cfg("v1.4"), exclude_mask=None)
        self.assertNotIn("exclude_mask", y)

    def test_v13_ignores_an_exclusion_file(self):
        self.assertEqual(build_model.render_build_yml(_cfg("v1.3"), exclude_mask="D:/x/e.geojson"),
                         build_model.render_build_yml(_cfg("v1.3")))

    def test_published_records_still_reproduced(self):
        import re
        from _common import load_config
        for ex, asr in {"emsr122_strymonas_enhanced.yaml": "emsr122_sfincs_enhanced",
                        "emsr257_mandra_enhanced.yaml": "mandra_sfincs_enhanced",
                        "emsr692_pineios_enhanced.yaml": "pineios_sfincs_enhanced"}.items():
            cfg = load_config(["--config", str(REPO / "skill" / "examples" / ex)])
            norm = lambda s: re.sub(r"reclass_table: .*", "reclass_table: X", s)  # noqa: E731
            self.assertEqual(norm(build_model.render_build_yml(cfg)),
                             norm((REPO / "configs" / "as_run" / asr / "sfincs_build.yml").read_text()), ex)


def _env():
    env = dict((_load_machine_override().get("env") or {}))
    return env if all(env.get(k) and Path(env[k]).exists() for k in ("hydromt", "sfincs_exe")) else None


def _write_strip_inputs(data: Path, rain_mm_h: float) -> Path:
    """West half land (+1.5 m, sloping to the coast), east half sea (0 m, touches the east edge), an inland
    pit at -0.5 m, WorldCover 30 (grass) on land / 80 on sea, ERA5-like p = 98825 Pa, rain on the whole box."""
    import pandas as pd
    import rasterio
    import xarray as xr
    from rasterio.transform import from_origin
    data.mkdir(parents=True, exist_ok=True)
    w, s, e, n = BBOX
    res = 0.0005; ny, nx = int(round((n - s + 0.02) / res)), int(round((e - w + 0.02) / res))
    tr = from_origin(w - 0.01, n + 0.01, res, res)
    lon = w - 0.01 + res * (np.arange(nx) + 0.5)
    coast = w + 0.05                                      # x = 5 km
    dep = np.where(lon[None, :] < coast, 1.5 - 1.0 * (lon[None, :] - w) / 0.05, 0.0).astype("float32")
    dep = np.repeat(dep, ny, axis=0) if dep.shape[0] == 1 else dep
    pit_c = np.argmin(np.abs(lon - (w + 0.02))); pit_r = ny // 2
    dep[pit_r - 2:pit_r + 3, pit_c - 2:pit_c + 3] = -0.5             # ~250 x 250 m pit, 2 km inland
    lulc = np.where(lon[None, :] < coast, 30, 80).astype("uint8"); lulc = np.repeat(lulc, ny, axis=0)
    for name, arr, nod in (("dep.tif", dep, -9999.0), ("landuse.tif", lulc, 0)):
        with rasterio.open(data / name, "w", driver="GTiff", height=ny, width=nx, count=1, dtype=arr.dtype,
                           crs="EPSG:4326", transform=tr, nodata=nod) as dst:
            dst.write(arr, 1)
    time = pd.date_range("2016-12-31 00:00", "2017-01-03 00:00", freq="1h")
    lat = np.arange(n + 0.5, s - 0.5, -0.25); lonc = np.arange(w - 0.5, e + 0.5, 0.25)
    shape = (time.size, lat.size, lonc.size)
    precip = np.zeros(shape, "float32"); precip[(time >= "2017-01-01 06:00") & (time <= "2017-01-01 12:00")] = rain_mm_h
    ds = xr.Dataset({"precip": (("time", "latitude", "longitude"), precip, {"units": "mm/h"}),
                     "wind10_u": (("time", "latitude", "longitude"), np.zeros(shape, "float32")),
                     "wind10_v": (("time", "latitude", "longitude"), np.zeros(shape, "float32")),
                     "press_msl": (("time", "latitude", "longitude"), np.full(shape, P_SYNTH, "float32"), {"units": "Pa"})},
                    coords={"time": time, "latitude": lat, "longitude": lonc})
    ds.to_netcdf(data / "era5_synth.nc")
    cat = data / "data_catalog.yml"
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


class CoastalStripIntegration(unittest.TestCase):
    """Real pipeline path: prepare_coastal_exclusion -> render_build_yml -> hydromt build -> inject bnd -> SFINCS."""

    @classmethod
    def setUpClass(cls):
        cls.env = _env()
        if cls.env is None:
            raise unittest.SkipTest("hydromt.exe / sfincs.exe not available")
        cls.work = Path(tempfile.mkdtemp(prefix="strip_v14_"))
        cls.catalog = _write_strip_inputs(cls.work / "data", rain_mm_h=10.0)
        cls.cfg = _cfg("v1.4", cls.work)
        cls.prep = build_model.prepare_coastal_exclusion(cls.cfg, cls.work, cls.catalog)
        yml = cls.work / "sfincs_build.yml"
        yml.write_text(build_model.render_build_yml(cls.cfg, exclude_mask=cls.prep["exclude_mask"]), encoding="utf-8")
        cls.model = cls.work / "model"; cls.model.mkdir()
        res = subprocess.run([cls.env["hydromt"], "build", "sfincs", str(cls.model), "-i", str(yml), "-d", str(cls.catalog), "--fo"],
                             capture_output=True, text=True)
        (cls.work / "hydromt.log").write_text(res.stdout + res.stderr, encoding="utf-8")
        if res.returncode != 0:
            raise RuntimeError(res.stdout[-2000:] + res.stderr[-2000:])
        cls.n_bnd = build_model.inject_waterlevel_bnd(cls.cfg, cls.model)
        run = subprocess.run([cls.env["sfincs_exe"]], cwd=str(cls.model), capture_output=True, text=True)
        (cls.work / "sfincs.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        import xarray as xr
        cls.ds = xr.open_dataset(cls.model / "sfincs_map.nc")
        cls.msk = cls.ds["msk"].values; cls.zb = cls.ds["zb"].values

    @classmethod
    def tearDownClass(cls):
        if not os.environ.get("KEEP_IB_TEST_DIR"):
            shutil.rmtree(cls.work, ignore_errors=True)

    def test_open_sea_is_inactive_except_the_coastal_ring(self):
        self.assertGreater(self.prep["n_open_sea"], 0)
        self.assertEqual(self.prep["n_exclude"], self.prep["n_open_sea"] - self.prep["n_ring"])
        x = self.ds["x"].values
        sea_cols = x > x.min() + 5100                                   # east of the coast (plus one cell margin)
        self.assertTrue((self.msk[sea_cols] == 0).all(), "open-sea cells still active")
        self.assertEqual(int((self.msk == 2).sum()), self.prep["n_ring"])
        self.assertTrue((self.zb[self.msk == 2] <= 0).all())

    def test_inland_pit_stays_active_and_starts_dry(self):
        pit = (self.msk == 1) & (self.zb < -0.3)
        self.assertGreater(int(pit.sum()), 0, "inland pit not active")
        zs0 = self.ds["zs"].isel(time=0).values
        h0 = np.where(np.isfinite(zs0), zs0 - self.zb, 0.0)
        self.assertLess(float(np.nanmax(h0[pit])), 0.001, "pit starts wet")
        import re
        self.assertRegex((self.model / "sfincs.inp").read_text(), r"zsini\s*=\s*-9999")

    def test_coastal_boundary_rises_by_the_inverse_barometer(self):
        self.assertGreaterEqual(self.n_bnd, 1)
        zs_last = self.ds["zs"].isel(time=-1).values
        b = zs_last[self.msk == 2]; b = b[np.isfinite(b)]
        self.assertGreater(b.size, 0)
        self.assertAlmostEqual(float(np.nanmean(b)), EXPECTED_M, delta=0.01)

    def test_rain_wets_the_land(self):
        zsmax = self.ds["zsmax"].max(dim="timemax").values
        hmax = np.where(np.isfinite(zsmax), zsmax - self.zb, 0.0)
        land = (self.msk == 1) & (self.zb > 0)
        self.assertGreater(float(np.nanmax(hmax[land])), 0.02)


if __name__ == "__main__":
    unittest.main()
