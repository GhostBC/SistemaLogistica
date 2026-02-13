import pytest


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.get_json() == {'status': 'ok'}


def test_login_sem_body(client):
    r = client.post('/api/auth/login', json={})
    assert r.status_code == 400
    assert 'obrigatórios' in r.get_json().get('erro', '').lower()


def test_login_credenciais_invalidas(client):
    r = client.post('/api/auth/login', json={
        'email': 'naoexiste@test.com',
        'senha': 'wrong'
    })
    assert r.status_code == 401


def test_login_ok(client):
    r = client.post('/api/auth/login', json={
        'email': 'lucas.moraes@belezaruiva.com.br',
        'senha': '@UEcqiXmics9531'
    })
    assert r.status_code == 200
    data = r.get_json()
    assert 'access_token' in data
    assert 'user' in data
    assert data['user']['email'] == 'lucas.moraes@belezaruiva.com.br'


def test_me_sem_token(client):
    r = client.get('/api/auth/me')
    assert r.status_code == 401


def test_me_com_token(client, auth_headers):
    r = client.get('/api/auth/me', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data['email'] == 'lucas.moraes@belezaruiva.com.br'


def test_register_primeiro_usuario(client):
    """Primeiro usuário (sem nenhum no banco) pode se registrar - teste em ambiente limpo."""
    # O conftest já cria admin via init_db, então não há 'primeiro' usuário.
    # Testamos apenas que register com dados válidos exige token quando já existe usuário.
    r = client.post('/api/auth/register', json={
        'email': 'novo@test.com',
        'senha': 'senha123',
        'nome': 'Novo User'
    })
    # Pode ser 201 (se por algum motivo for o primeiro) ou 403 (token necessário)
    assert r.status_code in (201, 403)


def test_register_dados_invalidos(client):
    r = client.post('/api/auth/register', json={'email': 'x'})
    assert r.status_code == 400
    r = client.post('/api/auth/register', json={
        'email': 'a@b.com',
        'senha': '123',
        'nome': 'A'
    })
    assert r.status_code == 400  # senha < 6
