"""
test_orbit.py — Phase 1 unit tests

Validates:
1. TLE loading from file works and yields the right satellite.
2. Propagated altitude/velocity fall in physically sane ranges for
   known orbit types (LEO here).
3. Orbital period computed from mean motion matches the well-known
   ISS period (~90-93 minutes) within tolerance.
4. Apogee > Perigee always holds (sanity check on element extraction).

Run with:  pytest tests/test_orbit.py -v
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from satellite_tracking.orbit.propagator import SatelliteTracker
from satellite_tracking.orbit.orbital_parameters import extract_orbital_elements

SAMPLE_FILE = Path(__file__).parent.parent / "satellite_tracking" / "sample_tles.txt"
SAMPLE_EPOCH = datetime(2024, 2, 14, 12, 25, tzinfo=timezone.utc)


@pytest.fixture
def iss_tracker():
    return SatelliteTracker.from_file(str(SAMPLE_FILE), satellite_name="ISS (ZARYA)")


def test_loads_correct_satellite(iss_tracker):
    assert iss_tracker.name == "ISS (ZARYA)"


def test_file_missing_satellite_raises():
    with pytest.raises(KeyError):
        SatelliteTracker.from_file(str(SAMPLE_FILE), satellite_name="NOT A REAL SATELLITE")


def test_altitude_in_leo_range(iss_tracker):
    """ISS orbits roughly 370-460 km; TLE age drift can widen this
    slightly, so we use a generous but still physically meaningful band."""
    state = iss_tracker.state_at(SAMPLE_EPOCH)
    assert 150 < state.altitude_km < 600, (
        f"Altitude {state.altitude_km} km is outside plausible ISS LEO range "
        "(this can happen with a very stale TLE — check TLE epoch)."
    )


def test_velocity_in_leo_range(iss_tracker):
    """LEO orbital velocity is close to ~7.5-7.8 km/s."""
    state = iss_tracker.state_at(SAMPLE_EPOCH)
    assert 6.5 < state.velocity_kms < 8.5


def test_orbital_period_matches_known_iss_value(iss_tracker):
    elements = extract_orbital_elements(iss_tracker.satellite)
    assert 88 < elements.orbital_period_minutes < 95


def test_apogee_greater_than_or_equal_perigee(iss_tracker):
    elements = extract_orbital_elements(iss_tracker.satellite)
    assert elements.apogee_altitude_km >= elements.perigee_altitude_km


def test_eccentricity_is_near_circular_for_iss(iss_tracker):
    elements = extract_orbital_elements(iss_tracker.satellite)
    assert 0 <= elements.eccentricity < 0.01


def test_multiple_satellites_in_same_file():
    hubble = SatelliteTracker.from_file(str(SAMPLE_FILE), satellite_name="HUBBLE SPACE TELESCOPE")
    noaa = SatelliteTracker.from_file(str(SAMPLE_FILE), satellite_name="NOAA 19")
    assert hubble.name != noaa.name


def test_bad_checksum_is_rejected(iss_tracker):
    bad_line1 = iss_tracker.line1[:-1] + ("0" if iss_tracker.line1[-1] != "0" else "1")
    with pytest.raises(ValueError, match="checksum"):
        SatelliteTracker.from_manual_tle("Bad", bad_line1, iss_tracker.line2)


def test_tle_lines_must_have_same_norad(iss_tracker):
    noaa = SatelliteTracker.from_file(str(SAMPLE_FILE), satellite_name="NOAA 19")
    with pytest.raises(ValueError, match="NORAD"):
        SatelliteTracker.from_manual_tle("Mixed", iss_tracker.line1, noaa.line2)
