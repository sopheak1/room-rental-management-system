from datetime import date
from app import db
from app.models import Building, Room, Tenant, Receipt

def _seed(app):
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='102', price=150000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Sopheak', tel='012345678',
                   move_in_date=date(2026, 1, 1), is_active=True)
        db.session.add(t)
        db.session.commit()
        return r.id, t.id

def test_get_tenant_by_room(client, auth_headers, app):
    room_id, _ = _seed(app)
    resp = client.get(f'/api/v1/tenants/{room_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Sopheak'

def test_get_tenant_vacant_room(client, auth_headers, app):
    with app.app_context():
        b = Building(name='C', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='201', price=100000, status='available')
        db.session.add(r)
        db.session.commit()
        room_id = r.id
    resp = client.get(f'/api/v1/tenants/{room_id}', headers=auth_headers)
    assert resp.status_code == 404

def test_create_tenant(client, auth_headers, app):
    with app.app_context():
        b = Building(name='D', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='301', price=100000, status='available')
        db.session.add(r)
        db.session.commit()
        room_id = r.id
    resp = client.post('/api/v1/tenants', headers=auth_headers, json={
        'room_id': room_id, 'name': 'Chan', 'tel': '011111111',
        'move_in_date': '2026-06-01', 'deposit_paid': 200000
    })
    assert resp.status_code == 201
    assert resp.get_json()['name'] == 'Chan'

def test_update_tenant(client, auth_headers, app):
    _, tenant_id = _seed(app)
    resp = client.put(f'/api/v1/tenants/{tenant_id}',
        headers=auth_headers, json={'tel': '099999999'})
    assert resp.status_code == 200
    assert resp.get_json()['tel'] == '099999999'

def test_checkout_tenant(client, auth_headers, app):
    room_id, tenant_id = _seed(app)
    resp = client.post(f'/api/v1/tenants/{tenant_id}/checkout',
        headers=auth_headers, json={
            'move_out_date': '2026-06-30',
            'deposit_refunded': 150000,
            'move_out_reason': 'End of contract'
        })
    assert resp.status_code == 200

def test_checkout_tenant_double_checkout(client, auth_headers, app):
    room_id, tenant_id = _seed(app)
    # First checkout should succeed
    resp = client.post(f'/api/v1/tenants/{tenant_id}/checkout',
        headers=auth_headers, json={
            'move_out_date': '2026-06-30',
            'deposit_refunded': 150000,
            'move_out_reason': 'End of contract'
        })
    assert resp.status_code == 200
    # Second checkout should fail with 400
    resp = client.post(f'/api/v1/tenants/{tenant_id}/checkout',
        headers=auth_headers, json={
            'move_out_date': '2026-07-01',
            'deposit_refunded': 150000,
            'move_out_reason': 'Already checked out'
        })
    assert resp.status_code == 400
    assert 'already checked out' in resp.get_json()['error'].lower()

def test_checkout_blocked_when_outstanding_balance(client, auth_headers, app):
    """Checkout must hard-block on outstanding balances, matching web —
    no bypass/force flag is honored."""
    room_id, tenant_id = _seed(app)
    with app.app_context():
        receipt = Receipt(
            receipt_number='RCP-202606-0001', room_id=room_id, tenant_id=tenant_id,
            billing_month=6, billing_year=2026, room_price=150000,
            total_amount=150000, paid_amount=0, remaining_balance=150000,
            payment_status='unpaid'
        )
        db.session.add(receipt)
        db.session.commit()
    resp = client.post(f'/api/v1/tenants/{tenant_id}/checkout',
        headers=auth_headers, json={
            'move_out_date': '2026-06-30',
            'deposit_refunded': 150000,
            'move_out_reason': 'End of contract',
            'force_checkout': True
        })
    assert resp.status_code == 400
    assert 'outstanding' in resp.get_json()['error'].lower()
    with app.app_context():
        assert Tenant.query.get(tenant_id).is_active is True

def test_checkout_allowed_after_write_off(client, auth_headers, app):
    room_id, tenant_id = _seed(app)
    with app.app_context():
        receipt = Receipt(
            receipt_number='RCP-202606-0001', room_id=room_id, tenant_id=tenant_id,
            billing_month=6, billing_year=2026, room_price=150000,
            total_amount=150000, paid_amount=0, remaining_balance=150000,
            payment_status='unpaid'
        )
        db.session.add(receipt)
        db.session.commit()
    resp = client.post(f'/api/v1/tenants/{tenant_id}/write-off', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['count'] == 1
    resp = client.post(f'/api/v1/tenants/{tenant_id}/checkout',
        headers=auth_headers, json={
            'move_out_date': '2026-06-30',
            'deposit_refunded': 150000,
            'move_out_reason': 'End of contract'
        })
    assert resp.status_code == 200
