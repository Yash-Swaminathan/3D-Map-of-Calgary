# Calgary Urban Intelligence Dashboard: implementation plan

## Outcome

Build a usable Calgary exploration and analysis dashboard: open a map, find a neighbourhood or address, see buildings promptly, ask a supported question, understand the evidence and missing data, compare areas, and save or export an analysis.

This plan extends the existing React, Three.js, Flask, Socrata and SQLite application. City data remains the source of building facts. An optional language model translates questions into validated filters; it does not invent attributes or determine which buildings exist.

## Starting point

- Dynamic, paginated tile loading and geographic cache membership work.
- The wider starting view rendered 9,989 buildings in verification; the Wider area view rendered 35,929. These are observed counts, not fixed application data.
- Larger views use simplified building shapes; the city overview uses live geographic roof-density counts.
- Height, type, assessed-value and zoning filters, building details and saved filter projects work.
- The current suite has 17 backend tests, 7 frontend tests and browser workflow checks.
- First visits still wait for all enrichment sources. The map lacks roads, river and neighbourhood labels. Question parsing can ignore unsupported parts. Saved projects have no authenticated ownership. Flan-T5 is optional and experimental.

## Delivery order

| Milestone | Main result | Depends on |
| --- | --- | --- |
| 1. Progressive loading | Buildings appear before enrichment finishes; stale data refreshes safely | Existing dynamic tile loader |
| 2. Geographic navigation | Roads, river, labels and neighbourhood/address search | Milestone 1 loading contracts |
| 3. Trustworthy data and questions | Provenance, complete question interpretation and optional model adapter | Source status from 1; area selection from 2 |
| 4. Analysis workspace | Area comparisons, charts, export and saved map context | Reliable data and filters from 3 |
| 5. Shared project access | Authenticated sessions and project ownership | Saved project model from 4 |
| 6. Public release | Persistent deployment, automated checks and documented demo | Previous milestone acceptance checks |

Each milestone ends with a working, reviewable increment. Security work must land before public users can access shared project writes. A read-only demo can be staged earlier.

## 1. Make loading progressive and resilient

### Build

1. Measure first-visible-building time, full regional load time, frame rate and API payload size on the existing default and Wider area views. Record browser, hardware, bounds and cache state.
2. Introduce a tile-loading service that separates geometry from height, zoning, assessment and permit enrichment. Return available geometry immediately; fetch the other sources independently.
3. Persist tile job state, per-source timestamps, completion/error status and retry state. Use a bounded worker pool initially, behind an interface that can move to a separate worker process for deployment. Recover interrupted jobs after restart.
4. Keep geometry pagination tied to a stable membership revision. Give enrichment its own revision so metadata updates do not invalidate geometry pages.
5. Add a lightweight job/status endpoint. The client polls active jobs, merges arriving attributes by stable building ID and reapplies filters. Show which attributes are still loading; incomplete results must not look final.
6. Keep usable buildings visible while replacing stale data. Ignore responses from an old view. Deduplicate concurrent requests for the same tile.
7. Add source-specific cache expiry, bounded retries with backoff, and explicit refresh. A failed refresh preserves the last successful source result and displays its age.
8. Add database migrations for new job/cache schema. Keep SQLite for local development; decide on a shared deployment database after profiling concurrency.

Primary files: `backend/app/services/calgary_data_fetcher.py`, `backend/app/routes/buildings.py`, `backend/app/models/building.py`, `frontend/src/App.js`, `frontend/src/services/dashboardApi.js`. Extract loading orchestration from App into a dedicated hook/service as this grows.

### Acceptance

- Delay the assessment API in a test: buildings still appear and remain navigable.
- Failed sources produce a specific status; other sources continue loading.
- Rapid pan/zoom cannot display results from the wrong view.
- Concurrent tile requests reuse one upstream job; restart resumes interrupted work.
- Refresh failure preserves cached geometry and attributes.
- Record before/after performance on identical areas. Initial targets under healthy upstream responses: first geometry within 10 seconds on an uncached view and first cached geometry within 2 seconds. These are targets to validate, not current guarantees.

## 2. Add geographic context and useful navigation

### Build

1. Prototype MapLibre GL JS as the geographic map/camera, with the existing Three.js buildings in a custom layer. Confirm projection, picking and instanced rendering before replacing the current canvas controls.
2. Align building geometry and density cells to the geographic projection. Check positions and metre heights against known Calgary landmarks.
3. Add a configured basemap with roads, river, place labels and attribution. Verify the chosen tile provider's usage terms, availability and costs before deployment; the rendering library does not supply unrestricted hosted map tiles.
4. Discover and validate City community-boundary and address datasets. Build indexed local neighbourhood/address search from verified records where practical; introduce an external geocoder only if needed and configured explicitly.
5. Add neighbourhood selection, fit-to-area, clear north/scale indicators and a shareable URL containing map position, zoom and filters.
6. Preserve the Wider area behaviour around the current location, building selection, mobile controls and city-density navigation.

Primary files: `frontend/src/components/CalgaryMap3D/`, `frontend/src/utils/mapCoordinates.js`, `frontend/src/utils/viewport.js`; add a geographic search service and endpoint.

Reference: [MapLibre's official Three.js custom-layer example](https://maplibre.org/maplibre-gl-js/docs/examples/add-a-3d-model-using-threejs/). The integration still needs validation with this project's building renderer.

### Acceptance

- Select a neighbourhood or search an address without entering coordinates.
- Buildings stay aligned with roads through pan, zoom, rotation and resize.
- Open a shared URL on a fresh browser and restore the same study area and filters.
- Detailed, simplified and density views remain selectable and responsive.
- A basemap/search outage has a visible fallback and does not erase building data.

## 3. Make data and questions trustworthy

### Data work

- Preserve multipart geometry and relevant polygon holes instead of keeping only the largest exterior ring.
- Store source identifiers, observation/fetch dates and matching evidence. Represent multiple assessment/parcel matches explicitly rather than silently choosing one as the building total.
- Define consistent matching rules at tile boundaries; an incomplete neighbouring fetch must not erase a previously known attribute without explanation.
- Show known, missing, estimated-for-display and still-loading attributes separately.
- Add fixtures for multipart buildings, duplicate outlines, boundary crossings and multiple assessments.

### Question work

1. Define a structured query contract: supported filters, geographic scope, interpreted clauses, unsupported clauses and requests for clarification.
2. Extend deterministic parsing and regression cases. Unsupported criteria must be reported even when another part of the question is understood.
3. Display the interpretation before or alongside results. For example, `commercial buildings near schools` must explain that proximity is unsupported until school data and distance filtering exist.
4. Add an optional model-provider interface. Implement and evaluate a local Ollama adapter first if the development machine can support it. Keep model name and endpoint configurable, with strict filter validation, timeouts and a rules fallback.
5. Evaluate hosted inference separately if needed. Do not assume a permanently free Hugging Face or hosted Ollama service. Keep server-side credentials out of the browser.
6. Create a fixed evaluation set containing supported, compound, ambiguous and unsupported questions. A model cannot add filters that the backend cannot execute.

Primary files: `backend/app/services/building_processor.py`, `backend/app/services/building_query_service.py`, `backend/app/utils/validation.py`, `frontend/src/components/BuildingQueryPanel/`, `frontend/src/components/BuildingDetailsPanel/`.

### Acceptance

- Every interpreted clause is applied or explicitly flagged; no silently discarded proximity or date requirement.
- Unknown values never satisfy attribute filters.
- Invalid model output cannot change query scope or execute arbitrary code/SQL.
- Rules continue working without a model or network inference service.
- Saved filters and new questions produce consistent results on the same data revision.
- Every displayed assessment identifies its scope and source date.

## 4. Build the analysis workspace

### Build

- Define comparisons using study-area bounds or neighbourhood polygons, the active filters and the same source-date rules.
- Add building-use distribution, known-height distribution, assessment summaries and permit activity by date/status.
- Show denominators and missing-data coverage beside each metric. Describe assessment summaries as matched property-record statistics, not whole-building or whole-neighbourhood totals unless that aggregation is supported.
- Compare two selected areas using the same criteria and include source/coverage differences.
- Export filtered records to CSV with identifiers, units, source dates and missing values; optionally export geometry as GeoJSON.
- Extend saved projects to optionally preserve area, camera, comparison selections and query text alongside filters. Migrate existing filter-only projects safely.

Primary files: add backend analysis routes/services and frontend analysis panels; extend `backend/app/models/project.py`, `backend/app/routes/projects.py` and `frontend/src/components/SavedProjectsPanel/`.

### Acceptance

- Chart values agree with the underlying filtered records and export.
- A permit-status/date query actually applies those criteria to verified permit records.
- A saved analysis restores its geographic context and criteria.
- Partial coverage and missing measurements remain visible in comparisons.

## 5. Protect shared saved projects

### Build

- Replace username-only identification with a supported authentication/session approach.
- Derive ownership from the authenticated session, not a submitted user ID.
- Enforce ownership for list, read, update, load and delete operations.
- Define an explicit read-only public demo mode and an isolated guest-project policy if guest saving is retained.
- Add request limits for expensive fetch, refresh and model operations, and secure production configuration.

### Acceptance

- One user cannot read or change another user's private projects by guessing an ID.
- Existing local projects have a documented migration/claim path.
- The public demo cannot write into another visitor's project collection.

## 6. Deploy and finish the release

### Build

- Choose hosting after measuring web/worker memory and cold-load behaviour; document expected operating costs and any tile/inference limits.
- Configure a production web server, durable database storage, worker recovery, HTTPS, secrets and backups. Verify that cached areas and projects survive restart/redeployment.
- Add CI for backend tests, frontend tests/build and a deterministic browser regression using controlled fixtures. Keep separate live-source smoke checks for API/schema drift.
- Add structured source/job error logs and health checks covering database and worker state.
- Run desktop/mobile end-to-end checks: navigate, query, inspect, compare, save/load, export, retry and reopen a shared URL.
- Publish updated setup instructions, architecture, screenshots, a short demo walkthrough and an honest supported-question/known-limits list.

### Acceptance

- A fresh checkout can be set up from the documented instructions.
- A fresh public visitor can navigate and run a supported question without local setup.
- Data and projects survive deployment restart; interrupted work recovers.
- Automated checks pass; a simulated source outage leaves the dashboard usable.

## What happens first

The first implementation increment is Milestone 1: capture a performance baseline, introduce independent geometry/enrichment loading, and make delayed assessment data a regression test. The next increment is the geographic map prototype, with projection and selection checks before migrating the current controls.

Do not begin with a larger model, a full frontend rewrite, citywide downloads on every launch or speculative infrastructure. Add new datasets and backend filters when a specific analysis requires them, with their own validation and coverage checks.

## Release discipline and decisions

- Make small commits around complete behaviour changes; verify each milestone before promoting changes to master.
- Keep planning targets separate from measured results in the README.
- User decisions needed later: hosting/cost preference, tile provider if an account is required, and whether private multi-user projects are required for the first public release. These do not block progressive loading or the local basemap prototype.
- Create provider accounts and supply secrets only when the chosen integration requires them. No additional key is required to start Milestone 1.
