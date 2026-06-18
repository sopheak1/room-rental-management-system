from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app.routes.api import api_bp
from app.models import User

# In-memory blocklist for revoked refresh tokens (cleared on server restart — acceptable for single admin)
_blocklist: set = set()

def is_token_revoked(jwt_payload: dict) -> bool:
    return jwt_payload['jti'] in _blocklist

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200

@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200

@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    _blocklist.add(jti)
    return jsonify({'msg': 'Logged out'}), 200
