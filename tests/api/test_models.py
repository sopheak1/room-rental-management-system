import pytest
from app.models import Building, Room, Tenant, Receipt, ConflictLog
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
