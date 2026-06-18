def test_login_success(client):
    resp = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'password123'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data

def test_login_wrong_password(client):
    resp = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'wrong'
    })
    assert resp.status_code == 401
    assert resp.get_json()['error'] == 'Invalid credentials'

def test_login_unknown_user(client):
    resp = client.post('/api/v1/auth/login', json={
        'username': 'nobody', 'password': 'x'
    })
    assert resp.status_code == 401

def test_refresh_token(client):
    login = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'password123'
    })
    refresh_token = login.get_json()['refresh_token']
    resp = client.post('/api/v1/auth/refresh',
        headers={'Authorization': f'Bearer {refresh_token}'})
    assert resp.status_code == 200
    assert 'access_token' in resp.get_json()

def test_logout(client, auth_headers):
    resp = client.post('/api/v1/auth/logout', headers=auth_headers)
    assert resp.status_code == 200

def test_protected_route_without_token(client):
    resp = client.get('/api/v1/rooms')
    assert resp.status_code == 401
