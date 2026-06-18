from app import db
from app.models import Building, Room, UtilityUsage

def _seed_room(app):
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=100000)
        db.session.add(r)
        db.session.commit()
        return r.id

def test_list_utility_usage(client, auth_headers, app):
    room_id = _seed_room(app)
    with app.app_context():
        u = UtilityUsage(room_id=room_id, billing_month=6, billing_year=2026,
                         electricity_from=100, electricity_to=120)
        db.session.add(u)
        db.session.commit()
    resp = client.get('/api/v1/utility-usage', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1

def test_batch_upsert_utility_usage(client, auth_headers, app):
    room_id = _seed_room(app)
    resp = client.post('/api/v1/utility-usage/batch', headers=auth_headers, json={
        'billing_month': 7, 'billing_year': 2026,
        'readings': [{'room_id': room_id, 'electricity_from': 200, 'electricity_to': 230,
                      'water_from': 50, 'water_to': 55}]
    })
    assert resp.status_code == 200
    assert resp.get_json()['saved'] == 1
