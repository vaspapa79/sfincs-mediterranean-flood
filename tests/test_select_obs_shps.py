"""F2 (CODE-10): observed-flood shapefile selection and the EMS portal's non-monitoring
delineation package `<EMSR>_AOInn_DEL_PRODUCT_v1`.

The published five-event numbers were scored WITHOUT DEL_PRODUCT observed-flood layers (the
patterns never matched them; the canonical EMSR664 8-AOI truth directory contains one). To keep
those numbers byte-identical, inclusion is an explicit per-event switch, `ems.include_del_product`
(default off), set only for EMSR933 where the first Tzermiado delineation is a DEL_PRODUCT.

Run:  python -m unittest discover -s tests -v   (from the repo root, sfincs-viz env)
"""
from __future__ import annotations

import fnmatch
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
sys.path.insert(0, str(REPO / "validation"))

import validate_event_v2 as v2  # noqa: E402
import download_ems  # noqa: E402

DP = "EMSR933_AOI03_DEL_PRODUCT_v1/EMSR933_AOI03_DEL_PRODUCT_observedEventA_v1.shp"
DM = "EMSR933_AOI03_DEL_MONIT02_v1/EMSR933_AOI03_DEL_MONIT02_observedEventA_v1.shp"
GP = "EMSR933_AOI03_GRA_PRODUCT_v1/EMSR933_AOI03_GRA_PRODUCT_observedEventA_v1.shp"


def _touch(root: Path, rel: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"")
    return p


class SelectObsShpsPublishedBehaviour(unittest.TestCase):
    """Guards rule 5: with the switch off, DEL_PRODUCT layers stay invisible (as for EMSR664)."""

    def test_del_product_ignored_by_default_next_to_monitoring_and_grading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _touch(root, DP)
            dm = _touch(root, DM)
            _touch(root, GP)
            self.assertEqual(v2._select_obs_shps(root), [dm])

    def test_del_product_alone_ignored_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _touch(root, DP)
            self.assertEqual(v2._select_obs_shps(root), [])


class SelectObsShpsOptIn(unittest.TestCase):
    def test_opt_in_selects_del_product_as_delineation_and_beats_grading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dp = _touch(root, DP)
            dm = _touch(root, DM)
            _touch(root, GP)
            self.assertEqual(v2._select_obs_shps(root, include_del_product=True), sorted([dp, dm]))

    def test_opt_in_del_product_alone_is_selected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            dp = _touch(root, DP)
            self.assertEqual(v2._select_obs_shps(root, include_del_product=True), [dp])

    def test_grading_only_aoi_unaffected_by_switch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gp = _touch(root, "EMSR664_AOI02_GRA_PRODUCT_v1/EMSR664_AOI02_GRA_PRODUCT_observedEventA_v1.shp")
            self.assertEqual(v2._select_obs_shps(root), [gp])
            self.assertEqual(v2._select_obs_shps(root, include_del_product=True), [gp])


class DownloadEmsMergePatterns(unittest.TestCase):
    NAME = "EMSR933_AOI03_DEL_PRODUCT_observedEventA_v1.shp"

    def test_published_patterns_do_not_match_del_product(self):
        pats = download_ems.obs_shp_patterns(include_del_product=False)
        self.assertFalse(any(fnmatch.fnmatch(self.NAME, p) for p in pats))

    def test_opt_in_patterns_match_del_product(self):
        pats = download_ems.obs_shp_patterns(include_del_product=True)
        self.assertTrue(any(fnmatch.fnmatch(self.NAME, p) for p in pats))

    def test_published_patterns_still_match_monitoring_and_grading(self):
        pats = download_ems.obs_shp_patterns(include_del_product=False)
        for name in ("EMSR773_AOI01_DEL_MONIT01_observedEventA_v1.shp",
                     "EMSR664_AOI02_GRA_PRODUCT_observedEventA_v1.shp"):
            self.assertTrue(any(fnmatch.fnmatch(name, p) for p in pats), name)


if __name__ == "__main__":
    unittest.main()
