from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, session, current_app
from flask_login import login_required
from app.models import Receipt, Room, Tenant, UtilityPrice, Building, PaymentLog, UtilityUsage, PromisedPaymentLog
from app import db
from app.utils.timezone import now as _now, today as _today
from datetime import date, datetime
from app.utils.google_drive import backup_to_drive
from app.utils.verification import generate_payment_hash

receipts_bp = Blueprint('receipts', __name__)

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
KM_MONTHS = ['មករា','កុម្ភៈ','មីនា','មេសា','ឧសភា','មិថុនា',
             'កក្កដា','សីហា','កញ្ញា','តុលា','វិច្ឆិកា','ធ្នូ']


def _flash_lang(en, km, category='info'):
    """Flash a message in whichever language the user currently has selected,
    instead of showing both languages glued together."""
    flash(km if session.get('lang', 'km') == 'km' else en, category)


def _generate_receipt_number(year, month):
    count = Receipt.query.filter_by(billing_year=year, billing_month=month).count()
    return f"RCP-{year}{month:02d}-{count + 1:04d}"


def _has_next_receipt(receipt):
    """Check if a receipt for the next billing month already exists."""
    next_month = receipt.billing_month + 1
    next_year  = receipt.billing_year
    if next_month > 12:
        next_month = 1
        next_year += 1
    return Receipt.query.filter_by(
        room_id=receipt.room_id,
        billing_month=next_month,
        billing_year=next_year
    ).first() is not None


def _get_previous_receipt(room_id, year, month):
    return Receipt.query.filter(
        Receipt.room_id == room_id,
        db.or_(
            Receipt.billing_year < year,
            db.and_(Receipt.billing_year == year, Receipt.billing_month < month)
        )
    ).order_by(Receipt.billing_year.desc(), Receipt.billing_month.desc()).first()


@receipts_bp.route('/receipts')
@login_required
def list():
    now = _now()
    month = request.args.get('month', type=int, default=now.month)
    year = request.args.get('year', type=int, default=now.year)
    status = request.args.get('status', '')
    building_id = request.args.get('building_id', type=int)

    query = Receipt.query.filter_by(billing_month=month, billing_year=year)
    if status:
        query = query.filter_by(payment_status=status)
    if building_id:
        query = query.join(Room).filter(Room.building_id == building_id)

    receipts = query.order_by(Receipt.created_at.desc()).all()

    overdue = Receipt.query.filter(
        Receipt.payment_status.in_(['unpaid', 'partial']),
        db.or_(
            Receipt.billing_year < year,
            db.and_(Receipt.billing_year == year, Receipt.billing_month < month)
        )
    ).order_by(Receipt.billing_year, Receipt.billing_month).all()


    buildings = Building.query.order_by(Building.name).all()

    return render_template('receipts/list.html',
        receipts=receipts, overdue=overdue,
        buildings=buildings, month=month, year=year,
        selected_status=status, selected_building=building_id,
        month_names=MONTH_NAMES
    )


@receipts_bp.route('/receipts/verify')
@login_required
def verify():
    raw = (request.args.get('code') or '').strip().upper().replace(' ', '')
    code = raw
    if code and '-' not in code and len(code) == 8:
        code = f"{code[:4]}-{code[4:]}"

    if code:
        log = PaymentLog.query.filter_by(verification_hash=code).first()
        if log:
            return redirect(url_for('receipts.detail', id=log.receipt_id, highlight=log.id))
        _flash_lang('No payment found for this verification code.',
                    'រកមិនឃើញការទូទាត់សម្រាប់លេខកូដនេះទេ។', 'warning')

    return render_template('receipts/verify.html', code=raw)


@receipts_bp.route('/receipts/generate', methods=['GET', 'POST'])
@login_required
def generate():
    rooms = Room.query.filter_by(status='occupied').order_by(Room.room_number).all()
    water_price = UtilityPrice.query.filter_by(utility_type='water').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    electricity_price = UtilityPrice.query.filter_by(utility_type='electricity').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    default_fee = UtilityPrice.query.filter_by(utility_type='fee').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()

    if request.method == 'POST':
        room_id = int(request.form['room_id'])
        billing_month = int(request.form['billing_month'])
        billing_year = int(request.form['billing_year'])

        room = Room.query.get_or_404(room_id)
        tenant = room.active_tenant

        # Block duplicate only for the same tenant — different tenant (new move-in) is allowed
        existing = Receipt.query.filter_by(
            room_id=room_id, billing_month=billing_month, billing_year=billing_year,
            tenant_id=tenant.id if tenant else None
        ).first()
        if existing:
            _flash_lang('Receipt already exists for this room and month.',
                        'វិក័យប័ត្រនេះបានបង្កើតរួចហើយ។', 'warning')
            return redirect(url_for('receipts.detail', id=existing.id))

        # Electricity
        elec_override = request.form.get('electricity_override') == 'on'
        if elec_override:
            electricity_total = float(request.form.get('electricity_total_override') or 0)
            elec_from = elec_to = elec_units = elec_ppu = None
        else:
            elec_from = float(request.form.get('electricity_from') or 0)
            elec_to = float(request.form.get('electricity_to') or 0)
            elec_units = max(elec_to - elec_from, 0)
            elec_ppu = float(request.form.get('electricity_price_per_unit') or 0)
            electricity_total = round(elec_units * elec_ppu, 2)

        # Water
        water_override = request.form.get('water_override') == 'on'
        if water_override:
            water_total = float(request.form.get('water_total_override') or 0)
            w_from = w_to = w_units = w_ppu = None
        else:
            w_from = float(request.form.get('water_from') or 0)
            w_to = float(request.form.get('water_to') or 0)
            w_units = max(w_to - w_from, 0)
            w_ppu = float(request.form.get('water_price_per_unit') or 0)
            water_total = round(w_units * w_ppu, 2)

        previous_balance = float(request.form.get('previous_balance') or 0)
        fee = float(request.form.get('fee') or 0)
        late_fee = float(request.form.get('late_fee') or 0)
        discount = float(request.form.get('discount') or 0)

        total_amount = round(room.price + electricity_total + water_total + previous_balance + fee + late_fee - discount, 2)

        payment_status = request.form.get('payment_status', 'unpaid')
        paid_amount = float(request.form.get('paid_amount') or 0)

        if payment_status == 'paid':
            paid_amount = total_amount
            remaining_balance = 0.0
        elif payment_status == 'partial':
            remaining_balance = round(max(total_amount - paid_amount, 0), 2)
        else:
            paid_amount = 0.0
            remaining_balance = total_amount

        payment_date_str = request.form.get('payment_date')
        payment_date = date.fromisoformat(payment_date_str) if payment_date_str else None

        receipt = Receipt(
            receipt_number=_generate_receipt_number(billing_year, billing_month),
            room_id=room_id,
            tenant_id=tenant.id if tenant else None,
            billing_month=billing_month,
            billing_year=billing_year,
            room_price=room.price,
            electricity_from=elec_from,
            electricity_to=elec_to,
            electricity_units=elec_units,
            electricity_price_per_unit=elec_ppu,
            electricity_total=electricity_total,
            water_from=w_from,
            water_to=w_to,
            water_units=w_units,
            water_price_per_unit=w_ppu,
            water_total=water_total,
            previous_balance=previous_balance,
            fee=fee,
            late_fee=late_fee,
            discount=discount,
            total_amount=total_amount,
            paid_amount=paid_amount,
            remaining_balance=remaining_balance,
            payment_status=payment_status,
            payment_method=request.form.get('payment_method') or None,
            payment_date=payment_date,
            notes=request.form.get('notes', '').strip() or None
        )
        db.session.add(receipt)
        db.session.commit()
        backup_to_drive()
        _flash_lang(f'Receipt {receipt.receipt_number} generated.',
                    f'វិក័យប័ត្រ {receipt.receipt_number} ត្រូវបានបង្កើតជោគជ័យ។', 'success')
        return redirect(url_for('receipts.detail', id=receipt.id))

    now = _now()
    room_id = request.args.get('room_id', type=int)
    billing_month = request.args.get('billing_month', type=int, default=now.month)
    billing_year = request.args.get('billing_year', type=int, default=now.year)
    selected_room = Room.query.get(room_id) if room_id else None
    prev_receipt = _get_previous_receipt(room_id, billing_year, billing_month) if room_id else None

    # Pre-fill from a staged batch reading, if the user already recorded one for this room/period.
    # This is read-only — generating the receipt never writes back to UtilityUsage.
    usage = UtilityUsage.query.filter_by(
        room_id=room_id, billing_month=billing_month, billing_year=billing_year
    ).first() if room_id else None

    # Don't carry over balance from a previous tenant — only meter readings transfer
    active_tenant = selected_room.active_tenant if selected_room else None
    same_tenant = (
        prev_receipt and active_tenant and
        prev_receipt.tenant_id == active_tenant.id
    )
    prev_balance = prev_receipt.remaining_balance if (prev_receipt and same_tenant) else 0

    # Warn upfront if this tenant already has a receipt for the selected month
    existing_receipt = Receipt.query.filter_by(
        room_id=room_id,
        billing_month=billing_month,
        billing_year=billing_year,
        tenant_id=active_tenant.id if active_tenant else None
    ).first() if room_id else None

    return render_template('receipts/generate.html',
        rooms=rooms,
        selected_room=selected_room,
        prev_receipt=prev_receipt,
        usage=usage,
        prev_balance=prev_balance,
        existing_receipt=existing_receipt,
        water_price=water_price,
        electricity_price=electricity_price,
        default_fee=default_fee,
        today=_today(),
        now=now,
        billing_month=billing_month,
        billing_year=billing_year,
        month_names=MONTH_NAMES,
        KM_MONTHS=KM_MONTHS
    )


@receipts_bp.route('/receipts/<int:id>')
@login_required
def detail(id):
    receipt = Receipt.query.get_or_404(id)
    current_app.logger.info(
        '[receipts.detail] QUERY id=%s status=%s total_amount=%s paid_amount=%s remaining_balance=%s',
        receipt.id, receipt.payment_status, receipt.total_amount,
        receipt.paid_amount, receipt.remaining_balance
    )
    return render_template('receipts/detail.html', receipt=receipt,
                           today=_today(), locked=_has_next_receipt(receipt))


@receipts_bp.route('/receipts/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    receipt = Receipt.query.get_or_404(id)
    current_app.logger.info(
        '[receipts.pay] REQUEST id=%s form=%s', receipt.id, dict(request.form)
    )
    current_app.logger.info(
        '[receipts.pay] BEFORE id=%s status=%s total_amount=%s paid_amount=%s remaining_balance=%s',
        receipt.id, receipt.payment_status, receipt.total_amount,
        receipt.paid_amount, receipt.remaining_balance
    )

    new_payment = float(request.form.get('paid_amount') or 0)
    payment_method = request.form.get('payment_method')
    date_str = request.form.get('payment_date')
    payment_date = date.fromisoformat(date_str) if date_str else _today()

    receipt.paid_amount = round(receipt.paid_amount + new_payment, 2)
    receipt.payment_method = payment_method
    receipt.payment_date = payment_date
    receipt.remaining_balance = round(max(receipt.total_amount - receipt.paid_amount, 0), 2)

    if receipt.paid_amount >= receipt.total_amount:
        receipt.payment_status = 'paid'
        receipt.remaining_balance = 0.0
    elif receipt.paid_amount > 0:
        receipt.payment_status = 'partial'
    else:
        receipt.payment_status = 'unpaid'

    log = PaymentLog(
        receipt_id=receipt.id,
        amount=new_payment,
        payment_method=payment_method,
        payment_date=payment_date,
        verification_hash=generate_payment_hash(
            receipt.receipt_number, receipt.remaining_balance, new_payment, payment_date, payment_method
        )
    )
    db.session.add(log)
    db.session.commit()
    backup_to_drive()

    current_app.logger.info(
        '[receipts.pay] AFTER id=%s status=%s total_amount=%s paid_amount=%s remaining_balance=%s new_payment=%s',
        receipt.id, receipt.payment_status, receipt.total_amount,
        receipt.paid_amount, receipt.remaining_balance, new_payment
    )
    current_app.logger.info(
        '[receipts.pay] RESPONSE id=%s redirect -> receipts.detail', receipt.id
    )

    _flash_lang('Payment recorded.', 'ការទូទាត់ត្រូវបានកត់ត្រា។', 'success')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/payment-log/<int:log_id>/delete', methods=['POST'])
@login_required
def delete_payment_log(id, log_id):
    receipt = Receipt.query.get_or_404(id)
    log     = PaymentLog.query.get_or_404(log_id)

    if _has_next_receipt(receipt):
        _flash_lang('Cannot delete payment — a receipt for the next month already exists.',
                    'មិនអាចលុប — វិក័យប័ត្រខែក្រោយបានបង្កើតហើយ។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    # Safety: only allow deleting the LAST active (non-deleted) payment log entry
    last_log = PaymentLog.query.filter_by(receipt_id=id, deleted_at=None)\
                               .order_by(PaymentLog.created_at.desc()).first()
    if not last_log or last_log.id != log_id:
        flash('Only the last payment can be deleted.', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    reason_code  = (request.form.get('delete_reason_code') or '').strip()
    reason_other = (request.form.get('delete_reason_other') or '').strip()
    if reason_code == 'other':
        delete_reason = reason_other
    else:
        delete_reason = reason_code

    if not delete_reason:
        _flash_lang('Please select a reason for deleting this payment.',
                    'សូមជ្រើសរើសមូលហេតុនៃការលុប។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    # Recalculate paid amount and balance
    receipt.paid_amount       = round(max(receipt.paid_amount - log.amount, 0), 2)
    receipt.remaining_balance = round(receipt.total_amount - receipt.paid_amount, 2)

    if receipt.paid_amount <= 0:
        receipt.payment_status = 'unpaid'
    elif receipt.paid_amount < receipt.total_amount:
        receipt.payment_status = 'partial'
    else:
        receipt.payment_status = 'paid'
        receipt.remaining_balance = 0.0

    log.deleted_at    = _now()
    log.delete_reason = delete_reason
    db.session.commit()
    backup_to_drive()
    _flash_lang('Payment deleted and balance updated.', 'ការទូទាត់ត្រូវបានលុប។', 'success')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/promise', methods=['POST'])
@login_required
def add_promise(id):
    receipt = Receipt.query.get_or_404(id)

    if _has_next_receipt(receipt):
        _flash_lang('Cannot set a promise — a receipt for the next month already exists.',
                    'មិនអាចកំណត់ — វិក័យប័ត្រខែក្រោយបានបង្កើតហើយ។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    promised_date_str = request.form.get('promised_date')
    if not promised_date_str:
        _flash_lang('Promised date is required.', 'សូមបញ្ចូលកាលបរិច្ឆេទសន្យា។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    promised_date = date.fromisoformat(promised_date_str)
    if promised_date < _today():
        _flash_lang('Promised date cannot be in the past.', 'កាលបរិច្ឆេទសន្យាមិនអាចជាថ្ងៃកន្លងហើយបានទេ។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    log = PromisedPaymentLog(
        receipt_id=id,
        promised_date=promised_date,
        notes=request.form.get('notes', '').strip() or None
    )
    db.session.add(log)
    # A promise lives in promised_payment_logs, not on the receipts row itself,
    # so the column's onupdate=datetime.utcnow never fires on its own — bump it
    # explicitly so mobile's delta sync (filtered by Receipt.updated_at) notices.
    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    backup_to_drive()
    _flash_lang('Promised date recorded.', 'កាលបរិច្ឆេទសន្យាត្រូវបានកត់ត្រា។', 'success')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/defer', methods=['POST'])
@login_required
def defer_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    receipt.payment_status = 'deferred'
    db.session.commit()
    _flash_lang('Balance deferred to next month. It will carry over automatically.',
                'សមតុល្យត្រូវបានពន្យារដល់ខែក្រោយ។', 'info')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/undefer', methods=['POST'])
@login_required
def undefer_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    receipt.payment_status = 'partial' if receipt.paid_amount > 0 else 'unpaid'
    db.session.commit()
    flash('Receipt restored to active status.', 'info')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_receipt(id):
    receipt = Receipt.query.get_or_404(id)

    if _has_next_receipt(receipt):
        _flash_lang('Cannot edit — a receipt for the next month already exists and carries this balance.',
                    'មិនអាចកែប្រែ — វិក័យប័ត្រខែក្រោយបានបង្កើតហើយ។', 'danger')
        return redirect(url_for('receipts.detail', id=id))

    if request.method == 'POST':
        elec_override = receipt.electricity_units is None
        water_override = receipt.water_units is None

        # Recalculate totals from form
        if elec_override:
            electricity_total = float(request.form.get('electricity_total') or 0)
            elec_from = elec_to = elec_units = elec_ppu = None
        else:
            elec_from = float(request.form.get('electricity_from') or 0)
            elec_to   = float(request.form.get('electricity_to') or 0)
            elec_units = max(elec_to - elec_from, 0)
            elec_ppu   = float(request.form.get('electricity_price_per_unit') or 0)
            electricity_total = round(elec_units * elec_ppu, 2)

        if water_override:
            water_total = float(request.form.get('water_total') or 0)
            w_from = w_to = w_units = w_ppu = None
        else:
            w_from  = float(request.form.get('water_from') or 0)
            w_to    = float(request.form.get('water_to') or 0)
            w_units = max(w_to - w_from, 0)
            w_ppu   = float(request.form.get('water_price_per_unit') or 0)
            water_total = round(w_units * w_ppu, 2)

        room_price       = float(request.form.get('room_price') or 0)
        previous_balance = float(request.form.get('previous_balance') or 0)
        fee              = float(request.form.get('fee') or 0)
        late_fee         = float(request.form.get('late_fee') or 0)
        discount         = float(request.form.get('discount') or 0)
        notes            = request.form.get('notes', '').strip() or None

        new_total = round(room_price + electricity_total + water_total + previous_balance + fee + late_fee - discount, 2)

        # Option 3: block if new total < already paid
        if new_total < receipt.paid_amount:
            flash(f'Cannot reduce total below paid amount ({receipt.paid_amount:,.0f} ៛). Adjust paid amount first.', 'danger')
            return redirect(url_for('receipts.edit_receipt', id=id))

        # Apply changes
        receipt.room_price            = room_price
        receipt.electricity_total     = electricity_total
        receipt.electricity_from      = elec_from
        receipt.electricity_to        = elec_to
        receipt.electricity_units     = elec_units
        receipt.electricity_price_per_unit = elec_ppu
        receipt.water_total           = water_total
        receipt.water_from            = w_from
        receipt.water_to              = w_to
        receipt.water_units           = w_units
        receipt.water_price_per_unit  = w_ppu
        receipt.previous_balance      = previous_balance
        receipt.fee                   = fee
        receipt.late_fee              = late_fee
        receipt.discount              = discount
        receipt.notes                 = notes
        receipt.total_amount          = new_total
        receipt.remaining_balance     = round(max(new_total - receipt.paid_amount, 0), 2)

        if receipt.paid_amount >= new_total:
            receipt.payment_status = 'paid'
            receipt.remaining_balance = 0.0
        elif receipt.paid_amount > 0:
            receipt.payment_status = 'partial'
        else:
            receipt.payment_status = 'unpaid'

        db.session.commit()
        backup_to_drive()
        _flash_lang('Receipt updated successfully.', 'វិក័យប័ត្រត្រូវបានកែប្រែ។', 'success')
        return redirect(url_for('receipts.detail', id=id))

    water_price       = UtilityPrice.query.filter_by(utility_type='water').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    electricity_price = UtilityPrice.query.filter_by(utility_type='electricity').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()
    default_fee       = UtilityPrice.query.filter_by(utility_type='fee').order_by(
        UtilityPrice.effective_date.desc(), UtilityPrice.id.desc()).first()

    return render_template('receipts/edit.html',
        receipt=receipt,
        water_price=water_price,
        electricity_price=electricity_price,
        default_fee=default_fee,
        today=_today()
    )


@receipts_bp.route('/receipts/<int:id>/print_table')
@login_required
def print_table(id):
    """Traditional Khmer table-style receipt — 58mm thermal, browser or PT-210."""
    receipt = Receipt.query.get_or_404(id)
    bridge = request.args.get('bridge') == '1'
    KM_MONTHS = ['មករា','កុម្ភៈ','មីនា','មេសា','ឧសភា','មិថុនា',
                 'កក្កដា','សីហា','កញ្ញា','តុលា','វិច្ឆិកា','ធ្នូ']
    return render_template('receipts/print_table.html',
                           receipt=receipt, KM_MONTHS=KM_MONTHS, bridge=bridge)


@receipts_bp.route('/receipts/<int:id>/escpos')
@login_required
def escpos(id):
    """Render receipt as ESC/POS bitmap for the Android Print Bridge."""
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageOps
    from escpos.printer import File as FilePrinter
    import io, tempfile, os

    receipt = Receipt.query.get_or_404(id)

    # --- 1. Render print_table.html to PNG via headless Chrome ---
    print_url = url_for('receipts.print_table', id=id, _external=True)
    # Add ?bridge=1 so the page can hide the toolbar
    print_url += '?bridge=1'

    # PT-210 print width: 48mm at 203 DPI = 384 dots
    PRINTER_DOTS = 384

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Set viewport to exactly match the CSS body width (58mm at 96 DPI ≈ 219px)
        # Use device_scale_factor=2 for sharper rendering, then scale down
        page = browser.new_page(
            viewport={'width': 220, 'height': 2000},
            device_scale_factor=2
        )
        cookies = [{'name': k, 'value': v, 'url': print_url}
                   for k, v in request.cookies.items()]
        page.context.add_cookies(cookies)
        page.goto(print_url, wait_until='networkidle')
        img_bytes = page.screenshot(type='png', full_page=True)
        browser.close()

    # --- 2. Convert to greyscale, crop content, scale to full printer width ---
    img = Image.open(io.BytesIO(img_bytes)).convert('L')

    # Crop white margins: find bounding box of non-white pixels
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        # Keep full width, add generous bottom padding so cutter clears last line
        img = img.crop((0, 0, img.width, min(bbox[3] + 60, img.height)))

    # Scale to exactly PRINTER_DOTS wide — fills the full 48mm print area
    new_height = int(img.height * PRINTER_DOTS / img.width)
    img = img.resize((PRINTER_DOTS, new_height), Image.LANCZOS)

    # Convert to 1-bit (black & white) with threshold
    img = img.point(lambda x: 0 if x < 180 else 255, '1')

    # --- 3. Build ESC/POS bytes ---
    buf = io.BytesIO()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        tmp_path = tmp.name

    try:
        printer = FilePrinter(tmp_path)
        printer.set_with_default()
        printer.image(img, impl='bitImageRaster')
        printer.cut()
        printer.close()
        with open(tmp_path, 'rb') as f:
            escpos_bytes = f.read()
    finally:
        os.unlink(tmp_path)

    return Response(
        escpos_bytes,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="receipt_{id}.bin"',
                 'Access-Control-Allow-Origin': '*'}
    )
