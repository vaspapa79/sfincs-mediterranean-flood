"""Phase 4e (GO Phases 3-5, 2026-10-19) — NUMBER_MAP.md: every number of the NHESS R5 manuscript and supplement that the
harness-v1.4 re-run changes, as "table / figure / sentence -> old -> new -> source JSON". The rewrite is done from this file.

Old values are read from the R5 text extracted with scripts/extract_docx.py (tables parsed into *_tables.json), never
retyped; new values are read from the v1.4 JSON records. Sentence numbers are located by regex in the extracted text
(line numbers given). Entries whose new value is not available yet print "pending" with the run that will produce it.
Usage: python -I number_map.py --repo <worktree> --r5-dir <dir with manuscript_R5_tables.json, supplement_R5_tables.json, *.txt> [--out NUMBER_MAP.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

THR_ROWS = [("hmax > 0.05 m", "h>0.05m"), ("hmax > 0.10 m", "h>0.10m"), ("hmax > 0.25 m", "h>0.25m"), ("hmax > 0.50 m", "h>0.50m")]
ENH = {"Mandra": "mandra_enhanced", "Strymonas": "strymonas_enhanced_postD6", "Pineios": "pineios_enhanced", "Valencia": "valencia_enhanced_164", "Emilia-R.": "emilia_enhanced_8aoi"}
BASE = {"Mandra": "mandra_baseline", "Strymonas": "strymonas_baseline", "Pineios": "pineios_baseline_gridmatched"}


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


class Src:
    """Lazy access to the v1.4 records with provenance strings."""

    def __init__(self, repo: Path):
        self.R = repo / "reproduction" / "v14_rerun"; self.res = self.R / "results"; self.P4 = self.R / "phase4"
        self.cache = {}

    def v14(self, run):
        p = self.res / f"{run}_v14_newmask.json"
        if p not in self.cache:
            self.cache[p] = J(p)
        return self.cache[p], f"results/{run}_v14_newmask.json"

    def strict(self, run, key="h>0.10m"):
        v, src = self.v14(run)
        return (v["validation"]["strict_threshold_sweep"][key] if v else None), src + f" strict_threshold_sweep[{key}]"

    def fuzzy(self, run, r=1):
        v, src = self.v14(run)
        return (v["validation"]["fuzzy_at_h_gt_0p10m"][f"r={r}"] if v else None), src + f" fuzzy_at_h_gt_0p10m[r={r}]"

    def aoi(self, run, token):
        v, src = self.v14(run)
        if not v:
            return None, src
        for a in v["validation"]["per_aoi_canonical_and_r1"]:
            if token in a["aoi_file"]:
                return a, src + f" per_aoi[{token}]"
        return None, src

    def skill(self, run):
        v, src = self.v14(run)
        if not v:
            return None, src
        sys.path.insert(0, str(self.R.parents[1] / "validation"))
        import skill_scores as ss
        s = v["validation"]["strict_threshold_sweep"]["h>0.10m"]
        return ss.skill_scores(s["tp"], s["fp"], s["fn"], s["tn"]), src + " (skill_scores.py)"

    def csi_star(self, run):
        v, src = self.v14(run)
        if not v:
            return None, src
        sw = v["validation"]["strict_threshold_sweep"]
        k = max(sw, key=lambda kk: sw[kk]["csi"])
        return {"threshold": k, "csi": sw[k]["csi"], "bias": sw[k]["bias"]}, src + " max over the sweep"

    def wet_km2(self, run):
        v, src = self.v14(run)
        if not v:
            return None, src
        s = v["validation"]["strict_threshold_sweep"]["h>0.10m"]; A = v["validation"]["tolerance_radius_m_at_r1"] ** 2 / 1e6
        return (s["tp"] + s["fp"]) * A, src + " (TP+FP) x cell area"

    def record(self, run):
        return J(self.res / f"{run}_record.json"), f"results/{run}_record.json"

    def rain(self, run):
        p = self.P4 / "rain" / f"{run}_v14.json"
        return J(p), f"phase4/rain/{run}_v14.json"

    def buffer(self, run):
        p = self.P4 / "truth_buffer" / f"{run}_v14.json"
        return J(p), f"phase4/truth_buffer/{run}_v14.json"

    def rebuild_q(self, run):
        p = self.res / f"{run}_rebuild_q.json"
        return J(p), f"results/{run}_rebuild_q.json"

    def map_csv(self, run):
        p = self.P4 / "figures" / f"map_{run}_v14.csv"
        if not p.exists():
            return None, f"phase4/figures/map_{run}_v14.csv"
        import csv
        return list(csv.DictReader(open(p, encoding="utf-8"))), f"phase4/figures/map_{run}_v14.csv"


def fmt(x, nd=3):
    if x is None:
        return "pending"
    if isinstance(x, str):
        return x
    return f"{x:.{nd}f}"


def table(tabs, tid):
    return next((t for t in tabs if t["id"] == tid), None)


def row(t, label_token, col_index):
    if not t:
        return None
    for r in t["rows"]:
        if r and label_token in r[0]:
            return r[col_index] if col_index < len(r) else None
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--r5-dir", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    S = Src(a.repo)
    man = J(a.r5_dir / "manuscript_R5_tables.json"); sup = J(a.r5_dir / "supplement_R5_tables.json")
    text = (a.r5_dir / "manuscript_R5.txt").read_text(encoding="utf-8").splitlines()
    stext = (a.r5_dir / "supplement_R5.txt").read_text(encoding="utf-8").splitlines()
    E = []   # entries: (location, old, new, source, note)

    def add(loc, old, new, src, note=""):
        cell = lambda v: str(v).replace(" | ", " / ").replace("|", "/")      # keep the markdown table intact  # noqa: E731
        E.append((cell(loc), cell(old), cell(new), src, cell(note)))

    # ---- Tables 3, 5, 7: threshold sweeps (TP FP FN CSI HR FAR)
    for tid, ev in (("Table 3", "Pineios"), ("Table 5", "Mandra"), ("Table 7", "Strymonas")):
        t = table(man, tid)
        for lab, key in THR_ROWS:
            s, src = S.strict(ENH[ev], key)
            old = next((r for r in (t["rows"] if t else []) if r and lab in r[0]), None)
            if old:
                add(f"{tid} ({ev}) row {lab}", " / ".join(old[1:7]), (f"{s['tp']} / {s['fp']} / {s['fn']} / {s['csi']:.3f} / {s['hr']:.3f} / {s['far']:.3f}" if s else "pending"), src, "TP / FP / FN / CSI / HR / FAR")
    # ---- Table 4 Pineios per AOI, Table 8 Strymonas per AOI (3 runs), Table 6 Mandra fuzzy
    t = table(man, "Table 4")
    if t:
        for r in t["rows"][1:]:
            tok = r[0].split()[0] if r and r[0] else ""
            if not tok or tok.lower() in ("aoi", "area", "union", "all"):
                continue
            aoi, src = S.aoi(ENH["Pineios"], tok.upper())
            add(f"Table 4 (Pineios per AOI) row {r[0]}", " | ".join(r[1:]), (f"active {aoi['active_km2']:.0f} km², obs {aoi['ems_wet_km2_strict']:.0f} km², TP {aoi['strict']['tp']}, CSI {aoi['strict']['csi']:.3f} HR {aoi['strict']['hr']:.3f} FAR {aoi['strict']['far']:.3f}; fuzzy r=1 CSI {aoi['fuzzy_r1']['csi']:.3f}" if aoi else "pending/AOI token not matched"), src,
                "Active / EMS wet (km²) / TP / CSI / HR / FAR; the v1.4 universe excludes WorldCover 80 and open sea")
    t = table(man, "Table 6")
    if t:
        for r in t["rows"][1:]:
            m = re.search(r"r\s*=\s*(\d)", r[0])
            if m:
                fzz, src = S.fuzzy(ENH["Mandra"], int(m.group(1)))
                add(f"Table 6 (Mandra fuzzy) row {r[0]}", " | ".join(r[1:]), (f"TP {fzz['tp']} FP {fzz['fp']} FN {fzz['fn']} CSI {fzz['csi']:.3f} HR {fzz['hr']:.3f} FAR {fzz['far']:.3f} F2 {fzz['f2']:.3f} GSS {fzz['gss']:.3f}" if fzz else "pending"), src)
    t = table(man, "Table 8")
    if t:
        for r in t["rows"][1:]:
            tok = (r[0].split()[0] if r and r[0] else "").upper()
            if not tok or tok in ("AOI",):
                continue
            outs = []
            for lab, run in (("baseline", "strymonas_baseline"), ("enhanced v1", "strymonas_v1_prefix_src"), ("enhanced v3", "strymonas_enhanced_postD6")):
                aoi, src = S.aoi(run, tok)
                outs.append(f"{lab}: " + (f"CSI {aoi['strict']['csi']:.3f} HR {aoi['strict']['hr']:.3f} FAR {aoi['strict']['far']:.3f}" if aoi else "pending"))
            add(f"Table 8 (Strymonas per AOI) row {r[0]}", " | ".join(r[1:]), "; ".join(outs), "results/strymonas_{baseline,v1_prefix_src,enhanced_postD6}_v14_newmask.json per_aoi")
    # ---- Table 9 / 10 / 14 rows
    t9, t10, t14 = table(man, "Table 9"), table(man, "Table 10"), table(man, "Table 14")
    for ev, run in ENH.items():
        s, src = S.strict(run); fzz, _ = S.fuzzy(run)
        o = next((r for r in (t9["rows"] if t9 else []) if r and r[0].startswith(ev)), None)
        if o:
            add(f"Table 9 row {ev}", " | ".join(o[2:]), (f"{s['csi']:.3f} | {s['hr']:.3f} | {s['far']:.3f} | {s['bias']:.2f} | {s['gss']:.3f} | fuzzy r=1 {fzz['csi']:.3f} | {fzz['hr']:.3f} | {fzz['far']:.3f}" if s else "pending"), src,
                "strict CSI HR FAR B GSS | fuzzy r=1 CSI HR FAR; Valencia/Emilia printed B/GSS 12.15/0.021 and 4.98/0.055 are the superseded 350-mm / Forlì-only values (MANIFEST §5)")
        o = next((r for r in (t10["rows"] if t10 else []) if r and r[0].startswith(ev)), None)
        if o:
            b = BASE.get(ev)
            bs, bsrc = (S.strict(b) if b else (None, ""))
            new = (f"{s['csi']:.3f} | {s['hr']:.3f} | {s['far']:.3f}" if s else "pending") + (f" | Δ {s['csi'] - bs['csi']:+.3f} | {s['hr'] - bs['hr']:+.3f} | {s['far'] - bs['far']:+.3f}" if (s and bs) else (" | — | — | —" if not b else " | Δ pending"))
            add(f"Table 10 row {ev}", " | ".join(o[1:]), new, src + (f"; baseline {bsrc}" if b else ""), "enhanced CSI HR FAR | Δ vs the same-harness baseline (v1.4 both)")
        o = next((r for r in (t14["rows"] if t14 else []) if r and r[0].startswith(ev)), None)
        if o:
            k, ksrc = S.skill(run); cs, _ = S.csi_star(run)
            add(f"Table 14 row {ev}", " | ".join(o[1:]), (f"{s['csi']:.3f} | SEDI {k['sedi']:.3f} | PSS {k['pss']:.3f} | B {s['bias']:.2f} | CSI* {cs['csi']:.3f} ({cs['threshold']}) | B* {cs['bias']:.2f}" if s else "pending"), ksrc,
                "published Strymonas SEDI/PSS came from the author-reference table (tests/test_skill_scores.py); Emilia PSS printed 0.282 is 0.281 exact; Valencia B* 7.8 is a 350-mm residue")
    # ---- Table 11: this study's rows
    t = table(man, "Table 11")
    if t:
        for r in t["rows"]:
            if r and ("This study" in " ".join(r) or "this study" in " ".join(r)):
                add(f"Table 11 row {r[0]}", " | ".join(r[1:]), "see Table 9/14 entries (CSI per event, CSI* for the peak)", "results/*_v14_newmask.json")
    # ---- Table 12
    t = table(man, "Table 12")
    for lab, run in (("Rain-on-grid baseline", "strymonas_baseline"), ("CN on + Q (canonical", "strymonas_enhanced_postD6"), ("CN off + Q", "strymonas_abl_cnoff_q"), ("CN on + Q off", "strymonas_abl_qoff_cn")):
        o = next((r for r in (t["rows"] if t else []) if r and lab in r[0]), None)
        s, src = S.strict(run)
        if o:
            add(f"Table 12 row {o[0]}", " | ".join(o[1:]), (f"{s['csi']:.3f} | {s['hr']:.3f} | {s['far']:.3f} | {s['bias']:.2f} | {s['gss']:.3f}" if s else "pending"), src)
    # ---- Table 13: the R2 factor line
    t = table(man, "Table 13")
    if t:
        o = next((r for r in t["rows"] if r and r[0].startswith("R2 rain bias")), None)
        rj, rsrc = S.rain("valencia_enhanced_164")
        add("Table 13 row R2 rain bias factor (Valencia)", o[1] if o else "", (f"×{rj['r2_realised']['factor']:.2f} (→ {rj['r2_realised']['target_mm']:g} mm), realised at run time" if rj and rj.get("r2_realised") else "pending (phase4 rain)"), rsrc)
    # ---- Supplement S1 (Mandra CN rows), S2 (v1 vs v3)
    t = table(sup, "Table S1")
    for lab, run in (("CN = 15", "mandra_cn_a15"), ("CN ≈ 58", "mandra_cn_a58"), ("HSG-B AMC-II", "mandra_cn_b_default"), ("HSG-D AMC-III", "mandra_cn_d_amc3"), ("No infiltration", "mandra_enhanced")):
        o = next((r for r in (t["rows"] if t else []) if r and lab in r[0]), None)
        rec, _ = S.record(run); s, src = S.strict(run); aoi, _ = S.aoi(run, "01MANDRA"); wk, _ = S.wet_km2(run)
        cn = (rec or {}).get("cn_realised", {}).get("active_mean_cn", "—")
        if o:
            add(f"Table S1 row {o[0]}", " | ".join(o[1:]), (f"mean CN (active) {cn} | wet {wk:.2f} km² | TP(01MANDRA) {aoi['strict']['tp'] if aoi else 'pending'} | CSI {s['csi']:.3f} | HR {s['hr']:.3f} | FAR {s['far']:.3f}" if s else "pending"), src,
                "relabel the row with the realised mean CN; HSG-A rows recreated with the pervious classes at CN 15 / 58, HSG-D with a TR-55 HSG-D lookup (configs/*.yaml)")
    t = table(sup, "Table S2")
    for ev, v1, v3 in (("Mandra", "mandra_enhanced", None), ("Strymonas", "strymonas_v1_prefix_src", "strymonas_enhanced_postD6"), ("Pineios", "pineios_enhanced", "pineios_timevarying_q")):
        s1, src1 = S.strict(v1); s3, src3 = (S.strict(v3) if v3 else (None, "not recreated (Mandra v3 mask restriction: MANIFEST row 16, not in the Phase-3 list)"))
        add(f"Table S2 {ev} v1 / v3 / Δ", "see supplement", (f"v1 {s1['csi']:.3f}/{s1['hr']:.3f}/{s1['far']:.3f}/{s1['bias']:.2f}/{s1['gss']:.3f}" if s1 else "pending") + (f"; v3 {s3['csi']:.3f}/{s3['hr']:.3f}/{s3['far']:.3f}/{s3['bias']:.2f}/{s3['gss']:.3f}; ΔCSI {s3['csi'] - s1['csi']:+.3f}" if (s1 and s3) else "; v3 " + ("pending" if v3 else src3)),
            f"{src1}; {src3 if v3 else ''}", "CSI/HR/FAR/B/GSS")
    add("Table S3 (evaluation-mask sensitivity ±1 km)", "see supplement", "not regenerated in Phase 4 (not in the Phase-4 list; the mask definition itself changed in v1.4 — regenerate on request with the new mask as the reference)", "—")
    # ---- sentences
    def find(pattern, lines=text, tag="manuscript"):
        hits = [i + 1 for i, ln in enumerate(lines) if re.search(pattern, ln)]
        return f"{tag} lines {hits}" if hits else f"{tag}: not found"

    rp, rps = S.rain("pineios_enhanced"); rm, rms = S.rain("mandra_enhanced")
    bufs = {ev: S.buffer(run) for ev, run in (("Pineios", "pineios_enhanced"), ("Strymonas", "strymonas_enhanced_postD6"), ("Mandra", "mandra_enhanced"))}
    q, qsrc = S.rebuild_q("pineios_timevarying_q")
    cn_on, cn_src = S.wet_km2("pineios_cn_on"); raw_p, raw_src = S.wet_km2("pineios_raw_imerg"); raw_v, raw_vsrc = S.strict("valencia_raw_imerg"); qi, qisrc = S.strict("pineios_qinf5")
    tvq, tvqsrc = S.strict("pineios_timevarying_q")
    mp, mpsrc = S.map_csv("strymonas_enhanced_postD6"); peak_s = next((r for r in (mp or []) if r["aoi_file"] == "WHOLE_ACTIVE_DOMAIN"), None)
    sent = [
        ("§4.1.2 (ii) / §6.2: 'collapsed the flood to ~38 km²' (Pineios CN-on)", "~38 km²", f"{cn_on:.1f} km² wet in the evaluation mask" if cn_on is not None else "pending", cn_src, find(r"38 km")),
        ("§5: 'raw IMERG recovers only 141 mm and bounds the flood below 40 km²'", "141 mm; < 40 km²", (f"raw IMERG bbox mean {rp['sources']['imerg_raw']['by_window']['simulated']['domain_mean_total_mm']:.0f} mm (file extent {rp['sources']['imerg_raw']['by_window_file_extent']['simulated']['domain_mean_total_mm']:.0f} mm) over the simulated window; " if rp and rp['sources'].get('imerg_raw', {}).get('by_window_file_extent') else "rain pending; ") + (f"flood {raw_p:.1f} km²" if raw_p is not None else "flood pending"), f"{rps}; {raw_src}", find(r"141 mm")),
        ("§4.1.2 / Fig. 4 caption: 'ERA5 331 mm domain-mean', '×2.73', 'post-correction 380 mm'", "331 mm; ×2.73; 380 mm", (f"ERA5 bbox mean {rp['sources']['era5']['by_window']['simulated']['domain_mean_total_mm']:.0f} mm; factor ×{rp['r2_realised']['factor']:.2f}; corrected IMERG bbox mean {rp['sources']['imerg']['by_window']['simulated']['domain_mean_total_mm']:.0f} mm; model forcing {rp['sources']['model_forcing']['by_window']['simulated']['domain_mean_total_mm']:.0f} mm" if rp else "pending"), rps, find(r"331 mm")),
        ("Fig. 6 caption / §3: Mandra '118 / 228 / 46 mm', 'raw watershed-mean ~23 mm', 'peak ~1.9 mm h⁻¹', '×8.55'", "118 / 228 / 46 mm; ~23 mm; 1.9 mm/h; ×8.55", (f"forcing-window bbox means raw {rm['sources']['imerg_raw']['by_window']['forcing']['domain_mean_total_mm']:.0f} / corrected {rm['sources']['imerg']['by_window']['forcing']['domain_mean_total_mm']:.0f} / ERA5 {rm['sources']['era5']['by_window']['forcing']['domain_mean_total_mm']:.0f} mm (file extent {rm['sources']['imerg_raw']['by_window_file_extent']['forcing']['domain_mean_total_mm']:.0f} / {rm['sources']['imerg']['by_window_file_extent']['forcing']['domain_mean_total_mm']:.0f} / {rm['sources']['era5']['by_window_file_extent']['forcing']['domain_mean_total_mm']:.0f}); raw watershed mean {rm['r2_realised']['raw_watershed_mean_mm']:.1f} mm; raw event-window peak {rm['sources']['imerg_raw']['by_window']['event']['domain_mean_peak_mm_h']:.1f} mm/h; factor ×{rm['r2_realised']['factor']:.2f}" if rm and rm['sources'].get('imerg_raw', {}).get('by_window_file_extent') else "pending"), rms, find(r"118 / 228 / 46")),
        ("§3 / §6: 'ERA5 ~4 mm h⁻¹ against >30 mm h⁻¹' (Mandra peak hour)", "~4 vs >30 mm/h", (f"ERA5 bbox-mean peak {rm['sources']['era5']['by_window']['forcing']['domain_mean_peak_mm_h']:.1f} mm/h; corrected IMERG bbox-mean peak {rm['sources']['imerg']['by_window']['event']['domain_mean_peak_mm_h']:.1f} mm/h (the >30 is the NOA gauge/radar value, unchanged)" if rm else "pending"), rms, find(r"4 mm h")),
        ("§4.1.1 / §5.2 / S2: 'peak 118 m³ s⁻¹ at Enipeas', '~135 m³ s⁻¹ coincident', time-varying audit", "118; ~135", (f"nearest-cell peaks " + ", ".join(f"{x['name']} {x['daily_peak_m3s']:.1f}" for x in q['sources']) + f"; combined hourly peak {q['combined_hourly_peak_m3s']:.1f} m³/s; pipeline file constant {q['pipeline_dis_constant_value']:.2f} m³/s (D7)" if q else "pending") + (f"; CSI time-varying {tvq['csi']:.3f}" if tvq else ""), f"{qsrc}; {tvqsrc}", find(r"118 m")),
        ("§5.2: 'qinf = 5 mm h⁻¹ leaves the canonical CSI unchanged (0.456)'", "0.456 unchanged", (f"qinf 5 on the time-varying build: CSI {qi['csi']:.3f} (time-varying without qinf {tvq['csi']:.3f})" if qi and tvq else "pending"), qisrc, find(r"qinf = 5")),
        ("§4.4.2 / §5.3 / S3.1: 'raw-IMERG run scores CSI = 0.105' (Valencia)", "0.105", (f"{raw_v['csi']:.3f} (HR {raw_v['hr']:.3f}, FAR {raw_v['far']:.3f}, B {raw_v['bias']:.2f})" if raw_v else "pending"), raw_vsrc, find(r"0\.105")),
        ("§7: truth-polygon uncertainty '±0.012 / ±0.003 / ±0.041' (Pineios / Strymonas / Mandra, ±20 m)", "±0.012 / ±0.003 / ±0.041",
         "; ".join(f"{ev} CSI {b['sweep']['-20']['csi']:.3f}–{b['sweep']['20']['csi']:.3f} (0 m {b['sweep']['0']['csi']:.3f})" if b else f"{ev} pending" for ev, (b, _) in bufs.items()), "phase4/truth_buffer/*_v14.json", find(r"±0\.012|± 0\.012")),
        ("§4.3.2: Strymonas '5.6 m' peak depth, 'B = 0.44' (v1), 'CSI 0.170→0.183', 'HR 0.210→0.328'", "5.6 m; 0.44; 0.170→0.183; 0.210→0.328",
         (f"peak hmax {float(peak_s['tp_km2']):.1f} m (v3, v1.4)" if peak_s else "peak pending (map CSV)") + "; v1→v3 under v1.4: see Table S2 Strymonas entry", f"{mpsrc}; results/strymonas_v1_prefix_src_v14_newmask.json", find(r"5\.6 m")),
        ("Abstract / §4.1.2 / §7: Pineios headline '0.46 … 0.95', '0.456 (peak 0.515)'", "0.456 / 0.947 / peak 0.515", (lambda s, cs: f"{s['csi']:.3f} / {s['hr']:.3f} / peak {cs['csi']:.3f} at {cs['threshold']}" if s else "pending")(S.strict("pineios_enhanced")[0], S.csi_star("pineios_enhanced")[0]), "results/pineios_enhanced_v14_newmask.json", find(r"0\.456")),
        ("§4.3.2 / §5 / Table 11: Strymonas headline '0.183 / 0.328'", "0.183 / 0.328", (lambda s: f"{s['csi']:.3f} / {s['hr']:.3f} (v1.4 + D6, canonical)" if s else "pending")(S.strict("strymonas_enhanced_postD6")[0]), "results/strymonas_enhanced_postD6_v14_newmask.json", find(r"0\.183")),
        ("§4.2.2 / Table 11: Mandra headline '0.106 / 0.873', fuzzy 0.205 (one-sided, V3) / 0.159", "0.106 / 0.873; 0.159", (lambda s, f1: f"{s['csi']:.3f} / {s['hr']:.3f}; fuzzy r=1 {f1['csi']:.3f}" if s else "pending")(S.strict("mandra_enhanced")[0], S.fuzzy("mandra_enhanced")[0]), "results/mandra_enhanced_v14_newmask.json", find(r"0\.106")),
        ("§4.2.2 / §4.3.2 / §5: Mandra baseline '0.080 / 0.400 / 0.910', Strymonas baseline '0.204 / 0.377 / 0.692', 'B 1.22 → 1.11'", "0.080/0.400/0.910; 0.204/0.377/0.692; 1.22→1.11",
         (lambda m, s, e: (f"Mandra base {m['csi']:.3f}/{m['hr']:.3f}/{m['far']:.3f}; Strymonas base {s['csi']:.3f}/{s['hr']:.3f}/{s['far']:.3f}; B {s['bias']:.2f} → {e['bias']:.2f}" if (m and s and e) else "pending"))(S.strict("mandra_baseline")[0], S.strict("strymonas_baseline")[0], S.strict("strymonas_enhanced_postD6")[0]), "results/{mandra,strymonas}_baseline_v14_newmask.json", find(r"0\.204")),
        ("§5 / Table 10 caption: grid-matched Pineios baseline 'CSI = 0.517, HR = 0.823, FAR = 0.418, B = 1.42, GSS = 0.319 … 0.390 at 0.50 m'", "0.517/0.823/0.418/1.42/0.319; 0.390",
         (lambda s, s5: f"{s['csi']:.3f}/{s['hr']:.3f}/{s['far']:.3f}/{s['bias']:.2f}/{s['gss']:.3f}; at 0.50 m {s5['csi']:.3f}" if s else "pending")(S.strict("pineios_baseline_gridmatched")[0], S.strict("pineios_baseline_gridmatched", "h>0.50m")[0]), "results/pineios_baseline_gridmatched_v14_newmask.json", find(r"0\.517")),
        ("§4.4.2 / §4.5.2 / Table 13-14: Valencia '0.094 / 0.989', Emilia '0.240 / 0.921', 'SEDI 0.470→0.460', 'CSI 0.185 → 0.240'", "0.094/0.989; 0.240/0.921",
         (lambda v, e: f"Valencia {v['csi']:.3f}/{v['hr']:.3f}; Emilia {e['csi']:.3f}/{e['hr']:.3f}" if (v and e) else "pending")(S.strict("valencia_enhanced_164")[0], S.strict("emilia_enhanced_8aoi")[0]), "results/{valencia_enhanced_164,emilia_enhanced_8aoi}_v14_newmask.json", find(r"0\.094")),
        ("S1 prose: Manning test '115.8 vs. 110.8 km² at CN = 97'", "115.8 vs 110.8 km²", (lambda a, b: f"{a:.1f} vs {b:.1f} km² (n 0.080 vs 0.012, HSG-D AMC-III recreation)" if (a is not None and b is not None) else "pending")(S.wet_km2("mandra_cn_d_amc3_manning080")[0], S.wet_km2("mandra_cn_d_amc3")[0]), "results/mandra_cn_d_amc3{,_manning080}_v14_newmask.json", find(r"115\.8", stext, "supplement")),
        ("S1 prose / §6.2: 'TP = 0 at 01MANDRA for CN ∈ [15,95]', 'CSI = 0.031 with zero true positives'", "TP = 0; 0.031", "; ".join(f"{run}: TP(01MANDRA) {a['strict']['tp']}, CSI {s['csi']:.3f}" if (a and s) else f"{run} pending" for run, (a, _), (s, _) in ((r, S.aoi(r, "01MANDRA"), S.strict(r)) for r in ("mandra_cn_a15", "mandra_cn_a58", "mandra_cn_b_default", "mandra_cn_d_amc3"))), "results/mandra_cn_*_v14_newmask.json", find(r"0\.031", stext, "supplement")),
    ]
    for loc, old, new, src, where in sent:
        add(loc, old, new, src, where)
    # ---- write
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = [f"# NUMBER_MAP — NHESS R5 manuscript + supplement numbers under harness v1.4 (new evaluation mask); generated {now} by `reproduction/v14_rerun/scripts/number_map.py`", "",
         "Old = the R5 text (`NHESS_manuscript_R5_clean.docx` / `NHESS_supplement_R5_clean.docx`, extracted with `scripts/extract_docx.py`); New = the v1.4 record named in the source column "
         "(paths relative to `reproduction/v14_rerun/`). Every row whose new value differs from the old one is a manuscript change; rows marked pending wait for the named run. "
         "Headline numbers recur in the Abstract, §4–§8 and the figure captions; the 'where' column lists the extracted-text line numbers found by regex so the rewrite can sweep every occurrence.", "",
         "| location | old (R5) | new (v1.4) | source | note / where |", "|---|---|---|---|---|"]
    for loc, old, new, src, note in E:
        L.append(f"| {loc} | {old} | {new} | `{src}` | {note} |")
    out = a.out or (a.repo / "reproduction" / "v14_rerun" / "NUMBER_MAP.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(E)} entries -> {out}")
    print("\n".join(L[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
