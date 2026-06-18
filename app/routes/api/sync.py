from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import Building, Room, Tenant, UtilityPrice, Receipt, PaymentLog, UtilityUsage

def _fmt(dt):
    """Return ISO string or None for a datetime/date value."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt.isoformat()  # handles date objects too

@api_bp.route('/sync', methods=['GET'])
@jwt_required()
def sync():
    since_str = request.args.get('since')
    if not since_str:
        return jsonify({'error': 'since parameter required'}), 400
    try:
        since = datetime.fromisoformat(since_str)
    except ValueError:
        return jsonify({'error': 'Invalid since format. Use ISO 8601 (e.g. 2026-01-01T00:00:00)'}), 400

    buildings = Building.query.filter(Building.updated_at >= since).all()
    rooms = Room.query.filter(Room.updated_at >= since).all()
    tenants = Tenant.query.filter(Tenant.updated_at >= since).all()
    utility_prices = UtilityPrice.query.filter(UtilityPrice.created_at >= since).all()
    receipts = Receipt.query.filter(Receipt.updated_at >= since).all()
    payment_logs = PaymentLog.query.filter(PaymentLog.created_at >= since).all()
    utility_usage = UtilityUsage.query.filter(UtilityUsage.updated_at >= since).all()

    return jsonify({
        'buildings': [{'id': b.id, 'name': b.name, 'address': b.address,
                       'created_at': _fmt(b.created_at), 'updated_at': _fmt(b.updated_at)}
                      for b in buildings],
        'rooms': [{'id': r.id, 'building_id': r.building_id, 'room_number': r.room_number,
                   'floor': r.floor, 'room_type': r.room_type, 'price': r.price,
                   'deposit_amount': r.deposit_amount, 'status': r.status,
                   'created_at': _fmt(r.created_at), 'updated_at': _fmt(r.updated_at)}
                  for r in rooms],
        'tenants': [{'id': t.id, 'room_id': t.room_id, 'name': t.name, 'gender': t.gender,
                     'nid': t.nid, 'tel': t.tel,
                     'emergency_contact_name': t.emergency_contact_name,
                     'emergency_contact_tel': t.emergency_contact_tel,
                     'num_roommates': t.num_roommates, 'contract_duration': t.contract_duration,
                     'move_in_date': _fmt(t.move_in_date), 'deposit_paid': t.deposit_paid,
                     'is_active': t.is_active,
                     'created_at': _fmt(t.created_at), 'updated_at': _fmt(t.updated_at)}
                    for t in tenants],
        'utility_prices': [{'id': u.id, 'utility_type': u.utility_type,
                             'price_per_unit': u.price_per_unit,
                             'effective_date': _fmt(u.effective_date),
                             'created_at': _fmt(u.created_at)}
                           for u in utility_prices],
        'receipts': [{'id': r.id, 'receipt_number': r.receipt_number,
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
                      'created_at': _fmt(r.created_at), 'updated_at': _fmt(r.updated_at)}
                     for r in receipts],
        'payment_logs': [{'id': p.id, 'receipt_id': p.receipt_id, 'amount': p.amount,
                          'payment_method': p.payment_method,
                          'payment_date': _fmt(p.payment_date),
                          'verification_hash': p.verification_hash,
                          'deleted_at': _fmt(p.deleted_at), 'delete_reason': p.delete_reason,
                          'created_at': _fmt(p.created_at)}
                         for p in payment_logs],
        'utility_usage': [{'id': u.id, 'room_id': u.room_id,
                           'billing_month': u.billing_month, 'billing_year': u.billing_year,
                           'electricity_from': u.electricity_from, 'electricity_to': u.electricity_to,
                           'electricity_amount': u.electricity_amount,
                           'water_from': u.water_from, 'water_to': u.water_to,
                           'water_amount': u.water_amount,
                           'created_at': _fmt(u.created_at), 'updated_at': _fmt(u.updated_at)}
                          for u in utility_usage],
    }), 200
