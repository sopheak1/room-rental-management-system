from datetime import datetime, date
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.models import Tenant, Room, TenantHistory, Receipt
from app.utils.google_drive import backup_to_drive
from app import db

def _tenant_dict(t):
    return {
        'id': t.id, 'room_id': t.room_id, 'name': t.name, 'gender': t.gender,
        'nid': t.nid, 'tel': t.tel,
        'emergency_contact_name': t.emergency_contact_name,
        'emergency_contact_tel': t.emergency_contact_tel,
        'num_roommates': t.num_roommates, 'contract_duration': t.contract_duration,
        'move_in_date': t.move_in_date.isoformat() if t.move_in_date else None,
        'deposit_paid': t.deposit_paid, 'is_active': t.is_active,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    }

@api_bp.route('/tenants/<int:room_id>', methods=['GET'])
@jwt_required()
def get_tenant(room_id):
    tenant = Tenant.query.filter_by(room_id=room_id, is_active=True).first()
    if not tenant:
        return jsonify({'error': 'No active tenant'}), 404
    return jsonify(_tenant_dict(tenant)), 200

@api_bp.route('/tenants', methods=['POST'])
@jwt_required()
def create_tenant():
    data = request.get_json(silent=True) or {}
    room = Room.query.get(data.get('room_id'))
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    move_in = data.get('move_in_date')
    tenant = Tenant(
        room_id=room.id,
        name=data.get('name', ''),
        gender=data.get('gender'),
        nid=data.get('nid'),
        tel=data.get('tel'),
        emergency_contact_name=data.get('emergency_contact_name'),
        emergency_contact_tel=data.get('emergency_contact_tel'),
        num_roommates=data.get('num_roommates', 1),
        contract_duration=data.get('contract_duration', 'monthly'),
        move_in_date=date.fromisoformat(move_in) if move_in else None,
        deposit_paid=data.get('deposit_paid', 0),
        is_active=True,
    )
    room.status = 'occupied'
    room.updated_at = datetime.utcnow()
    db.session.add(tenant)
    db.session.commit()
    return jsonify(_tenant_dict(tenant)), 201

@api_bp.route('/tenants/<int:tenant_id>', methods=['PUT'])
@jwt_required()
def update_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    data = request.get_json(silent=True) or {}
    allowed = ['name', 'gender', 'nid', 'tel', 'emergency_contact_name',
               'emergency_contact_tel', 'num_roommates', 'contract_duration',
               'move_in_date', 'deposit_paid']
    for field in allowed:
        if field in data:
            val = data[field]
            if field == 'move_in_date' and val:
                val = date.fromisoformat(val)
            setattr(tenant, field, val)
    tenant.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_tenant_dict(tenant)), 200

@api_bp.route('/tenants/<int:tenant_id>/checkout', methods=['POST'])
@jwt_required()
def checkout_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    if not tenant.is_active:
        return jsonify({'error': 'Tenant already checked out'}), 400
    outstanding_count = Receipt.query.filter_by(room_id=tenant.room_id).filter(
        Receipt.remaining_balance > 0,
        Receipt.payment_status.in_(['unpaid', 'partial'])
    ).count()
    if outstanding_count > 0:
        return jsonify({
            'error': 'Cannot check out — there are still outstanding balances. Pay or write off first.',
            'outstanding_count': outstanding_count
        }), 400
    data = request.get_json(silent=True) or {}
    move_out = data.get('move_out_date')
    history = TenantHistory(
        room_id=tenant.room_id,
        name=tenant.name, gender=tenant.gender, nid=tenant.nid, tel=tenant.tel,
        num_roommates=tenant.num_roommates,
        move_in_date=tenant.move_in_date,
        move_out_date=date.fromisoformat(move_out) if move_out else date.today(),
        move_out_reason=data.get('move_out_reason', ''),
        deposit_paid=tenant.deposit_paid,
        deposit_refunded=data.get('deposit_refunded', 0),
    )
    tenant.is_active = False
    tenant.updated_at = datetime.utcnow()
    room = Room.query.get(tenant.room_id)
    if room:
        room.status = 'available'
        room.updated_at = datetime.utcnow()
    db.session.add(history)
    db.session.commit()
    backup_to_drive()
    return jsonify({'msg': 'Checked out successfully'}), 200


@api_bp.route('/tenants/<int:tenant_id>/write-off', methods=['POST'])
@jwt_required()
def write_off_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404
    outstanding = Receipt.query.filter_by(room_id=tenant.room_id).filter(
        Receipt.remaining_balance > 0,
        Receipt.payment_status.in_(['unpaid', 'partial'])
    ).all()
    for receipt in outstanding:
        receipt.notes = ((receipt.notes or '') + ' [Written off at checkout]').strip()
        receipt.remaining_balance = 0.0
        receipt.payment_status = 'paid'
    db.session.commit()
    backup_to_drive()
    return jsonify({'msg': f'{len(outstanding)} receipt(s) written off', 'count': len(outstanding)}), 200
