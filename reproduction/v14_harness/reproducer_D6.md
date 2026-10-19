# SFINCS v2.3.0 — curve-number infiltration removes standing water when `storecumprcp = 0` (DRAFT, private note)

**To:** Deltares SFINCS team, by e-mail. **Do not open a public issue.** **From:** the EMSR flood-reproduction authors
(CERTH-ITI). **Status of the issue upstream:** already listed in the SFINCS known issues since 2026-04-02 (commit
`e394b7f02e`) and fixed on `main` by `360c1592ee` (2026-07-15), which also notes that v2.4.0 Galibier is still affected.
This note is therefore a confirmation with a river-fed reproducer, not a new report. Send only if the authors agree.

**Binary:** SFINCS v2.3.0 mt Faber release (Windows executable, build 2025.02). The model was built with hydromt-sfincs
1.2.2: `setup_cn_infiltration` writes `scsfile`, giving `inftype = 'cna'`. Subgrid mode, `storecumprcp` not set
(default 0).

**Minimal case (closed domain, so all water must stay on the grid):**
- 9.1 × 10.0 km plain at +2 m, 100-m cells, 4 subgrid pixels, no water-level boundary cells.
- Curve number 76 everywhere: S = 80.2 mm, Ia = 0.2 S = 16.0 mm.
- Rain: 30 mm in 3 h (10 mm h⁻¹, 01:00–04:00), spatially uniform, 2-D NetCDF forcing (`netamprfile`).
- One point source of 20 m³ s⁻¹ from 06:00 to 18:00 (`srcfile`/`disfile`); 48-h run.

**Expected (SCS-CN):** runoff Q(30 mm) = (30 − 16.0)² / (30 + 64.2) = 2.07 mm over the plain, plus 0.864 Mm³ from the
source. That is **1 062 364 m³** on the grid from 18:00 onward.

| `storecumprcp` | water on the grid at 06:00 (rain runoff) | at the end | end / expected |
|---|---|---|---|
| 0 (default) | 0 m³ | **0 m³** | 0.000 |
| 1 | 198 926 m³ (2.07 mm) | 1 062 676 m³ | 1.0003 |

**Mechanism (v2.3.0 source).** `sfincs_infiltration.f90:87-112` sets `qinfmap = (I − cuminf)/dt`, with
`I = cumprcp − Q(cumprcp)`. But `cuminf` is incremented only `if (store_cumulative_precipitation)`. The flag defaults
to false (`sfincs_input.f90:219, 439-441`), while `cumprcp` is always accumulated (`sfincs_meteo.f90:1266`). Past
Ia, every time step therefore removes the whole I again. `z_volume = z_volume + dvol` has no floor
(`sfincs_continuity.f90:535`), and the 'cna' branch has no `z_volume <= 0` guard, unlike the constant-rate branch
(`:43-47`). Each such cell becomes an unbounded sink for later rain and for any inflow.

**Magnitude in a real case.** In a river-fed model of the Strymonas flood (Greece, March 2015; 150-m grid, ERA5/IMERG
rain, two GloFAS inflows), 41 % of the active area crossed Ia during the run. About 312 Mm³ of upstream discharge
disappeared in the floodplain instead of ponding or reaching the sea. Setting `storecumprcp = 1` restores the SCS
budget; for models without curve numbers the flag leaves the water levels bit-identical (checked).

**Suggestions (already partly done on `main`).** The release notes of v2.4.0 Galibier say the bug is fixed; a short
erratum there would help users of the released binaries. A `z_volume <= 0` guard in 'cna'/'cnb', as in 'con', would
also make the method robust if the bookkeeping flag is ever lost again.

**Files available on request:** the Python generator of the case (hydromt-sfincs 1.2.2 + the SFINCS executable),
`d6_cn_sink_check.py`, and its JSON output.
