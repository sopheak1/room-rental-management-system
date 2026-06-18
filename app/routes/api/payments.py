from datetime import datetime, date
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.routes.api import api_bp
from app.routes.api.receipts import _receipt_dict
from app.models import Receipt, PaymentLog
from app.utils.verification import generate_payment_hash
from app import db

@api_bp.route('/receipts/<int:receipt_id>/payments', methods=['POST'])
@jwt_required()
def record_payment(receipt_id):
    receipt = Receipt.query.get(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404
    data = request.get_json(silent=True) or {}
    amount = float(data.get('amount', 0))
    if amount > receipt.remaining_balance + 0.01:
        return jsonify({
            'error': 'Payment exceeds remaining balance',
            'remaining_balance': receipt.remaining_balance,
            'server_data': _receipt_dict(receipt, include_logs=True)
        }), 409
    payment_date_str = data.get('payment_date')
    pay_date = date.fromisoformat(payment_date_str) if payment_date_str else date.today()
    new_paid = receipt.paid_amount + amount
    new_remaining = receipt.total_amount - new_paid
    status = data.get('status', 'partial')
    if new_remaining <= 0.01:
        status = 'paid'
        new_remaining = 0
    elif status not in ('partial', 'deferred'):
        status = 'partial'
    verification_hash = generate_payment_hash(
        receipt.receipt_number, new_remaining, amount, pay_date, data.get('payment_method', '')
    )
    log = PaymentLog(
        receipt_id=receipt_id, amount=amount,
        payment_method=data.get('payment_method', 'cash'),
        payment_date=pay_date, verification_hash=verification_hash
    )
    receipt.paid_amount = new_paid
    receipt.remaining_balance = new_remaining
    receipt.payment_status = status
    receipt.updated_at = datetime.utcnow()
    db.session.add(log)
    db.session.commit()
    return jsonify(_receipt_dict(receipt, include_logs=True)), 200

@api_bp.route('/receipts/<int:receipt_id>/payments/<int:log_id>', methods=['DELETE'])
@jwt_required()
def delete_payment(receipt_id, log_id):
    receipt = Receipt.query.get(receipt_id)
    log = PaymentLog.query.get(log_id)
    if not receipt or not log or log.receipt_id != receipt_id:
        return jsonify({'error': 'Not found'}), 404
    if log.deleted_at:
        return jsonify({'error': 'Payment already deleted'}), 409
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', '')
    log.deleted_at = datetime.utcnow()
    log.delete_reason = reason
    # Recalculate receipt paid_amount from non-deleted logs
    active_logs = PaymentLog.query.filter_by(
        receipt_id=receipt_id, deleted_at=None).all()
    receipt.paid_amount = sum(l.amount for l in active_logs)
    receipt.remaining_balance = receipt.total_amount - receipt.paid_amount
    receipt.payment_status = 'unpaid' if receipt.paid_amount == 0 else 'partial'
    receipt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'msg': 'Payment deleted', 'receipt': _receipt_dict(receipt, include_logs=True)}), 200
