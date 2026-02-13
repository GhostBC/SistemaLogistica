"""
Rotas de administração (ex.: limpar dados em desenvolvimento).
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from database.models import db, CustoFrete, PedidoLogistica, Auditoria

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/limpar-dados', methods=['POST'])
@jwt_required()
def limpar_dados():
    """
    POST /api/admin/limpar-dados
    Remove todos os pedidos e custos do banco (desenvolvimento).
    Permite sincronizar novamente com o Bling do zero.
    Usuários e embalagens são mantidos.
    """
    try:
        # Ordem: CustoFrete tem FK para pedidos_logistica
        deletados_custos = CustoFrete.query.delete()
        deletados_pedidos = PedidoLogistica.query.delete()
        deletados_auditoria = Auditoria.query.filter(
            Auditoria.recurso == 'pedido'
        ).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({
            'mensagem': 'Dados de pedidos e custos removidos. Sincronize novamente com o Bling.',
            'deletados': {
                'custos_frete': deletados_custos,
                'pedidos': deletados_pedidos,
                'auditoria_pedidos': deletados_auditoria,
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
