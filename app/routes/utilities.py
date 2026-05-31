from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models import UtilityPrice
from app import db
from datetime import date

utilities_bp = Blueprint('utilities', __name__)


@utilities_bp.route('/utilities')
@login_required
def index():
    water_prices = UtilityPrice.query.filter_by(utility_type='water').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).all()
    electricity_prices = UtilityPrice.query.filter_by(utility_type='electricity').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).all()
    current_water = water_prices[0] if water_prices else None
    current_electricity = electricity_prices[0] if electricity_prices else None
    return render_template('utilities/index.html',
        water_prices=water_prices,
        electricity_prices=electricity_prices,
        current_water=current_water,
        current_electricity=current_electricity,
        today=date.today()
    )


@utilities_bp.route('/utilities/update', methods=['POST'])
@login_required
def update():
    utility_type = request.form.get('utility_type')
    price_str = request.form.get('price_per_unit')
    date_str = request.form.get('effective_date')

    if not all([utility_type, price_str, date_str]):
        flash('All fields are required. / ត្រូវការទិន្នន័យទាំងអស់។', 'danger')
        return redirect(url_for('utilities.index'))

    try:
        price = UtilityPrice(
            utility_type=utility_type,
            price_per_unit=float(price_str),
            effective_date=date.fromisoformat(date_str)
        )
        db.session.add(price)
        db.session.commit()
        flash('Utility price updated. / តម្លៃប្រើប្រាស់ត្រូវបានធ្វើបច្ចុប្បន្នភាព។', 'success')
    except ValueError:
        flash('Invalid price or date.', 'danger')

    return redirect(url_for('utilities.index'))


@utilities_bp.route('/utilities/current-prices')
@login_required
def current_prices():
    water = UtilityPrice.query.filter_by(utility_type='water').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    electricity = UtilityPrice.query.filter_by(utility_type='electricity').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    return jsonify({
        'water': water.price_per_unit if water else 0,
        'electricity': electricity.price_per_unit if electricity else 0
    })
