import io
import os
from datetime import datetime
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER

RECEIPT_WIDTH = 80 * mm
MONTH_NAMES = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']

# ── Styles (Helvetica — reliable on all platforms) ───────────
S_TITLE  = ParagraphStyle('title',  fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=15)
S_CENTER = ParagraphStyle('center', fontSize=9,  fontName='Helvetica-Bold', alignment=TA_CENTER, leading=13)
S_NORMAL = ParagraphStyle('normal', fontSize=8,  fontName='Helvetica',      leading=12)
S_BOLD   = ParagraphStyle('bold',   fontSize=8,  fontName='Helvetica-Bold', leading=12)
S_SMALL  = ParagraphStyle('small',  fontSize=7,  fontName='Helvetica',      leading=10, textColor=colors.grey)
S_FOOTER = ParagraphStyle('footer', fontSize=8,  fontName='Helvetica',      alignment=TA_CENTER, leading=12)
S_GEN    = ParagraphStyle('gen',    fontSize=6,  fontName='Helvetica',      alignment=TA_CENTER, textColor=colors.grey)

F_NORMAL = 'Helvetica'
F_BOLD   = 'Helvetica-Bold'


def _hr():
    return HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=2, spaceBefore=2)


def _hr_thick():
    return HRFlowable(width='100%', thickness=1, color=colors.black, spaceAfter=3, spaceBefore=3)


def generate_receipt_pdf(receipt):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(RECEIPT_WIDTH, 280 * mm),
        rightMargin=5 * mm,
        leftMargin=5 * mm,
        topMargin=5 * mm,
        bottomMargin=5 * mm
    )

    story = []

    # ── Header ───────────────────────────────────────────────
    story.append(Paragraph('RENTAL MANAGEMENT', S_TITLE))
    story.append(Paragraph('Payment Receipt', S_CENTER))
    story.append(_hr_thick())

    # ── Receipt meta ─────────────────────────────────────────
    story.append(Paragraph(f'<b>Receipt #:</b> {receipt.receipt_number}', S_NORMAL))
    story.append(Paragraph(f'<b>Date:</b> {receipt.created_at.strftime("%d/%m/%Y")}', S_NORMAL))
    story.append(Paragraph(
        f'<b>Period:</b> {MONTH_NAMES[receipt.billing_month - 1]} {receipt.billing_year}',
        S_NORMAL
    ))
    story.append(Spacer(1, 2 * mm))

    # ── Room & Tenant ─────────────────────────────────────────
    story.append(_hr())
    story.append(Paragraph(
        f'<b>Room:</b> {receipt.room.room_number}  ({receipt.room.building.name})',
        S_NORMAL
    ))
    if receipt.tenant:
        story.append(Paragraph(f'<b>Tenant:</b> {receipt.tenant.name}', S_NORMAL))
        if receipt.tenant.tel:
            story.append(Paragraph(f'<b>Tel:</b> {receipt.tenant.tel}', S_NORMAL))
    story.append(Spacer(1, 2 * mm))

    # ── Line items ────────────────────────────────────────────
    story.append(_hr())

    rows = [['Description', 'USD ($)']]
    rows.append(['Room Rent', f'{receipt.room_price:.2f}'])

    if receipt.electricity_units is not None:
        elec_label = (
            f'Electricity\n'
            f'({receipt.electricity_from:.0f}->{receipt.electricity_to:.0f},'
            f' {receipt.electricity_units:.1f} units x ${receipt.electricity_price_per_unit:.4f})'
        )
    else:
        elec_label = 'Electricity'
    rows.append([elec_label, f'{receipt.electricity_total:.2f}'])

    if receipt.water_units is not None:
        water_label = (
            f'Water\n'
            f'({receipt.water_from:.0f}->{receipt.water_to:.0f},'
            f' {receipt.water_units:.1f} units x ${receipt.water_price_per_unit:.4f})'
        )
    else:
        water_label = 'Water'
    rows.append([water_label, f'{receipt.water_total:.2f}'])

    if receipt.previous_balance and receipt.previous_balance > 0:
        rows.append(['Due Balance (Previous)', f'{receipt.previous_balance:.2f}'])

    if receipt.late_fee and receipt.late_fee > 0:
        rows.append(['Late Fee', f'{receipt.late_fee:.2f}'])

    if receipt.discount and receipt.discount > 0:
        rows.append(['Discount', f'- {receipt.discount:.2f}'])

    line_tbl = Table(rows, colWidths=[50 * mm, 18 * mm])
    line_tbl.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1,  0), F_BOLD),
        ('FONTNAME',      (0, 1), (-1, -1), F_NORMAL),
        ('FONTSIZE',      (0, 0), (-1, -1), 7.5),
        ('ALIGN',         (1, 0), (1,  -1), 'RIGHT'),
        ('LINEBELOW',     (0, 0), (-1,  0), 0.5, colors.black),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    story.append(line_tbl)

    # ── Totals ────────────────────────────────────────────────
    story.append(_hr_thick())

    balance_color = colors.red if receipt.remaining_balance > 0 else colors.green
    totals = Table([
        ['TOTAL',   f'$ {receipt.total_amount:.2f}'],
        ['Paid',    f'$ {receipt.paid_amount:.2f}'],
        ['Balance', f'$ {receipt.remaining_balance:.2f}'],
    ], colWidths=[50 * mm, 18 * mm])
    totals.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), F_BOLD),
        ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
        ('ALIGN',         (1, 0), (1,  -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TEXTCOLOR',     (0, 2), (-1,  2), balance_color),
    ]))
    story.append(totals)

    # ── Payment info ──────────────────────────────────────────
    if receipt.payment_method or receipt.payment_date:
        story.append(Spacer(1, 2 * mm))
        status_map = {'paid': 'PAID', 'partial': 'PARTIAL PAYMENT', 'unpaid': 'UNPAID'}
        method_map = {'cash': 'Cash', 'bank_transfer': 'Bank Transfer', 'qr': 'QR Code'}
        story.append(Paragraph(
            f'<b>Status:</b> {status_map.get(receipt.payment_status, receipt.payment_status)}',
            S_NORMAL
        ))
        if receipt.payment_method:
            story.append(Paragraph(
                f'<b>Method:</b> {method_map.get(receipt.payment_method, receipt.payment_method)}',
                S_NORMAL
            ))
        if receipt.payment_date:
            story.append(Paragraph(
                f'<b>Payment Date:</b> {receipt.payment_date.strftime("%d/%m/%Y")}',
                S_NORMAL
            ))

    if receipt.notes:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f'Notes: {receipt.notes}', S_SMALL))

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(_hr())
    story.append(Paragraph('Thank you!', S_FOOTER))
    story.append(Paragraph(
        f'Generated: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        S_GEN
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
