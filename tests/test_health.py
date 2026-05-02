from fastapi.testclient import TestClient


def test_root():
    from app import app

    client = TestClient(app)
    r = client.get('/')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_health():
    from app import app

    client = TestClient(app)
    r = client.get('/health')
    # Health may be degraded if DB isn't running; ensure response structure
    assert r.status_code in (200, 503)
    body = r.json()
    assert 'service' in body and body['service'] == 'AdvocateAI'
