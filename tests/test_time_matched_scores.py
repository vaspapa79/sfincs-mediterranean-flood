"""Phase 4b (GO Phases 3-5): time-matched diagnostic — CSI/HR/FAR/B with hmax accumulated only up to each EMS acquisition
time. Helpers: the running maximum from the hourly zs + the daily zsmax blocks, and the acquisition parser for the EMS
source layers ('Post-event' rows; 'DD/MM/YYYY' + 'THH:MM:SSZ' | 'HH:MM:SS'; legacy date-only polygons)."""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import time_matched_scores as tm  # noqa: E402


def _synthetic():
    """2 x 2 grid, zb = 0; hourly zs for 48 h with a spike of 2.0 m at hour 30 in cell (0, 0); daily zsmax blocks
    (00:00 of day 0, day 1, day 2) where day 1's block also records a sub-hourly peak of 3.0 m in cell (1, 1)."""
    import xarray as xr
    t0 = np.datetime64("2023-09-01T00:00:00")
    time = t0 + np.arange(49) * np.timedelta64(1, "h")
    zs = np.full((49, 2, 2), 0.2)
    zs[30, 0, 0] = 2.0
    timemax = t0 + np.arange(3) * np.timedelta64(1, "D")
    zsmax = np.full((3, 2, 2), 0.2)
    zsmax[2, 0, 0] = 2.0        # the hour-30 spike falls in the block ending at day 2 00:00 (blocks end at timemax[k])
    zsmax[2, 1, 1] = 3.0        # sub-hourly peak inside the same block, invisible in the hourly zs
    ds = xr.Dataset({"zs": (("time", "n", "m"), zs), "zsmax": (("timemax", "n", "m"), zsmax)},
                    coords={"time": time, "timemax": timemax})
    return ds, np.zeros((2, 2))


class RunningHmax(unittest.TestCase):
    def test_before_the_spike_the_running_max_excludes_it(self):
        ds, zb = _synthetic()
        h = tm.running_hmax(ds, zb, dt.datetime(2023, 9, 2, 5, 0))       # hour 29
        self.assertAlmostEqual(float(h[0, 0]), 0.2)

    def test_after_the_spike_the_running_max_includes_it(self):
        ds, zb = _synthetic()
        h = tm.running_hmax(ds, zb, dt.datetime(2023, 9, 2, 7, 0))       # hour 31
        self.assertAlmostEqual(float(h[0, 0]), 2.0)

    def test_completed_daily_blocks_add_sub_hourly_peaks(self):
        ds, zb = _synthetic()
        h_end = tm.running_hmax(ds, zb, dt.datetime(2023, 9, 3, 0, 0))   # the block ending at day 2 00:00 is complete
        self.assertAlmostEqual(float(h_end[1, 1]), 3.0)
        h_mid = tm.running_hmax(ds, zb, dt.datetime(2023, 9, 2, 12, 0))  # that block is not complete yet
        self.assertAlmostEqual(float(h_mid[1, 1]), 0.2)

    def test_window_lower_bound(self):
        ds, zb = _synthetic()
        h = tm.running_hmax(ds, zb, dt.datetime(2023, 9, 3, 0, 0), t_from=dt.datetime(2023, 9, 2, 8, 0))
        self.assertAlmostEqual(float(h[0, 0]), 0.2)                      # the spike at hour 30 is before t_from (hour 32)

    def test_full_window_equals_validator_hmax(self):
        ds, zb = _synthetic()
        h = tm.running_hmax(ds, zb, None)
        ref = np.maximum(ds["zsmax"].max(dim="timemax").values - zb, 0)
        ref = np.maximum(ref, np.maximum(ds["zs"].max(dim="time").values - zb, 0))
        np.testing.assert_allclose(h, ref)


class AcquisitionParser(unittest.TestCase):
    def test_post_event_rows_with_rapidmapping_time(self):
        rows = [{"source_nam": "Open Street Map", "src_date": "30/10/2024", "source_tm": "Not Applicable", "eventphase": "Pre-event"},
                {"source_nam": "ICEYE", "src_date": "03/11/2024", "source_tm": "T01:51:00Z", "sensor_res": "2.5 m", "eventphase": "Post-event"}]
        acq = tm.post_event_acquisitions(rows)
        self.assertEqual(acq, [("ICEYE", dt.datetime(2024, 11, 3, 1, 51), "2.5 m")])

    def test_legacy_time_without_prefix(self):
        rows = [{"source_nam": "Pleiades-1A-1B", "src_date": "20/11/2017", "source_tm": "09:41:00", "eventphase": "Post-event"}]
        self.assertEqual(tm.post_event_acquisitions(rows)[0][1], dt.datetime(2017, 11, 20, 9, 41))

    def test_date_only_is_flagged(self):
        when, date_only = tm.parse_acq("2015-03-29", None)
        self.assertEqual((when, date_only), (dt.datetime(2015, 3, 29), True))
        when, date_only = tm.parse_acq("04/10/2026", "T16:22:00Z")
        self.assertEqual((when, date_only), (dt.datetime(2026, 10, 4, 16, 22), False))


if __name__ == "__main__":
    unittest.main()
