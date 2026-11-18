"""territory-circles CLI.

  geo         compute centre, density and radius for one territory from its Census geo ids (needs network)
  candidates  rank candidate cities by target-population share (needs network)
  pick        choose the best free territory for a person (offline, reads the CSV)
  check       explain what blocks a territory for a person (offline)
"""
import argparse
import csv
import datetime
import sys

from . import core

FIELDS = ["id", "name", "state", "geo_ids", "center_lat", "center_lon", "radius_km", "density_per_km2",
          "target_score", "status", "rest_until", "last_round", "last_by"]


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def today_arg(s):
    return datetime.date.fromisoformat(s) if s else datetime.date.today()


def cmd_geo(a):
    from . import sources
    rows = read_csv(a.csv)
    t = next((r for r in rows if r["id"] == a.id), None)
    if t is None:
        sys.exit(f"territory {a.id} not found")
    geoids = t["geo_ids"].split()
    places = [sources.place(g) for g in geoids]
    t.update({k: str(v) for k, v in core.circle(places).items()})
    write_csv(a.csv, rows)
    print(f"{a.id}: centre {t['center_lat']}, {t['center_lon']} | {t['density_per_km2']} people/km2 | "
          f"radius {t['radius_km']} km (" + ", ".join(f"{p['name']} [{p['center_source']}]" for p in places) + ")")


def cmd_candidates(a):
    from . import sources
    counts = sources.target_counts(a.geoids, (a.table, a.column))
    ranked = []
    for gid, (total, tgt) in counts.items():
        share = 100 * tgt / total if total else 0.0
        ranked.append({"geoid": gid, "population": total, "target_count": tgt, "share_pct": round(share, 2),
                       "score": core.target_score(share, tgt)})
    print("| Rank | Geo ID | Population | Target | Share % | Score |\n|---|---|---|---|---|---|")
    for i, c in enumerate(core.rank(ranked), 1):
        print(f"| {i} | {c['geoid']} | {c['population']:,} | {c['target_count']:,} | {c['share_pct']} | {c['score']} |")


def cmd_check(a):
    rows = read_csv(a.csv)
    t = next((r for r in rows if r["id"] == a.id), None)
    if t is None:
        sys.exit(f"territory {a.id} not found")
    why = core.blockers(t, rows, today_arg(a.today), a.me)
    print("FREE" if not why else "BLOCKED:\n- " + "\n- ".join(why))


def cmd_pick(a):
    rows = read_csv(a.csv)
    today = today_arg(a.today)
    free = [r for r in rows if not core.blockers(r, rows, today, a.me)]
    free.sort(key=lambda r: int(r.get("target_score") or 0), reverse=True)
    if not free:
        sys.exit("no free territory today")
    r = free[0]
    print(f"{r['id']} - {r['name']}, {r['state']} (score {r.get('target_score') or '?'}, radius {r.get('radius_km') or '?'} km)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="territory-circles")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("geo"); g.add_argument("csv"); g.add_argument("id"); g.set_defaults(f=cmd_geo)
    c = sub.add_parser("candidates"); c.add_argument("geoids", nargs="+")
    c.add_argument("--table", default="B05006"); c.add_argument("--column", default="B05006167",
                                                               help="ACS column of the target population")
    c.set_defaults(f=cmd_candidates)
    for name, f in (("check", cmd_check), ("pick", cmd_pick)):
        p = sub.add_parser(name); p.add_argument("csv")
        if name == "check":
            p.add_argument("id")
        p.add_argument("--me", required=True); p.add_argument("--today"); p.set_defaults(f=f)
    a = ap.parse_args(argv)
    a.f(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
