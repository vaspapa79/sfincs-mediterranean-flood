"""Phase 2 (2026-10-19) — the pipeline's step 06b passes the R2 watershed box to bias_correct_imerg.py on the command
line. For a western-hemisphere box ("-0.75,39.33,-0.30,39.55", EMSR773 Valencia) argparse read the value as an
option ("expected one argument") and the first pipeline-native Valencia run stopped at step 06b. The published runs
are not affected (Mandra/Pineios boxes are east of Greenwich; the published Valencia 164-mm output was a scaled copy,
not a pipeline run). Run: python -m unittest tests.test_bias_correct_cli -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

import bias_correct_imerg  # noqa: E402
import run_pipeline  # noqa: E402

BC = {"enabled": True, "target_mm": 164.0, "watershed_bbox": "-0.75,39.33,-0.3,39.55",
      "event_start": "2024-10-29 00:00", "event_end": "2024-10-30 00:00"}


class BiasCorrectCommand(unittest.TestCase):
    def _parse(self, bc):
        cmd = run_pipeline.bias_correct_cmd("python", Path("cfg.yaml"), bc)
        args, rest = bias_correct_imerg.build_parser().parse_known_args(cmd[2:])
        return cmd, args, rest

    def test_negative_longitude_box_reaches_the_script_intact(self):
        _, args, rest = self._parse(BC)
        self.assertEqual(args.watershed_bbox, "-0.75,39.33,-0.3,39.55")
        self.assertEqual(rest, [])

    def test_all_values_pass_through(self):
        _, args, _ = self._parse(BC)
        self.assertEqual((args.target_mm, args.event_start, args.event_end, args.config),
                         (164.0, "2024-10-29 00:00", "2024-10-30 00:00", Path("cfg.yaml")))

    def test_positive_box_is_unchanged(self):
        bc = dict(BC, watershed_bbox="23.40,38.05,23.55,38.15", target_mm=200.0)
        _, args, _ = self._parse(bc)
        self.assertEqual(args.watershed_bbox, "23.40,38.05,23.55,38.15")
        self.assertEqual(args.target_mm, 200.0)


if __name__ == "__main__":
    unittest.main()
