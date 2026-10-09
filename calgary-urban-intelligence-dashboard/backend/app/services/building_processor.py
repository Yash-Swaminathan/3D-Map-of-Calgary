import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app import db
from app.models.building import Building

logger = logging.getLogger(__name__)

class BuildingProcessor:
    """Service for processing and storing building data"""
    
    def __init__(self):
        pass
    
    def process_and_store_buildings(self, raw_data: List[Dict]) -> List[Building]:
        """
        Process raw building data and store in database
        
        Args:
            raw_data: Raw building data from Calgary Open Data API
            
        Returns:
            List of processed Building objects
        """
        processed_buildings = []
        
        for building_data in raw_data:
            try:
                building = self._process_single_building(building_data)
                if building:
                    processed_buildings.append(building)
            except Exception as e:
                logger.error(f"Error processing building {building_data.get('building_id', 'unknown')}: {e}")
                continue
        
        # Bulk commit to database
        try:
            db.session.add_all(processed_buildings)
            db.session.commit()
            logger.info(f"Successfully stored {len(processed_buildings)} buildings in database")
        except Exception as e:
            logger.error(f"Error committing buildings to database: {e}")
            db.session.rollback()
            return []
        
        return processed_buildings
    
    def _process_single_building(self, data: Dict) -> Optional[Building]:
        """
        Process a single building record
        
        Args:
            data: Raw building data dictionary
            
        Returns:
            Processed Building object or None if processing failed
        """
        try:
            # Extract building ID
            building_id = data.get('building_id') or data.get('id') or str(data.get('objectid', ''))
            
            # Skip if no valid ID
            if not building_id:
                return None
            
            # Check if building already exists
            existing_building = Building.query.filter_by(building_id=building_id).first()
            if existing_building:
                # Update existing building with new data
                self._update_building_from_data(existing_building, data)
                return existing_building
            
            # Create new building
            building = Building()
            building.building_id = building_id
            
            self._update_building_from_data(building, data)
            
            return building
            
        except Exception as e:
            logger.error(f"Error processing building data: {e}")
            return None
    
    def _update_building_from_data(self, building: Building, data: Dict) -> None:
        """
        Update building object with data from raw API response
        
        Args:
            building: Building object to update
            data: Raw data dictionary
        """
        # Address information
        building.address = self._extract_address(data)
        
        # Spatial data - handle both direct lat/lng and geometry objects
        if data.get('latitude') and data.get('longitude'):
            building.latitude = self._safe_float(data.get('latitude'))
            building.longitude = self._safe_float(data.get('longitude'))
        
        # Handle geometry object or footprint data
        geometry = data.get('geometry') or data.get('the_geom')
        footprint_coords = data.get('footprint')
        
        if geometry:
            lat, lng, footprint = self._extract_spatial_data(geometry)
            if lat and lng and not building.latitude:
                building.latitude = lat
                building.longitude = lng
            if footprint:
                building.footprint = footprint
        elif footprint_coords:
            # Handle direct footprint coordinates
            building.footprint = footprint_coords
        
        # Building characteristics
        building.height = self._safe_float(data.get('height') or data.get('max_height'))
        
        # Handle floors from data or estimate from height
        floors = data.get('floors') or data.get('num_floors')
        if floors:
            building.floors = self._safe_int(floors)
        elif building.height:
            # Estimate floors from height (3.5m per floor average)
            building.floors = max(1, int(building.height / 3.5))
        
        # Building type and use
        building_type = (data.get('building_type') or 
                        data.get('building_use') or 
                        data.get('use_type') or
                        data.get('land_use'))
        building.building_type = self._normalize_building_type(building_type)
        
        # Zoning and assessment
        building.zoning = (data.get('zoning') or 
                          data.get('zone_class') or
                          data.get('zone_code'))
        building.assessed_value = self._safe_float(data.get('assessed_value') or 
                                                  data.get('total_assessed_value'))
        building.land_use = (data.get('land_use') or 
                            data.get('use_description') or
                            building.building_type)
        
        # Additional metadata - construction year removed
        building.last_updated = datetime.utcnow()
        
        # Store data source for tracking
        if hasattr(building, '_data_source'):
            building._data_source = data.get('data_source', 'unknown')
    
    def _extract_address(self, data: Dict) -> str:
        """Extract and format address from building data"""
        address_fields = ['address', 'full_address', 'street_address', 'civic_address']
        
        for field in address_fields:
            if data.get(field):
                return str(data[field]).strip()
        
        # Try to construct address from components
        number = data.get('house_number') or data.get('civic_number')
        street = data.get('street_name')
        suffix = data.get('street_suffix')
        
        if number and street:
            address_parts = [str(number), str(street)]
            if suffix:
                address_parts.append(str(suffix))
            return ' '.join(address_parts)
        
        return f"Building {data.get('building_id', 'Unknown')}"
    
    def _extract_spatial_data(self, geometry: Dict) -> Tuple[Optional[float], Optional[float], List]:
        """
        Extract latitude, longitude, and footprint coordinates from geometry
        
        Args:
            geometry: Geometry object from API response
            
        Returns:
            Tuple of (latitude, longitude, footprint_coordinates)
        """
        try:
            coordinates = geometry.get('coordinates', [])
            if not coordinates:
                return None, None, []
            
            # Handle different geometry types
            geom_type = geometry.get('type', '').lower()
            
            if geom_type == 'polygon':
                # For polygons, coordinates are nested: [[[x, y], [x, y], ...]]
                if coordinates and len(coordinates) > 0:
                    polygon_coords = coordinates[0]  # Take outer ring
                    footprint = [[coord[0], coord[1]] for coord in polygon_coords]
                    
                    # Calculate centroid for lat/lng
                    if footprint:
                        avg_lng = sum(coord[0] for coord in footprint) / len(footprint)
                        avg_lat = sum(coord[1] for coord in footprint) / len(footprint)
                        return avg_lat, avg_lng, footprint
            
            elif geom_type == 'point':
                # For points, coordinates are [x, y]
                if len(coordinates) >= 2:
                    return coordinates[1], coordinates[0], [[coordinates[0], coordinates[1]]]
            
            return None, None, []
            
        except Exception as e:
            logger.warning(f"Error extracting spatial data: {e}")
            return None, None, []
    
    def _normalize_building_type(self, building_type: str) -> str:
        """Normalize building type to standard categories"""
        if not building_type:
            return "Unknown"
        
        building_type_lower = building_type.lower()
        
        # Map various types to standard categories
        if any(term in building_type_lower for term in ['commercial', 'office', 'retail', 'store']):
            return "Commercial"
        elif any(term in building_type_lower for term in ['residential', 'apartment', 'condo', 'house']):
            return "Residential"
        elif any(term in building_type_lower for term in ['industrial', 'warehouse', 'manufacturing']):
            return "Industrial"
        elif any(term in building_type_lower for term in ['mixed', 'multi']):
            return "Mixed Use"
        else:
            return building_type.title()
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to integer"""
        if value is None:
            return None
        try:
            return int(float(value))  # Handle string numbers
        except (ValueError, TypeError):
            return None
    
    def get_buildings_in_bounds(self, bounds: Tuple[float, float, float, float]) -> List[Building]:
        """
        Get buildings within specified geographical bounds
        
        Args:
            bounds: (lat_min, lon_min, lat_max, lon_max)
            
        Returns:
            List of Building objects within bounds
        """
        lat_min, lon_min, lat_max, lon_max = bounds
        
        buildings = Building.query.filter(
            Building.latitude.between(lat_min, lat_max),
            Building.longitude.between(lon_min, lon_max)
        ).all()
        
        return buildings
    
    def filter_buildings(self, buildings: List[Building], filter_criteria: Dict) -> List[Building]:
        """
        Filter buildings based on criteria
        
        Args:
            buildings: List of Building objects to filter
            filter_criteria: Filter criteria dictionary
            
        Returns:
            List of buildings matching the criteria
        """
        if not filter_criteria:
            return buildings
        
        filtered_buildings = []
        for building in buildings:
            if building.matches_filter(filter_criteria):
                filtered_buildings.append(building)
        
        return filtered_buildings
    
    def get_building_statistics(self, buildings: List[Building]) -> Dict:
        """
        Calculate statistics for a list of buildings
        
        Args:
            buildings: List of Building objects
            
        Returns:
            Dictionary with building statistics
        """
        if not buildings:
            return {
                'total_count': 0,
                'avg_height': 0,
                'avg_assessed_value': 0,
                'building_types': {},
                'zoning_types': {}
            }
        
        # Calculate averages
        heights = [b.height for b in buildings if b.height is not None]
        values = [b.assessed_value for b in buildings if b.assessed_value is not None]
        
        avg_height = sum(heights) / len(heights) if heights else 0
        avg_value = sum(values) / len(values) if values else 0
        
        # Count building types
        building_types = {}
        zoning_types = {}
        
        for building in buildings:
            if building.building_type:
                building_types[building.building_type] = building_types.get(building.building_type, 0) + 1
            if building.zoning:
                zoning_types[building.zoning] = zoning_types.get(building.zoning, 0) + 1
        
        return {
            'total_count': len(buildings),
            'avg_height': round(avg_height, 2),
            'avg_assessed_value': round(avg_value, 2),
            'building_types': building_types,
            'zoning_types': zoning_types
        } 