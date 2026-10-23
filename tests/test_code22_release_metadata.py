"""CODE-22: the commit map of the history rewrite of 2026-10-23 and the published texts that use it — the hash mapper, the
fix-commit columns of the release-history table, the changelog heading of the re-created release tag, the Zenodo metadata
file, the side commit that carries the release metadata, and the classification of the remaining pre-rewrite hashes.
Data-driven: no pre-rewrite hash and no defect label is written into this file (the release-history generator scans the
tests for defect labels, and the grep check counts pre-rewrite hashes in the tracked tree)."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "reproduction" / "r6" / "scripts", ROOT / "reproduction" / "v14_rerun" / "scripts"):
    sys.path.insert(0, str(p))
import commit_map as CM  # noqa: E402
import release_docs as RD  # noqa: E402

CONCEPT = "10.5281/zenodo.20523154"
RECORD = ROOT / "reproduction" / "v14_rerun" / "code22" / "zenodo_record_21488879.json"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, encoding="utf-8").stdout.strip()


class CommitMap(unittest.TestCase):
    def test_the_rewrite_record_maps_34_commits_to_commits_of_this_repository(self):
        cmap = CM.load_map(ROOT)
        self.assertEqual(len(cmap), 34)
        for new in cmap.values():
            self.assertEqual(git(ROOT, "cat-file", "-t", new), "commit")

    def test_resolve_keeps_the_length_of_the_hash_it_is_given(self):
        cmap = CM.load_map(ROOT)
        old, new = sorted(cmap.items())[0]
        self.assertEqual(CM.resolve(old[:7], cmap), new[:7])
        self.assertEqual(CM.resolve(old, cmap), new)
        self.assertIsNone(CM.resolve(new[:7], cmap))          # a published hash is not a pre-rewrite hash


class MapText(unittest.TestCase):
    OLD = "1234567" + "0" * 33
    NEW = "abcdef1" + "1" * 33

    def test_abbreviated_and_full_hashes_are_replaced(self):
        text = f"fix `{self.OLD[:7]}`; full {self.OLD}; again {self.OLD[:9]}."
        out, reps = CM.map_text(text, {self.OLD: self.NEW})
        self.assertEqual(out, f"fix `{self.NEW[:7]}`; full {self.NEW}; again {self.NEW[:9]}.")
        self.assertEqual(reps, [(self.OLD[:7], self.NEW[:7]), (self.OLD, self.NEW), (self.OLD[:9], self.NEW[:9])])

    def test_longer_hex_runs_and_unrelated_hashes_are_left_alone(self):
        sha256 = self.OLD[:7] + "f" * 57                         # a 64-hex digest that starts like the old hash
        text = f"sha256 {sha256}; other commit 7654321; prefix e{self.OLD[:7]}"
        out, reps = CM.map_text(text, {self.OLD: self.NEW})
        self.assertEqual(out, text)
        self.assertEqual(reps, [])


class ReleaseHistoryColumns(unittest.TestCase):
    def test_csv_carries_published_and_pre_rewrite_fix_commits(self):
        cmap = CM.load_map(ROOT)
        with open(ROOT / "reproduction" / "r6" / "tables" / "S10.csv", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        new7 = {n[:7] for n in cmap.values()}
        n_fix = 0
        for r in rows:
            if r["fix commit"] in ("", "—"):
                self.assertEqual(r["pre-rewrite fix commit"], "—")
                continue
            n_fix += 1
            self.assertIn(r["fix commit"], new7)
            self.assertEqual(CM.resolve(r["pre-rewrite fix commit"], cmap), r["fix commit"])
        self.assertEqual(n_fix, 7)
        self.assertEqual(list(rows[0])[-1], "pre-rewrite fix commit")

    def test_markdown_has_no_pre_rewrite_column_and_no_pre_rewrite_hash(self):
        md = (ROOT / "reproduction" / "r6" / "tables" / "S10.md").read_text(encoding="utf-8")
        self.assertNotIn("pre-rewrite fix commit", md.split("\n|---")[0])
        self.assertEqual(CM.map_text(md, CM.load_map(ROOT))[1], [])


class PublishedTexts(unittest.TestCase):
    FILES = ["CHANGELOG.md", "README.md", "reproduction/r6/README_REVIEW.md", "reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md",
             "reproduction/r6/tables/S10.md", ".zenodo.json", "CITATION.cff", "reproduction/r6/scripts/release_docs.py"]

    def test_no_pre_rewrite_hash_left_in_the_published_texts(self):
        cmap = CM.load_map(ROOT)
        for f in self.FILES:
            self.assertEqual(CM.map_text((ROOT / f).read_text(encoding="utf-8"), cmap)[1], [], f)


class ReleaseHeading(unittest.TestCase):
    def test_heading_of_a_tag_recreated_on_a_release_metadata_commit(self):
        self.assertEqual(RD.release_heading("v1.4.2", "2026-10-23", "779a8e0", "2026-10-20"),
                         "## v1.4.2 — 2026-10-23 (tag `v1.4.2` → the release-metadata commit on top of the number-freeze commit `779a8e0` of 2026-10-20)")

    def test_citation_date_is_the_date_of_the_recreated_tag(self):
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn('version: "1.4.2"', cff)
        self.assertIn(f"date-released: {RD.RETAGGED['v1.4.2']}", cff)


class ZenodoJson(unittest.TestCase):
    def test_metadata_copies_the_creators_and_points_at_the_concept_record(self):
        rec = json.loads(RECORD.read_text(encoding="utf-8"))
        z = RD.zenodo_json(ROOT, rec)
        self.assertEqual(z["creators"], [{k: c[k] for k in ("name", "affiliation", "orcid") if k in c} for c in rec["metadata"]["creators"]])
        self.assertEqual(len(z["creators"]), 7)
        self.assertEqual(z["version"], "1.4.2")
        self.assertEqual((z["upload_type"], z["license"], z["access_right"]), ("software", "mit", "open"))
        self.assertIn({"identifier": CONCEPT, "relation": "isVersionOf", "resource_type": "software", "scheme": "doi"}, z["related_identifiers"])
        self.assertEqual(z["keywords"], rec["metadata"]["keywords"])
        self.assertTrue(z["description"].startswith("<p>"))

    def test_committed_file_is_the_generated_one(self):
        rec = json.loads(RECORD.read_text(encoding="utf-8"))
        self.assertEqual(json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8")), RD.zenodo_json(ROOT, rec))


class SideCommit(unittest.TestCase):
    def test_side_commit_differs_from_its_base_by_the_listed_files_only(self):
        import code22_release_commit as RC
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            git(r, "init", "-q")
            git(r, "config", "user.name", "Test"); git(r, "config", "user.email", "test@example.invalid")
            (r / "a.txt").write_text("a0\n"); (r / "c.txt").write_text("c0\n")
            git(r, "add", "-A"); git(r, "commit", "-q", "-m", "base")
            base = git(r, "rev-parse", "HEAD")
            (r / "a.txt").write_text("a1\n"); (r / "b.txt").write_text("b1\n"); (r / "c.txt").write_text("c1\n")
            git(r, "add", "-A"); git(r, "commit", "-q", "-m", "later")
            side = RC.build_side_commit(r, base, "HEAD", ["a.txt", "b.txt"], "side commit\n")
            self.assertEqual(git(r, "rev-parse", f"{side}^"), base)
            self.assertEqual(sorted(git(r, "diff", "--name-only", base, side).split()), ["a.txt", "b.txt"])
            self.assertEqual(git(r, "show", f"{side}:a.txt"), "a1")
            self.assertEqual(git(r, "show", f"{side}:c.txt"), "c0")
            self.assertEqual(git(r, "status", "--porcelain"), "")        # the working tree and the index are untouched


class GrepCategories(unittest.TestCase):
    def test_categories_of_the_files_that_may_still_quote_pre_rewrite_hashes(self):
        import code22_grep_check as G
        self.assertEqual(G.category("docs/COMMIT_MAP_2026-10-23.md"), "commit map")
        self.assertEqual(G.category("docs/AUDIT.md"), "audit trail (entries before the rewrite)")
        self.assertEqual(G.category("reproduction/r6/tables/S10.csv"), "S10.csv pre-rewrite column (by design)")
        self.assertEqual(G.category("reproduction/v14_rerun/code21/history_rewrite.json"), "rewrite record (source of the map)")
        self.assertEqual(G.category("reproduction/v14_rerun/results/x_record.json"), "dated record")
        self.assertEqual(G.category("reproduction/v14_rerun/CHECKPOINT7.md"), "dated record")
        self.assertEqual(G.category("CHANGELOG.md"), "other")


if __name__ == "__main__":
    unittest.main()
