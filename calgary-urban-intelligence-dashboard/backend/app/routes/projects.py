from werkzeug.exceptions import HTTPException
from app.utils.validation import validate_bounds, validate_filters
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
        if not isinstance(data, dict):
            raise ValueError('Request body must be a JSON object.')
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['user_id', 'name', 'filters']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        user_id = data['user_id']
        if not isinstance(data['name'], str) or len(data['name'].strip()) > 120:
            raise ValueError('Project name must be a string of at most 120 characters.')
        name = data['name'].strip()
        filters = validate_filters(data['filters'])
        description = data.get('description', '')
        if not isinstance(description, str):
            raise ValueError('Description must be a string.')
        description = description.strip()
        
        if not name:
            return jsonify({'error': 'Project name cannot be empty'}), 400
        
        # Verify user exists
        user = db.session.get(User, user_id)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_projects(user_id):
    """Get all projects for a specific user"""
    try:
        # Verify user exists
        user = db.session.get(User, user_id)
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
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID"""
    try:
        project = db.get_or_404(Project, project_id)
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update an existing project"""
    try:
        project = db.get_or_404(Project, project_id)
        
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError('Request body must be a JSON object.')
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Update fields if provided
        if 'name' in data:
            if not isinstance(data['name'], str) or len(data['name'].strip()) > 120:
                raise ValueError('Project name must be a string of at most 120 characters.')
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
            if not isinstance(data['description'], str):
                raise ValueError('Description must be a string.')
            project.description = data['description'].strip()
        
        if 'filters' in data:
            project.filters = validate_filters(data['filters'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'project': project.to_dict(),
            'message': 'Project updated successfully'
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        project = db.get_or_404(Project, project_id)
        project_name = project.name
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Project "{project_name}" deleted successfully'
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<int:project_id>/load', methods=['POST'])
def load_project(project_id):
    """Load a project and return its filters for application to the map"""
    try:
        project = db.get_or_404(Project, project_id)
        
        # Optional: Apply filters to buildings and return filtered results
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            raise ValueError('Request body must be a JSON object.')
        bounds = validate_bounds(data['bounds']) if data.get('bounds') is not None else None
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
            buildings = processor.get_buildings_in_bounds(bounds) if bounds else Building.query.all()
            filtered_buildings = processor.filter_buildings(buildings, project.filters)
            
            response_data.update({
                'buildings': [building.to_dict() for building in filtered_buildings],
                'statistics': processor.get_building_statistics(filtered_buildings)
            })
        
        return jsonify(response_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 