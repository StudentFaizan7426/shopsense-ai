from flask import Blueprint, request, jsonify, make_response
from database import db
from models import User
from datetime import datetime
import hashlib
import time

auth_bp = Blueprint('auth', __name__)
@auth_bp.after_request
def after_request(response):
    response.headers.add(
        'Access-Control-Allow-Origin', '*')
    response.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type, X-Auth-Token')
    response.headers.add(
        'Access-Control-Allow-Methods',
        'GET, POST, PUT, DELETE, OPTIONS')
    return response

# ── Simple token store (in memory) ────────
# Format: { token: { user_id, expires } }
active_tokens = {}

def generate_token(user_id):
    """Generate a simple secure token"""
    raw   = f"{user_id}-{time.time()}-shopmanager"
    token = hashlib.sha256(raw.encode()).hexdigest()
    # Store token with expiry (12 hours)
    active_tokens[token] = {
        'user_id': user_id,
        'expires': time.time() + (12 * 3600)
    }
    return token

def get_current_user():
    """Get user from token in request header"""
    token = request.headers.get('X-Auth-Token')
    if not token:
        return None
    token_data = active_tokens.get(token)
    if not token_data:
        return None
    # Check expiry
    if time.time() > token_data['expires']:
        del active_tokens[token]
        return None
    return User.query.get(token_data['user_id'])

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error'  : 'Please login first!',
                'code'   : 'UNAUTHORIZED'
            }), 401
        return f(*args, **kwargs)
    return decorated

def owner_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error'  : 'Please login first!',
                'code'   : 'UNAUTHORIZED'
            }), 401
        if user.role != 'owner':
            return jsonify({
                'success': False,
                'error'  : 'Owner access required!',
                'code'   : 'FORBIDDEN'
            }), 403
        return f(*args, **kwargs)
    return decorated

def manager_or_above(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error'  : 'Please login first!',
                'code'   : 'UNAUTHORIZED'
            }), 401
        if user.role not in ['owner', 'manager']:
            return jsonify({
                'success': False,
                'error'  : 'Manager access required!',
                'code'   : 'FORBIDDEN'
            }), 403
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data     = request.get_json()
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({
                'success': False,
                'error'  : 'Please enter username and password!'
            }), 400

        user = User.query.filter_by(username=username).first()

        if not user:
            return jsonify({
                'success': False,
                'error'  : 'Invalid username or password!'
            }), 401

        if not user.is_active:
            return jsonify({
                'success': False,
                'error'  : 'Account deactivated. Contact owner!'
            }), 401

        if not user.check_password(password):
            return jsonify({
                'success': False,
                'error'  : 'Invalid username or password!'
            }), 401

        # Generate token
        token = generate_token(user.id)

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Welcome back, {user.full_name}!',
            'token'  : token,
            'user'   : {
                'id'       : user.id,
                'username' : user.username,
                'full_name': user.full_name,
                'role'     : user.role,
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500


# ─────────────────────────────────────────
# POST /api/auth/logout
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    token = request.headers.get('X-Auth-Token')
    if token and token in active_tokens:
        del active_tokens[token]
    return jsonify({
        'success': True,
        'message': 'Logged out successfully!'
    })


# ─────────────────────────────────────────
# GET /api/auth/me
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/me', methods=['GET'])
def get_me():
    user = get_current_user()
    if not user:
        return jsonify({
            'success': False,
            'error'  : 'Not logged in!',
            'code'   : 'UNAUTHORIZED'
        }), 401
    return jsonify({
        'success': True,
        'user'   : user.to_dict()
    })


# ─────────────────────────────────────────
# GET /api/auth/users — Owner only
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/users', methods=['GET'])
@owner_required
def get_users():
    try:
        users = User.query.order_by(
            User.created_at.desc()
        ).all()
        return jsonify({
            'success': True,
            'data'   : [u.to_dict() for u in users]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500


# ─────────────────────────────────────────
# POST /api/auth/users — Owner only
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/users', methods=['POST'])
@owner_required
def create_user():
    try:
        data      = request.get_json()
        username  = data.get('username','').strip().lower()
        password  = data.get('password','')
        full_name = data.get('full_name','').strip()
        role      = data.get('role','staff')

        if not username or not password or not full_name:
            return jsonify({
                'success': False,
                'error'  : 'All fields are required!'
            }), 400

        if role not in ['owner','manager','staff']:
            return jsonify({
                'success': False,
                'error'  : 'Invalid role!'
            }), 400

        if len(password) < 6:
            return jsonify({
                'success': False,
                'error'  : 'Password must be 6+ characters!'
            }), 400

        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'error'  : f'Username "{username}" already exists!'
            }), 400

        new_user = User(
            username = username,
            full_name= full_name,
            role     = role
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'User "{full_name}" created!',
            'data'   : new_user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500


# ─────────────────────────────────────────
# PUT /api/auth/users/<id> — Owner only
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/users/<int:user_id>',
               methods=['PUT'])
@owner_required
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        if 'full_name' in data:
            user.full_name = data['full_name'].strip()
        if 'role' in data and \
           data['role'] in ['owner','manager','staff']:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        if 'password' in data and data['password']:
            if len(data['password']) < 6:
                return jsonify({
                    'success': False,
                    'error'  : 'Password must be 6+ characters!'
                }), 400
            user.set_password(data['password'])

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'User "{user.full_name}" updated!',
            'data'   : user.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500


# ─────────────────────────────────────────
# DELETE /api/auth/users/<id> — Owner only
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/users/<int:user_id>',
               methods=['DELETE'])
@owner_required
def delete_user(user_id):
    try:
        current = get_current_user()
        if current.id == user_id:
            return jsonify({
                'success': False,
                'error'  : 'Cannot delete your own account!'
            }), 400

        user = User.query.get_or_404(user_id)
        name = user.full_name
        db.session.delete(user)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'User "{name}" deleted!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500


# ─────────────────────────────────────────
# POST /api/auth/change-password
# ─────────────────────────────────────────
@auth_bp.route('/api/auth/change-password',
               methods=['POST'])
@login_required
def change_password():
    try:
        user     = get_current_user()
        data     = request.get_json()
        old_pass = data.get('old_password','')
        new_pass = data.get('new_password','')

        if not user.check_password(old_pass):
            return jsonify({
                'success': False,
                'error'  : 'Current password is incorrect!'
            }), 400

        if len(new_pass) < 6:
            return jsonify({
                'success': False,
                'error'  : 'New password must be 6+ characters!'
            }), 400

        user.set_password(new_pass)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Password changed successfully!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error'  : str(e)
        }), 500