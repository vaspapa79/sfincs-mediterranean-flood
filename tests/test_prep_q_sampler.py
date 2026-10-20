"""Harness v1.4.1 (CODE-14 B, 2026-10-20) — D7: the GloFAS point sampler of skill/scripts/prep_q_at_outlets.py.

The sampler's cell rule (max-mean-discharge cell of the +-0.1 deg window around each named point, hourly step-fill) is kept
— it is what every correctly-sampled run (Strymonas, Valencia, Emilia) carries — but it must not depend on the latitude
order of the GloFAS file (the Pineios file is ascending, which emptied the window and sent the script into a domain-mean
constant), and the fallback is a hard error. The Pineios real-data checks pin the cells the fixed rule selects.
"""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import prep_q_at_outlets as pq  # noqa: E402

PINEIOS_DATA = Path("D:/ELKAK/implementation/pineios_sfincs_enhanced/data")


def synthetic_da(ascending: bool):
    """Two rivers on a 5 x 5 grid at 0.05 deg: river A through (lon 22.075, lat 39.125) with a 3-day peak, river B through
    (lon 22.175, lat 39.225); all other cells carry a small hillslope discharge."""
    import xarray as xr
    lat = 39.025 + 0.05 * np.arange(5)
    lon = 22.025 + 0.05 * np.arange(5)
    times = np.array(["2023-09-01", "2023-09-02", "2023-09-03"], dtype="datetime64[ns]")
    vals = np.full((3, 5, 5), 0.5)
    vals[:, 2, 1] = [10.0, 100.0, 20.0]      # river A: lat 39.125 (index 2), lon 22.075 (index 1)
    vals[:, 4, 3] = [5.0, 40.0, 60.0]        # river B: lat 39.225 (index 4), lon 22.175 (index 3)
    da = xr.DataArray(vals, dims=("time", "latitude", "longitude"), coords={"time": times, "latitude": lat, "longitude": lon}, name="discharge")
    return da if ascending else da.isel(latitude=slice(None, None, -1))


class WindowCellSelection(unittest.TestCase):
    def test_same_cell_and_series_for_both_latitude_orders(self):
        for asc in (True, False):
            with self.subTest(ascending=asc):
                ser, cell, n = pq.select_window_cell(synthetic_da(asc), lon=22.06, lat=39.14)
                self.assertEqual(cell, (22.075, 39.125))
                np.testing.assert_array_equal(ser, [10.0, 100.0, 20.0])
                self.assertEqual(n, 12)                      # +-0.1 deg around (22.06, 39.14): lats 39.075..39.225 (4) x lons 22.025..22.125 (3)

    def test_the_literal_descending_slice_matches_the_order_agnostic_window(self):
        """On a descending file the fixed rule must select exactly what the v1.3/v1.4.0 sampler selected."""
        da = synthetic_da(False)
        sub = da.sel(latitude=slice(39.14 + 0.1, 39.14 - 0.1), longitude=slice(22.06 - 0.1, 22.06 + 0.1))
        qmat = sub.mean("time").values
        i, j = np.unravel_index(int(np.argmax(qmat)), qmat.shape)
        legacy = (round(float(sub.longitude[j]), 3), round(float(sub.latitude[i]), 3))
        _, cell, n = pq.select_window_cell(da, lon=22.06, lat=39.14)
        self.assertEqual(cell, legacy)
        self.assertEqual(n, qmat.size)

    def test_a_cell_centre_exactly_on_the_window_edge_is_inside_even_with_float32_coordinates(self):
        """GloFAS files carry float32 coordinates: 39.81f = 39.81000137, which a float64 bound of 39.71 + 0.1 would exclude.
        The window is inclusive up to a 1e-4 deg (~10 m) tolerance, so a centre on the edge belongs to the window on both axes."""
        import xarray as xr
        lat = np.array([39.61, 39.71, 39.81], dtype=np.float32); lon = np.array([22.34, 22.44], dtype=np.float32)
        vals = np.full((2, 3, 2), 1.0); vals[:, 2, 1] = 500.0                     # the big cell sits at (lon 22.44, lat 39.81)
        da = xr.DataArray(vals, dims=("time", "latitude", "longitude"),
                          coords={"time": np.array(["2023-09-01", "2023-09-02"], dtype="datetime64[ns]"), "latitude": lat, "longitude": lon})
        ser, cell, n = pq.select_window_cell(da, lon=22.42, lat=39.71)
        self.assertEqual(n, 6)
        self.assertEqual(cell, (22.44, 39.81))

    def test_empty_window_is_a_hard_error(self):
        with self.assertRaises(pq.NoChannelError):
            pq.select_window_cell(synthetic_da(True), lon=30.0, lat=50.0)

    def test_window_without_positive_discharge_is_a_hard_error(self):
        da = synthetic_da(True).copy()
        da[:] = 0.0
        with self.assertRaises(pq.NoChannelError):
            pq.select_window_cell(da, lon=22.06, lat=39.14)


class SamplePoints(unittest.TestCase):
    def test_two_points_write_their_own_cell_series_hourly_step_filled(self):
        pts = [{"name": "river_a", "lon": 22.06, "lat": 39.14}, {"name": "river_b", "lon": 22.18, "lat": 39.21}]
        for asc in (True, False):
            with self.subTest(ascending=asc):
                df, rep = pq.sample_points(synthetic_da(asc), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 3))
                self.assertEqual(list(df.columns), ["1", "2"])
                self.assertEqual(len(df), 49)
                # nearest GloFAS step in time: day 1 until 12:00, day 2 until 36 h, day 3 after
                np.testing.assert_array_equal(df["1"].values[:12], 10.0)
                np.testing.assert_array_equal(df["1"].values[13:36], 100.0)
                np.testing.assert_array_equal(df["1"].values[37:], 20.0)
                self.assertEqual(float(df["2"].max()), 60.0)
                self.assertEqual(rep["points"][0]["cell_lonlat"], [22.075, 39.125])
                self.assertEqual(rep["points"][1]["cell_lonlat"], [22.175, 39.225])
                self.assertEqual(rep["duplicate_cells"], [])

    def test_a_point_may_carry_its_own_window_half_width(self):
        """`window_deg` per point (default WINDOW_HALF_DEG): a one-cell window keeps a tributary point off a neighbouring main stem."""
        pts = [{"name": "near_b_default", "lon": 22.13, "lat": 39.18},                    # +-0.1: reaches river A (mean 43) and river B (35) -> A
               {"name": "near_b_narrow", "lon": 22.13, "lat": 39.18, "window_deg": 0.05}]  # +-0.05: lats 39.175/39.225 x lons 22.125/22.175 -> B only
        df, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))
        self.assertEqual(rep["points"][0]["cell_lonlat"], [22.075, 39.125])
        self.assertEqual(rep["points"][1]["cell_lonlat"], [22.175, 39.225])
        self.assertEqual(rep["points"][1]["window_half_deg"], 0.05)
        self.assertEqual(float(df["2"].max()), 40.0)

    def test_two_points_resolving_to_one_cell_are_reported(self):
        pts = [{"name": "p1", "lon": 22.06, "lat": 39.14}, {"name": "p2", "lon": 22.10, "lat": 39.10}]
        _, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))
        self.assertEqual(rep["duplicate_cells"], [{"cell_lonlat": [22.075, 39.125], "points": ["p1", "p2"]}])

    def test_a_point_without_channel_aborts_the_whole_sampling(self):
        pts = [{"name": "ok", "lon": 22.06, "lat": 39.14}, {"name": "nowhere", "lon": 30.0, "lat": 50.0}]
        with self.assertRaises(pq.NoChannelError):
            pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))


class WriteOutputs(unittest.TestCase):
    def test_csv_and_cell_report_are_written(self):
        import pandas as pd
        pts = [{"name": "river_a", "lon": 22.06, "lat": 39.14}]
        df, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))
        with tempfile.TemporaryDirectory() as td:
            csv, js = pq.write_outputs(Path(td), df, rep)
            back = pd.read_csv(csv, index_col=0, parse_dates=True)
            np.testing.assert_array_equal(back["1"].values, df["1"].values)
            self.assertTrue(js.exists())
            self.assertIn("river_a", js.read_text(encoding="utf-8"))


@unittest.skipUnless((PINEIOS_DATA / "glofas_pineios_clean.nc").exists(), "Pineios GloFAS file not on this machine")
class PineiosRealData(unittest.TestCase):
    """The frozen Pineios config under the fixed rule (0.1 deg GloFAS file, ascending latitude)."""

    @classmethod
    def setUpClass(cls):
        import xarray as xr
        cls.da = xr.open_dataset(PINEIOS_DATA / "glofas_pineios_clean.nc")["discharge"]
        cls.pts = [{"name": "pineios_trikala", "lon": 21.77, "lat": 39.56, "src_lon": 21.86, "src_lat": 39.56},
                   {"name": "pineios_kalambaka", "lon": 21.63, "lat": 39.70, "src_lon": 21.86, "src_lat": 39.70},
                   {"name": "titarisios", "lon": 22.42, "lat": 39.71},
                   {"name": "enipeas", "lon": 22.39, "lat": 39.30, "src_lon": 22.39, "src_lat": 39.33}]

    def test_latitude_axis_is_ascending_and_the_legacy_slice_is_empty(self):
        lat = self.da.latitude.values
        self.assertGreater(lat[-1], lat[0])
        self.assertEqual(self.da.sel(latitude=slice(39.56 + 0.1, 39.56 - 0.1)).sizes["latitude"], 0)

    def test_enipeas_peak_is_118_4_and_the_trikala_window_reaches_the_main_stem(self):
        df, rep = pq.sample_points(self.da, self.pts, tref=dt.datetime(2023, 8, 27), tstop=dt.datetime(2023, 9, 11))
        by = {p["name"]: p for p in rep["points"]}
        self.assertEqual(by["enipeas"]["cell_lonlat"], [22.34, 39.31])
        self.assertAlmostEqual(float(df["4"].max()), 118.40, places=2)
        self.assertEqual(by["pineios_trikala"]["cell_lonlat"], [21.84, 39.51])
        self.assertAlmostEqual(float(df["1"].max()), 371.39, places=2)
        self.assertEqual(by["titarisios"]["cell_lonlat"], [22.44, 39.81])          # D8: the Pineios main stem one cell north
        self.assertFalse(np.allclose(df.values, df.values[0, 0]))                  # never a constant


@unittest.skipUnless((PINEIOS_DATA / "glofas_pineios_clean.nc").exists(), "Pineios GloFAS file not on this machine")
class PineiosAuditRebuildRegression(unittest.TestCase):
    """The audit rebuild (nearest cell at the injection point, hourly linear) — the numbers of MANIFEST row 14 / S2."""

    def test_enipeas_118_4_and_combined_135_0(self):
        import xarray as xr
        import rebuild_pineios_q as rq
        da = xr.open_dataset(PINEIOS_DATA / "glofas_pineios_clean.nc")["discharge"]
        pts = [(21.86, 39.56), (21.86, 39.70), (22.42, 39.71), (22.39, 39.33)]
        cols = []
        for lon, lat in pts:
            ser, _ = rq.nearest_series(da, lon, lat)
            _, hourly = rq.hourly_linear(da.time.values, np.nan_to_num(ser), dt.datetime(2023, 8, 27), dt.datetime(2023, 9, 11))
            cols.append(hourly)
        self.assertAlmostEqual(float(cols[3].max()), 118.40, places=2)
        self.assertAlmostEqual(float(np.sum(cols, axis=0).max()), 135.0, places=1)




# ------------------------------------------------------------------------------------------ harness v1.4.2 (CODE-15 B, 2026-10-20)
V14 = Path("D:/ELKAK/implementation/v14")
PINEIOS_EXT = V14 / "_seed" / "pineios" / "data" / "glofas_pineios.nc"        # the lattice re-downloaded with the extended request area (D8 (2))


class StrictDuplicates(unittest.TestCase):
    """D8 (4): under harness v1.4 two points resolving to one GloFAS cell abort the sampling; v1.3 keeps the warning."""

    def test_strict_mode_raises_on_a_shared_cell(self):
        pts = [{"name": "p1", "lon": 22.06, "lat": 39.14}, {"name": "p2", "lon": 22.10, "lat": 39.10}]
        with self.assertRaises(pq.DuplicateCellError):
            pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2), strict_duplicates=True)

    def test_default_mode_still_reports_the_duplicate(self):
        pts = [{"name": "p1", "lon": 22.06, "lat": 39.14}, {"name": "p2", "lon": 22.10, "lat": 39.10}]
        _, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))
        self.assertEqual(len(rep["duplicate_cells"]), 1)

    def test_per_point_windows_make_two_points_distinct(self):
        """Two points whose default windows both reach river A: a one-cell window keeps the second on river B (its own river)."""
        pts = [{"name": "a", "lon": 22.06, "lat": 39.14}, {"name": "b", "lon": 22.13, "lat": 39.18, "window_deg": 0.05}]
        df, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2), strict_duplicates=True)
        self.assertEqual(rep["points"][0]["cell_lonlat"], [22.075, 39.125])
        self.assertEqual(rep["points"][1]["cell_lonlat"], [22.175, 39.225])

    def test_inject_flag_is_carried_in_the_report(self):
        pts = [{"name": "sampled_only", "lon": 22.06, "lat": 39.14, "inject": False}, {"name": "b", "lon": 22.18, "lat": 39.21}]
        df, rep = pq.sample_points(synthetic_da(True), pts, tref=dt.datetime(2023, 9, 1), tstop=dt.datetime(2023, 9, 2))
        self.assertEqual([p["inject"] for p in rep["points"]], [False, True])
        self.assertEqual(list(df.columns), ["1", "2"])                 # every point is sampled; injection is decided at build time


@unittest.skipUnless(PINEIOS_EXT.exists(), "extended Pineios GloFAS lattice not on this machine")
class PineiosV142RealData(unittest.TestCase):
    """The v1.4.2 Pineios source points on the extended lattice: Trikala 371.39, Kalambaka > 2.1 (40.78, its window no longer
    clipped), Titarisios 42.85 at its own cell (22.24, 39.71), Enipeas 118.40; every column distinct."""

    def test_peaks_and_cells(self):
        import xarray as xr
        da = pq.open_glofas(PINEIOS_EXT)
        pts = [{"name": "pineios_trikala", "lon": 21.77, "lat": 39.56},
               {"name": "pineios_kalambaka", "lon": 21.63, "lat": 39.70, "inject": False},
               {"name": "titarisios", "lon": 22.24, "lat": 39.71, "window_deg": 0.05},
               {"name": "enipeas", "lon": 22.39, "lat": 39.30}]
        df, rep = pq.sample_points(da, pts, tref=dt.datetime(2023, 8, 27), tstop=dt.datetime(2023, 9, 11), strict_duplicates=True)
        by = {p["name"]: p for p in rep["points"]}
        self.assertAlmostEqual(float(df["1"].max()), 371.39, places=2)
        self.assertGreater(float(df["2"].max()), 2.1); self.assertAlmostEqual(float(df["2"].max()), 40.78, places=2)
        self.assertEqual(by["pineios_kalambaka"]["cell_lonlat"], [21.54, 39.71])
        self.assertEqual(by["titarisios"]["cell_lonlat"], [22.24, 39.71]); self.assertAlmostEqual(float(df["3"].max()), 42.85, places=2)
        self.assertAlmostEqual(float(df["4"].max()), 118.40, places=2)
        self.assertEqual(rep["duplicate_cells"], [])

    def test_the_extension_kept_every_frozen_cell(self):
        import xarray as xr
        new = pq.open_glofas(PINEIOS_EXT); old = pq.open_glofas(PINEIOS_DATA / "glofas_pineios_clean.nc")
        sub = new.sel(longitude=old.longitude.values, latitude=old.latitude.values, method="nearest")
        np.testing.assert_allclose(np.nan_to_num(sub.values), np.nan_to_num(old.values), rtol=0, atol=1e-6)
        self.assertLess(float(new.longitude.min()), float(old.longitude.min()))


@unittest.skipUnless((V14 / "emilia_enhanced_8aoi" / "data" / "glofas_emilia_romagna_clean.nc").exists(), "Emilia GloFAS file not on this machine")
class EmiliaV142RealData(unittest.TestCase):
    """Senio and Montone resolve to distinct cells of their own rivers (Senio: its last cell before the Reno system, Montone: a one-cell window)."""

    def test_senio_and_montone_are_distinct(self):
        da = pq.open_glofas(V14 / "emilia_enhanced_8aoi" / "data" / "glofas_emilia_romagna_clean.nc")
        pts = [{"name": "lamone", "lon": 11.9, "lat": 44.24},
               {"name": "senio", "lon": 11.875, "lat": 44.375, "window_deg": 0.02},
               {"name": "montone", "lon": 11.98, "lat": 44.18, "window_deg": 0.05},
               {"name": "ronco", "lon": 12.03, "lat": 44.13}, {"name": "savio", "lon": 12.1, "lat": 44.06}]
        df, rep = pq.sample_points(da, pts, tref=dt.datetime(2023, 5, 1), tstop=dt.datetime(2023, 5, 20), strict_duplicates=True)
        by = {p["name"]: p for p in rep["points"]}
        self.assertEqual(by["senio"]["cell_lonlat"], [11.875, 44.375])
        self.assertEqual(by["montone"]["cell_lonlat"], [12.025, 44.225])
        self.assertNotEqual(by["senio"]["cell_lonlat"], by["montone"]["cell_lonlat"])
        self.assertEqual(rep["duplicate_cells"], [])


if __name__ == "__main__":
    unittest.main()
