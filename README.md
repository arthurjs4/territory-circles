# territory-circles

Turn cities into **circular sales territories** using only public data, and stop two people from working overlapping areas.

## Why

When a small team prospects local businesses, "which city do I work next?" gets messy: city names overlap, metro areas blur, and two people end up contacting the same neighbourhood. A circle (centre + radius) is a simple, honest model: the distance between two centres tells you if territories collide.

The tool combines:

- **[Census Reporter](https://censusreporter.org/)** (ACS data): total population, land area and one configurable *target population* column (for example people born in a given country, table `B05006`).
- **[OpenStreetMap Nominatim](https://nominatim.org/)**: the centre point of each city (1 request per second, identifying User-Agent, only city and state are sent).
- **Density-based radius**: dense city 15 km, medium 25 km, sparse 35 km (about 25 minutes by car), widened in 5 km steps so every place of a multi-city territory fits.
- **Distance blocking**: a territory is blocked if it is resting, worked too recently, or its circle overlaps a circle another person worked in the last 90 days.
- **Candidate ranking**: rank cities by share of the target population, with a 1 to 5 score.

## The San Francisco anecdote (why the centre comes from OpenStreetMap)

The first version took the "internal point" of the official Census outline as the city centre. For San Francisco that landed far out in the Pacific: the official city boundary includes water and the **Farallon Islands**, about 30 miles offshore, so the geometric centre was dragged toward the sea. The fix: use OpenStreetMap's city-centre point as the primary centre, and keep the outline centroid only as a fallback (weighting each polygon by its own area so tiny islands do not drag it). The fallback is labelled `CHECK` in the output so a human looks at it.

## Install

```bash
pip install .      # Python 3.9+, standard library only
```

## Usage

```bash
# rank candidate places by target-population share (ACS 5-year data, one request)
territory-circles candidates 16000US0000001 16000US0000002 --column B05006167

# compute centre, density and radius of territory T01 from the geo ids in the CSV (writes the CSV)
territory-circles geo examples/territories.csv T01

# offline: what blocks T02 for "bruno" today? and which free territory should he take?
territory-circles check examples/territories.csv T02 --me bruno --today 2026-03-01
territory-circles pick  examples/territories.csv --me bruno --today 2026-03-01
```

`examples/territories.csv` uses fictitious places and made-up coordinates. Real geo ids look like `16000US0667000` (a place) or `86000US02139` (a ZIP code).

## Example output

```
$ territory-circles check examples/territories.csv T02 --me bruno --today 2026-03-01
BLOCKED:
- overlaps T01 (11 km apart), worked by ana 9 day(s) ago

$ territory-circles pick examples/territories.csv --me bruno --today 2026-03-01
T03 - Demo City, XX (score 3, radius 15 km)

$ territory-circles candidates ...
| Rank | Geo ID | Population | Target | Share % | Score |
|---|---|---|---|---|---|
| 1 | 16000US0000001 | 120,000 | 9,600 | 8.0 | 4 |
| 2 | 16000US0000002 | 80,000 | 800 | 1.0 | 1 |
```

## Tests

```bash
pip install pytest && pytest
```

The tests cover geometry, radius, blocking and scoring, offline.

## Limitations

- US only (Census geographies). Census Reporter is a third-party service and may be rate-limited or change its API.
- Circles are an approximation: they ignore rivers, highways and borders.
- The radius thresholds are a starting point; calibrate them with your own results.
- Respect the Nominatim usage policy and put your own contact in the User-Agent (`sources.py`) if you fork this.

## License

MIT

## Resumo em português

Transforma cidades em territórios de venda em forma de círculo (centro + raio) usando dados públicos: população e uma coluna-alvo do Censo (via Census Reporter) e o centro da cidade pelo OpenStreetMap. O raio vem da densidade. Dois territórios se bloqueiam quando os círculos se sobrepõem e a outra pessoa trabalhou ali nos últimos 90 dias. Curiosidade: o centro de São Francisco pelo contorno do Censo caía perto das ilhas Farallon, em pleno mar; por isso o centro vem do OpenStreetMap. Só EUA; os raios são ponto de partida.
