"""GloFAS v4 river network from the CEMS static maps (CODE-15 A, 2026-10-20): `uparea_glofas_v4_0.nc` (upstream area, m2)
and `ldd_glofas_v4_0.nc` (PCRaster local drain direction, keypad 1-9, 5 = pit), 0.05 deg global, downloaded from
https://confluence.ecmwf.int/display/CEMS/Auxiliary+Data (attachments of page 242067380). They make "same river", "downstream
of a confluence" and "nested" objective instead of a reading of the discharge field.

Conventions: cells are (i, j) = (latitude index, longitude index) of the 0.05 deg grid; a file coordinate of a discharge
file is mapped to the cell CONTAINING it (EWDS files share the grid; the Open-Meteo 0.1 deg lattice of the Pineios file
returns the 0.05 deg cell containing the requested point).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

R3_MIN_KM2 = 120.0          # rule R3: a river counts from 4 GloFAS cells (~120 km2)
CONFLUENCE_RATIO = 2.0      # a step that multiplies the upstream area by more than this = another, larger river joined
MAIN_STEM_SHARE = 2.0 / 3.0  # tracing upstream, the largest tributary must carry more than this share of the area to count as the main stem
# PCRaster LDD keypad -> (di, dj) on a north-up grid (i grows southward)
_LDD = {1: (1, -1), 2: (1, 0), 3: (1, 1), 4: (0, -1), 5: (0, 0), 6: (0, 1), 7: (-1, -1), 8: (-1, 0), 9: (-1, 1)}


class GlofasNetwork:
    def __init__(self, static_dir: Path):
        import xarray as xr
        up = xr.open_dataset(Path(static_dir) / "uparea_glofas_v4_0.nc")
        ld = xr.open_dataset(Path(static_dir) / "ldd_glofas_v4_0.nc")
        self.lat = np.asarray(up["latitude"].values, dtype=float)          # descending, 89.975 .. -59.975
        self.lon = np.asarray(up["longitude"].values, dtype=float)         # -179.975 .. 179.975
        self.uparea_km2 = np.asarray(up["uparea"].values, dtype=np.float64) / 1e6
        self.ldd = np.asarray(ld["ldd"].values, dtype=float)
        assert self.ldd.shape == self.uparea_km2.shape
        self.step = 0.05

    # ---- indexing
    def cell(self, lon: float, lat: float) -> tuple[int, int]:
        """(i, j) of the 0.05 deg cell containing (lon, lat)."""
        j = int(math.floor((lon + 180.0) / self.step)) % self.lon.size
        i = int(math.floor((90.0 - lat) / self.step))
        return i, j

    def centre(self, ij) -> tuple[float, float]:
        i, j = ij
        return round(float(self.lon[j]), 3), round(float(self.lat[i]), 3)

    def uparea(self, ij) -> float:
        v = self.uparea_km2[ij[0], ij[1]]
        return float(v) if np.isfinite(v) else 0.0

    # ---- routing
    def downstream(self, ij):
        d = self.ldd[ij[0], ij[1]]
        if not np.isfinite(d) or int(d) == 5:
            return None
        di, dj = _LDD[int(d)]
        i, j = ij[0] + di, (ij[1] + dj) % self.lon.size
        if not (0 <= i < self.lat.size):
            return None
        return (i, j)

    def path_down(self, ij, max_steps: int = 400) -> list[tuple[int, int]]:
        out = [tuple(ij)]
        cur = tuple(ij)
        for _ in range(max_steps):
            nxt = self.downstream(cur)
            if nxt is None or nxt in out:
                break
            out.append(nxt)
            cur = nxt
        return out

    def is_downstream(self, a, b, max_steps: int = 400) -> bool:
        """True when cell b lies on the drainage path downstream of cell a (a itself excluded)."""
        return tuple(b) in self.path_down(a, max_steps)[1:]

    def first_river_cell(self, ij, min_km2: float = R3_MIN_KM2):
        """First cell on the path from ij (inclusive) with upstream area >= min_km2 — the river the point drains to."""
        for c in self.path_down(ij):
            if self.uparea(c) >= min_km2:
                return c
        return None

    def last_cell_before_larger_river(self, ij, ratio: float = CONFLUENCE_RATIO):
        """Follow the path from ij: the last cell before a step that multiplies the upstream area by more than `ratio`
        (the river's own last cell before it joins a larger one); the pit / last cell when no such step occurs."""
        p = self.path_down(ij)
        for k in range(len(p) - 1):
            if self.uparea(p[k]) > 0 and self.uparea(p[k + 1]) > ratio * self.uparea(p[k]):
                return p[k]
        return p[-1]

    def classify_rule_cell(self, point_lonlat, rule_lonlat, min_km2: float = R3_MIN_KM2, ratio: float = CONFLUENCE_RATIO) -> dict:
        """How the sampler's cell relates to the river the named point drains to."""
        p0 = self.cell(*point_lonlat)
        river = self.first_river_cell(p0, min_km2)
        rule = self.cell(*rule_lonlat)
        path = self.path_down(p0)
        on_path = rule in path
        out = {"point_cell": self.centre(p0), "point_cell_uparea_km2": round(self.uparea(p0), 1),
               "first_river_cell": (self.centre(river) if river else None), "first_river_uparea_km2": (round(self.uparea(river), 1) if river else None),
               "rule_cell": self.centre(rule), "rule_cell_uparea_km2": round(self.uparea(rule), 1), "rule_cell_on_drainage_path": on_path,
               "own_river_last_cell": None, "relation": None}
        if river:
            last = self.last_cell_before_larger_river(river, ratio)
            out["own_river_last_cell"] = self.centre(last); out["own_river_last_cell_uparea_km2"] = round(self.uparea(last), 1)
        if not on_path:
            out["relation"] = "another river (not on the drainage path of the point)"
        elif river and self.uparea(rule) > ratio * self.uparea(river):
            out["relation"] = f"downstream of a confluence with a larger river (upstream area x{self.uparea(rule) / self.uparea(river):.1f})"
        elif river and path.index(rule) < path.index(river):
            out["relation"] = "upstream of the point's river (headwater cell below the R3 threshold)"
        else:
            out["relation"] = "the point's own river"
        return out


# ------------------------------------------------------------------------------------------------ rivers by reference
def same_river(net: GlofasNetwork, a, b, ratio: float = CONFLUENCE_RATIO) -> bool:
    """a and b lie on one river: one is downstream of the other and no step on the connecting path multiplies the upstream
    area by more than `ratio` (i.e. no larger river joins in between)."""
    a, b = tuple(a), tuple(b)
    if a == b:
        return True
    for up, down in ((a, b), (b, a)):
        p = net.path_down(up)
        if down in p:
            seg = p[: p.index(down) + 1]
            return all(not (net.uparea(seg[k]) > 0 and net.uparea(seg[k + 1]) > ratio * net.uparea(seg[k])) for k in range(len(seg) - 1))
    return False


def main_stem_upstream(net: GlofasNetwork, ij, min_km2: float = R3_MIN_KM2, max_steps: int = 400) -> list[tuple[int, int]]:
    """Cells of the main stem upstream of ij (inclusive): at every step the upstream neighbour with the largest upstream area,
    until it falls below min_km2."""
    out = [tuple(ij)]
    cur = tuple(ij)
    for _ in range(max_steps):
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                n = (cur[0] + di, (cur[1] + dj) % net.lon.size)
                if 0 <= n[0] < net.lat.size and net.downstream(n) == cur:
                    if best is None or net.uparea(n) > net.uparea(best):
                        best = n
        if best is None or net.uparea(best) < min_km2 or net.uparea(best) < MAIN_STEM_SHARE * net.uparea(cur):
            break      # below the river threshold, or a confluence of comparable rivers: the main stem is ambiguous, stop
        out.append(best)
        cur = best
    return out


def river_cells(net: GlofasNetwork, reference, ratio: float = CONFLUENCE_RATIO, min_km2: float = R3_MIN_KM2) -> list[tuple[int, int]]:
    """All cells of the river through `reference`: its main stem upstream (down to min_km2) plus its course downstream until
    a larger river joins (the river's own last cell)."""
    ref = tuple(reference)
    up = main_stem_upstream(net, ref, min_km2)
    down = []
    p = net.path_down(ref)
    for k in range(len(p) - 1):
        if net.uparea(p[k]) > 0 and net.uparea(p[k + 1]) > ratio * net.uparea(p[k]):
            break
        down.append(p[k + 1])
    return list(dict.fromkeys(up[::-1] + down))


def lattice_shift_test(net: GlofasNetwork, da, shifts=((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0))) -> dict:
    """Which (row, col) shift of the containing cell makes a discharge file consistent with the static maps: river points
    (mean > 10 m3/s) must not sit on < 100 km2 cells, dry points (mean < 1) not on > 300 km2 cells."""
    import numpy as np
    m = da.mean("time")
    pts = [(float(lo), float(la), float(m.sel(latitude=la, longitude=lo))) for la in da.latitude.values for lo in da.longitude.values]
    riv = [p for p in pts if p[2] > 10]; dry = [p for p in pts if p[2] < 1]
    out = {"n_river_points": len(riv), "n_dry_points": len(dry), "shifts": {}}
    for di, dj in shifts:
        bad_r = sum(1 for lo, la, _ in riv if net.uparea((net.cell(lo, la)[0] + di, net.cell(lo, la)[1] + dj)) < 100)
        bad_d = sum(1 for lo, la, _ in dry if net.uparea((net.cell(lo, la)[0] + di, net.cell(lo, la)[1] + dj)) > 300)
        out["shifts"][f"rows{di:+d}_cols{dj:+d}"] = {"river_points_on_small_cells": bad_r, "dry_points_on_river_cells": bad_d}
    best = min(out["shifts"].items(), key=lambda kv: kv[1]["river_points_on_small_cells"] + kv[1]["dry_points_on_river_cells"])
    out["best_shift"] = best[0]
    return out
