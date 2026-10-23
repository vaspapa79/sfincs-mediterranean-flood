"""CODE-17: helpers of the release-document generator (reproduction/r6/scripts/release_docs.py) and of the EMSR933
per-AOI-catchment rainfall diagnostic (reproduction/v14_rerun/scripts/crete_rain_per_aoi.py) — defect-line format, the
S10 column mapping, nearest-grid-cell lookup on either axis order, and the event-total convention (rates x step)."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reproduction" / "r6" / "scripts"))
sys.path.insert(0, str(ROOT / "reproduction" / "v14_rerun" / "scripts"))
import crete_rain_per_aoi as RA  # noqa: E402
import release_docs as RD  # noqa: E402


class DefectLine(unittest.TestCase):
    def test_fix_commit_runs_and_guard(self):
        d = {"defect": "D0", "symptom": "GloFAS point sampling", "runs affected": "14 of 28 release runs", "fix commit": "ca0f7cb",
             "tag": "v1.4.1", "guard": "tests: test_prep_q_sampler.py"}
        self.assertEqual(RD.defect_line(d), "- **D0** GloFAS point sampling — runs affected: 14 of 28 release runs — fix `ca0f7cb` — "
                                            "guard: test_prep_q_sampler.py")

    def test_text_only_defect_has_no_fix_commit(self):
        d = {"defect": "D0", "symptom": "tspinup = 0", "runs affected": "none (methods text only)", "fix commit": "—", "tag": "—",
             "guard": "no test naming it"}
        line = RD.defect_line(d)
        self.assertIn("no code change", line)
        self.assertNotIn("`—`", line)


class S10Mapping(unittest.TestCase):
    def test_every_defect_has_symptom_runs_fix_and_guard(self):
        dd = RD.defects(ROOT)
        self.assertEqual(sorted(dd), [f"D{k}" for k in range(1, 9)])
        for d in dd.values():
            for k in ("symptom", "runs affected", "fix commit", "guard"):
                self.assertTrue(d[k], (d["defect"], k))


class NearestIndex(unittest.TestCase):
    def test_ascending_and_descending_axes(self):
        asc = np.array([34.85, 34.95, 35.05])
        vals = np.array([34.80, 34.99, 35.20])
        self.assertEqual(RA.nearest_index(asc, vals).tolist(), [0, 1, 2])
        self.assertEqual(RA.nearest_index(asc[::-1], vals).tolist(), [2, 1, 0])

    def test_value_between_cells_takes_the_closer_one(self):
        self.assertEqual(RA.nearest_index(np.array([0.0, 0.1, 0.2]), np.array([0.14, 0.16])).tolist(), [1, 2])


class FieldTotal(unittest.TestCase):
    def test_total_is_rate_times_step_inside_the_half_open_window(self):
        import pandas as pd
        import xarray as xr
        t = pd.date_range("2026-10-01T00:00", periods=6, freq="30min")
        da = xr.DataArray(np.full((6, 1, 2), 2.0), dims=("time", "latitude", "longitude"),
                          coords={"time": t, "latitude": [35.0], "longitude": [25.0, 25.1]})
        tot, lats, lons, step_h, n = RA.field_total(da, t[1], t[5])
        self.assertEqual(step_h, 0.5)
        self.assertEqual(n, 4)
        self.assertTrue(np.allclose(tot, 4 * 2.0 * 0.5))


if __name__ == "__main__":
    unittest.main()
