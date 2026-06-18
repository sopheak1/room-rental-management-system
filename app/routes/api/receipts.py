from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import Receipt, PaymentLog
from app import db

def _receipt_dict(r, include_logs=False):
    d = {
        'id': r.id, 'receipt_number': r.receipt_number,
        'room_id': r.room_id, 'tenant_id': r.tenant_id,
        'billing_month': r.billing_month, 'billing_year': r.billing_year,
        'room_price': r.room_price,
        'electricity_from': r.electricity_from, 'electricity_to': r.electricity_to,
        'electricity_units': r.electricity_units,
        'electricity_price_per_unit': r.electricity_price_per_unit,
        'electricity_total': r.electricity_total,
        'water_from': r.water_from, 'water_to': r.water_to,
        'water_units': r.water_units,
        'water_price_per_unit': r.water_price_per_unit,
        'water_total': r.water_total,
        'previous_balance': r.previous_balance, 'fee': r.fee,
        'late_fee': r.late_fee, 'discount': r.discount,
        'total_amount': r.total_amount, 'paid_amount': r.paid_amount,
        'remaining_balance': r.remaining_balance,
        'payment_status': r.payment_status, 'notes': r.notes,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None,
    }
    if include_logs:
        d['payment_logs'] = [{
            'id': p.id, 'amount': p.amount, 'payment_method': p.payment_method,
            'payment_date': p.payment_date.isoformat() if p.payment_date else None,
            'verification_hash': p.verification_hash,
            'deleted_at': p.deleted_at.isoformat() if p.deleted_at else None,
            'delete_reason': p.delete_reason,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        } for p in r.payment_logs]
    return d

@api_bp.route('/receipts', methods=['GET'])
@jwt_required()
def list_receipts():
    q = Receipt.query
    month = request.args.get('month', type=int)
    year  = request.args.get('year', type=int)
    status = request.args.get('status')
    if month:
        q = q.filter(Receipt.billing_month == month)
    if year:
        q = q.filter(Receipt.billing_year == year)
    if status:
        q = q.filter(Receipt.payment_status == status)
    receipts = q.order_by(Receipt.created_at.desc()).all()
    return jsonify([_receipt_dict(r) for r in receipts]), 200

@api_bp.route('/receipts/<int:receipt_id>', methods=['GET'])
@jwt_required()
def get_receipt(receipt_id):
    r = Receipt.query.get(receipt_id)
    if not r:
        return jsonify({'error': 'Receipt not found'}), 404
    return jsonify(_receipt_dict(r, include_logs=True)), 200

@api_bp.route('/receipts', methods=['POST'])
@jwt_required()
def create_receipt():
    data = request.get_json(silent=True) or {}
    room_id = data.get('room_id')
    month   = data.get('billing_month')
    year    = data.get('billing_year')
    # Check for duplicate
    existing = Receipt.query.filter_by(
        room_id=room_id, billing_month=month, billing_year=year
    ).first()
    if existing:
        return jsonify({
            'error': 'Receipt already exists for this room and month',
            'existing_id': existing.id,
            'server_data': _receipt_dict(existing, include_logs=True)
        }), 409
    # Generate receipt number
    count = Receipt.query.filter_by(billing_year=year).count() + 1
    receipt_number = f"RCP-{year}{month:02d}-{count:04d}"
    total = (data.get('room_price', 0) + data.get('electricity_total', 0) +
             data.get('water_total', 0) + data.get('previous_balance', 0) +
             data.get('late_fee', 0) - data.get('discount', 0))
    receipt = Receipt(
        receipt_number=receipt_number,
        room_id=room_id, tenant_id=data.get('tenant_id'),
        billing_month=month, billing_year=year,
        room_price=data.get('room_price', 0),
        electricity_from=data.get('electricity_from'),
        electricity_to=data.get('electricity_to'),
        electricity_units=data.get('electricity_units'),
        electricity_price_per_unit=data.get('electricity_price_per_unit'),
        electricity_total=data.get('electricity_total', 0),
        water_from=data.get('water_from'),
        water_to=data.get('water_to'),
        water_units=data.get('water_units'),
        water_price_per_unit=data.get('water_price_per_unit'),
        water_total=data.get('water_total', 0),
        previous_balance=data.get('previous_balance', 0),
        fee=data.get('fee', 0),
        late_fee=data.get('late_fee', 0),
        discount=data.get('discount', 0),
        total_amount=data.get('total_amount', total),
        paid_amount=0,
        remaining_balance=data.get('total_amount', total),
        payment_status='unpaid',
        notes=data.get('notes', ''),
    )
    db.session.add(receipt)
    db.session.commit()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 201
