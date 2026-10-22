# Box 1 as committed — `docs/frozen_rule_R.md`

- commit: `786fc50302e25fe7ce17430b4243403a168a842d` (786fc50; author date 2026-07-20T15:12:30+03:00, committer date 2026-07-20T15:12:30+03:00; subject: Sync README to the NHESS manuscript; publish frozen rule R + freeze evidence)
- blob: `8f7586269723fdf24003b5fe44665a7e3e4778fd` (unchanged at HEAD: yes)
- extracted rule block: bytes 1060–2104 of the blob, 1044 bytes, SHA-256 `e05a3836dd34cd16e9378cea50a9de9b1c431cd4435714e1b67a4beaad01f857`
- extracted Box 1 caption: bytes 2105–2857, 752 bytes, SHA-256 `1361aa5115a1448b40bfd4249034729a818654a271892c5bcbb03ca1d0afbb59`
- line endings LF; encoding UTF-8 (the caption contains U+2014 and U+00D7). The block below is the committed bytes, wrapped in a four-backtick fence so that its own three-backtick fence is preserved.

## Rule block (byte-identical)

````markdown
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
````

## Box 1 caption (byte-identical)

````markdown
**Box 1.** The frozen a-priori activation rule. Applied to the three development events it reproduces
the configurations reported in the manuscript — Mandra (R2 on, ×8.55; R3 off; R4 off; R5, R6 on),
Strymonas (R2 off; R3 on; R4 on; R5, R6 on) and Pineios (R2 on, ×2.73; R3 on; R4 off; R5, R6 on) — so
those per-event choices are consequences of the rule, not free parameters. Applied blind to the two
held-out events it yields their reported configurations. The one quantity the rule does **not** set a
priori is the numerical value of the R2 multiplier, which is anchored to an independent gauge or
literature total and therefore conditions the skill on knowledge of the event rainfall; the rule
fixes only *whether* the correction is applied.
````
