from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from config import config
from werkzeug.exceptions import HTTPException

# Initialize extensions
db = SQLAlchemy()

def create_app(config_name='default', config_overrides=None):
    """Application factory pattern for Flask app creation"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    app.config.update(config_overrides or {})
    
    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({'error': error.description}), error.code

    @app.before_request
    def validate_json_body():
        if request.path.startswith('/api/') and request.method in {'POST', 'PUT'}:
            if not request.is_json:
                return jsonify({'error': 'Use a JSON request body.'}), 400
            if not isinstance(request.get_json(), dict):
                return jsonify({'error': 'Request body must be a JSON object.'}), 400

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Register blueprints
    from app.routes.api import api_bp
    from app.routes.buildings import buildings_bp
    from app.routes.projects import projects_bp
    from app.routes.queries import queries_bp
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(buildings_bp, url_prefix='/api/buildings')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(queries_bp, url_prefix='/api/query')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 