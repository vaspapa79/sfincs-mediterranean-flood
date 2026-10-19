"""Phase 4a (GO Phases 3-5): truth-polygon positional uncertainty — re-score with the EMS observed extent buffered by
+/-20 m, in the RASTER domain exactly as validation/truth_uncertainty.py did for the published runs: the polygons are
rasterised on a fine grid of ~20 m (refine = round(dx / 20)), eroded/dilated by round(|d| / fine_cell) fine cells, and a
model cell is wet if any of its sub-cells is (the all_touched rule). Tests on a 10-m synthetic grid (refine 1, so a 20-m
buffer is two cells): buffering grows / shrinks the rasterised truth exactly and a zero buffer reproduces the plain rasterisation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "reproduction" / "v14_rerun" / "scripts"))

import truth_buffer_scores as tb  # noqa: E402


def _grid(n=20, dx=10.0):
    xs = (np.arange(n) + 0.5) * dx
    ys = (np.arange(n) + 0.5) * dx
    x, y = np.meshgrid(xs, ys)
    return {"x": x, "y": y, "dx": dx, "dy": dx, "cell_area_km2": dx * dx / 1e6}


class Buffering(unittest.TestCase):
    def setUp(self):
        from shapely.geometry import box
        self.s = _grid()
        self.geom = box(50.0, 50.0, 110.0, 110.0)        # 60 x 60 m square = cells 5..10 (36 cells) on the 10-m grid

    def test_zero_buffer_matches_plain_rasterisation(self):
        a = tb.rasterise_geoms([self.geom], self.s, buffer_m=0.0)
        b = tb.rasterise_geoms([self.geom], self.s)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(int(a.sum()), 36)

    def test_positive_buffer_grows_and_negative_shrinks_by_whole_fine_cells(self):
        plus = tb.rasterise_geoms([self.geom], self.s, buffer_m=20.0)      # +2 cells of 10 m: cells 3..12 -> 10 x 10
        minus = tb.rasterise_geoms([self.geom], self.s, buffer_m=-20.0)    # -2 cells: cells 7..8 -> 2 x 2
        base = tb.rasterise_geoms([self.geom], self.s)
        self.assertTrue(np.all(base <= plus)); self.assertTrue(np.all(minus <= base))
        self.assertEqual(int(plus.sum()), 100)
        self.assertEqual(int(minus.sum()), 4)

    def test_refine_follows_the_published_rule(self):
        self.assertEqual(tb.refine_for(150.0), 8)      # 150 m / 20 m -> 7.5 -> 8 (fine cell 18.75 m)
        self.assertEqual(tb.refine_for(50.0), 2)       # 25 m fine cells
        self.assertEqual(tb.refine_for(100.0), 5)      # 20 m fine cells
        self.assertEqual(tb.refine_for(10.0), 1)

    def test_rows_are_in_map_order(self):
        """The validator returns rows with y ascending (row 0 = south). A polygon at the south edge must land in row 0."""
        from shapely.geometry import box
        r = tb.rasterise_geoms([box(0.0, 0.0, 10.0, 10.0)], self.s)
        self.assertTrue(r[0, 0]); self.assertFalse(r[-1, 0])


class Scores(unittest.TestCase):
    def test_contingency_on_buffered_truth(self):
        s = _grid()
        from shapely.geometry import box
        truth = box(50.0, 50.0, 110.0, 110.0)
        model_wet = tb.rasterise_geoms([box(50.0, 50.0, 130.0, 110.0)], s)   # 60 x 80 m: covers the truth + 12 cells more
        out = tb.buffer_sweep(model_wet, [truth], np.ones((20, 20), dtype=bool), s, buffers_m=(-20.0, 0.0, 20.0))
        self.assertEqual(out["0"]["tp"], 36); self.assertEqual(out["0"]["fp"], 12); self.assertEqual(out["0"]["fn"], 0)
        self.assertGreater(out["20"]["fn"], 0)          # the dilated truth exceeds the model on three sides
        self.assertLess(out["-20"]["tp"], out["0"]["tp"])


if __name__ == "__main__":
    unittest.main()
