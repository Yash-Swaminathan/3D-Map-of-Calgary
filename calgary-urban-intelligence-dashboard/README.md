# Calgary Urban Intelligence Dashboard

Explore Calgary in an interactive 3D map. Ask a plain-English question about height, building use, assessment value, or zoning; select a building to inspect its data; and save filters as a project.

## What works

- React 18 and Three.js render vertically extruded footprints with meter coordinates and a stable coordinate origin. Filtering preserves positions.
- Flask serves routes under /api on port 5001.
- Five Calgary datasets are paginated completely within map-driven geographic tiles and joined with Shapely spatial indexes. OpenStreetMap enrichment is optional. Missing sources produce visible coverage notes.
- Building use comes from Calgary roof-outline classifications, enriched with OpenStreetMap tags when available. Heights use Calgary rooftop/ground elevations or OSM height tags.
- Supported natural-language filters use deterministic rules with feet-to-meter and CAD suffix conversions. Local Flan-T5 is optional.
- SQLite stores buildings, provenance, versioned area caches with shared building membership, usernames, and saved filter sets. Projects reapply the same filters within the current study area.
- The responsive UI includes coverage counts, loading/error/empty states, readable filters, building details, and project save/load/delete.

Missing addresses, assessment values, and zoning remain unknown. Unknown-height meshes use a disclosed display placeholder that is not saved as a measurement. Assessment values belong to a matched property record and are not whole-building totals. Buildings can overlap multiple property records.

## Run locally

Use Python 3.10+ and Node.js with npm. From this directory:

~~~powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
~~~

In another terminal:

~~~powershell
cd frontend
npm ci
npm start
~~~

Open http://localhost:3000. The development server proxies /api to http://localhost:5001. If port 3000 is occupied:

~~~powershell
$env:PORT = '3006'
npm start
~~~

For a separately hosted frontend, set REACT_APP_API_URL to the backend origin or its /api URL before building. Configure backend CORS_ORIGINS for that frontend origin.

The default database is backend/instance/urban_dashboard.db. Existing building/project tables remain usable; new provenance/cache tables are created on startup. Areas are cached until refresh is requested. Refresh fetches first, then replaces that area's membership without deleting buildings belonging to neighbouring tiles. Legacy capped caches are bypassed automatically. A failed upstream fetch preserves the cache. DATABASE_URL can select another SQLAlchemy database.

## Navigate the city

Right-drag to pan, scroll to zoom, double-click the ground to explore that location, or enter latitude, longitude in the map's Go control. Reset view returns downtown; City overview zooms out across Calgary. The study-area coordinates update from camera/ground intersections, including after resizing. Active filters stay applied as new buildings arrive. Requests for an old view are cancelled and cannot replace a newer view. Loaded tiles are reused in memory and SQLite.

No new API key, database reset, or manual bounds edit is needed. Restart the backend and frontend after pulling. New cache tables are created automatically. The first visit to an uncached area can take one to several minutes because assessment records require many upstream pages. Failures remain visible alongside partial results; Retry loading area retries unfinished tiles. Refresh data explicitly refreshes the visible tiles.

OpenStreetMap is disabled for automatic map loading by default to avoid repeated Overpass delays. To enable additional OSM tags/footprints, set ENABLE_OSM_ENRICHMENT=true in backend/.env and restart, then refresh the view. City building outlines still load without OSM.

## Optional local model

Common questions work without Torch, Transformers, or a model download:

- commercial buildings over 100 feet
- buildings under 50 meters
- properties over $2 million
- buildings worth less than $500,000
- CC-X buildings

To enable local Flan-T5 for other wording, install backend/requirements-llm.txt, set ENABLE_LOCAL_LLM=true in backend/.env, and restart. Model loading is lazy and cached. Invalid output produces a clear unsupported-question message. No hosted Hugging Face or Ollama endpoint is configured. The optional model path remains experimental.

## Verification

Backend tests use an isolated in-memory database and mocked upstream sources:

~~~powershell
cd backend
python -m unittest discover -s tests -v
~~~

Frontend geometry/filter tests and production build:

~~~powershell
cd frontend
$env:CI = 'true'
npm test -- --watchAll=false --runInBand
npm run build
~~~

Optional browser check with the app running:

~~~powershell
pip install -r scripts/requirements-browser.txt
python scripts/browser_smoke_check.py --url http://localhost:3006
python scripts/viewport_smoke_check.py
~~~

The browser check uses installed Chrome or Edge, exercises query/project/map/mobile workflows, and captures actual UI screenshots. Its temporary project is deleted after verification.

## Scope and remaining limits

This is a local prototype. The camera starts downtown, then pan/zoom loads the visible area anywhere in Calgary. All five sources paginate until exhausted; the area API sends 500-row pages with total_count, next_offset, and a snapshot version. The browser consumes every page and deduplicates shared footprints across tiles. Broad views covering more than 16 tiles show a live roof-record count; zoom in anywhere to render individual buildings. This avoids rendering hundreds of thousands of meshes at once. Coverage can change when public APIs fail. Caches only refresh on request. Spatial matches do not establish legal parcel/building relationships; complex multipart buildings and multiple assessment records need deeper modeling. Username identification has no passwords or access control. The optional model path has not been validated end to end.

## Layout and documentation

The application is split into frontend and backend folders. Frontend components cover the map, query panel, building details, saved projects, and identity form. Backend services cover data fetching, building persistence/filtering, and question interpretation.

- [Calgary API setup](docs/calgary-api-setup.md)
- [System architecture](docs/architecture/system-overview.md)
- [UI screenshots](docs/screenshots/README.md)
- docs/archive/original-internship-assignment-2025.pdf preserves the original assignment.

Data attribution: City of Calgary Open Data and OpenStreetMap contributors.
