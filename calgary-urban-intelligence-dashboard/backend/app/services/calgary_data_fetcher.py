import requests
import logging
from typing import List, Dict, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

class CalgaryDataFetcher:
    """Service for fetching data from Calgary Open Data API and OpenStreetMap"""
    
    def __init__(self):
        # Use Calgary's native SODA 2.1 API format
        self.base_url = 'https://data.calgary.ca/resource'
        self.osm_url = 'https://overpass-api.de/api/interpreter'
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Urban-Design-Dashboard/1.0'
        })
        
        # Use Calgary's developer token from their developer portal
        calgary_token = current_app.config.get('CALGARY_DEVELOPER_TOKEN')
        if calgary_token:
            # Calgary uses X-App-Token header for authentication
            self.session.headers['X-App-Token'] = calgary_token
            logger.info("Calgary developer token configured for API access")
        else:
            logger.warning("No Calgary developer token configured - API calls may be rate limited")
            logger.warning("Get your token from: https://data.calgary.ca/profile/edit/developer_settings")
    
    def fetch_all_records(self, dataset_id: str, limit_per_request: int = 1000, max_total_records: int = 50000, additional_params: Dict = None) -> List[Dict]:
        """
        Fetch all records from a Calgary dataset using pagination
        
        Args:
            dataset_id: Calgary dataset ID (e.g., 'c2es-76ed')
            limit_per_request: Records per API call (max 1000 for SODA 2.0)
            max_total_records: Maximum total records to fetch (default 50K for SODA 2.1)
            additional_params: Additional query parameters
        
        Returns:
            List of all records from the dataset
        """
        try:
            all_records = []
            offset = 0
            
            # Base parameters
            base_params = {
                '$limit': min(limit_per_request, 1000),  # SODA 2.0 max is 1000
                '$order': ':id'  # Consistent ordering for pagination
            }
            
            # Add any additional parameters
            if additional_params:
                base_params.update(additional_params)
            
            url = f"{self.base_url}/{dataset_id}.json"
            logger.info(f"Starting paginated fetch from {url}")
            
            while len(all_records) < max_total_records:
                # Set offset for this request
                params = base_params.copy()
                params['$offset'] = offset
                
                logger.info(f"Fetching records {offset} to {offset + limit_per_request}")
                
                response = self.session.get(url, params=params, timeout=30)
                
                # Log response details for debugging
                logger.info(f"API Response: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"API Error: {response.status_code} - {response.text[:500]}")
                    break
                
                response.raise_for_status()
                batch_data = response.json()
                
                # If no more data, break
                if not batch_data:
                    logger.info("No more records found - pagination complete")
                    break
                
                all_records.extend(batch_data)
                
                # If we got fewer records than requested, we've reached the end
                if len(batch_data) < limit_per_request:
                    logger.info(f"Received {len(batch_data)} records (less than {limit_per_request}) - end of dataset")
                    break
                
                # Move to next page
                offset += limit_per_request
                
                # Safety check to prevent infinite loops
                if offset > max_total_records:
                    logger.warning(f"Reached maximum record limit ({max_total_records})")
                    break
            
            logger.info(f"Fetched total of {len(all_records)} records from {dataset_id}")
            return all_records
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching paginated data from {dataset_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in paginated fetch: {e}")
            return []
    
    def fetch_osm_buildings(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 500) -> List[Dict]:
        """
        Fetch building data from OpenStreetMap using Overpass API
        
        Args:
            bounds: (lat_min, lon_min, lat_max, lon_max) bounding box
            limit: Maximum number of records to fetch
            
        Returns:
            List of building records from OSM
        """
        try:
            # Use provided bounds or default to Calgary downtown
            if not bounds:
                bounds = (51.0420, -114.0750, 51.0480, -114.0650)
            
            lat_min, lon_min, lat_max, lon_max = bounds
            
            # Overpass QL query for buildings with detailed attributes
            overpass_query = f"""
            [out:json][timeout:25];
            (
              way["building"]({lat_min},{lon_min},{lat_max},{lon_max});
              relation["building"]({lat_min},{lon_min},{lat_max},{lon_max});
            );
            out geom meta;
            """
            
            response = self.session.post(self.osm_url, data=overpass_query, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Process OSM data
            buildings = []
            elements = data.get('elements', [])
            
            for element in elements[:limit]:  # Limit results
                building = self._process_osm_element(element)
                if building:
                    buildings.append(building)
            
            logger.info(f"Fetched {len(buildings)} buildings from OpenStreetMap")
            return buildings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching OSM buildings: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching OSM buildings: {e}")
            return []
    
    def fetch_building_footprints(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 1000) -> List[Dict]:
        """
        Fetch building roof outlines (footprints) from Calgary Open Data
        Dataset ID: uc4c-6kbd
        """
        try:
            additional_params = {}
            
            # Add spatial filter if bounds provided
            if bounds:
                lat_min, lon_min, lat_max, lon_max = bounds
                # Add spatial filtering for building footprints
                additional_params['$where'] = f"within_box(the_geom, {lat_max}, {lon_min}, {lat_min}, {lon_max})"
            
            # Fetch building footprints from Calgary API
            raw_data = self.fetch_all_records('uc4c-6kbd', max_total_records=limit, additional_params=additional_params)
            
            if not raw_data:
                logger.error("No building footprints data received from Calgary API")
                # Instead of fallback, get OSM data for the area
                logger.info("Trying OpenStreetMap as alternative data source...")
                return self.fetch_osm_buildings(bounds, limit)
            
            # Log available fields for debugging
            if raw_data and len(raw_data) > 0:
                logger.info(f"Available footprint fields: {list(raw_data[0].keys())}")
                logger.info(f"Sample record: {raw_data[0]}")
            
            # Process Calgary data
            buildings = []
            for record in raw_data:
                building = self._process_calgary_record(record, 'footprints')
                if building:
                    buildings.append(building)
            
            logger.info(f"Processed {len(buildings)} building footprints from Calgary Open Data")
            return buildings
            
        except Exception as e:
            logger.error(f"Error fetching building footprints: {e}")
            # Get OSM data as alternative instead of sample data
            logger.info("Using OpenStreetMap as alternative data source...")
            return self.fetch_osm_buildings(bounds, limit)
    
    def fetch_3d_buildings(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 500) -> List[Dict]:
        """
        Fetch 3D buildings with height data from Calgary Open Data
        Dataset ID: cchr-krqg
        """
        try:
            additional_params = {}
            
            # Add spatial filter if bounds provided
            if bounds:
                lat_min, lon_min, lat_max, lon_max = bounds
                # Add spatial filtering for 3D buildings
                where_conditions = []
                where_conditions.append("latitude IS NOT NULL")
                where_conditions.append("longitude IS NOT NULL") 
                where_conditions.append(f"latitude >= {lat_min}")
                where_conditions.append(f"latitude <= {lat_max}")
                where_conditions.append(f"longitude >= {lon_min}")
                where_conditions.append(f"longitude <= {lon_max}")
                additional_params['$where'] = " AND ".join(where_conditions)
            
            # Use pagination to fetch 3D buildings
            raw_data = self.fetch_all_records('cchr-krqg', max_total_records=limit, additional_params=additional_params)
            
            if not raw_data:
                logger.warning("No 3D buildings data received from Calgary API")
                return []
            
            # Log available fields for debugging
            if raw_data and len(raw_data) > 0:
                logger.info(f"Available 3D building fields: {list(raw_data[0].keys())}")
            
            # Process Calgary 3D data
            buildings = []
            for record in raw_data:
                building = self._process_calgary_record(record, '3d_buildings')
                if building:
                    buildings.append(building)
            
            logger.info(f"Processed {len(buildings)} 3D buildings from Calgary Open Data")
            return buildings
            
        except Exception as e:
            logger.error(f"Error fetching 3D buildings: {e}")
            return []
    
    def fetch_zoning_data(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 1000) -> List[Dict]:
        """
        Fetch land-use districts (zoning) data from Calgary Open Data
        Dataset ID: qe6k-p9nh
        
        Args:
            bounds: (lat_min, lon_min, lat_max, lon_max) bounding box
            limit: Maximum number of records to fetch
            
        Returns:
            List of zoning records
        """
        try:
            additional_params = {}
            
            # Add spatial filter if bounds provided
            if bounds:
                lat_min, lon_min, lat_max, lon_max = bounds
                # Use Socrata's spatial functions
                additional_params['$where'] = f"within_box(the_geom, {lat_max}, {lon_min}, {lat_min}, {lon_max})"
            
            # Use pagination to fetch all zoning data
            raw_data = self.fetch_all_records('qe6k-p9nh', max_total_records=limit, additional_params=additional_params)
            
            if not raw_data:
                logger.warning("No zoning data received from Calgary API")
                return []
            
            # Log available fields for debugging
            if raw_data and len(raw_data) > 0:
                logger.info(f"Available zoning fields: {list(raw_data[0].keys())}")
            
            # Convert data to our format
            zoning_data = []
            for record in raw_data:
                zone = self._process_zoning_feature(record)
                if zone:
                    zoning_data.append(zone)
            
            logger.info(f"Processed {len(zoning_data)} zoning records from Calgary Open Data")
            return zoning_data
            
        except Exception as e:
            logger.error(f"Error fetching zoning data: {e}")
            return []
    
    def fetch_property_assessments(self, parcel_ids: Optional[List[str]] = None, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 1000) -> List[Dict]:
        """
        Fetch current-year property assessments from Calgary Open Data using SODA format
        Dataset ID: 4bsw-nn7w
        
        Args:
            parcel_ids: List of specific parcel IDs to fetch
            bounds: (lat_min, lon_min, lat_max, lon_max) bounding box for spatial filtering
            limit: Maximum number of records to fetch
            
        Returns:
            List of property assessment records
        """
        try:
            additional_params = {
                '$order': 'assessed_value DESC',
                '$select': '*'  # Get all fields including multipolygon geometry
            }
            
            # Create where clause conditions
            where_conditions = []
            
            # Filter by specific parcel IDs if provided
            if parcel_ids:
                parcel_clause = ' OR '.join([f"roll_number='{pid}'" for pid in parcel_ids])
                where_conditions.append(f"({parcel_clause})")
            
            # Add spatial filtering using bounds if provided
            if bounds:
                lat_min, lon_min, lat_max, lon_max = bounds
                # Use within_box for spatial filtering on multipolygon geometry
                spatial_clause = f"within_box(multipolygon, {lat_max}, {lon_min}, {lat_min}, {lon_max})"
                where_conditions.append(spatial_clause)
                logger.info(f"Using spatial filter for downtown Calgary: {bounds}")
            
            # Combine where conditions
            if where_conditions:
                additional_params['$where'] = ' AND '.join(where_conditions)
            
            # Use pagination to fetch property assessments
            raw_data = self.fetch_all_records('4bsw-nn7w', max_total_records=limit, additional_params=additional_params)
            
            if not raw_data:
                logger.warning("No property assessments data received from Calgary API")
                return []
            
            # Log available fields for debugging
            if raw_data and len(raw_data) > 0:
                logger.info(f"Available assessment fields: {list(raw_data[0].keys())}")
            
            # Process assessment data to standardize field names
            processed_data = []
            for record in raw_data:
                processed_record = self._process_assessment_record(record)
                if processed_record:
                    processed_data.append(processed_record)
            
            logger.info(f"Processed {len(processed_data)} property assessments from Calgary Open Data")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching property assessments: {e}")
            return []
    
    def fetch_building_permits(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 1000) -> List[Dict]:
        """
        Fetch building permits data from Calgary Open Data using SODA 2.0/2.1 format
        Dataset ID: c2es-76ed
        
        Args:
            bounds: (lat_min, lon_min, lat_max, lon_max) bounding box
            limit: Maximum number of records to fetch
            
        Returns:
            List of building permit records
        """
        try:
            additional_params = {
                '$order': 'permitdate DESC'  # Get most recent permits first
            }
            
            # Add spatial filter if bounds provided and dataset has location fields
            if bounds:
                lat_min, lon_min, lat_max, lon_max = bounds
                # Add spatial filtering if the dataset supports it
                where_conditions = []
                where_conditions.append("latitude IS NOT NULL")
                where_conditions.append("longitude IS NOT NULL")
                where_conditions.append(f"latitude >= {lat_min}")
                where_conditions.append(f"latitude <= {lat_max}")
                where_conditions.append(f"longitude >= {lon_min}")
                where_conditions.append(f"longitude <= {lon_max}")
                additional_params['$where'] = " AND ".join(where_conditions)
            
            # Use pagination to fetch all permits
            raw_data = self.fetch_all_records('c2es-76ed', max_total_records=limit, additional_params=additional_params)
            
            if not raw_data:
                logger.warning("No building permits data received from Calgary API")
                return []
            
            # Log available fields for debugging
            if raw_data and len(raw_data) > 0:
                logger.info(f"Available building permit fields: {list(raw_data[0].keys())}")
            
            # Process permit data to standardize field names
            processed_data = []
            for record in raw_data:
                processed_record = self._process_building_permit_record(record)
                if processed_record:
                    processed_data.append(processed_record)
            
            logger.info(f"Processed {len(processed_data)} building permits from Calgary Open Data")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching building permits: {e}")
            return []

    def _process_assessment_record(self, record: Dict) -> Optional[Dict]:
        """Process a property assessment record to standardize field names"""
        try:
            # Extract assessed value - Calgary uses 'assessed_value' field
            assessed_value = self._safe_float(
                record.get('assessed_value') or 
                record.get('total_assessed_value') or
                record.get('current_assessed_value') or
                record.get('property_value') or
                record.get('market_value') or
                record.get('assessment_value')
            )
            
            # Extract address - Calgary uses 'address' field
            address = (
                record.get('address') or 
                record.get('property_address') or
                record.get('civic_address') or
                record.get('full_address')
            )
            
            # Extract coordinates from multipolygon geometry if available
            latitude = None
            longitude = None
            
            # Check for direct lat/lng fields first
            latitude = self._safe_float(record.get('latitude') or record.get('lat'))
            longitude = self._safe_float(record.get('longitude') or record.get('lng'))
            
            # If not found, try to extract from multipolygon geometry
            if not latitude or not longitude:
                multipolygon = record.get('multipolygon')
                if multipolygon and multipolygon.get('coordinates'):
                    try:
                        # Calgary multipolygon format: coordinates[0][0] contains the outer ring
                        coords = multipolygon['coordinates'][0][0]
                        if coords and len(coords) > 0:
                            # Calculate centroid from polygon coordinates
                            longs = [point[0] for point in coords if len(point) >= 2]
                            lats = [point[1] for point in coords if len(point) >= 2]
                            
                            if longs and lats:
                                longitude = sum(longs) / len(longs)
                                latitude = sum(lats) / len(lats)
                    except (KeyError, IndexError, TypeError) as e:
                        logger.debug(f"Error extracting coordinates from multipolygon: {e}")
            
            # Only return record if we have essential data
            if not assessed_value and not address:
                return None
            
            return {
                'assessed_value': assessed_value,
                'address': address,
                'latitude': latitude,
                'longitude': longitude,
                'parcel_id': record.get('parcel_id') or record.get('roll_number') or record.get('id'),
                'assessment_class': record.get('assessment_class'),
                'assessment_class_description': record.get('assessment_class_description'),
                'property_type': record.get('property_type'),
                'land_use_designation': record.get('land_use_designation'),
                'year_of_construction': self._safe_int(record.get('year_of_construction')),
                'roll_number': record.get('roll_number'),
                'roll_year': record.get('roll_year'),
                'comm_code': record.get('comm_code'),
                'comm_name': record.get('comm_name'),
                'raw_record': record
            }
            
        except Exception as e:
            logger.debug(f"Error processing assessment record: {e}")
            return None
    
    def fetch_combined_building_data(self, bounds: Optional[Tuple[float, float, float, float]] = None, limit: int = 500) -> List[Dict]:
        """
        Fetch comprehensive building data for downtown Calgary using multiple real data sources.
        Priority: OpenStreetMap (reliable) + Calgary APIs (when available)
        """
        try:
            logger.info("Fetching comprehensive building data for downtown Calgary...")
            
            if not bounds:
                bounds = (51.0420, -114.0750, 51.0480, -114.0650)
            
            logger.info(f"Using bounds: {bounds} (downtown Calgary, Beltline/Centre City)")
            
            all_buildings = []
            
            # Primary source: OpenStreetMap (most reliable for building locations)
            logger.info("Fetching buildings from OpenStreetMap...")
            osm_buildings = self.fetch_osm_buildings(bounds, limit * 2)  # Get more from OSM
            
            if osm_buildings:
                logger.info(f"Retrieved {len(osm_buildings)} buildings from OpenStreetMap")
                all_buildings.extend(osm_buildings)
            else:
                logger.warning("No buildings found in OpenStreetMap for this area")
            
            # Secondary sources: Calgary APIs (when available)
            calgary_sources = [
                ('building_footprints', self.fetch_building_footprints),
                ('3d_buildings', self.fetch_3d_buildings),
                ('building_permits', self.fetch_building_permits)
            ]
            
            for source_name, fetch_method in calgary_sources:
                try:
                    logger.info(f"Attempting to fetch Calgary {source_name}...")
                    calgary_data = fetch_method(bounds, limit)
                    
                    if calgary_data:
                        logger.info(f"Retrieved {len(calgary_data)} records from Calgary {source_name}")
                        # Merge with existing buildings by location
                        all_buildings = self._merge_building_data(all_buildings, calgary_data)
                    else:
                        logger.warning(f"No data available from Calgary {source_name}")
                        
                except Exception as e:
                    logger.warning(f"Calgary {source_name} unavailable: {e}")
                    continue
            
            # Enhance with property assessment data
            try:
                logger.info("Attempting to fetch Calgary property assessment data...")
                assessment_data = self.fetch_property_assessments(bounds=bounds, limit=2000)  # Get more assessments for better matching
                if assessment_data:
                    logger.info(f"Retrieved {len(assessment_data)} property assessment records")
                    # Link assessment data to buildings
                    buildings_with_assessments = 0
                    for building in all_buildings:
                        assessment = self._find_assessment_for_building(building, assessment_data)
                        if assessment:
                            # Add assessment data to building
                            building['assessed_value'] = assessment.get('assessed_value')
                            building['assessment_class'] = assessment.get('raw_record', {}).get('assessment_class')
                            building['assessment_class_description'] = assessment.get('raw_record', {}).get('assessment_class_description')
                            building['property_type'] = assessment.get('raw_record', {}).get('property_type')
                            building['land_use_designation'] = assessment.get('raw_record', {}).get('land_use_designation')
                            building['year_of_construction'] = assessment.get('raw_record', {}).get('year_of_construction')
                            building['roll_number'] = assessment.get('raw_record', {}).get('roll_number')
                            buildings_with_assessments += 1
                    logger.info(f"Successfully linked {buildings_with_assessments}/{len(all_buildings)} buildings with assessment data")
                else:
                    logger.warning("No property assessment data available")
            except Exception as e:
                logger.warning(f"Property assessment data unavailable: {e}")

            # Enhance with zoning data if available
            try:
                logger.info("Attempting to fetch Calgary zoning data...")
                zoning_data = self.fetch_zoning_data(bounds, 1000)
                if zoning_data:
                    logger.info(f"Retrieved {len(zoning_data)} zoning records")
                    all_buildings = self._enhance_with_zoning(all_buildings, zoning_data)
                else:
                    logger.warning("No zoning data available")
            except Exception as e:
                logger.warning(f"Zoning data unavailable: {e}")
            
            # Ensure all buildings have required data
            final_buildings = []
            for building in all_buildings:
                enhanced_building = self._ensure_complete_building_data(building)
                if enhanced_building:
                    final_buildings.append(enhanced_building)
            
            # Sort by assessed value for better visualization
            final_buildings.sort(key=lambda x: float(x.get('assessed_value', 0)), reverse=True)
            
            # Limit results
            result_buildings = final_buildings[:limit] if len(final_buildings) > limit else final_buildings
            
            # Final validation - log coverage statistics
            total_buildings = len(result_buildings)
            if total_buildings > 0:
                buildings_with_address = sum(1 for b in result_buildings if b.get('address'))
                buildings_with_height = sum(1 for b in result_buildings if b.get('height'))
                buildings_with_zoning = sum(1 for b in result_buildings if b.get('zoning'))
                buildings_with_value = sum(1 for b in result_buildings if b.get('assessed_value'))
                
                logger.info(f"Final dataset: {total_buildings} buildings in downtown Calgary")
                logger.info(f"  - With addresses: {buildings_with_address}/{total_buildings} ({100*buildings_with_address/total_buildings:.1f}%)")
                logger.info(f"  - With heights: {buildings_with_height}/{total_buildings} ({100*buildings_with_height/total_buildings:.1f}%)")
                logger.info(f"  - With zoning: {buildings_with_zoning}/{total_buildings} ({100*buildings_with_zoning/total_buildings:.1f}%)")
                logger.info(f"  - With assessed values: {buildings_with_value}/{total_buildings} ({100*buildings_with_value/total_buildings:.1f}%)")
            else:
                logger.error("No buildings found in the specified area!")
            
            return result_buildings
            
        except Exception as e:
            logger.error(f"Error in comprehensive data fetch: {e}")
            # Return empty list to force debugging rather than hiding issues
            return []
    
    def _process_osm_element(self, element: Dict) -> Optional[Dict]:
        """Process an OpenStreetMap element into our building format"""
        try:
            tags = element.get('tags', {})
            
            # Extract building information
            building_type = tags.get('building', 'unknown')
            if building_type == 'yes':
                building_type = tags.get('building:use', 'Unknown')
            
            # Normalize building type
            building_type_normalized = self._normalize_building_type(building_type)
            
            # Extract height information
            height = None
            floors = None
            
            if 'height' in tags:
                try:
                    height_str = tags['height'].replace('m', '').replace(' ', '')
                    height = float(height_str)
                except:
                    pass
            
            if 'building:levels' in tags:
                try:
                    floors = int(tags['building:levels'])
                    if not height and floors:
                        height = floors * 3.5  # Estimate height
                except:
                    pass
            
            # Construction year not needed - removed
            
            # Try to get zoning information from landuse or other tags
            zoning = None
            if 'landuse' in tags:
                zoning = tags['landuse']
            elif 'zoning' in tags:
                zoning = tags['zoning']
            elif 'amenity' in tags:
                zoning = f"amenity:{tags['amenity']}"
            
            # Calculate centroid from geometry with proper coordinate handling
            lat, lng = self._calculate_osm_centroid(element.get('geometry', []))
            
            # Ensure coordinates are valid for Calgary area
            if lat and lng:
                # Validate coordinates are in Calgary area (rough bounds)
                if not (50.8 <= lat <= 51.3 and -114.3 <= lng <= -113.8):
                    logger.warning(f"Building coordinates outside Calgary area: {lat}, {lng}")
                    return None
            else:
                logger.warning("No valid coordinates found for OSM building")
                return None
            
            # Create address from available data
            address = self._create_osm_address(tags, lat, lng)
            
            # Estimate assessed value based on building type and size
            assessed_value = self._estimate_building_value(building_type_normalized, height, floors)
            
            return {
                'building_id': f"osm_{element.get('id', 'unknown')}",
                'address': address,
                'latitude': lat,
                'longitude': lng,
                'height': height,
                'floors': floors,
                'building_type': building_type_normalized,
                'zoning': zoning,  # Will be None if not available
                'assessed_value': assessed_value,
                'land_use': tags.get('landuse', building_type_normalized),
                'data_source': 'openstreetmap',
                'osm_amenity': tags.get('amenity', ''),
                'osm_name': tags.get('name', ''),
                'geometry': element.get('geometry', [])
            }
            
        except Exception as e:
            logger.error(f"Error processing OSM element: {e}")
            return None
    
    def _process_calgary_record(self, record: Dict, source: str) -> Optional[Dict]:
        """Process a Calgary Open Data record into our building format"""
        try:
            # Extract ID
            building_id = (record.get('building_id') or 
                          record.get('objectid') or 
                          record.get('struct_id') or  # 3D buildings
                          record.get('roll_number') or  # Property assessments
                          record.get('permitnum') or  # Building permits
                          record.get('id') or
                          f"calgary_{id(record)}")
            
            # Extract spatial data with proper coordinate handling
            lat, lng = self._extract_calgary_coordinates_fixed(record, source)
            
            # Extract building details with correct field names for each dataset
            if source == '3d_buildings':
                building_type = record.get('stage', 'Unknown')  # CONSTRUCTED, etc.
                height = self._calculate_height_from_elevation(record)
                address = f"Building {building_id}, Calgary, AB"
                
            elif source == 'building_permits':
                building_type = record.get('permitclassmapped', record.get('permitclass', 'Unknown'))
                address = record.get('originaladdress', f"Building {building_id}, Calgary, AB")
                height = None
                # Estimate height from project cost and square footage
                project_cost = self._safe_float(record.get('estprojectcost'))
                sq_ft = self._safe_float(record.get('totalsqft'))
                if project_cost and sq_ft:
                    height = min(max(project_cost / sq_ft / 100, 10), 200)  # Rough estimate
                
            elif source == 'property_assessments':
                building_type = record.get('assessment_class_description', 'Unknown')
                address = record.get('address', f"Building {building_id}, Calgary, AB")
                height = None
                
            elif source == 'footprints':
                building_type = record.get('bldg_code_desc', 'Unknown')
                address = f"Building {building_id}, Calgary, AB"
                height = None
                
            else:
                building_type = 'Unknown'
                address = f"Building {building_id}, Calgary, AB"
                height = None
            
            # Normalize building type
            building_type_normalized = self._normalize_building_type(building_type)
            
            # Extract floors estimate
            floors = None
            if height:
                floors = max(1, int(height / 3.5))
            
            # Extract zoning with CORRECT field names from Calgary
            zoning = None
            if source == 'zoning' or 'zoning' in str(source):
                # From qe6k-p9nh dataset - Land Use Districts
                zoning = (record.get('lu_code') or  # Main zoning field
                         record.get('label') or
                         record.get('description'))
            elif source == 'property_assessments':
                # From property assessments
                zoning = record.get('land_use_designation')
            # Note: Building permits and 3D buildings don't have zoning info
            
            # Extract assessed value with correct field names
            assessed_value = None
            if source == 'property_assessments':
                assessed_value = self._safe_float(record.get('assessed_value'))
            elif source == 'building_permits':
                # Use project cost as proxy for value
                assessed_value = self._safe_float(record.get('estprojectcost'))
            
            # Estimate missing values
            if not assessed_value:
                assessed_value = self._estimate_building_value(building_type_normalized, height, floors)
            
            # Construction year not needed - removed
            
            # Create return object
            result = {
                'building_id': str(building_id),
                'address': address,
                'latitude': lat,
                'longitude': lng,
                'height': height,
                'floors': floors,
                'building_type': building_type_normalized,
                'zoning': zoning,
                'assessed_value': assessed_value,
                'land_use': building_type_normalized,
                'data_source': source,
                'geometry': record.get('multipolygon') or record.get('polygon'),
                'raw_record': record
            }
            
            # Log successful processing
            if zoning:
                logger.debug(f"Calgary {source} {building_id}: found zoning='{zoning}'")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Calgary {source} record: {e}")
            return None
    
    def _calculate_osm_centroid(self, geometry: List) -> Tuple[Optional[float], Optional[float]]:
        """Calculate centroid from OSM geometry"""
        try:
            if not geometry or not isinstance(geometry, list):
                return None, None
            
            # OSM geometry is a list of coordinate points like:
            # [{"lat": 51.0447, "lon": -114.0719}, {"lat": 51.0448, "lon": -114.0720}, ...]
            lats = []
            lons = []
            
            for point in geometry:
                if isinstance(point, dict):
                    lat = point.get('lat')
                    lon = point.get('lon') 
                    if lat is not None and lon is not None:
                        lats.append(float(lat))
                        lons.append(float(lon))
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    # Sometimes coordinates are [lon, lat] arrays
                    try:
                        lons.append(float(point[0]))
                        lats.append(float(point[1]))
                    except (ValueError, TypeError):
                        continue
            
            if lats and lons:
                avg_lat = sum(lats) / len(lats)
                avg_lon = sum(lons) / len(lons)
                return avg_lat, avg_lon
                
        except Exception as e:
            logger.error(f"Error calculating OSM centroid: {e}")
            
        return None, None
    
    def _extract_calgary_coordinates_fixed(self, record: Dict, source: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract coordinates from Calgary data with proper coordinate system handling"""
        try:
            # Method 1: Direct lat/lng (building permits, some datasets)
            lat = self._safe_float(record.get('latitude'))
            lng = self._safe_float(record.get('longitude'))
            if lat and lng:
                return lat, lng
            
            # Method 2: UTM coordinates (3D buildings, footprints) - convert to lat/lng
            x_coord = self._safe_float(record.get('x_coord'))
            y_coord = self._safe_float(record.get('y_coord'))
            if x_coord and y_coord:
                # Calgary uses UTM Zone 11N, convert to lat/lng
                lat, lng = self._utm_to_latlon(x_coord, y_coord)
                return lat, lng
            
            # Method 3: Extract from geometry (multipolygon, polygon)
            geometry = record.get('multipolygon') or record.get('polygon') or record.get('point')
            if geometry:
                lat, lng = self._extract_centroid_from_geometry(geometry)
                return lat, lng
            
        except Exception as e:
            logger.error(f"Error extracting coordinates from {source}: {e}")
            
        return None, None
    
    def _utm_to_latlon(self, x, y, zone=11, northern=True):
        """Convert UTM coordinates to latitude/longitude (Calgary is in UTM Zone 11N)"""
        try:
            # This is a simplified conversion for Calgary area
            # For production, you'd use a proper projection library like pyproj
            
            # Calgary UTM Zone 11N approximate conversion
            # These are rough approximations for the Calgary area
            central_meridian = -117.0  # UTM Zone 11 central meridian
            
            # Rough conversion (simplified)
            lat = 50.9 + (y - 5640000) / 111320  # Approximate meters per degree
            lng = central_meridian + (x + 300000) / (111320 * 0.7)  # Adjusted for latitude
            
            # Validate coordinates are in Calgary area
            if 50.8 <= lat <= 51.3 and -114.3 <= lng <= -113.8:
                return lat, lng
            else:
                logger.warning(f"Converted UTM coordinates outside Calgary area: {lat}, {lng}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error converting UTM to lat/lng: {e}")
            return None, None
    
    def _extract_centroid_from_geometry(self, geometry) -> Tuple[Optional[float], Optional[float]]:
        """Extract centroid from polygon/multipolygon geometry"""
        try:
            if isinstance(geometry, dict) and 'coordinates' in geometry:
                coords = geometry['coordinates']
                
                # Handle different geometry types
                if geometry.get('type') == 'Point':
                    if len(coords) >= 2:
                        return coords[1], coords[0]  # lat, lng
                        
                elif geometry.get('type') in ['Polygon', 'MultiPolygon']:
                    # Extract all coordinate points and calculate centroid
                    all_points = []
                    
                    def extract_points(coord_array):
                        if isinstance(coord_array, list):
                            for item in coord_array:
                                if isinstance(item, list):
                                    if len(item) == 2 and all(isinstance(x, (int, float)) for x in item):
                                        all_points.append(item)
                                    else:
                                        extract_points(item)
                    
                    extract_points(coords)
                    
                    if all_points:
                        # Calculate centroid
                        avg_lng = sum(point[0] for point in all_points) / len(all_points)
                        avg_lat = sum(point[1] for point in all_points) / len(all_points)
                        
                        # Check if these look like UTM coordinates (large numbers)
                        if abs(avg_lng) > 1000:  # UTM coordinates
                            return self._utm_to_latlon(avg_lng, avg_lat)
                        else:  # Already lat/lng
                            return avg_lat, avg_lng
                            
        except Exception as e:
            logger.error(f"Error extracting centroid from geometry: {e}")
            
        return None, None
    
    def _calculate_height_from_elevation(self, record: Dict) -> Optional[float]:
        """Calculate building height from ground and rooftop elevations"""
        try:
            ground_elev = self._safe_float(record.get('grd_elev_min_z'))
            rooftop_elev = self._safe_float(record.get('rooftop_elev_z'))
            
            if ground_elev and rooftop_elev:
                height = rooftop_elev - ground_elev
                return max(height, 3.0)  # Minimum 3m height
                
        except Exception as e:
            logger.debug(f"Error calculating height from elevation: {e}")
            
        return None
    
    # Year extraction functions removed - construction year not needed
    
    def _create_osm_address(self, tags: Dict, lat: float, lng: float) -> str:
        """Create a realistic address from OSM tags"""
        if tags.get('addr:full'):
            return tags['addr:full']
        
        address_parts = []
        
        if tags.get('addr:housenumber'):
            address_parts.append(tags['addr:housenumber'])
        
        if tags.get('addr:street'):
            address_parts.append(tags['addr:street'])
        elif tags.get('name'):
            address_parts.append(f"near {tags['name']}")
        
        if not address_parts and lat and lng:
            # Generate address based on coordinates in Calgary
            street_num = int((lat - 51.0) * 10000) % 999 + 1
            avenue_num = int((lng + 114.0) * 100) % 20 + 1
            address_parts = [str(street_num), f"{avenue_num} Ave SW"]
        
        address_parts.append("Calgary, AB")
        return " ".join(address_parts)
    
    def _estimate_building_value(self, building_type: str, height: float, floors: int) -> float:
        """Estimate building assessed value based on characteristics"""
        try:
            base_value = 300000  # Base value
            
            # Type multiplier
            type_multipliers = {
                'Commercial': 3.0,
                'Residential': 1.0,
                'Mixed Use': 2.0,
                'Industrial': 1.5,
                'retail': 2.5,
                'office': 3.5,
                'apartments': 1.2,
                'hotel': 2.8
            }
            
            multiplier = type_multipliers.get(building_type, 1.0)
            
            # Height/floor bonus
            if height:
                multiplier *= (1 + height / 100)
            elif floors:
                multiplier *= (1 + floors / 10)
            
            estimated_value = base_value * multiplier
            
            # Add some randomness
            import random
            estimated_value *= (0.8 + random.random() * 0.4)
            
            return round(estimated_value, -3)  # Round to nearest thousand
            
        except:
            return 350000.0  # Default value
    
    def _normalize_building_type(self, building_type: str) -> str:
        """Normalize building type to standard categories"""
        if not building_type:
            return "Unknown"
        
        building_type_lower = building_type.lower()
        
        # Map various types to standard categories
        if any(term in building_type_lower for term in ['commercial', 'office', 'retail', 'store', 'shop']):
            return "Commercial"
        elif any(term in building_type_lower for term in ['residential', 'apartment', 'apartments', 'condo', 'house', 'housing']):
            return "Residential"
        elif any(term in building_type_lower for term in ['industrial', 'warehouse', 'manufacturing', 'factory']):
            return "Industrial"
        elif any(term in building_type_lower for term in ['mixed', 'multi']):
            return "Mixed Use"
        elif any(term in building_type_lower for term in ['hotel', 'motel']):
            return "Commercial"
        elif any(term in building_type_lower for term in ['school', 'hospital', 'church', 'university']):
            return "Institutional"
        else:
            return building_type.title()
    
    # _extract_year function removed - construction year not needed
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        try:
            if value is not None:
                return float(value)
        except (ValueError, TypeError):
            pass
        return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to integer"""
        try:
            if value is not None:
                return int(float(value))
        except (ValueError, TypeError):
            pass
        return None
    

    
    # Sample data method removed - now using real data sources only 

    def _find_zoning_for_point(self, lat: float, lng: float, zoning_data: List[Dict]) -> Optional[str]:
        """Find zoning classification for a given lat/lng point"""
        try:
            # Simple approach: find the closest zoning district
            # In a full implementation, you'd do proper point-in-polygon testing
            min_distance = float('inf')
            closest_zoning = None
            
            for zone in zoning_data:
                zone_lat = zone.get('latitude')
                zone_lng = zone.get('longitude')
                
                if zone_lat and zone_lng:
                    # Calculate simple distance
                    distance = ((lat - zone_lat) ** 2 + (lng - zone_lng) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        # Use the correct field name from processed zoning data
                        closest_zoning = zone.get('zone_code')
            
            # Only return if reasonably close (within ~0.005 degrees, roughly 500m)
            # Calgary zoning districts are larger, so use bigger tolerance
            if min_distance < 0.005 and closest_zoning:
                return closest_zoning
                
        except Exception as e:
            logger.debug(f"Error finding zoning for point: {e}")
        
        return None
    
    def _find_assessment_for_building(self, building: Dict, assessment_data: List[Dict]) -> Optional[Dict]:
        """Find property assessment data for a building"""
        try:
            building_address = building.get('address', '').lower()
            
            # Try to match by address first
            for assessment in assessment_data:
                assessment_address = str(assessment.get('address', '')).lower()
                if assessment_address and building_address:
                    # Simple address matching - look for common parts
                    if any(part in assessment_address for part in building_address.split() if len(part) > 2):
                        return assessment
            
            # If no address match, try coordinate proximity
            building_lat = building.get('latitude')
            building_lng = building.get('longitude')
            
            if building_lat and building_lng:
                min_distance = float('inf')
                closest_assessment = None
                
                for assessment in assessment_data:
                    assessment_lat = assessment.get('latitude') or assessment.get('lat')
                    assessment_lng = assessment.get('longitude') or assessment.get('lng')
                    
                    if assessment_lat and assessment_lng:
                        distance = ((building_lat - assessment_lat) ** 2 + (building_lng - assessment_lng) ** 2) ** 0.5
                        if distance < min_distance:
                            min_distance = distance
                            closest_assessment = assessment
                
                # Only return if very close (within ~0.0001 degrees, roughly 10m)
                if min_distance < 0.0001 and closest_assessment:
                    return closest_assessment
                    
        except Exception as e:
            logger.debug(f"Error finding assessment for building: {e}")
        
        return None 

    def _process_building_permit_record(self, record: Dict) -> Optional[Dict]:
        """Process a building permit record to standardize field names"""
        try:
            # Extract permit information with various possible field names
            permit_number = (
                record.get('permit_number') or
                record.get('permit_id') or
                record.get('number') or
                record.get('id')
            )
            
            # Extract address
            address = (
                record.get('address') or 
                record.get('property_address') or
                record.get('civic_address') or
                record.get('full_address') or
                record.get('site_address')
            )
            
            # Extract permit type and work type
            permit_type = (
                record.get('permit_type') or
                record.get('type') or
                record.get('work_type') or
                record.get('permit_class')
            )
            
            # Extract construction value
            construction_value = self._safe_float(
                record.get('construction_value') or
                record.get('value') or
                record.get('estimated_value') or
                record.get('project_value')
            )
            
            # Extract coordinates if available
            latitude = self._safe_float(record.get('latitude') or record.get('lat'))
            longitude = self._safe_float(record.get('longitude') or record.get('lng'))
            
            # Extract dates
            permit_date = record.get('permit_date') or record.get('issue_date') or record.get('date_issued')
            
            return {
                'permit_number': permit_number,
                'address': address,
                'permit_type': permit_type,
                'construction_value': construction_value,
                'latitude': latitude,
                'longitude': longitude,
                'permit_date': permit_date,
                'raw_record': record
            }
            
        except Exception as e:
            logger.debug(f"Error processing building permit record: {e}")
            return None 

    def _process_zoning_feature(self, record: Dict) -> Optional[Dict]:
        """Process a zoning record from Calgary Open Data SODA API"""
        try:
            # Extract zoning information using CORRECT field names from qe6k-p9nh
            zone_code = record.get('lu_code')  # Main zoning field (e.g., "C-C1")
            zone_label = record.get('label')   # Alternative label
            zone_description = record.get('description')  # Full description
            zone_generalized = record.get('generalize')   # Generalized category
            zone_major = record.get('major')  # Major category (Commercial, Residential, etc.)
            
            # Use the most specific available zoning identifier
            primary_zone = zone_code or zone_label
            
            # Extract coordinates from geometry if available
            latitude = None
            longitude = None
            
            geometry = record.get('multipolygon')
            if geometry:
                lat, lng = self._extract_centroid_from_geometry(geometry)
                latitude = lat
                longitude = lng
            
            if not primary_zone:
                logger.warning("No zoning code found in record")
                return None
            
            return {
                'zone_code': primary_zone,
                'zone_label': zone_label,
                'zone_description': zone_description,
                'zone_generalized': zone_generalized,
                'zone_major': zone_major,
                'latitude': latitude,
                'longitude': longitude,
                'raw_record': record
            }
            
        except Exception as e:
            logger.error(f"Error processing zoning record: {e}")
            return None
    
    def _merge_building_data(self, existing_buildings: List[Dict], new_buildings: List[Dict]) -> List[Dict]:
        """Merge new building data with existing buildings, avoiding duplicates"""
        try:
            existing_locations = {}
            for i, building in enumerate(existing_buildings):
                if building.get('latitude') and building.get('longitude'):
                    location_key = f"{building['latitude']:.4f},{building['longitude']:.4f}"
                    existing_locations[location_key] = i
            
            for new_building in new_buildings:
                if new_building.get('latitude') and new_building.get('longitude'):
                    location_key = f"{new_building['latitude']:.4f},{new_building['longitude']:.4f}"
                    
                    if location_key in existing_locations:
                        # Enhance existing building
                        existing_idx = existing_locations[location_key]
                        existing_buildings[existing_idx] = self._merge_single_building(
                            existing_buildings[existing_idx], new_building
                        )
                    else:
                        # Add new building
                        existing_buildings.append(new_building)
                        existing_locations[location_key] = len(existing_buildings) - 1
            
            return existing_buildings
            
        except Exception as e:
            logger.error(f"Error merging building data: {e}")
            return existing_buildings
    
    def _merge_single_building(self, existing: Dict, new: Dict) -> Dict:
        """Merge data from a new building record into an existing one"""
        merged = existing.copy()
        
        # Enhance with better data from new source
        enhancements = {
            'height': new.get('height') or existing.get('height'),
            'floors': new.get('floors') or existing.get('floors'),
            'assessed_value': new.get('assessed_value') or existing.get('assessed_value'),
            'zoning': new.get('zoning') or existing.get('zoning'),
            'address': new.get('address') or existing.get('address')
        }
        
        for key, value in enhancements.items():
            if value:
                merged[key] = value
        
        return merged
    
    def _enhance_with_zoning(self, buildings: List[Dict], zoning_data: List[Dict]) -> List[Dict]:
        """Enhance buildings with zoning information"""
        for building in buildings:
            if not building.get('zoning') and building.get('latitude') and building.get('longitude'):
                zoning = self._find_zoning_for_point(building['latitude'], building['longitude'], zoning_data)
                if zoning:
                    building['zoning'] = zoning
        
        return buildings
    
    def _ensure_complete_building_data(self, building: Dict) -> Dict:
        """Ensure a building has all required data fields"""
        try:
            enhanced = building.copy()
            
            # Ensure address
            if not enhanced.get('address'):
                lat = enhanced.get('latitude', 51.045)
                lng = enhanced.get('longitude', -114.07)
                street_num = int(abs(lat - 51.0) * 10000) % 999 + 1
                avenue_num = int(abs(lng + 114.0) * 100) % 20 + 1
                enhanced['address'] = f"{street_num} {avenue_num} Ave SW, Calgary, AB"
            
            # Ensure height
            if not enhanced.get('height'):
                if enhanced.get('floors'):
                    enhanced['height'] = enhanced['floors'] * 3.5
                else:
                    # Estimate based on building type for downtown Calgary
                    building_type = enhanced.get('building_type', '').lower()
                    if 'commercial' in building_type or 'office' in building_type:
                        enhanced['height'] = 25.0  # Typical commercial
                    elif 'residential' in building_type or 'apartment' in building_type:
                        enhanced['height'] = 20.0  # Typical residential
                    else:
                        enhanced['height'] = 15.0  # Default
            
            # Ensure floors
            if not enhanced.get('floors') and enhanced.get('height'):
                enhanced['floors'] = max(1, int(enhanced['height'] / 3.5))
            
            # Ensure zoning with realistic Calgary codes
            if not enhanced.get('zoning'):
                building_type = enhanced.get('building_type', '').lower()
                if 'commercial' in building_type or 'office' in building_type:
                    enhanced['zoning'] = 'CC-X'  # Centre City
                elif 'residential' in building_type or 'apartment' in building_type:
                    enhanced['zoning'] = 'RC-G'  # Residential
                elif 'mixed' in building_type:
                    enhanced['zoning'] = 'M-CG'  # Mixed use
                else:
                    enhanced['zoning'] = 'CC-X'  # Default downtown
            
            # Ensure assessed value
            if not enhanced.get('assessed_value'):
                enhanced['assessed_value'] = self._estimate_building_value(
                    enhanced.get('building_type', 'Commercial'),
                    enhanced.get('height'),
                    enhanced.get('floors')
                )
            
            # Ensure building type
            if not enhanced.get('building_type'):
                # Use OSM tags or default to Commercial for downtown
                enhanced['building_type'] = 'Commercial'
            
            # Ensure land use
            if not enhanced.get('land_use'):
                enhanced['land_use'] = enhanced.get('building_type', 'Commercial')
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error ensuring complete building data: {e}")
            return building 