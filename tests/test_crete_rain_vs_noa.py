"""Phase 5d (GO Phases 3-5): Crete rainfall diagnostics vs the NOA stations. The station file holds local calendar days
(EEST = UTC+3, so a local day is 21:00 UTC -> 21:00 UTC); the anchor window of rule_ledger.md §8 is the five local days
30 Sep - 4 Oct 2026 = 2026-09-29T21:00Z -> 2026-10-04T21:00Z. Helpers: station totals over the local days, the UTC window
they correspond to, and the nearest-cell total of a gridded rate field over that window."""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import crete_rain_vs_noa as cr  # noqa: E402

CSV = """station_slug,station_name,lat,lon,elev_m,date,rain_mm,source_url,accessed_utc,note
tz,"Tz",35.2,25.5,820,2026-09-29,6.8,u,t,n
tz,"Tz",35.2,25.5,820,2026-09-30,40.6,u,t,n
tz,"Tz",35.2,25.5,820,2026-10-01,231.0,u,t,n
tz,"Tz",35.2,25.5,820,2026-10-02,107.2,u,t,n
tz,"Tz",35.2,25.5,820,2026-10-03,35.6,u,t,n
tz,"Tz",35.2,25.5,820,2026-10-04,33.4,u,t,n
tz,"Tz",35.2,25.5,820,2026-10-05,1.0,u,t,n
an,"An",35.3,24.9,811,2026-10-01,100.0,u,t,n
"""


class StationTotals(unittest.TestCase):
    def test_five_local_days_sum(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "daily.csv"; p.write_text(CSV, encoding="utf-8")
            tot = cr.station_totals(p, ("2026-09-30", "2026-10-04"))
        self.assertAlmostEqual(tot["tz"]["noa_total_mm"], 40.6 + 231.0 + 107.2 + 35.6 + 33.4)
        self.assertEqual(tot["tz"]["n_days"], 5)
        self.assertEqual((tot["tz"]["lat"], tot["tz"]["lon"]), (35.2, 25.5))
        self.assertEqual(tot["an"]["n_days"], 1)                     # incomplete record flagged by the day count

    def test_local_days_to_utc_window(self):
        t0, t1 = cr.utc_window("2026-09-30", "2026-10-04")
        self.assertEqual(t0, dt.datetime(2026, 9, 29, 21, 0)); self.assertEqual(t1, dt.datetime(2026, 10, 4, 21, 0))


class NearestCellTotal(unittest.TestCase):
    def test_total_over_window_at_nearest_cell(self):
        import xarray as xr
        t0 = np.datetime64("2026-09-29T00:00:00")
        time = t0 + np.arange(24 * 7) * np.timedelta64(1, "h")
        rate = np.zeros((len(time), 2, 2)); rate[:, 1, 0] = 2.0                      # 2 mm/h at (lat 35.2, lon 25.4)
        da = xr.DataArray(rate, dims=("time", "latitude", "longitude"), coords={"time": time, "latitude": [35.1, 35.2], "longitude": [25.4, 25.6]})
        tot, cell = cr.nearest_total_mm(da, lon=25.45, lat=35.22, t0=dt.datetime(2026, 9, 29, 21), t1=dt.datetime(2026, 10, 4, 21))
        self.assertAlmostEqual(tot, 2.0 * 120)
        self.assertEqual(cell, (25.4, 35.2))


if __name__ == "__main__":
    unittest.main()
