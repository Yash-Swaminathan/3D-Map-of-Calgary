# Calgary Urban Intelligence Dashboard

An in-progress dashboard for exploring Calgary buildings, property assessments, permits, and zoning in an interactive 3D map. The intended workflow is to load a bounded area, ask a plain-English question, inspect matching buildings, and save the filters as a project.

## Current implementation

- React 18 and Three.js render building footprints and heights.
- Flask serves routes under `/api` on port 5001.
- `CalgaryDataFetcher` combines OpenStreetMap data with Calgary open datasets for outlines, 3D buildings, permits, assessments, and land-use districts.
- `BuildingProcessor` stores building records and applies filters.
- `BuildingQueryService` uses local `google/flan-t5-small` through Transformers, with rule-based parsing if model loading or interpretation fails.
- SQLAlchemy models represent buildings, users, and saved project filters. SQLite is the default; `DATABASE_URL` can override it.

This is a prototype, and the full workflow has not been verified. There is currently no Ollama integration or hosted Hugging Face inference API integration.

## Project layout

```text
calgary-urban-intelligence-dashboard/
  backend/
    app/
      models/                       # Buildings, users, and saved projects
      routes/
        api.py                      # Health and user endpoints
        buildings.py                # Building data endpoints
        projects.py                 # Saved project endpoints
        queries.py                  # Natural-language query endpoints
      services/
        calgary_data_fetcher.py      # OpenStreetMap and Calgary integration
        building_processor.py       # Storage and building filters
        building_query_service.py   # Local model and rule-based interpretation
      utils/
    config.py
    requirements.txt
    run.py
  frontend/
    public/
    src/
      components/
        CalgaryMap3D/               # Map and BuildingMesh rendering
        BuildingQueryPanel/         # Plain-English query input
        BuildingDetailsPanel/       # Selected building details
        SavedProjectsPanel/         # Save and load filters
        UserIdentityForm/           # Username-based identification
      services/dashboardApi.js      # Browser API client
      App.js
      index.js
  docs/
    architecture/system-overview.md
    archive/original-internship-assignment-2025.pdf
    calgary-api-setup.md
  api_smoke_check.py                 # Manual check against a running backend
```

The original assignment is retained for historical context. The existing architecture diagrams and API setup notes also need a functional audit.

## Local setup

From this project directory, install and start the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Backend configuration can be placed in `backend/.env`:

```dotenv
FLASK_CONFIG=development
SECRET_KEY=replace-with-a-local-secret
PORT=5001
CALGARY_DEVELOPER_TOKEN=
```

The default database filename remains `urban_dashboard.db` so existing local data is still used. Set `DATABASE_URL` for a different database. The local model downloads its weights on first use; `HUGGINGFACE_API_KEY` is not used by the current query service.

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm ci
npm start
```

The frontend serves on `http://localhost:3000`; the backend serves on `http://localhost:5001`.

## Known integration gaps

The naming cleanup preserves application behavior. Inspection identified existing issues to address before treating the dashboard as working:

- The browser API client defaults to port 5000, while the backend defaults to 5001.
- The browser requests `/api/llm/*`, while the backend registers `/api/query/*`.
- Several components request a named `apiService` export, while the client only exports a default.
- The user and saved-project interfaces call client methods that have not been implemented (`login`, `getUserProjects`, and `deleteProject`).

Live data coverage, spatial merging, model interpretation, and project persistence still need end-to-end verification. The manual `api_smoke_check.py` checks query processing and one debug endpoint; it is not a comprehensive test suite.

## Documentation

- [Calgary API setup notes](docs/calgary-api-setup.md)
- [Architecture diagrams](docs/architecture/system-overview.md)

Building data comes from OpenStreetMap and the City of Calgary Open Data portal. Some attributes are estimated or unavailable; the dashboard should distinguish those from source measurements as development continues.
