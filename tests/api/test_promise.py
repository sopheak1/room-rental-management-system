from datetime import date, timedelta
from app import db
from app.models import Building, Room, Tenant, Receipt
from app.utils.timezone import today as _today


def _seed(app):
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=200000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Chan', is_active=True, move_in_date=date(2026, 1, 1))
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


def test_get_receipt_promised_payment_date_defaults_to_null(client, auth_headers, app):
    receipt_id = _seed(app)
    resp = client.get(f'/api/v1/receipts/{receipt_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['promised_payment_date'] is None


def test_add_promise_success(client, auth_headers, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': tomorrow, 'notes': 'Will pay after payday'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['promised_payment_date'] == tomorrow


def test_add_promise_requires_date(client, auth_headers, app):
    receipt_id = _seed(app)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers, json={})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_add_promise_rejects_past_date(client, auth_headers, app):
    receipt_id = _seed(app)
    yesterday = (_today() - timedelta(days=1)).isoformat()
    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': yesterday})
    assert resp.status_code == 400


def test_add_promise_allows_today(client, auth_headers, app):
    receipt_id = _seed(app)
    today = _today().isoformat()
    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': today})
    assert resp.status_code == 200


def test_add_promise_blocked_when_next_receipt_exists(client, auth_headers, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    with app.app_context():
        receipt = Receipt.query.get(receipt_id)
        next_receipt = Receipt(
            receipt_number='RCP-202607-0001', room_id=receipt.room_id, tenant_id=receipt.tenant_id,
            billing_month=7, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(next_receipt)
        db.session.commit()

    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': tomorrow})

    assert resp.status_code == 400


def test_add_promise_requires_auth(client, app):
    receipt_id = _seed(app)
    resp = client.post(f'/api/v1/receipts/{receipt_id}/promise', json={'promised_date': '2026-07-01'})
    assert resp.status_code == 401


def test_add_promise_bumps_receipt_updated_at_for_sync(client, auth_headers, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    with app.app_context():
        before = Receipt.query.get(receipt_id).updated_at

    client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': tomorrow})

    with app.app_context():
        after = Receipt.query.get(receipt_id).updated_at
        assert after > before


def test_sync_includes_promised_payment_date(client, auth_headers, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    client.post(f'/api/v1/receipts/{receipt_id}/promise', headers=auth_headers,
        json={'promised_date': tomorrow})

    resp = client.get('/api/v1/sync?since=2000-01-01T00:00:00', headers=auth_headers)

    assert resp.status_code == 200
    receipts = resp.get_json()['receipts']
    matching = next(r for r in receipts if r['id'] == receipt_id)
    assert matching['promised_payment_date'] == tomorrow
