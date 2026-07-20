# Frozen a-priori activation rule R

Public, citable record of the **frozen a-priori activation rule R** used in the manuscript
*"Enhanced-forcing SFINCS hindcasts of Mediterranean flood archetypes, validated against the
Copernicus Emergency Management Service"* (Natural Hazards and Earth System Sciences).

The five forcing modules could in principle be switched on or off case by case; instead their
activation is fixed by a single rule R that maps properties knowable a priori from catchment and
event metadata — catchment area, convective-core scale relative to the satellite footprint,
antecedent soil-moisture state, fire history, and whether the domain reaches the sea — to a
configuration, with no tuning to the observed flood extent.

The rule and its Box 1 specification are reproduced verbatim below. The provenance of the freeze
(the originating commit, its date, and the held-out run timestamps) is documented separately in
[`FREEZE_EVIDENCE.md`](FREEZE_EVIDENCE.md); this file is published at its real commit date and is
**not** backdated.

```
Frozen a-priori activation rule R  (fixed before any held-out run;
inputs knowable a priori from catchment and event metadata)

R1 precipitation     := GPM IMERG Final V07     # always; never ERA5 grid
R2 rain bias factor  := IF core scale L_c < IMERG footprint (0.1 deg,
                           ~11 km)
                        THEN gauge-anchored multiplier to an independent
                             watershed-mean total    ELSE raw IMERG
R3 upstream Q        := IF catchment_area >= 4 x GloFAS-v4 cell (~120 km2)
                        THEN GloFAS-v4 at named inflow points, snapped
                             to the lowest-z_b channel cell    ELSE off
R4 SCS-CN infiltr.   := IF AMC-III (multi-day wet spell OR peak intensity
                           > HSG saturated capacity) OR fire-affected /
                           near-impervious catchment
                        THEN off    ELSE on at HSG-B, AMC-II
R5 coastal IB bound. := on IF domain contains sea cells (z <= 0) ELSE off
R6 wind + MSLP stress:= on (always)
```

**Box 1.** The frozen a-priori activation rule. Applied to the three development events it reproduces
the configurations reported in the manuscript — Mandra (R2 on, ×8.55; R3 off; R4 off; R5, R6 on),
Strymonas (R2 off; R3 on; R4 on; R5, R6 on) and Pineios (R2 on, ×2.73; R3 on; R4 off; R5, R6 on) — so
those per-event choices are consequences of the rule, not free parameters. Applied blind to the two
held-out events it yields their reported configurations. The one quantity the rule does **not** set a
priori is the numerical value of the R2 multiplier, which is anchored to an independent gauge or
literature total and therefore conditions the skill on knowledge of the event rainfall; the rule
fixes only *whether* the correction is applied.

---

The deterministic SFINCS reproduction pipeline, per-event YAML configurations and validation harness
are in this repository; concept archive DOI **10.5281/zenodo.20523154**.
