from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database.models import db, Usuario
from datetime import timedelta
from utils.validators import is_valid_email

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Body: { "email": "...", "senha": "...", "nome": "..." }
    Apenas ADMIN pode criar usuários, ou o primeiro usuário do sistema.
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('senha') or not data.get('nome'):
        return jsonify({'erro': 'Email, senha e nome são obrigatórios'}), 400

    email = data['email'].strip().lower()
    senha = data['senha']
    nome = data.get('nome', '').strip()

    if not is_valid_email(email):
        return jsonify({'erro': 'Email inválido'}), 400

    if len(senha) < 6:
        return jsonify({'erro': 'Senha deve ter no mínimo 6 caracteres'}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({'erro': 'Email já cadastrado'}), 409

    # Primeiro usuário do sistema vira ADMIN; demais precisam ser criados por ADMIN
    eh_primeiro = Usuario.query.count() == 0
    categoria = data.get('categoria', 'ADMIN' if eh_primeiro else 'USER_LOGISTICA')

    if not eh_primeiro:
        # Verificar se quem está criando é ADMIN (via token)
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                criador = Usuario.query.get(int(user_id))
                if not criador or criador.categoria != 'ADMIN':
                    return jsonify({'erro': 'Apenas administradores podem criar usuários'}), 403
            else:
                return jsonify({'erro': 'Token de administrador necessário para criar usuário'}), 403
        except Exception:
            return jsonify({'erro': 'Token de administrador necessário para criar usuário'}), 403
        categoria = data.get('categoria', 'USER_LOGISTICA')

    usuario = Usuario(
        email=email,
        nome=nome or email.split('@')[0],
        categoria=categoria,
        status='ativo'
    )
    usuario.set_password(senha)
    db.session.add(usuario)
    db.session.commit()
    current_app.logger.info(f"Usuário criado: {email} (categoria={categoria})")
    return jsonify(usuario.to_dict()), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Body: { "email": "user@example.com", "senha": "senha123" }
    Response: { "access_token": "...", "user": {...} }
    """
    data = request.get_json()

    if not data or not data.get('email') or not data.get('senha'):
        return jsonify({'erro': 'Email e senha são obrigatórios'}), 400

    usuario = Usuario.query.filter_by(email=data['email'].strip()).first()

    if not usuario or not usuario.check_password(data['senha']):
        return jsonify({'erro': 'Email ou senha inválidos'}), 401

    if usuario.status != 'ativo':
        return jsonify({'erro': 'Usuário inativo'}), 403

    access_token = create_access_token(
        identity=str(usuario.id),
        expires_delta=timedelta(hours=24)
    )

    return jsonify({
        'access_token': access_token,
        'user': usuario.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """
    GET /api/auth/me
    Headers: { "Authorization": "Bearer {token}" }
    Response: { usuario data }
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(int(user_id))

    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    return jsonify(usuario.to_dict()), 200
