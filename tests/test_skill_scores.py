"""Base-rate-robust skill scores (validation/skill_scores.py): the properties the manuscript relies on, the F-is-POFD
distinction, and a regression against the published Table 14 values recomputed from the committed contingency tables
(the published outputs re-scored in Phase 1/2: reproduction/v14_rerun/results/<run>_v13_publishedmask.json)."""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "validation"))

import skill_scores as ss  # noqa: E402

RES = REPO / "reproduction" / "v14_rerun" / "results"
# NHESS R5 Table 14: event -> (contingency-table record, SEDI, PSS). The Strymonas row of Table 14 was computed from the
# author-reference v3 output (CSI 0.183 / HR 0.328; reproduction/val_json/strymonas_v3_author.json), not from the committed
# re-run (0.182 / 0.322), so that JSON is the regression source. Emilia: the printed PSS is 0.282, which is H and F rounded
# first (0.921 - 0.639); the exact value from the 8-AOI table is 0.2815 -> 0.281 (recorded for NUMBER_MAP.md).
TABLE14 = {
    "Mandra": (RES / "mandra_enhanced_v13_publishedmask.json", 0.362, 0.227),
    "Strymonas": (Path("D:/ELKAK/reproduction/val_json/strymonas_v3_author.json"), 0.429, 0.253),
    "Pineios": (RES / "pineios_enhanced_v13_publishedmask.json", 0.636, 0.423),
    "Emilia-R.": (RES / "emilia_enhanced_8aoi_v13_publishedmask.json", 0.460, 0.281),
    "Valencia": (RES / "valencia_enhanced_164_v13_publishedmask.json", 0.658, 0.352),
}


class Properties(unittest.TestCase):
    def test_no_skill_gives_zero(self):
        self.assertAlmostEqual(ss.sedi(0.3, 0.3), 0.0, places=12)
        self.assertAlmostEqual(ss.pss(0.3, 0.3), 0.0, places=12)

    def test_perfect_forecast(self):
        self.assertAlmostEqual(ss.pss(1.0, 0.0), 1.0)
        self.assertGreater(ss.sedi(1.0, 0.0), 0.999)

    def test_depends_on_h_and_f_only(self):
        a = ss.skill_scores(tp=100, fp=50, fn=100, tn=950)      # base rate 200 / 1200
        b = ss.skill_scores(tp=10, fp=500, fn=10, tn=9500)      # base rate 20 / 10020, same H = 0.5 and F = 0.05
        self.assertAlmostEqual(a["hit_rate"], b["hit_rate"]); self.assertAlmostEqual(a["pofd"], b["pofd"])
        self.assertAlmostEqual(a["sedi"], b["sedi"], places=12); self.assertAlmostEqual(a["pss"], b["pss"], places=12)

    def test_pofd_is_not_far(self):
        s = ss.skill_scores(tp=1526, fp=3639, fn=3211, tn=45965)
        self.assertNotAlmostEqual(s["pofd"], s["far"], places=2)
        self.assertAlmostEqual(s["far"], 3639 / (1526 + 3639))
        self.assertAlmostEqual(s["pofd"], 3639 / (3639 + 45965))

    def test_nan_when_undefined(self):
        self.assertTrue(math.isnan(ss.hit_rate(0, 0)))
        self.assertTrue(math.isnan(ss.pofd(0, 0)))


class PublishedTable14(unittest.TestCase):
    def test_sedi_pss_reproduce_table_14_from_the_committed_contingency_tables(self):
        for event, (p, sedi_pub, pss_pub) in TABLE14.items():
            if not p.exists():
                self.skipTest(f"{p.name} missing")
            c = json.loads(p.read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"]
            s = ss.skill_scores(c["tp"], c["fp"], c["fn"], c["tn"])
            with self.subTest(event=event):
                self.assertAlmostEqual(round(s["sedi"], 3), sedi_pub, places=3)
                self.assertAlmostEqual(round(s["pss"], 3), pss_pub, places=3)
                # the clamp is inert for every published event
                self.assertTrue(ss._EPS < s["hit_rate"] < 1 - ss._EPS and ss._EPS < s["pofd"] < 1 - ss._EPS)


if __name__ == "__main__":
    unittest.main()
