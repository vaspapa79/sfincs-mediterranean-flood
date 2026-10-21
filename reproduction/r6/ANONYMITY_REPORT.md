# ANONYMITY_REPORT — dry run (report only; nothing changed)

Generated 2026-10-21T10:14:58Z by `reproduction/r6/scripts/anonymity_grep.py`. Scanned: the tracked tree at tag `v1.4.2` (`0084600`, 1211 files, contents read from git) and 112 record files changed or added after the tag under `reproduction/r6`, `reproduction/v14_rerun/code16`, `reproduction/v14_rerun/scripts`, `reproduction/v14_rerun/NUMBER_MAP.md`, `docs/AUDIT.md`, `reproduction/emsr933` (working tree). PNG files are scanned through their metadata text chunks and 16 TIFF files through their text tags (DocumentName, ImageDescription, Software, Artist, HostComputer, Copyright); 0 other binary files are not scanned (listed at the end). This script, this report and `anonymity_hits.json` contain the patterns by construction and are excluded.

## Summary by class

| class | hits | files | in the tag tree | in records after the tag |
|---|---|---|---|---|
| author names | 48 | 17 | 33 | 15 |
| author names (Greek) | 0 | 0 | 0 | 0 |
| author handles / initials | 72 | 22 | 66 | 6 |
| affiliation: CERTH | 15 | 2 | 15 | 0 |
| affiliation: ITI | 8 | 2 | 8 | 0 |
| e-mail addresses | 4 | 1 | 0 | 4 |
| ORCIDs | 336 | 2 | 2 | 334 |
| vaspapa | 469 | 104 | 467 | 2 |
| github.com URLs | 467 | 10 | 18 | 449 |
| Zenodo DOIs / records | 144 | 7 | 7 | 137 |
| grant numbers | 2 | 1 | 2 | 0 |
| ECHO | 2 | 2 | 1 | 1 |

## author names (48 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 5, 9, 12, 15, 18, 21, 24 | Anagnostopoulos; Gialampoukidis; Kompatsiaris; Moumtzidou; Papaioannou; Valsamis; Vrochidis |
| `docs/AUDIT.md` | record after the tag (modified) | 418, 453, 472, 483, 523, 554, 589 | Papaioannou |
| `docs/AUDIT.md` | tag v1.4.2 | 418, 453, 472, 483, 523, 554 | Papaioannou |
| `docs/VALIDATION_FINDINGS.md` | tag v1.4.2 | 162 | Papaioannou |
| `reproduction/emsr933/F5_VERIFY.md` | tag v1.4.2 | 16 | Papaioannou |
| `reproduction/emsr933/STAGE0_REPORT.md` | tag v1.4.2 | 99 | PAPAIOANNOU |
| `reproduction/emsr933/rule_ledger.md` | record after the tag (modified) | 30, 171 | PAPAIOANNOU; Papaioannou |
| `reproduction/emsr933/rule_ledger.md` | tag v1.4.2 | 30, 171 | PAPAIOANNOU; Papaioannou |
| `reproduction/emsr933/timing.md` | record after the tag (modified) | 6, 7, 70, 99 | Papaioannou; Valsamis |
| `reproduction/emsr933/timing.md` | tag v1.4.2 | 6, 7, 70, 99 | Papaioannou; Valsamis |
| `reproduction/v14_harness/D6_CN_SINK.md` | tag v1.4.2 | 3 | Papaioannou |
| `reproduction/v14_harness/scripts/code12_summary.py` | tag v1.4.2 | 40 | Papaioannou |
| `reproduction/v14_rerun/MANIFEST.md` | tag v1.4.2 | 4, 93, 154 | Papaioannou |
| `reproduction/v14_rerun/scripts/checkpoint4_tables.py` | tag v1.4.2 | 65 | Papaioannou |
| `reproduction/v14_rerun/scripts/checkpoint4b_tables.py` | tag v1.4.2 | 86 | Papaioannou |
| `reproduction/v14_rerun/scripts/checkpoint5a_tables.py` | tag v1.4.2 | 111 | Papaioannou |
| `reproduction/v14_rerun/scripts/code16_freeze_closeout.py` | record after the tag (new) | 3, 114 | Papaioannou |
| `skill/examples/emsr933_crete_enhanced.yaml` | tag v1.4.2 | 9 | PAPAIOANNOU |
| `skill/examples/emsr933_crete_enhanced_R2on.yaml` | tag v1.4.2 | 5 | Papaioannou |
| `validation/eval_exclusion.py` | tag v1.4.2 | 1 | Papaioannou |

## author names (Greek) (0 hits)

none

## author handles / initials (72 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `docs/AUDIT.md` | record after the tag (modified) | 589 | DvS |
| `docs/VALIDATION_FINDINGS.md` | tag v1.4.2 | 10 | dvalsamis |
| `reproduction/emsr933/STAGE0_REPORT.md` | tag v1.4.2 | 99 | DvS |
| `reproduction/emsr933/f5/F5_abc.json` | tag v1.4.2 | 3, 9, 15, 69, 86, 96, 109, 130, 137, 158, 826 | dvalsamis |
| `reproduction/emsr933/f5/F5_f.json` | tag v1.4.2 | 3, 1676, 1689, 1702, 1713, 1722, 1743, 1744, 1817, 1821, 1825 | dvalsamis |
| `reproduction/emsr933/f5/F5_f.md` | tag v1.4.2 | 60 | dvalsamis |
| `reproduction/emsr933/f5/f5_abc_synthetic.py` | tag v1.4.2 | 34 | dvalsamis |
| `reproduction/emsr933/f5/f5_d_volume.py` | tag v1.4.2 | 19, 20 | dvalsamis |
| `reproduction/emsr933/f5/f5_e_ib.py` | tag v1.4.2 | 7 | dvalsamis |
| `reproduction/emsr933/preflight_stage0.json` | tag v1.4.2 | 3, 26, 30, 38, 42, 63, 64 | dvalsamis |
| `reproduction/emsr933/preflight_stage0.log` | tag v1.4.2 | 1, 24, 25, 27, 28, 33 | dvalsamis |
| `reproduction/emsr933/regression_f2f4.json` | tag v1.4.2 | 6, 8, 13, 21, 22, 23, 28 | dvalsamis |
| `reproduction/emsr933/timing.md` | record after the tag (modified) | 6, 12 | DvS |
| `reproduction/emsr933/timing.md` | tag v1.4.2 | 6, 12 | DvS |
| `reproduction/v14_harness/D6_cn_sink_check.json` | tag v1.4.2 | 3 | dvalsamis |
| `reproduction/v14_harness/ib_shortfall_diagnosis.json` | tag v1.4.2 | 3 | dvalsamis |
| `reproduction/v14_harness/ib_synthetic_result.json` | tag v1.4.2 | 4 | dvalsamis |
| `reproduction/v14_harness/pineios_slice_d5_result.json` | tag v1.4.2 | 4, 6, 9, 17, 25 | dvalsamis |
| `reproduction/v14_harness/pineios_slice_ib_result.json` | tag v1.4.2 | 4 | dvalsamis |
| `reproduction/v14_harness/regression_forcing_v13_pineios.json` | tag v1.4.2 | 6, 7 | dvalsamis |
| `reproduction/v14_rerun/scripts/code16_freeze_closeout.py` | record after the tag (new) | 3, 114 | DvS |
| `validation/score_fuzzy_onesided.py` | tag v1.4.2 | 26 | dvalsamis |
| `validation/truth_uncertainty.py` | tag v1.4.2 | 27 | dvalsamis |

## affiliation: CERTH (15 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 8, 11, 14, 17, 20, 23, 26 | CERTH; Centre for Research and Technology |
| `reproduction/v14_harness/reproducer_D6.md` | tag v1.4.2 | 4 | CERTH |

## affiliation: ITI (8 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 8, 11, 14, 17, 20, 23, 26 | Information Technologies Institute |
| `reproduction/v14_harness/reproducer_D6.md` | tag v1.4.2 | 4 | ITI |

## e-mail addresses (4 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `reproduction/r6/refs_crossref_raw.json` | record after the tag (new); third-party bibliographic metadata (Crossref/DataCite records of the cited works) | 48623, 66539, 66674, 67092 | git@github.com; rray@geodesy2.gsfc.nasa.gov |

## ORCIDs (336 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 7 | 0000-0001-6598-7107; orcid.org |
| `reproduction/r6/refs_crossref_raw.json` | record after the tag (new); third-party bibliographic metadata (Crossref/DataCite records of the cited works) | 873, 3243, 3261, 3311, 4042, 4068, 4130, 4863, 4925, 4939, 4953, 8787, 8837, 8911, 10222, 10240, 10277, 10295, 10329, 10347, 10381, 10415, 11433, 11446, 11459, 11472, 11493, 11506, 11519, 11532, 11545, 11558, 11571, 11584, 12079, 12097, 12111, 12125, 12151, 12165, … (173 lines) | 0000-0001-5001-5698; 0000-0001-5102-1598; 0000-0001-5330-7071; 0000-0001-5331-9064; 0000-0001-5470-4714; 0000-0001-5471-172X; 0000-0001-5950-0921; 0000-0001-5999-153X; 0000-0001-6101-421X; 0000-0001-6 |

## vaspapa (469 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 28 | vaspapa79 |
| `README.md` | tag v1.4.2 | 71 | vaspapa79 |
| `configs/as_run/emsr122_sfincs/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/emsr122_sfincs/sfincs_build.yml` | tag v1.4.2 | 43 | vaspapa |
| `configs/as_run/emsr122_sfincs_enhanced/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/emsr122_sfincs_enhanced/sfincs_build.yml` | tag v1.4.2 | 44 | vaspapa |
| `configs/as_run/emsr122_sfincs_v3/README.md` | tag v1.4.2 | 10 | vaspapa |
| `configs/as_run/emsr122_sfincs_v3/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/emsr122_sfincs_v3/sfincs_build.yml` | tag v1.4.2 | 44 | vaspapa |
| `configs/as_run/mandra_sfincs/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/mandra_sfincs/sfincs_build.yml` | tag v1.4.2 | 43 | vaspapa |
| `configs/as_run/mandra_sfincs_enhanced/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/mandra_sfincs_enhanced/sfincs_build.yml` | tag v1.4.2 | 44 | vaspapa |
| `configs/as_run/pineios_sfincs/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/pineios_sfincs/sfincs_build.yml` | tag v1.4.2 | 18, 43 | vaspapa |
| `configs/as_run/pineios_sfincs/sfincs_build_wide.yml` | tag v1.4.2 | 43 | vaspapa |
| `configs/as_run/pineios_sfincs_enhanced/data_catalog.yml` | tag v1.4.2 | 4 | vaspapa |
| `configs/as_run/pineios_sfincs_enhanced/sfincs_build.yml` | tag v1.4.2 | 44 | vaspapa |
| `configs/as_run/strymonas_forecast/data_catalog.yml` | tag v1.4.2 | 4, 9, 22 | vaspapa |
| `configs/as_run/strymonas_forecast/forecast_config.yaml` | tag v1.4.2 | 40, 41, 42, 44, 45, 48, 49, 50, 51 | vaspapa |
| `configs/as_run/strymonas_forecast/sfincs_build.yml` | tag v1.4.2 | 43 | vaspapa |
| `configs/as_run/strymonas_forecast_v2/forecast_config_v2.yaml` | tag v1.4.2 | 29, 30, 31, 32, 33, 34, 35, 36 | vaspapa |
| `docs/AUDIT.md` | record after the tag (modified) | 222, 340 | vaspapa; vaspapa79 |
| `docs/AUDIT.md` | tag v1.4.2 | 222, 340 | vaspapa; vaspapa79 |
| `docs/CODEBASE_MAP.md` | tag v1.4.2 | 70 | vaspapa |
| `docs/VALIDATION_FINDINGS.md` | tag v1.4.2 | 10, 27, 29, 32, 190 | vaspapa; vaspapa79 |
| `reproduction/emsr933/f5/F5_f.json` | tag v1.4.2 | 203, 513, 793, 1093, 1403 | vaspapa |
| `reproduction/v14_rerun/CHECKPOINT6.md` | tag v1.4.2 | 171 | vaspapa79 |
| `reproduction/v14_rerun/INVENTORY_2026-10-12.md` | tag v1.4.2 | 12, 48, 69, 92, 127, 128 | vaspapa |
| `reproduction/v14_rerun/code14/F_branch_plan.md` | tag v1.4.2 | 4 | vaspapa79 |
| `reproduction/v14_rerun/configs/crete_baseline.yaml` | tag v1.4.2 | 40, 41, 42, 43, 44 | vaspapa |
| `reproduction/v14_rerun/configs/crete_canonical_r2on.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/crete_sens_anchor_224.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/crete_sens_anchor_336.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/crete_sens_anchor_582.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/crete_sens_karst_q1914.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/crete_sens_r2off.yaml` | tag v1.4.2 | 74, 75, 76, 77, 78 | vaspapa |
| `reproduction/v14_rerun/configs/emilia_enhanced_8aoi.yaml` | tag v1.4.2 | 82, 83, 84, 85, 86 | vaspapa |
| `reproduction/v14_rerun/configs/emilia_enhanced_8aoi_v142.yaml` | tag v1.4.2 | 88, 89, 90, 91, 92 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_baseline.yaml` | tag v1.4.2 | 33, 34, 35, 36, 37 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_cn_a15.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_cn_a58.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_cn_b_default.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_cn_d_amc3.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_cn_d_amc3_manning080.yaml` | tag v1.4.2 | 74, 75, 76, 77, 78 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_enhanced.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_r2_140.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_r2_255.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_r2_95.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/mandra_v3_maskrestrict.yaml` | tag v1.4.2 | 72, 73, 74, 75, 76 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_baseline_gridmatched.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_cn_on.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_cn_on_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_cn_on_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_enhanced.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_enhanced_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_enhanced_v141_d8titarisios.yaml` | tag v1.4.2 | 97, 98, 99, 100, 101 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_enhanced_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_qinf5.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_qinf5_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_qinf5_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_220.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_220_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_220_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_295.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_295_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_295_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_510.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_510_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_r2_510_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_raw_imerg.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_raw_imerg_v141.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_raw_imerg_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_timevarying_q.yaml` | tag v1.4.2 | 94, 95, 96, 97, 98 | vaspapa |
| `reproduction/v14_rerun/configs/pineios_timevarying_q_v142.yaml` | tag v1.4.2 | 98, 99, 100, 101, 102 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_abl_cnoff_q.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_abl_cnoff_q_v142.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_abl_qoff_cn.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_baseline.yaml` | tag v1.4.2 | 33, 34, 35, 36, 37 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_enhanced.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_enhanced_postD6.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_enhanced_postD6_v142.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_leadin7d.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_leadin7d_v142.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_v1_prefix_src.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/strymonas_v1_prefix_src_v142.yaml` | tag v1.4.2 | 73, 74, 75, 76, 77 | vaspapa |
| `reproduction/v14_rerun/configs/valencia_enhanced_164.yaml` | tag v1.4.2 | 85, 86, 87, 88, 89 | vaspapa |
| `reproduction/v14_rerun/configs/valencia_enhanced_164_v142.yaml` | tag v1.4.2 | 88, 89, 90, 91, 92 | vaspapa |
| `reproduction/v14_rerun/configs/valencia_raw_imerg.yaml` | tag v1.4.2 | 85, 86, 87, 88, 89 | vaspapa |
| `reproduction/v14_rerun/configs/valencia_raw_imerg_v142.yaml` | tag v1.4.2 | 88, 89, 90, 91, 92 | vaspapa |
| `skill/SKILL.md` | tag v1.4.2 | 46, 47, 58 | vaspapa |
| `skill/examples/emsr122_strymonas.yaml` | tag v1.4.2 | 34, 35, 36, 39, 40, 41, 42, 43 | vaspapa |
| `skill/examples/emsr122_strymonas_enhanced.yaml` | tag v1.4.2 | 80, 81, 82, 85, 86, 87, 88, 89 | vaspapa |
| `skill/examples/emsr257_mandra.yaml` | tag v1.4.2 | 57, 58, 59, 62, 63, 64, 65, 66 | vaspapa |
| `skill/examples/emsr257_mandra_enhanced.yaml` | tag v1.4.2 | 101, 102, 103, 106, 107, 108, 109, 110 | vaspapa |
| `skill/examples/emsr664_emilia_romagna_enhanced.yaml` | tag v1.4.2 | 75, 76, 77, 80, 81, 82, 83, 84 | vaspapa |
| `skill/examples/emsr692_pineios.yaml` | tag v1.4.2 | 39, 40, 41, 44, 45, 46, 47, 48 | vaspapa |
| `skill/examples/emsr692_pineios_enhanced.yaml` | tag v1.4.2 | 101, 102, 103, 106, 107, 108, 109, 110 | vaspapa |
| `skill/examples/emsr773_valencia_enhanced.yaml` | tag v1.4.2 | 86, 87, 88, 91, 92, 93, 94, 95 | vaspapa |
| `skill/examples/emsr933_crete.yaml` | tag v1.4.2 | 48, 49, 50, 53, 54, 55, 56, 57 | vaspapa |
| `skill/examples/emsr933_crete_enhanced.yaml` | tag v1.4.2 | 85, 86, 87, 90, 91, 92, 93, 94 | vaspapa |
| `skill/examples/emsr933_crete_enhanced_R2on.yaml` | tag v1.4.2 | 91, 92, 93, 96, 97, 98, 99, 100 | vaspapa |
| `skill/machine.local.example.yaml` | tag v1.4.2 | 22 | vaspapa |
| `skill/references/config_schema.md` | tag v1.4.2 | 48, 50, 52, 60, 61, 62, 63, 64 | vaspapa |
| `skill/references/environment_setup.md` | tag v1.4.2 | 9, 10, 11, 12, 13 | vaspapa |

## github.com URLs (467 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `CITATION.cff` | tag v1.4.2 | 28 | github.com/vaspapa79/sfincs-mediterranean-flood |
| `README.md` | tag v1.4.2 | 71 | github.com/vaspapa79/sfincs-mediterranean-flood |
| `docs/AUDIT.md` | record after the tag (modified) | 340 | github.com/vaspapa79/sfincs-mediterranean-flood |
| `docs/AUDIT.md` | tag v1.4.2 | 340 | github.com/vaspapa79/sfincs-mediterranean-flood |
| `reproduction/r6/REFERENCES_REPORT.md` | record after the tag (new) | 268, 269, 270 | github.com/Deltares/SFINCS/issues/253; github.com/Deltares/SFINCS/issues/386; github.com/Deltares/SFINCS/pull/254 |
| `reproduction/r6/refs_crossref_raw.json` | record after the tag (new); third-party bibliographic metadata (Crossref/DataCite records of the cited works) | 11635, 15516, 45628, 45640, 45644, 45656, 45660, 45672, 45676, 45687, 45701, 66077, 66083, 66084, 66085, 66086, 66087, 66088, 66099, 66100, 66101, 66102, 66103, 66104, 66105, 66106, 66107, 66108, 66109, 66139, 66146, 66147, 66148, 66149, 66150, 66151, 66152, 66153, 66154, 66155, … (442 lines) | github.com; github.com/CarsonW503; github.com/Deltares; github.com/Deltares/SFINCS; github.com/Deltares/SFINCS.git; github.com/Deltares/SFINCS/blob/82c8c4cfb8077fc6754b5c48643791e14bbcb98b/source/; gi |
| `reproduction/r6/scripts/build_refs.py` | record after the tag (new) | 324, 356 | github.com/; github.com/graphql |
| `reproduction/v14_harness/D6_CN_SINK.md` | tag v1.4.2 | 102 | github.com/Deltares/SFINCS |
| `reproduction/v14_rerun/CHECKPOINT6.md` | tag v1.4.2 | 164, 171 | github.com/Deltares/SFINCS/issues/253; github.com/Deltares/SFINCS/issues/375; github.com/Deltares/SFINCS/issues/386; github.com/Deltares/SFINCS/releases; github.com/Deltares/hydromt_sfincs/issues; git |
| `reproduction/v14_rerun/code14/E_d5_provenance.md` | tag v1.4.2 | 13 | github.com/Deltares/SFINCS/issues/253; github.com/Deltares/SFINCS/issues/375; github.com/Deltares/SFINCS/issues/386; github.com/Deltares/SFINCS/releases; github.com/Deltares/hydromt_sfincs/issues; git |
| `reproduction/v14_rerun/code14/F_branch_plan.md` | tag v1.4.2 | 4 | github.com/vaspapa79/sfincs-mediterranean-flood.git |

## Zenodo DOIs / records (144 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `README.md` | tag v1.4.2 | 72 | 10.5281/zenodo.20523154; 10.5281/zenodo.20829572 |
| `docs/AUDIT.md` | record after the tag (modified) | 342 | 10.5281/zenodo.20523154 |
| `docs/AUDIT.md` | tag v1.4.2 | 342 | 10.5281/zenodo.20523154 |
| `docs/FREEZE_EVIDENCE.md` | tag v1.4.2 | 61 | 10.5281/zenodo.20523154 |
| `docs/frozen_rule_R.md` | tag v1.4.2 | 50 | 10.5281/zenodo.20523154 |
| `reproduction/r6/REFERENCES_REPORT.md` | record after the tag (new) | 32, 65, 81 | 10.5281/zenodo.7254221; 10.5281/zenodo.8365009; zenodo.org/doi/10.5281/zenodo.8365009; zenodo.org/record/7254221 |
| `reproduction/r6/refs_crossref_raw.json` | record after the tag (new); third-party bibliographic metadata (Crossref/DataCite records of the cited works) | 1281, 1282, 11363, 11371, 11380, 11381, 11385, 11389, 11390, 11394, 11400, 11409, 11410, 11414, 11417, 11420, 11641, 11646, 11651, 11656, 11661, 11666, 11671, 11676, 11681, 11686, 11691, 11696, 11701, 11706, 11711, 11741, 11785, 11804, 11808, 11812, 11816, 11820, 11824, 11828, … (127 lines) | 10.5281/zenodo.10548224; 10.5281/zenodo.10548225; 10.5281/zenodo.10728098; 10.5281/zenodo.11093876; 10.5281/zenodo.12786106; 10.5281/zenodo.13154470; 10.5281/zenodo.13691619; 10.5281/zenodo.13693006;  |
| `reproduction/r6/refs_datacite.bib` | record after the tag (new) | 6, 13, 34, 41 | 10.5281/zenodo.7254221; 10.5281/zenodo.8365009 |

## grant numbers (2 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `docs/VALIDATION_FINDINGS.md` | tag v1.4.2 | 154, 156 | 101225575 |

## ECHO (2 hits)

| file | where | lines | matches (distinct) |
|---|---|---|---|
| `docs/VALIDATION_FINDINGS.md` | tag v1.4.2 | 154 | ECHO |
| `reproduction/r6/refs_crossref_raw.json` | record after the tag (new); third-party bibliographic metadata (Crossref/DataCite records of the cited works) | 12412 | ECHO |

## Not scanned (binary)

none
