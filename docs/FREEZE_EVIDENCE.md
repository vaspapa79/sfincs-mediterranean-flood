# Freeze evidence for the a-priori activation rule R

Evidence that rule R (Box 1; see [`frozen_rule_R.md`](frozen_rule_R.md)) was fixed **before** either
held-out event — the 2024 Valencia DANA (EMSR773) and the 2023 Emilia-Romagna flood (EMSR664) — was
configured or executed. The rule maps a-priori catchment/event metadata to a forcing configuration,
with no tuning to the observed flood extent.

This file is published at its real commit date; nothing here is backdated.

## Origin commit

The rule text and its Box 1 caption were written and frozen in a single commit of the private
manuscript-build repository:

| field | value |
|---|---|
| origin commit | `bfd005a6f65074662086f30e45ee7869022fc1f6` (`bfd005a`) |
| author date | **2026-07-15 14:33:54 +03:00** (committer date identical — not amended/rebased) |
| where the rule lives | the manuscript build script, §3.4 / Box 1 |

The Box 1 text in this repository's `frozen_rule_R.md` is a byte-for-byte extraction of that
specification (verified against the manuscript draft: all R1–R6 lines present verbatim; Box 1 caption
similarity 1.0000).

## Held-out run timestamps

First artefacts of the two blind runs, from the manuscript repository's run directory (local time
+03:00):

| event | config written | first execution | first score |
|---|---|---|---|
| EMSR773 Valencia | 2026-07-15 15:17 | **2026-07-15 16:10** | 2026-07-15 21:00 |
| EMSR664 Emilia-Romagna | 2026-07-15 15:17 | **2026-07-15 16:30** | 2026-07-15 16:50 |

The freeze (`bfd005a`, 14:33:54) precedes the first held-out configuration by ~43 min and the first
model execution by ~1 h 36 min. A follow-up commit `49da0d1` *"Held-out runs executed: real Valencia
+ Emilia-Romagna SFINCS results"* is dated 2026-07-15 17:00:54 — after both runs, as expected.

## Corroboration internal to the freeze commit

The ordering above rests on git dates, which are self-asserted; the stronger evidence is inside
`bfd005a` itself, and is hard to stage after the fact:

- the commit body states verbatim *"Held-out skill scores are **TBD until the runs**; **no results
  are fabricated**"*;
- it ships placeholder figures **`fig_valencia_pending.png`** and **`fig_emilia_pending.png`** — the
  held-out results were demonstrably not yet known at commit time;
- §2.4 as committed reads *"their skill scores are reported once the two runs are executed and are
  **not pre-empted here**."*

The rule was **not** edited after the results were known: the R1–R6 lines and the Box 1 caption are
identical between the freeze commit and the later revised manuscript.

## Relationship between the two hashes

`bfd005a` (private repository, no public remote) is the **origin** of the rule text and carries the
freeze author date. The public artefact is a **content extraction** of only rule R + Box 1 from it —
added to this repository by the same commit that introduces `frozen_rule_R.md`, published at its real
(later) date. `bfd005a` itself is not replayed into the public history, so the public commit hash
differs from it by construction. The pipeline, validator and configurations are archived at Zenodo
under concept DOI **10.5281/zenodo.20523154**.

## Honest reading

The freeze is genuine and internally corroborated, but the ±43-minute margin was produced by the same
author on the same machine, and the earliest *third-party-attested* timestamp is the public push date,
not 2026-07-15. Treat the timestamp ordering as **supporting** evidence and the TBD commit body plus
the `*_pending.png` figures as the decisive corroboration; the rule's a-priori status does not rest on
the minutes alone.
