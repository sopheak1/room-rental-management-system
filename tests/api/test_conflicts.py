import json

def test_save_conflict(client, auth_headers):
    resp = client.post('/api/v1/conflicts', headers=auth_headers, json={
        'entity_type': 'receipt', 'entity_id': 1,
        'mobile_data': {'total_amount': 200000},
        'server_data': {'total_amount': 250000}
    })
    assert resp.status_code == 201
    assert 'id' in resp.get_json()

def test_resolve_keep_server(client, auth_headers):
    create = client.post('/api/v1/conflicts', headers=auth_headers, json={
        'entity_type': 'receipt', 'entity_id': 1,
        'mobile_data': {}, 'server_data': {}
    })
    conflict_id = create.get_json()['id']
    resp = client.post(f'/api/v1/conflicts/{conflict_id}/resolve-keep', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'resolved_keep'

def test_resolve_override(client, auth_headers, app):
    from app import db
    from app.models import Building, Room, Receipt
    from datetime import date
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=200000, status='occupied')
        db.session.add(r)
        db.session.flush()
        receipt = Receipt(
            receipt_number='RCP-202606-0001', room_id=r.id,
            billing_month=6, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(receipt)
        db.session.commit()
        receipt_id = receipt.id
    create = client.post('/api/v1/conflicts', headers=auth_headers, json={
        'entity_type': 'receipt', 'entity_id': receipt_id,
        'mobile_data': {'notes': 'override note'}, 'server_data': {'notes': ''}
    })
    conflict_id = create.get_json()['id']
    resp = client.post(f'/api/v1/conflicts/{conflict_id}/override', headers=auth_headers)
    assert resp.status_code == 200
