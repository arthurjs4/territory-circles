"""Pure geometry and rules for circular sales territories. No network, no files: easy to test."""
import datetime
import math

EARTH_KM = 6371.0


def km(a, b):
    """Great-circle distance in km between two (lat, lon) points."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return EARTH_KM * 2 * math.asin(math.sqrt(h))


def centroid(geom):
    """Area-weighted centroid (lat, lon) of a GeoJSON Polygon or MultiPolygon (outer rings only).

    Every polygon is weighted by its own area, so a tiny island does not drag the centre. This is only a fallback:
    for places whose official outline includes water, prefer a point-of-interest centre such as OpenStreetMap's
    (see the San Francisco note in the README).
    """
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    total = sx = sy = 0.0
    for poly in polys:
        ring = poly[0]
        a = cx = cy = 0.0
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            c = x1 * y2 - x2 * y1
            a += c
            cx += (x1 + x2) * c
            cy += (y1 + y2) * c
        if abs(a) < 1e-12:
            continue
        w = abs(a) / 2
        total += w
        sx += w * cx / (3 * a)
        sy += w * cy / (3 * a)
    if total == 0:
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        return sum(ys) / len(ys), sum(xs) / len(xs)
    return sy / total, sx / total


def radius_by_density(density):
    """Roughly 25 minutes by car: dense city 15 km, medium 25 km, sparse 35 km. Tune with your own results."""
    return 15 if density >= 2500 else 25 if density >= 800 else 35


def circle(places):
    """Combine places (dicts with pop, land_km2, lat, lon) into one territory circle.

    The centre is the population-weighted mean; the radius comes from density but is widened (in 5 km steps) so every
    place centre fits inside, plus a 5 km margin.
    """
    pop = sum(p["pop"] for p in places) or 1
    area = sum(p["land_km2"] for p in places) or 1
    w = sum((p["pop"] or 1) for p in places)
    lat = sum(p["lat"] * (p["pop"] or 1) for p in places) / w
    lon = sum(p["lon"] * (p["pop"] or 1) for p in places) / w
    density = pop / area
    reach = max(km((lat, lon), (p["lat"], p["lon"])) for p in places) + 5
    radius = max(radius_by_density(density), math.ceil(reach / 5) * 5)
    return {"center_lat": round(lat, 4), "center_lon": round(lon, 4), "radius_km": radius,
            "density_per_km2": round(density)}


def target_score(share_pct, target_count):
    """1 to 5 score for how concentrated the target population is; +1 for a big absolute count."""
    n = 5 if share_pct >= 10 else 4 if share_pct >= 6 else 3 if share_pct >= 3 else 2 if share_pct >= 1.5 else 1
    return min(5, n + (1 if target_count >= 10000 else 0))


def point(t):
    try:
        return float(t["center_lat"]), float(t["center_lon"]), float(t["radius_km"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_date(v):
    if not v:
        return None
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def blockers(t, territories, today, me, min_days_between_rounds=14, lock_days=90):
    """Reasons why `me` cannot work territory `t` today (empty list = free).

    A territory is blocked if it is resting, if it was worked too recently, or if its circle overlaps a circle that
    ANOTHER person worked within `lock_days`. Overlap = distance between centres < the larger of the two radii.
    """
    reasons = []
    resting_until = parse_date(t.get("rest_until"))
    if t.get("status") == "resting" and resting_until and resting_until > today:
        reasons.append(f"resting until {resting_until.isoformat()}")
    last = parse_date(t.get("last_round"))
    if last and (today - last).days < min_days_between_rounds:
        reasons.append(f"worked {(today - last).days} day(s) ago by {t.get('last_by') or '?'}")
    pt = point(t)
    for other in territories:
        if other is t or other.get("id") == t.get("id"):
            continue
        po = point(other)
        other_last = parse_date(other.get("last_round"))
        if not (pt and po and other_last):
            continue
        if other.get("last_by") and other.get("last_by") == me:
            continue
        if (today - other_last).days >= lock_days:
            continue
        dist = km(pt[:2], po[:2])
        if dist < max(pt[2], po[2]):
            reasons.append(f"overlaps {other['id']} ({dist:.0f} km apart), worked by {other.get('last_by') or '?'} "
                           f"{(today - other_last).days} day(s) ago")
    return reasons


def rank(candidates):
    """Sort candidate places by target score, then target share, then absolute count (best first)."""
    return sorted(candidates, key=lambda c: (c["score"], c["share_pct"], c["target_count"]), reverse=True)
