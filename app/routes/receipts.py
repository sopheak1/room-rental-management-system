from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required
from app.models import Receipt, Room, Tenant, UtilityPrice, Building, PaymentLog
from app import db
from datetime import date, datetime
from app.utils.google_drive import backup_to_drive

receipts_bp = Blueprint('receipts', __name__)

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


def _generate_receipt_number(year, month):
    count = Receipt.query.filter_by(billing_year=year, billing_month=month).count()
    return f"RCP-{year}{month:02d}-{count + 1:04d}"


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
    now = datetime.now()
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

        existing = Receipt.query.filter_by(
            room_id=room_id, billing_month=billing_month, billing_year=billing_year
        ).first()
        if existing:
            flash('វិក័យប័ត្រនេះបានបង្កើតរួចហើយ។ / Receipt already exists for this room and month.', 'warning')
            return redirect(url_for('receipts.detail', id=existing.id))

        room = Room.query.get_or_404(room_id)
        tenant = room.active_tenant

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
        flash(f'Receipt {receipt.receipt_number} generated. / វិក័យប័ត្រត្រូវបានបង្កើតជោគជ័យ។', 'success')
        return redirect(url_for('receipts.detail', id=receipt.id))

    now = datetime.now()
    room_id = request.args.get('room_id', type=int)
    billing_month = request.args.get('billing_month', type=int, default=now.month)
    billing_year = request.args.get('billing_year', type=int, default=now.year)
    selected_room = Room.query.get(room_id) if room_id else None
    prev_receipt = _get_previous_receipt(room_id, billing_year, billing_month) if room_id else None

    return render_template('receipts/generate.html',
        rooms=rooms,
        selected_room=selected_room,
        prev_receipt=prev_receipt,
        water_price=water_price,
        electricity_price=electricity_price,
        default_fee=default_fee,
        today=date.today(),
        now=now,
        billing_month=billing_month,
        billing_year=billing_year,
        month_names=MONTH_NAMES
    )


@receipts_bp.route('/receipts/<int:id>')
@login_required
def detail(id):
    receipt = Receipt.query.get_or_404(id)
    return render_template('receipts/detail.html', receipt=receipt, today=date.today())


@receipts_bp.route('/receipts/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    receipt = Receipt.query.get_or_404(id)
    new_payment = float(request.form.get('paid_amount') or 0)
    payment_method = request.form.get('payment_method')
    date_str = request.form.get('payment_date')
    payment_date = date.fromisoformat(date_str) if date_str else date.today()

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
        payment_date=payment_date
    )
    db.session.add(log)
    db.session.commit()
    backup_to_drive()
    flash('Payment recorded. / ការទូទាត់ត្រូវបានកត់ត្រា។', 'success')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/defer', methods=['POST'])
@login_required
def defer_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    receipt.payment_status = 'deferred'
    db.session.commit()
    flash('Balance deferred to next month. It will carry over automatically. / សមតុល្យត្រូវបានពន្យារដល់ខែក្រោយ។', 'info')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/undefer', methods=['POST'])
@login_required
def undefer_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    receipt.payment_status = 'partial' if receipt.paid_amount > 0 else 'unpaid'
    db.session.commit()
    flash('Receipt restored to active status.', 'info')
    return redirect(url_for('receipts.detail', id=id))


@receipts_bp.route('/receipts/<int:id>/print')
@login_required
def print_receipt(id):
    receipt = Receipt.query.get_or_404(id)
    bridge = request.args.get('bridge') == '1'
    return render_template('receipts/print.html', receipt=receipt, bridge=bridge)


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

    # --- 1. Render print.html to PNG via headless Chrome ---
    print_url = url_for('receipts.print_receipt', id=id, _external=True)
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
