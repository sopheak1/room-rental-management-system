from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Building
from app import db

buildings_bp = Blueprint('buildings', __name__)


@buildings_bp.route('/buildings')
@login_required
def list():
    buildings = Building.query.order_by(Building.name).all()
    return render_template('buildings/list.html', buildings=buildings)


@buildings_bp.route('/buildings/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        if not name:
            flash('Building name is required.', 'danger')
            return render_template('buildings/form.html', building=None)
        db.session.add(Building(name=name, address=address))
        db.session.commit()
        flash('Building created successfully. / បង្កើតអគារបានជោគជ័យ។', 'success')
        return redirect(url_for('buildings.list'))
    return render_template('buildings/form.html', building=None)


@buildings_bp.route('/buildings/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    building = Building.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        if not name:
            flash('Building name is required.', 'danger')
            return render_template('buildings/form.html', building=building)
        building.name = name
        building.address = address
        db.session.commit()
        flash('Building updated. / ធ្វើបច្ចុប្បន្នភាពអគារបានជោគជ័យ។', 'success')
        return redirect(url_for('buildings.list'))
    return render_template('buildings/form.html', building=building)


@buildings_bp.route('/buildings/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    building = Building.query.get_or_404(id)
    if building.rooms:
        flash('Cannot delete building with rooms. Remove all rooms first. / មិនអាចលុបអគារដែលមានបន្ទប់បានទេ។', 'danger')
        return redirect(url_for('buildings.list'))
    db.session.delete(building)
    db.session.commit()
    flash('Building deleted. / លុបអគារបានជោគជ័យ។', 'success')
    return redirect(url_for('buildings.list'))
