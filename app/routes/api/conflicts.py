import json
from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import ConflictLog, Receipt
from app import db

@api_bp.route('/conflicts', methods=['POST'])
@jwt_required()
def save_conflict():
    data = request.get_json(silent=True) or {}
    entry = ConflictLog(
        entity_type=data.get('entity_type', ''),
        entity_id=data.get('entity_id', 0),
        mobile_data_json=json.dumps(data.get('mobile_data', {})),
        server_data_json=json.dumps(data.get('server_data', {})),
        status='pending_review',
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({'id': entry.id, 'status': entry.status}), 201

@api_bp.route('/conflicts/<int:conflict_id>/resolve-keep', methods=['POST'])
@jwt_required()
def resolve_keep(conflict_id):
    entry = ConflictLog.query.get(conflict_id)
    if not entry:
        return jsonify({'error': 'Conflict not found'}), 404
    entry.status = 'resolved_keep'
    entry.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'id': entry.id, 'status': entry.status}), 200

@api_bp.route('/conflicts/<int:conflict_id>/override', methods=['POST'])
@jwt_required()
def resolve_override(conflict_id):
    entry = ConflictLog.query.get(conflict_id)
    if not entry:
        return jsonify({'error': 'Conflict not found'}), 404
    mobile_data = json.loads(entry.mobile_data_json)
    # Apply mobile_data fields to the entity (receipts only for now)
    if entry.entity_type == 'receipt':
        receipt = Receipt.query.get(entry.entity_id)
        if receipt:
            allowed = ['notes', 'late_fee', 'discount']
            for field in allowed:
                if field in mobile_data:
                    setattr(receipt, field, mobile_data[field])
            receipt.updated_at = datetime.utcnow()
    entry.status = 'resolved_override'
    entry.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'id': entry.id, 'status': entry.status}), 200
