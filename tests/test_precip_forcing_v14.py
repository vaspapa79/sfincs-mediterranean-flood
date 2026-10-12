"""CODE-12 D1 — the precipitation kwargs harness v1.4 passes to
hydromt_sfincs.SfincsModel.setup_precip_forcing_from_grid write the input x1.000 with no time
offset, for the F5 synthetic cases: half-hourly IMERG-like rates (time stamp = START of the 30-min
interval) and hourly ERA5-like accumulations (time stamp = END of the hour, ECMWF convention).

In-process hydromt (no SFINCS run). Run: python -m unittest tests.test_precip_forcing_v14 -v
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
os.environ.setdefault("GDAL_DATA", str(Path(sys.executable).parent / "Library" / "share" / "gdal"))

from _common import EventCfg  # noqa: E402
import build_model  # noqa: E402

LAT = np.array([35.08, 35.04, 35.00, 34.96, 34.92])   # around the 5x5 km test grid (UTM 34N 500000, 3870000)
LON = np.array([20.90, 20.95, 21.00, 21.05, 21.10])


def _cfg(rain_source, version="v1.4") -> EventCfg:
    raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-01"},
           "bbox": {"west": 23.0, "south": 35.0, "east": 23.1, "north": 35.09}, "crs": {"epsg": 32634},
           "paths": {"work_dir": "D:/tmp/synth", "deliverable_dir": "D:/tmp/synth/d"},
           "rain_source": rain_source, "harness_version": version}
    return EventCfg(raw=raw, config_path=Path("synth.yaml"))


def _da(stamps, values):
    import pandas as pd
    import xarray as xr
    import hydromt  # noqa: F401
    data = np.zeros((len(stamps), LAT.size, LON.size), dtype="float32")
    for i, v in enumerate(values):
        data[i] = v
    da = xr.DataArray(data, dims=("time", "latitude", "longitude"),
                      coords={"time": pd.to_datetime(stamps), "latitude": LAT, "longitude": LON},
                      name="precip", attrs={"units": "mm/h"})
    da.raster.set_crs(4326)
    return da


def _written(stamps, values, tstop, **kw):
    """Spatial-mean written rate per time stamp, through the real hydromt method."""
    from hydromt_sfincs import SfincsModel
    root = Path(tempfile.mkdtemp(prefix="precip_v14_"))
    try:
        mod = SfincsModel(root=str(root), mode="w+")
        mod.setup_config(tref="20170101 000000", tstart="20170101 000000", tstop=tstop)
        mod.setup_grid(x0=500000, y0=3870000, dx=1000, dy=1000, nmax=5, mmax=5, rotation=0, epsg=32634)
        mod.setup_precip_forcing_from_grid(precip=_da(stamps, values), aggregate=False, **kw)
        da = mod.forcing["precip_2d"]
        return {str(t)[:16]: float(v) for t, v in zip(da["time"].values, da.mean(dim=("y", "x")).values)}
    finally:
        shutil.rmtree(root, ignore_errors=True)


class HalfHourlyRates(unittest.TestCase):
    """IMERG: 10 mm/h stamped at 00:00, 00:30, 01:00, 01:30 (interval starts) = 20 mm."""
    STAMPS = ["2017-01-01T00:00", "2017-01-01T00:30", "2017-01-01T01:00", "2017-01-01T01:30"]

    def test_v14_passes_the_rates_through_unchanged(self):
        kw = build_model.precip_forcing_kwargs(_cfg("imerg_half_hourly"))
        out = _written(self.STAMPS, [10, 10, 10, 10], "20170101 013000", **kw)
        self.assertEqual([out[s] for s in self.STAMPS], [10.0, 10.0, 10.0, 10.0])   # x1.000
        self.assertAlmostEqual(sum(out.values()) * 0.5, 20.0)                      # total preserved

    def test_v14_pulse_keeps_its_time_stamp(self):
        kw = build_model.precip_forcing_kwargs(_cfg("imerg_half_hourly"))
        stamps = [f"2017-01-01T0{h}:{m}" for h in range(4) for m in ("00", "30")]
        values = [0, 0, 10, 0, 0, 0, 0, 0]                                           # 10 mm/h at 01:00 only
        out = _written(stamps, values, "20170101 033000", **kw)
        self.assertEqual(out["2017-01-01T01:00"], 10.0)
        self.assertEqual(sum(v for k, v in out.items() if k != "2017-01-01T01:00"), 0.0)   # 0-min offset

    def test_v13_defaults_reproduce_the_f5_defect(self):
        """Documents what v1.4 fixes: the hydromt defaults give x2 and -30 min (F5_VERIFY (b))."""
        kw = build_model.precip_forcing_kwargs(_cfg("imerg_half_hourly", version="v1.3"))
        self.assertEqual(kw, {})
        out = _written(self.STAMPS, [10, 10, 10, 10], "20170101 013000", **kw)
        self.assertEqual([out[s] for s in self.STAMPS], [20.0, 20.0, 20.0, 0.0])


class HourlyAccumulations(unittest.TestCase):
    """ERA5: 10 mm accumulated over 00:00-01:00 is stamped 01:00 (ECMWF: accumulations are over the
    hour ending at the validity date/time); SFINCS wants the rate at the START of its interval."""
    STAMPS = ["2017-01-01T00:00", "2017-01-01T01:00", "2017-01-01T02:00", "2017-01-01T03:00"]

    def test_v14_puts_the_hour_on_its_physical_interval(self):
        kw = build_model.precip_forcing_kwargs(_cfg("era5_hourly"))
        out = _written(self.STAMPS, [0, 10, 0, 0], "20170101 030000", **kw)
        self.assertEqual(out["2017-01-01T00:00"], 10.0)                            # x1.000 on [00:00, 01:00)
        self.assertEqual(sum(v for k, v in out.items() if k != "2017-01-01T00:00"), 0.0)   # 0-min physical offset

    def test_v14_total_is_preserved(self):
        kw = build_model.precip_forcing_kwargs(_cfg("era5_hourly"))
        out = _written(self.STAMPS, [0, 10, 10, 10], "20170101 030000", **kw)     # 30 mm over 00:00-03:00
        self.assertAlmostEqual(sum(out.values()) * 1.0, 30.0)

    def test_era5_kwargs_equal_the_v13_behaviour(self):
        """The baseline (ERA5) forcing is NOT changed by v1.4: same written field as the defaults."""
        kw14 = build_model.precip_forcing_kwargs(_cfg("era5_hourly"))
        out14 = _written(self.STAMPS, [0, 10, 5, 2], "20170101 030000", **kw14)
        out13 = _written(self.STAMPS, [0, 10, 5, 2], "20170101 030000")
        self.assertEqual(out14, out13)


if __name__ == "__main__":
    unittest.main()
