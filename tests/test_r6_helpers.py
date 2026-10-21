"""CODE-16: helpers of the manuscript-table generator (reproduction/r6/scripts/r6_tables.py) and of the anonymity dry run
(reproduction/r6/scripts/anonymity_grep.py) — formatting rules, release-name mapping, record-label stripping, the patterns."""
import struct
import sys
import unittest
import zlib
from pathlib import Path

R6 = Path(__file__).resolve().parents[1] / "reproduction" / "r6" / "scripts"
sys.path.insert(0, str(R6))
import anonymity_grep as AG  # noqa: E402
import r6_tables as T  # noqa: E402


class Formatting(unittest.TestCase):
    def test_score_and_bias_decimals(self):
        self.assertEqual(T.f3(0.49591), "0.496")
        self.assertEqual(T.f2(1.7154), "1.72")
        self.assertEqual(T.f1(4506.6825), "4506.7")
        self.assertEqual(T.f0(223703.0), "223703")

    def test_signed_deltas(self):
        self.assertEqual(T.s3(0.0234), "+0.023")
        self.assertEqual(T.s3(-0.0466), "-0.047")
        self.assertEqual(T.s2(0.329), "+0.33")

    def test_missing_and_nan_become_dash(self):
        self.assertEqual(T.f3(None), T.NA)
        self.assertEqual(T.f1(float("nan")), T.NA)

    def test_numeric_text_is_formatted_other_text_passes(self):
        self.assertEqual(T.f1("681.8000000000001"), "681.8")
        self.assertEqual(T.f0("811"), "811")
        self.assertEqual(T.f3("not defined"), "not defined")

    def test_bracket_keeps_release_value_only_when_present(self):
        self.assertEqual(T.bracket("0.496", "0.456"), "0.496 [0.456]")
        self.assertEqual(T.bracket("0.221", None), "0.221")
        self.assertEqual(T.bracket("0.221", T.NA), "0.221")


class ReleaseMapping(unittest.TestCase):
    def test_v14x_suffix_and_post_d6_label_map_to_the_release_run(self):
        self.assertEqual(T.release_base("strymonas_enhanced_postD6_v142"), "strymonas_enhanced")
        self.assertEqual(T.release_base("pineios_r2_220_v142"), "pineios_r2_220")
        self.assertEqual(T.release_base("pineios_enhanced_v141"), "pineios_enhanced")
        self.assertEqual(T.release_base("mandra_enhanced"), "mandra_enhanced")

    def test_base_of_keeps_post_d6(self):
        self.assertEqual(T.base_of("strymonas_enhanced_postD6_v142"), "strymonas_enhanced_postD6")


class _Ctx:
    def __init__(self, label):
        self.label = label

    def res(self, run, kind="v14_newmask", required=True):
        return {"label": self.label}


class RunLabel(unittest.TestCase):
    def test_rerun_prefix_is_removed(self):
        lab = "v1.4.2 (D8 source-point resolution) re-run of strymonas_leadin7d: sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN on"
        self.assertEqual(T.run_label(_Ctx(lab), "x"), "sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN on")

    def test_supplement_row_prefix_is_removed(self):
        self.assertEqual(T.run_label(_Ctx("S1 row 1: HSG-A AMC-II (CN = 15 test) — pervious classes CN 15"), "x"), "HSG-A AMC-II (CN = 15 test) — pervious classes CN 15")
        self.assertEqual(T.run_label(_Ctx("S1 prose: Manning test, built-up n 0.012 -> 0.080"), "x"), "Manning test, built-up n 0.012 -> 0.080")


def _pattern(cls):
    return next(rx for c, rx, _s in AG.CLASSES if c == cls)


class AnonymityPatterns(unittest.TestCase):
    def test_email_needs_a_letter_tld_not_a_threshold(self):
        rx = _pattern("e-mail addresses")
        self.assertTrue(rx.search("remote git@github.com:owner/repo"))
        self.assertTrue(rx.search("contact a.b-c@example.org today"))
        self.assertFalse(rx.search("printed strict@0.10m CSI"))
        self.assertFalse(rx.search("CSI@0.10 and B@0.50"))

    def test_echo_and_iti_are_case_sensitive_tokens(self):
        self.assertTrue(_pattern("ECHO").search("cite DG ECHO GA"))
        self.assertFalse(_pattern("ECHO").search('echo "done"'))
        self.assertTrue(_pattern("affiliation: ITI").search("CERTH-ITI"))
        self.assertFalse(_pattern("affiliation: ITI").search("utility"))

    def test_greek_names_match_without_accents(self):
        rx = _pattern("author names (Greek)")
        self.assertTrue(rx.search(AG.strip_accents("ο Παπαϊωάννου έγραψε").lower()))

    def test_png_text_chunks_are_read(self):
        def chunk(typ, body):
            return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)) + chunk(b"tEXt", b"Author\x00Someone") + chunk(b"IEND", b"")
        self.assertEqual(AG.png_text(png), ["Author: Someone"])


if __name__ == "__main__":
    unittest.main()
