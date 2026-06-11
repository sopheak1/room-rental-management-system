from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Room, Building, Receipt
from app import db
from app.utils.timezone import now as _now, today as _today
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    now = _now()
    current_month = now.month
    current_year = now.year
    today_day = now.day

    total_rooms = Room.query.count()
    occupied_count = Room.query.filter_by(status='occupied').count()
    vacant_rooms = Room.query.filter_by(status='available').count()

    monthly_receipts = Receipt.query.filter_by(
        billing_month=current_month, billing_year=current_year
    ).all()
    total_expected = sum(r.total_amount for r in monthly_receipts)
    total_collected = sum(r.paid_amount for r in monthly_receipts)

    overdue_count = Receipt.query.filter(
        Receipt.payment_status.in_(['unpaid', 'partial']),
        db.or_(
            Receipt.billing_year < current_year,
            db.and_(Receipt.billing_year == current_year, Receipt.billing_month < current_month)
        )
    ).count()


    recent_payments = Receipt.query.filter(
        Receipt.payment_status.in_(['paid', 'partial']),
        Receipt.payment_date.isnot(None)
    ).order_by(Receipt.payment_date.desc()).limit(8).all()

    # This month payment status per room
    occupied_rooms = Room.query.join(Building).filter(Room.status == 'occupied') \
        .order_by(Building.name, Room.room_number).all()
    month_status = []
    for room in occupied_rooms:
        tenant = room.active_tenant
        if not tenant or not tenant.move_in_date:
            continue
        receipt = Receipt.query.filter_by(
            room_id=room.id, billing_year=current_year, billing_month=current_month
        ).first()
        start_day = tenant.move_in_date.day
        if receipt and receipt.payment_status == 'paid':
            status = 'paid'
        elif receipt and receipt.payment_status == 'deferred':
            status = 'deferred'
        elif today_day >= start_day:
            status = 'overdue'
        else:
            status = 'upcoming'
        month_status.append({
            'room': room, 'tenant': tenant,
            'receipt': receipt, 'start_day': start_day, 'status': status
        })

    KM_MONTHS = ['មករា','កុម្ភៈ','មីនា','មេសា','ឧសភា','មិថុនា',
                 'កក្កដា','សីហា','កញ្ញា','តុលា','វិច្ឆិកា','ធ្នូ']
    EN_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    # Split month_status into tabs — only rooms WITH a receipt
    tab_overdue  = [e for e in month_status if e['status'] == 'overdue']
    tab_upcoming = [e for e in month_status if e['status'] == 'upcoming']
    tab_paid     = [e for e in month_status if e['status'] == 'paid'     and e['receipt']]

    return render_template('dashboard.html',
        total_rooms=total_rooms,
        occupied_rooms=occupied_count,
        vacant_rooms=vacant_rooms,
        total_expected=total_expected,
        total_collected=total_collected,
        overdue_count=overdue_count,
        recent_payments=recent_payments,
        month_status=month_status,
        tab_overdue=tab_overdue,
        tab_upcoming=tab_upcoming,
        tab_paid=tab_paid,
        current_month=current_month,
        current_year=current_year,
        KM_MONTHS=KM_MONTHS,
        MONTH_NAMES=EN_MONTHS
    )
