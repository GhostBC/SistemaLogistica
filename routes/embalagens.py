from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from services.embalagem_service import EmbalagemService

embalagens_bp = Blueprint('embalagens', __name__, url_prefix='/api/embalagens')


@embalagens_bp.route('', methods=['GET'])
@jwt_required()
def listar():
    """GET /api/embalagens. Query: ?status=ativo"""
    status = request.args.get('status')
    embalagens = EmbalagemService.listar(status=status)
    return jsonify([e.to_dict() for e in embalagens]), 200


@embalagens_bp.route('/<int:id_embalagem>', methods=['GET'])
@jwt_required()
def obter(id_embalagem):
    """GET /api/embalagens/{id}"""
    emb = EmbalagemService.obter(id_embalagem)
    if not emb:
        return jsonify({'erro': 'Embalagem não encontrada'}), 404
    return jsonify(emb.to_dict()), 200


@embalagens_bp.route('', methods=['POST'])
@jwt_required()
def criar():
    """POST /api/embalagens. Body: nome, custo, altura, largura, comprimento, peso (opcional)"""
    data = request.get_json()
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    nome = data.get('nome')
    custo = data.get('custo', 0)
    altura = data.get('altura', 0)
    largura = data.get('largura', 0)
    comprimento = data.get('comprimento', 0)
    peso = data.get('peso')
    estoque = data.get('estoque', 0)
    emb, err = EmbalagemService.criar(nome, custo, altura, largura, comprimento, peso, estoque=estoque)
    if err:
        return jsonify({'erro': err}), 400
    return jsonify(emb.to_dict()), 201


@embalagens_bp.route('/<int:id_embalagem>', methods=['PUT'])
@jwt_required()
def atualizar(id_embalagem):
    """PUT /api/embalagens/{id}. Body: nome, custo, altura, largura, comprimento, peso, status"""
    data = request.get_json() or {}
    emb, err = EmbalagemService.atualizar(id_embalagem, **data)
    if err:
        return jsonify({'erro': err}), 404 if err == 'Embalagem não encontrada' else 400
    return jsonify(emb.to_dict()), 200


@embalagens_bp.route('/<int:id_embalagem>', methods=['DELETE'])
@jwt_required()
def excluir(id_embalagem):
    """DELETE /api/embalagens/{id} (soft delete: status=inativo)"""
    ok, err = EmbalagemService.excluir(id_embalagem)
    if err:
        return jsonify({'erro': err}), 404
    return jsonify({'mensagem': 'Embalagem desativada'}), 200
