import json
from datetime import datetime
from app import db

class Project(db.Model):
    """Project model for saving user map analyses and filters"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    filters_json = db.Column(db.Text)  # JSON string of active filters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.name} by User {self.user_id}>'
    
    @property
    def filters(self):
        """Parse filters JSON string to Python object"""
        if self.filters_json:
            try:
                return json.loads(self.filters_json)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @filters.setter
    def filters(self, value):
        """Set filters by converting Python object to JSON string"""
        if value is None:
            self.filters_json = None
        else:
            self.filters_json = json.dumps(value)
    
    def to_dict(self):
        """Convert project object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'filters': self.filters,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_filters(self, new_filters):
        """Update project filters and timestamp"""
        self.filters = new_filters
        self.updated_at = datetime.utcnow()
        db.session.commit() 