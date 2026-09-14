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
- `frontend/` – React + Vite + Tailwind single-page app
  - `src/components/` – `CitySelect`, `Filters`, `FacilityList`, `MapView`, `Pagination`
  - `src/lib/` – shared helpers: facility-type colours, contact/URL normalisation

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

   - `DJANGO_SECRET_KEY` – any random string for local dev
   - `DJANGO_DEBUG` – set to `true` for local development
   - `DJANGO_ALLOWED_HOSTS` – usually `*` for local dev
   - `CORS_ALLOWED_ORIGINS` – frontend origin, e.g. `http://localhost:5173`
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

   Example:

   ```bash
   curl "http://localhost:8000/api/facilities?city=Peshawar&limit=100"
   ```

   The backend:

   - Validates `city` against the supported KPK list (unknown cities get a `400`)
   - Clamps `limit` to `1…500`, defaulting to `500` when omitted
   - Queries the configured provider around the city's centre coordinates
   - Normalises results into a consistent facility shape regardless of provider
   - Applies **in‑memory caching** by `(provider, city, limit)` using Django's `LocMemCache`
   - Returns JSON via DRF serializer

   Response shape:

   ```json
   [
     {
       "osm_id": "854341089",
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

- **`CitySelect`** – dropdown for KPK cities (Peshawar, Mardan, Abbottabad, Mingora/Swat, Kohat, Bannu, D.I. Khan, etc.)
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
- Calls `GET /api/facilities` via Axios with `city` and `limit`
- Handles **loading** (skeletons), **error**, and **empty** states
- Applies filters client-side, then paginates at **20 per page**, resetting to page 1
  whenever the city or filters change
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
    - `osm_id`, `name`, `facility_type` (`Hospital`, `Clinic`, `BHU`, `RHC`, etc.)
    - `address`, `phone`, `website`, `email`
    - `is_24_7`, `is_emergency`
    - `ownership` (government vs private, best‑effort from tags)
    - `lat`, `lon`
  - Wraps low-level/network errors into a custom `FacilityProviderError`
  - Uses Django cache (`LocMemCache`) keyed by `(provider, city, limit)` so switching
    providers doesn't serve stale results from the other one

- **`facilities/views.py`**
  - DRF `APIView` (`FacilityListView`) bound to `GET /api/facilities`
  - Validates query parameters (`city` against the supported list, optional `limit`
    clamped to `MAX_LIMIT`)
  - Delegates to the service layer and serialises results via `FacilitySerializer`
  - Returns clean error responses (400 for bad input, 502 for upstream provider failures)

---

### CORS configuration

For local development (React at `localhost:5173`, Django at `localhost:8000`):

- In `backend/.env`, either:
  - keep `CORS_ALLOW_ALL_ORIGINS=true` (easy for local), or
  - set:

    ```env
    CORS_ALLOW_ALL_ORIGINS=false
    CORS_ALLOWED_ORIGINS=http://localhost:5173
    ```

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
  - filters for ownership, emergency, 24/7
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

