"""F4 (CODE-10): `rain_source` may select the IMERG product (declared deviation for EMSR933:
Final V07 does not exist yet for Oct 2026, so the Late Run is used). The string form stays valid
and keeps the Final-run behaviour byte-for-byte:

    rain_source: imerg_half_hourly                      # unchanged -> Final
    rain_source: {name: imerg_half_hourly, product: late}

Run:  python -m unittest discover -s tests -v   (from the repo root, sfincs-viz env)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

from _common import EventCfg  # noqa: E402
import download_imerg  # noqa: E402


def _cfg(extra: dict) -> EventCfg:
    raw = {"event": {"id": "EMSR933", "name": "Crete", "date": "2026-10-01"},
           "bbox": {"west": 23.4, "south": 34.8, "east": 26.4, "north": 35.7},
           "crs": {"epsg": 32634},
           "paths": {"work_dir": "D:/tmp/x", "deliverable_dir": "D:/tmp/x/deliverable"}}
    raw.update(extra)
    return EventCfg(raw=raw, config_path=Path("x.yaml"))


class RainSourceProduct(unittest.TestCase):
    def test_default_rain_source_is_still_era5(self):
        self.assertEqual(_cfg({}).rain_source, "era5_hourly")

    def test_string_form_unchanged_and_product_defaults_to_final(self):
        c = _cfg({"rain_source": "imerg_half_hourly"})
        self.assertEqual(c.rain_source, "imerg_half_hourly")
        self.assertEqual(c.imerg_product, "final")

    def test_mapping_form_selects_late_run(self):
        c = _cfg({"rain_source": {"name": "imerg_half_hourly", "product": "late"}})
        self.assertEqual(c.rain_source, "imerg_half_hourly")
        self.assertEqual(c.imerg_product, "late")

    def test_unknown_product_is_rejected(self):
        with self.assertRaises(ValueError):
            _cfg({"rain_source": {"name": "imerg_half_hourly", "product": "early"}}).imerg_product


class ImergProductCatalogue(unittest.TestCase):
    def test_short_names_per_product(self):
        self.assertEqual(download_imerg.IMERG_PRODUCTS["final"]["short_name"], "GPM_3IMERGHH")
        self.assertEqual(download_imerg.IMERG_PRODUCTS["late"]["short_name"], "GPM_3IMERGHHL")

    def test_labels_name_the_run(self):
        self.assertIn("Final", download_imerg.IMERG_PRODUCTS["final"]["label"])
        self.assertIn("Late", download_imerg.IMERG_PRODUCTS["late"]["label"])


if __name__ == "__main__":
    unittest.main()
