# Calgary Open Data setup

Public datasets use Calgary's Socrata JSON endpoints. Set the optional CALGARY_DEVELOPER_TOKEN in backend/.env if you have one. That token is never sent to OpenStreetMap.

| Dataset | ID | Geometry field | Attributes used |
| --- | --- | --- | --- |
| Building outlines | uc4c-6kbd | multipolygon | bldg_code_desc, footprints |
| 3D buildings | cchr-krqg | polygon | struct_id, rooftop_elev_z, grd_elev_min_z |
| Land-use districts | qe6k-p9nh | multipolygon | lu_code, description |
| Property assessments | 4bsw-nn7w | multipolygon | roll_number, assessed_value, address, classification |
| Building permits | c2es-76ed | point | permitnum, statuscurrent, description, applieddate |

Schemas were checked against live /api/views/{id}.json metadata during the repair. Polygon queries use [Socrata's intersects function](https://dev.socrata.com/docs/functions/intersects) with a WKT rectangle so districts crossing the area boundary are included. WKT uses longitude before latitude. GeoJSON supplies geographic coordinates; the old approximate x_coord/y_coord conversion is removed. Invalid source geometries are repaired with Shapely.

Official datasets: [building outlines](https://data.calgary.ca/Base-Maps/Buildings/uc4c-6kbd/about_data), [3D buildings](https://data.calgary.ca/d/cchr-krqg), [land-use districts](https://data.calgary.ca/d/qe6k-p9nh), [assessments](https://data.calgary.ca/d/4bsw-nn7w), and [permits](https://data.calgary.ca/d/c2es-76ed).

## Check the API

With the backend running:

~~~powershell
Invoke-RestMethod 'http://localhost:5001/api/health'
Invoke-RestMethod 'http://localhost:5001/api/buildings/area?bounds=51.042,-114.075,51.048,-114.065'
~~~

Responses include buildings, statistics, cache_status, fetched_at, and source warnings. Add &refresh=true to fetch again. Initial requests can take roughly a minute while public APIs respond. OpenStreetMap enrichment tries a second Overpass endpoint when the first fails.

Supported rules require no model or API key. Optional local Flan-T5 is described in the README. HUGGINGFACE_API_KEY is not a hosted inference setting.
