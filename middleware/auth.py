"""
Middleware de validação JWT.
O uso de @jwt_required() nas rotas já faz a validação; este módulo pode
estender comportamentos (ex: verificar categoria do usuário).
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request


def admin_required():
    """Decorator que exige que o usuário seja ADMIN."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            from database.models import Usuario
            user_id = get_jwt_identity()
            usuario = Usuario.query.get(int(user_id))
            if not usuario or usuario.categoria != 'ADMIN':
                return jsonify({'erro': 'Acesso negado. Apenas administradores.'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
