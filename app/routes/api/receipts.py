from datetime import date, datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import Receipt, PaymentLog, PromisedPaymentLog
from app.routes.receipts import _generate_receipt_number, _has_next_receipt
from app.utils.google_drive import backup_to_drive
from app.utils.timezone import today as _today
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
        'promised_payment_date': r.current_promised_date.isoformat() if r.current_promised_date else None,
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
    if not room_id or not month or not year:
        return jsonify({'error': 'room_id, billing_month, and billing_year are required'}), 400
    tenant_id = data.get('tenant_id')
    # Check for duplicate
    existing = Receipt.query.filter_by(
        tenant_id=tenant_id, room_id=room_id, billing_month=month, billing_year=year
    ).first()
    if existing:
        return jsonify({
            'error': 'Receipt already exists for this tenant, room, and month',
            'existing_id': existing.id,
            'server_data': _receipt_dict(existing, include_logs=True)
        }), 409
    receipt_number = _generate_receipt_number(year, month)
    total = round(data.get('room_price', 0) + data.get('electricity_total', 0) +
                  data.get('water_total', 0) + data.get('previous_balance', 0) +
                  data.get('fee', 0) + data.get('late_fee', 0) - data.get('discount', 0), 2)
    total_amount = data.get('total_amount', total)

    payment_status = data.get('payment_status', 'unpaid')
    paid_amount = float(data.get('paid_amount', 0) or 0)
    if payment_status == 'paid':
        paid_amount = total_amount
        remaining_balance = 0.0
    elif payment_status == 'partial':
        remaining_balance = round(max(total_amount - paid_amount, 0), 2)
    else:
        paid_amount = 0.0
        remaining_balance = total_amount

    receipt = Receipt(
        receipt_number=receipt_number,
        room_id=room_id, tenant_id=tenant_id,
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
        total_amount=total_amount,
        paid_amount=paid_amount,
        remaining_balance=remaining_balance,
        payment_status=payment_status,
        notes=data.get('notes', ''),
    )
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.add(receipt)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A receipt for this tenant, room, and month already exists (concurrent request conflict)'}), 409
    backup_to_drive()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 201

@api_bp.route('/receipts/<int:receipt_id>', methods=['PUT'])
@jwt_required()
def edit_receipt(receipt_id):
    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404
    if _has_next_receipt(receipt):
        return jsonify({'error': 'Cannot edit — a receipt for the next month already exists and carries this balance'}), 400

    data = request.get_json(silent=True) or {}
    elec_override = receipt.electricity_units is None
    water_override = receipt.water_units is None

    if elec_override:
        electricity_total = float(data.get('electricity_total', 0) or 0)
        elec_from = elec_to = elec_units = elec_ppu = None
    else:
        elec_from = float(data.get('electricity_from', 0) or 0)
        elec_to = float(data.get('electricity_to', 0) or 0)
        elec_units = max(elec_to - elec_from, 0)
        elec_ppu = float(data.get('electricity_price_per_unit', 0) or 0)
        electricity_total = round(elec_units * elec_ppu, 2)

    if water_override:
        water_total = float(data.get('water_total', 0) or 0)
        w_from = w_to = w_units = w_ppu = None
    else:
        w_from = float(data.get('water_from', 0) or 0)
        w_to = float(data.get('water_to', 0) or 0)
        w_units = max(w_to - w_from, 0)
        w_ppu = float(data.get('water_price_per_unit', 0) or 0)
        water_total = round(w_units * w_ppu, 2)

    room_price = float(data.get('room_price', 0) or 0)
    previous_balance = float(data.get('previous_balance', 0) or 0)
    fee = float(data.get('fee', 0) or 0)
    late_fee = float(data.get('late_fee', 0) or 0)
    discount = float(data.get('discount', 0) or 0)
    notes = (data.get('notes') or '').strip() or None

    new_total = round(room_price + electricity_total + water_total + previous_balance +
                       fee + late_fee - discount, 2)

    if new_total < receipt.paid_amount:
        return jsonify({
            'error': f'Cannot reduce total below paid amount ({receipt.paid_amount:,.0f})',
            'paid_amount': receipt.paid_amount
        }), 400

    receipt.room_price = room_price
    receipt.electricity_total = electricity_total
    receipt.electricity_from = elec_from
    receipt.electricity_to = elec_to
    receipt.electricity_units = elec_units
    receipt.electricity_price_per_unit = elec_ppu
    receipt.water_total = water_total
    receipt.water_from = w_from
    receipt.water_to = w_to
    receipt.water_units = w_units
    receipt.water_price_per_unit = w_ppu
    receipt.previous_balance = previous_balance
    receipt.fee = fee
    receipt.late_fee = late_fee
    receipt.discount = discount
    receipt.notes = notes
    receipt.total_amount = new_total
    receipt.remaining_balance = round(max(new_total - receipt.paid_amount, 0), 2)

    if receipt.paid_amount >= new_total:
        receipt.payment_status = 'paid'
        receipt.remaining_balance = 0.0
    elif receipt.paid_amount > 0:
        receipt.payment_status = 'partial'
    else:
        receipt.payment_status = 'unpaid'

    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    backup_to_drive()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 200

@api_bp.route('/receipts/<int:receipt_id>/defer', methods=['POST'])
@jwt_required()
def defer_receipt(receipt_id):
    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404
    receipt.payment_status = 'deferred'
    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 200

@api_bp.route('/receipts/<int:receipt_id>/promise', methods=['POST'])
@jwt_required()
def add_promise(receipt_id):
    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404
    if _has_next_receipt(receipt):
        return jsonify({'error': 'Cannot set a promise — a receipt for the next month already exists'}), 400

    data = request.get_json(silent=True) or {}
    promised_date_str = data.get('promised_date')
    if not promised_date_str:
        return jsonify({'error': 'promised_date is required'}), 400

    try:
        promised_date = date.fromisoformat(promised_date_str)
    except ValueError:
        return jsonify({'error': 'Invalid promised_date format. Use YYYY-MM-DD'}), 400
    if promised_date < _today():
        return jsonify({'error': 'Promised date cannot be in the past'}), 400

    log = PromisedPaymentLog(
        receipt_id=receipt_id,
        promised_date=promised_date,
        notes=(data.get('notes') or '').strip() or None
    )
    db.session.add(log)
    # Same reasoning as the web route — promised_payment_logs is a separate
    # table, so the receipts row's onupdate trigger won't fire on its own.
    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    backup_to_drive()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 200

@api_bp.route('/receipts/<int:receipt_id>/undefer', methods=['POST'])
@jwt_required()
def undefer_receipt(receipt_id):
    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404
    receipt.payment_status = 'partial' if receipt.paid_amount > 0 else 'unpaid'
    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 200
