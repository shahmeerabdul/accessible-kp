## Accessible KPK – Healthcare Facility Finder

A small full-stack web app to explore healthcare facilities (hospitals, clinics, BHUs, RHCs) in **Khyber Pakhtunkhwa (KPK), Pakistan**.  
Data comes live from **OpenStreetMap** — via either the **healthsites.io** API or the **Overpass API** — through a Django REST API, and is visualised in a **React + Leaflet** frontend.

### Tech stack

- **Backend**: Django 5, Django REST Framework, `requests`, `django-cors-headers`
- **Frontend**: React (Vite), Tailwind CSS, Leaflet (`react-leaflet`)
- **External data**: [healthsites.io](https://healthsites.io/) v3 API or the OpenStreetMap Overpass
  API — both OSM-derived and selectable via `FACILITIES_PROVIDER`

---

### Repository layout

- `backend/` – Django + DRF project
  - `backend/settings.py` – core Django/DRF, CORS, and cache configuration
  - `facilities/` – app that talks to the upstream provider and normalises facility data
  - `Dockerfile`, `gunicorn.conf.py`, `requirements-prod.txt` – production server and image
- `frontend/` – React + Vite + Tailwind single-page app
  - `src/components/` – `CitySelect`, `Filters`, `FacilityList`, `MapView`, `Pagination`
  - `src/lib/` – shared helpers: facility-type colours, contact/URL normalisation
  - `Dockerfile`, `nginx.conf` – static-site image
- `docker-compose.yml` – local stack: API + frontend + Redis
- `deploy/` – AWS deployment guide (S3 + CloudFront, EC2), nginx and systemd examples
- `.github/workflows/ci.yml` – CI: backend tests, frontend lint + build, Docker image builds

---

### Backend setup (Django + DRF)

1. **Create and activate a virtualenv (recommended)**

   ```bash
   cd backend
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # or cmd
   .venv\Scripts\activate.bat
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   Copy the example env file and adjust if needed:

   ```bash
   copy .env.example .env  # on Windows
   ```

   Key variables:

   - `DJANGO_SECRET_KEY` – any random string for local dev; must be a unique secret when `DJANGO_DEBUG` is not `true`
   - `DJANGO_DEBUG` – off by default; set to `true` for local development only
   - `DJANGO_ALLOWED_HOSTS` – usually `*` for local dev; real host name(s) (no `*`) otherwise
   - `CORS_ALLOWED_ORIGINS` – frontend origin, e.g. `http://localhost:5173` (required when `DJANGO_DEBUG` is not `true`)
   - `API_THROTTLE_RATE` – per-client rate limit (default `60/min`); over the limit the API returns `429`
   - `API_NUM_PROXIES` – number of reverse proxies in front of Django (so the limit sees the real client IP)
   - `FACILITIES_PROVIDER` – data source: `healthsites` (default) or `overpass`
   - `HEALTHSITES_API_KEY` – required when using the `healthsites` provider. Get one free at
     [healthsites.io](https://healthsites.io/): sign in with an OpenStreetMap account, then generate
     a key from your profile page. Keep it in `.env` (gitignored) — never commit it.
   - `OVERPASS_API_URL` – Overpass endpoint (used when `FACILITIES_PROVIDER=overpass`)
   - `OVERPASS_USER_AGENT` – identifies this app to Overpass; public instances 406-reject requests with a generic client User-Agent
   - `CITY_SEARCH_RADIUS_METERS` – radius (meters) searched around each city's center point (default `12000`)
   - `FACILITIES_CACHE_TTL` – cache duration (seconds) for city results

4. **Run migrations**

   ```bash
   python manage.py migrate
   ```

5. **Run the Django dev server**

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

6. **API endpoint**

   - `GET /api/facilities?city=<city_name>&limit=<int>`
     optionally with `&ownership=government|private`, `&emergency=true`, `&open_24_7=true`

   Example:

   ```bash
   curl "http://localhost:8000/api/facilities?city=Peshawar&limit=100&emergency=true"
   ```

   The backend:

   - Validates `city` against the supported KPK list (unknown cities get a `400`)
   - Fetches up to 500 facilities for the city (`FETCH_CAP`), de-duplicated, and caches that
     once per `(provider, city)` using Django's `LocMemCache`
   - Applies the filters to **all** fetched facilities, *then* clamps to `limit`
     (`1…500`, default `500`) — so a filter never misses matches beyond the first `limit`
   - Rejects bad `ownership` / `emergency` / `open_24_7` values with a `400`
   - Normalises results into a consistent facility shape regardless of provider
   - Returns JSON via DRF serializer, plus two response headers:
     - `X-Total-Count` – facilities matching the filters (can be larger than the array returned)
     - `X-Upstream-Capped` – `true` if the city hit the 500 cap, so more may exist in OSM

   Response shape:

   ```json
   [
     {
       "osm_id": "way/854341089",
       "name": "CMH Peshawar - Combined Military Hospital",
       "facility_type": "Hospital",
       "address": "",
       "phone": "",
       "website": "",
       "email": "",
       "is_24_7": null,
       "is_emergency": true,
       "ownership": "",
       "lat": 34.0034083,
       "lon": 71.5427023
     }
   ]
   ```

   `is_24_7` / `is_emergency` are `true`, `false`, or `null` when OSM records nothing.
   Empty strings mean the tag is absent upstream.

---

### Frontend setup (React + Vite + Tailwind + Leaflet)

1. **Install dependencies**

   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**

   ```bash
   copy .env.example .env
   ```

   - `VITE_API_BASE_URL` – base URL of the Django backend, e.g. `http://localhost:8000`

3. **Run the dev server**

   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173` by default.

---

### Frontend architecture

The UI is a three-pane layout: a filter rail, a results panel, and the map.
A **Split / List / Map** toggle in the header controls which panes are shown —
List mode hides the map and lays results out as a multi-column grid.

- **`CitySelect`** – dropdown for KPK cities (Peshawar, Mardan, Abbottabad, Mingora, Kohat, Bannu, D.I. Khan, etc.)
- **`Filters`** – segmented ownership control (All / Govt / Private), Emergency and
  Open 24/7 toggle pills, and the fetch limit
- **`FacilityList`** – cards showing:
  - name, facility type, address
  - facility-type, ownership, emergency and 24/7 badges
  - a contact row: tap-to-call phone, website and email when present, plus a
    **Directions** link (available for every facility, since it only needs coordinates)
- **`MapView`** – Leaflet map with markers colour-coded by facility type and a matching
  legend. Auto-fits bounds to the current results, flies to the selected facility, and
  calls `invalidateSize()` on container resize so the view toggle doesn't leave grey tiles.
- **`Pagination`** – page numbers plus prev/next, showing the current range

The root `App` component:

- Manages selected city, filters, result limit, view mode, pagination and selection
- Calls `GET /api/facilities` via Axios with `city`, `limit` and the active filters
  (filtering happens on the server, before the limit)
- Handles **loading** (skeletons), **error**, and **empty** states
- Shows a notice when results are cut off (more matches than the limit, or the city hit
  the 500-facility fetch cap)
- Paginates the loaded results at **20 per page**, resetting to page 1 whenever the city
  or filters change
- Shows "Unnamed <type>" for facilities with no name
- Feeds only the current page to both the list and the map, keeping the two in sync and
  avoiding overlapping-pin clutter on dense cities

**List ↔ map selection** is shared: clicking a card or a marker highlights the card and
flies the map to that facility with an enlarged marker.

---

### Backend architecture (Django + facility providers)

- **`facilities/services.py`**
  - Supports two interchangeable providers, selected by `FACILITIES_PROVIDER`:
    - **healthsites** (default) – queries [healthsites.io](https://healthsites.io/)'s v3 API with a
      bounding box derived from the city center; needs `HEALTHSITES_API_KEY`
    - **overpass** – queries the Overpass API directly
  - Both search within `CITY_SEARCH_RADIUS_METERS` of each supported city's known center
    coordinates (`CITY_COORDINATES`) rather than doing an OSM administrative boundary lookup,
    since those boundaries are tagged with local-script (Urdu/Pashto) names in OSM and don't
    reliably match an English city name
  - Both normalise through the same `infer_*` helpers, so the API response shape is identical
    regardless of provider
  - Normalises each element into a facility object:
    - `osm_id` (type-qualified and unique, e.g. `node/123`, `way/123`), `name`,
      `facility_type` (`Hospital`, `Clinic`, `BHU`, `RHC`, etc.; BHU/RHC match whole words only)
    - `address`, `phone`, `website`, `email`
    - `is_24_7`, `is_emergency`
    - `ownership` (government vs private): explicit operator/ownership tags first, then
      unmistakable government markers in the name (DHQ, THQ, BHU, RHC, Civil Hospital, …);
      otherwise left empty rather than guessed
    - `lat`, `lon`
  - Wraps low-level/network errors into a custom `FacilityProviderError`
  - De-duplicates facilities by `osm_id` and provides `filter_facilities`
  - Uses Django cache (`LocMemCache`) keyed by `(provider, city)` so switching
    providers doesn't serve stale results from the other one

- **`facilities/views.py`**
  - DRF `APIView` (`FacilityListView`) bound to `GET /api/facilities`
  - Validates query parameters (`city` against the supported list, optional `limit`
    clamped to `MAX_LIMIT`, optional `ownership` / `emergency` / `open_24_7` filters)
  - Delegates to the service layer, filters, applies the limit and serialises results via
    `FacilitySerializer`; sets the `X-Total-Count` / `X-Upstream-Capped` headers
  - Returns clean error responses (400 for bad input, 502 for upstream provider failures)

---

### CORS configuration

For local development (React at `localhost:5173`, Django at `localhost:8000`):

- With `DJANGO_DEBUG=true`, all origins are allowed unless you set `CORS_ALLOWED_ORIGINS`.
- To restrict it locally, set in `backend/.env`:

  ```env
  CORS_ALLOWED_ORIGINS=http://localhost:5173
  ```

Outside `DJANGO_DEBUG=true`, `CORS_ALLOWED_ORIGINS` is required and the app refuses to start without it.

---

### Development, testing and CI

```bash
# Backend (from backend/, with the virtualenv active)
python manage.py test            # unit and API tests
python manage.py check --deploy  # audit the production configuration (set the production env vars first)

# Frontend (from frontend/)
npm run lint                     # ESLint (React + hooks rules)
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs the backend tests, the frontend lint and
build, and builds both Docker images on every push to `main` and every pull request.

**Health check:** `GET /api/health` returns `{"status": "ok"}`. It never calls an upstream
provider and is not rate-limited, so it is safe for load balancers and uptime monitors.

**Logging:** logs go to the console (`LOG_LEVEL`, default `INFO`). Upstream failures are logged
by type only, never with request URLs, so the API key cannot end up in the logs.

**Shared cache:** by default results are cached in each process's memory. Set `REDIS_URL`
(e.g. an ElastiCache endpoint) to share one cache across gunicorn workers and servers. If the
cache is unreachable the API keeps working (slower, with a logged warning).

### Docker

```bash
cp backend/.env.example backend/.env    # put your HEALTHSITES_API_KEY in it
docker compose up --build
```

Frontend at http://localhost:8080, API health at http://localhost:8000/api/health. The compose
file also starts Redis and points the API at it. Secrets are never baked into the images
(`.env` is excluded by `.dockerignore`); they are passed at runtime. The frontend image bakes in
`VITE_API_BASE_URL` at build time (see the build arg in `docker-compose.yml`).

### Deploying to AWS

See [deploy/README.md](deploy/README.md) for the S3 + CloudFront (frontend) and EC2 (API)
setup, including nginx and systemd examples, the production settings, and TLS.

---

### Features implemented

- KPK‑only city dropdown, validated server-side as well as in the UI
- Facilities fetched dynamically from OSM data, **not hard-coded**
- Two interchangeable upstream providers (healthsites.io / Overpass)
- REST endpoint: `GET /api/facilities?city=<city_name>&limit=<int>`
- Basic in‑memory caching via Django cache framework (`LocMemCache`)
- React SPA with:
  - responsive layout (mobile + desktop) with Split / List / Map view modes
  - cards list + interactive Leaflet map, linked by a shared selection
  - client-side pagination at 20 per page
  - server-side filters for ownership, emergency, 24/7, plus a notice when results are cut off
  - contact details (phone / website / email) plus Directions for every facility
  - colour-coded map markers with a legend, auto-fitted to results
  - loading skeletons, empty, and error states
- Env‑driven configuration for both backend and frontend

---

### Limitations / notes

- **OSM data completeness**: Only facilities mapped in OpenStreetMap will appear. Many BHUs/RHCs and private clinics may be missing or outdated.
- **Contact data is sparse**: this is the biggest practical limitation. In a sample of 88
  Peshawar facilities, only **8 had a phone number** (~9%), 3 had a website and 2 an email.
  "No phone listed" is therefore the common case, not a bug. The Directions link is provided
  precisely because coordinates are the one field that is always present.
- **City search is radius-based**: results come from a `CITY_SEARCH_RADIUS_METERS` radius
  around hard-coded city centre coordinates, not true administrative boundaries. OSM tags
  KPK boundaries with local-script (Urdu/Pashto) names, so matching them by English name
  does not work. A facility just outside the radius will be missed.
- **healthsites API keys need manual approval**: keys are issued inactive and only start
  working once a healthsites admin approves the enrolment (they email you). Until then the
  API returns `403` and you should stay on `FACILITIES_PROVIDER=overpass`.
- **Public Overpass instances are unreliable**: they frequently return `504`s under load.
  The default is OSM France's mirror, which benchmarked far better than `overpass-api.de`.
  A descriptive `OVERPASS_USER_AGENT` is mandatory — generic agents get `406`-rejected.
- **No authentication**: This is a public, read-only discovery tool.
- **No write operations**: The app does not modify OpenStreetMap or store data permanently.
- **Not a replacement for Google Maps**: Routing, turn‑by‑turn navigation, and rich POI data are out of scope for this MVP.

