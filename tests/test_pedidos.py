import pytest
from app import create_app
from database.models import db, PedidoLogistica, Embalagem


def test_pedidos_lista_exige_auth(client):
    r = client.get('/api/pedidos')
    assert r.status_code == 401


def test_pedidos_lista_com_token(client, auth_headers):
    r = client.get('/api/pedidos', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)


def test_embalagens_lista(client, auth_headers):
    r = client.get('/api/embalagens', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    # init_db cria 4 embalagens padrão
    assert len(data) >= 4
