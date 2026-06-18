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

def test_batch_upsert_utility_usage_update_path(client, auth_headers, app):
    """Test that the UPDATE path works: existing row is updated in place, not duplicated."""
    room_id = _seed_room(app)
    # Seed an existing UtilityUsage row for the room/month/year
    with app.app_context():
        existing = UtilityUsage(room_id=room_id, billing_month=8, billing_year=2026,
                                electricity_from=100, electricity_to=120)
        db.session.add(existing)
        db.session.commit()

    # POST with same room_id/month/year but different readings
    resp = client.post('/api/v1/utility-usage/batch', headers=auth_headers, json={
        'billing_month': 8, 'billing_year': 2026,
        'readings': [{'room_id': room_id, 'electricity_from': 200, 'electricity_to': 230}]
    })
    assert resp.status_code == 200
    assert resp.get_json()['saved'] == 1

    # Verify there is still only ONE row for this room/month/year
    with app.app_context():
        rows = UtilityUsage.query.filter_by(room_id=room_id, billing_month=8, billing_year=2026).all()
        assert len(rows) == 1
        # Verify the values were updated
        assert rows[0].electricity_from == 200
        assert rows[0].electricity_to == 230

def test_batch_upsert_utility_usage_empty_readings(client, auth_headers, app):
    """Test that POST with empty readings list returns 200 with saved == 0."""
    _seed_room(app)
    resp = client.post('/api/v1/utility-usage/batch', headers=auth_headers, json={
        'billing_month': 9, 'billing_year': 2026,
        'readings': []
    })
    assert resp.status_code == 200
    assert resp.get_json()['saved'] == 0
