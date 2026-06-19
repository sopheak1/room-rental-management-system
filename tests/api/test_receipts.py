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

def test_create_receipt_total_includes_fee(client, auth_headers, app):
    """The computed total must include `fee`, matching web's
    room_price + electricity_total + water_total + previous_balance + fee + late_fee - discount."""
    with app.app_context():
        b = Building(name='F', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='401', price=150000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Vuthy', is_active=True, move_in_date=date(2026,1,1))
        db.session.add(t)
        db.session.commit()
        room_id, tenant_id = r.id, t.id
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_id,
        'billing_month': 8, 'billing_year': 2026,
        'room_price': 150000, 'electricity_total': 20000, 'water_total': 5000,
        'previous_balance': 0, 'fee': 10000, 'late_fee': 0, 'discount': 0,
    })
    assert resp.status_code == 201
    assert resp.get_json()['total_amount'] == 185000  # 150000+20000+5000+10000

def test_create_receipt_number_resets_per_month(client, auth_headers, app):
    """Receipt numbering must reset per (year, month), matching web's
    _generate_receipt_number — not accumulate across the whole year."""
    with app.app_context():
        b = Building(name='G', address='')
        db.session.add(b)
        db.session.flush()
        r1 = Room(building_id=b.id, room_number='501', price=100000, status='occupied')
        r2 = Room(building_id=b.id, room_number='502', price=100000, status='occupied')
        db.session.add_all([r1, r2])
        db.session.flush()
        t1 = Tenant(room_id=r1.id, name='A', is_active=True, move_in_date=date(2026,1,1))
        t2 = Tenant(room_id=r2.id, name='B', is_active=True, move_in_date=date(2026,1,1))
        db.session.add_all([t1, t2])
        db.session.commit()
        room1_id, tenant1_id = r1.id, t1.id
        room2_id, tenant2_id = r2.id, t2.id
    # Two receipts in March, then one in April — April's counter must restart at 0001
    client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room1_id, 'tenant_id': tenant1_id,
        'billing_month': 3, 'billing_year': 2026, 'room_price': 100000
    })
    client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room2_id, 'tenant_id': tenant2_id,
        'billing_month': 3, 'billing_year': 2026, 'room_price': 100000
    })
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room1_id, 'tenant_id': tenant1_id,
        'billing_month': 4, 'billing_year': 2026, 'room_price': 100000
    })
    assert resp.status_code == 201
    assert resp.get_json()['receipt_number'] == 'RCP-202604-0001'

def test_edit_receipt_recomputes_total_with_fee(client, auth_headers, app):
    _, _, receipt_id = _seed(app)
    resp = client.put(f'/api/v1/receipts/{receipt_id}', headers=auth_headers, json={
        'room_price': 200000, 'electricity_total': 10000, 'water_total': 5000,
        'previous_balance': 0, 'fee': 5000, 'late_fee': 0, 'discount': 0,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total_amount'] == 220000  # 200000+10000+5000+5000
    assert data['remaining_balance'] == 220000

def test_edit_receipt_blocks_total_below_paid_amount(client, auth_headers, app):
    _, _, receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 150000, 'payment_method': 'cash', 'payment_date': '2026-06-17'
    })
    resp = client.put(f'/api/v1/receipts/{receipt_id}', headers=auth_headers, json={
        'room_price': 50000, 'electricity_total': 0, 'water_total': 0,
        'previous_balance': 0, 'fee': 0, 'late_fee': 0, 'discount': 0,
    })
    assert resp.status_code == 400

def test_edit_receipt_blocked_when_next_receipt_exists(client, auth_headers, app):
    room_id, tenant_id, receipt_id = _seed(app)
    with app.app_context():
        next_receipt = Receipt(
            receipt_number='RCP-202607-0001', room_id=room_id, tenant_id=tenant_id,
            billing_month=7, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(next_receipt)
        db.session.commit()
    resp = client.put(f'/api/v1/receipts/{receipt_id}', headers=auth_headers, json={
        'room_price': 200000, 'electricity_total': 0, 'water_total': 0,
        'previous_balance': 0, 'fee': 0, 'late_fee': 0, 'discount': 0,
    })
    assert resp.status_code == 400

def test_create_receipt_with_initial_payment_status_paid(client, auth_headers, app):
    """Mirrors web's generate() form, which lets staff mark a receipt as already
    paid at creation time instead of always starting 'unpaid'."""
    with app.app_context():
        b = Building(name='H', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='601', price=100000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Vanna', is_active=True, move_in_date=date(2026,1,1))
        db.session.add(t)
        db.session.commit()
        room_id, tenant_id = r.id, t.id
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_id,
        'billing_month': 9, 'billing_year': 2026,
        'room_price': 100000, 'payment_status': 'paid'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['payment_status'] == 'paid'
    assert data['paid_amount'] == 100000
    assert data['remaining_balance'] == 0

def test_create_receipt_with_initial_payment_status_partial(client, auth_headers, app):
    with app.app_context():
        b = Building(name='I', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='701', price=100000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Bopha', is_active=True, move_in_date=date(2026,1,1))
        db.session.add(t)
        db.session.commit()
        room_id, tenant_id = r.id, t.id
    resp = client.post('/api/v1/receipts', headers=auth_headers, json={
        'room_id': room_id, 'tenant_id': tenant_id,
        'billing_month': 9, 'billing_year': 2026,
        'room_price': 100000, 'payment_status': 'partial', 'paid_amount': 40000
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['payment_status'] == 'partial'
    assert data['paid_amount'] == 40000
    assert data['remaining_balance'] == 60000

def test_defer_receipt_sets_status_without_payment_log(client, auth_headers, app):
    """Web's defer just flips payment_status — it must NOT create a PaymentLog row."""
    _, _, receipt_id = _seed(app)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/defer', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['payment_status'] == 'deferred'
    assert data['payment_logs'] == []

def test_undefer_receipt_restores_unpaid(client, auth_headers, app):
    _, _, receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/defer', headers=auth_headers)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/undefer', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['payment_status'] == 'unpaid'

def test_undefer_receipt_restores_partial_when_paid_amount_positive(client, auth_headers, app):
    _, _, receipt_id = _seed(app)
    client.post(f'/api/v1/receipts/{receipt_id}/payments', headers=auth_headers, json={
        'amount': 50000, 'payment_method': 'cash', 'payment_date': '2026-06-17'
    })
    client.post(f'/api/v1/receipts/{receipt_id}/defer', headers=auth_headers)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/undefer', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['payment_status'] == 'partial'
