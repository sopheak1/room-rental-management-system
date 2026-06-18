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
