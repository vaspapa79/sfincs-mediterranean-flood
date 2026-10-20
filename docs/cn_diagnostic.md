# docs/cn_diagnostic.md — SCS-CN infiltration diagnostic (referee M4)

**Question.** The manuscript disables SCS-CN infiltration for Pineios and Mandra and keeps it only as a *diagnostic* for Strymonas, reporting that enabling it *suppresses* the reproduced flood (Strymonas ablation: CN-off+Q CSI **0.238** -> CN-on+Q **0.183**; CN-on+**Q-off collapses to 0.016**). Referee M4 asks whether this suppression is a **solver bug**, an **ingestion/unit error**, or **expected physics at this regime**. This note characterises the mechanism on a minimal, fully-instrumented SFINCS domain.

## Method

- **Binary**: SFINCS v2.3.0 `mt_Faber_release_2025.02` (the canonical exe).
- **Domain**: synthetic 40x40 @ 100 m, regular grid (no subgrid), closed walls.
  - `pan` — flat closed bowl = a **calorimeter**: with no outflow, basin infiltration(t) = cumulative_rain(t) - mean_pond(t), read directly from `sfincs_map.nc`.
  - `tilt` — plane tilted N(high)->S(low) draining to a closed southern sump = flood-extent (cells hmax>0.10 m) vs CN.
- **Forcing**: spatially-uniform pulse 100 mm/hr x 2 h (=200 mm) then dry to 12 h, run BOTH ways — uniform `precipfile` and 2-D `netamprfile` (the production path).
- **Infiltration**: OFF, then ON at CN in {70,85,95}; uniform `sfincs.scs` = (1000/CN-10) inch (hydromt-sfincs convention). Geometry & forcing byte-identical across the four settings.

## 1. Unit handoff — CORRECT (rules out a gross ingestion error)

hydromt-sfincs writes S in **inches**; SFINCS converts to **metres** internally. Verified from map var `qinf` (`long_name = moisture storage (S) capacity - Curve number`, `units = m`):

| CN | S written [inch] | S expected [mm] | S in `qinf` output [mm] |
|---|---|---|---|
| 70 | 4.286 | 108.9 | 108.9 |
| 85 | 1.765 | 44.8 | 44.8 |
| 95 | 0.526 | 13.4 | 13.4 |

`S[mm]` = `S[inch]x25.4` to the decimal -> inch->metre conversion is correct; the scsfile is **not** mis-scaled. A gross unit/ingestion error is ruled out.

## 2. Per-timestep trace (pan calorimeter, `precipfile`)

_CN-OFF conservation check: max|rain - pond| = 0.62 mm -> the closed pan conserves water exactly (infiltration = 0)._

With CN ON, the surface **never ponds** — every output step is 0 mm — although 100 mm/hr is falling. `F_emp` = cumulative rain - pond; `F_scs` = bounded SCS infiltration P-Q (Ia=0.2 S, asymptote Ia+S):

| CN | S [mm] | Ia+S [mm] (SCS max) | pond@2h [mm] | F_emp@2h [mm] | F_scs@2h [mm] |
|---|---|---|---|---|---|
| 70 | 108.9 | 130.6 | 0.0 | 200.0 | 89.4 |
| 85 | 44.8 | 53.8 | 0.0 | 200.0 | 45.3 |
| 95 | 13.4 | 16.0 | 0.0 | 200.0 | 15.2 |

SFINCS infiltrates the **whole 200 mm** for every CN, i.e. **>10x the bounded SCS maximum Ia+S** (16 mm at CN95, 131 mm at CN70), and the result is **independent of CN**. The bounded SCS curve (`F_scs`) would leave 111/155/185 mm ponded at CN70/85/95 — it does not.

## 3. Rate vs storage probes (pan, CN70 & CN95)

Vary rain rate and total to separate the mechanisms. **Storage-capped** (true SCS) -> pond appears once total > ~Ia+S, any rate. **Rate-capped** (Horton f_c) -> pond appears once rate > f_c, any total. **Unbounded/mis-applied** -> pond never appears.

| CN | rate [mm/hr] | total [mm] | Ia+S [mm] | peak pond [mm] |
|---|---|---|---|---|
| 95 | 25 | 200 | 16.0 | 0.00 |
| 95 | 50 | 200 | 16.0 | 0.00 |
| 95 | 200 | 400 | 16.0 | 0.00 |
| 95 | 400 | 400 | 16.0 | 0.00 |
| 70 | 25 | 200 | 130.6 | 0.00 |
| 70 | 200 | 400 | 130.6 | 0.00 |

Pond is **0.00 mm in every case** — even at 400 mm/hr (not rate-capped) and at 400 mm total >> Ia+S (not storage-capped). Infiltration is **effectively unbounded**.

## 4. Production-path confirmation (2-D `netamprfile`)

The real Strymonas/Pineios/Mandra runs force rain with a 2-D `netamprfile`. Reproducing the pan with a uniform 2-D precip (same code path) gives identical behaviour — so this is **not** an artifact of the uniform `precipfile`:

| run (2-D path) | peak pond [mm] |
|---|---|
| CN OFF | 166.05 |
| CN 70 | 0.00 |
| CN 95 | 0.00 |

CN-OFF ponds (~166 mm, rain delivered & conserved); CN70/CN95 annihilate it to 0.00 mm.

## 5. Flood-extent suppression (tilt basin)

| run | active cells | flooded (hmax>0.10 m) | mean pond [mm] |
|---|---|---|---|
| OFF | 1600 | 1520 | 291.2 |
| CN 70 | 1600 | 0 | 0.0 |
| CN 85 | 1600 | 0 | 0.0 |
| CN 95 | 1600 | 0 | 0.0 |

CN-OFF floods 1520/1600 cells; **any** CN drops it to **0** flooded cells — exactly the referee's reported "any non-zero SCS-CN suppresses the flood".

## 6. Corroboration in the production runs

The toy finding is exactly consistent with the committed Strymonas ablations (docs/AUDIT.md), the only event where CN is enabled:

| Strymonas config | CSI | note |
|---|---|---|
| baseline rain-on-grid, **no CN** | 0.204 | rain produces a flood |
| CN-off + Q | 0.238 | rain + injected Kerkini Q |
| **CN-on + Q-off** | **0.016** | **rain alone, CN on -> flood ~annihilated** |
| CN-on + Q (v3 canonical) | 0.183 | survives only on injected Q |

With CN on, the rain-on-grid contribution collapses (0.238 -> 0.016 when Q is removed); the canonical v3 flood (0.183) is **Q-driven**, not rain-driven. That is precisely the toy result — CN on removes essentially all rain-on-grid water — observed in the real model, and it is why the manuscript injects discharge and/or disables CN.

## 7. Verdict

| candidate | result |
|---|---|
| ingestion / unit error | **ruled out** — S correct in metres (Sec 1) |
| expected physics at this regime | **ruled out** — true SCS is bounded by Ia+S and CN-graded; observed infiltration is >10x Ia+S and CN-independent (Sec 2-3) |
| rate-capped | **ruled out** — survives 400 mm/hr (Sec 3) |
| storage-capped (depth-capped) | **ruled out** — survives 400 mm >> Ia+S (Sec 3) |
| **solver / application bug** | **supported** — the SCS path infiltrates ~100% of rainfall irrespective of CN, rate and total, via both forcing paths (Sec 2-5) |

**One-line verdict: solver / application bug — *not* a unit error and *not* expected physics.** The SCS-CN scheme in this SFINCS build acts as a near-total rainfall sink: it removes essentially all incoming rain regardless of curve number, rain rate, or storm total, instead of the bounded SCS storm runoff (Q = P - Ia - F_a, infiltration capped at Ia+S). The scsfile itself is correctly ingested (inch->m verified), so the fault is in how the infiltration is *applied*, not how it is read.

**Most likely internal mechanism (hypothesis — needs the binary source to confirm):** the SCS cumulative-rainfall state is not accumulating across timesteps (or the initial abstraction Ia is effectively re-applied each step), so the runoff fraction S^2/(P-Ia+S)^2 stays ~1 (full infiltration) for all CN. A correctly-accumulating cumulative P would drive that fraction toward 0 (runoff) as the storm builds; here it never does.

**Manuscript implication (referee M4).** The authors' decision to disable SCS-CN for Pineios and Mandra and to treat the Strymonas CN run as a *diagnostic*, not a headline, is **vindicated**: the flood suppression is an artifact of the infiltration routine, not physical infiltration. Recommend the paper state this explicitly — that the SCS-CN scheme in SFINCS v2.3.0 `mt_Faber_release_2025.02`, as applied here, over-removes rainfall (characterised in this diagnostic), which is why rain-on-grid forcing without CN is the reproducible configuration. A recovery-enabled scheme (`setup_cn_infiltration_with_ks`, Horton, or constant `qinf`) should be used if infiltration is wanted.

---
_Reproduce: `reproduction/cn_diagnostic/run_cn_toy.py` (8 base runs) + `probe_cn.py` (6 probes) + the 2-D path block in this folder; then `make_report.py`. Raw per-run numbers in `cn_diagnostic.csv`._