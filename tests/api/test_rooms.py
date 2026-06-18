from app import db
from app.models import Building, Room

def _seed_room(app):
    with app.app_context():
        b = Building(name='Block A', address='St 1')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=200000, status='available')
        db.session.add(r)
        db.session.commit()
        return b.id, r.id

def test_list_rooms(client, auth_headers, app):
    _seed_room(app)
    resp = client.get('/api/v1/rooms', headers=auth_headers)
    assert resp.status_code == 200
    rooms = resp.get_json()
    assert len(rooms) >= 1
    assert 'building_name' in rooms[0]

def test_update_room(client, auth_headers, app):
    _, room_id = _seed_room(app)
    resp = client.put(f'/api/v1/rooms/{room_id}',
        headers=auth_headers,
        json={'price': 250000, 'status': 'occupied'})
    assert resp.status_code == 200
    assert resp.get_json()['price'] == 250000

def test_update_room_not_found(client, auth_headers):
    resp = client.put('/api/v1/rooms/9999', headers=auth_headers, json={'price': 100})
    assert resp.status_code == 404
