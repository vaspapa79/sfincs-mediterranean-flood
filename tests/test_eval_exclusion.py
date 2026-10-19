"""GO-C decision 3 — evaluation-mask exclusion, identical for every event: WorldCover class 80 (permanent water,
sampled at the model cell centre) UNION the v1.4 open-sea mask (build_model.open_sea_split on the v1.3-style
active mask + dep, i.e. what prepare_coastal_exclusion deactivates plus its coastal ring). The excluded cells leave
the evaluation universe on BOTH sides (model and EMS truth); the observed-flood area removed is reported.

The validator default (no --exclusion-tif) is untouched, so the published JSONs stay byte-identical.
Run: python -m unittest tests.test_eval_exclusion -v
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
sys.path.insert(0, str(REPO / "validation"))
os.environ.setdefault("GDAL_DATA", str(Path(sys.executable).parent / "Library" / "share" / "gdal"))

import eval_exclusion as EX  # noqa: E402
import validate_event_v2 as V  # noqa: E402

EPSG = 32634
X0, Y0, RES = 500_000.0, 4_000_000.0, 100.0        # a 6 x 5 UTM grid: x 500000..500600, y 4000000..4000500


def _write_tif(path: Path, arr, transform, crs, nodata=None):
    import rasterio
    arr = np.asarray(arr)
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype=arr.dtype,
                       crs=crs, transform=transform, nodata=nodata) as dst:
        dst.write(arr, 1)


def _north_up_transform(nx=6, ny=5):
    from rasterio.transform import from_origin
    return from_origin(X0, Y0 + ny * RES, RES, RES)


class OpenSeaFromGis(unittest.TestCase):
    """The v1.3 route: open sea from a model's gis/msk.tif + gis/dep.tif (north-up GeoTIFFs written by hydromt)."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="ex_gis_")); (self.d / "gis").mkdir()
        dep = np.full((5, 6), 5.0, "float32"); dep[:, 4:] = 0.0; dep[2, 1] = -1.0      # sea east (touches edge), inland pit
        msk = np.ones((5, 6), "uint8"); msk[:, 5] = 2                                 # perimeter boundary as published
        _write_tif(self.d / "gis" / "dep.tif", dep, _north_up_transform(), f"EPSG:{EPSG}", nodata=-9999.0)
        _write_tif(self.d / "gis" / "msk.tif", msk, _north_up_transform(), f"EPSG:{EPSG}", nodata=0)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_open_sea_is_the_edge_connected_sea_incl_the_ring_and_not_the_pit(self):
        sea, tr, crs = EX.open_sea_from_gis(self.d / "gis")
        self.assertEqual(sea.shape, (5, 6)); self.assertEqual(sea.dtype, bool)
        self.assertTrue(sea[:, 4:].all()); self.assertFalse(sea[:, :4].any())
        self.assertEqual(tr, _north_up_transform()); self.assertEqual(crs.to_epsg(), EPSG)


class WorldCover80AtCentres(unittest.TestCase):
    """Class 80 sampled at the model cell centre (the CODE-13 D4_check definition)."""

    def setUp(self):
        import pyproj
        from rasterio.transform import from_origin
        self.d = Path(tempfile.mkdtemp(prefix="ex_wc_"))
        # 0.0001-deg (~10 m) WorldCover-like raster covering the grid, class 80 west of lon_split, 30 elsewhere
        to_ll = pyproj.Transformer.from_crs(EPSG, 4326, always_xy=True)
        lon0, lat1 = to_ll.transform(X0 - 200, Y0 + 5 * RES + 200)
        lon1, lat0 = to_ll.transform(X0 + 6 * RES + 200, Y0 - 200)
        res = 0.0001; nx = int((lon1 - lon0) / res) + 1; ny = int((lat1 - lat0) / res) + 1
        lon = lon0 + res * (np.arange(nx) + 0.5)
        self.lon_split, _ = to_ll.transform(X0 + 2.5 * RES, Y0 + 2.5 * RES)          # between columns 2 and 3 (approx.)
        arr = np.where(lon[None, :] < self.lon_split, 80, 30).astype("uint8"); arr = np.repeat(arr, ny, axis=0)
        _write_tif(self.d / "wc.tif", arr, from_origin(lon0, lat1, res, res), "EPSG:4326", nodata=0)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_cells_whose_centre_is_class_80_are_flagged(self):
        wc80 = EX.worldcover80_at_centres(self.d / "wc.tif", _north_up_transform(), (5, 6), EPSG)
        self.assertEqual(wc80.shape, (5, 6)); self.assertEqual(wc80.dtype, bool)
        self.assertTrue(wc80[:, :2].all()); self.assertFalse(wc80[:, 3:].any())      # column 2 straddles the split


class MaskOnTheSfincsGrid(unittest.TestCase):
    """The exclusion GeoTIFF is north-up; sfincs_map.nc arrays are y-ascending (row 0 = south)."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="ex_grid_"))
        self.pattern = np.zeros((5, 6), "uint8"); self.pattern[0, 0] = 1               # NW corner cell only
        _write_tif(self.d / "excl.tif", self.pattern, _north_up_transform(), f"EPSG:{EPSG}", nodata=255)
        x = X0 + RES * (np.arange(6) + 0.5); y = Y0 + RES * (np.arange(5) + 0.5)        # ascending, as in the outputs
        self.s = {"x": np.tile(x, (5, 1)), "y": np.tile(y[:, None], (1, 6)), "dx": RES, "dy": RES}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_mask_is_flipped_onto_a_y_ascending_grid(self):
        m = EX.read_mask_for_grid(self.d / "excl.tif", self.s)
        self.assertEqual(m.dtype, bool); self.assertEqual(int(m.sum()), 1)
        self.assertTrue(m[4, 0])                                                      # the NW cell is the last row when y ascends

    def test_grid_mismatch_is_refused(self):
        s = dict(self.s); s["x"] = s["x"] + 50.0
        with self.assertRaises(ValueError):
            EX.read_mask_for_grid(self.d / "excl.tif", s)

    def test_write_then_read_round_trip(self):
        sea = np.zeros((5, 6), bool); sea[:, 4:] = True
        EX.write_mask_tif(self.d / "sea.tif", sea, _north_up_transform(), f"EPSG:{EPSG}")
        m = EX.read_mask_for_grid(self.d / "sea.tif", self.s)
        self.assertTrue(m[:, 4:].all()); self.assertFalse(m[:, :4].any())


class ValidatorApplyExclusion(unittest.TestCase):
    """validate_event_v2.apply_exclusion: both sides lose the excluded cells; the removed truth is reported."""

    def test_mask_shrinks_and_removed_truth_is_counted(self):
        ev = np.ones((4, 4), bool); ev[0, :] = False                                  # 12 evaluation cells
        ems = np.zeros((4, 4), bool); ems[1, :2] = True; ems[0, 0] = True             # 2 observed cells inside ev, 1 outside
        ex = np.zeros((4, 4), bool); ex[1, 0] = True; ex[3, 3] = True; ex[0, 1] = True  # 2 inside ev (one observed), 1 outside
        new, st = V.apply_exclusion(ev, ems, ex, cell_km2=0.0225)
        self.assertEqual(int(new.sum()), 10); self.assertFalse(new[1, 0]); self.assertFalse(new[3, 3])
        self.assertEqual(st["excluded_cells"], 2); self.assertAlmostEqual(st["excluded_km2"], 0.045)
        self.assertEqual(st["observed_wet_excluded_cells"], 1); self.assertAlmostEqual(st["observed_wet_excluded_km2"], 0.0225)
        self.assertEqual(st["observed_wet_before_cells"], 2); self.assertEqual(st["observed_wet_after_cells"], 1)

    def test_no_exclusion_returns_the_mask_unchanged(self):
        ev = np.ones((3, 3), bool); ems = np.zeros((3, 3), bool)
        new, st = V.apply_exclusion(ev, ems, None, cell_km2=1.0)
        self.assertIs(new, ev); self.assertIsNone(st)

    def test_validate_signature_defaults_to_no_exclusion(self):
        import inspect
        sig = inspect.signature(V._validate_ems_v2)
        self.assertIn("exclusion", sig.parameters); self.assertIsNone(sig.parameters["exclusion"].default)


class ExclusionUnionAndStats(unittest.TestCase):
    def test_union_and_counts(self):
        sea = np.zeros((2, 3), bool); sea[:, 2] = True
        wc = np.zeros((2, 3), bool); wc[0, 0] = True; wc[1, 2] = True
        ex, st = EX.union_exclusion(sea, wc, cell_km2=1.0)
        self.assertEqual(int(ex.sum()), 3)
        self.assertEqual((st["open_sea_cells"], st["wc80_cells"], st["wc80_land_cells"], st["union_cells"]), (2, 2, 1, 3))
        self.assertEqual(st["union_km2"], 3.0)


if __name__ == "__main__":
    unittest.main()
