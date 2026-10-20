"""GloFAS request area (harness v1.4.2, CODE-15 B (2), 2026-10-20).

The sampler reads every named point's window [lon +- half, lat +- half] (half = upstream_q.src_points[*].window_deg,
default prep_q_at_outlets.WINDOW_HALF_DEG). v1.3 downloaded the buffered bbox only, so a point near the domain edge had
its window clipped by the file edge (Pineios/Kalambaka: 21.63 - 0.1 < 21.84 - 0.2 — two of the four window cells were
missing and the rule picked a 0.6 m3/s hillslope cell). Under harness v1.4 the area is extended, side by side, in whole
lattice steps until every window plus half a cell lies inside, so the Open-Meteo lattice stays anchored at the buffered
bbox corner and every previously downloaded coordinate keeps its value.
"""
from __future__ import annotations

import math

DEFAULT_WINDOW_HALF_DEG = 0.1


def request_area(bbox: dict, src_points: list, step: float, window_half: float = DEFAULT_WINDOW_HALF_DEG, default_buffer: float = 0.2):
    """[N, W, S, E] (CDS/EWDS order) of the buffered bbox extended in whole `step`s so that every point's sampling window plus
    half a lattice cell is inside; returns (area, report)."""
    buf = float(bbox.get("era5_buffer_deg", default_buffer))
    n0, w0, s0, e0 = float(bbox["north"]) + buf, float(bbox["west"]) - buf, float(bbox["south"]) - buf, float(bbox["east"]) + buf
    steps = {"north": 0, "west": 0, "south": 0, "east": 0}
    by_point = {}
    for sp in src_points:
        lon, lat = float(sp["lon"]), float(sp["lat"])
        half = float(sp.get("window_deg", window_half)) + step / 2.0
        need = {"west": w0 - (lon - half), "east": (lon + half) - e0, "south": s0 - (lat - half), "north": (lat + half) - n0}
        sides = []
        for side, deficit in need.items():
            if deficit > 1e-9:
                k = int(math.ceil(round(deficit / step, 9)))
                if k > steps[side]:
                    steps[side] = k
                sides.append(side)
        if sides:
            by_point[sp.get("name", f"{lon},{lat}")] = sides
    area = [round(n0 + steps["north"] * step, 6), round(w0 - steps["west"] * step, 6), round(s0 - steps["south"] * step, 6), round(e0 + steps["east"] * step, 6)]
    return area, {"buffered_bbox_nwse": [round(n0, 6), round(w0, 6), round(s0, 6), round(e0, 6)], "step_deg": step, "extended_steps": steps, "extended_by": by_point}


def lattice_coords(lo: float, hi: float, step: float):
    """Lattice coordinates lo, lo + step, ... up to hi (inclusive within half a step): an explicit count, so the legacy
    np.arange(lo, hi + step/2, step) result is reproduced without its float-rounding sensitivity to the start value."""
    import math
    import numpy as np
    n = int(math.floor(round((hi - lo) / step, 6) + 1e-9)) + 1
    return np.round(lo + step * np.arange(n), 2)
