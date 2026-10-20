"""Harness v1.4.2 (CODE-15 B, 2026-10-20) — D8 (3): the R3 snap. Under harness v1.4 a discharge source is injected at the
lowest-z_b ACTIVE CHANNEL cell within 1 km of the YAML injection point (channel = D8 upstream area at least half of the
largest within the radius, so a pit beside the river does not win), never at the raw coordinate; no active cell within
1 km is a hard error. v1.3 keeps the raw coordinate (published behaviour).

Run:  python -m unittest tests.test_source_snap -v   (repo root, sfincs-viz env)
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

import source_snap as ss  # noqa: E402

V14 = Path("D:/ELKAK/implementation/v14")


def synthetic_grid(res=100.0, n=30):
    """n x n grid, EPSG-like projected coordinates with origin (500000, 4400000) at the top-left. A plane sloping down to the
    east (0.5 m per cell) with a channel along row 15 three metres below the plane, an off-channel pit at (10, 10) that is
    the lowest cell of all, and a block of inactive cells over the channel's eastern (lowest) part."""
    from rasterio.transform import from_origin
    T = from_origin(500000.0, 4400000.0, res, res)
    rows, cols = np.indices((n, n))
    dep = 50.0 - 0.5 * cols.astype(float)
    dep[15, :] -= 3.0                       # the channel
    dep[10, 10] = 10.0                      # a pit, lower than any channel cell, off-channel
    uparea = np.ones((n, n))
    uparea[15, :] = 100.0 * (cols[15, :] + 1)   # the channel accumulates eastward
    msk = np.ones((n, n))
    msk[12:19, 22:] = np.nan                # inactive block over the channel's lowest cells (east of column 21)
    return dep, msk, uparea, T, res


class SnapSource(unittest.TestCase):
    def test_lowest_active_channel_cell_within_1km_not_the_pit(self):
        dep, msk, uparea, T, res = synthetic_grid()
        # point at the centre of cell (15, 15): channel cells within 1 km = columns 5..25 of row 15 (plus nothing else on the channel);
        # the active ones end at column 21 -> the lowest active channel cell is (15, 21)
        x = 500000.0 + 15.5 * res; y = 4400000.0 - 15.5 * res
        r = ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)
        self.assertEqual((r["row"], r["col"]), (15, 21))
        self.assertAlmostEqual(r["x"], 500000.0 + 21.5 * res); self.assertAlmostEqual(r["y"], 4400000.0 - 15.5 * res)
        self.assertAlmostEqual(r["zb"], 50.0 - 0.5 * 21 - 3.0)
        self.assertLessEqual(r["distance_m"], 1000.0)
        self.assertGreater(r["uparea_km2"], 0)

    def test_the_pit_is_rejected_because_it_is_off_channel(self):
        dep, msk, uparea, T, res = synthetic_grid()
        x = 500000.0 + 10.5 * res; y = 4400000.0 - 12.5 * res       # 200 m from the pit, 300 m from the channel
        r = ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)
        self.assertEqual(r["row"], 15)                              # a channel cell, not (10, 10)
        self.assertGreater(r["zb"], 10.0)

    def test_cells_beyond_the_radius_are_not_candidates(self):
        dep, msk, uparea, T, res = synthetic_grid()
        x = 500000.0 + 5.5 * res; y = 4400000.0 - 15.5 * res        # column 5: within 1 km = columns 0..15 (cells > 1000 m excluded)
        r = ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)
        self.assertEqual((r["row"], r["col"]), (15, 15))

    def test_no_active_cell_within_1km_is_a_hard_error(self):
        dep, msk, uparea, T, res = synthetic_grid()
        msk[:, :] = np.nan
        x = 500000.0 + 15.5 * res; y = 4400000.0 - 15.5 * res
        with self.assertRaises(ss.NoActiveCellError):
            ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)

    def test_boundary_cells_msk_2_are_not_injection_cells(self):
        dep, msk, uparea, T, res = synthetic_grid()
        msk[15, 21] = 2.0                                            # the would-be winner becomes a water-level boundary cell
        x = 500000.0 + 15.5 * res; y = 4400000.0 - 15.5 * res
        r = ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)
        self.assertEqual((r["row"], r["col"]), (15, 20))


class InjectQForcingSnap(unittest.TestCase):
    """build_model.inject_q_forcing: v1.4 writes the snapped cell centres to sfincs.src (+ a JSON report), v1.3 the raw points."""

    def _model(self, td: Path, harness: str):
        import pandas as pd
        import rasterio
        import yaml
        from _common import load_config
        dep, msk, uparea, T, res = synthetic_grid()
        model = td / "model"; (model / "gis").mkdir(parents=True); data = td / "data"; data.mkdir()
        for name, arr in (("dep.tif", dep.astype("float32")), ("msk.tif", msk)):
            with rasterio.open(model / "gis" / name, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype=arr.dtype, crs="EPSG:32634", transform=T, nodata=np.nan) as dst:
                dst.write(arr, 1)
        (model / "sfincs.inp").write_text("mmax = 30\nnmax = 30\n")
        import pyproj
        to_ll = pyproj.Transformer.from_crs(32634, 4326, always_xy=True)
        lon, lat = to_ll.transform(500000.0 + 15.5 * res, 4400000.0 - 15.5 * res)
        hours = pd.date_range("2017-01-01", periods=3, freq="h")
        pd.DataFrame({"1": [1.0, 2.0, 3.0], "2": [5.0, 5.0, 5.0]}, index=hours).to_csv(data / "q_outlet.csv", index_label="time")
        raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-02"},
               "window": {"spinup_days": 1, "pre_event_days": 1, "post_event_days": 0},
               "bbox": {"west": 23.0, "south": 35.0, "east": 23.1, "north": 35.09}, "crs": {"epsg": 32634}, "grid": {"res": 100, "zmax": 250},
               "paths": {"work_dir": str(td).replace("\\", "/"), "deliverable_dir": str(td / "deliverable").replace("\\", "/"), "manning_lookup": str(td / "manning.csv").replace("\\", "/")},
               "harness_version": harness,
               "upstream_q": {"enabled": True, "src_points": [{"name": "river", "lon": lon, "lat": lat}, {"name": "sampled_only", "lon": lon, "lat": lat, "inject": False}]}}
        cfgp = td / "cfg.yaml"; cfgp.write_text(yaml.safe_dump(raw), encoding="utf-8")
        cfg = load_config(["--config", str(cfgp)])
        return cfg, model, (lon, lat), res

    def test_v14_writes_the_snapped_channel_cell_and_skips_inject_false_points(self):
        import build_model
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg, model, (lon, lat), res = self._model(td, "v1.4")
            build_model.inject_q_forcing(cfg, model)
            src = np.loadtxt(model / "sfincs.src"); src = src[None, :] if src.ndim == 1 else src
            self.assertEqual(src.shape[0], 1)                                           # the inject: false point is not a source
            self.assertAlmostEqual(src[0, 0], 500000.0 + 21.5 * res, places=1); self.assertAlmostEqual(src[0, 1], 4400000.0 - 15.5 * res, places=1)
            dis = np.loadtxt(model / "sfincs.dis")
            self.assertEqual(dis.shape, (3, 2))                                          # time + one column
            np.testing.assert_allclose(dis[:, 1], [1.0, 2.0, 3.0])
            rep = json.loads((model / "sfincs_src_snap.json").read_text(encoding="utf-8"))
            self.assertEqual(rep["harness_version"], "v1.4")
            self.assertEqual(rep["points"][0]["row_col"], [15, 21])
            self.assertFalse(rep["points"][1]["injected"])

    def test_v13_writes_the_raw_coordinates(self):
        import build_model
        import pyproj
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg, model, (lon, lat), res = self._model(td, "v1.3")
            build_model.inject_q_forcing(cfg, model)
            src = np.loadtxt(model / "sfincs.src")
            x, y = pyproj.Transformer.from_crs(4326, 32634, always_xy=True).transform(lon, lat)
            self.assertEqual(src.shape[0], 2)                                            # v1.3: every point, raw coordinates
            self.assertAlmostEqual(src[0, 0], x, places=1); self.assertAlmostEqual(src[0, 1], y, places=1)
            self.assertFalse((model / "sfincs_src_snap.json").exists())

    def test_v14_hard_error_when_no_active_cell_within_1km(self):
        import build_model
        import rasterio
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg, model, _, _ = self._model(td, "v1.4")
            with rasterio.open(model / "gis" / "msk.tif", "r+") as m:
                m.write(np.full((30, 30), np.nan), 1)
            with self.assertRaises(ss.NoActiveCellError):
                build_model.inject_q_forcing(cfg, model)


@unittest.skipUnless((V14 / "valencia_enhanced_164" / "model" / "gis" / "dep.tif").exists(), "Valencia v1.4 model not on this machine")
class ValenciaMagroRealData(unittest.TestCase):
    """The resolved Magro injection point (CODE-15 ledger) lands on an active channel cell of the Valencia v1.4 model."""

    def test_magro_snaps_to_an_active_channel_cell(self):
        import pyproj
        import rasterio
        g = V14 / "valencia_enhanced_164" / "model" / "gis"
        with rasterio.open(g / "dep.tif") as s:
            dep = s.read(1).astype(float); T = s.transform
        with rasterio.open(g / "msk.tif") as s:
            msk = s.read(1).astype(float)
        uparea = ss.dem_uparea_on_grid(V14 / "valencia_enhanced_164" / "data" / "copdem30", 32630, T, dep.shape)
        x, y = pyproj.Transformer.from_crs(4326, 32630, always_xy=True).transform(-0.68, 39.20)
        r = ss.snap_source(dep, msk, uparea, T, x, y, radius_m=1000.0)
        self.assertEqual(msk[r["row"], r["col"]], 1.0)
        self.assertTrue(np.isfinite(dep[r["row"], r["col"]]))
        self.assertGreaterEqual(r["uparea_km2"], 0.5 * r["max_uparea_within_radius_km2"])
        self.assertLessEqual(r["distance_m"], 1000.0)


if __name__ == "__main__":
    unittest.main()
