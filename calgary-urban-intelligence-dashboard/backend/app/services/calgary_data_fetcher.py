"""Bounded Calgary/OSM fetching with measured attributes and spatial joins."""
import hashlib
import logging
import math
from concurrent.futures import ThreadPoolExecutor
import requests
from flask import current_app
from shapely.geometry import shape, Point, box
from shapely.strtree import STRtree
from shapely import make_valid
from shapely.errors import ShapelyError

logger = logging.getLogger(__name__)
DEFAULT_BOUNDS = (51.042, -114.075, 51.048, -114.065)

class CalgaryDataFetcher:
    def __init__(self):
        self.base_url = current_app.config.get('CALGARY_OPEN_DATA_BASE_URL', 'https://data.calgary.ca/resource')
        self.osm_url = 'https://overpass-api.de/api/interpreter'
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json', 'User-Agent': 'Calgary-Urban-Intelligence-Dashboard/1.0'})
        token = current_app.config.get('CALGARY_DEVELOPER_TOKEN')
        if token:
            self.session.headers['X-App-Token'] = token
        self.warnings = []

    def fetch_all_records(self, dataset_id, limit_per_request=1000, max_total_records=1000, additional_params=None):
        records = []
        try:
            while max_total_records is None or len(records) < max_total_records:
                page_size = min(limit_per_request, 5000)
                if max_total_records is not None:
                    page_size = min(page_size, max_total_records - len(records))
                params = {'$order': ':id', '$limit': page_size, '$offset': len(records)}
                params.update(additional_params or {})
                response = self.session.get(f'{self.base_url}/{dataset_id}.json', params=params, timeout=20)
                response.raise_for_status()
                batch = response.json()
                if not isinstance(batch, list):
                    raise ValueError('Expected a list of records')
                records.extend(batch)
                if len(batch) < page_size:
                    break
        except (requests.RequestException, ValueError) as error:
            logger.warning('%s unavailable: %s', dataset_id, error)
            self.warnings.append(f'Calgary dataset {dataset_id} is unavailable or incomplete.')
        return records[:max_total_records]

    def _bounded(self, dataset, field, bounds, limit, order=None, parcel_ids=None):
        south, west, north, east = bounds or DEFAULT_BOUNDS
        polygon = f'POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))'
        params = {'$where': f"intersects({field}, '{polygon}')"}
        if parcel_ids:
            quoted = ["'" + str(v).replace("'", "''") + "'" for v in parcel_ids]
            params['$where'] += ' AND roll_number in (' + ','.join(quoted) + ')'
        if order:
            params['$order'] = order + ', :id'
        return self.fetch_all_records(dataset, limit_per_request=5000, max_total_records=limit, additional_params=params)

    @staticmethod
    def _number(value):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _geometry(record):
        for key in ['multipolygon', 'polygon', 'point', 'geometry']:
            geo = record.get(key)
            if isinstance(geo, dict) and geo.get('coordinates'):
                try:
                    result = shape(geo)
                    if not result.is_valid:
                        result = make_valid(result)
                    if not result.is_empty:
                        return result
                except (ValueError, TypeError, ShapelyError):
                    pass
        return None

    def _building(self, record, source):
        geo = self._geometry(record)
        if geo is None or geo.geom_type not in {'Polygon', 'MultiPolygon'}:
            return None
        polygon = max(geo.geoms, key=lambda g: g.area) if geo.geom_type == 'MultiPolygon' else geo
        center = polygon.centroid
        height = None
        if source == 'calgary_3d':
            roof, ground = self._number(record.get('rooftop_elev_z')), self._number(record.get('grd_elev_min_z'))
            if roof is not None and ground is not None and roof > ground:
                height = roof - ground
        description = str(record.get('bldg_code_desc') or '').lower()
        kind = next((label for token, label in [('commercial', 'Commercial'), ('residential', 'Residential'),
                    ('industrial', 'Industrial'), ('mixed', 'Mixed Use')] if token in description), 'Unknown')
        ident = record.get('struct_id') or hashlib.sha256(polygon.wkb).hexdigest()[:24]
        return {'building_id': f'{source}_{ident}', 'latitude': center.y, 'longitude': center.x,
                'footprint': [list(c[:2]) for c in polygon.exterior.coords],
                'height': height, 'height_source': source if height is not None else None,
                'building_type': kind, 'source_building_use': record.get('bldg_code_desc'), 'address': None, 'assessed_value': None,
                'zoning': None, 'data_source': source, 'sources': [source], 'permits': []}

    def fetch_building_footprints(self, bounds=None, limit=1000):
        rows = self._bounded('uc4c-6kbd', 'multipolygon', bounds, limit)
        return [b for row in rows if (b := self._building(row, 'calgary_footprints'))]

    def fetch_3d_buildings(self, bounds=None, limit=500):
        rows = self._bounded('cchr-krqg', 'polygon', bounds, limit)
        return [b for row in rows if (b := self._building(row, 'calgary_3d'))]

    def fetch_zoning_data(self, bounds=None, limit=1000):
        return self._bounded('qe6k-p9nh', 'multipolygon', bounds, limit)

    def fetch_property_assessments(self, parcel_ids=None, bounds=None, limit=1000):
        rows = self._bounded('4bsw-nn7w', 'multipolygon', bounds, limit, parcel_ids=parcel_ids)
        for row in rows:
            row['assessed_value'] = self._number(row.get('assessed_value'))
        return rows

    def fetch_building_permits(self, bounds=None, limit=1000):
        return self._bounded('c2es-76ed', 'point', bounds, limit, order='applieddate DESC')

    def fetch_osm_buildings(self, bounds=None, limit=500):
        south, west, north, east = bounds or DEFAULT_BOUNDS
        query = f'[out:json][timeout:20];way["building"]({south},{west},{north},{east});out tags geom;'
        try:
            # Calgary's token must never be sent to OpenStreetMap.
            response = None
            for endpoint in [self.osm_url, 'https://overpass.kumi.systems/api/interpreter']:
                try:
                    response = requests.post(endpoint, data={'data': query},
                                             headers={'User-Agent': 'Calgary-Urban-Intelligence-Dashboard/1.0'}, timeout=25)
                    response.raise_for_status()
                    break
                except requests.RequestException:
                    if endpoint != self.osm_url:
                        raise
            result = []
            for element in response.json().get('elements', [])[:limit]:
                tags = element.get('tags', {})
                points = [[g['lon'], g['lat']] for g in element.get('geometry', [])]
                if len(points) < 3:
                    continue
                row = {'geometry': {'type': 'Polygon', 'coordinates': [points]}}
                building = self._building(row, 'openstreetmap')
                if not building:
                    continue
                building['building_id'] = f'osm_way_{element["id"]}'
                raw_height = str(tags.get('height', '')).strip().removesuffix('m').strip()
                building['height'] = self._number(raw_height)
                building['height_source'] = 'openstreetmap' if building['height'] is not None else None
                building['floors'] = self._number(tags.get('building:levels'))
                kind = tags.get('building:use') or tags.get('building')
                mapping = {'apartments': 'Residential', 'house': 'Residential', 'residential': 'Residential',
                           'office': 'Commercial', 'retail': 'Commercial', 'commercial': 'Commercial',
                           'industrial': 'Industrial', 'warehouse': 'Industrial', 'mixed_use': 'Mixed Use'}
                building['building_type'] = mapping.get(kind, 'Unknown')
                address = ' '.join(str(tags[k]) for k in ['addr:housenumber', 'addr:street'] if tags.get(k))
                building['address'] = address or tags.get('name')
                result.append(building)
            return result
        except (requests.RequestException, ValueError, KeyError) as error:
            logger.warning('OpenStreetMap unavailable: %s', error)
            self.warnings.append('OpenStreetMap enrichment is unavailable.')
            return []

    @staticmethod
    def _building_polygon(building):
        return shape({'type': 'Polygon', 'coordinates': [building['footprint']]})

    def fetch_combined_building_data(self, bounds=None, limit=None, include_osm=True):
        # Sources are independent and bounded; fetch once per source.
        methods = [self.fetch_building_footprints, self.fetch_3d_buildings, self.fetch_osm_buildings,
                   self.fetch_zoning_data, self.fetch_property_assessments, self.fetch_building_permits]
        def fetch(method):
            if method == self.fetch_osm_buildings and not include_osm:
                return []
            return method(bounds=bounds, limit=limit)
        with ThreadPoolExecutor(max_workers=6) as pool:
            footprints, heights, osm, zones, assessments, permits = list(pool.map(fetch, methods))
        buildings = footprints or heights or osm
        if not buildings:
            return []
        buildings = list({b['building_id']: b for b in buildings}.values())
        # Join heights and OSM tags only to an existing footprint containing their center.
        shapes = [(b, self._building_polygon(b)) for b in buildings]
        tree = STRtree([g for _, g in shapes])
        known_ids = {b['building_id'] for b in buildings}
        for additions in [heights, osm]:
            if additions is buildings:
                continue
            for record in additions:
                point = Point(record['longitude'], record['latitude'])
                target = next((shapes[i][0] for i in tree.query(point, predicate='covered_by')), None)
                if target:
                    for key in ['height', 'height_source', 'floors', 'address']:
                        if record.get(key) is not None and target.get(key) is None:
                            target[key] = record[key]
                    if record.get('building_type') != 'Unknown':
                        target['building_type'] = record['building_type']
                    target['sources'] = list(dict.fromkeys(target['sources'] + record['sources']))
                elif additions is osm:
                    if record['building_id'] not in known_ids:
                        buildings.append(record)
                        shapes.append((record, self._building_polygon(record)))
                        known_ids.add(record['building_id'])
                        tree = STRtree([g for _, g in shapes])
        def indexed(rows):
            pairs = [(row, g) for row in rows if (g := self._geometry(row)) is not None]
            return pairs, STRtree([g for _, g in pairs])
        zone_shapes, zone_tree = indexed(zones)
        assessment_shapes, assessment_tree = indexed(assessments)
        permit_shapes, permit_tree = indexed(permits)
        for building in buildings:
            polygon = self._building_polygon(building)
            point = polygon.representative_point()
            zone = next((zone_shapes[i][0] for i in zone_tree.query(point, predicate='covered_by')), None)
            if zone:
                building['zoning'] = zone.get('lu_code')
                building['land_use'] = zone.get('description')
                building['sources'].append('calgary_zoning')
            matches = [(assessment_shapes[i][0], polygon.intersection(assessment_shapes[i][1]).area)
                       for i in assessment_tree.query(polygon, predicate='intersects')]
            if matches:
                assessment, area = max(matches, key=lambda pair: pair[1])
                if area > polygon.area * 0.5:
                    for key in ['assessed_value', 'address', 'roll_number', 'roll_year', 'property_type',
                                'assessment_class_description', 'land_use_designation', 'comm_name', 'year_of_construction']:
                        if assessment.get(key) is not None:
                            building[key] = assessment[key]
                    if building['building_type'] == 'Unknown' and assessment.get('assessment_class_description') == 'Residential':
                        building['building_type'] = 'Residential'
                    building['assessment_scope'] = 'Matched property record; not a whole-building total'
                    building['sources'].append('calgary_assessments')
            building['permits'] = [
                {k: row.get(k) for k in ['permitnum', 'statuscurrent', 'description', 'applieddate', 'estprojectcost']}
                for i in permit_tree.query(polygon, predicate='covers') for row in [permit_shapes[i][0]]
            ]
            if building['permits']:
                building['sources'].append('calgary_permits')
        south, west, north, east = bounds or DEFAULT_BOUNDS
        viewport = box(west, south, east, north)
        return [b for b in buildings if self._building_polygon(b).intersects(viewport)][:limit]
