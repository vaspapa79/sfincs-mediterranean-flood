"""Model-independent truth rasters cached on disk (Phase 4): keyed by the event, the model grid (shape, origin, cell size)
and the shapefile set, so every run of the same event/grid reuses one rasterisation of the EMS polygons."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


def cache_key(slug: str, s: dict, files, tag: str) -> str:
    x, y = np.asarray(s["x"]), np.asarray(s["y"])
    meta = {"slug": slug, "shape": list(x.shape), "x0": float(x[0, 0]), "y0": float(y[0, 0]), "dx": float(s["dx"]), "dy": float(s["dy"]),
            "files": sorted(str(Path(f).name) for f in files), "tag": tag}
    return hashlib.sha1(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:16]


def cached_bool(cache_dir: Path, key: str, compute):
    """Return the bool array for `key` from cache_dir, computing and storing it (packed bits) when absent."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / f"{key}.npz"
    if p.exists():
        with np.load(p) as z:
            return np.unpackbits(z["bits"])[: int(z["n"])].reshape(tuple(z["shape"])).astype(bool)
    arr = np.asarray(compute(), dtype=bool)
    np.savez_compressed(p, bits=np.packbits(arr.ravel()), n=np.int64(arr.size), shape=np.array(arr.shape))
    return arr
