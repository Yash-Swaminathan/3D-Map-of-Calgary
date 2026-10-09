from werkzeug.exceptions import HTTPException
from app.utils.validation import validate_bounds, validate_filters
from flask import Blueprint, jsonify, request
from app import db
from app.models.user import User

api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Calgary Urban Intelligence Dashboard API is running'
    })

@api_bp.route('/users/login', methods=['POST'])
def user_login():
    """Simple user login/identification endpoint"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError('Request body must be a JSON object.')
        if not data or 'username' not in data:
            return jsonify({'error': 'Username is required'}), 400
        
        if not isinstance(data['username'], str) or len(data['username'].strip()) > 80:
            raise ValueError('Username must be a string of at most 80 characters.')
        username = data['username'].strip()
        if not username:
            return jsonify({'error': 'Username cannot be empty'}), 400
        
        # Find or create user
        user = User.find_or_create(username)
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': f'Welcome, {user.username}!'
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information by ID"""
    try:
        user = db.get_or_404(User, user_id)
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except HTTPException:
        raise
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 