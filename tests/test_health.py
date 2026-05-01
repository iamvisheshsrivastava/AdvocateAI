import os

from fastapi.testclient import TestClient

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app


def test_root():
    client = TestClient(app)
    r = client.get('/')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_health():
    client = TestClient(app)
    r = client.get('/health')
    # Health may be degraded if DB isn't running; ensure response structure
    assert r.status_code in (200, 503)
    body = r.json()
    assert 'service' in body and body['service'] == 'AdvocateAI'
