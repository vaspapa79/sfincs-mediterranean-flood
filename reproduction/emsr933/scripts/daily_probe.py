"""CODE-10 — daily data-latency probe (F1 accepted as latency; Stage 2 waits for ERA5T through 7 Oct).

Re-checks, without downloading or re-snapshotting: the last requestable ERA5 day on CDS, the IMERG
Final granule count for the window, the last GloFAS-v4 intermediate day on EWDS, and the EMSR933
product status counts from the public API (incl. the AOI03 GRA). Appends one row to
<out-dir>/latency_probe.csv and one row to the probe table in <out-dir>/timing.md.

Usage: python -I daily_probe.py --out-dir <worktree>/reproduction/emsr933
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from data_availability import cds_key, http_json, imerg_counts, UA  # noqa: E402

API = "https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR933"


def era5_last_day(key: str | None) -> str:
    cds = "https://cds.climate.copernicus.eu/api"
    last = None
    for month in ("09", "10", "11"):
        c = http_json(f"{cds}/retrieve/v1/processes/reanalysis-era5-single-levels/constraints",
                      {"inputs": {"product_type": ["reanalysis"], "year": ["2026"], "month": [month],
                                  "variable": ["total_precipitation"]}}, token=key)
        days = c.get("day") or []
        if days:
            last = f"2026-{month}-{max(days)}"
    return last or "none"


def glofas_last_day(key: str | None) -> str:
    ewds = "https://ewds.climate.copernicus.eu/api"
    last = None
    for month in ("09", "10", "11"):
        c = http_json(f"{ewds}/retrieve/v1/processes/cems-glofas-historical/constraints",
                      {"inputs": {"system_version": ["version_4_0"], "hydrological_model": ["lisflood"],
                                  "product_type": ["intermediate"], "year": ["2026"], "month": [month]}},
                      token=key)
        days = c.get("day") or []
        if days:
            last = f"2026-{month}-{max(days)}"
    return last or "none"


def ems_status() -> tuple[str, str, bool]:
    req = urllib.request.Request(API, headers=dict(UA, Accept="application/json"))
    act = json.loads(urllib.request.urlopen(req, timeout=120).read())["results"][0]
    counts = {"F": 0, "I": 0, "N": 0, "other": 0}
    gra = "absent"
    for aoi in act["aois"]:
        for p in aoi["products"]:
            sc = (p.get("version") or {}).get("statusCode")
            counts[sc if sc in counts else "other"] += 1
            if aoi["number"] == 3 and p["type"] == "GRA":
                gra = f"{sc} (id {p['id']}, maps {p.get('mapsCount')}, dl={'yes' if p.get('downloadPath') else 'no'})"
    return f"{counts['F']}/{counts['I']}/{counts['N']}" + (f" (+{counts['other']} other)" if counts["other"] else ""), gra, bool(act["closed"])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    key = cds_key()
    row = {"probe_utc": now, "era5_last_day": era5_last_day(key),
           "imerg_final_granules": imerg_counts("GPM_3IMERGHH")["n_granules"],
           "glofas_v4_intermediate_last_day": glofas_last_day(key)}
    row["ems_F_I_N"], row["aoi03_gra"], row["ems_closed"] = ems_status()
    csv_p = a.out_dir / "latency_probe.csv"
    new = not csv_p.exists()
    with open(csv_p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    line = (f"| {row['probe_utc']} | {row['era5_last_day']} | {row['imerg_final_granules']} | "
            f"{row['glofas_v4_intermediate_last_day']} | {row['ems_F_I_N']}{' CLOSED' if row['ems_closed'] else ''} | "
            f"{row['aoi03_gra']} |")
    tm = a.out_dir / "timing.md"
    txt = tm.read_text(encoding="utf-8")
    marker = "|---|---|---|---|---|---|\n"
    i = txt.find("## Data-latency probe")
    j = txt.find(marker, i) + len(marker)
    # insert after the last existing probe row (rows start with "| 2026")
    k = j
    while txt.startswith("| 20", k):
        k = txt.find("\n", k) + 1
    tm.write_text(txt[:k] + line + "\n" + txt[k:], encoding="utf-8")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
