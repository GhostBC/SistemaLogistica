import pytest
import os
import sys

# Garantir que o projeto está no path e usar banco em memória nos testes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-with-at-least-32-chars'

from app import create_app
from database.models import db, Usuario


@pytest.fixture
def app():
    """App Flask para testes com banco em memória."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Faz login e retorna headers com Bearer token (admin)."""
    r = client.post('/api/auth/login', json={
        'email': 'lucas.moraes@belezaruiva.com.br',
        'senha': '@UEcqiXmics9531'
    })
    assert r.status_code == 200
    data = r.get_json()
    token = data['access_token']
    return {'Authorization': f'Bearer {token}'}
