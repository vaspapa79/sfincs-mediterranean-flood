"""CODE-10 Stage 0a — extended preflight for the EMSR933 Crete run.

Complements `skill/scripts/run_pipeline.py --check` (tools/paths/creds presence) with:
numpy BLAS sanity, package versions, SFINCS binary + co-located DLLs, live credential
tests (CDS, EWDS, NASA Earthdata) and both _common import paths. Secrets are never printed.

Run with the sfincs-viz interpreter:
  <sfincs-viz>/python.exe reproduction/emsr933/scripts/preflight_stage0.py
Writes a JSON report next to this script's parent (reproduction/emsr933/preflight_stage0.json).
"""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVENT_DIR = HERE.parent                      # reproduction/emsr933
REPO = EVENT_DIR.parent.parent               # worktree root
WORKSPACE = Path("D:/ELKAK")
CLAUDE_SKILL = WORKSPACE / ".claude/skills/sfincs-flood-reproduction/scripts"

report: dict = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "python": sys.executable, "python_version": platform.python_version(),
                "checks": {}}
fails: list[str] = []


def rec(name: str, ok: bool, detail) -> None:
    report["checks"][name] = {"ok": bool(ok), "detail": detail}
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: {detail}")
    if not ok:
        fails.append(name)


# 1. numpy BLAS sanity (mkl-2026 numpy.dot crash guard)
import numpy as np  # noqa: E402
v = float(np.dot(np.eye(3), np.eye(3)).sum())
rec("numpy.dot(eye3,eye3).sum()==3.0", v == 3.0, v)
# conda-forge numpy links the generic libblas; the implementation is selected by the
# libblas build string (the mandatory `libblas=*=*openblas` pin), so read conda-meta.
meta = sorted((Path(sys.prefix) / "conda-meta").glob("libblas-*.json"))
builds = [json.loads(m.read_text(encoding="utf-8")).get("build", "") for m in meta]
rec("libblas pinned to openblas (conda-meta build string)",
    bool(builds) and all("openblas" in b for b in builds), builds or "no libblas in conda-meta")

# 2. package versions
vers = {}
for mod in ("numpy", "xarray", "hydromt", "hydromt_sfincs", "rasterio", "pyogrio", "geopandas",
            "shapely", "pyproj", "earthaccess", "cdsapi", "h5netcdf", "netCDF4", "yaml", "scipy"):
    try:
        m = importlib.import_module(mod)
        vers[mod] = getattr(m, "__version__", None) or importlib.metadata.version(mod)
    except Exception as e:
        vers[mod] = f"IMPORT FAILED: {e.__class__.__name__}: {e}"
try:
    import rasterio
    vers["GDAL(rasterio)"] = rasterio.__gdal_version__
except Exception:
    pass
try:
    import pyogrio
    vers["GDAL(pyogrio)"] = pyogrio.__gdal_version_string__
except Exception:
    pass
report["versions"] = vers
for k, val in vers.items():
    print(f"       {k:16s} {val}")
rec("hydromt 0.10.1 / hydromt_sfincs 1.2.2 (pinned)",
    vers.get("hydromt") == "0.10.1" and vers.get("hydromt_sfincs") == "1.2.2",
    f"hydromt {vers.get('hydromt')}, hydromt_sfincs {vers.get('hydromt_sfincs')}")

# 3. pipeline _common (worktree copy) + machine override
sys.path.insert(0, str(REPO / "skill" / "scripts"))
import _common  # noqa: E402
ov = _common.machine_override_path()
rec("worktree skill/scripts/_common import + machine override", ov is not None,
    f"_common={Path(_common.__file__).resolve()}  override={ov}")
ovd = _common._load_machine_override()
env = ovd.get("env", {}) or {}

# 4. tools from the override
for key in ("python", "hydromt", "sfincs_exe", "gdalbuildvrt", "gdal_data"):
    p = env.get(key)
    rec(f"env.{key}", bool(p) and Path(p).exists(), p)
try:
    out = subprocess.run([env["gdalbuildvrt"], "--version"], capture_output=True, text=True,
                         timeout=60)
    rec("gdalbuildvrt --version", out.returncode == 0, (out.stdout or out.stderr).strip())
except Exception as e:
    rec("gdalbuildvrt --version", False, str(e))
try:
    out = subprocess.run([env["hydromt"], "--version"], capture_output=True, text=True, timeout=120)
    rec("hydromt CLI --version", out.returncode == 0, (out.stdout or out.stderr).strip()[-200:])
except Exception as e:
    rec("hydromt CLI --version", False, str(e))

# 5. SFINCS binary + co-located DLLs
exe = Path(env.get("sfincs_exe", ""))
if exe.exists():
    dlls = sorted(p.name for p in exe.parent.glob("*.dll"))
    rec("sfincs.exe + DLLs co-located", len(dlls) > 0,
        f"{exe} ({exe.stat().st_size} B); {len(dlls)} DLLs")
    report["sfincs_dlls"] = dlls
else:
    rec("sfincs.exe + DLLs co-located", False, f"missing {exe}")

# 6. credentials files (never print secrets)
home = Path(os.path.expanduser("~"))
cds = home / ".cdsapirc"
cds_url = cds_key = None
if cds.exists():
    for ln in cds.read_text().splitlines():
        if ln.startswith("url:"):
            cds_url = ln.split(":", 1)[1].strip()
        if ln.startswith("key:"):
            cds_key = ln.split(":", 1)[1].strip()
rec("~/.cdsapirc url+key", bool(cds_url and cds_key),
    f"url={cds_url}  key={'<set>' if cds_key else None}")
netrc_info = {}
for nf in (home / ".netrc", home / "_netrc"):
    if nf.exists():
        txt = nf.read_text().split()
        netrc_info[str(nf)] = ("urs.earthdata.nasa.gov" in txt)
rec("Earthdata netrc (urs.earthdata.nasa.gov)", any(netrc_info.values()), netrc_info)


def pat_check(base: str) -> tuple[bool, str]:
    """Same call the ECMWF datastores client makes for check_authentication()."""
    url = base.rstrip("/") + "/profiles/v1/account/verification/pat"
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"PRIVATE-TOKEN": cds_key or "",
                                          "User-Agent": "elkak-emsr933-preflight"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return True, f"HTTP {r.status} {url}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} {url}"
    except Exception as e:
        return False, f"{e.__class__.__name__}: {e} ({url})"


ok, det = pat_check("https://cds.climate.copernicus.eu/api")
rec("CDS token live check", ok, det)
ok, det = pat_check("https://ewds.climate.copernicus.eu/api")
rec("EWDS token live check (same key)", ok, det)

try:
    import earthaccess
    auth = earthaccess.login(strategy="netrc")
    rec("Earthdata live login (earthaccess netrc)", bool(auth.authenticated),
        f"authenticated={auth.authenticated} (login redacted)")
except Exception as e:
    rec("Earthdata live login (earthaccess netrc)", False, f"{e.__class__.__name__}: {e}")

# 7. the .claude skill import path (validators of the NH era) — import in a subprocess
c_common = CLAUDE_SKILL / "_common.py"
if c_common.exists():
    code = ("import sys; sys.path.insert(0, r'%s'); import _common; print(_common.__file__)"
            % CLAUDE_SKILL)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    rec(".claude/skills/sfincs-flood-reproduction/scripts import", out.returncode == 0,
        (out.stdout or out.stderr).strip()[-300:])
else:
    rec(".claude/skills/sfincs-flood-reproduction/scripts import", False, f"missing {c_common}")
rec("SFINCS_SKILL_DIR unset (validator uses the worktree's own skill/)",
    "SFINCS_SKILL_DIR" not in os.environ, os.environ.get("SFINCS_SKILL_DIR"))

report["fails"] = fails
outp = EVENT_DIR / "preflight_stage0.json"
outp.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\n{'PREFLIGHT OK' if not fails else 'PREFLIGHT FAILED: ' + ', '.join(fails)}  -> {outp}")
sys.exit(1 if fails else 0)
