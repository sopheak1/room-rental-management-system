from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Room, Tenant, TenantHistory
from app import db
from datetime import date

tenants_bp = Blueprint('tenants', __name__)


@tenants_bp.route('/rooms/<int:room_id>/tenant/add', methods=['GET', 'POST'])
@login_required
def add(room_id):
    room = Room.query.get_or_404(room_id)
    if room.active_tenant:
        flash('Room already has an active tenant. Check out first. / បន្ទប់នេះមានអ្នកជួលហើយ។', 'warning')
        return redirect(url_for('rooms.detail', id=room_id))

    if request.method == 'POST':
        try:
            move_in_date = date.fromisoformat(request.form['move_in_date'])
        except (ValueError, KeyError):
            move_in_date = date.today()

        tenant = Tenant(
            room_id=room_id,
            name=request.form.get('name', '').strip(),
            gender=request.form.get('gender', ''),
            nid=request.form.get('nid', '').strip(),
            tel=request.form.get('tel', '').strip(),
            emergency_contact_name=request.form.get('emergency_contact_name', '').strip(),
            emergency_contact_tel=request.form.get('emergency_contact_tel', '').strip(),
            num_roommates=int(request.form.get('num_roommates') or 1),
            contract_duration=request.form.get('contract_duration', 'monthly'),
            move_in_date=move_in_date,
            deposit_paid=float(request.form.get('deposit_paid') or 0),
            is_active=True
        )
        room.status = 'occupied'
        db.session.add(tenant)
        db.session.commit()
        flash('Tenant added successfully. / អ្នកជួលត្រូវបានបន្ថែមជោគជ័យ។', 'success')
        return redirect(url_for('rooms.detail', id=room_id))

    return render_template('tenants/form.html', room=room, tenant=None)


@tenants_bp.route('/tenants/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    tenant = Tenant.query.get_or_404(id)
    room = tenant.room

    if request.method == 'POST':
        tenant.name = request.form.get('name', '').strip()
        tenant.gender = request.form.get('gender', '')
        tenant.nid = request.form.get('nid', '').strip()
        tenant.tel = request.form.get('tel', '').strip()
        tenant.emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        tenant.emergency_contact_tel = request.form.get('emergency_contact_tel', '').strip()
        tenant.num_roommates = int(request.form.get('num_roommates') or 1)
        tenant.contract_duration = request.form.get('contract_duration', 'monthly')
        tenant.deposit_paid = float(request.form.get('deposit_paid') or 0)
        move_in_str = request.form.get('move_in_date', '').strip()
        if move_in_str:
            try:
                tenant.move_in_date = date.fromisoformat(move_in_str)
            except ValueError:
                pass
        db.session.commit()
        flash('Tenant updated. / ធ្វើបច្ចុប្បន្នភាពអ្នកជួលបានជោគជ័យ។', 'success')
        return redirect(url_for('rooms.detail', id=room.id))

    return render_template('tenants/form.html', room=room, tenant=tenant)


@tenants_bp.route('/tenants/<int:id>/checkout', methods=['POST'])
@login_required
def checkout(id):
    tenant = Tenant.query.get_or_404(id)
    room = tenant.room

    try:
        move_out_date = date.fromisoformat(request.form['move_out_date'])
    except (ValueError, KeyError):
        move_out_date = date.today()

    history = TenantHistory(
        room_id=room.id,
        name=tenant.name,
        gender=tenant.gender,
        nid=tenant.nid,
        tel=tenant.tel,
        num_roommates=tenant.num_roommates,
        move_in_date=tenant.move_in_date,
        move_out_date=move_out_date,
        move_out_reason=request.form.get('move_out_reason', '').strip(),
        deposit_paid=tenant.deposit_paid,
        deposit_refunded=float(request.form.get('deposit_refunded') or 0)
    )
    tenant.is_active = False
    room.status = 'available'
    db.session.add(history)
    db.session.commit()
    flash('Tenant checked out. / អ្នកជួលចេញបានជោគជ័យ។', 'success')
    return redirect(url_for('rooms.detail', id=room.id))
