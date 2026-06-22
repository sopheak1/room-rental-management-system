"""
Tests for the "Promised Payment Date" web route — POST /receipts/<id>/promise.
Run: venv/bin/pytest tests/test_promise_route.py -v
"""
import itertools
from datetime import date, timedelta
from app import db
from app.models import Building, Room, Tenant, Receipt, PromisedPaymentLog
from app.utils.timezone import today as _today

_seq = itertools.count(1)


def _seed(app, payment_status='unpaid'):
    n = next(_seq)
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number=f'10{n}', price=200000, status='occupied')
        db.session.add(r)
        db.session.flush()
        t = Tenant(room_id=r.id, name='Chan', is_active=True, move_in_date=date(2026, 1, 1))
        db.session.add(t)
        db.session.flush()
        receipt = Receipt(
            receipt_number=f'RCP-PROMISE-{n:04d}', room_id=r.id, tenant_id=t.id,
            billing_month=6, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status=payment_status
        )
        db.session.add(receipt)
        db.session.commit()
        return receipt.id


def test_add_promise_succeeds_for_unpaid_receipt(logged_in_client, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    resp = logged_in_client.post(f'/receipts/{receipt_id}/promise',
        data={'promised_date': tomorrow, 'notes': 'Will pay after payday'}, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        receipt = Receipt.query.get(receipt_id)
        assert receipt.current_promised_date.isoformat() == tomorrow
        log = PromisedPaymentLog.query.filter_by(receipt_id=receipt_id).first()
        assert log.notes == 'Will pay after payday'


def test_add_promise_bumps_receipt_updated_at(logged_in_client, app):
    """A promise lives in a separate table, so it never touches the receipts
    row — the model's onupdate=datetime.utcnow trigger won't fire on its own.
    Mobile's delta sync (GET /api/v1/sync?since=...) filters receipts by
    Receipt.updated_at, so without an explicit bump here, a promise set on
    web would never reach an already-synced mobile device."""
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    with app.app_context():
        before = Receipt.query.get(receipt_id).updated_at

    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': tomorrow})

    with app.app_context():
        after = Receipt.query.get(receipt_id).updated_at
        assert after > before


def test_add_promise_requires_date(logged_in_client, app):
    receipt_id = _seed(app)

    resp = logged_in_client.post(f'/receipts/{receipt_id}/promise',
        data={'notes': 'no date given'}, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        assert PromisedPaymentLog.query.filter_by(receipt_id=receipt_id).count() == 0


def test_add_promise_rejects_past_date(logged_in_client, app):
    receipt_id = _seed(app)
    yesterday = (_today() - timedelta(days=1)).isoformat()

    resp = logged_in_client.post(f'/receipts/{receipt_id}/promise',
        data={'promised_date': yesterday}, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        assert PromisedPaymentLog.query.filter_by(receipt_id=receipt_id).count() == 0


def test_add_promise_allows_today(logged_in_client, app):
    receipt_id = _seed(app)
    today = _today().isoformat()

    resp = logged_in_client.post(f'/receipts/{receipt_id}/promise',
        data={'promised_date': today}, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        assert PromisedPaymentLog.query.filter_by(receipt_id=receipt_id).count() == 1


def test_add_promise_blocked_when_next_receipt_exists(logged_in_client, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    with app.app_context():
        receipt = Receipt.query.get(receipt_id)
        next_receipt = Receipt(
            receipt_number=f'RCP-PROMISE-NEXT-{next(_seq)}', room_id=receipt.room_id, tenant_id=receipt.tenant_id,
            billing_month=7, billing_year=2026, room_price=200000,
            total_amount=200000, paid_amount=0, remaining_balance=200000,
            payment_status='unpaid'
        )
        db.session.add(next_receipt)
        db.session.commit()

    resp = logged_in_client.post(f'/receipts/{receipt_id}/promise',
        data={'promised_date': tomorrow}, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        assert PromisedPaymentLog.query.filter_by(receipt_id=receipt_id).count() == 0


def test_detail_page_renders_with_and_without_promise(logged_in_client, app):
    receipt_id = _seed(app)

    resp = logged_in_client.get(f'/receipts/{receipt_id}')
    assert resp.status_code == 200
    assert b'setPromiseModal' in resp.data
    assert b'Promise History' not in resp.data

    tomorrow = (_today() + timedelta(days=1)).isoformat()
    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': tomorrow})

    resp = logged_in_client.get(f'/receipts/{receipt_id}')
    assert resp.status_code == 200
    assert b'Promise History' in resp.data
    assert b'Promised Date' in resp.data


def _room_number(app, receipt_id):
    with app.app_context():
        return Receipt.query.get(receipt_id).room.room_number


def _card_html_for_room(resp, room_number):
    """The dashboard renders one dash-room-card per room — the session-scoped
    `app` fixture means OTHER tests' overdue rooms are still on the page, so
    badge assertions must be scoped to this test's own room card, not the
    whole response body."""
    html = resp.data.decode()
    start = html.index(room_number)
    end = html.index('</a>', start)
    return html[start:end]


def test_dashboard_overdue_tab_shows_overdue_badge_without_promise(logged_in_client, app):
    # _seed()'s receipt is billing_month=6/2026 (this month) and the tenant's
    # move_in_date is day 1, so the dashboard naturally classifies it as
    # overdue (today_day >= start_day, receipt not paid/deferred) without
    # needing to fake the billing period.
    receipt_id = _seed(app)
    room_number = _room_number(app, receipt_id)

    resp = logged_in_client.get('/')

    assert resp.status_code == 200
    card = _card_html_for_room(resp, room_number)
    assert 'dash-badge-overdue' in card
    assert 'dash-badge-promised' not in card


def test_dashboard_overdue_tab_shows_promise_badge_instead_of_overdue(logged_in_client, app):
    receipt_id = _seed(app)
    room_number = _room_number(app, receipt_id)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': tomorrow})

    resp = logged_in_client.get('/')

    assert resp.status_code == 200
    card = _card_html_for_room(resp, room_number)
    assert 'dash-badge-promised' in card
    assert 'dash-badge-overdue' not in card


def test_print_table_renders_promise_line(logged_in_client, app):
    receipt_id = _seed(app)
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': tomorrow})

    resp = logged_in_client.get(f'/receipts/{receipt_id}/print_table')

    assert resp.status_code == 200
    assert 'សន្យាបង់'.encode() in resp.data


def test_multiple_promises_keep_full_history(logged_in_client, app):
    receipt_id = _seed(app)
    day1 = (_today() + timedelta(days=1)).isoformat()
    day2 = (_today() + timedelta(days=5)).isoformat()

    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': day1})
    logged_in_client.post(f'/receipts/{receipt_id}/promise', data={'promised_date': day2})

    with app.app_context():
        receipt = Receipt.query.get(receipt_id)
        assert len(receipt.promised_payment_logs) == 2
        assert receipt.current_promised_date.isoformat() == day2
