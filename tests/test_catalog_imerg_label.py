"""F4 follow-up (CODE-10): the data-catalog entry written by prep_inputs.py must name the IMERG
product that was actually downloaded (Final vs Late), while the Final string stays byte-identical.

Run:  python -m unittest discover -s tests -v   (from the repo root, sfincs-viz env)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

from _common import EventCfg  # noqa: E402
import prep_inputs  # noqa: E402


def _cfg(rain_source) -> EventCfg:
    raw = {"event": {"id": "EMSR933", "name": "Crete", "slug": "crete", "date": "2026-10-01"},
           "window": {"spinup_days": 7, "pre_event_days": 3, "post_event_days": 4},
           "bbox": {"west": 23.4, "south": 34.8, "east": 26.4, "north": 35.7},
           "crs": {"epsg": 32634},
           "paths": {"work_dir": "D:/tmp/crete", "deliverable_dir": "D:/tmp/crete/deliverable"},
           "rain_source": rain_source}
    return EventCfg(raw=raw, config_path=Path("x.yaml"))


class CatalogImergLabel(unittest.TestCase):
    def test_final_string_form_keeps_published_label(self):
        txt = prep_inputs.render_catalog(_cfg("imerg_half_hourly"))
        self.assertIn("GPM IMERG Final V07 half-hourly (September 28 2026 - October 06 2026, 0.1 deg)", txt)

    def test_late_mapping_form_names_the_late_run(self):
        txt = prep_inputs.render_catalog(_cfg({"name": "imerg_half_hourly", "product": "late"}))
        self.assertIn("GPM IMERG Late Run V07 half-hourly", txt)
        self.assertNotIn("Final V07 half-hourly", txt)

    def test_paths_follow_slug_and_data_root(self):
        txt = prep_inputs.render_catalog(_cfg("imerg_half_hourly"))
        self.assertIn("path: imerg_crete.nc", txt)
        self.assertIn("root: D:/tmp/crete/data", txt)


if __name__ == "__main__":
    unittest.main()
