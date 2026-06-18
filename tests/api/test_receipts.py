from app import db
from app.models import Building, Room, Tenant, Receipt
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
        return r.id, t.id, receipt.id

def test_list_receipts(client, auth_headers, app):
    _seed(app)
    resp = client.get('/api/v1/receipts', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1

def test_list_receipts_filter_by_month(client, auth_headers, app):
    _seed(app)
    resp = client.get('/api/v1/receipts?month=6&year=2026', headers=auth_headers)
    assert resp.status_code == 200
    for r in resp.get_json():
        assert r['billing_month'] == 6

def test_get_receipt(client, auth_headers, app):
    _, _, receipt_id = _seed(app)
    resp = client.get(f'/api/v1/receipts/{receipt_id}', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['receipt_number'] == 'RCP-202606-0001'
    assert 'payment_logs' in data

def test_create_receipt(client, auth_headers, app):
    with app.app_context():
        b = Building(name='C', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='201', price=150000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Dara', is_active=True, move_in_date=date(2026,1,1))
        db.session.add(t)
        db.session.commit()
        room_id, tenant_id = r.id, t.id
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_id,
        'billing_month': 7, 'billing_year': 2026,
        'room_price': 150000, 'electricity_total': 20000, 'water_total': 5000,
        'previous_balance': 0, 'late_fee': 0, 'discount': 0,
        'total_amount': 175000, 'notes': ''
    })
    assert resp.status_code == 201
    assert resp.get_json()['total_amount'] == 175000

def test_create_receipt_duplicate_returns_409(client, auth_headers, app):
    room_id, tenant_id, _ = _seed(app)
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_id,
        'billing_month': 6, 'billing_year': 2026,
        'room_price': 200000, 'total_amount': 200000
    })
    assert resp.status_code == 409

def test_create_receipt_same_room_different_tenant_returns_201(client, auth_headers, app):
    """A tenant can check out and a new tenant can check into the SAME room within
    the SAME billing month — that's two legitimate receipts for the same room+month,
    one per tenant. The duplicate-check key must include tenant_id, not just
    room_id + billing_month + billing_year."""
    room_id, tenant_a_id, _ = _seed(app)
    with app.app_context():
        tenant_b = Tenant(room_id=room_id, name='Sokha', is_active=True, move_in_date=date(2026, 6, 15))
        db.session.add(tenant_b)
        db.session.commit()
        tenant_b_id = tenant_b.id
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_b_id,
        'billing_month': 6, 'billing_year': 2026,
        'room_price': 200000, 'total_amount': 200000
    })
    assert resp.status_code == 201
    assert resp.get_json()['tenant_id'] == tenant_b_id

def test_create_receipt_missing_room_id_returns_400(client, auth_headers, app):
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'billing_month': 7, 'billing_year': 2026,
        'room_price': 150000, 'total_amount': 150000
    })
    assert resp.status_code == 400
