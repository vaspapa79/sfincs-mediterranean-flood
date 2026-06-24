"""Shared helpers for sfincs-flood-reproduction scripts.

Loads the YAML config, derives the time window + bbox + tile lists, and
provides small utilities every script wants (Path coercion, ensure_dir,
the GDAL_DATA env-var bootstrap).
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    sys.exit("pyyaml is required; the user's sfincs-viz env should have it. "
             "Do NOT pip install — surface this to the user. (" + str(e) + ")")


SKILL_DIR = Path(__file__).resolve().parent.parent


def setup_gdal_env(env_cfg: dict) -> None:
    """Set GDAL_DATA before importing rasterio / pyogrio, so they don't warn."""
    gdal_data = env_cfg.get("gdal_data")
    if gdal_data and not os.environ.get("GDAL_DATA"):
        os.environ["GDAL_DATA"] = str(gdal_data)


# ---------------------------------------------------------------------------
# R1 portability: machine-local env/paths override.
#
# The committed examples/*.yaml carry the *author machine's* absolute env/paths
# as a frozen as-run record; on any other box those don't resolve. We layer a
# machine-local override on top of the loaded YAML. With NO override present,
# behaviour is byte-identical to before. Precedence (low -> high):
#   committed YAML  <  author->local root remap  <  override-file env/paths
#   <  SFINCS_* env vars  <  ~ / ${VAR} / %VAR% expansion.
# ---------------------------------------------------------------------------

# Convenience per-key env-var overrides (win over the override file).
_ENV_OVERRIDES = {
    "SFINCS_PYTHON":          ("env", "python"),
    "SFINCS_HYDROMT":         ("env", "hydromt"),
    "SFINCS_EXE":             ("env", "sfincs_exe"),
    "SFINCS_GDAL_DATA":       ("env", "gdal_data"),
    "SFINCS_GDALBUILDVRT":    ("env", "gdalbuildvrt"),
    "SFINCS_WORK_DIR":        ("paths", "work_dir"),
    "SFINCS_DELIVERABLE_DIR": ("paths", "deliverable_dir"),
    "SFINCS_ZIP_DIR":         ("paths", "zip_dir"),
}


def _expand(value: Any) -> Any:
    """Expand ~, ${VAR} and %VAR% in a path-like string; pass through non-strings."""
    if not isinstance(value, str):
        return value
    return os.path.expandvars(os.path.expanduser(value))


def machine_override_path() -> Path | None:
    """Resolve the machine-local override file, if any.

    Search order: $SFINCS_MACHINE_CONFIG (explicit), then <skill>/machine.local.yaml.
    """
    cand = os.environ.get("SFINCS_MACHINE_CONFIG")
    for p in ([Path(cand)] if cand else []) + [SKILL_DIR / "machine.local.yaml"]:
        if p and p.is_file():
            return p
    return None


def _load_machine_override() -> dict:
    p = machine_override_path()
    if not p:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _apply_machine_overrides(raw: dict) -> dict:
    """Layer machine-local env/paths over the committed (author-machine) YAML."""
    ov = _load_machine_override()

    # 1. root remap: swap the author ELKAK root prefix for this machine's.
    author_root, local_root = ov.get("author_root"), ov.get("local_root")
    if author_root and local_root:
        ar = str(author_root).replace("\\", "/").rstrip("/")
        lr = str(local_root).replace("\\", "/").rstrip("/")
        for section in ("env", "paths"):
            sect = dict(raw.get(section) or {})
            for k, v in list(sect.items()):
                if isinstance(v, str):
                    vn = v.replace("\\", "/")
                    if vn.lower().startswith(ar.lower()):
                        sect[k] = lr + vn[len(ar):]
            if sect:
                raw[section] = sect

    # 2. explicit env/paths blocks from the override file win over the remap.
    for section in ("env", "paths"):
        if isinstance(ov.get(section), dict):
            raw[section] = {**(raw.get(section) or {}), **ov[section]}

    # 3. SFINCS_* env vars win over everything in the files.
    for var, (section, key) in _ENV_OVERRIDES.items():
        val = os.environ.get(var)
        if val:
            raw[section] = {**(raw.get(section) or {}), key: val}

    # 4. expand ~, ${VAR}, %VAR% in all env/paths string values.
    for section in ("env", "paths"):
        sect = dict(raw.get(section) or {})
        for k, v in list(sect.items()):
            sect[k] = _expand(v)
        if sect:
            raw[section] = sect
    return raw


def preflight_check(cfg: "EventCfg") -> int:
    """Validate tools / paths / credentials a run needs, BEFORE step 01.

    Without this, a wrong tool path only surfaces at step 10-11, after hours of
    downloads. Returns 0 if every HARD requirement resolves, 1 otherwise.
    """
    env = cfg.env
    problems: list[str] = []
    warnings: list[str] = []

    def need(label: str, val: Any) -> None:
        if not val:
            problems.append(f"{label}: not configured")
        elif not Path(str(val)).exists():
            problems.append(f"{label}: not found -> {val}")
        else:
            print(f"  ok   {label}: {val}")

    print(f"preflight --check  [{cfg.event_label}]  (override: "
          f"{machine_override_path() or 'none'})")
    need("env.python", env.get("python"))
    need("env.hydromt", env.get("hydromt"))
    need("env.sfincs_exe", env.get("sfincs_exe"))
    need("env.gdalbuildvrt", env.get("gdalbuildvrt"))
    if env.get("gdal_data"):
        need("env.gdal_data", env.get("gdal_data"))

    cds = Path(_expand(str(env.get("cds_key_file", "~/.cdsapirc"))))
    if cds.exists():
        print(f"  ok   cds creds (ERA5/GloFAS): {cds}")
    else:
        problems.append(f"cds creds (~/.cdsapirc): not found -> {cds}")

    netrc = Path(_expand("~/.netrc"))
    if cfg.rain_source == "imerg_half_hourly":
        if netrc.exists():
            print(f"  ok   earthdata creds (IMERG): {netrc}")
        else:
            problems.append("earthdata creds (~/.netrc): REQUIRED for IMERG "
                            f"(rain_source=imerg_half_hourly), not found -> {netrc}")
    elif not netrc.exists():
        warnings.append("~/.netrc absent (only needed when an IMERG/enhanced run is selected)")

    for w in warnings:
        print(f"  warn {w}")
    if problems:
        print("\npreflight FAILED — fix before running the pipeline:")
        for p in problems:
            print(f"  MISSING  {p}")
        return 1
    print("preflight OK.")
    return 0


@dataclass
class EventCfg:
    raw: dict
    config_path: Path

    @property
    def event_id(self) -> str | None:
        return self.raw["event"].get("id") or None

    @property
    def event_name(self) -> str:
        return self.raw["event"]["name"]

    @property
    def event_slug(self) -> str:
        s = self.raw["event"].get("slug")
        if s:
            return s
        return self.event_name.lower().replace(" ", "_")

    @property
    def event_label(self) -> str:
        # "EMSR122 Strymonas" or just "Strymonas" if no EMS code.
        if self.event_id:
            return f"{self.event_id} {self.event_name}"
        return self.event_name

    @property
    def event_date(self) -> dt.date:
        return dt.date.fromisoformat(str(self.raw["event"]["date"]))

    @property
    def window(self) -> dict:
        w = self.raw.get("window", {}) or {}
        return {
            "spinup_days": int(w.get("spinup_days", 1)),
            "pre_event_days": int(w.get("pre_event_days", 3)),
            "post_event_days": int(w.get("post_event_days", 3)),
        }

    @property
    def tref(self) -> dt.datetime:
        w = self.window
        d = self.event_date - dt.timedelta(days=w["pre_event_days"] + w["spinup_days"])
        return dt.datetime.combine(d, dt.time())

    @property
    def tstart(self) -> dt.datetime:
        w = self.window
        d = self.event_date - dt.timedelta(days=w["pre_event_days"])
        return dt.datetime.combine(d, dt.time())

    @property
    def tstop(self) -> dt.datetime:
        # tstop is midnight at the START of the day after the last simulated
        # day. With post_event_days=3 and event=03-31, the sim covers 03-31,
        # 04-01, 04-02, 04-03 — so tstop = 04-04 00:00.
        w = self.window
        d = self.event_date + dt.timedelta(days=w["post_event_days"] + 1)
        return dt.datetime.combine(d, dt.time())

    @property
    def bbox(self) -> dict:
        return dict(self.raw["bbox"])  # {west, south, east, north, era5_buffer_deg?}

    @property
    def bbox_list(self) -> list[float]:
        b = self.bbox
        return [float(b["west"]), float(b["south"]),
                float(b["east"]), float(b["north"])]

    @property
    def bbox_with_buffer(self) -> list[float]:
        """[N, W, S, E] for CDS / EWDS (NWSE order, with era5_buffer_deg padding)."""
        b = self.bbox
        buf = float(b.get("era5_buffer_deg", 0.2))
        return [float(b["north"]) + buf, float(b["west"]) - buf,
                float(b["south"]) - buf, float(b["east"]) + buf]

    @property
    def epsg(self) -> int:
        return int(self.raw["crs"]["epsg"])

    @property
    def grid(self) -> dict:
        g = self.raw.get("grid", {}) or {}
        return {
            "res": int(g.get("res", 150)),
            "rotated": bool(g.get("rotated", False)),
            "subgrid_pixels": int(g.get("subgrid_pixels", 4)),
            "manning_land": float(g.get("manning_land", 0.04)),
            "manning_sea": float(g.get("manning_sea", 0.02)),
            "zmin": float(g.get("zmin", -2)),
            "zmax": float(g.get("zmax", 250)),
            "fill_area_km2": float(g.get("fill_area_km2", 20)),
            "drop_area_km2": float(g.get("drop_area_km2", 5)),
        }

    @property
    def paths(self) -> dict:
        p = dict(self.raw.get("paths", {}) or {})
        work = Path(p["work_dir"])
        return {
            "work_dir": work,
            "data_dir": work / "data",
            "model_dir": work / "model",
            "deliverable_dir": Path(p["deliverable_dir"]),
            "zip_dir": Path(p.get("zip_dir", Path(p["deliverable_dir"]).parent)),
            "manning_lookup": Path(p["manning_lookup"]) if p.get("manning_lookup")
                              else SKILL_DIR / "manning_lookup.csv",
            "era5_extracted_dir": Path(p["era5_extracted_dir"]) if p.get("era5_extracted_dir")
                                  else work / "data" / "era5_extracted",
            "glofas_extracted_dir": Path(p["glofas_extracted_dir"]) if p.get("glofas_extracted_dir")
                                    else work / "data" / "glofas_extracted",
        }

    @property
    def env(self) -> dict:
        return self.raw.get("env", {}) or {}

    @property
    def ems(self) -> dict:
        return self.raw.get("ems", {}) or {}

    @property
    def animation(self) -> dict:
        return self.raw.get("animation", {}) or {}

    # --- enhanced-forcing config sections (all optional / off by default) ----
    @property
    def coastal_bc(self) -> dict:
        """Aegean / coastal BC config.

        keys:
          enabled (bool, default False) — if True, set pavbnd=1 in sfincs.inp
          pavbnd (int 0/1, default 1)  — explicit pavbnd override
          tide_source (str, default 'none') — 'none' | 'fes2014' | 'tpxo'
          tide_note (str) — free-text rationale (e.g. "microtidal Aegean")
        """
        c = self.raw.get("coastal_bc", {}) or {}
        return {
            "enabled": bool(c.get("enabled", False)),
            "pavbnd": int(c.get("pavbnd", 1)),
            "tide_source": str(c.get("tide_source", "none")),
            "tide_note": str(c.get("tide_note", "Aegean microtidal "
                              "(<5 cm M2; Tsimplis & Bryden 2000) — tide neglected.")),
        }

    @property
    def wind_pressure(self) -> dict:
        """Atmospheric (wind + MSLP) forcing config.

        keys:
          enabled (bool, default False) — emit netCDFs + wire setup_*_forcing_from_grid
          source (str, default 'era5')  — which dataset
        """
        a = self.raw.get("wind_pressure", {}) or {}
        return {
            "enabled": bool(a.get("enabled", False)),
            "source": str(a.get("source", "era5")),
        }

    @property
    def infiltration(self) -> dict:
        """SCS-CN infiltration config (mirrors forecast_v2 schema).

        keys:
          enabled (bool, default False)
          hsg (str, default 'B') — hydrologic soil group (A/B/C/D)
          amc (int 1-3, default 2) — antecedent moisture condition
          cn_lookup (dict[int, int]) — WorldCover class -> CN
        """
        i = self.raw.get("infiltration", {}) or {}
        default_lookup = {
            10: 65, 20: 65, 30: 72, 40: 76, 50: 88, 60: 80,
            70: 99, 80: 99, 90: 85, 95: 85, 100: 70,
        }
        return {
            "enabled": bool(i.get("enabled", False)),
            "hsg": str(i.get("hsg", "B")),
            "amc": int(i.get("amc", 2)),
            "cn_lookup": dict(i.get("cn_lookup", default_lookup)),
        }

    @property
    def upstream_q(self) -> dict:
        """Upstream discharge boundary config — GloFAS sampled at named points.

        keys:
          enabled (bool, default False)
          src_points (list[{name, lon, lat}]) — boundary inflow locations
          glofas_var (str, default 'discharge') — variable name in the catalog
        """
        q = self.raw.get("upstream_q", {}) or {}
        return {
            "enabled": bool(q.get("enabled", False)),
            "src_points": list(q.get("src_points", [])),
            "glofas_var": str(q.get("glofas_var", "discharge")),
        }

    @property
    def rain_source(self) -> str:
        """Precipitation source. Currently supported:
          - era5_hourly         (default, ~25 km, hourly, ECMWF)
          - imerg_half_hourly   (~10 km, 30 min, NASA GPM IMERG Final V07)
        """
        return str(self.raw.get("rain_source", "era5_hourly"))

    @property
    def rain_bias_correct(self) -> dict:
        """R5: gauge-anchored IMERG bias correction, captured in-config.

        Previously the multiplicative IMERG scaling lived only in CLI history /
        prose (Pineios x2.73 / 400 mm; Mandra x8.55 / 200 mm), so rainfall
        forcing was not deterministically reproducible from the YAML. This block
        records the exact target + window + watershed, and run_pipeline.py passes
        them to bias_correct_imerg.py right after the IMERG download. Off by
        default → behaviour unchanged for any config without the block.

        keys:
          enabled (bool, default False)
          target_mm (float) — gauge-based 24-h watershed catchment-mean target (mm)
          watershed_bbox (list[float] | str) — 'minlon,minlat,maxlon,maxlat'
          event_start / event_end (str 'YYYY-MM-DD HH:MM', UTC) — scaling window
        """
        b = self.raw.get("rain_bias_correct", {}) or {}
        wb = b.get("watershed_bbox")
        if isinstance(wb, (list, tuple)):
            wb = ",".join(str(x) for x in wb)
        return {
            "enabled": bool(b.get("enabled", False)),
            "target_mm": float(b.get("target_mm", 200.0)),
            "watershed_bbox": wb,
            "event_start": str(b["event_start"]) if b.get("event_start") else None,
            "event_end": str(b["event_end"]) if b.get("event_end") else None,
        }

    # --- derived bits ----------------------------------------------------
    @staticmethod
    def _ceil_tile_edge(value: float, tile_size: int) -> int:
        """Smallest multiple of tile_size that is strictly greater than value.

        Used to compute the exclusive upper bound of a tile range so that a
        bbox whose east/north edge lands *on* a tile boundary still pulls
        the tile immediately to the right/north. E.g. east=24.0 with 1° tiles
        should include E024 (which covers [24,25)), not stop at E023.
        """
        return (math.floor(value) // tile_size + 1) * tile_size

    def dem_tiles(self) -> list[tuple[str, str]]:
        """List of (N-tag, E-tag) Copernicus DEM tiles intersecting the bbox."""
        b = self.bbox
        ws = math.floor(b["west"])
        en = self._ceil_tile_edge(b["east"], 1)
        ss = math.floor(b["south"])
        nn = self._ceil_tile_edge(b["north"], 1)
        out = []
        for lat in range(ss, nn):
            n_tag = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            for lon in range(ws, en):
                e_tag = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
                out.append((n_tag, e_tag))
        return out

    def worldcover_tiles(self) -> list[tuple[str, str]]:
        """ESA WorldCover tile (N, E) tags. Tiles are 3° aligned to (39, 42, …)."""
        b = self.bbox
        ws = (math.floor(b["west"]) // 3) * 3
        en = self._ceil_tile_edge(b["east"], 3)
        ss = (math.floor(b["south"]) // 3) * 3
        nn = self._ceil_tile_edge(b["north"], 3)
        out = []
        for lat in range(ss, nn, 3):
            n_tag = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            for lon in range(ws, en, 3):
                e_tag = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
                out.append((n_tag, e_tag))
        return out


def load_config(argv: list[str] | None = None) -> EventCfg:
    """Parse --config from sys.argv and load the YAML."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path,
                        help="Event YAML config (see references/config_schema.md)")
    args, _ = parser.parse_known_args(argv)
    with open(args.config, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    raw = _apply_machine_overrides(raw)  # R1: layer machine-local env/paths
    cfg = EventCfg(raw=raw, config_path=args.config)
    setup_gdal_env(cfg.env)
    return cfg


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
