from datetime import datetime
from app import db

class User(db.Model):
    """User model for simple identification - no complex auth required"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with projects
    projects = db.relationship('Project', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'project_count': len(self.projects)
        }
    
    @classmethod
    def find_or_create(cls, username):
        """Find existing user or create new one"""
        user = cls.query.filter_by(username=username).first()
        if not user:
            user = cls(username=username)
            db.session.add(user)
            db.session.commit()
        return user 