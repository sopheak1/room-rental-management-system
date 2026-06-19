import os
import pytest

# Must be set before create_app() runs — create_app() itself calls db.create_all()
# against whatever SQLALCHEMY_DATABASE_URI is in config.py at that point, and
# Flask-SQLAlchemy caches the engine on first use. Overriding the URI *after*
# create_app() returns is too late and silently falls through to the real
# instance/rental.db file (this previously wiped the live database).
os.environ['RENTAL_TESTING'] = '1'

from app import create_app, db as _db
from app.models import User

@pytest.fixture(scope='function')
def app():
    # Create app with in-memory SQLite database
    app = create_app()
    app.config.update({
        'TESTING': True,
        'JWT_SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:', \
        'Refusing to run tests against a non-in-memory database'
    with app.app_context():
        # Explicitly remove and drop any existing session/tables
        _db.session.remove()
        _db.drop_all()
        # Create fresh tables
        _db.create_all()
        # Create admin user
        user = User(username='admin', full_name='Admin')
        user.set_password('password123')
        _db.session.add(user)
        _db.session.commit()
        yield app
        # Cleanup
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    resp = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'password123'
    })
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
