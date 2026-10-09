import json
from datetime import datetime
from app import db

class Building(db.Model):
    """Building model for Calgary city building data"""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic building information
    address = db.Column(db.String(200))
    building_id = db.Column(db.String(50), unique=True, index=True)  # External ID from Calgary data
    
    # Spatial data
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    footprint_coords = db.Column(db.Text)  # JSON string of polygon coordinates
    
    # Building characteristics
    height = db.Column(db.Float)  # Height in feet/meters
    floors = db.Column(db.Integer)
    building_type = db.Column(db.String(100))  # Residential, Commercial, Industrial, etc.
    
    # Zoning and assessment data
    zoning = db.Column(db.String(50))  # Zoning classification (e.g., RC-G)
    assessed_value = db.Column(db.Float)  # Property assessment value
    land_use = db.Column(db.String(100))
    
    # Additional metadata
    last_updated = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Building {self.building_id}: {self.address}>'
    
    @property
    def footprint(self):
        """Return footprint coordinates as Python object"""
        if self.footprint_coords:
            try:
                return json.loads(self.footprint_coords)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @footprint.setter
    def footprint(self, value):
        """Set footprint coordinates from Python object"""
        if value:
            try:
                self.footprint_coords = json.dumps(value)
            except (TypeError, ValueError):
                self.footprint_coords = None
        else:
            self.footprint_coords = None
    
    def to_dict(self):
        """Convert building to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'building_id': self.building_id,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'height': self.height,
            'floors': self.floors,
            'building_type': self.building_type,
            'zoning': self.zoning,
            'assessed_value': self.assessed_value,
            'land_use': self.land_use,
            'footprint': self.footprint,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def matches_filter(self, filter_criteria):
        """Check if building matches the given filter criteria"""
        try:
            # Height filters - support both old and new format
            min_height = filter_criteria.get('min_height') or filter_criteria.get('height_min')
            max_height = filter_criteria.get('max_height') or filter_criteria.get('height_max')
            
            if min_height and (not self.height or self.height < min_height):
                return False
            if max_height and (not self.height or self.height > max_height):
                return False
            
            # Floors filters - support both old and new format
            min_floors = filter_criteria.get('min_floors') or filter_criteria.get('floors_min')
            max_floors = filter_criteria.get('max_floors') or filter_criteria.get('floors_max')
            
            if min_floors and (not self.floors or self.floors < min_floors):
                return False
            if max_floors and (not self.floors or self.floors > max_floors):
                return False
            
            # Building type filter - support both old and new format
            building_types = filter_criteria.get('building_types', [])
            building_type = filter_criteria.get('building_type')
            
            # If single building_type specified, convert to list for compatibility
            if building_type:
                building_types = [building_type]
            
            if building_types and self.building_type and self.building_type.lower() not in [bt.lower() for bt in building_types]:
                return False
            
            # Zoning filter - support both old and new format
            zoning_types = filter_criteria.get('zoning_types', [])
            zoning = filter_criteria.get('zoning')
            
            # If single zoning specified, convert to list for compatibility  
            if zoning:
                zoning_types = [zoning]
            
            if zoning_types and self.zoning and self.zoning.upper() not in [zt.upper() for zt in zoning_types]:
                return False
            
            # Assessment value filters - support both old and new format
            min_value = filter_criteria.get('min_value') or filter_criteria.get('value_min')
            max_value = filter_criteria.get('max_value') or filter_criteria.get('value_max')
            
            if min_value and (not self.assessed_value or self.assessed_value < min_value):
                return False
            if max_value and (not self.assessed_value or self.assessed_value > max_value):
                return False
            
            return True
            
        except Exception as e:
            return False 