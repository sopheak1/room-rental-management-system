from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import Room
from app import db

def _room_dict(r):
    return {
        'id': r.id, 'building_id': r.building_id,
        'building_name': r.building.name if r.building else None,
        'room_number': r.room_number, 'floor': r.floor,
        'room_type': r.room_type, 'price': r.price,
        'deposit_amount': r.deposit_amount, 'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None,
    }

@api_bp.route('/rooms', methods=['GET'])
@jwt_required()
def list_rooms():
    rooms = Room.query.all()
    return jsonify([_room_dict(r) for r in rooms]), 200

@api_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    data = request.get_json(silent=True) or {}
    allowed = ['room_number', 'floor', 'room_type', 'price', 'deposit_amount', 'status']
    for field in allowed:
        if field in data:
            setattr(room, field, data[field])
    room.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_room_dict(room)), 200
