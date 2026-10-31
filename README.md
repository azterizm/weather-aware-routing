# Weather-Aware Truck Routing

Weather-Aware Truck Routing recommends the safest of 3 truck routes for a trip, based on weather, load weight and travel time. A React single-page app sends the trip to a Django REST API. The API plans the routes with TomTom, reads the Open-Meteo forecast at each checkpoint for the hour the truck reaches it, scores the risk and returns a ranked result.

The hosted app runs at https://weather-aware-routing-e8f465157fa2.herokuapp.com on Heroku in the United States.

The driver enters an origin, a destination, a departure date and time, and a load weight. The app then completes six steps.

1. TomTom returns 3 truck route options.
2. Checkpoints are placed every 10, 25 or 50 miles along each route, and each checkpoint gets the truck's estimated arrival time.
3. The hourly forecast is read at each checkpoint for that arrival time.
4. Each checkpoint is classified with the risk and load rules below.
5. The routes are ranked by fewest Severe miles, then fewest High miles, then lowest average risk, then shortest travel time.
6. The map shows the routes, checkpoints, risk levels, arrival times and route summaries, with a weather risk heatmap along the trip corridor and a slider that covers 0 to 48 hours after departure.

## Contents

- [Architecture](#architecture)
- [Risk model](#risk-model)
- [API](#api)
- [Running locally](#running-locally)
- [Configuration](#configuration)
- [Performance and stability](#performance-and-stability)
- [Deployment](#deployment)
- [Decisions and limits](#decisions-and-limits)

## Architecture

The repository holds both halves of the app. In production, Django serves the REST API and the built single-page app from one process, so one Docker image is the whole deployment.

```
backend/                 Django 5.2 LTS and Django REST Framework on Python 3.13, managed with uv
  config/                settings read from environment variables, URLs, WSGI entry point
  trips/
    domain/              risk rules, geometry, checkpoints, arrival times and ranking, with no I/O
    providers/           TomTom geocoding and truck routing, Open-Meteo forecasts
    services/            route options, trip planning and the corridor heatmap
    api/                 request validation, JSON output, views and the error handler
    tests/               pytest suite, with trimmed real provider responses as fixtures
frontend/                Vite, React 19, TypeScript, Material UI and react-leaflet
  src/api/               axios client and typed calls for each endpoint
  src/hooks/             TanStack Query hooks for the plan, the heatmap and place search
  src/components/        trip form, route summaries and the map with its layers and slider
Dockerfile               builds the single-page app, then the Python runtime with gunicorn and WhiteNoise
heroku.yml               Heroku container build
```

The browser makes four kinds of request.

1. `GET /api/geocode/?q=` returns place suggestions from TomTom Search while the driver types.
2. `POST /api/trips/plan/` requests truck routes from TomTom, places the checkpoints, fetches the forecast for every checkpoint in one batched Open-Meteo request, scores the risk and returns the ranked routes.
3. `POST /api/trips/corridor-weather/` builds a grid around the returned routes and returns the risk for every cell for each hour from departure to 48 hours later.
4. `GET /api/tiles/{z}/{x}/{y}.png` returns TomTom map tiles through the API, so the TomTom key never reaches the browser. When a tile request fails, the map loads that tile from OpenStreetMap instead.

The heatmap request starts after the plan returns, so routes and checkpoints appear first. On the Dallas to Denver test trip the plan took 8.2 seconds and the heatmap followed 0.9 seconds later. The API stores nothing and has no database.

## Risk model

### Weather thresholds

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind in mph | below 25 | 25 to under 35 | 35 to under 45 | 45 to under 55 | 55 or more |
| Rain in inches per hour | below 0.10 | 0.10 to under 0.25 | 0.25 to under 0.50 | 0.50 to 1.00 | above 1.00 |
| Snow in inches per hour | below 0.5 | 0.5 to under 1.0 | 1.0 to under 2.0 | 2.0 to 3.0 | above 3.0 |

The brief gives ranges that share endpoints, such as rain from 0.10 to 0.25 and from 0.25 to 0.50. Each range includes its lower endpoint and excludes its upper one, so a shared endpoint belongs to the higher level. A wind of 35 mph is High, and rain of 0.25 inches per hour is High. The No Travel thresholds for rain and snow are strict, so exactly 1.00 inch of rain or 3.0 inches of snow per hour is Severe. A wind of 34.6 mph falls in the 25 to 34 band and is Moderate.

### Load rules

- A wind of 55 mph or more is No Travel for any load.
- A wind from 45 to 54 mph with a load over 30,000 lb is No Travel.
- A wind from 35 to 44 mph with a load over 40,000 lb is Severe.

A checkpoint's risk is the worst of the load-adjusted wind level, the rain level and the snow level. The tooltip for each checkpoint names the factor and the load rule that set the level.

### Weather inputs

- Wind is Open-Meteo `wind_speed_10m`, the sustained wind at 10 metres in mph. It is a value at the hour mark, so the app interpolates between the two hours around the arrival time.
- Rain is `rain` plus `showers`, which together cover all liquid precipitation. Snow is `snowfall`. Open-Meteo reports both as totals for the previous hour, so the app reads the value stamped at the end of the hour the truck is driving through. That one-hour total is the rate in inches per hour.
- The app requests mph and inches and checks the units in every response. Any other unit is converted, and an unknown unit stops the request with an error.
- Displayed values are rounded down, so a shown value never crosses a threshold. A wind of 34.96 mph is Moderate and appears as 34.9.

### Checkpoints and arrival times

- The checkpoint spacing depends on trip length and is the same for all 3 routes, so their miles compare fairly. The shortest route sets it. A trip under 250 miles uses 10 miles, a trip from 250 to 1,000 miles uses 25 miles, and a longer trip uses 50 miles.
- Checkpoints sit at mile 0, at every multiple of the spacing and at the destination. A regular checkpoint within 10 percent of one spacing of the destination merges into the destination checkpoint.
- The arrival time at a checkpoint is the departure time plus TomTom's travel time to that point on the route. TomTom returns travel times with traffic for points along the route, and the app interpolates by distance between them.
- Each checkpoint covers half the distance to each neighbouring checkpoint, so the covered miles add up to the route length. Severe miles, High miles and the other totals are sums of covered miles.
- Average risk weights each checkpoint's score by its covered miles. Low scores 0, Moderate 1, High 2, Severe 3 and No Travel 4.

### Recommendation

Routes are compared on five criteria in this order.

1. Fewest No Travel miles.
2. Fewest Severe miles.
3. Fewest High miles.
4. Lowest average risk.
5. Shortest travel time.

The brief lists Severe first and does not rank No Travel. No Travel is worse than Severe, so it is compared first, and a route with any No Travel miles ranks below an otherwise equal route without them. Miles are compared to the nearest 0.1 mile and average risk to the nearest 0.01, so rounding noise cannot decide a ranking. The recommendation panel names the first criterion on which the winner beat the runner-up and shows both values.

### Three route options

TomTom is asked for its best route and 2 alternatives. In 3 test requests for Dallas to Denver departing 20 hours later, TomTom returned 2 routes each time. The same trip departing immediately returned 3.

When fewer than 3 routes come back, the app requests 2 detour routes in parallel. Each detour passes through a point beside the midpoint of the trip, offset by 12 percent of the straight-line distance, one on each side. A detour is kept only if it is no longer than 1.5 times the length of the first route and shares less than 80 percent of its path with every route already chosen. If 3 distinct routes still cannot be found, the panel states the number of routes found.

### Corridor heatmap

The corridor covers every grid cell within 25 miles of any route. The grid starts at 0.1 degrees and grows coarser until it holds 250 cells or fewer, because each cell is one forecast location. The Dallas to Denver corridor used 242 cells, each about 0.31 degrees across. Each cell is scored for every hour from departure to 48 hours later with the same weather and load rules as the checkpoints, so the heatmap shows risk for the load entered.

## API

All endpoints sit under `/api/`, accept and return JSON, and use UTC timestamps in ISO 8601 format. Input timestamps must carry a UTC offset. Every error has the same shape.

```json
{ "detail": "Human-readable message", "code": "invalid", "fields": { "load_weight_lbs": ["…"] } }
```

| Status | Code | Meaning |
|---|---|---|
| 400 | `invalid` | The request failed validation, and `fields` lists the message for each field. |
| 422 | `no_route` | TomTom found no truck route between the two places. |
| 429 | `throttled` | The IP address reached its request limit. |
| 503 | `upstream_unavailable` or `quota_exceeded` | TomTom or Open-Meteo failed or reached its quota. |

### `GET /api/health/`

The endpoint returns `{"status": "ok"}`.

### `GET /api/geocode/?q=denver`

The endpoint returns place suggestions for the form. The query needs at least 3 characters.

```json
{ "results": [{ "label": "Denver, CO", "lat": 39.738453, "lon": -104.984853 }] }
```

### `POST /api/trips/plan/`

The request body has this shape.

```json
{
  "origin": { "label": "Dallas, TX", "lat": 32.7767, "lon": -96.797 },
  "destination": { "label": "Denver, CO", "lat": 39.7392, "lon": -104.9903 },
  "departure_time": "2026-11-01T08:00:00-05:00",
  "load_weight_lbs": 42000
}
```

The departure must fall between 15 minutes ago and 7 days ahead. The load must be from 1 to 80,000 lb. The origin and destination must be at least half a mile apart.

The response has this shape, shortened to one route and one checkpoint.

```json
{
  "departure_time": "2026-11-01T13:00:00Z",
  "load_weight_lbs": 42000.0,
  "checkpoint_interval_miles": 25,
  "recommended_route_id": "route-2",
  "recommendation_reason": "Route B has the fewest Severe miles, 0 mi against 50 mi on Route A.",
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

### `POST /api/trips/corridor-weather/`

The request carries the plan's route geometries as 1 to 3 encoded polylines, the plan's departure time as `start_time`, and the load.

```json
{ "routes": ["<encoded>", "…"], "start_time": "2026-11-01T13:00:00Z", "load_weight_lbs": 42000 }
```

The response holds 49 hourly timestamps and one matrix per measure, indexed by hour and then by cell. Risk scores run from 0 for Low to 4 for No Travel, and -1 marks a cell without forecast data.

```json
{
  "hours": ["2026-11-01T13:00:00Z", "… 49 in total"],
  "cell_size_deg": 0.31241,
  "cells": [[33.12, -97.18], "…"],
  "risk": [[0, 1, 3, "…"], "…"],
  "wind_mph": [[12.3, "…"]], "rain_in_hr": [[0.0, "…"]], "snow_in_hr": [[0.0, "…"]]
}
```

### `GET /api/tiles/{z}/{x}/{y}.png`

The endpoint returns a 256 pixel TomTom map tile as PNG for zoom levels 0 to 18, cached by the browser for 1 day. A tile outside the map returns 404. A TomTom failure returns 502 or 503, and the map then loads that tile from `tile.openstreetmap.org`. The page sends its origin as the Referer, which OpenStreetMap's tile usage policy requires.

## Running locally

The backend needs [uv](https://docs.astral.sh/uv/), which installs Python 3.13 itself. The frontend needs Node 22 or newer, and `frontend/.nvmrc` pins Node 24. Routing and geocoding need a free API key from [TomTom](https://developer.tomtom.com/). Open-Meteo needs no key.

```bash
cp .env.example .env          # then set TOMTOM_API_KEY
make install                  # installs backend and frontend dependencies
make dev-backend              # Django API on http://127.0.0.1:8000
make dev-frontend             # Vite on http://localhost:5173, forwarding /api to Django
```

Open http://localhost:5173 once both servers are running. Two more commands run the checks.

```bash
make test                     # pytest for the backend, Vitest for the frontend
make lint                     # ruff, ESLint, TypeScript and Prettier
```

## Configuration

Every setting comes from an environment variable. Local development reads them from `.env` at the repository root.

| Variable | Default | Purpose |
|---|---|---|
| `TOMTOM_API_KEY` | Required | TomTom routing and geocoding. |
| `DJANGO_SECRET_KEY` | Required outside debug mode | Django secret key. |
| `DJANGO_DEBUG` | `0` | Set to `1` for local development. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Host names the app answers to, separated by commas. |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` | Redirects HTTP to HTTPS outside debug mode. |
| `OPEN_METEO_API_KEY` | Not set | Switches to the paid Open-Meteo service. |
| `GEOCODE_COUNTRY_SET` | `US` | Countries the place search covers. |
| `CORRIDOR_MAX_CELLS` | `250` | Maximum heatmap cells, each one forecast location. |
| `THROTTLE_PLAN`, `THROTTLE_CORRIDOR`, `THROTTLE_GEOCODE`, `THROTTLE_TILES` | `20/min`, `20/min`, `60/min`, `600/min` | Request limits per IP address. |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker processes, each with 4 threads. |

## Performance and stability

- Every outbound call has its own timeout so a plan finishes inside Heroku's 30-second request limit. Routing gets 14 seconds, each detour gets 6 seconds and each weather batch gets 8 seconds. Detours are skipped when the main routing call has already taken 12 seconds.
- Failed connections and provider responses with status 429 or 5xx are retried with a short backoff. A slow response is not retried, because a retry would push the plan past the time limit.
- Measured on 31 October 2026, plans took 2.3 seconds for Dallas to Austin, 4.7 seconds for Chicago to Atlanta and 8.2 seconds for Dallas to Denver. TomTom's truck routing accounted for 5.8 seconds of the Dallas to Denver time.
- A plan makes 1 routing request, up to 2 detour requests in parallel and 1 batched weather request. Checkpoints are snapped to a 0.05 degree grid, about 3.5 miles, before the weather lookup. On Dallas to Denver this merged 106 checkpoints into 94 forecast locations.
- Each server process caches place searches for 24 hours and forecasts for 30 minutes. The browser reuses the result of an identical plan request for 5 minutes.
- Route lines are simplified to about 30 metres of tolerance and encoded before they are sent, after the checkpoints are computed on the full line. The Dallas to Denver plan response was 35 KB, and its heatmap response was 23 KB after gzip.
- The first page load downloads 229 KB of JavaScript with Brotli compression. The map code loads separately and adds 42 KB. Files with a content hash in their name are cached for a year, and `index.html` is never cached.
- The map draws on canvas, and moving the slider only recolours the heatmap cells.
- API keys never reach the logs. The TomTom key is removed from every logged message, and provider errors are raised again without their URLs.
- Each IP address is limited to 20 plans, 20 heatmaps, 60 place searches and 600 map tiles per minute. The production container runs as a non-root user, with HSTS and strict security headers.

## Deployment

The app ships as one Docker image built from `Dockerfile`. On Heroku, `heroku.yml` selects the container build. The hosted app is the Heroku app `weather-aware-routing` in the US region, running on 1 Basic dyno.

```bash
heroku create <app-name>
heroku stack:set container -a <app-name>
heroku config:set -a <app-name> \
  TOMTOM_API_KEY=… \
  DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  DJANGO_ALLOWED_HOSTS=<app-name>.herokuapp.com
git push heroku main
```

The same image runs on Azure App Service for containers with the same variables and `WEBSITES_PORT=8000`. A local run uses these commands.

```bash
docker build -t weather-aware-routing .
docker run --rm -p 8000:8000 -e TOMTOM_API_KEY=… -e DJANGO_SECRET_KEY=dev \
  -e DJANGO_ALLOWED_HOSTS=localhost -e DJANGO_SECURE_SSL_REDIRECT=0 weather-aware-routing
```

GitHub Actions runs lint, type checks and tests for both halves on every push, then builds the single-page app and the Docker image.

## Decisions and limits

- Load weight feeds only the risk rules. TomTom expects gross vehicle weight, and deriving it would need an assumed tractor and trailer weight.
- Arrival times are TomTom driving times with traffic for the departure time, and they include no rest breaks. Federal hours-of-service rules cap drivers of property-carrying trucks at 11 hours of driving before a 10-hour break. The Dallas to Denver drive takes 11 hours 52 minutes, so on trips that long the last checkpoints are checked earlier than a legal schedule reaches them.
- Times are entered and shown in the browser's time zone, which the form names. The API works in UTC.
- Departure is limited to the next 7 days so the whole trip stays inside Open-Meteo's 16-day forecast. A checkpoint without forecast data is marked Unknown and left out of the average risk.
- The place search covers the United States through `GEOCODE_COUNTRY_SET`.
- The ranking follows the brief strictly. A route with 0.1 fewer Severe miles wins even when it is hours slower.
- TomTom's free tier allows 2,500 routing and search requests a day and 50,000 map tile requests a day. A plan uses 1 to 3 requests, each place search uses 1 after a 350 millisecond pause in typing, and a map view loads 20 to 40 tiles. A tile TomTom cannot serve, for any reason, loads from OpenStreetMap, so the map stays complete when the tile quota runs out.
- Open-Meteo's free tier is for non-commercial use and allows 10,000 location lookups a day and 600 a minute from one IP address. The Dallas to Denver trip used 94 lookups for the plan and 242 for the heatmap. A second uncached trip of that size inside the same minute exceeds the per-minute limit, and in testing on 31 October the third trip planned within one minute was refused. A refused plan returns a rate-limit message. A refused heatmap leaves the routes on screen and shows the message in the slider panel. Setting `OPEN_METEO_API_KEY` switches to the paid service and its higher limits.
- The cache lives inside each server process and only saves time. Results do not depend on it.
