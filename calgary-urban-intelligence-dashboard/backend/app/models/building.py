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
    height = db.Column(db.Float)  # Height in meters
    floors = db.Column(db.Integer)
    building_type = db.Column(db.String(100))  # Residential, Commercial, Industrial, etc.
    
    # Zoning and assessment data
    zoning = db.Column(db.String(50))  # Zoning classification (e.g., RC-G)
    assessed_value = db.Column(db.Float)  # Property assessment value
    land_use = db.Column(db.String(100))
    
    details_record = db.relationship('BuildingDetails', uselist=False, cascade='all, delete-orphan')

    @property
    def details(self):
        return json.loads(self.details_record.data_json) if self.details_record else {}

    @details.setter
    def details(self, value):
        if self.details_record is None:
            self.details_record = BuildingDetails()
        self.details_record.data_json = json.dumps(value)

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
            **self.details,
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
        """Apply the same criteria to live queries and saved projects; unknowns do not match."""
        def normalized(value):
            return str(value or '').lower().replace('_', ' ').replace('-', ' ').strip()

        for field, kind in [('height', 'height'), ('floors', 'floors'), ('assessed_value', 'value')]:
            value = getattr(self, field)
            low = filter_criteria.get(f'{kind}_min', filter_criteria.get(f'min_{kind}'))
            high = filter_criteria.get(f'{kind}_max', filter_criteria.get(f'max_{kind}'))
            if low is not None and (value is None or value < low):
                return False
            if high is not None and (value is None or value > high):
                return False
        for field, plural in [('building_type', 'building_types'), ('zoning', 'zoning_types')]:
            choices = filter_criteria.get(plural, [])
            if field in filter_criteria:
                choices = [filter_criteria[field]]
            if choices and normalized(getattr(self, field)) not in {normalized(v) for v in choices}:
                return False
        return True


class BuildingDetails(db.Model):
    """Additional provenance and source attributes without changing existing building columns."""
    __tablename__ = 'building_details'
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), primary_key=True)
    data_json = db.Column(db.Text, nullable=False, default='{}')


class CachedArea(db.Model):
    """Record which exact bounded areas were fetched, including empty results."""
    __tablename__ = 'cached_areas'
    bounds_key = db.Column(db.String(160), primary_key=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    warnings_json = db.Column(db.Text, nullable=False, default='[]')
