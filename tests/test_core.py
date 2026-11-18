import datetime

from territory_circles import core

TODAY = datetime.date(2026, 3, 1)


def test_km_known_distance():
    # roughly 111 km per degree of latitude
    assert 110 < core.km((0, 0), (1, 0)) < 112


def test_radius_by_density():
    assert core.radius_by_density(5000) == 15
    assert core.radius_by_density(1000) == 25
    assert core.radius_by_density(100) == 35


def test_centroid_ignores_tiny_island():
    mainland = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    island = [[100, 100], [100.01, 100], [100.01, 100.01], [100, 100.01], [100, 100]]
    lat, lon = core.centroid({"type": "MultiPolygon", "coordinates": [[mainland], [island]]})
    assert abs(lat - 5) < 0.1 and abs(lon - 5) < 0.1


def test_circle_widens_for_far_places():
    places = [{"pop": 1000, "land_km2": 100, "lat": 40.0, "lon": -75.0},
              {"pop": 1000, "land_km2": 100, "lat": 40.0, "lon": -74.5}]
    c = core.circle(places)
    assert c["radius_km"] >= 30 and c["radius_km"] % 5 == 0


def test_target_score():
    assert core.target_score(12, 500) == 5
    assert core.target_score(2, 20000) == 3
    assert core.target_score(0.5, 10) == 1


def terr(i, lat, lon, r, last=None, by=None, **kw):
    return {"id": i, "center_lat": lat, "center_lon": lon, "radius_km": r, "last_round": last, "last_by": by, **kw}


def test_overlap_blocks_other_person():
    a = terr("T1", 40.0, -75.0, 25, "2026-02-20", "ana")
    b = terr("T2", 40.1, -75.0, 25)
    rows = [a, b]
    assert core.blockers(b, rows, TODAY, "bruno")
    assert not core.blockers(b, rows, TODAY, "ana")


def test_far_territory_is_free_and_lock_expires():
    a = terr("T1", 40.0, -75.0, 25, "2026-02-20", "ana")
    far = terr("T3", 45.0, -75.0, 25)
    assert not core.blockers(far, [a, far], TODAY, "bruno")
    old = terr("T4", 40.0, -75.0, 25, "2025-10-01", "ana")
    near = terr("T5", 40.1, -75.0, 25)
    assert not core.blockers(near, [old, near], TODAY, "bruno")


def test_min_days_and_resting():
    t = terr("T1", 40, -75, 25, "2026-02-25", "ana")
    assert any("day(s) ago" in r for r in core.blockers(t, [t], TODAY, "ana"))
    r = terr("T2", 41, -75, 25, status="resting", rest_until="2026-04-01")
    assert any("resting" in x for x in core.blockers(r, [r], TODAY, "ana"))
