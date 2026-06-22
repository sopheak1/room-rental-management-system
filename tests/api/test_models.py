import pytest
from datetime import date
from app.models import Building, Room, Tenant, Receipt, ConflictLog, PromisedPaymentLog
from app import db

def test_building_has_updated_at(app):
    with app.app_context():
        b = Building(name='Test', address='123 St')
        db.session.add(b)
        db.session.commit()
        assert b.updated_at is not None

def test_room_has_updated_at(app):
    with app.app_context():
        b = Building(name='B', address='')
        db.session.add(b)
        db.session.flush()
        r = Room(building_id=b.id, room_number='101', price=100000)
        db.session.add(r)
        db.session.commit()
        assert r.updated_at is not None

def test_conflict_log_model_exists(app):
    with app.app_context():
        cl = ConflictLog(
            entity_type='receipt',
            entity_id=1,
            mobile_data_json='{}',
            server_data_json='{}',
            status='pending_review'
        )
        db.session.add(cl)
        db.session.commit()
        assert cl.id is not None
        assert cl.conflict_at is not None

def _make_receipt():
    b = Building(name='B', address='')
    db.session.add(b)
    db.session.flush()
    r = Room(building_id=b.id, room_number='101', price=200000)
    db.session.add(r)
    db.session.flush()
    receipt = Receipt(
        receipt_number='RCP-202606-0001', room_id=r.id,
        billing_month=6, billing_year=2026, room_price=200000,
        total_amount=200000, remaining_balance=200000, payment_status='unpaid'
    )
    db.session.add(receipt)
    db.session.commit()
    return receipt

def test_receipt_has_no_promised_date_by_default(app):
    with app.app_context():
        receipt = _make_receipt()
        assert receipt.current_promised_date is None
        assert list(receipt.promised_payment_logs) == []

def test_current_promised_date_returns_most_recent(app):
    with app.app_context():
        receipt = _make_receipt()
        db.session.add(PromisedPaymentLog(
            receipt_id=receipt.id, promised_date=date(2026, 6, 20), notes='first promise'
        ))
        db.session.commit()
        db.session.add(PromisedPaymentLog(
            receipt_id=receipt.id, promised_date=date(2026, 6, 25), notes='broke first promise'
        ))
        db.session.commit()
        assert receipt.current_promised_date == date(2026, 6, 25)
        assert len(receipt.promised_payment_logs) == 2

def test_promised_payment_log_requires_receipt_and_date(app):
    with app.app_context():
        receipt = _make_receipt()
        log = PromisedPaymentLog(receipt_id=receipt.id, promised_date=date(2026, 7, 1))
        db.session.add(log)
        db.session.commit()
        assert log.id is not None
        assert log.notes is None
        assert log.created_at is not None
