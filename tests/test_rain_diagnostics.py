"""Phase 4c (GO Phases 3-5): rainfall diagnostics re-derived from the v1.4 forcing files and the raw products —
domain-mean totals, peak domain-mean and peak cell intensities over a window, bbox subsetting independent of the
latitude order. Pure-function tests on synthetic fields."""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import rain_diagnostics as rd  # noqa: E402


def _field(dt_h: float, n: int, lat_desc: bool = False):
    import xarray as xr
    t0 = np.datetime64("2017-11-14T00:00:00")
    time = t0 + (np.arange(n) * dt_h * 60).astype("timedelta64[m]")
    lat = np.array([38.0, 38.1, 38.2]); lon = np.array([23.3, 23.4, 23.5, 23.6])
    rate = np.zeros((n, 3, 4))
    rate[:, :, :] = 2.0                 # 2 mm/h everywhere
    if n > 5:
        rate[5, 1, 2] = 50.0            # one cell peak at step 5
    da = xr.DataArray(rate, dims=("time", "latitude", "longitude"), coords={"time": time, "latitude": lat, "longitude": lon}, attrs={"units": "mm/h"})
    return da.isel(latitude=slice(None, None, -1)) if lat_desc else da


class Totals(unittest.TestCase):
    def test_domain_mean_total_integrates_rate_times_dt(self):
        da = _field(0.5, 48)                       # 24 h of 2 mm/h at half-hourly steps -> 48 mm (+ the one-cell spike share)
        tot = rd.domain_mean_total_mm(da, dt.datetime(2017, 11, 14), dt.datetime(2017, 11, 15))
        spike = (50.0 - 2.0) * 0.5 / 12            # one of 12 cells, one half-hour step
        self.assertAlmostEqual(tot, 48.0 + spike, places=6)

    def test_window_bounds_are_half_open(self):
        da = _field(1.0, 24)
        tot = rd.domain_mean_total_mm(da, dt.datetime(2017, 11, 14, 0), dt.datetime(2017, 11, 14, 6))
        self.assertAlmostEqual(tot, 6 * 2.0 + (50.0 - 2.0) / 12, places=6)   # steps 0..5 (step 5 holds the spike)

    def test_cell_total_max(self):
        da = _field(1.0, 24)
        self.assertAlmostEqual(rd.max_cell_total_mm(da, dt.datetime(2017, 11, 14), dt.datetime(2017, 11, 15)), 23 * 2.0 + 50.0)


class Peaks(unittest.TestCase):
    def test_domain_mean_and_cell_peak(self):
        da = _field(0.5, 48)
        pk = rd.peak_intensity(da, dt.datetime(2017, 11, 14), dt.datetime(2017, 11, 15))
        self.assertAlmostEqual(pk["cell_peak_mm_h"], 50.0)
        self.assertAlmostEqual(pk["domain_mean_peak_mm_h"], 2.0 + 48.0 / 12)
        self.assertEqual(pk["domain_mean_peak_time"][:16], "2017-11-14T02:30")


class Subset(unittest.TestCase):
    def test_bbox_subset_is_independent_of_latitude_order(self):
        a = rd.subset_bbox(_field(1.0, 2), 23.35, 38.05, 23.55, 38.25)
        b = rd.subset_bbox(_field(1.0, 2, lat_desc=True), 23.35, 38.05, 23.55, 38.25)
        self.assertEqual(a.sizes, {"time": 2, "latitude": 2, "longitude": 2})
        np.testing.assert_allclose(np.sort(a.latitude.values), np.sort(b.latitude.values))
        self.assertAlmostEqual(float(a.sum()), float(b.sum()))


if __name__ == "__main__":
    unittest.main()
