"""Phase 3 (GO Phases 3-5, 2026-10-19): the Pineios time-varying-Q audit row (MANIFEST row 14 / inventory 5a) rebuilds
sfincs.dis from the GloFAS series at the injection points and re-snaps sfincs.src to the lowest-zb cell nearby.
The helpers must be insensitive to the latitude order of the GloFAS file (the Pineios file is ascending, which is what
sends the pipeline's own sampler into its domain-mean fallback)."""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import rebuild_pineios_q as rq  # noqa: E402


class NearestSeries(unittest.TestCase):
    def _da(self, ascending: bool):
        import xarray as xr
        lat = np.array([39.0, 39.1, 39.2]); lon = np.array([22.0, 22.1])
        vals = np.arange(2 * 3 * 2, dtype=float).reshape(2, 3, 2)
        da = xr.DataArray(vals, dims=("time", "latitude", "longitude"),
                          coords={"time": np.array(["2023-09-01", "2023-09-02"], dtype="datetime64[ns]"), "latitude": lat, "longitude": lon})
        return da if ascending else da.isel(latitude=slice(None, None, -1))

    def test_latitude_order_does_not_change_the_sampled_cell(self):
        s_asc, c_asc = rq.nearest_series(self._da(True), lon=22.06, lat=39.17)
        s_desc, c_desc = rq.nearest_series(self._da(False), lon=22.06, lat=39.17)
        np.testing.assert_array_equal(s_asc, s_desc)
        self.assertEqual(c_asc, c_desc)
        self.assertEqual(c_asc, (22.1, 39.2))
        np.testing.assert_array_equal(s_asc, self._da(True).values[:, 2, 1])


class HourlyLinear(unittest.TestCase):
    def test_daily_values_are_interpolated_linearly_to_hours(self):
        t0 = dt.datetime(2023, 8, 27)
        times = np.array([t0, t0 + dt.timedelta(days=1), t0 + dt.timedelta(days=2)], dtype="datetime64[ns]")
        hours, vals = rq.hourly_linear(times, np.array([0.0, 24.0, 0.0]), tref=t0, tstop=t0 + dt.timedelta(days=2))
        self.assertEqual(len(hours), 49)
        self.assertAlmostEqual(vals[12], 12.0)
        self.assertAlmostEqual(vals[24], 24.0)
        self.assertAlmostEqual(vals[36], 12.0)

    def test_hours_outside_the_series_hold_the_end_values(self):
        t0 = dt.datetime(2023, 8, 27)
        times = np.array([t0 + dt.timedelta(days=1), t0 + dt.timedelta(days=2)], dtype="datetime64[ns]")
        hours, vals = rq.hourly_linear(times, np.array([5.0, 7.0]), tref=t0, tstop=t0 + dt.timedelta(days=3))
        self.assertAlmostEqual(vals[0], 5.0)
        self.assertAlmostEqual(vals[-1], 7.0)


class SnapToLowestZb(unittest.TestCase):
    def setUp(self):
        from rasterio.transform import from_origin
        self.dep = np.full((7, 7), 10.0)
        self.dep[5, 1] = 2.0          # lowest inside +-2 cells of the centre cell (3, 3), outside +-1
        self.dep[0, 6] = 1.0          # lower still, but outside +-2
        self.tr = from_origin(0.0, 700.0, 100.0, 100.0)   # 100-m cells, rows top-down; (350, 350) lies in cell (3, 3)

    def test_picks_the_lowest_cell_inside_the_window(self):
        x, y, zb, rc = rq.snap_to_lowest_zb(350.0, 350.0, self.dep, self.tr, ncells=2)
        self.assertEqual(rc, (5, 1))
        self.assertAlmostEqual(x, 150.0); self.assertAlmostEqual(y, 150.0); self.assertAlmostEqual(zb, 2.0)

    def test_window_bounds_the_search(self):
        x, y, zb, rc = rq.snap_to_lowest_zb(350.0, 350.0, self.dep, self.tr, ncells=1)
        self.assertEqual(rc, (3, 3))        # nothing lower than the centre within +-1 cell
        self.assertAlmostEqual(zb, 10.0)

    def test_nodata_is_ignored(self):
        self.dep[3, 3] = np.nan
        x, y, zb, rc = rq.snap_to_lowest_zb(350.0, 350.0, self.dep, self.tr, ncells=2)
        self.assertEqual(rc, (5, 1))


class WriteDis(unittest.TestCase):
    def test_seconds_since_tref_and_two_decimals(self):
        import pandas as pd
        t0 = dt.datetime(2023, 8, 27)
        hours = pd.date_range(t0, periods=3, freq="h")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sfincs.dis"
            rq.write_dis(p, t0, hours, [np.array([1.0, 2.0, 3.0]), np.array([0.123, 0.456, 0.789])])
            lines = p.read_text().splitlines()
        self.assertEqual(lines[0], "0  1.00  0.12")
        self.assertEqual(lines[2], "7200  3.00  0.79")


if __name__ == "__main__":
    unittest.main()
