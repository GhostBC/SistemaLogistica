"""
Tratamento global de erros da aplicação.
"""
from flask import jsonify


def register_error_handlers(app):
    """Registra handlers de erro na app Flask."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'erro': str(e) or 'Requisição inválida'}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'erro': 'Não autorizado'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'erro': 'Acesso negado'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'erro': 'Recurso não encontrado',
            'dica': 'Verifique a URL. Ex.: GET /health, GET /api/bling/authorize, POST /api/auth/login'
        }), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'erro': 'Erro interno do servidor'}), 500
