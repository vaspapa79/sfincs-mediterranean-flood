# Reproducibility of the reported skill scores

## Which values are canonical

The canonical skill scores are computed from the **authors' stored SFINCS outputs**
(`model_author_ref/sfincs_map.nc` for the three development events; the single stored run for each
held-out event) and printed in the manuscript. `validation/validate_event_v2.py` reproduces those
values from the stored `sfincs_map.nc` exactly.

## The SFINCS solver is deterministic

Given a fixed input set, SFINCS is bit-reproducible on this platform — verified directly:

- **Strymonas run twice** from the identical `model_author_ref` input set → the two `sfincs_map.nc`
  are **bit-identical in data** to each other and to the canonical output (max |Δ hmax| = 0).
- **Emilia-Romagna** and **Valencia** re-run from their committed inputs → `sfincs_map.nc`
  **bit-identical** to the stored held-out output (max |Δ hmax| = 0).

So re-running the pipeline from the **committed inputs** reproduces every reported score exactly. There
is no run-to-run solver nondeterminism.

## What actually differs between the author reference and the 2026-06-19 re-run

Each development event also has an independent 2026-06-19 re-run in `model/`. That run does **not**
score identically to `model_author_ref` — but the cause is **different inputs**, not the solver. The
control and mask files are byte-identical (`sfincs.inp`, `sfincs.msk`, `sfincs.ind`), but the forcing
was regenerated:

| event | meteo (`precip/press/wind_2d.nc`) | subgrid | discharge `sfincs.dis` / source `sfincs.src` | scored effect @0.10 m |
|---|---|---|---|---|
| **Pineios** | regenerated (differ) | rebuilt (differ) | **identical** | **none** — metrics byte-identical (CSI 0.45586, TP 63910) |
| **Mandra** | regenerated (differ) | rebuilt (differ) | n/a (no upstream Q) | ΔCSI +7×10⁻⁶ (2 FP cells); 0.106 unchanged |
| **Strymonas** | regenerated (differ) | rebuilt (differ) | **regenerated (differ)** — peak 618.50 vs 640.34 m³ s⁻¹; source cell re-snapped | ΔCSI −0.0012 (TP 1552→1526); **0.183 vs 0.182** |

The diagnostic contrast is Pineios vs Strymonas: Pineios's re-run kept the **same** discharge and
source and its scores are byte-identical despite regenerated meteorology and subgrid, whereas
Strymonas's re-run also regenerated its GloFAS discharge and re-snapped its source. The largest local
field difference for Strymonas — up to ~0.44 m near the injection point — sits exactly where the
discharge hydrograph and source cell changed. It is a **forcing-regeneration difference, not solver
noise, and not sub-centimetre.**

## Why only Strymonas moves at printed precision

The impact scales inversely with flood robustness. Pineios and Mandra are large, rain-dominated
inundations whose wet area is far from the 0.10 m contour, so regenerated meteorology and subgrid shift
essentially no scored cell. Strymonas is the smallest flood and is **upstream-discharge-driven and
channel-confined**: its wet extent hugs the wet/dry margin, and a re-sampled GloFAS discharge (~3–4 %
different) plus a re-snapped source cell move ~26 cells inside the ~4737-cell evaluation mask — a
third-decimal shift, CSI 0.183 → 0.182.

## What this means for reproduction

- From the **committed inputs**, every reported score reproduces **exactly** (deterministic solver;
  demonstrated bit-for-bit for Strymonas, Emilia, Valencia).
- Regenerating the forcing **from scratch** (re-downloading ERA5/GloFAS, re-snapping source cells,
  rebuilding the subgrid) is not bit-stable across builds — GloFAS discharge sampling and DEM tiling
  can change — and on the smallest, discharge-driven event (Strymonas) this shifts CSI by ≤ 0.001. The
  canonical values are the authors' archived outputs (Strymonas 0.183); an independent rebuild lands
  within ±0.001 CSI.

Reproducing these checks: `ELKAK2/NHESS/R1_verification/task9_portability/repro_drift/` (drift scorer,
field-difference, input-hash and re-run determinism scripts) and `task2_strymonas_delta/` (the
Strymonas contingency re-score).
