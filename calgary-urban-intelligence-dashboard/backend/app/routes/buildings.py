from app import db
from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import HTTPException
from app.services.calgary_data_fetcher import CalgaryDataFetcher
from app.services.building_processor import BuildingProcessor
from app.models.building import Building
from app.utils.validation import validate_bounds, validate_filters

from threading import RLock
cache_write_lock = RLock()

buildings_bp = Blueprint('buildings', __name__)

@buildings_bp.route('/area', methods=['GET'])
def get_buildings_in_area():
    """Cache complete source results; deliver every building through stable pages."""
    import json
    from datetime import datetime
    from app.models.building import AreaSnapshot, AreaBuilding
    try:
        bounds = validate_bounds(request.args.get('bounds'))
        offset = int(request.args.get('offset', 0))
        page_size = int(request.args.get('page_size', 500))
        if offset < 0 or not 1 <= page_size <= 2000:
            raise ValueError('Use offset >= 0 and page_size between 1 and 2000.')
        refresh = request.args.get('refresh', 'false').lower() == 'true' and offset == 0
        key = ','.join(str(v) for v in bounds)
        area = db.session.get(AreaSnapshot, key)
        processor = BuildingProcessor()
        fresh = refresh or area is None
        if fresh:
            fetcher = CalgaryDataFetcher()
            raw_data = fetcher.fetch_combined_building_data(
                bounds=bounds, include_osm=current_app.config.get('ENABLE_OSM_ENRICHMENT', False))
            if not raw_data and fetcher.warnings:
                return jsonify({'error': 'Building sources are unavailable. Try again shortly.',
                                'warnings': fetcher.warnings}), 502
            with cache_write_lock:
                area = db.session.get(AreaSnapshot, key, populate_existing=True)
                stored = processor.process_and_store_buildings(raw_data, commit=False)
                if raw_data and not stored:
                    return jsonify({'error': 'Could not store the fetched buildings.'}), 500
                if area is None:
                    area = AreaSnapshot(bounds_key=key)
                    db.session.add(area)
                # Membership changes affect only this area; shared building rows survive.
                area.members.clear()
                db.session.flush()
                area.members = [AreaBuilding(building_id=b.id) for b in stored]
                area.fetched_at = datetime.utcnow()
                area.warnings_json = json.dumps(fetcher.warnings)
                db.session.commit()
        version = area.fetched_at.isoformat()
        if request.args.get('version') and request.args['version'] != version:
            return jsonify({'error': 'Area changed during pagination; restart loading.'}), 409
        query = Building.query.join(AreaBuilding).filter(AreaBuilding.bounds_key == key)
        total = query.count()
        buildings = query.order_by(Building.building_id).offset(offset).limit(page_size).all()
        next_offset = offset + len(buildings)
        return jsonify({
            'success': True, 'buildings': [b.to_dict() for b in buildings],
            'bounds': bounds, 'total_count': total,
            'next_offset': next_offset if next_offset < total else None,
            'cache_status': 'fresh' if fresh else 'cached', 'version': version,
            'fetched_at': version, 'warnings': json.loads(area.warnings_json),
            'coverage_complete': not bool(json.loads(area.warnings_json)),
        })
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Building area request failed')
        return jsonify({'error': 'Could not load this area.'}), 500


@buildings_bp.route('/coverage', methods=['GET'])
def get_coverage():
    """Count live roof records for broad views without sending citywide meshes."""
    import math
    try:
        values = request.args.get('bounds', '').split(',')
        south, west, north, east = (float(v) for v in values)
        if not all(math.isfinite(v) for v in [south, west, north, east]) or not (
                -90 <= south < north <= 90 and -180 <= west < east <= 180):
            raise ValueError('Invalid coverage bounds.')
        fetcher = CalgaryDataFetcher()
        polygon = f'POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))'
        response = fetcher.session.get(f'{fetcher.base_url}/uc4c-6kbd.json', params={
            '$select': 'count(*) AS count', '$where': f"intersects(multipolygon, '{polygon}')"}, timeout=20)
        response.raise_for_status()
        return jsonify({'success': True, 'source_record_count': int(response.json()[0]['count'])})
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid coverage bounds.'}), 400
    except Exception:
        return jsonify({'error': 'Could not count roof records for this view.'}), 502

@buildings_bp.route('/<int:building_id>', methods=['GET'])
def get_building_details(building_id):
    """Get detailed information about a specific building"""
    try:
        building = db.get_or_404(Building, building_id)
        
        return jsonify({
            'success': True,
            'building': building.to_dict()
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/filter', methods=['POST'])
def filter_buildings():
    """Filter buildings based on criteria"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        filter_criteria = validate_filters(data.get('filters'))
        bounds = validate_bounds(data['bounds']) if data.get('bounds') is not None else None
        
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@buildings_bp.route('/refresh', methods=['POST'])
def refresh_building_data():
    """Force refresh of building data from Calgary Open Data API"""
    try:
        data = request.get_json() or {}
        bounds = validate_bounds(data['bounds']) if data.get('bounds') is not None else None
        
        # Initialize services
        fetcher = CalgaryDataFetcher()
        processor = BuildingProcessor()
        
        # Fetch fresh data
        if bounds and len(bounds) == 4:
            raw_data = fetcher.fetch_combined_building_data(bounds=tuple(bounds))
        else:
            raw_data = fetcher.fetch_combined_building_data()
        
        if not raw_data:
            return jsonify({'error': 'Failed to fetch building data from API'}), 500
        
        # Process and store buildings
        buildings = processor.process_and_store_buildings(raw_data)
        
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed {len(buildings)} buildings',
            'buildings_count': len(buildings)
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
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
                bounds = validate_bounds(bounds_str)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 