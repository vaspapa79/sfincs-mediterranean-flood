"""CODE-20 (figure set after the benchmark correction, three records, S2 digest rows): helpers of the figure script
(reproduction/r6/scripts/r6_figures.py), the table generator (r6_tables.py) and the record scripts
(reproduction/v14_rerun/scripts/code20_*.py)."""
import csv
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "reproduction" / "r6" / "scripts", ROOT / "reproduction" / "v14_rerun" / "scripts"):
    sys.path.insert(0, str(p))
import r6_tables as T  # noqa: E402


class F10Benchmarks(unittest.TestCase):
    def test_band_is_the_bernhofen_average_csi_range(self):
        import r6_figures as F
        lab, lo, hi = F.F10_BAND
        self.assertEqual((lo, hi), (0.45, 0.70))                     # Bernhofen et al. 2018, p. 5: 0.45 (GLOFRIS) to 0.70 (JRC)
        self.assertEqual(lab, "global models vs MODIS extents, Bernhofen et al. (2018)")

    def test_reference_lines_are_the_sadana_same_solver_means(self):
        import r6_figures as F
        lines = {ln["label"]: ln for ln in F.F10_LINES}
        g = lines["SFINCS, GloFAS forcing, ≥ 1000 km² / < 50 km² (Sadana et al. 2026)"]
        self.assertEqual(g["values"], (0.42, 0.29))
        self.assertEqual(g["ls"], ":")
        o = lines["SFINCS, observed discharge (Sadana et al. 2026)"]
        self.assertEqual(o["values"], (0.67,))
        self.assertEqual(o["ls"], "--")

    def test_no_hocini_band_and_a_fixed_axis(self):
        import r6_figures as F
        self.assertEqual(F.F10_YLIM, (0.0, 0.8))
        self.assertNotIn("Hocini", repr(F.F10_BAND) + repr(F.F10_LINES))


class MapDrawOrder(unittest.TestCase):
    def test_every_map_figure_draws_the_exclusion_mask_above_the_depth_layer(self):
        import r6_figures as F
        self.assertEqual(set(F.EXCL_ON_TOP), {"F3", "F5", "F6", "F7", "F8", "F9"})
        self.assertTrue(all(F.EXCL_ON_TOP.values()))

    def test_draw_layers_puts_the_exclusion_image_after_the_depth_image_when_on_top(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import r6_figures as F
        from types import SimpleNamespace
        wet = np.ones((3, 4), bool)
        excl = np.zeros((3, 4), bool); excl[0, 0] = True
        ems = np.zeros((3, 4), bool); ems[1, 1] = True
        k = SimpleNamespace(ext=[0, 4, 0, 3], active=np.ones((3, 4), bool), excl=excl, wet=wet, hmax=np.full((3, 4), 0.5),
                            ems_wet=ems, aoi_m=np.ones((3, 4), bool))
        for on_top, expect in ((True, [False, True, False]), (False, [False, False, True])):   # position of the depth image
            fig, ax = plt.subplots()
            F.draw_layers(ax, k, excl_on_top=on_top)
            self.assertEqual([im.get_cmap().name == "depth" for im in ax.images], expect)
            plt.close(fig)


class S2Digest(unittest.TestCase):
    def test_strymonas_baseline_rows_in_the_digest_columns(self):
        with open(ROOT / "reproduction" / "r6" / "tables" / "S2.csv", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh); header = next(rd); rows = list(rd)
        d = T.s2_baseline_digest(header, rows)
        self.assertEqual([r[0] for r in d], ["01STRYMONAS", "02BALTOTOPI", "03ACHINOS", "04MAVROTHALASSA"])
        self.assertEqual(d[0][1:], ["104.2", "145.1", "0.207", "0.410", "0.706", "0.229"])
        self.assertEqual(d[1][3:5], ["0.124", "0.357"])      # section 4.2 values
        self.assertEqual(d[2][3:5], ["0.333", "0.365"])
        self.assertEqual(d[3][3], "0.358")
        self.assertEqual(T.S2_DIGEST_HEADER, ["AOI", "observed km²", "modelled km² (h_max > 0.10 m)", "CSI", "HR", "FAR", "fuzzy r=1 CSI"])


class FreezeOrder(unittest.TestCase):
    def test_local_offset_timestamps_convert_to_utc(self):
        import code20_b1_freeze_order as B1
        self.assertEqual(B1.to_utc("2026-07-15 14:33:54 +0300"), "2026-07-15T11:33:54Z")
        self.assertEqual(B1.to_utc("2026-07-15 14:33:54 +03:00"), "2026-07-15T11:33:54Z")
        self.assertEqual(B1.to_utc("2026-07-15T13:13:03Z"), "2026-07-15T13:13:03Z")

    def test_order_names_the_earlier_event_and_the_lead(self):
        import code20_b1_freeze_order as B1
        r = B1.order("2026-07-15T11:33:54Z", "2026-07-15T13:13:03Z")
        self.assertEqual(r["first"], "commit")
        self.assertEqual(r["lead_s"], 5949)
        self.assertEqual(B1.order("2026-07-15T14:00:00Z", "2026-07-15T13:13:03Z")["first"], "metrics")


class NestedProducts(unittest.TestCase):
    def test_covered_fraction_of_a_polygon_by_another(self):
        import code20_b3_emsr773_nested as B3
        from shapely.geometry import box
        self.assertAlmostEqual(B3.covered_fraction(box(0, 0, 2, 2), box(1, 0, 3, 2)), 0.5)
        self.assertEqual(B3.covered_fraction(box(0, 0, 2, 2), None), 0.0)
        self.assertEqual(B3.covered_fraction(box(0, 0, 0, 0), box(0, 0, 1, 1)), 0.0)


class ReleasePage(unittest.TestCase):
    def test_release_summary_reads_name_dates_and_asset_count(self):
        import code20_b4_sfincs_release as B4
        rel = [{"tag_name": "v2.3.0_mt_Faber_release", "name": "SFINCS v2.3.0 mt Faber Release 2025.02", "published_at": "2025-11-19T14:43:54Z",
                "created_at": "2025-11-18T13:50:39Z", "assets": [], "html_url": "u", "prerelease": False, "body": "x"}]
        s = B4.release_summary(rel, "v2.3.0_mt_Faber_release")
        self.assertEqual(s["name"], "SFINCS v2.3.0 mt Faber Release 2025.02")
        self.assertEqual((s["published_at"], s["created_at"], s["n_assets"]), ("2025-11-19T14:43:54Z", "2025-11-18T13:50:39Z", 0))
        self.assertEqual(s["assets_dated"], [])


if __name__ == "__main__":
    unittest.main()
