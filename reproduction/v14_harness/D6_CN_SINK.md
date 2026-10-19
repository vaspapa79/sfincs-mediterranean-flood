# D6 — curve-number infiltration acts as an unbounded water sink (found 2026-10-19 during GO-C Phase 1; REPORT ONLY)

Status: **not changed.** Harness v1.4 as decided at GO-C (D1, D2, D4, D5) still contains this behaviour. The fix is the
author's decision; nothing has been run with it on any event.

## 1. The defect (SFINCS v2.3.0 `v2.3.0_mt_Faber_release`, source in the session scratchpad `sfincs_src/`)

| step | source | what happens |
|---|---|---|
| branch | `sfincs_domain.f90:2066-2069` | `scsfile` given → `inftype = 'cna'` ("Curve Number, old method; no recovery"). This is the route `hydromt setup_cn_infiltration` writes (`scsfile = sfincs.scs`, S in inch, ×0.0254 at `:2190`). |
| rain | `sfincs_meteo.f90:1265-1266` | 2-D rain: `netprcp = prcp`; `cumprcp = cumprcp + prcp*dt` — **always**. |
| infiltration | `sfincs_infiltration.f90:87-112` | if `cumprcp > 0.2 S`: `I = cumprcp − Q(cumprcp)`, `qinfmap = (I − cuminf)/dt`, `netprcp −= qinfmap`; `cuminf += qinfmap*dt` **only if `store_cumulative_precipitation`**. |
| flag | `sfincs_input.f90:219, 439-441` | `storecumprcp` default 0 → `store_cumulative_precipitation = .false.` The published runs do not set it. |
| volume | `sfincs_continuity.f90:~535` | `z_volume = z_volume + dvol` — no floor, and the 'cna' branch has no `z_volume <= 0` guard (the constant-rate branch has one, `sfincs_infiltration.f90:45-46`). |

So with `storecumprcp = 0`, `cuminf` stays 0. Once a cell's cumulative rain passes Ia = 0.2 S, every time step removes
the whole cumulative infiltration I from it, and the volume may go negative. The cell absorbs all later rain and all
inflowing water, including river discharge. With `storecumprcp = 1` the same code applies the SCS increments
(`qinfmap = ΔI/dt ≤ prcp`) and never touches standing water.

## 2. Synthetic proof (`D6_cn_sink_check.json`, `scripts/d6_cn_sink_check.py`; no event, no score)
Closed 9 × 10 km plain at 2 m (no boundary), CN 76 everywhere (S 80.2 mm, Ia 16.0 mm), 30 mm of rain in 3 h, then a
20 m³ s⁻¹ point source for 12 h; one hydromt build, two SFINCS runs differing only in `storecumprcp`.
Correct SCS budget: 2.069 mm runoff over the plain + 0.864 Mm³ from the source = 1 062 364 m³.

| `storecumprcp` | rain runoff at 06:00 (mm) | water on the grid at the end (m³) | end / expected |
|---|---|---|---|
| 0 (as published) | 0.000 | 0 | 0.000 |
| 1 | 2.075 | 1 062 676 | 1.0003 |

## 3. Strymonas v3 enhanced (the only Phase-1 run with CN on)
Inputs only (`D6_strymonas_sink_cells.json`, `scripts/d6_sink_cells.py`: cumulative rain per cell rebuilt with
SFINCS's own grid and block rules vs 0.2 S): cells past Ia by the end of the simulated week —
v1.3 published rain (IMERG ×2, unaligned) **1 905 km² = 41 % of the active area**, 27 % of the Serres-plain/gorge window;
v1.4 rain (×1, aligned) 244 km² = 6 %, 1.3 % of the window. Isolation runs on copies (no scoring;
`../v14_rerun/strymonas_v14_diagnosis.md`, records in `d6_isolation/`): peak/end water on land is 52.5 / 10.9 Mm³
for the published run, for v1.3 with a dry start, for v1.3 with the v1.4 IB boundary, and for v1.4 with the published
rain file; it is 314.8 / 314.8 Mm³ for v1.4, v1.4 with zsini 0, v1.4 without the IB boundary, and v1.4 with unaligned
wind/pressure. D2, D4 and D5 for wind/pressure change nothing on land; the rain file decides how much of the plain
becomes a sink, and the sink decides whether the 312 Mm³ of Kerkini + Angitis discharge in the simulated week survives.

Consequences: the published Strymonas enhanced flood (CSI 0.183) was shaped by the sink. The v1.4 Strymonas enhanced
run (Phase 1) is still affected on 688 plain cells, so its score is **not a valid v1.4 number**. Neither run
represents SCS-CN.

## 4. Scope
- Uses CN (`setup_cn_infiltration`): MANIFEST row 1 (Strymonas v3 enhanced, canonical), row 10 (`abl_qoff.yaml`, Table 12
  "CN-on, Q-off"), row 13 (Strymonas v1 pre-fix, `configs/as_run/emsr122_sfincs_enhanced`), rows 17–18 as configured
  for recreation (Mandra SCS-CN sweep ×5, Pineios CN-on), and the `reproduction/cn_diagnostic` toy runs. Manuscript
  statements resting on CN-on runs: Table 12 CN contrast, §4.1.2 (ii) "~38 km²", §6.2 "CN-on collapses the flood",
  Suppl. Table S1 and its prose.
- Not affected: every baseline, Mandra/Pineios/Valencia/Emilia enhanced (CN off), Crete (CN off; the karst bracket
  uses a constant `qinf`, branch 'con', which has the dry-cell guard).

## 5. Fix options (author's decision)
- **(a) recommended**: under v1.4 write `storecumprcp = 1` into `sfincs.inp` whenever `infiltration.enabled`
  (one inp key; side effect: `cumprcp`/`cuminf` maps in `sfincs_map.nc`). Tests before any run: render/inject test
  (v1.4 + CN → key present; v1.3 byte-identical) and the §2 synthetic water balance through hydromt + SFINCS
  (v1.4 within 0.5 %, v1.3 documents 0). Then re-run Phase-1 Strymonas enhanced (≈ 3 min) and, in Phase 3, rows 10,
  13, 17, 18.
- (b) switch to the 'cnb' method (`setup_cn_infiltration_with_ks`, with recovery): a different model from the one
  published, so not recommended for a re-run.
