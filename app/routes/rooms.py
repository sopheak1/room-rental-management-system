from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Room, Building, Receipt, TenantHistory
from app import db
from datetime import date

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route('/rooms')
@login_required
def list():
    building_id = request.args.get('building_id', type=int)
    status = request.args.get('status', '')
    query = Room.query
    if building_id:
        query = query.filter_by(building_id=building_id)
    if status:
        query = query.filter_by(status=status)
    rooms = query.order_by(Room.room_number).all()
    buildings = Building.query.order_by(Building.name).all()
    return render_template('rooms/list.html', rooms=rooms, buildings=buildings,
                           selected_building=building_id, selected_status=status)


@rooms_bp.route('/rooms/new', methods=['GET', 'POST'])
@login_required
def new():
    buildings = Building.query.order_by(Building.name).all()
    if not buildings:
        flash('Please create a building first. / សូមបង្កើតអគារជាមុនសិន។', 'warning')
        return redirect(url_for('buildings.new'))

    if request.method == 'POST':
        try:
            room = Room(
                building_id=int(request.form['building_id']),
                room_number=request.form['room_number'].strip(),
                floor=int(request.form.get('floor') or 1),
                room_type=request.form.get('room_type', 'single'),
                price=float(request.form['price']),
                deposit_amount=float(request.form.get('deposit_amount') or 0),
                status='available'
            )
            db.session.add(room)
            db.session.commit()
            flash('Room created successfully. / បន្ទប់ត្រូវបានបង្កើតជោគជ័យ។', 'success')
            return redirect(url_for('rooms.list'))
        except (ValueError, KeyError):
            flash('Invalid input. Please check all fields.', 'danger')

    return render_template('rooms/form.html', room=None, buildings=buildings)


@rooms_bp.route('/rooms/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    room = Room.query.get_or_404(id)
    buildings = Building.query.order_by(Building.name).all()

    if request.method == 'POST':
        try:
            room.building_id = int(request.form['building_id'])
            room.room_number = request.form['room_number'].strip()
            room.floor = int(request.form.get('floor') or 1)
            room.room_type = request.form.get('room_type', 'single')
            room.price = float(request.form['price'])
            room.deposit_amount = float(request.form.get('deposit_amount') or 0)
            room.status = request.form.get('status', room.status)
            db.session.commit()
            flash('Room updated. / ធ្វើបច្ចុប្បន្នភាពបន្ទប់បានជោគជ័យ។', 'success')
            return redirect(url_for('rooms.detail', id=room.id))
        except (ValueError, KeyError):
            flash('Invalid input.', 'danger')

    return render_template('rooms/form.html', room=room, buildings=buildings)


@rooms_bp.route('/rooms/<int:id>')
@login_required
def detail(id):
    room = Room.query.get_or_404(id)
    history = TenantHistory.query.filter_by(room_id=id).order_by(TenantHistory.move_in_date.desc()).all()
    receipts = Receipt.query.filter_by(room_id=id).order_by(
        Receipt.billing_year.desc(), Receipt.billing_month.desc()).all()
    return render_template('rooms/detail.html', room=room, history=history, receipts=receipts, today=date.today())


@rooms_bp.route('/rooms/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    room = Room.query.get_or_404(id)
    if room.active_tenant:
        flash('Cannot delete room with active tenant. Check out tenant first.', 'danger')
        return redirect(url_for('rooms.list'))
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted. / លុបបន្ទប់បានជោគជ័យ។', 'success')
    return redirect(url_for('rooms.list'))
