from datetime import datetime, timedelta

def test_sync_returns_all_tables(client, auth_headers):
    resp = client.get('/api/v1/sync?since=2000-01-01T00:00:00', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ['buildings', 'rooms', 'tenants', 'utility_prices', 'receipts', 'payment_logs', 'utility_usage']:
        assert key in data, f"Missing key: {key}"

def test_sync_requires_auth(client):
    resp = client.get('/api/v1/sync?since=2000-01-01T00:00:00')
    assert resp.status_code == 401

def test_sync_since_filters_records(client, auth_headers, app):
    from app import db
    from app.models import Building
    # Create a building with a past updated_at
    with app.app_context():
        b = Building(name='Old', address='')
        b.updated_at = datetime(2020, 1, 1)
        db.session.add(b)
        db.session.commit()
    # Sync since yesterday — should not include the old building
    since = (datetime.utcnow() - timedelta(days=1)).isoformat()
    resp = client.get(f'/api/v1/sync?since={since}', headers=auth_headers)
    names = [b['name'] for b in resp.get_json()['buildings']]
    assert 'Old' not in names

def test_sync_missing_since_returns_400(client, auth_headers):
    resp = client.get('/api/v1/sync', headers=auth_headers)
    assert resp.status_code == 400

def test_sync_rooms_include_building_name(client, auth_headers, app):
    """Mobile's local Room model/dashboard/filters key off building_name —
    it must be flattened into the room payload since mobile is offline-first
    and never joins against a live buildings table."""
    from app import db
    from app.models import Building, Room
    with app.app_context():
        b = Building(name='Sunrise Apartments', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=100000, status='occupied')
        db.session.add(r)
        db.session.commit()
    resp = client.get('/api/v1/sync?since=2000-01-01T00:00:00', headers=auth_headers)
    rooms = resp.get_json()['rooms']
    assert any(r['building_name'] == 'Sunrise Apartments' for r in rooms)
