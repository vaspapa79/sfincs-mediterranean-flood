"""CODE-10 Stage 0c — input-data availability for EMSR933 Crete, 27 Sep - 7 Oct 2026.

Checks (no model inputs are written):
  * GPM IMERG half-hourly granule counts per day: Late Run V07 (GPM_3IMERGHHL) and
    Final Run V07 (GPM_3IMERGHH) via NASA CMR/earthaccess, plus the file-naming pattern.
  * ERA5 single levels: CDS catalogue temporal extent + the retrieve-API constraints
    (which days of Sep/Oct 2026 are requestable). ERA5 vs ERA5T is settled separately
    by era5t_probe.py (a one-point retrieval whose `expver` tags each time step).
  * GloFAS v4 historical (EWDS): constraints per product_type for Sep/Oct 2026.
  * Copernicus DEM GLO-30 and ESA WorldCover 2021 v200 tiles covering 23.4-26.4E, 34.8-35.7N
    (HTTP HEAD on the public buckets the pipeline downloads from).

Writes <out-dir>/data_availability_<UTC>.{json,md}.
Usage: python -I data_availability.py --out-dir <worktree>/reproduction/emsr933
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

W, S, E, N = 23.4, 34.8, 26.4, 35.7
T0, T1 = dt.date(2026, 9, 27), dt.date(2026, 10, 7)
UA = {"User-Agent": "Mozilla/5.0 (ELKAK EMSR933 availability)"}


def cds_key() -> str | None:
    p = Path(os.path.expanduser("~/.cdsapirc"))
    for ln in p.read_text().splitlines():
        if ln.startswith("key:"):
            return ln.split(":", 1)[1].strip()
    return None


def http_json(url: str, body: dict | None = None, token: str | None = None, timeout: int = 120):
    h = dict(UA, Accept="application/json")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    if token:
        h["PRIVATE-TOKEN"] = token
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def head(url: str) -> tuple[int, int | None]:
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, int(r.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as e:
        return e.code, None


def imerg_counts(short_name: str) -> dict:
    import earthaccess
    earthaccess.login(strategy="netrc")
    res = earthaccess.search_data(short_name=short_name, version="07",
                                  temporal=(f"{T0}T00:00:00Z", f"{T1}T23:59:59Z"),
                                  bounding_box=(W, S, E, N))
    names = sorted(g["umm"]["GranuleUR"] for g in res)
    per_day = collections.Counter()
    for nm in names:
        # ...3IMERG.YYYYMMDD-SHHMMSS-EHHMMSS....
        try:
            d = nm.split("3IMERG.")[1][:8]
            per_day[f"{d[:4]}-{d[4:6]}-{d[6:]}"] += 1
        except Exception:
            per_day["unparsed"] += 1
    days = [(T0 + dt.timedelta(days=i)).isoformat() for i in range((T1 - T0).days + 1)]
    return {"short_name": short_name, "version": "07", "n_granules": len(names),
            "expected_full_window": 48 * len(days),
            "per_day": {d: per_day.get(d, 0) for d in days},
            "first": names[0] if names else None, "last": names[-1] if names else None,
            "version_suffixes": sorted({nm.split(".")[-2] if nm.count(".") >= 2 else "?" for nm in names})}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    tag = now.strftime("%Y%m%dT%H%M%SZ")
    rep: dict = {"checked_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "window": [str(T0), str(T1)],
                 "bbox_WSEN": [W, S, E, N]}

    # --- IMERG ---------------------------------------------------------------
    rep["imerg_late"] = imerg_counts("GPM_3IMERGHHL")
    rep["imerg_final"] = imerg_counts("GPM_3IMERGHH")

    # --- ERA5 (CDS) ------------------------------------------------------------
    key = cds_key()
    cds = "https://cds.climate.copernicus.eu/api"
    era5 = {}
    try:
        cat = http_json(f"{cds}/catalogue/v1/collections/reanalysis-era5-single-levels")
        era5["catalogue_temporal_extent"] = cat.get("extent", {}).get("temporal", {}).get("interval")
    except Exception as e:
        era5["catalogue_error"] = f"{e.__class__.__name__}: {e}"
    for month in ("09", "10"):
        try:
            c = http_json(f"{cds}/retrieve/v1/processes/reanalysis-era5-single-levels/constraints",
                          {"inputs": {"product_type": ["reanalysis"], "year": ["2026"], "month": [month],
                                      "variable": ["total_precipitation"]}}, token=key)
            era5[f"constraints_2026-{month}_days"] = c.get("day")
        except Exception as e:
            era5[f"constraints_2026-{month}_error"] = f"{e.__class__.__name__}: {e}"
    rep["era5"] = era5

    # --- GloFAS v4 (EWDS) -------------------------------------------------------
    ewds = "https://ewds.climate.copernicus.eu/api"
    gl = {}
    proc = http_json(f"{ewds}/retrieve/v1/processes/cems-glofas-historical")
    gl["process_inputs"] = {k: ((v.get("schema", {}).get("items", {}) or {}).get("enum")
                                or v.get("schema", {}).get("enum"))
                            for k, v in (proc.get("inputs") or {}).items() if k not in ("year", "day", "area")}
    cons = f"{ewds}/retrieve/v1/processes/cems-glofas-historical/constraints"
    # (a) the request vocabulary download_glofas.py uses today (hyear/hmonth/...): expected to be rejected
    try:
        http_json(cons, {"inputs": {"system_version": ["version_4_0"], "hydrological_model": ["lisflood"],
                                    "product_type": ["consolidated"], "hyear": ["2026"], "hmonth": ["10"]}},
                  token=key)
        gl["pipeline_vocabulary_hyear_hmonth"] = "accepted"
    except urllib.error.HTTPError as e:
        gl["pipeline_vocabulary_hyear_hmonth"] = f"REJECTED HTTP {e.code}: {e.read()[:200]!r}"
    # (b) current vocabulary (year/month/day, timespan)
    for sv in ("version_4_0", "version_5_0"):
        for pt in ("consolidated", "intermediate"):
            for month in ("09", "10"):
                k = f"{sv}_{pt}_2026-{month}_days"
                try:
                    c = http_json(cons, {"inputs": {"system_version": [sv], "hydrological_model": ["lisflood"],
                                                    "product_type": [pt], "year": ["2026"], "month": [month]}},
                                  token=key)
                    gl[k] = c.get("day")
                    gl[f"{sv}_{pt}_2026-{month}_timespan"] = c.get("timespan")
                    gl[f"{sv}_{pt}_2026-{month}_variable"] = c.get("variable")
                except urllib.error.HTTPError as e:
                    gl[k] = f"HTTP {e.code}: {e.read()[:200]!r}"
                except Exception as e:
                    gl[k] = f"{e.__class__.__name__}: {e}"
    rep["glofas"] = gl

    # --- Copernicus DEM GLO-30 (AWS) --------------------------------------------
    dem = []
    for lat in range(math.floor(S), math.floor(N) + 1):
        for lon in range(math.floor(W), math.floor(E) + 1):
            name = f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM"
            st, size = head(f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif")
            dem.append({"tile": name, "http": st, "bytes": size})
    rep["copdem_glo30"] = dem

    # --- ESA WorldCover 2021 v200 (AWS) ------------------------------------------
    wc = []
    for lat in range((math.floor(S) // 3) * 3, math.floor(N) + 1, 3):
        for lon in range((math.floor(W) // 3) * 3, math.floor(E) + 1, 3):
            name = f"ESA_WorldCover_10m_2021_v200_N{lat:02d}E{lon:03d}_Map"
            st, size = head(f"https://esa-worldcover.s3.amazonaws.com/v200/2021/map/{name}.tif")
            wc.append({"tile": name, "http": st, "bytes": size})
    rep["worldcover_2021_v200"] = wc

    out = args.out_dir / f"data_availability_{tag}.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1)[:6000])
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
