from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import Receipt, Room, Building
from app import db
from datetime import datetime

reports_bp = Blueprint('reports', __name__)

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


@reports_bp.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')


@reports_bp.route('/reports/breakdown')
@login_required
def breakdown():
    now = datetime.now()
    month = request.args.get('month', type=int, default=now.month)
    year  = request.args.get('year',  type=int, default=now.year)

    receipts = Receipt.query.filter_by(billing_month=month, billing_year=year).all()

    data = {
        'room_fee':          sum(r.room_price              for r in receipts),
        'electricity_units': sum((r.electricity_units or 0) for r in receipts),
        'electricity_fee':   sum(r.electricity_total        for r in receipts),
        'water_units':       sum((r.water_units or 0)       for r in receipts),
        'water_fee':         sum(r.water_total              for r in receipts),
        'service_fee':       sum((r.fee or 0)               for r in receipts),
        'credit':            sum(r.paid_amount              for r in receipts),
        'credit_balance':    sum(r.remaining_balance        for r in receipts if r.payment_status != 'deferred'),
        'deferred':          sum(r.remaining_balance        for r in receipts if r.payment_status == 'deferred'),
        'total_expected':    sum(r.total_amount             for r in receipts),
        'count':             len(receipts),
    }

    KM_MONTHS = ['មករា','កុម្ភៈ','មីនា','មេសា','ឧសភា','មិថុនា',
                 'កក្កដា','សីហា','កញ្ញា','តុលា','វិច្ឆិកា','ធ្នូ']

    return render_template('reports/breakdown.html',
        data=data, month=month, year=year,
        KM_MONTHS=KM_MONTHS, MONTH_NAMES=MONTH_NAMES, now=now
    )


@reports_bp.route('/reports/summary')
@login_required
def summary():
    now = datetime.now()
    month = request.args.get('month', type=int, default=now.month)
    year  = request.args.get('year',  type=int, default=now.year)

    receipts = Receipt.query.filter_by(
        billing_month=month, billing_year=year
    ).order_by(Receipt.created_at.desc()).all()

    total_expected   = sum(r.total_amount       for r in receipts)
    total_collected  = sum(r.paid_amount        for r in receipts)
    total_outstanding= sum(r.remaining_balance  for r in receipts)
    collection_rate  = round(total_collected / total_expected * 100, 1) if total_expected > 0 else 0

    by_status = {
        'paid':     [r for r in receipts if r.payment_status == 'paid'],
        'partial':  [r for r in receipts if r.payment_status == 'partial'],
        'unpaid':   [r for r in receipts if r.payment_status == 'unpaid'],
        'deferred': [r for r in receipts if r.payment_status == 'deferred'],
    }

    KM_MONTHS = ['មករា','កុម្ភៈ','មីនា','មេសា','ឧសភា','មិថុនា',
                 'កក្កដា','សីហា','កញ្ញា','តុលា','វិច្ឆិកា','ធ្នូ']

    return render_template('reports/summary.html',
        receipts=receipts,
        month=month, year=year,
        total_expected=total_expected,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        collection_rate=collection_rate,
        by_status=by_status,
        KM_MONTHS=KM_MONTHS,
        MONTH_NAMES=MONTH_NAMES,
        now=now
    )


@reports_bp.route('/reports/revenue')
@login_required
def revenue():
    year = request.args.get('year', type=int, default=datetime.now().year)
    monthly_data = []
    for m in range(1, 13):
        receipts = Receipt.query.filter_by(billing_year=year, billing_month=m).all()
        expected = sum(r.total_amount for r in receipts)
        collected = sum(r.paid_amount for r in receipts)
        monthly_data.append({
            'month': m,
            'month_name': MONTH_NAMES[m - 1],
            'expected': expected,
            'collected': collected,
            'outstanding': round(expected - collected, 2),
            'count': len(receipts)
        })
    return render_template('reports/revenue.html', monthly_data=monthly_data, year=year)


@reports_bp.route('/reports/overdue')
@login_required
def overdue():
    from app.models import Room
    now = datetime.now()
    today_day = now.day

    # Past months: unpaid/partial receipts before current month (deferred excluded)
    past_overdue = Receipt.query.filter(
        Receipt.payment_status.in_(['unpaid', 'partial']),
        db.or_(
            Receipt.billing_year < now.year,
            db.and_(Receipt.billing_year == now.year, Receipt.billing_month < now.month)
        )
    ).order_by(Receipt.billing_year, Receipt.billing_month).all()

    # Current month: check every occupied room
    occupied_rooms = Room.query.filter_by(status='occupied').order_by(Room.room_number).all()
    current_overdue = []   # past start date, not settled
    current_upcoming = []  # start date not reached yet

    for room in occupied_rooms:
        tenant = room.active_tenant
        if not tenant or not tenant.move_in_date:
            continue  # no tenant or unknown start date

        receipt = Receipt.query.filter_by(
            room_id=room.id,
            billing_year=now.year,
            billing_month=now.month
        ).first()

        # Skip rooms fully paid or deferred this month
        if receipt and receipt.payment_status in ('paid', 'deferred'):
            continue

        start_day = tenant.move_in_date.day
        is_past_due = today_day >= start_day
        entry = {'room': room, 'tenant': tenant, 'receipt': receipt, 'start_day': start_day}

        if is_past_due:
            current_overdue.append(entry)
        else:
            current_upcoming.append(entry)

    return render_template('reports/overdue.html',
        past_overdue=past_overdue,
        current_overdue=current_overdue,
        current_upcoming=current_upcoming,
        now=now,
        today_day=today_day
    )


@reports_bp.route('/reports/occupancy')
@login_required
def occupancy():
    buildings = Building.query.all()
    data = []
    for b in buildings:
        total = len(b.rooms)
        occupied = sum(1 for r in b.rooms if r.status == 'occupied')
        vacant = sum(1 for r in b.rooms if r.status == 'available')
        maintenance = sum(1 for r in b.rooms if r.status == 'maintenance')
        data.append({
            'building': b,
            'total': total,
            'occupied': occupied,
            'vacant': vacant,
            'maintenance': maintenance,
            'rate': round(occupied / total * 100, 1) if total > 0 else 0
        })
    return render_template('reports/occupancy.html', data=data)
