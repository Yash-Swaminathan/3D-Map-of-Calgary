from flask import Blueprint, jsonify, request, current_app
from app.services.calgary_data_fetcher import CalgaryDataFetcher
from app.services.building_processor import BuildingProcessor
from app.models.building import Building

buildings_bp = Blueprint('buildings', __name__)

@buildings_bp.route('/area', methods=['GET'])
def get_buildings_in_area():
    """Get buildings within a specified area using intelligent combined data sources"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        # Always use combined intelligent data source
        
        if not bounds_str:
            return jsonify({'error': 'bounds parameter is required (format: lat_min,lng_min,lat_max,lng_max)'}), 400
        
        try:
            bounds = [float(x) for x in bounds_str.split(',')]
            if len(bounds) != 4:
                raise ValueError("Invalid bounds format")
        except ValueError:
            return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        
        # Initialize services
        fetcher = CalgaryDataFetcher()
        processor = BuildingProcessor()
        
        # Check if we should refresh data or use cached data
        if refresh or Building.query.count() == 0:
            # Always use intelligent combined data source
            raw_data = fetcher.fetch_combined_building_data(bounds=tuple(bounds))
            
            if raw_data:
                # Process and store buildings
                buildings = processor.process_and_store_buildings(raw_data)
            else:
                return jsonify({'error': 'Failed to fetch building data'}), 500
        else:
            # Use cached data from database
            buildings = processor.get_buildings_in_bounds(tuple(bounds))
        
        # Convert to JSON
        buildings_json = [building.to_dict() for building in buildings]
        
        # Get statistics
        stats = processor.get_building_statistics(buildings)
        
        return jsonify({
            'success': True,
            'buildings': buildings_json,
            'statistics': stats,
            'bounds': bounds,
            'data_source': 'combined_intelligent',
            'cache_status': 'fresh' if refresh else 'cached'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/<int:building_id>', methods=['GET'])
def get_building_details(building_id):
    """Get detailed information about a specific building"""
    try:
        building = Building.query.get_or_404(building_id)
        
        return jsonify({
            'success': True,
            'building': building.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/filter', methods=['POST'])
def filter_buildings():
    """Filter buildings based on criteria"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        filter_criteria = data.get('filters')
        bounds = data.get('bounds')
        
        if not filter_criteria:
            return jsonify({'error': 'filters parameter is required'}), 400
        
        processor = BuildingProcessor()
        
        # Get buildings (either all or within bounds)
        if bounds and len(bounds) == 4:
            buildings = processor.get_buildings_in_bounds(tuple(bounds))
        else:
            buildings = Building.query.all()
        
        # Apply filters
        filtered_buildings = processor.filter_buildings(buildings, filter_criteria)
        
        # Convert to JSON
        buildings_json = [building.to_dict() for building in filtered_buildings]
        
        # Get statistics
        stats = processor.get_building_statistics(filtered_buildings)
        
        return jsonify({
            'success': True,
            'buildings': buildings_json,
            'statistics': stats,
            'filter_criteria': filter_criteria,
            'total_matched': len(filtered_buildings)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/refresh', methods=['POST'])
def refresh_building_data():
    """Force refresh of building data from Calgary Open Data API"""
    try:
        data = request.get_json() or {}
        bounds = data.get('bounds')
        
        # Initialize services
        fetcher = CalgaryDataFetcher()
        processor = BuildingProcessor()
        
        # Fetch fresh data
        if bounds and len(bounds) == 4:
            raw_data = fetcher.fetch_building_footprints(bounds=tuple(bounds))
        else:
            raw_data = fetcher.fetch_building_footprints()
        
        if not raw_data:
            return jsonify({'error': 'Failed to fetch building data from API'}), 500
        
        # Process and store buildings
        buildings = processor.process_and_store_buildings(raw_data)
        
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed {len(buildings)} buildings',
            'buildings_count': len(buildings)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/zoning', methods=['GET'])
def get_zoning_data():
    """Get zoning data for a specified area"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        limit = int(request.args.get('limit', 1000))
        
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) != 4:
                    raise ValueError("Invalid bounds format")
                bounds = tuple(bounds)
            except ValueError:
                return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        else:
            bounds = None
        
        # Fetch zoning data
        fetcher = CalgaryDataFetcher()
        zoning_data = fetcher.fetch_zoning_data(bounds=bounds, limit=limit)
        
        return jsonify({
            'success': True,
            'zoning_data': zoning_data,
            'bounds': bounds,
            'count': len(zoning_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@buildings_bp.route('/3d', methods=['GET'])
def get_3d_buildings():
    """Get 3D building data with height information"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        limit = int(request.args.get('limit', 500))
        
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) != 4:
                    raise ValueError("Invalid bounds format")
                bounds = tuple(bounds)
            except ValueError:
                return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        else:
            bounds = None
        
        # Fetch 3D building data
        fetcher = CalgaryDataFetcher()
        buildings_3d = fetcher.fetch_3d_buildings(bounds=bounds, limit=limit)
        
        return jsonify({
            'success': True,
            'buildings': buildings_3d,
            'bounds': bounds,
            'count': len(buildings_3d)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/osm', methods=['GET'])
def get_osm_buildings():
    """Get building data from OpenStreetMap"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        limit = int(request.args.get('limit', 100))
        
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) != 4:
                    raise ValueError("Invalid bounds format")
                bounds = tuple(bounds)
            except ValueError:
                return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        else:
            bounds = None
        
        # Fetch OSM building data
        fetcher = CalgaryDataFetcher()
        buildings_osm = fetcher.fetch_osm_buildings(bounds=bounds, limit=limit)
        
        return jsonify({
            'success': True,
            'buildings': buildings_osm,
            'bounds': bounds,
            'count': len(buildings_osm),
            'data_source': 'openstreetmap'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/statistics', methods=['GET'])
def get_building_statistics():
    """Get overall building statistics"""
    try:
        bounds_str = request.args.get('bounds')
        
        processor = BuildingProcessor()
        
        # Get buildings (either all or within bounds)
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) == 4:
                    buildings = processor.get_buildings_in_bounds(tuple(bounds))
                else:
                    buildings = Building.query.all()
            except ValueError:
                buildings = Building.query.all()
        else:
            buildings = Building.query.all()
        
        # Get statistics
        stats = processor.get_building_statistics(buildings)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@buildings_bp.route('/debug/calgary-fields', methods=['GET'])
def debug_calgary_fields():
    """Debug endpoint to see what fields are available in Calgary Open Data APIs using SODA format"""
    try:
        fetcher = CalgaryDataFetcher()
        debug_info = {}
        
        # Test 3D Buildings API with SODA format
        try:
            url = f"{fetcher.base_url}/cchr-krqg.json"
            params = {'$limit': 1}
            response = fetcher.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    debug_info['3d_buildings'] = {
                        'status': 'success',
                        'available_fields': list(data[0].keys()),
                        'sample_record': data[0],
                        'api_url': url,
                        'record_count': len(data)
                    }
                else:
                    debug_info['3d_buildings'] = {'status': 'no_data', 'api_url': url}
            else:
                debug_info['3d_buildings'] = {
                    'status': 'error',
                    'error': f"{response.status_code}: {response.text[:200]}",
                    'api_url': url
                }
        except Exception as e:
            debug_info['3d_buildings'] = {'status': 'exception', 'error': str(e)}
        
        # Test Building Footprints API with SODA format
        try:
            url = f"{fetcher.base_url}/uc4c-6kbd.json"
            params = {'$limit': 1}
            response = fetcher.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    debug_info['building_footprints'] = {
                        'status': 'success',
                        'available_fields': list(data[0].keys()),
                        'sample_record': data[0],
                        'api_url': url,
                        'record_count': len(data)
                    }
                else:
                    debug_info['building_footprints'] = {'status': 'no_data', 'api_url': url}
            else:
                debug_info['building_footprints'] = {
                    'status': 'error',
                    'error': f"{response.status_code}: {response.text[:200]}",
                    'api_url': url
                }
        except Exception as e:
            debug_info['building_footprints'] = {'status': 'exception', 'error': str(e)}
        
        # Test Property Assessments API with SODA format
        try:
            url = f"{fetcher.base_url}/4bsw-nn7w.json"
            params = {'$limit': 1}
            response = fetcher.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    debug_info['property_assessments'] = {
                        'status': 'success',
                        'available_fields': list(data[0].keys()),
                        'sample_record': data[0],
                        'api_url': url,
                        'record_count': len(data)
                    }
                else:
                    debug_info['property_assessments'] = {'status': 'no_data', 'api_url': url}
            else:
                debug_info['property_assessments'] = {
                    'status': 'error',
                    'error': f"{response.status_code}: {response.text[:200]}",
                    'api_url': url
                }
        except Exception as e:
            debug_info['property_assessments'] = {'status': 'exception', 'error': str(e)}
        
        # Test Zoning API with SODA format  
        try:
            url = f"{fetcher.base_url}/qe6k-p9nh.json"
            params = {'$limit': 1}
            response = fetcher.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    debug_info['zoning'] = {
                        'status': 'success',
                        'available_fields': list(data[0].keys()),
                        'sample_record': data[0],
                        'api_url': url,
                        'record_count': len(data)
                    }
                else:
                    debug_info['zoning'] = {'status': 'no_data', 'api_url': url}
            else:
                debug_info['zoning'] = {
                    'status': 'error',
                    'error': f"{response.status_code}: {response.text[:200]}",
                    'api_url': url
                }
        except Exception as e:
            debug_info['zoning'] = {'status': 'exception', 'error': str(e)}
        
        # Test Building Permits API with SODA format  
        try:
            url = f"{fetcher.base_url}/c2es-76ed.json"
            params = {'$limit': 1}
            response = fetcher.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    debug_info['building_permits'] = {
                        'status': 'success',
                        'available_fields': list(data[0].keys()),
                        'sample_record': data[0],
                        'api_url': url,
                        'record_count': len(data)
                    }
                else:
                    debug_info['building_permits'] = {'status': 'no_data', 'api_url': url}
            else:
                debug_info['building_permits'] = {
                    'status': 'error',
                    'error': f"{response.status_code}: {response.text[:200]}",
                    'api_url': url
                }
        except Exception as e:
            debug_info['building_permits'] = {'status': 'exception', 'error': str(e)}
        
        # Show authentication status
        auth_status = {
            'socrata_token_configured': bool(current_app.config.get('SOCRATA_APP_TOKEN')),
            'token_usage': 'NOT_USED - Calgary APIs work with anonymous access',
            'calgary_token_note': 'Calgary developer tokens are incompatible with Socrata format',
            'base_url': fetcher.base_url,
            'api_format': 'SODA 2.0/2.1 (/resource/ endpoints)',
            'authentication_method': 'Anonymous public access'
        }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'authentication': auth_status,
            'pagination_info': {
                'max_per_request': 1000,
                'soda_2_0_limit': 50000,
                'soda_2_1_limit': 'unlimited',
                'pagination_implemented': True
            },
            'analysis': {
                'zoning_fields_to_check': ['land_use_district', 'zoning', 'zone_class', 'zone_code', 'landuse', 'land_use', 'district_name'],
                # Construction year fields removed - not needed
                'value_fields_to_check': ['assessed_value', 'total_assessed_value', 'current_assessed_value', 'property_value']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@buildings_bp.route('/permits', methods=['GET'])
def get_building_permits():
    """Get building permits data for a specified area"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        limit = int(request.args.get('limit', 1000))
        
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) != 4:
                    raise ValueError("Invalid bounds format")
                bounds = tuple(bounds)
            except ValueError:
                return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        else:
            bounds = None
        
        # Fetch building permits data
        fetcher = CalgaryDataFetcher()
        permits_data = fetcher.fetch_building_permits(bounds=bounds, limit=limit)
        
        return jsonify({
            'success': True,
            'permits': permits_data,
            'bounds': bounds,
            'count': len(permits_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@buildings_bp.route('/assessments', methods=['GET'])
def get_property_assessments():
    """Get property assessment data for a specified area from Calgary Open Data"""
    try:
        # Parse query parameters
        bounds_str = request.args.get('bounds')
        limit = int(request.args.get('limit', 1000))
        
        if bounds_str:
            try:
                bounds = [float(x) for x in bounds_str.split(',')]
                if len(bounds) != 4:
                    raise ValueError("Invalid bounds format")
                bounds = tuple(bounds)
            except ValueError:
                return jsonify({'error': 'Invalid bounds format. Use: lat_min,lng_min,lat_max,lng_max'}), 400
        else:
            # Default to downtown Calgary bounds
            bounds = (51.0420, -114.0750, 51.0480, -114.0650)
        
        # Fetch property assessments data
        fetcher = CalgaryDataFetcher()
        assessments_data = fetcher.fetch_property_assessments(bounds=bounds, limit=limit)
        
        # Calculate some statistics for debugging
        if assessments_data:
            values = [a.get('assessed_value', 0) for a in assessments_data if a.get('assessed_value')]
            stats = {
                'count': len(values),
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'avg': sum(values) / len(values) if values else 0
            }
        else:
            stats = {'count': 0, 'min': 0, 'max': 0, 'avg': 0}
        
        return jsonify({
            'success': True,
            'assessments': assessments_data,
            'bounds': bounds,
            'count': len(assessments_data),
            'value_stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 