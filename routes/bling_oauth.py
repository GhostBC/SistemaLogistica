"""
Rotas para o fluxo OAuth2 do Bling (authorize + callback).
Permitem que o usuário autorize o app no Bling e o sistema armazene os tokens.
"""
from flask import Blueprint, request, jsonify, redirect
from utils.bling_oauth import (
    build_authorize_url,
    exchange_code_for_tokens,
    has_tokens,
    get_access_token,
)

bling_oauth_bp = Blueprint('bling_oauth', __name__, url_prefix='/api/bling')


@bling_oauth_bp.route('/authorize', methods=['GET'])
def authorize():
    """
    GET /api/bling/authorize
    Redireciona o usuário para a tela de autorização OAuth2 do Bling.
    Após autorizar, o Bling redireciona para BLING_REDIRECT_URI (callback) com ?code=...&state=...
    """
    url_with_state = build_authorize_url()
    if not url_with_state:
        from utils.bling_oauth import _get_config
        cfg = _get_config()
        faltando = [k for k, v in [('BLING_CLIENT_ID', cfg['client_id']), ('BLING_REDIRECT_URI', cfg['redirect_uri'])] if not v]
        return jsonify({
            'erro': 'Bling OAuth não configurado. Defina no .env: ' + ', '.join(faltando) + '. Reinicie o servidor após alterar o .env (python app.py).'
        }), 400
    # build_authorize_url retorna (url, state); a URL já inclui state
    if isinstance(url_with_state, tuple):
        url_to_redirect = url_with_state[0]
    else:
        url_to_redirect = url_with_state
    return redirect(url_to_redirect)


@bling_oauth_bp.route('/callback', methods=['GET'])
def callback():
    """
    GET /api/bling/callback?code=...&state=...
    URL de redirecionamento configurada no aplicativo Bling (BLING_REDIRECT_URI).
    Troca o code por access_token e refresh_token e salva no arquivo data/bling_tokens.json.
    """
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return jsonify({'erro': 'Parâmetro code ausente na URL de callback'}), 400

    access_token, refresh_token, expires_in = exchange_code_for_tokens(code)
    if not access_token:
        return jsonify({
            'erro': 'Não foi possível obter os tokens do Bling. Verifique BLING_CLIENT_ID, BLING_CLIENT_SECRET e BLING_REDIRECT_URI.'
        }), 400

    return jsonify({
        'mensagem': 'Bling conectado com sucesso. Os tokens foram salvos.',
        'access_token_obtido': True,
        'expires_in': expires_in,
    }), 200


@bling_oauth_bp.route('/status', methods=['GET'])
def status():
    """
    GET /api/bling/status
    Indica se há tokens Bling configurados (útil para o frontend saber se precisa autorizar).
    """
    return jsonify({
        'conectado': has_tokens(),
        'tem_token': bool(get_access_token()),
    }), 200
