# A2 — what `pavbnd` means in SFINCS v2.3.0 (source verification)

Source: GitHub Deltares/SFINCS, tag **`v2.3.0_mt_Faber_release`** ("SFINCS v2.3.0 mt Faber Release 2025.02",
published 2025-11-19; tree `e829fd2e1554b3b1d3b36b8e721e5071a673161a`), files `source/src/*.f90`, fetched
2026-10-12 (scratch copies, not committed). Line numbers refer to that tag. The binary used by the pipeline
reports `Build-Revision: $Rev: v2.3.0 mt. Faber Release` in every log.

## 1. Input parsing — `pavbnd` is a REAL in Pa, default 0.0 (not an on/off flag)

`sfincs_input.f90:93-95`
```fortran
   call read_real_input(500,'pavbnd',pavbnd,0.0)
   call read_real_input(500,'gapres',gapres,101200.0)
   call read_int_input(500,'baro',baro,1)
```
`sfincs_data.f90:71-72`: `real*4 pavbnd` / `real*4 gapres`.

## 2. Where it acts — the water-level boundary update (per boundary cell, kcs = 2)

`sfincs_boundaries.f90:776-800` (inside the loop over the boundary grid points `ib` of `update_boundary_conditions`)
```fortran
      if (kcs(nmb) == 2) then
         ! Regular water level boundary point
         ! Get water levels (surge + tide) from time series boundary conditions
         if (nbnd > 1) then
            zst   = zst_bnd(ind1_bnd_gbp(ib)) * fac_bnd_gbp(ib) + zst_bnd(ind2_bnd_gbp(ib)) * (1.0 - fac_bnd_gbp(ib))
         else
            zst   = zst_bnd(1)
         endif
         if (patmos .and. pavbnd>1.0) then
            ! Barometric pressure correction
            zst = zst + (pavbnd - patmb(ib)) / (rhow * 9.81)
         endif
```
So the boundary water level is **bzs (interpolated between the bnd points) + (pavbnd − p_atm) / (ρ_w g)**,
and the correction is applied **only when `pavbnd > 1.0`**. `pavbnd` is the reference (average) atmospheric
pressure in Pa against which the local pressure at the boundary cell is compared.

`sfincs_meteo.f90:1328-1335` — the pressure used is the one interpolated to each boundary **cell**:
```fortran
      if (patmos .and. pavbnd > 0.0) then
         ! Update atmospheric pressure at boundary points (patmb)
         do ib = 1, ngbnd
            patmb(ib) = patm(nmindbnd(ib))
         enddo
```
`sfincs_domain.f90:2727-2730` — allocation and initial value:
```fortran
      if (pavbnd>0) then
         allocate(patmb(ngbnd))
         patmb = 101200.0
      endif
```
`patmos` is set in `sfincs_domain.f90:94-96` when a pressure file is given and `baro == 1`:
```fortran
   if ((ampfile(1:4) /= 'none' .or. netampfile(1:4) /= 'none' .or. spwfile(1:4) /= 'none' .or. netspwfile(1:4) /= 'none') .and. baro==1) then
      patmos = .true.
```
`rhow` default 1024.0 (`sfincs_input.f90:81`); g is hard-coded 9.81 in the correction.

## 3. What happens without a bnd file

`sfincs_boundaries.f90:166-185`: when the mask contains water-level boundary cells but no `bndfile`, SFINCS
logs *"Warning! Boundary cells found in mask without boundary points from bnd file. Setting water level at
0.0 m at mask boundary cells."* and creates **one dummy boundary point** (`nbnd = 1`, x = y = 0, zs = 0 at
t0 and t1). The update loop above then uses `zst = zst_bnd(1) = 0` for every boundary cell.

## 4. Consequences for the published runs (v1.3.0 harness: `pavbnd = 1`, no bnd/bzs files)

- The published value **1** fails the guard `pavbnd > 1.0`, so the correction **never ran** — the boundary
  stayed at exactly 0.000 m (F5_VERIFY (e)). The hypothesis that `pavbnd = 1` would lower the boundary by
  ≈ 10 m once boundary points exist is **not** what the source does: with the `> 1.0` guard, 1 Pa is treated
  as "off" (1 Pa would indeed give (1 − 101 300)/(1024·9.81) ≈ −10.1 m if the guard were `> 0`).
- Because of the dummy point (§3), bnd/bzs files are not strictly required for the correction to act — but
  relying on a warning path is fragile and the bzs level is then unavailable for a tide. Harness v1.4 writes
  explicit bnd points along the msk = 2 cells (every 10 km, hydromt default) with **bzs = 0 m** (tide
  neglected, Sect. 3.3.3) and `pavbnd = 101325` Pa.
- With `pavbnd = 101325` the boundary level is (101325 − p_atm)/(ρ_w g): +0.249 m for a 25-hPa depression,
  plus a constant offset wherever the event-mean pressure differs from 101325 Pa (A2_pavbnd_reference.md:
  −0.05 … +0.04 m across the six events).

## 5. Precipitation time semantics (for D1, same tag)

`sfincs_input.f90:107,465-468`: `amprblock` default 1 → `ampr_block = .true.` ("Default use data in ampr
file as block rather than linear interpolation"); `sfincs_meteo.f90:1080-1105`: with `ampr_block` the
weight `twfac = 0.0`, i.e. the field at the last stamp ≤ t is held constant until the next stamp
(**left-labelled block rates**). hydromt_sfincs 1.2.2 documents the same: "SFINCS requires the mean
precipitation rate in mm/hr over the upcoming interval. It will use the rate at the start of this interval
and keep it constant throughout." ECMWF (ERA5 data documentation, "Mean rates/fluxes and accumulations"):
*"reanalysis: accumulations are over the hour (the accumulation/processing period) ending at the validity
date/time"* — hence `cumulative_input=True, time_label='right'` is the correct ERA5 setting (identical to the
v1.3 default), while IMERG half-hourly rates stamped at the interval start need
`cumulative_input=False, time_label='left'`.
