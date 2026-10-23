"""CODE-22 — the commit map of the history rewrite of 2026-10-23 and a mapper from pre-rewrite to published hashes.

The map is read from the rewrite record reproduction/v14_rerun/code21/history_rewrite.json (filter-repo's commit-map, verified
there by checks (a)-(e)); only the 34 rewritten commits are in it — commits up to the published v1.3.0 kept their hashes.
docs/COMMIT_MAP_2026-10-23.md is the human-readable copy (written by reproduction/v14_rerun/scripts/code22_commit_map_doc.py).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RECORD = Path("reproduction/v14_rerun/code21/history_rewrite.json")
HEX_RUN = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")      # 7-40 lowercase hex, not part of a longer hex run


def load_map(repo: Path) -> dict[str, str]:
    """Full pre-rewrite hash -> full published hash, for the rewritten commits only."""
    rec = json.loads((Path(repo) / RECORD).read_text(encoding="utf-8"))
    return {r["old"]: r["new"] for r in rec["commit_map"] if r["old"] != r["new"]}


def resolve(h: str, cmap: dict[str, str]) -> str | None:
    """The published hash for a pre-rewrite hash given in full or abbreviated (>= 7 hex), at the same length;
    None when h is not a pre-rewrite hash."""
    hits = [o for o in cmap if o.startswith(h)]
    if len(hits) > 1:
        raise ValueError(f"ambiguous pre-rewrite hash {h}: {hits}")
    return cmap[hits[0]][: len(h)] if hits else None


def map_text(text: str, cmap: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Replace every pre-rewrite hash in text by its published hash of the same length. Returns the new text and the
    (old, new) replacements in the order they occur; other hex strings (published hashes, digests) are left as they are."""
    reps: list[tuple[str, str]] = []

    def sub(m: re.Match) -> str:
        new = resolve(m.group(0), cmap)
        if new is None:
            return m.group(0)
        reps.append((m.group(0), new))
        return new
    return HEX_RUN.sub(sub, text), reps
