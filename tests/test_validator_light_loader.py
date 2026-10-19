"""validate_event_v2.open_sfincs_light: the validator needs zb, msk, x, y, dx, dy and the zsmax blocks of sfincs_map.nc —
not the hourly zs that _anim_common.open_sfincs loads in full (2.4 GB for the 860 k-cell Crete grid, plus the same again
for its depth array). The light loader must agree with open_sfincs on every field the scoring uses and must not load zs."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "validation"))
sys.path.insert(0, str(REPO / "skill" / "scripts"))

import validate_event_v2 as v2  # noqa: E402
from _anim_common import open_sfincs  # noqa: E402

MODEL = Path("D:/ELKAK/implementation/v14/mandra_baseline/model")


class LightLoader(unittest.TestCase):
    def setUp(self):
        if not (MODEL / "sfincs_map.nc").exists():
            self.skipTest("local Mandra v1.4 model not present")

    def test_agrees_with_open_sfincs_on_the_scoring_fields(self):
        a, b = open_sfincs(MODEL), v2.open_sfincs_light(MODEL)
        for k in ("zb", "msk", "x", "y"):
            np.testing.assert_array_equal(a[k], b[k])
        for k in ("dx", "dy", "cell_area_km2", "ny", "nx"):
            self.assertEqual(a[k], b[k])
        np.testing.assert_array_equal(a["ds"]["zsmax"].values, b["ds"]["zsmax"].values)
        a["ds"].close(); b["ds"].close()

    def test_does_not_hold_the_hourly_series(self):
        b = v2.open_sfincs_light(MODEL)
        self.assertNotIn("zs", b); self.assertNotIn("h", b)
        self.assertFalse(b["ds"]["zs"].variable._in_memory)      # lazy: nothing read from the zs variable
        b["ds"].close()


if __name__ == "__main__":
    unittest.main()
