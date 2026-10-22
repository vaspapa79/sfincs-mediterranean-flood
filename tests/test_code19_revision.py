"""CODE-19 (R6b referee-driven revision, zero-compute): helpers of the table generator (reproduction/r6/scripts/r6_tables.py),
the figure script (r6_figures.py) and the look-up scripts (reproduction/v14_rerun/scripts/code19_*.py)."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "reproduction" / "r6" / "scripts", ROOT / "reproduction" / "v14_rerun" / "scripts"):
    sys.path.insert(0, str(p))
import r6_tables as T  # noqa: E402


class LeadInLabel(unittest.TestCase):
    def test_label_names_the_simulated_lead_in_and_both_pre_event_windows(self):
        w = {"spinup_days": 0, "pre_event_days": 10, "post_event_days": 3}
        w0 = {"spinup_days": 7, "pre_event_days": 3, "post_event_days": 3}
        self.assertEqual(T.leadin_label(w, w0), "7-day lead-in simulated (10 d before the event day; canonical 3 d)")


class ManningTable(unittest.TestCase):
    def test_rows_come_from_the_pipeline_lookup_file(self):
        rows = T.manning_rows(ROOT)
        self.assertEqual(len(rows), 11)
        n = {code: val for code, _name, val in rows}
        self.assertEqual(n[50], 0.012)       # built-up, the value the manuscript quotes
        self.assertEqual(n[80], 0.020)
        names = {code: name for code, name, _ in rows}
        self.assertEqual(names[50], "Built-up")
        self.assertEqual(names[80], "Permanent water bodies")

    def test_every_worldcover_class_of_the_file_has_a_name(self):
        codes = {code for code, _n, _v in T.manning_rows(ROOT)}
        self.assertTrue(codes <= set(T.WORLDCOVER_CLASSES))


class BaselineRows(unittest.TestCase):
    def test_s1_baseline_rows_resolve_the_manuscript_values(self):
        ctx = T.Ctx(ROOT, None)
        rows = T.baseline_sweep_rows(ctx)
        self.assertEqual(len(rows), 16)      # four ERA5(T) baselines x four thresholds
        pin = next(r for r in rows if r[1] == "pineios_baseline_gridmatched" and r[2] == "h_max > 0.50 m")
        self.assertEqual(pin[6], "0.422")    # section 4.1
        crete = {r[2]: r[6] for r in rows if r[1] == "crete_baseline"}
        self.assertEqual((crete["h_max > 0.25 m"], crete["h_max > 0.50 m"]), ("0.302", "0.270"))   # section 4.6
        self.assertTrue(all("baseline" in r[0] for r in rows))


class MapLegend(unittest.TestCase):
    def test_inactive_entry_is_first_and_white(self):
        import r6_figures as F
        h = F.map_legend_handles()
        self.assertEqual(h[0].get_label(), "inactive (above the elevation ceiling or open sea)")
        self.assertEqual(tuple(h[0].get_facecolor()[:3]), (1.0, 1.0, 1.0))
        self.assertIn(F.EXCL_LABEL, [x.get_label() for x in h])


class WorkflowFigure(unittest.TestCase):
    def test_box_texts_set_h_max_as_mathtext(self):
        import r6_figures as F
        texts = [b["text"] for b in F.FIG2_BOXES]
        self.assertFalse(any("h_max" in t for t in texts))
        self.assertTrue(any(F.HMAX in t for t in texts))


class RainWindows(unittest.TestCase):
    def test_end_labelled_hourly_accumulations_take_t0_exclusive_t1_inclusive(self):
        import code19_a1_rain_leadin as A1
        t = np.arange("2015-03-20T22:00", "2015-03-21T04:00", dtype="datetime64[h]")
        sel = A1.select_steps(t, np.datetime64("2015-03-21T00:00"), np.datetime64("2015-03-21T02:00"), labelling="end")
        self.assertEqual([str(x) for x in t[sel]], ["2015-03-21T01", "2015-03-21T02"])

    def test_start_labelled_half_hourly_rates_take_t0_inclusive_t1_exclusive(self):
        import code19_a1_rain_leadin as A1
        t = np.arange("2015-03-20T23:00", "2015-03-21T03:00", np.timedelta64(30, "m"), dtype="datetime64[m]")
        sel = A1.select_steps(t, np.datetime64("2015-03-21T00:00"), np.datetime64("2015-03-21T02:00"), labelling="start")
        self.assertEqual([str(x) for x in t[sel]], ["2015-03-21T00:00", "2015-03-21T00:30", "2015-03-21T01:00", "2015-03-21T01:30"])

    def test_rolling_24h_total_is_the_largest_window_sum(self):
        import code19_a1_rain_leadin as A1
        rate = np.zeros(72)             # hourly mm/h over three days
        rate[30:40] = 2.0               # 20 mm inside one day
        rate[60:62] = 5.0               # 10 mm later
        tot, i0 = A1.rolling_max(rate, step_h=1.0, hours=24)
        self.assertAlmostEqual(tot, 20.0)
        self.assertTrue(7 <= i0 <= 30)   # any 24-step window that holds the whole 2.0 block


class InverseBarometer(unittest.TestCase):
    def test_25hpa_depression_raises_the_boundary_by_25cm(self):
        import code19_a2_ib_boundary as A2
        self.assertAlmostEqual(A2.ib_m(np.array([101325.0 - 2500.0]))[0], 0.2489, places=4)   # as the CODE-12 synthetic test


class SouthernEdge(unittest.TestCase):
    def test_counts_the_southern_rows_with_y_ascending(self):
        import code19_b45_map_checks as B
        wet = np.zeros((8, 4), bool); wet[0, 1] = True; wet[4, 0] = True; wet[7, 3] = True
        msk = np.ones((8, 4), int); msk[0, 2] = 2
        aoi = np.zeros((8, 4), bool); aoi[4, 0] = True
        hmax = np.where(wet, 0.5, 0.0)
        r = B.southern_rows_summary(wet, msk, aoi, hmax, n_rows=5)
        self.assertEqual(r["wet_cells"], 2)
        self.assertEqual(r["wet_in_aoi"], 1)
        self.assertEqual(r["row0_wet_closed"], 1)      # the wet row-0 cell is msk = 1 (closed edge)
        self.assertEqual(r["row0_msk2"], 1)


if __name__ == "__main__":
    unittest.main()
