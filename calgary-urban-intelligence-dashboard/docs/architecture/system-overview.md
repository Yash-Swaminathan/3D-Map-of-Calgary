# System architecture

~~~mermaid
flowchart LR
    Browser[React dashboard] --> Map[Three.js map]
    Browser -->|GET /api/buildings/area| Area[Area route]
    Area --> Cache{Exact area cached?}
    Cache -->|Yes, no refresh| Rows[(Cached buildings)]
    Cache -->|No or refresh| Fetcher[CalgaryDataFetcher]
    Fetcher --> Sources[Five Calgary datasets + OpenStreetMap]
    Sources --> Join[Spatial joins with Shapely]
    Join --> Processor[BuildingProcessor]
    Processor --> Rows
    Rows --> Browser
    Browser -->|POST /api/query/process| Query[BuildingQueryService]
    Query --> Rules[Supported deterministic rules]
    Rules -->|Unrecognized and enabled| Model[Optional lazy local Flan-T5]
    Rules --> Filter[Validated filter dictionary]
    Model --> Filter
    Filter --> Match[Building.matches_filter]
    Rows --> Match
    Match --> Browser
    Browser -->|/api/projects| Projects[Saved project routes]
    Projects --> Saved[(User identity + project filters)]
    Saved -->|Load within current bounds| Match
~~~

Flask normally runs on port 5001. One shared browser HTTP client calls /api/query for questions and supplies the same bounds for area requests and project loads. The development server proxies /api to Flask.

CalgaryDataFetcher requests independent bounded sources concurrently. It merges heights and OSM tags into outlines, matches zoning by polygon containment, and matches property records by footprint overlap. Source attributes and permits are stored in building_details alongside buildings. Unknown values remain unknown; matched assessments are not whole-building totals.

cached_areas stores exact rectangles, warnings, and fetch times, including successful empty areas. Refresh fetches before replacing rows; upstream failures preserve cached data. Caches do not automatically expire.

The database, query parser, and map use meter heights. A bounds-derived origin serves both positions and footprints, preserving geography across filtering. Unknown-height meshes have a disclosed display placeholder. Colors represent building use.

projects stores filter dictionaries as JSON without copying buildings. Live queries and project loads call Building.matches_filter. Unknown attributes fail requested attribute filters. users supplies username identification without authentication.

SQLite is the default; DATABASE_URL selects another SQLAlchemy backend. Common rules work without ML packages. Optional Flan-T5 loads only for unsupported wording when enabled.
