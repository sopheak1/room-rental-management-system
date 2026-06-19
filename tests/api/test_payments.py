from app import db
from app.models import Building, Room, Tenant, Receipt, PaymentLog
from datetime import date

def _seed(app):
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=200000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Chan', is_active=True, move_in_date=date(2026,1,1))
        db.session.add(t)
        db.session.flush()
        receipt = Receipt(
            receipt_number='RCP-202606-0001', room_id=r.id, tenant_id=t.id,
            billing_month=6, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(receipt)
        db.session.commit()
        return receipt.id

def test_record_payment(client, auth_headers, app):
    receipt_id = _seed(app)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 200000, 'payment_method': 'cash',
        'payment_date': '2026-06-17', 'status': 'paid'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['payment_status'] == 'paid'
    assert data['remaining_balance'] == 0

def test_overpayment_returns_409(client, auth_headers, app):
    receipt_id = _seed(app)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 999999, 'payment_method': 'cash',
        'payment_date': '2026-06-17', 'status': 'paid'
    })
    assert resp.status_code == 409

def test_soft_delete_payment(client, auth_headers, app):
    receipt_id = _seed(app)
    # record a payment first
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 100000, 'payment_method': 'cash', 'payment_date': '2026-06-17', 'status': 'partial'
    })
    with app.app_context():
        log = PaymentLog.query.filter_by(receipt_id=receipt_id).first()
        log_id = log.id
    resp = client.delete(f'/api/v1/receipts/{receipt_id}/payments/{log_id}',
        headers=auth_headers, json={'reason': 'wrong_amount'})
    assert resp.status_code == 200
    with app.app_context():
        log = PaymentLog.query.get(log_id)
        assert log.deleted_at is not None

def test_soft_delete_payment_multi_payment_recalculates_correctly(client, auth_headers, app):
    receipt_id = _seed(app)
    # Record 3 payments: 80000, 50000, 30000 (total 160000)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 80000, 'payment_method': 'cash', 'payment_date': '2026-06-17'
    })
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 50000, 'payment_method': 'cash', 'payment_date': '2026-06-18'
    })
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 30000, 'payment_method': 'cash', 'payment_date': '2026-06-19'
    })
    with app.app_context():
        logs = PaymentLog.query.filter_by(receipt_id=receipt_id, deleted_at=None).order_by(PaymentLog.created_at).all()
        assert len(logs) == 3
        last_log_id = logs[2].id  # 30000 — only this one can be deleted
    # Delete the most recent payment
    resp = client.delete(f'/api/v1/receipts/{receipt_id}/payments/{last_log_id}',
        headers=auth_headers, json={'reason': 'correction'})
    assert resp.status_code == 200
    # Verify receipt paid_amount is recomputed (80000 + 50000 = 130000, not 160000 - 30000 via stale cache)
    data = resp.get_json()
    receipt_data = data['receipt']
    assert receipt_data['paid_amount'] == 130000
    assert receipt_data['remaining_balance'] == 70000  # 200000 - 130000
    # Verify logs: exactly 2 non-deleted with correct amounts
    with app.app_context():
        active_logs = PaymentLog.query.filter_by(receipt_id=receipt_id, deleted_at=None).all()
        assert len(active_logs) == 2
        amounts = sorted([l.amount for l in active_logs])
        assert amounts == [50000, 80000]

def test_delete_payment_blocks_non_last_log(client, auth_headers, app):
    """Only the most recent payment log may be deleted — deleting an earlier
    one would desync the receipt's running balance, exactly like web."""
    receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 80000, 'payment_method': 'cash', 'payment_date': '2026-06-17'
    })
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 50000, 'payment_method': 'cash', 'payment_date': '2026-06-18'
    })
    with app.app_context():
        logs = PaymentLog.query.filter_by(receipt_id=receipt_id, deleted_at=None).order_by(PaymentLog.created_at).all()
        first_log_id = logs[0].id
    resp = client.delete(f'/api/v1/receipts/{receipt_id}/payments/{first_log_id}',
        headers=auth_headers, json={'reason': 'oops'})
    assert resp.status_code == 400
    assert 'last payment' in resp.get_json()['error'].lower()

def test_delete_payment_requires_reason(client, auth_headers, app):
    receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 50000, 'payment_method': 'cash', 'payment_date': '2026-06-18'
    })
    with app.app_context():
        log_id = PaymentLog.query.filter_by(receipt_id=receipt_id).first().id
    resp = client.delete(f'/api/v1/receipts/{receipt_id}/payments/{log_id}',
        headers=auth_headers, json={'reason': '  '})
    assert resp.status_code == 400
    assert 'reason' in resp.get_json()['error'].lower()

def test_delete_payment_blocked_when_next_receipt_exists(client, auth_headers, app):
    receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 50000, 'payment_method': 'cash', 'payment_date': '2026-06-18'
    })
    with app.app_context():
        receipt = Receipt.query.get(receipt_id)
        next_receipt = Receipt(
            receipt_number='RCP-202607-0001', room_id=receipt.room_id, tenant_id=receipt.tenant_id,
            billing_month=7, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(next_receipt)
        db.session.commit()
        log_id = PaymentLog.query.filter_by(receipt_id=receipt_id).first().id
    resp = client.delete(f'/api/v1/receipts/{receipt_id}/payments/{log_id}',
        headers=auth_headers, json={'reason': 'correction'})
    assert resp.status_code == 400
    assert 'next month' in resp.get_json()['error'].lower()
