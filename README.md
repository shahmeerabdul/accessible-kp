## Accessible KPK – Healthcare Facility Finder

A small full-stack web app to explore healthcare facilities (hospitals, clinics, BHUs, RHCs) in **Khyber Pakhtunkhwa (KPK), Pakistan**.  
Data is fetched live from **OpenStreetMap** using the **Overpass API**, via a Django REST API, and visualised in a **React + Leaflet** frontend.

### Tech stack

- **Backend**: Django 5, Django REST Framework, `requests`, `django-cors-headers`
- **Frontend**: React (Vite), Tailwind CSS, Leaflet (`react-leaflet`)
- **External API**: OpenStreetMap Overpass API (configurable via env variable)

---

### Repository layout

- `backend/` – Django + DRF project
  - `backend/settings.py` – core Django/DRF, CORS, and cache configuration
  - `facilities/` – app that talks to Overpass and normalises facility data
- `frontend/` – React + Vite + Tailwind single-page app

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
   - `OVERPASS_API_URL` – Overpass endpoint (`https://overpass-api.de/api/interpreter` by default)
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

   - Builds an Overpass query scoped to the specified city
   - Calls Overpass API via `requests`
   - Normalises results into a consistent facility shape (name, type, address, phone, emergency/24‑7 flags, ownership, coordinates)
   - Applies **in‑memory caching** by `(city, limit)` using Django’s `LocMemCache`
   - Returns JSON via DRF serializer

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

- **`CitySelect`** – dropdown for KPK cities (Peshawar, Mardan, Abbottabad, Mingora/Swat, Kohat, Bannu, D.I. Khan, etc.)
- **`Filters`** – simple controls for:
  - government vs private (inferred from OSM tags if possible)
  - emergency-only
  - 24/7-only
- **`FacilityList`** – list view showing:
  - name, facility type, address
  - phone (when available)
  - emergency / 24‑hour badges (where inferred)
  - government/private badges (where inferred)
- **`MapView`** – Leaflet map with markers for each facility:
  - OpenStreetMap tiles
  - popups summarising key facility info

The root `App` component:

- Manages selected city, filters, and result limit
- Calls `GET /api/facilities` via Axios with `city` and `limit`
- Handles **loading**, **error**, and **empty** states
- Applies filters client‑side before passing to list + map

---

### Backend architecture (Django + Overpass)

- **`facilities/services.py`**
  - Constructs Overpass QL queries for a given city
  - Calls the Overpass API (endpoint configurable via `OVERPASS_API_URL`)
  - Normalises each OSM element into a facility object:
    - `osm_id`, `name`, `facility_type` (`Hospital`, `Clinic`, `BHU`, `RHC`, etc.)
    - `address`, `phone`
    - `is_24_7`, `is_emergency`
    - `ownership` (government vs private, best‑effort from tags)
    - `lat`, `lon`
  - Wraps low-level/network errors into a custom `OverpassError`
  - Uses Django cache (`LocMemCache`) keyed by `(city, limit)` to avoid hitting Overpass too often

- **`facilities/views.py`**
  - DRF `APIView` (`FacilityListView`) bound to `GET /api/facilities`
  - Validates query parameters (`city`, optional `limit`)
  - Delegates to the service layer and serialises results via `FacilitySerializer`
  - Returns clean error responses (400 for bad input, 502 for Overpass failures)

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

- KPK‑only city dropdown (hard‑coded list of common cities/towns in KPK)
- Facilities fetched dynamically from Overpass, **not hard-coded**
- REST endpoint: `GET /api/facilities?city=<city_name>&limit=<int>`
- Basic in‑memory caching via Django cache framework (`LocMemCache`)
- React SPA with:
  - responsive layout (mobile + desktop)
  - cards list + interactive Leaflet map
  - filters for ownership, emergency, 24/7
  - loading, empty, and error states
- Env‑driven configuration for both backend and frontend

---

### Limitations / notes

- **OSM data completeness**: Only facilities mapped in OpenStreetMap will appear. Many BHUs/RHCs and private clinics may be missing or outdated.
- **No authentication**: This is a public, read-only discovery tool.
- **No write operations**: The app does not modify OpenStreetMap or store data permanently.
- **Overpass rate limiting**: Heavy use may hit Overpass API limits. The built‑in cache helps, but for production you would likely need your own Overpass instance or a more robust caching layer.
- **Not a replacement for Google Maps**: Routing, turn‑by‑turn navigation, and rich POI data are out of scope for this MVP.

