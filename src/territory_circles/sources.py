"""Public data sources: Census Reporter (population, land area, a target-population column) and
OpenStreetMap Nominatim (the centre point of a city). Network code lives only here."""
import json
import time
import urllib.parse
import urllib.request

from .core import centroid

CENSUS_API = "https://api.censusreporter.org/1.0"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "territory-circles/0.1 (open-source example)"  # set a contact in your own fork, per Nominatim policy
RELEASE = "acs2023_5yr"
TOTAL_POP = ("B01003", "B01003001")        # total population
DEFAULT_TARGET = ("B05006", "B05006167")   # foreign-born population from Brazil (example; any ACS column works)

_last_osm = [0.0]


def fetch_json(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3)


def osm_center(city, state):
    """(lat, lon) of a US city centre from Nominatim, or None. Sends only city and state.

    Nominatim usage policy: at most 1 request per second and an identifying User-Agent.
    """
    wait = 1.1 - (time.time() - _last_osm[0])
    if wait > 0:
        time.sleep(wait)
    _last_osm[0] = time.time()
    q = urllib.parse.urlencode({"city": city, "state": state, "country": "USA", "format": "json", "limit": 1})
    try:
        r = fetch_json(f"{NOMINATIM}?{q}")
        return (float(r[0]["lat"]), float(r[0]["lon"])) if r else None
    except (TypeError, KeyError, ValueError, IndexError):
        return None


def place(geoid):
    """Population, land area and centre of one Census geography (geoid like '16000US0667000')."""
    g = fetch_json(f"{CENSUS_API}/geo/tiger2023/{geoid}?geom=true")
    p = g.get("properties") or {}
    name = p.get("simple_name") or p.get("display_name") or geoid
    state = str(p.get("display_name") or "").split(",")[-1].strip()
    c = osm_center(name, state)
    source = "OpenStreetMap"
    if not c:
        if not g.get("geometry"):
            raise RuntimeError(f"no centre found for {geoid} ({name})")
        c, source = centroid(g["geometry"]), "census outline (CHECK: may be pulled toward water)"
    return {"name": name, "pop": int(p.get("population") or 0), "land_km2": float(p.get("aland") or 0) / 1e6,
            "lat": c[0], "lon": c[1], "center_source": source}


def target_counts(geoids, target=DEFAULT_TARGET):
    """{geoid: (total_population, target_count)} for the given geographies, in one request."""
    tables = f"{TOTAL_POP[0]},{target[0]}"
    q = urllib.parse.urlencode({"table_ids": tables, "geo_ids": ",".join(geoids)})
    d = fetch_json(f"{CENSUS_API}/data/show/latest?{q}")
    out = {}
    for gid in geoids:
        data = (d.get("data") or {}).get(gid) or {}
        total = data.get(TOTAL_POP[0], {}).get("estimate", {}).get(TOTAL_POP[1], 0) or 0
        tgt = data.get(target[0], {}).get("estimate", {}).get(target[1], 0) or 0
        out[gid] = (int(total), int(tgt))
    return out
