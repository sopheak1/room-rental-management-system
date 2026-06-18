from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import UtilityUsage
from app import db

def _usage_dict(u):
    return {
        'id': u.id, 'room_id': u.room_id,
        'billing_month': u.billing_month, 'billing_year': u.billing_year,
        'electricity_from': u.electricity_from, 'electricity_to': u.electricity_to,
        'electricity_amount': u.electricity_amount,
        'water_from': u.water_from, 'water_to': u.water_to,
        'water_amount': u.water_amount,
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'updated_at': u.updated_at.isoformat() if u.updated_at else None,
    }

@api_bp.route('/utility-usage', methods=['GET'])
@jwt_required()
def list_utility_usage():
    q = UtilityUsage.query
    month = request.args.get('month', type=int)
    year  = request.args.get('year', type=int)
    if month:
        q = q.filter(UtilityUsage.billing_month == month)
    if year:
        q = q.filter(UtilityUsage.billing_year == year)
    return jsonify([_usage_dict(u) for u in q.all()]), 200

@api_bp.route('/utility-usage/batch', methods=['POST'])
@jwt_required()
def batch_upsert_utility_usage():
    data = request.get_json(silent=True) or {}
    month    = data.get('billing_month')
    year     = data.get('billing_year')
    readings = data.get('readings', [])
    saved = 0
    for r in readings:
        room_id = r.get('room_id')
        existing = UtilityUsage.query.filter_by(
            room_id=room_id, billing_month=month, billing_year=year
        ).first()
        if existing:
            for field in ['electricity_from', 'electricity_to', 'electricity_amount',
                          'water_from', 'water_to', 'water_amount']:
                if field in r:
                    setattr(existing, field, r[field])
            existing.updated_at = datetime.utcnow()
        else:
            usage = UtilityUsage(
                room_id=room_id, billing_month=month, billing_year=year,
                electricity_from=r.get('electricity_from'),
                electricity_to=r.get('electricity_to'),
                electricity_amount=r.get('electricity_amount'),
                water_from=r.get('water_from'),
                water_to=r.get('water_to'),
                water_amount=r.get('water_amount'),
            )
            db.session.add(usage)
        saved += 1
    db.session.commit()
    return jsonify({'saved': saved}), 200
