"""
Utilitários para OAuth2 do Bling: armazenamento e renovação de tokens.
Os tokens são salvos em arquivo JSON (data/bling_tokens.json).
"""
import os
import json
import secrets
import requests
from datetime import datetime
from urllib.parse import urlencode

# Diretório e arquivo de tokens (na raiz do projeto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOKENS_FILE = os.path.join(DATA_DIR, 'bling_tokens.json')


def _get_config():
    return {
        'client_id': os.getenv('BLING_CLIENT_ID'),
        'client_secret': os.getenv('BLING_CLIENT_SECRET'),
        'redirect_uri': os.getenv('BLING_REDIRECT_URI'),
        'authorize_url': os.getenv('BLING_OAUTH_AUTHORIZE_URL', 'https://www.bling.com.br/Api/v3/oauth/authorize'),
        'token_url': os.getenv('BLING_OAUTH_TOKEN_URL', 'https://www.bling.com.br/Api/v3/oauth/token'),
    }


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_tokens():
    """Carrega tokens do arquivo. Retorna dict ou None."""
    if not os.path.isfile(TOKENS_FILE):
        return None
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _save_tokens(access_token, refresh_token, expires_in_seconds=None):
    """Salva tokens no arquivo."""
    _ensure_data_dir()
    data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'updated_at': datetime.utcnow().isoformat(),
    }
    if expires_in_seconds is not None:
        data['expires_in'] = expires_in_seconds
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def build_authorize_url(state=None):
    """
    Monta a URL para o usuário autorizar o app no Bling (Authorization Code).
    state: string opcional para CSRF; se None, gera um aleatório.
    """
    cfg = _get_config()
    if not cfg['client_id'] or not cfg['redirect_uri']:
        return None
    state = state or secrets.token_urlsafe(32)
    params = {
        'client_id': cfg['client_id'],
        'response_type': 'code',
        'state': state,
    }
    if cfg['redirect_uri']:
        params['redirect_uri'] = cfg['redirect_uri']
    base = cfg['authorize_url']
    sep = '&' if '?' in base else '?'
    url = base + sep + urlencode(params)
    return url, state


def exchange_code_for_tokens(code):
    """
    Troca o authorization code por access_token e refresh_token.
    Retorna (access_token, refresh_token, expires_in) ou (None, None, None) em caso de erro.
    """
    cfg = _get_config()
    if not all([cfg['client_id'], cfg['client_secret'], cfg['token_url']]):
        return None, None, None
    auth = (cfg['client_id'], cfg['client_secret'])
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
    }
    if cfg['redirect_uri']:
        payload['redirect_uri'] = cfg['redirect_uri']
    try:
        r = requests.post(
            cfg['token_url'],
            auth=auth,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        access = data.get('access_token')
        refresh = data.get('refresh_token')
        expires_in = data.get('expires_in')
        if access:
            _save_tokens(access, refresh or '', expires_in)
        return access, refresh, expires_in
    except Exception as e:
        print(f"Erro ao trocar code por tokens Bling: {e}")
        return None, None, None


def refresh_access_token():
    """
    Renova o access_token usando o refresh_token salvo.
    Retorna o novo access_token ou None.
    """
    tokens = _load_tokens()
    if not tokens or not tokens.get('refresh_token'):
        return None
    cfg = _get_config()
    if not all([cfg['client_id'], cfg['client_secret'], cfg['token_url']]):
        return None
    auth = (cfg['client_id'], cfg['client_secret'])
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token'],
    }
    try:
        r = requests.post(
            cfg['token_url'],
            auth=auth,
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        access = data.get('access_token')
        refresh = data.get('refresh_token', tokens['refresh_token'])
        expires_in = data.get('expires_in')
        if access:
            _save_tokens(access, refresh, expires_in)
        return access
    except Exception as e:
        print(f"Erro ao renovar token Bling: {e}")
        return None


def get_access_token():
    """
    Retorna o access_token válido para uso nas requisições à API Bling.
    Se houver token salvo, usa; se expirado, tenta refresh. Retorna None se indisponível.
    """
    tokens = _load_tokens()
    if tokens and tokens.get('access_token'):
        # Opcional: checar expiração se tiver expires_in e updated_at
        return tokens['access_token']
    new_token = refresh_access_token()
    return new_token


def has_tokens():
    """Retorna True se existir access_token (ou refresh_token) configurado."""
    t = _load_tokens()
    return bool(t and (t.get('access_token') or t.get('refresh_token')))
