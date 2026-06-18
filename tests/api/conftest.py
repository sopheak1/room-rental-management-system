import pytest
from app import create_app, db as _db
from app.models import User

@pytest.fixture(scope='function')
def app():
    # Create app with in-memory SQLite database
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
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
