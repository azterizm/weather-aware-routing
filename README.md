# Weather-Aware Truck Routing

A React + Django web app that helps a truck driver choose the safest route based on
**weather, load weight and travel time**.

The driver enters an origin, destination, departure date/time and load weight. The app then:

1. gets **3 truck route options** from TomTom;
2. places **checkpoints every 10 / 25 / 50 miles** along each route and estimates the truck's
   **ETA** at each one;
3. samples the hourly weather forecast (Open-Meteo) **at each checkpoint's ETA**;
4. classifies each checkpoint with the **risk and load rules** below;
5. **recommends** the best route (fewest Severe miles → fewest High miles → lowest average
   risk → shortest travel time);
6. shows the routes, checkpoints, risk levels, ETAs and route summaries on a map, with a
   **weather-risk heatmap along the trip corridor** and a **0–48 hour forecast slider**.

## Contents

- [Architecture](#architecture)
- [Risk model](#risk-model)
- [API](#api)
- [Running locally](#running-locally)
- [Configuration](#configuration)
- [Performance and stability](#performance-and-stability)
- [Deployment](#deployment)
- [Assumptions and limitations](#assumptions-and-limitations)

## Architecture

Monorepo, single deployable: Django serves the REST API **and** the built single-page app.

```
backend/                 Django 5.2 LTS + Django REST Framework (Python 3.13, uv)
  config/                settings (environment-driven), URLs, WSGI
  trips/
    domain/              pure logic, no I/O: risk rules, geometry, checkpoints/ETAs,
                         weather-at-time selection, ranking
    providers/           TomTom (geocoding, truck routing) and Open-Meteo clients
    services/            orchestration: route options, trip planner, corridor heatmap
    api/                 request validation, JSON presenters, views, error handler
    tests/               pytest (fixtures are trimmed real provider responses)
frontend/                Vite + React 19 + TypeScript + MUI + react-leaflet
  src/api/               axios client (error normalisation) and typed endpoint calls
  src/hooks/             TanStack Query hooks (plan, corridor heatmap, place search)
  src/components/        TripForm, RouteSummaries, Map (routes, checkpoints, heatmap, slider)
Dockerfile               multi-stage: build SPA → Python runtime (gunicorn + WhiteNoise)
heroku.yml               Heroku container-stack build
```

Request flow:

```
Browser (React SPA)
  │  GET  /api/geocode/?q=…              → TomTom Search (typeahead)
  │  POST /api/trips/plan/               → TomTom Calculate Route (truck, 2 alternatives)
  │                                        → checkpoints + ETAs → Open-Meteo (one batched call)
  │                                        → risk → summaries → recommendation
  │  POST /api/trips/corridor-weather/   → corridor grid → Open-Meteo (0–48 h) → risk matrix
  ▼
Django REST API (stateless, no database)
```

The heatmap is a separate request, so routes and checkpoints render first and the heatmap
follows.

## Risk model

### Weather thresholds

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 – < 35 | 35 – < 45 | 45 – < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 – < 0.25 | 0.25 – < 0.50 | 0.50 – 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 – < 1.0 | 1.0 – < 2.0 | 2.0 – 3.0 | > 3.0 |

The spec's ranges share endpoints (e.g. rain "0.10–0.25" and "0.25–0.50"). They are read as
half-open intervals, so **a shared endpoint belongs to the higher level** (35 mph is High,
0.25 in/hr is High). The No Travel thresholds for rain and snow are strict (`>`), so exactly
1.00 in/hr rain or 3.0 in/hr snow is Severe. Wind values like 34.6 mph fall in "25–34"
(Moderate).

### Load rules

- Wind ≥ 55 mph → **No Travel** for any load.
- Wind 45–54 mph and load > 30,000 lb → **No Travel**.
- Wind 35–44 mph and load > 40,000 lb → **Severe**.

A checkpoint's risk is the **worst** of (load-adjusted wind, rain, snow). Tooltips show
which factor and which load rule set the level.

### Weather inputs

- **Wind** is Open-Meteo `wind_speed_10m` (sustained wind at 10 m, mph). It is an
  instantaneous value, so it is linearly interpolated between the two hours around the ETA.
- **Rain** is `rain + showers` (large-scale plus convective liquid precipitation), and
  **snow** is `snowfall`, both in inches. Open-Meteo reports these as totals for the
  *preceding* hour, so the value stamped `floor(ETA) + 1 h` is used: it covers the hour the
  truck is driving through, and that one-hour total is the in/hr rate.
- Units are requested in mph and inches and checked against the response's `hourly_units`.
  Anything unexpected is converted or rejected.

### Checkpoints and ETAs

- **Sampling interval** is fixed by trip length and is the same for all three routes, so
  their miles compare fairly. It is set from the shortest route option: under 250 mi →
  **10 mi**, 250–1,000 mi → **25 mi**, over 1,000 mi → **50 mi**.
- Checkpoints sit at mile 0, N, 2N, … plus the destination. A regular mark within 10% of an
  interval of the destination is merged into it.
- **ETA** = departure + TomTom's travel time to that point on the route. TomTom returns
  traffic-aware cumulative travel times for points along the polyline; between those points
  the time is interpolated by distance.
- Each checkpoint **covers** half the distance to each neighbouring checkpoint, so covered
  miles add up exactly to the route length. "Severe miles", "High miles" and so on are
  sums of covered miles.
- **Average risk** = mean risk score weighted by covered miles (Low 0, Moderate 1, High 2,
  Severe 3, No Travel 4).

### Recommendation

Routes are ranked by this key, compared in order:

1. fewest **No Travel** miles (the spec doesn't list this level, but it is strictly worse
   than Severe, so it is compared first)
2. fewest **Severe** miles
3. fewest **High** miles
4. lowest **average risk**
5. shortest **travel time**

Miles are compared at 0.1 mi and average risk at 0.01, so floating-point noise cannot decide
a ranking. The UI explains the first criterion on which the winner beat the runner-up, e.g.
*"Fewest Severe miles: 0 mi vs 42 mi on Route B."*

### Three route options

TomTom is asked for the best route plus 2 alternatives. For some trips it returns fewer
(for example, long-haul trips with a future departure often return 2). When that happens
the app tops up with **detour routes** through a via point offset ±12% of the straight-line
distance at the midpoint. A detour is accepted only if it is at most 1.5× the primary
route's length and shares less than 80% of its path with an existing option. If three
distinct routes still can't be found, the UI says so.

### Corridor heatmap

The corridor is every grid cell within **25 miles** of any route option. The grid starts at
0.1° and coarsens automatically to stay within 250 cells (one forecast location each). For
each cell and each hour from **departure +0 h to +48 h** (the slider), the same weather
selection and risk rules apply, **including the load rules**, so the heatmap shows risk for
this truck.

## API

All endpoints are under `/api/`, take and return JSON, and use UTC ISO 8601 timestamps
(inputs must include an offset). Errors share one shape:

```json
{ "detail": "Human-readable message", "code": "invalid", "fields": { "load_weight_lbs": ["…"] } }
```

| Status | `code` | When |
|---|---|---|
| 400 | `invalid` | validation failed (`fields` lists per-field messages) |
| 422 | `no_route` | no truck route between the places |
| 429 | `throttled` | per-IP rate limit reached |
| 503 | `upstream_unavailable` / `quota_exceeded` | TomTom or Open-Meteo failed or hit its quota |

### `GET /api/health/`

Returns `{"status": "ok"}`.

### `GET /api/geocode/?q=denver`

Place suggestions for the form (the query needs at least 3 characters).

```json
{ "results": [{ "label": "Denver, CO", "lat": 39.738453, "lon": -104.984853 }] }
```

### `POST /api/trips/plan/`

Request:

```json
{
  "origin": { "label": "Dallas, TX", "lat": 32.7767, "lon": -96.797 },
  "destination": { "label": "Denver, CO", "lat": 39.7392, "lon": -104.9903 },
  "departure_time": "2026-11-01T08:00:00-05:00",
  "load_weight_lbs": 42000
}
```

Validation:
- Departure is from 15 minutes ago up to 7 days ahead.
- Load is 1–80,000 lb.
- Origin and destination must be different places.

Response (abridged):

```json
{
  "departure_time": "2026-11-01T13:00:00Z",
  "load_weight_lbs": 42000.0,
  "checkpoint_interval_miles": 25,
  "recommended_route_id": "route-2",
  "recommendation_reason": "Fewest Severe miles: 0 mi vs 50 mi on Route A.",
  "warnings": [],
  "routes": [
    {
      "id": "route-1", "label": "Route A",
      "distance_miles": 882.3, "duration_seconds": 42715,
      "departure_time": "2026-11-01T13:00:00Z", "arrival_time": "2026-11-02T00:51:55Z",
      "geometry": "<Google encoded polyline, precision 5>",
      "summary": {
        "miles_by_risk": { "LOW": 832.3, "MODERATE": 0, "HIGH": 0, "SEVERE": 50, "NO_TRAVEL": 0, "UNKNOWN": 0 },
        "average_risk": 0.17, "max_risk": "SEVERE"
      },
      "checkpoints": [
        {
          "index": 1, "mile": 25.0, "lat": 33.07, "lon": -97.03, "eta": "2026-11-01T13:24:10Z",
          "weather": { "wind_mph": 38.2, "rain_in_hr": 0.0, "snow_in_hr": 0.0 },
          "risk": "SEVERE",
          "factors": { "wind": "SEVERE", "rain": "LOW", "snow": "LOW", "load_rule": "wind_35_44_load_over_40000" }
        }
      ]
    }
  ]
}
```

Weather values in responses are **rounded down** for display, so a shown value never
crosses a threshold (for example, 34.96 mph Moderate is shown as 34.9, not 35.0).

### `POST /api/trips/corridor-weather/`

Request: the plan's route geometries (1–3 encoded polylines), its `departure_time` as
`start_time`, and the load:

```json
{ "routes": ["<encoded>", "…"], "start_time": "2026-11-01T13:00:00Z", "load_weight_lbs": 42000 }
```

Response: 49 hourly timestamps and per-cell matrices indexed `[hour][cell]`:

```json
{
  "hours": ["2026-11-01T13:00:00Z", "… 49 total"],
  "cell_size_deg": 0.31241,
  "cells": [[33.12, -97.18], "…"],
  "risk": [[0, 1, 3, "…"], "…"],
  "wind_mph": [[12.3, "…"]], "rain_in_hr": [[0.0, "…"]], "snow_in_hr": [[0.0, "…"]]
}
```

Risk scores are 0 (Low) to 4 (No Travel); −1 means the forecast was unavailable.

## Running locally

Prerequisites: [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 itself), Node 22 or
newer (24 recommended, see `frontend/.nvmrc`), and a free
[TomTom API key](https://developer.tomtom.com/). Open-Meteo needs no key.

```bash
cp .env.example .env          # then set TOMTOM_API_KEY
make install                  # uv sync + npm ci
make dev-backend              # Django API on http://127.0.0.1:8000
make dev-frontend             # Vite on http://localhost:5173 (proxies /api to Django)
```

Open http://localhost:5173.

Quality checks:

```bash
make test                     # pytest (backend) + Vitest (frontend)
make lint                     # ruff + ESLint + tsc + Prettier
```

## Configuration

All settings come from environment variables. Locally they are read from the root `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `TOMTOM_API_KEY` | — (required) | TomTom routing and geocoding |
| `DJANGO_SECRET_KEY` | — (required when not in debug) | Django secret key |
| `DJANGO_DEBUG` | `0` | `1` for local development |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated host names |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` | redirect HTTP→HTTPS when not in debug |
| `OPEN_METEO_API_KEY` | empty | optional commercial Open-Meteo key |
| `GEOCODE_COUNTRY_SET` | `US` | geocoding country filter |
| `CORRIDOR_MAX_CELLS` | `250` | heatmap cell cap (one forecast location per cell) |
| `THROTTLE_PLAN` / `THROTTLE_CORRIDOR` / `THROTTLE_GEOCODE` | `20/min` / `20/min` / `60/min` | per-IP rate limits |
| `WEB_CONCURRENCY` | `2` | gunicorn worker processes (4 threads each) |

## Performance and stability

- **Request budget.** Heroku cuts requests off at 30 s, so every outbound call has an
  explicit timeout: routing 14 s, detours 6 s, weather 8 s. Detours are skipped if the main
  routing call already took 12 s. Connection errors and 429/5xx responses are retried once
  or twice with backoff; read timeouts are not retried. Typical plan times: ~2 s for a
  regional trip and ~5–8 s for long-haul, where most of the time is TomTom's truck routing.
- **Few upstream calls.** A plan makes one routing call (plus at most two detour calls run in
  parallel) and one batched weather call for every checkpoint of every route. Checkpoints
  are snapped to a 0.05° grid and deduplicated, since alternative routes overlap a lot.
  Weather requests are split into batches of up to 100 locations and run in parallel.
- **Caching.** Geocoding results are cached for 24 h and forecasts for 30 min (in-process
  cache). Identical plan requests in the browser are served from the TanStack Query cache.
- **Small payloads.** Route geometry is simplified (Ramer–Douglas–Peucker, ~30 m tolerance)
  and polyline-encoded after the checkpoints have been computed on the full geometry. API
  responses are gzipped. The SPA is pre-compressed with Brotli and gzip, hashed assets are
  cached immutably, and `index.html` is never cached.
- **Fast first paint.** The map code (Leaflet) is a lazily loaded chunk. React and MUI are
  separate long-lived vendor chunks.
- **Smooth map.** Layers are canvas-rendered and memoised, and slider updates go through
  `useDeferredValue`, so only cell colours change between hours.
- **Safety.**
  - Input is validated on both client and server.
  - API keys are never logged: the TomTom key is redacted, and upstream errors are re-raised
    without URLs.
  - Per-IP throttling protects the provider quotas.
  - The production settings include strict security headers, HSTS, and a non-root container
    user.

## Deployment

The app ships as one Docker image (see `Dockerfile`). Heroku's container stack is set up
through `heroku.yml`:

```bash
heroku create <app-name>
heroku stack:set container -a <app-name>
heroku config:set -a <app-name> \
  TOMTOM_API_KEY=… \
  DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  DJANGO_ALLOWED_HOSTS=<app-name>.herokuapp.com
git push heroku main
```

The same image runs on Azure App Service (Web App for Containers) or any container host.
Set the same variables, plus `WEBSITES_PORT=8000` on Azure.

Run the image locally:

```bash
docker build -t weather-aware-routing .
docker run --rm -p 8000:8000 -e TOMTOM_API_KEY=… -e DJANGO_SECRET_KEY=dev \
  -e DJANGO_ALLOWED_HOSTS=localhost -e DJANGO_SECURE_SSL_REDIRECT=0 weather-aware-routing
```

CI (GitHub Actions) runs lint, type checks and tests for both halves, builds the SPA, and
builds the Docker image.

## Assumptions and limitations

- **Load weight only feeds the risk rules.** It is not sent to TomTom as gross vehicle
  weight, because that would need an assumed tractor/trailer weight.
- **ETAs are driving time from TomTom** (traffic-aware for the departure time). They don't
  include rest breaks or hours-of-service limits.
- **Times** are entered and shown in the browser's time zone (labelled in the form); the API
  uses UTC. Departure is limited to the next 7 days so the whole trip stays inside the
  forecast horizon. A checkpoint without forecast data is shown as *Unknown* and left out
  of the average risk.
- **Geocoding** is limited to the US by default (`GEOCODE_COUNTRY_SET`).
- **Provider limits.**
  - TomTom's free tier allows 2,500 requests per day; a plan uses 1–3 and each autocomplete
    query 1.
  - Open-Meteo's free tier is for non-commercial use: 10,000 location-calls a day and 600 a
    minute. A plan uses roughly 50–200 location-calls and a heatmap up to 250, before
    caching. Set `OPEN_METEO_API_KEY` to use the commercial endpoint.
- The cache is per process (Django local-memory cache). It is only an optimisation, so
  correctness doesn't depend on it.
