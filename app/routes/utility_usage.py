from collections import OrderedDict
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required
from app.models import Room, Building, UtilityUsage
from app.routes.receipts import _get_previous_receipt
from app import db
from app.utils.timezone import now as _now

utility_usage_bp = Blueprint('utility_usage', __name__)

MONTH_NAMES = ['មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា',
               'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ']


def _room_meter_mode(room_id, year, month):
    """Detect whether a room bills electricity/water by meter reading or a flat direct amount,
    based on its most recent receipt. Defaults to direct-input when there's no history."""
    prev = _get_previous_receipt(room_id, year, month)
    if not prev:
        return {'electricity': 'direct', 'water': 'direct', 'prev': None}
    return {
        'electricity': 'direct' if prev.electricity_units is None else 'meter',
        'water': 'direct' if prev.water_units is None else 'meter',
        'prev': prev
    }


@utility_usage_bp.route('/utility-usage')
@login_required
def setup():
    """Step 1 — choose billing period, which utility to record, and which rooms."""
    rooms = Room.query.join(Building).filter(Room.status == 'occupied') \
        .order_by(Building.name, Room.room_number).all()
    now = _now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year

    # Mark which utilities are already staged per room for the chosen billing period,
    # so the user can see at a glance what's left to fill in.
    filled = {}
    for u in UtilityUsage.query.filter_by(billing_month=month, billing_year=year).all():
        filled[u.room_id] = {
            'electricity': u.electricity_amount is not None or u.electricity_to is not None,
            'water': u.water_amount is not None or u.water_to is not None,
        }

    return render_template('utility_usage/setup.html',
        rooms=rooms,
        month=month,
        year=year,
        filled=filled,
        month_names=MONTH_NAMES
    )


@utility_usage_bp.route('/utility-usage/input')
@login_required
def batch_input():
    """Step 2 — mobile-friendly list to punch in readings for the chosen rooms."""
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    utility = request.args.get('utility')  # 'electricity', 'water', or 'both'
    room_ids = request.args.get('room_ids', '')

    if not month or not year or utility not in ('electricity', 'water', 'both'):
        flash('សូមជ្រើសរើសព័ត៌មានឲ្យបានគ្រប់គ្រាន់។ / Please complete the setup first.', 'warning')
        return redirect(url_for('utility_usage.setup'))

    if room_ids == 'all':
        rooms = Room.query.join(Building).filter(Room.status == 'occupied') \
            .order_by(Building.name, Room.room_number).all()
    else:
        try:
            ids = [int(x) for x in room_ids.split(',') if x.strip()]
        except ValueError:
            ids = []
        rooms = Room.query.join(Building).filter(Room.id.in_(ids)) \
            .order_by(Building.name, Room.room_number).all() if ids else []

    if not rooms:
        flash('មិនមានបន្ទប់ត្រូវបានជ្រើសរើសទេ។ / No rooms selected.', 'warning')
        return redirect(url_for('utility_usage.setup'))

    entries = []
    for room in rooms:
        mode = _room_meter_mode(room.id, year, month)
        existing = UtilityUsage.query.filter_by(room_id=room.id, billing_month=month, billing_year=year).first()
        prev = mode['prev']

        elec_from = (existing.electricity_from if existing and existing.electricity_from is not None
                     else (prev.electricity_to if prev else None))
        water_from = (existing.water_from if existing and existing.water_from is not None
                      else (prev.water_to if prev else None))

        entries.append({
            'room': room,
            'tenant': room.active_tenant,
            'electricity_mode': mode['electricity'],
            'water_mode': mode['water'],
            'electricity_from': elec_from,
            'electricity_to': existing.electricity_to if existing else None,
            'electricity_amount': existing.electricity_amount if existing else None,
            'water_from': water_from,
            'water_to': existing.water_to if existing else None,
            'water_amount': existing.water_amount if existing else None,
        })

    return render_template('utility_usage/batch_input.html',
        entries=entries,
        month=month,
        year=year,
        utility=utility,
        room_ids=room_ids,
        month_names=MONTH_NAMES
    )


@utility_usage_bp.route('/utility-usage/save', methods=['POST'])
@login_required
def save():
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    utility = request.form.get('utility')
    room_ids = request.form.get('room_ids', '')
    submitted_room_ids = request.form.getlist('room_id')

    saved_count = 0
    for rid_str in submitted_room_ids:
        room_id = int(rid_str)
        usage = UtilityUsage.query.filter_by(room_id=room_id, billing_month=month, billing_year=year).first()
        if not usage:
            usage = UtilityUsage(room_id=room_id, billing_month=month, billing_year=year)
            db.session.add(usage)

        if utility in ('electricity', 'both'):
            mode = request.form.get(f'electricity_mode_{room_id}')
            if mode == 'direct':
                amount = request.form.get(f'electricity_amount_{room_id}')
                if amount not in (None, ''):
                    usage.electricity_amount = float(amount)
                    usage.electricity_from = None
                    usage.electricity_to = None
            else:
                e_from = request.form.get(f'electricity_from_{room_id}')
                e_to = request.form.get(f'electricity_to_{room_id}')
                if e_from not in (None, ''):
                    usage.electricity_from = float(e_from)
                if e_to not in (None, ''):
                    usage.electricity_to = float(e_to)
                usage.electricity_amount = None

        if utility in ('water', 'both'):
            mode = request.form.get(f'water_mode_{room_id}')
            if mode == 'direct':
                amount = request.form.get(f'water_amount_{room_id}')
                if amount not in (None, ''):
                    usage.water_amount = float(amount)
                    usage.water_from = None
                    usage.water_to = None
            else:
                w_from = request.form.get(f'water_from_{room_id}')
                w_to = request.form.get(f'water_to_{room_id}')
                if w_from not in (None, ''):
                    usage.water_from = float(w_from)
                if w_to not in (None, ''):
                    usage.water_to = float(w_to)
                usage.water_amount = None

        saved_count += 1

    db.session.commit()
    flash(f'បានរក្សាទុកការអានមីទ័រសម្រាប់ {saved_count} បន្ទប់។ / Saved readings for {saved_count} room(s).', 'success')
    return redirect(url_for('utility_usage.batch_input', month=month, year=year, utility=utility, room_ids=room_ids))


def _usage_groups(month, year, room_ids=None):
    """Saved UtilityUsage rows for the period, grouped by building, sorted by room number.
    If room_ids is given, only those rooms are included."""
    query = UtilityUsage.query.filter_by(billing_month=month, billing_year=year)
    if room_ids is not None:
        query = query.filter(UtilityUsage.room_id.in_(room_ids))
    usages = query.all()
    usages.sort(key=lambda u: (u.room.building.name, u.room.room_number))

    groups = OrderedDict()
    for u in usages:
        groups.setdefault(u.room.building.name, []).append(u)
    return groups


def _parse_room_ids(raw):
    """Parse a comma-separated room_ids query param. Returns None if absent (= no filter)."""
    if raw is None or raw == '' or raw == 'all':
        return None
    try:
        return [int(x) for x in raw.split(',') if x.strip()]
    except ValueError:
        return None


@utility_usage_bp.route('/utility-usage/print')
@login_required
def print_sheet():
    """Minimalist printable sheet of saved readings — 58mm thermal, browser or PT-210.
    Optionally filtered to specific rooms via ?room_ids=1,2,3."""
    now = _now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year
    bridge = request.args.get('bridge') == '1'
    room_ids = _parse_room_ids(request.args.get('room_ids'))

    groups = _usage_groups(month, year, room_ids=room_ids)
    return render_template('utility_usage/print_sheet.html',
        groups=groups, month=month, year=year, month_names=MONTH_NAMES, bridge=bridge)


@utility_usage_bp.route('/utility-usage/escpos')
@login_required
def escpos():
    """Render the print sheet as an ESC/POS bitmap for the Android Print Bridge (PT-210)."""
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageOps
    from escpos.printer import File as FilePrinter
    import io, tempfile, os

    now = _now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year
    room_ids_raw = request.args.get('room_ids')

    print_kwargs = {'month': month, 'year': year, 'bridge': 1, '_external': True}
    if room_ids_raw:
        print_kwargs['room_ids'] = room_ids_raw
    print_url = url_for('utility_usage.print_sheet', **print_kwargs)

    # PT-210 print width: 48mm at 203 DPI = 384 dots
    PRINTER_DOTS = 384

    with sync_playwright() as p:
        browser = p.chromium.launch()
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

    img = Image.open(io.BytesIO(img_bytes)).convert('L')
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop((0, 0, img.width, min(bbox[3] + 60, img.height)))

    new_height = int(img.height * PRINTER_DOTS / img.width)
    img = img.resize((PRINTER_DOTS, new_height), Image.LANCZOS)
    img = img.point(lambda x: 0 if x < 180 else 255, '1')

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
        headers={'Content-Disposition': f'attachment; filename="utility_usage_{year}_{month:02d}.bin"',
                 'Access-Control-Allow-Origin': '*'}
    )
