import os
import pytest

# Must be set before create_app() runs — see tests/api/conftest.py for why.
os.environ['RENTAL_TESTING'] = '1'

from app import create_app, db as _db
from app.models import User


@pytest.fixture(scope='session')
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
        'SECRET_KEY': 'test-secret',
    })
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:', \
        'Refusing to run tests against a non-in-memory database'
    with app.app_context():
        _db.create_all()
        # Create a test user
        user = User(username='testuser')
        user.set_password('testpass')
        _db.session.add(user)
        _db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in_client(client):
    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    return client
