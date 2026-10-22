"""CODE-17 (push preparation): the directory mode of the anonymity scanner, the review-archive scrub rules, the D9 line of
the CHANGELOG generator and the centre-point burning helper of the any-touched check."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reproduction" / "r6" / "scripts"))
sys.path.insert(0, str(ROOT / "reproduction" / "v14_rerun" / "scripts"))
import anonymity_grep as AG  # noqa: E402
import build_review_archive as BRA  # noqa: E402
import c6_alltouched_inflation as C6  # noqa: E402
import release_docs as RD  # noqa: E402


class ScannerTreeMode(unittest.TestCase):
    def test_scan_tree_finds_planted_strings_and_reports_zero_on_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "a.md").write_text("written by Papaioannou at CERTH\n", encoding="utf-8")
            (d / "b.json").write_text(json.dumps({"path": "C:/Users/vaspapa/Desktop/x"}), encoding="utf-8")
            (d / "c.txt").write_text("nothing here\n", encoding="utf-8")
            hits, scanned = AG.scan_tree(d)
            classes = {h["class"] for h in hits}
            self.assertIn("author names", classes)
            self.assertIn("affiliation: CERTH", classes)
            self.assertIn("vaspapa", classes)
            self.assertEqual(scanned["text"], 3)
            hits2, _ = AG.scan_tree(d, only=["c.txt"])
            self.assertEqual(hits2, [])


class ArchiveScrub(unittest.TestCase):
    def test_repository_url_and_our_dois_get_the_brief_placeholders(self):
        s = "see https://github.com/vaspapa79/sfincs-mediterranean-flood/tree/v1.3.0 and 10.5281/zenodo.20523154 (also 10.5281/zenodo.21488879)"
        out, n = BRA.scrub_text(s)
        self.assertNotIn("vaspapa79", out)
        self.assertIn("[repository withheld for review]", out)
        self.assertEqual(out.count("[DOI withheld for review]"), 2)
        self.assertGreater(sum(n.values()), 0)

    def test_machine_paths_become_relative(self):
        s = r"C:/Users/vaspapa/Desktop/ELKAK/implementation/x/model and D:\ELKAK\implementation\v14\run\model\sfincs_map.nc"
        out, _ = BRA.scrub_text(s)
        self.assertEqual(out, "implementation/x/model and implementation/v14/run/model/sfincs_map.nc")

    def test_names_affiliation_grant_and_funder(self):
        s = "Valsamis (DvS) and V. Papaioannou, CERTH-ITI, ECHO GA 101225575, dvalsamis@example.org"
        out, _ = BRA.scrub_text(s)
        for bad in ("Valsamis", "Papaioannou", "DvS", "CERTH", "ITI", "ECHO", "101225575", "dvalsamis@"):
            self.assertNotIn(bad, out, bad)

    def test_cited_work_metadata_is_left_alone(self):
        s = "author ORCID 0000-0002-1234-5678, github.com/Deltares/SFINCS, 10.5281/zenodo.7254221"
        out, _ = BRA.scrub_text(s)
        self.assertEqual(out, s)


class ChangelogD9(unittest.TestCase):
    def test_d9_line_reads_offsets_from_the_residuals_record(self):
        line = RD.d9_line(ROOT)
        self.assertTrue(line.startswith("- **D9**"))
        for frag in ("Trikala", "3.76", "Titarisios", "10.95", "documented, not fixed"):
            self.assertIn(frag, line)


class CentrePointBurning(unittest.TestCase):
    def test_thin_polygon_touches_more_cells_than_it_centres(self):
        from shapely.geometry import box
        x, y = np.meshgrid(np.arange(5) * 10.0 + 5.0, np.arange(4) * 10.0 + 5.0)   # 10 m cells, centres at 5, 15, ...
        s = {"x": x, "y": y, "dx": 10.0, "dy": 10.0}
        thin = box(12.0, 12.0, 38.0, 18.0)           # one row high: centres (15,15), (25,15), (35,15) inside; touches the same 3 columns
        touched, centre = C6.burn([thin], s, True), C6.burn([thin], s, False)
        self.assertEqual(int(touched.sum()), 3)
        self.assertEqual(int(centre.sum()), 3)
        sliver = box(12.0, 17.0, 38.0, 23.0)         # straddles the row boundary at 20 m: touches 6 cells, no centre inside
        self.assertEqual(int(C6.burn([sliver], s, True).sum()), 6)
        self.assertEqual(int(C6.burn([sliver], s, False).sum()), 0)


if __name__ == "__main__":
    unittest.main()
