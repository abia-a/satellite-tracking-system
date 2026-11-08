"""Smoke tests for the packaged dashboard sample data and PDF report."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from satellite_tracking import satellite_report
from satellite_tracking.orbit.propagator import SatelliteTracker


SAMPLE_FILE = Path(__file__).parents[1] / "satellite_tracking" / "sample_tles.txt"


def test_report_tle_sample_has_valid_checksums():
    lines = [x for x in satellite_report.SAMPLE_TLES.splitlines() if x.startswith(("1 ", "2 "))]
    assert len(lines) == 6
    assert all(len(x) == 69 and int(x[68]) == satellite_report.tle_checksum(x) for x in lines)


def test_report_sgp4_agrees_with_skyfield_at_epoch():
    sat = SatelliteTracker.from_file(str(SAMPLE_FILE), "ISS (ZARYA)")
    s = satellite_report.SGP4(sat.name, sat.line1, sat.line2)
    sky = sat.state_at(s.epoch)
    other = satellite_report.state(s, s.epoch)
    assert abs(other["alt"] - sky.altitude_km) < 0.1
    assert abs(other["lat"] - sky.latitude_deg) < 0.01
    assert abs(other["lon"] - sky.longitude_deg) < 0.01


def test_pdf_report_writes_pdf(tmp_path, monkeypatch):
    out = tmp_path / "satellite_report_test.pdf"
    monkeypatch.setattr("sys.argv", ["satellite-report", "--at", "epoch", "--hours", "0.5",
                                    "--out", str(out)])
    satellite_report.main()
    assert out.read_bytes().startswith(b"%PDF-")
    assert out.stat().st_size > 10_000


def test_dashboard_sample_data_is_valid():
    pytest.importorskip("streamlit")
    from satellite_tracking.satellite_dashboard import SAMPLE_TLES, Satellite, parse_tles

    fleet = {name: Satellite(name, *lines) for name, lines in parse_tles(SAMPLE_TLES).items()}
    assert set(fleet) == {"ISS (ZARYA)", "HUBBLE SPACE TELESCOPE", "NOAA 19"}
