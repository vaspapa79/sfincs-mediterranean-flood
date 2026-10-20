"""Harness v1.4.2 (CODE-15 B, 2026-10-20) — D8 (2): the GloFAS download area covers every named point's sampling window.
Under harness v1.4 the request area is the buffered bbox extended, side by side and in whole lattice steps (so the
Open-Meteo lattice stays anchored and the already-downloaded cells keep their coordinates), until every point's
window [lon +- half, lat +- half] plus half a cell lies inside; v1.3 keeps the buffered bbox (Kalambaka's window was clipped).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

import glofas_area as ga  # noqa: E402

PINEIOS_BBOX = {"west": 21.84, "south": 39.31, "east": 22.99, "north": 40.02, "era5_buffer_deg": 0.2}
PINEIOS_POINTS = [{"name": "pineios_trikala", "lon": 21.77, "lat": 39.56, "src_lon": 21.86, "src_lat": 39.56},
                  {"name": "pineios_kalambaka", "lon": 21.63, "lat": 39.70, "src_lon": 21.86, "src_lat": 39.70},
                  {"name": "titarisios", "lon": 22.42, "lat": 39.71},
                  {"name": "enipeas", "lon": 22.39, "lat": 39.30, "src_lon": 22.39, "src_lat": 39.33}]


class RequestArea(unittest.TestCase):
    def test_no_points_keeps_the_buffered_bbox(self):
        area, rep = ga.request_area(PINEIOS_BBOX, [], step=0.1)
        self.assertEqual(area, [40.22, 21.64, 39.11, 23.19])            # N, W, S, E (CDS order)
        self.assertEqual(rep["extended_steps"], {"north": 0, "west": 0, "south": 0, "east": 0})

    def test_points_inside_the_buffer_do_not_extend(self):
        area, rep = ga.request_area(PINEIOS_BBOX, [PINEIOS_POINTS[2], PINEIOS_POINTS[3]], step=0.1)
        self.assertEqual(area, [40.22, 21.64, 39.11, 23.19])

    def test_kalambaka_extends_the_west_side_by_two_lattice_steps(self):
        """Kalambaka (21.63) needs cells down to 21.63 - 0.1 - 0.05 = 21.48 < 21.64: 0.16 deg -> 2 whole steps of 0.1 -> west = 21.44,
        so the lattice 21.44, 21.54, 21.64, ... keeps every previously downloaded coordinate."""
        area, rep = ga.request_area(PINEIOS_BBOX, PINEIOS_POINTS, step=0.1)
        self.assertEqual(area, [40.22, 21.44, 39.11, 23.19])
        self.assertEqual(rep["extended_steps"]["west"], 2)
        self.assertEqual(rep["extended_by"]["pineios_kalambaka"], ["west"])

    def test_a_narrow_per_point_window_needs_less(self):
        pts = [{"name": "narrow", "lon": 21.63, "lat": 39.70, "window_deg": 0.02}]
        area, rep = ga.request_area(PINEIOS_BBOX, pts, step=0.1)
        self.assertEqual(area, [40.22, 21.54, 39.11, 23.19])             # 21.63 - 0.02 - 0.05 = 21.56 -> one step

    def test_ewds_grid_step_0_05(self):
        bbox = {"west": 11.35, "south": 44.0, "east": 12.55, "north": 44.75, "era5_buffer_deg": 0.3}
        pts = [{"name": "far_north", "lon": 12.0, "lat": 45.0}]
        area, rep = ga.request_area(bbox, pts, step=0.05)
        self.assertEqual(area[0], 45.15)                                 # 45.0 + 0.1 + 0.025 = 45.125 > 45.05 -> 2 steps of 0.05
        self.assertEqual(rep["extended_steps"]["north"], 2)




class LatticeCoordinates(unittest.TestCase):
    """The Open-Meteo lattice is built from an explicit point count, not np.arange(stop + step/2): the legacy count is kept
    (21.64..23.19 -> 16 columns, 39.11..40.22 -> 12 rows) and an extended west edge does not add a float-rounding column."""

    def test_legacy_counts(self):
        self.assertEqual(list(ga.lattice_coords(21.64, 23.19, 0.1)), [round(21.64 + 0.1 * k, 2) for k in range(16)])
        self.assertEqual(list(ga.lattice_coords(39.11, 40.22, 0.1)), [round(39.11 + 0.1 * k, 2) for k in range(12)])

    def test_extended_west_edge_keeps_the_east_end(self):
        lons = list(ga.lattice_coords(21.44, 23.19, 0.1))
        self.assertEqual(len(lons), 18)
        self.assertEqual(lons[-1], 23.14)
        self.assertIn(21.64, lons)


if __name__ == "__main__":
    unittest.main()
