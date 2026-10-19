"""CODE-12 harness v1.4 (D1 + D2) — behaviour switch `harness_version`, build-yml rendering and the
post-build water-level boundary injection.

v1.3 (the default) must render the published as-run build records byte-identically (modulo the
machine-local Manning reclass-table path); v1.4 changes the implementation only:
  D1  IMERG half-hourly rates are written as left-labelled rates (cumulative_input=False,
      time_label=left); ERA5 hourly accumulations keep cumulative_input=True, time_label=right
      (ECMWF: accumulated over the hour ENDING at the validity time, so the right-to-left
      relabelling is the correct conversion for the block-left rates SFINCS expects).
  D2  water-level boundary points along the msk=2 cells with bzs = 0 m, and pavbnd = the reference
      atmospheric pressure in Pa (SFINCS v2.3.0 sfincs_boundaries.f90:796-800 applies the inverse
      barometer only when pavbnd > 1.0).

Run:  python -m unittest discover -s tests -v   (repo root, sfincs-viz env)
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skill" / "scripts"))

from _common import EventCfg, load_config  # noqa: E402
import build_model  # noqa: E402


def _raw(**over) -> dict:
    raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-02"},
           "window": {"spinup_days": 1, "pre_event_days": 1, "post_event_days": 0},
           "bbox": {"west": 23.0, "south": 35.0, "east": 23.1, "north": 35.09},
           "crs": {"epsg": 32634},
           "grid": {"res": 100, "zmax": 250},
           "paths": {"work_dir": "D:/tmp/synth", "deliverable_dir": "D:/tmp/synth/deliverable",
                     "manning_lookup": "D:/tmp/manning.csv"},
           "rain_source": "imerg_half_hourly",
           "coastal_bc": {"enabled": True, "pavbnd": 1},
           "wind_pressure": {"enabled": True}}
    raw.update(over)
    return raw


def _cfg(**over) -> EventCfg:
    return EventCfg(raw=_raw(**over), config_path=Path("synth.yaml"))


class HarnessVersion(unittest.TestCase):
    def test_default_is_v13(self):
        self.assertEqual(_cfg().harness_version, "v1.3")

    def test_v14_is_accepted(self):
        self.assertEqual(_cfg(harness_version="v1.4").harness_version, "v1.4")

    def test_unknown_version_is_rejected(self):
        with self.assertRaises(ValueError):
            _cfg(harness_version="v2.0").harness_version


class RenderBuildYmlV13(unittest.TestCase):
    """The default must reproduce the frozen as-run records of the published enhanced runs."""
    AS_RUN = {"emsr122_strymonas_enhanced.yaml": "emsr122_sfincs_enhanced",
              "emsr257_mandra_enhanced.yaml": "mandra_sfincs_enhanced",
              "emsr692_pineios_enhanced.yaml": "pineios_sfincs_enhanced"}

    def test_published_as_run_records_are_reproduced(self):
        for ex, asr in self.AS_RUN.items():
            cfg = load_config(["--config", str(REPO / "skill" / "examples" / ex)])
            rendered = build_model.render_build_yml(cfg)
            published = (REPO / "configs" / "as_run" / asr / "sfincs_build.yml").read_text()
            norm = lambda s: re.sub(r"reclass_table: .*", "reclass_table: X", s)  # noqa: E731
            self.assertEqual(norm(rendered), norm(published), ex)

    def test_v13_carries_no_v14_keys(self):
        y = build_model.render_build_yml(_cfg())
        for key in ("cumulative_input", "time_label", "setup_waterlevel", "101325"):
            self.assertNotIn(key, y)
        self.assertIn("  advection: 1\n  pavbnd: 1\n", y)

    def test_v13_precip_kwargs_are_the_hydromt_defaults(self):
        self.assertEqual(build_model.precip_forcing_kwargs(_cfg()), {})


class RenderBuildYmlV14(unittest.TestCase):
    def test_imerg_is_written_as_left_labelled_rates(self):
        y = build_model.render_build_yml(_cfg(harness_version="v1.4"))
        self.assertIn("setup_precip_forcing_from_grid:\n  precip: imerg_half_hourly\n  aggregate: false\n"
                      "  cumulative_input: false\n  time_label: left\n", y)

    def test_era5_accumulations_keep_the_right_label(self):
        y = build_model.render_build_yml(_cfg(harness_version="v1.4", rain_source="era5_hourly"))
        self.assertIn("setup_precip_forcing_from_grid:\n  precip: era5_hourly\n  aggregate: false\n"
                      "  cumulative_input: true\n  time_label: right\n", y)

    def test_precip_kwargs_follow_the_source(self):
        self.assertEqual(build_model.precip_forcing_kwargs(_cfg(harness_version="v1.4")),
                         {"cumulative_input": False, "time_label": "left"})
        self.assertEqual(build_model.precip_forcing_kwargs(_cfg(harness_version="v1.4", rain_source="era5_hourly")),
                         {"cumulative_input": True, "time_label": "right"})

    def test_pavbnd_is_the_reference_pressure_in_pa(self):
        y = build_model.render_build_yml(_cfg(harness_version="v1.4"))
        self.assertIn("  advection: 1\n  pavbnd: 101325\n", y)
        self.assertNotIn("pavbnd: 1\n", y)

    def test_coastal_bc_disabled_writes_no_pavbnd(self):
        y = build_model.render_build_yml(_cfg(harness_version="v1.4", coastal_bc={"enabled": False}))
        self.assertNotIn("pavbnd", y)

    def test_everything_else_is_unchanged(self):
        """v1.4 touches only zsini (D4, CODE-13), the pavbnd line and the precipitation kwargs."""
        a = build_model.render_build_yml(_cfg()).splitlines()
        b = build_model.render_build_yml(_cfg(harness_version="v1.4")).splitlines()
        self.assertEqual([ln for ln in b if ln not in a],
                         ["  zsini: -9999", "  pavbnd: 101325", "  cumulative_input: false", "  time_label: left"])
        self.assertEqual([ln for ln in a if ln not in b], ["  zsini: 0", "  pavbnd: 1"])


def _square_mask(n: int = 40, res: float = 100.0):
    """n x n UTM grid, all active, outer ring of msk=2 cells (closed water-level boundary)."""
    import xarray as xr
    import hydromt  # noqa: F401  (registers the .raster accessor)
    msk = np.ones((n, n), dtype=np.uint8)
    msk[0, :] = msk[-1, :] = msk[:, 0] = msk[:, -1] = 2
    x = 500_000.0 + res * (np.arange(n) + 0.5)
    y = 4_000_000.0 + res * (np.arange(n) + 0.5)
    da = xr.DataArray(msk, dims=("y", "x"), coords={"y": y, "x": x}, name="msk")
    da.raster.set_crs(32634)
    da.raster.set_nodata(0)
    return da


class WaterlevelBoundaryInjection(unittest.TestCase):
    """D2: bnd points along the msk=2 boundary at BND_SPACING_M with bzs = 0 m, written after the
    hydromt build (hydromt_sfincs.set_forcing_1d is unusable under pandas 3: RangeIndex.is_integer)."""

    def test_points_follow_the_spacing_and_sit_on_the_boundary(self):
        da = _square_mask()                       # ring of 40 cells x 100 m -> 16.0 km of boundary
        gdf = build_model.waterlevel_bnd_points(da, distance=1000.0)
        self.assertTrue(15 <= len(gdf) <= 17, len(gdf))
        self.assertEqual(gdf.crs.to_epsg(), 32634)
        x, y = gdf.geometry.x.values, gdf.geometry.y.values
        xmin, xmax = 500_000.0, 504_000.0
        ymin, ymax = 4_000_000.0, 4_004_000.0
        on_ring = ((np.abs(x - xmin) <= 100) | (np.abs(x - xmax) <= 100)
                   | (np.abs(y - ymin) <= 100) | (np.abs(y - ymax) <= 100))
        self.assertTrue(on_ring.all())

    def test_no_boundary_cells_gives_no_points(self):
        da = _square_mask()
        da = da.where(da != 2, 1).astype("uint8")
        da.raster.set_crs(32634)
        gdf = build_model.waterlevel_bnd_points(da, distance=1000.0)
        self.assertEqual(len(gdf), 0)

    def test_constants(self):
        self.assertEqual(build_model.BND_SPACING_M, 10_000.0)
        self.assertEqual(build_model.PAVBND_REF_PA, 101_325.0)

    def test_writer_creates_bnd_bzs_and_patches_inp(self):
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(geometry=[Point(500_000, 4_000_000), Point(501_000, 4_000_000)], crs=32634)
        with tempfile.TemporaryDirectory() as td:
            md = Path(td)
            (md / "sfincs.inp").write_text("tref                 = 20170101 000000\n"
                                           "tstart               = 20170102 000000\n"
                                           "tstop                = 20170103 000000\n"
                                           "pavbnd               = 101325.0\n")
            n = build_model.write_waterlevel_bnd(md, gdf, tref="20170101 000000", tstop="20170103 000000")
            self.assertEqual(n, 2)
            bnd = (md / "sfincs.bnd").read_text().split()
            self.assertEqual([float(v) for v in bnd], [500_000.0, 4_000_000.0, 501_000.0, 4_000_000.0])
            rows = [ln.split() for ln in (md / "sfincs.bzs").read_text().strip().splitlines()]
            self.assertEqual(len(rows), 2)                                   # tref .. tstop
            self.assertEqual([float(r[0]) for r in rows], [0.0, 172_800.0])
            self.assertTrue(all(float(v) == 0.0 for r in rows for v in r[1:]))
            inp = (md / "sfincs.inp").read_text()
            self.assertIn("bndfile = sfincs.bnd", inp)
            self.assertIn("bzsfile = sfincs.bzs", inp)
            build_model.write_waterlevel_bnd(md, gdf, tref="20170101 000000", tstop="20170103 000000")
            self.assertEqual((md / "sfincs.inp").read_text().count("bndfile"), 1)   # idempotent

    def test_writer_accepts_the_datetimes_hydromt_returns_from_a_read_config(self):
        """SfincsModel.read_config() hands back datetime objects, not 'YYYYmmdd HHMMSS' strings."""
        import datetime as dt
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(geometry=[Point(500_000, 4_000_000)], crs=32634)
        with tempfile.TemporaryDirectory() as td:
            md = Path(td)
            (md / "sfincs.inp").write_text("tref                 = 20170101 000000\n")
            build_model.write_waterlevel_bnd(md, gdf, tref=dt.datetime(2017, 1, 1), tstop=dt.datetime(2017, 1, 3))
            rows = [ln.split() for ln in (md / "sfincs.bzs").read_text().strip().splitlines()]
            self.assertEqual([float(r[0]) for r in rows], [0.0, 172_800.0])
            build_model.write_waterlevel_bnd(md, gdf, tref="2017-01-01 00:00:00", tstop="2017-01-03 00:00:00")
            rows = [ln.split() for ln in (md / "sfincs.bzs").read_text().strip().splitlines()]
            self.assertEqual([float(r[0]) for r in rows], [0.0, 172_800.0])


if __name__ == "__main__":
    unittest.main()
