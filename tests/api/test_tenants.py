from datetime import date
from app import db
from app.models import Building, Room, Tenant

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
