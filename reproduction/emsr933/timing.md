# EMSR933 Crete — timing log (CODE-10)

Purpose: the manuscript reports the elapsed time from the EMS activation
(**2026-10-04 11:02 UTC**, to be confirmed from the API snapshot) to a validated hindcast. Every stage
logs wall-clock start/end in UTC and person-hours. "Claude" = the Claude Code session
(agent wall-clock, including waiting on downloads); "DvS" = Dimitris Valsamis (to be filled in by DvS);
"VP" = Papaioannou decision time, if any.

Wall-clock sources: Claude session transcript timestamps (session `9345177c`) and `date -u` at stage
boundaries. Times are UTC.

| Stage | Start (UTC) | End (UTC) | Wall-clock | Claude (h) | DvS (h) | VP (h) | Notes |
|---|---|---|---|---|---|---|---|
| 0 Preflight + EMS snapshot + availability | 2026-10-09T12:35:48Z | 2026-10-09T12:56Z | 0 h 20 min | 0.35 | _to fill_ | — | session start = task paste; end = STAGE0_REPORT.md written |
| 1 Rule ledger + YAMLs (no model runs); also F2/F4 fixes + regression, F5_VERIFY.md, daily latency probe, NOA station retrieval | 2026-10-09T13:08:34Z | 2026-10-09T14:15Z | 1 h 07 min | 1.1 | _to fill_ | | start = Checkpoint-0 go; end = Checkpoint-1 posted; four F5 agents + one web-research agent ran in parallel (their wall-clock is inside this hour) |
| CODE-12 (harness v1.4 code + tests, re-run manifest, Crete build QC) — on branch `fix/harness-v1.4` | 2026-10-12T09:35:27Z | 2026-10-12T10:40Z | 1 h 05 min | 1.1 | _to fill_ | | start = CODE-12 paste; A1–A2 commit `513ce5a` 10:12:15Z; Crete build-only QC 09:47:40–09:52:32Z (4 min 52 s hydromt); Crete ERA5/IMERG downloaded for A3 (not run); one inventory agent ran in parallel; end = Checkpoint-2 posted |
| CODE-13 (D4 coastal set-up check + fix, IB diagnosis, manifest clean-up) — `fix/harness-v1.4` | 2026-10-19T08:03:12Z | 2026-10-19T08:45Z | 0 h 42 min | 0.7 | _to fill_ | | start = CODE-13 paste; D4 commit `561e8a0` 08:23:45Z; Crete rebuild with the coastal set-up 08:19:34–08:23:17Z (prep 6.6 s + hydromt 208.6 s); no model run of any event; end = Checkpoint-3 posted |
| GO-C (D5 + evaluation mask code/tests, Phase 1 re-runs of Strymonas/Mandra/Pineios, D6 diagnosis, Crete ledger §8) — `fix/harness-v1.4` | 2026-10-19T08:36:18Z | 2026-10-19T10:3xZ | ≈ 2 h | 2.0 | _to fill_ | | start = GO-C paste; D5 commit `8ccabb0` 08:57:24Z; mask commit `c6f39fa` 09:04:55Z; Phase 1 09:05:52–10:22:13Z (six runs, 1 h 16 min); D6 found and diagnosed 09:3x–10:1xZ with eight isolation/synthetic runs on copies (no scoring); end = Checkpoint 4 |
| GO-D6 + Phase 2 (D6 code/tests/provenance, Strymonas re-run, Valencia + Emilia re-runs, Checkpoint 4b) — `fix/harness-v1.4` | 2026-10-19T12:01:29Z | 2026-10-19T13:1xZ | ≈ 1 h 15 min | 1.3 | _to fill_ | | start = GO-D6 paste; bias-box CLI fix `e33eacb` 12:05:51Z; D6 commit `4735429` 12:54:21Z; Valencia 12:06–12:48Z, Emilia 12:03–12:31Z, Strymonas post-D6 12:54–12:58Z; four SFINCS jobs ran concurrently, so all wall-clocks are inflated; end = Checkpoint 4b |
## Data-latency probe (daily, until ERA5T covers 7 Oct) — `scripts/daily_probe.py`, CSV in `latency_probe.csv`
| probe UTC | ERA5 last requestable day | IMERG Final granules 27 Sep–7 Oct | GloFAS v4 intermediate last day | EMS products F/I/N | AOI03 GRA |
|---|---|---|---|---|---|
| 2026-10-09T13:20:35Z | 2026-10-03 | 0 | 2026-10-06 | 6/1/11 | I (id 2965, maps 0, dl=no) |
| 2026-10-12T09:01:29Z | 2026-10-06 | 0 | 2026-10-08 | 7/0/11 | F (id 2965, maps 1, dl=yes) |

Reference point for the manuscript: `activationTime` **2026-10-04T11:02:00** UTC (API snapshot
`ems_api_snapshot_20261009T124720Z.json`). Task issued 2026-10-09T12:35:48Z, i.e. 5 d 1 h 34 min after
activation — idle time before CODE-10 existed, to be reported as such, not as pipeline time.

## Stage 0 — event log
- 2026-10-09T12:35:48Z — CODE-10 task received; workspace orientation (CLAUDE.md, DIRECTORY_MAP, memory, held-out templates).
- 2026-10-09T12:43Z — branch `emsr933-crete` created as a linked worktree at
  `sfincs-mediterranean-floods/.worktrees/emsr933-crete`, base `origin/main` = v1.3.0 (`ccd423a`), `--no-track`.
- 2026-10-09T12:44Z — preflight (`run_pipeline.py --check` + `scripts/preflight_stage0.py`) PASS.
- 2026-10-09T12:47:20Z — EMS API snapshot (provisional cut-off); 6 released packages downloaded by 12:48Z.
- 2026-10-09T12:51:44Z — availability checks (IMERG/CDS/EWDS/DEM/WorldCover); 12:52:19–12:53Z ERA5T expver probe (2 CDS requests, 35 s each).
- 2026-10-09T12:56Z — STAGE0_REPORT.md written; commit follows. Waiting for Checkpoint-0 go.
- 2026-10-09T12:59:16Z — commit `6a5e64b` (Stage 0 records); AUDIT.md §8 entry + this line committed next.

## Stage 1 — event log
- 2026-10-09T13:08:34Z — Checkpoint-0 go received (decisions 1–8); Stage 1 started.
- 2026-10-09T13:1xZ — found that `docs/AUDIT.md` was never tracked in the public repo; canonical copy brought onto the branch (`d1752c6`).
- 2026-10-09T13:20:35Z — first daily latency probe (table above).
- 2026-10-09T13:27Z — F2/F4 implemented under TDD (14 tests GREEN); regression vs published Valencia/Emilia records IDENTICAL (`regression_f2f4.json`); F5 analyses (a–f) dispatched to four parallel read-only agents at 13:12Z; NOA station research dispatched 13:27Z; GLO-30 + WorldCover tile download started 13:27Z (done 13:29Z).
- 2026-10-09T13:32:48Z — `stage1_terrain.py` (pyflwdir on GLO-30 @ 90 m, 23 s); 13:38:33Z `stage1_depressions.py` (polje components).
- 2026-10-09T13:31–13:37Z — the four F5 agents returned (a–c 13:31, e 13:33, f 13:35, d 13:37); `F5_VERIFY.md` compiled 13:45Z; agent numbers spot-checked against their JSONs.
- 2026-10-09T13:49Z — catalog-label test GREEN (17 tests); schema validation of `emsr933_crete.yaml` + `emsr933_crete_enhanced.yaml` OK (`stage1_yaml_validation.json`); `rule_ledger.md` written, §7 (R2-on anchor) pending the NOA/meteo.gr retrieval; commit `46aba38` 13:50Z.
- 2026-10-09T14:04Z — NOA/meteo.gr retrieval returned (13 stations, 117 daily values, 57 published figures, sources + licence); Tzermiado 30 Sep–4 Oct = 447.8 mm (NOA 448).
- 2026-10-09T14:08Z — polje catchments recomputed basin-based (Lasithi 128.6 km², was 223 by inlet-sum double counting); `emsr933_crete_enhanced_R2on.yaml` written and schema-checked (3 configs, preflight OK); ledger §7 completed.
- 2026-10-12T09:01:29Z — daily probe (ERA5T through 2026-10-06 → F1 gate open); Checkpoint 1 posted; AUDIT §8 Stage-1 block (`69d1c58`).

## CODE-12 — event log (harness v1.4; Crete work limited to the build-only QC)
- 2026-10-12T09:35:27Z — CODE-12 received; branch `fix/harness-v1.4` from `69d1c58` (09:35:39Z).
- 2026-10-12T09:42–09:45Z — Crete ERA5 (CDS, 0.6 MB) and IMERG Late (721 granules) downloaded for A3 — not run.
- 2026-10-12T09:47:40Z — Crete build-only hydromt QC build (grid/dep/mask/subgrid, no forcing) started; first attempt with hydromt `setup_waterlevel_bnd_from_mask` failed (pandas-3 `RangeIndex.is_integer`), re-run without it finished 09:52:32Z; subgrid 1.95 GB.
- 2026-10-12T09:5xZ — tests written (RED: 22 attribute errors), implementation, 40 unit tests GREEN; pre-/post-change Pineios forcing regression byte-identical.
- 2026-10-12T10:0xZ — A2 reference pressures, A3 spin-up totals, Crete QC analysis; synthetic 25-hPa SFINCS test GREEN (boundary 0.2489 m vs expected 0.2489).
- 2026-10-12T10:12:15Z — commit `513ce5ab73bbf4ef41e091cf3c49c3b836f2cd8b` (A1–A2 + tests + records; no corrected published-event run exists at this commit).
- 2026-10-12T10:2xZ — one-day Pineios boundary slice (copy of the as-run model, no scoring) run with the v1.4 boundary; MANIFEST.md (Part B) written from the read-only inventory; AUDIT §9 block generated; second commit; Checkpoint 2.

## CODE-13 — event log (D4 coastal set-up; still no model run of any event)
- 2026-10-19T08:03:12Z — CODE-13 received (Checkpoint-2 decisions: A1/A2 accepted, D3 text-only, Crete YAMLs → v1.4).
- 2026-10-19T08:09Z — Crete YAMLs set to `harness_version: v1.4`; Part A geometry check written (`d4_check.py`), run 08:11Z and again 08:20Z after switching to the production `open_sea_split` (numbers identical).
- 2026-10-19T08:1xZ — IB-shortfall diagnosis on the kept slice (`ib_shortfall_diagnosis.py`): half-cell netamp registration found (SFINCS `sfincs_ncinput.F90:496-499`, `sfincs_meteo.f90:977-978`); D4 tests written (RED), implementation, 57 tests GREEN.
- 2026-10-19T08:19:34–08:23:17Z — Crete rebuild with the coastal set-up (`crete_rebuild_v14.py`; 859 727 active cells, 160 bnd points).
- 2026-10-19T08:23:45Z — commit `561e8a03510125016ada36bb1bf30dc2ca4c085f` (D4 code + tests; no corrected published-event run exists at this commit).
- 2026-10-19T08:3xZ — F5_VERIFY correction, schema doc, MANIFEST C1–C3, AUDIT block (`code13_summary.py`), records commit, Checkpoint 3.

## GO-C — event log (decisions received; D5 + evaluation mask before any run; Phase 1 runs)
- 2026-10-19T08:36:18Z — GO-C received (Papaioannou, decisions 1–6 + execution order).
- 2026-10-19T08:4xZ — D5 tests written (RED: 10 attribute errors), implementation (`align_meteo_grids`), unit tests GREEN 08:47Z; first SFINCS gradient test insensitive (gradient perpendicular to the half-cell shift) → rotated, GREEN 08:50Z.
- 2026-10-19T08:51:06–08:55:53Z — full suite 72 tests GREEN (with the D5 metrics record); 08:51–08:54:50Z one-day Pineios slice re-run with aligned grids (220 s; shortfall gone: RMSE 0.0000 m, r = 1.0000).
- 2026-10-19T08:57:24Z — commit `8ccabb03f5f2164be5b52c0633aac1bfff0d73ca` (D5 + tests; no corrected published-event run exists at this commit).
- 2026-10-19T08:5x–09:04Z — evaluation-mask exclusion under TDD (9 unit tests + GeoTIFF check in the strip test), validator default verified identical on the published Strymonas baseline; commit `c6f39fad46b8a71b0172d1b19809d875f415ccd6` 09:04:55Z.
- 2026-10-19T09:05:52Z — Phase 1 started (`phase1.py`, MANIFEST order: Strymonas enhanced, Strymonas baseline, Mandra pair, Pineios pair); karst-recharge literature agent 08:5x–09:0xZ (`karst_recharge_sources.md`).
- 2026-10-19T09:05:52Z → 2026-10-19T09:09:57Z — Phase 1 `strymonas_enhanced` (MANIFEST row 1): hydromt build 43.3 s, SFINCS 168.7 s (published 109.2 s), v1.4 validation 4.2 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T09:09:57Z → 2026-10-19T09:13:13Z — Phase 1 `strymonas_baseline` (MANIFEST row 2): hydromt build 36.2 s, SFINCS 145.5 s (published 256.5 s), v1.4 validation 4.4 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T09:13:13Z → 2026-10-19T09:20:34Z — Phase 1 `mandra_enhanced` (MANIFEST row 3): hydromt build 23.7 s, SFINCS 399.0 s (published 1097.8 s), v1.4 validation 2.6 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T09:20:34Z → 2026-10-19T09:23:00Z — Phase 1 `mandra_baseline` (MANIFEST row 4): hydromt build 23.0 s, SFINCS 112.8 s (published 546.6 s), v1.4 validation 2.5 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T09:23:00Z → 2026-10-19T10:01:00Z — Phase 1 `pineios_enhanced` (MANIFEST row 5): hydromt build 33.2 s, SFINCS 1576.9 s (published 1456.2 s), v1.4 validation 323.2 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T10:01:00Z → 2026-10-19T10:22:13Z — Phase 1 `pineios_baseline_gridmatched` (MANIFEST row 6): hydromt build 89.1 s, SFINCS 980.3 s (published 1006.4 s), v1.4 validation 94.8 s; v1.3 re-scoring in parallel with SFINCS.
- 2026-10-19T09:3x–10:1xZ — Strymonas enhanced v1.4 doubles its flood with half the rain → diagnosis: SFINCS curve-number sink (D6). Six isolation runs on copies (`strym_exp`, 180–600 s each), synthetic closed-plain test (`d6_cn_sink_check.py`, ~1 min), sink-cell map from inputs; report only.
- 2026-10-19T10:19:21–10:20:59Z — full suite 82 tests GREEN; 10:22:13Z Phase 1 finished; Checkpoint-4 tables + AUDIT block generated (`checkpoint4_tables.py`); records commit; Checkpoint 4 posted.

## GO-D6 + Phase 2 — event log
- 2026-10-19T12:01:29Z — GO-D6 + Phase 2 received (D6 adopted with tests first; provenance + private reproducer; Strymonas re-run → 4b; Phase 2 in parallel).
- 2026-10-19T12:03:33Z — Phase 2 seeded and launched (Valencia, Emilia in parallel). 12:03:4xZ Valencia stopped at step 06b: the west-of-Greenwich watershed box was read by argparse as an option; fixed test-first, commit `e33eacb` 12:05:51Z; Valencia relaunched 12:06Z.
- 2026-10-19T12:06:51–12:31:24Z — D6 test (iii) on the event: Mandra enhanced v1.4 with storecumprcp = 1, water levels bit-identical.
- 2026-10-19T12:08–12:23Z — D6 tests written and run before the implementation (RED: no flag, mass ratio 0.0); implementation 12:2xZ; 12:24–12:42Z D6 tests GREEN (15).
- 2026-10-19T12:2x–12:3xZ — provenance: SFINCS main, commits and releases via the GitHub API (known issue since 2026-04-02, fix on main 2026-07-15); D6_CN_SINK.md §1/§6 and reproducer_D6.md.
- 2026-10-19T12:42:30–12:50:07Z — full suite 100 GREEN; multi-day test found to read daily, not hourly, maps (duplicate dtmaxout key) → fixed; 12:51:26–12:54:05Z full suite 101 GREEN.
- 2026-10-19T12:54:21Z — commit `47354293d770c56b1ff8fc7b7fe92491da3bfeca` (D6 + tests; no corrected CN run exists at this commit).
- 2026-10-19T12:03:44Z → 2026-10-19T12:31:38Z — `emilia_enhanced_8aoi` (MANIFEST row 7): hydromt build 41.7 s, SFINCS 1181.3 s (published 754.7 s), v1.4 validation 186.1 s.
- 2026-10-19T12:06:02Z → 2026-10-19T12:48:12Z — `valencia_enhanced_164` (MANIFEST row 8): hydromt build 618.4 s, SFINCS 1397.8 s (published 2230.7 s), v1.4 validation 8.8 s.
- 2026-10-19T12:54:30Z → 2026-10-19T12:58:48Z — `strymonas_enhanced_postD6` (MANIFEST row 1): hydromt build 43.6 s, SFINCS 190.7 s (published 109.2 s), v1.4 validation 5.3 s.
- 2026-10-19T12:59–13:0xZ — Strymonas post-D6 sink check and sub-grid water balance; Checkpoint-4b tables + AUDIT block (`checkpoint4b_tables.py`); records commit; Checkpoint 4b posted.
