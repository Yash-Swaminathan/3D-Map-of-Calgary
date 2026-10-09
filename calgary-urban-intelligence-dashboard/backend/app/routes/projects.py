from flask import Blueprint, jsonify, request
from app import db
from app.models.project import Project
from app.models.user import User

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/save', methods=['POST'])
def save_project():
    """Save a new project with current filters"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['user_id', 'name', 'filters']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        user_id = data['user_id']
        name = data['name'].strip()
        filters = data['filters']
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Project name cannot be empty'}), 400
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if project name already exists for this user
        existing_project = Project.query.filter_by(
            user_id=user_id, 
            name=name
        ).first()
        
        if existing_project:
            return jsonify({'error': 'Project name already exists'}), 409
        
        # Create new project
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            filters=filters
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'project': project.to_dict(),
            'message': f'Project "{name}" saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_projects(user_id):
    """Get all projects for a specific user"""
    try:
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's projects
        projects = Project.query.filter_by(user_id=user_id).order_by(
            Project.updated_at.desc()
        ).all()
        
        projects_json = [project.to_dict() for project in projects]
        
        return jsonify({
            'success': True,
            'projects': projects_json,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID"""
    try:
        project = Project.query.get_or_404(project_id)
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update an existing project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Update fields if provided
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Project name cannot be empty'}), 400
            
            # Check for name conflicts (excluding current project)
            existing_project = Project.query.filter(
                Project.user_id == project.user_id,
                Project.name == name,
                Project.id != project_id
            ).first()
            
            if existing_project:
                return jsonify({'error': 'Project name already exists'}), 409
            
            project.name = name
        
        if 'description' in data:
            project.description = data['description'].strip()
        
        if 'filters' in data:
            project.filters = data['filters']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'project': project.to_dict(),
            'message': 'Project updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Project "{project_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>/load', methods=['POST'])
def load_project(project_id):
    """Load a project and return its filters for application to the map"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Optional: Apply filters to buildings and return filtered results
        apply_filters = request.args.get('apply_filters', 'false').lower() == 'true'
        
        response_data = {
            'success': True,
            'project': project.to_dict(),
            'filters': project.filters,
            'message': f'Project "{project.name}" loaded successfully'
        }
        
        if apply_filters and project.filters:
            from app.services.building_processor import BuildingProcessor
            from app.models.building import Building
            
            processor = BuildingProcessor()
            buildings = Building.query.all()
            filtered_buildings = processor.filter_buildings(buildings, project.filters)
            
            response_data.update({
                'buildings': [building.to_dict() for building in filtered_buildings],
                'statistics': processor.get_building_statistics(filtered_buildings)
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 