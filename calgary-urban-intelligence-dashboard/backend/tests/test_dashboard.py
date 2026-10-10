import unittest
from unittest.mock import patch, Mock
from app import create_app, db
from app.models.building import Building
from app.services.building_processor import BuildingProcessor
from app.services.building_query_service import BuildingQueryService
from app.services.calgary_data_fetcher import CalgaryDataFetcher

BOUNDS = [51.042, -114.075, 51.048, -114.065]
AREA = '/api/buildings/area?bounds=' + ','.join(str(x) for x in BOUNDS)

def sample(ident='test-1', lat=51.045, height=40, zoning='CC-X'):
    return {'building_id': ident, 'latitude': lat, 'longitude': -114.07,
            'height': height, 'building_type': 'Commercial', 'zoning': zoning,
            'assessed_value': 2000000, 'data_source': 'test_fixture', 'sources': ['test_fixture'],
            'footprint': [[-114.0701, lat-.0001], [-114.0699, lat-.0001],
                          [-114.0699, lat+.0001], [-114.0701, lat+.0001], [-114.0701, lat-.0001]]}

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(config_overrides={'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'ENABLE_LOCAL_LLM': False})
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def seed(self):
        return BuildingProcessor().process_and_store_buildings([sample(), sample('test-2', height=20, zoning=None)])

    def test_full_project_workflow_reapplies_same_filters_and_bounds(self):
        self.seed()
        BuildingProcessor().process_and_store_buildings([sample('outside', lat=51.1)])
        user = self.client.post('/api/users/login', json={'username': 'Tester'}).get_json()['user']
        response = self.client.post('/api/query/process', json={'query': 'commercial buildings over 100 feet', 'bounds': BOUNDS})
        self.assertEqual(response.status_code, 200)
        query = response.get_json()
        self.assertEqual(len(query['buildings']), 1)
        self.assertNotIn('value_min', query['filters'])
        project = self.client.post('/api/projects/save', json={'user_id': user['id'], 'name': 'Tall buildings', 'filters': query['filters']}).get_json()['project']
        self.assertEqual(len(self.client.get(f'/api/projects/user/{user["id"]}').get_json()['projects']), 1)
        loaded = self.client.post(f'/api/projects/{project["id"]}/load?apply_filters=true', json={'bounds': BOUNDS}).get_json()
        self.assertEqual([b['id'] for b in query['buildings']], [b['id'] for b in loaded['buildings']])
        self.assertEqual(self.client.delete(f'/api/projects/{project["id"]}').status_code, 200)
        self.assertEqual(self.client.get(f'/api/projects/{project["id"]}').status_code, 404)

    def test_cache_is_scoped_to_area_and_reports_first_fetch_as_fresh(self):
        self.seed()  # Untracked old rows must not prevent the first actual area fetch.
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample()]) as fetch:
            first = self.client.get(AREA).get_json()
            self.assertEqual(first['cache_status'], 'fresh')
            second = self.client.get(AREA).get_json()
            self.assertEqual(second['cache_status'], 'cached')
            self.assertEqual(fetch.call_count, 1)
            self.client.get('/api/buildings/area?bounds=51.049,-114.075,51.052,-114.065')
            self.assertEqual(fetch.call_count, 2)
            self.client.get(AREA + '&refresh=true')
            self.assertEqual(fetch.call_count, 3)

    def test_parser_units_and_money_suffixes(self):
        service = BuildingQueryService()
        cases = [
            ('buildings over 100 feet', {'height_min': 30.48}),
            ('buildings under 50 meters', {'height_max': 50}),
            ('properties over $2 million', {'value_min': 2000000}),
            ('buildings worth less than $500,000', {'value_max': 500000}),
            ('properties under $1.5m', {'value_max': 1500000}),
            ('commercial buildings worth more than $500k', {'building_type': 'commercial', 'value_min': 500000}),
            ('mixed use buildings', {'building_type': 'mixed use'}),
            ('R-CG zoning', {'zoning': 'R-CG'}),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                result = service.process_query(text)['filters']
                self.assertEqual(result.keys(), expected.keys())
                for key, value in expected.items():
                    if isinstance(value, (int, float)):
                        self.assertAlmostEqual(result[key], value)
                    else:
                        self.assertEqual(result[key], value)

    def test_unknown_values_do_not_match_and_zero_limits_work(self):
        unknown = Building(building_type=None, zoning=None, assessed_value=None, height=0)
        self.assertFalse(unknown.matches_filter({'zoning': 'CC-X'}))
        self.assertFalse(unknown.matches_filter({'building_type': 'commercial'}))
        self.assertFalse(unknown.matches_filter({'value_max': 500000}))
        self.assertTrue(unknown.matches_filter({'height_max': 0}))
        self.assertTrue(Building(building_type='Mixed Use').matches_filter({'building_type': 'mixed_use'}))

    def test_bad_inputs_return_400_and_missing_objects_return_404(self):
        for bounds in ['nan,-114,51,-113', '52,-114,51,-113', '51,-114,52,-113', 'bad']:
            self.assertEqual(self.client.get('/api/buildings/area?bounds=' + bounds).status_code, 400)
        self.assertEqual(self.client.post('/api/users/login', json={'username': 42}).status_code, 400)
        self.assertEqual(self.client.post('/api/query/process', json={'query': []}).status_code, 400)
        self.assertEqual(self.client.post('/api/buildings/filter', json={'filters': {'invented': 1}}).status_code, 400)
        self.assertEqual(self.client.get('/api/buildings/999').status_code, 404)
        self.assertFalse(self.client.post('/api/query/validate', json={'filters': {'height_min': 50, 'height_max': 20}}).get_json()['valid'])

    def test_source_geometry_and_missing_values_survive_storage(self):
        fetcher = CalgaryDataFetcher()
        footprint = sample()['footprint']
        record = {'multipolygon': {'type': 'MultiPolygon', 'coordinates': [[footprint]]}, 'x_coord': '12345', 'y_coord': '67890'}
        building = fetcher._building(record, 'calgary_footprints')
        self.assertAlmostEqual(building['latitude'], 51.045)
        self.assertIsNone(building['address'])
        self.assertIsNone(building['assessed_value'])
        self.assertIsNone(building['height'])
        stored = BuildingProcessor().process_and_store_buildings([building])[0].to_dict()
        self.assertEqual(stored['sources'], ['calgary_footprints'])
        self.assertEqual(stored['footprint'], building['footprint'])
        self.assertIsNone(stored['assessed_value'])

    def test_duplicate_geometries_do_not_break_storage_and_refresh_removes_old_rows(self):
        self.assertEqual(len(BuildingProcessor().process_and_store_buildings([sample(), sample()])), 1)
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample()]):
            self.assertEqual(len(self.client.get(AREA).get_json()['buildings']), 1)
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample('replacement')]):
            refreshed = self.client.get(AREA + '&refresh=true').get_json()
            self.assertEqual([b['building_id'] for b in refreshed['buildings']], ['replacement'])

    def test_polygon_queries_include_districts_crossing_the_area_boundary(self):
        fetcher = CalgaryDataFetcher()
        with patch.object(fetcher, 'fetch_all_records', return_value=[]) as fetch:
            fetcher.fetch_zoning_data(bounds=BOUNDS)
            clause = fetch.call_args.kwargs['additional_params']['$where']
            self.assertIn('intersects(multipolygon', clause)
            self.assertIn('-114.075 51.042', clause)

    def test_city_classifications_and_repaired_source_polygons(self):
        fetcher = CalgaryDataFetcher()
        polygon = {'type': 'Polygon', 'coordinates': [sample()['footprint']]}
        building = fetcher._building({'polygon': polygon, 'bldg_code_desc': 'Commercial'}, 'calgary_footprints')
        self.assertEqual(building['building_type'], 'Commercial')
        invalid = {'type': 'Polygon', 'coordinates': [[[-114.071,51.044],[-114.069,51.046],[-114.069,51.044],[-114.071,51.046],[-114.071,51.044]]]}
        repaired = fetcher._geometry({'multipolygon': invalid})
        self.assertIsNotNone(repaired)
        self.assertTrue(repaired.is_valid)

    def test_osm_retry_does_not_forward_calgary_token(self):
        import requests
        self.app.config['CALGARY_DEVELOPER_TOKEN'] = 'test-token'
        fetcher = CalgaryDataFetcher()
        response = Mock()
        response.json.return_value = {'elements': []}
        with patch('app.services.calgary_data_fetcher.requests.post', side_effect=[requests.RequestException('Test outage'), response]) as post:
            self.assertEqual(fetcher.fetch_osm_buildings(BOUNDS), [])
            self.assertEqual(post.call_count, 2)
            for call in post.call_args_list:
                self.assertNotIn('X-App-Token', call.kwargs['headers'])
        self.assertEqual(fetcher.warnings, [])

    def test_failed_refresh_preserves_existing_cache(self):
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample()]):
            self.assertEqual(self.client.get(AREA).status_code, 200)
        def fail(fetcher, **kwargs):
            fetcher.warnings.append('Test upstream failure')
            return []
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', fail):
            self.assertEqual(self.client.get(AREA + '&refresh=true').status_code, 502)
            self.assertEqual(len(self.client.get(AREA).get_json()['buildings']), 1)

    def test_pagination_returns_more_than_500_without_refetching(self):
        records = [sample(f'building-{i:04d}') for i in range(1205)]
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=records) as fetch:
            collected = []
            offset = 0
            version = None
            while offset is not None:
                response = self.client.get(AREA + f'&offset={offset}' + (f'&version={version}' if version else ''))
                self.assertEqual(response.status_code, 200)
                page = response.get_json()
                collected.extend(page['buildings'])
                offset = page['next_offset']
                version = page['version']
                self.assertEqual(page['total_count'], 1205)
            self.assertEqual(len({b['building_id'] for b in collected}), 1205)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(self.client.get(AREA + '&version=stale').status_code, 409)

    def test_refresh_does_not_destroy_overlapping_area_membership(self):
        other = '/api/buildings/area?bounds=51.044,-114.075,51.050,-114.065'
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample()]):
            self.client.get(AREA)
            self.client.get(other)
        with patch.object(CalgaryDataFetcher, 'fetch_combined_building_data', return_value=[sample('new')]):
            self.client.get(AREA + '&refresh=true')
        self.assertEqual([b['building_id'] for b in self.client.get(other).get_json()['buildings']], ['test-1'])
        self.assertEqual([b['building_id'] for b in self.client.get(AREA).get_json()['buildings']], ['new'])

    def test_unlimited_source_pagination_uses_stable_order_and_offsets(self):
        fetcher = CalgaryDataFetcher()
        responses = []
        for batch in [[{'id': i} for i in range(1000)], [{'id': i} for i in range(1000, 1407)]]:
            response = Mock()
            response.json.return_value = batch
            responses.append(response)
        with patch.object(fetcher.session, 'get', side_effect=responses) as get:
            rows = fetcher.fetch_all_records('dataset', max_total_records=None)
        self.assertEqual(len(rows), 1407)
        self.assertEqual([call.kwargs['params']['$offset'] for call in get.call_args_list], [0, 1000])
        self.assertTrue(all(call.kwargs['params']['$order'] == ':id' for call in get.call_args_list))

    def test_combined_fetch_keeps_buildings_crossing_view_boundary(self):
        fetcher = CalgaryDataFetcher()
        crossing = sample(lat=51.04195)
        with patch.object(fetcher, 'fetch_building_footprints', return_value=[crossing]), \
             patch.object(fetcher, 'fetch_3d_buildings', return_value=[]), \
             patch.object(fetcher, 'fetch_zoning_data', return_value=[]), \
             patch.object(fetcher, 'fetch_property_assessments', return_value=[]), \
             patch.object(fetcher, 'fetch_building_permits', return_value=[]):
            crossing['sources'] = ['test']
            crossing['permits'] = []
            result = fetcher.fetch_combined_building_data(BOUNDS, include_osm=False)
        self.assertEqual(len(result), 1)

    def test_regional_query_bounds_are_supported(self):
        self.seed()
        response = self.client.post('/api/query/process', json={
            'query': 'buildings over 100 feet', 'bounds': [51.02, -114.12, 51.08, -114.02]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['buildings']), 1)

    def test_city_density_is_geographic_live_cached_and_refreshable(self):
        from app.services import building_coverage_service as coverage
        coverage._cache.clear()
        response = Mock()
        response.json.return_value = [{'count': '100'}]
        url = '/api/buildings/coverage?bounds=50.9,-114.3,51.2,-113.9&density=true'
        with patch('app.services.calgary_data_fetcher.requests.Session.get', return_value=response) as get:
            result = self.client.get(url)
            self.assertEqual(result.status_code, 200)
            data = result.get_json()
            self.assertEqual(data['source_record_count'], 100)
            self.assertEqual(len(data['density_cells']), 16)
            self.assertEqual(len({tuple(c['bounds']) for c in data['density_cells']}), 16)
            self.assertTrue(all(c['count'] == 100 for c in data['density_cells']))
            self.assertEqual(get.call_count, 17)
            self.client.get(url)
            self.assertEqual(get.call_count, 17)
            self.client.get(url + '&refresh=true')
            self.assertEqual(get.call_count, 34)
            moved = self.client.get('/api/buildings/coverage?bounds=51.0,-114.2,51.3,-113.8&density=true').get_json()
            self.assertNotEqual(data['density_cells'][0]['bounds'], moved['density_cells'][0]['bounds'])
        coverage._cache.clear()

if __name__ == '__main__':
    unittest.main()
