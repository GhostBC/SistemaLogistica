import io
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import db, PedidoLogistica, Embalagem, Auditoria, CustoFrete, Usuario, CacheSincronizacao, PedidoEmbalagem
from services.bling_service import BlingService
from services.custo_service import CustoService
from config import Config
from datetime import datetime, timedelta, date
from middleware.auth import admin_required

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/pedidos')

# Mapeamento de loja.id para nome da loja
LOJA_ID_TO_NOME = {
    205483326: 'TikTok',
    204638501: 'Shopee',
    204701093: 'Tray',
    204638516: 'Mercado Livre',
    204786235: 'Shein',
    0: 'Época',
    205175249: 'BLZWEB',
    205315713: 'Loja Física',
    205513975: 'Ifood',
    'AmazonMBS': 'Amazon Serviços de Varejo do Brasil Ltda',
}


def traduzir_loja_id(loja_id):
    """Traduz loja_id para nome da loja."""
    if loja_id is None:
        return None
    # Tentar como int primeiro
    try:
        loja_id_int = int(loja_id)
        return LOJA_ID_TO_NOME.get(loja_id_int)
    except (ValueError, TypeError):
        pass
    # Tentar como string
    return LOJA_ID_TO_NOME.get(str(loja_id)) or LOJA_ID_TO_NOME.get(loja_id)


def _sincronizar_pedidos_bling():
    """Busca pedidos em aberto no Bling; remove do banco os abertos que não estão mais no Bling; insere/atualiza o restante."""
    pedidos_bling = BlingService.buscar_pedidos_abertos()
    numeros_no_bling = {str(p['numero_pedido']) for p in pedidos_bling}

    # Limpeza: remover pedidos em aberto que já não existem no Bling (renovar lista)
    pedidos_abertos_locais = PedidoLogistica.query.filter_by(status='aberto').all()
    for p in pedidos_abertos_locais:
        if p.numero_pedido not in numeros_no_bling:
            db.session.delete(p)

    inseridos = 0
    atualizados = 0
    for pedido in pedidos_bling:
        existe = PedidoLogistica.query.filter_by(
            numero_pedido=str(pedido['numero_pedido'])
        ).first()
        if not existe:
            novo = PedidoLogistica(
                numero_pedido=str(pedido['numero_pedido']),
                id_bling=str(pedido['id_bling']),
                marketplace='site',
                frete_cliente=float(pedido.get('frete', 0) or 0),
                transportadora=pedido.get('transportadora'),
                tracking_code=pedido.get('tracking_code'),
                numero_loja=pedido.get('numero_loja'),
                loja_id=str(pedido.get('loja_id')) if pedido.get('loja_id') else None,
                status='aberto'
            )
            db.session.add(novo)
            inseridos += 1
        else:
            # Atualizar numero_loja e loja_id se não estiverem preenchidos e vierem do Bling
            if not existe.numero_loja and pedido.get('numero_loja'):
                existe.numero_loja = pedido.get('numero_loja')
                atualizados += 1
            if not existe.loja_id and pedido.get('loja_id'):
                existe.loja_id = str(pedido.get('loja_id'))
                atualizados += 1
    
    # Atualizar timestamp da última sincronização
    cache = CacheSincronizacao.query.filter_by(tipo='pedidos_abertos').first()
    if cache:
        cache.ultima_sincronizacao = datetime.utcnow()
    else:
        cache = CacheSincronizacao(tipo='pedidos_abertos', ultima_sincronizacao=datetime.utcnow())
        db.session.add(cache)
    
    db.session.commit()
    return inseridos


def _deve_sincronizar_automaticamente():
    """Verifica se deve sincronizar automaticamente baseado no timestamp da última sincronização.
    Retorna True se passou mais de 30 minutos desde a última sincronização."""
    cache = CacheSincronizacao.query.filter_by(tipo='pedidos_abertos').first()
    if not cache:
        return True  # Se nunca sincronizou, deve sincronizar
    
    tempo_decorrido = datetime.utcnow() - cache.ultima_sincronizacao
    minutos_decorridos = tempo_decorrido.total_seconds() / 60
    
    return minutos_decorridos >= 30


@pedidos_bp.route('', methods=['POST'])
@jwt_required()
def criar_pedido_manual():
    """
    POST /api/pedidos
    Body: { "numero_pedido": "...", "marketplace": "...", "frete_cliente": 0.0, "id_bling": "...", "loja_id": "...", "numero_loja": "..." }
    Cria um pedido manualmente. Se id_bling for enviado (após buscar no Bling), armazena para sincronização.
    """
    try:
        data = request.get_json() or {}
        numero_pedido = (data.get('numero_pedido') or '').strip()
        marketplace = (data.get('marketplace') or '').strip()
        frete_cliente = data.get('frete_cliente', 0.0)
        id_bling = (data.get('id_bling') or '').strip()
        loja_id = str(data.get('loja_id')).strip() if data.get('loja_id') is not None else None
        numero_loja = (data.get('numero_loja') or '').strip() or None
        
        if not numero_pedido:
            return jsonify({'erro': 'Número do pedido é obrigatório'}), 400
        if not marketplace:
            return jsonify({'erro': 'Marketplace é obrigatório'}), 400
        
        existe = PedidoLogistica.query.filter_by(numero_pedido=numero_pedido).first()
        if existe:
            return jsonify({'erro': 'Pedido já existe'}), 409
        
        pedido = PedidoLogistica(
            numero_pedido=numero_pedido,
            id_bling=id_bling or '',
            marketplace=marketplace,
            status='aberto',
            frete_cliente=float(frete_cliente) if frete_cliente else 0.0,
            numero_loja=numero_loja,
            loja_id=loja_id or None
        )
        db.session.add(pedido)
        db.session.commit()
        
        return jsonify(pedido.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/lojas', methods=['GET'])
@jwt_required()
def listar_lojas():
    """
    GET /api/pedidos/lojas
    Retorna: lista de nomes das lojas (Bling) para o submenu Pedidos.
    """
    lojas = list(Config.BLING_LOJAS.values())
    return jsonify({'lojas': lojas}), 200


@pedidos_bp.route('', methods=['GET'])
@jwt_required()
def listar_pedidos():
    """
    GET /api/pedidos
    Query: ?sincronizar=1 para forçar sincronização com Bling antes de listar (só pedidos em aberto).
    Query: ?marketplace=NomeDaLoja para filtrar por loja (ex: TikTok, Shopee).
    Query: ?status=finalizado para listar pedidos finalizados (aba Finalizados).
    Query: ?busca=termo para buscar por número do pedido, marketplace ou transportadora.
    Retorna: lista de pedidos (abertos ou finalizados conforme status).
    """
    try:
        from sqlalchemy import or_

        status = (request.args.get('status') or '').strip() or 'aberto'
        if status != 'finalizado':
            status = 'aberto'

        # Sincronizar apenas se solicitado explicitamente ou se passou mais de 30 minutos
        sincronizar_explicito = request.args.get('sincronizar')
        if status == 'aberto':
            if sincronizar_explicito:
                # Sincronização forçada pelo usuário
                _sincronizar_pedidos_bling()
            elif _deve_sincronizar_automaticamente():
                # Sincronização automática (após 30 minutos)
                _sincronizar_pedidos_bling()

        q = PedidoLogistica.query.filter_by(status=status)
        
        # Filtro por marketplace (nome da loja, ex: TikTok, Shopee)
        marketplace = request.args.get('marketplace')
        if marketplace and marketplace.strip():
            q = q.filter_by(marketplace=marketplace.strip())
        
        # Filtro por loja (nome traduzido: TikTok, Tray, etc.) — para abas Pedidos e Finalizados
        loja = request.args.get('loja')
        if loja and loja.strip():
            nome_to_id = {v: str(k) for k, v in LOJA_ID_TO_NOME.items()}
            loja_id_str = nome_to_id.get(loja.strip())
            if loja_id_str is not None:
                q = q.filter(PedidoLogistica.loja_id == loja_id_str)
        
        # Filtro de busca (número do pedido, canal/loja, marketplace, transportadora, rastreio)
        busca = request.args.get('busca')
        if busca and busca.strip():
            termo_busca = f"%{busca.strip()}%"
            q = q.filter(
                or_(
                    PedidoLogistica.numero_pedido.like(termo_busca),
                    PedidoLogistica.numero_loja.like(termo_busca),
                    PedidoLogistica.marketplace.like(termo_busca),
                    PedidoLogistica.transportadora.like(termo_busca),
                    PedidoLogistica.tracking_code.like(termo_busca)
                )
            )
        
        total = q.count()
        per_page = min(max(1, int(request.args.get('per_page', 100))), 100)
        page = max(1, int(request.args.get('page', 1)))
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        order_by = (request.args.get('order_by') or '').strip() or 'data_finalizacao'
        sort_dir = (request.args.get('sort') or '').strip().lower() or 'desc'
        if sort_dir not in ('asc', 'desc'):
            sort_dir = 'desc'
        order_column = None
        if status == 'finalizado':
            col_map = {
                'numero_pedido': PedidoLogistica.numero_pedido,
                'loja': PedidoLogistica.loja_id,
                'marketplace': PedidoLogistica.marketplace,
                'frete_cliente': PedidoLogistica.frete_cliente,
                'peso': PedidoLogistica.peso,
                'transportadora': PedidoLogistica.transportadora,
                'tracking_code': PedidoLogistica.tracking_code,
                'data_finalizacao': PedidoLogistica.data_finalizacao,
            }
            order_column = col_map.get(order_by) or PedidoLogistica.data_finalizacao
            if sort_dir == 'asc':
                q = q.order_by(order_column.asc())
            else:
                q = q.order_by(order_column.desc())
        
        if status == 'finalizado':
            pedidos_bd = q.offset(offset).limit(per_page).all()
        else:
            pedidos_bd = q.order_by(PedidoLogistica.data_abertura).offset(offset).limit(per_page).all()

        if not pedidos_bd and status == 'aberto' and not marketplace and not loja and not busca:
            # Se não há pedidos e não foi sincronizado ainda, sincronizar
            if _deve_sincronizar_automaticamente():
                _sincronizar_pedidos_bling()
            q_abertos = PedidoLogistica.query.filter_by(status='aberto')
            total = q_abertos.count()
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
            pedidos_bd = q_abertos.order_by(PedidoLogistica.data_abertura).offset(offset).limit(per_page).all()

        resultado = []
        for p in pedidos_bd:
            d = p.to_dict()
            if status == 'finalizado':
                custo = CustoFrete.query.filter_by(numero_pedido=p.numero_pedido).first()
                if custo:
                    d['custo_mandae'] = custo.custo_mandae
            # Adicionar nome da loja traduzido
            if p.loja_id:
                d['loja_nome'] = traduzir_loja_id(p.loja_id)
            else:
                d['loja_nome'] = None
            resultado.append(d)
        
        # Resposta com paginação
        payload = {
            'pedidos': resultado,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }
        if status == 'aberto':
            cache = CacheSincronizacao.query.filter_by(tipo='pedidos_abertos').first()
            if cache:
                payload['ultima_sincronizacao'] = cache.ultima_sincronizacao.isoformat()
        
        return jsonify(payload), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/exportar-finalizados', methods=['GET'])
@jwt_required()
def exportar_finalizados_excel():
    """
    GET /api/pedidos/exportar-finalizados?loja=...&busca=...
    Exporta pedidos finalizados para Excel (mesmos filtros: loja e busca). Limite 10000 registros.
    """
    try:
        from sqlalchemy import or_
        from utils.excel_exporter import exportar_finalizados as gerar_excel_finalizados

        q = PedidoLogistica.query.filter_by(status='finalizado')
        loja = request.args.get('loja')
        if loja and loja.strip():
            nome_to_id = {v: str(k) for k, v in LOJA_ID_TO_NOME.items()}
            loja_id_str = nome_to_id.get(loja.strip())
            if loja_id_str is not None:
                q = q.filter(PedidoLogistica.loja_id == loja_id_str)
        busca = request.args.get('busca')
        if busca and busca.strip():
            termo_busca = f"%{busca.strip()}%"
            q = q.filter(
                or_(
                    PedidoLogistica.numero_pedido.like(termo_busca),
                    PedidoLogistica.numero_loja.like(termo_busca),
                    PedidoLogistica.marketplace.like(termo_busca),
                    PedidoLogistica.transportadora.like(termo_busca),
                    PedidoLogistica.tracking_code.like(termo_busca)
                )
            )
        pedidos_bd = q.order_by(PedidoLogistica.data_finalizacao.desc()).limit(10000).all()
        resultado = []
        for p in pedidos_bd:
            d = p.to_dict()
            custo = CustoFrete.query.filter_by(numero_pedido=p.numero_pedido).first()
            if custo:
                d['custo_mandae'] = custo.custo_mandae
            d['loja_nome'] = traduzir_loja_id(p.loja_id) if p.loja_id else None
            resultado.append(d)

        buffer = gerar_excel_finalizados(resultado)
        nome_arquivo = 'finalizados-' + date.today().isoformat() + '.xlsx'
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/sincronizar', methods=['POST'])
@jwt_required()
def sincronizar_pedidos():
    """
    POST /api/pedidos/sincronizar
    Força sincronização com Bling (busca pedidos abertos e insere os novos).
    Retorna: { "mensagem": "...", "inseridos": N }
    """
    try:
        inseridos = _sincronizar_pedidos_bling()
        return jsonify({
            'mensagem': f'Sincronização concluída. {inseridos} novo(s) pedido(s) inserido(s).',
            'inseridos': inseridos
        }), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/bling/<id_bling>', methods=['GET'])
@jwt_required()
def get_pedido_bling(id_bling):
    """
    GET /api/pedidos/bling/{id_bling}
    Busca dados do pedido no Bling pelo ID (para adicionar pedido manual).
    Retorna: numero_pedido, id_bling, frete_cliente, transportadora, tracking_code, loja_id, numero_loja, loja_nome.
    """
    try:
        id_str = (id_bling or '').strip()
        if not id_str:
            return jsonify({'erro': 'ID do pedido (Bling) é obrigatório'}), 400
        detalhes = BlingService.buscar_detalhes_pedido(id_str)
        if detalhes is None:
            return jsonify({'erro': 'Pedido não encontrado no Bling ou erro ao consultar'}), 404
        loja_nome = traduzir_loja_id(detalhes.get('loja_id')) if detalhes.get('loja_id') else None
        out = {k: v for k, v in detalhes.items()}
        out['loja_nome'] = loja_nome
        return jsonify(out), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/obter-rastreio-em-lote', methods=['POST'])
@jwt_required()
def obter_rastreio_em_lote():
    """
    POST /api/pedidos/obter-rastreio-em-lote
    Busca código de rastreio no Bling para todos os pedidos finalizados sem rastreio.
    Intervalo de 5 segundos entre cada requisição ao Bling.
    Retorna: { atualizados: N, erros: [...] }
    """
    import time
    try:
        from sqlalchemy import or_
        pedidos_sem_rastreio = PedidoLogistica.query.filter(
            PedidoLogistica.status == 'finalizado',
            or_(
                PedidoLogistica.tracking_code.is_(None),
                PedidoLogistica.tracking_code == ''
            ),
            PedidoLogistica.id_bling.isnot(None),
            PedidoLogistica.id_bling != ''
        ).all()
        atualizados = 0
        erros = []
        for i, pedido in enumerate(pedidos_sem_rastreio):
            if i > 0:
                time.sleep(5)  # intervalo de 5 segundos entre cada requisição ao Bling
            try:
                detalhes = BlingService.buscar_detalhes_pedido_para_finalizacao(pedido.id_bling)
                if detalhes and detalhes.get('codigo_rastreamento'):
                    pedido.tracking_code = detalhes.get('codigo_rastreamento')
                    atualizados += 1
            except Exception as e:
                erros.append({'numero_pedido': pedido.numero_pedido, 'erro': str(e)})
        db.session.commit()
        return jsonify({'atualizados': atualizados, 'erros': erros[:50]}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/detalhes', methods=['GET'])
@jwt_required()
def get_detalhes_pedido(numero_pedido):
    """
    GET /api/pedidos/{numero}/detalhes
    Retorna: dados do pedido do banco (sem chamar Bling).
    O operador preenche marketplace, frete, transportadora e rastreio manualmente no modal.
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        resp = pedido.to_dict()
        if pedido.status == 'finalizado':
            custo = CustoFrete.query.filter_by(numero_pedido=numero).first()
            if custo:
                resp['custo_mandae'] = custo.custo_mandae
        return jsonify(resp), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/detalhes-bling', methods=['GET'])
@jwt_required()
def get_detalhes_pedido_bling(numero_pedido):
    """
    GET /api/pedidos/{numero}/detalhes-bling
    Busca detalhes do pedido diretamente no Bling usando o id_bling.
    Retorna: {
        "numero_loja": ... ou null,
        "loja_id": ... ou null,
        "frete": ... ou null,
        "contato_nome": ... ou null,
        "codigo_rastreamento": ... ou null
    }
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        if not pedido.id_bling:
            return jsonify({'erro': 'ID do Bling não encontrado para este pedido'}), 400

        detalhes = BlingService.buscar_detalhes_pedido_para_finalizacao(pedido.id_bling)
        
        if detalhes is None:
            return jsonify({'erro': 'Erro ao buscar detalhes do pedido no Bling'}), 500

        # Atualizar numero_loja e loja_id no banco se foram encontrados no Bling
        if detalhes.get('numero_loja') and not pedido.numero_loja:
            pedido.numero_loja = detalhes.get('numero_loja')
        if detalhes.get('loja_id') and not pedido.loja_id:
            pedido.loja_id = str(detalhes.get('loja_id'))
        if pedido.numero_loja or pedido.loja_id:
            db.session.commit()

        return jsonify(detalhes), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>', methods=['PUT', 'PATCH'])
@jwt_required()
def atualizar_dados_pedido(numero_pedido):
    """
    PUT /api/pedidos/{numero}
    Body: { "marketplace": "...", "frete_cliente": 0, "transportadora": "...", "tracking_code": "..." }
    Atualiza os dados informados manualmente pelo operador (apenas pedidos em aberto).
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        if pedido.status != 'aberto':
            return jsonify({'erro': 'Só é possível editar pedidos em aberto'}), 400

        data = request.get_json() or {}
        if data.get('marketplace') is not None:
            pedido.marketplace = str(data['marketplace']).strip() or 'site'
        if data.get('frete_cliente') is not None:
            try:
                pedido.frete_cliente = float(data['frete_cliente'])
            except (TypeError, ValueError):
                pass
        if data.get('peso') is not None:
            try:
                peso_val = data['peso']
                pedido.peso = float(peso_val) if peso_val != '' else None
            except (TypeError, ValueError):
                pass
        if data.get('transportadora') is not None:
            pedido.transportadora = str(data['transportadora']).strip() or None
        if data.get('tracking_code') is not None:
            pedido.tracking_code = str(data['tracking_code']).strip() or None

        db.session.commit()
        return jsonify(pedido.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>', methods=['DELETE'])
@jwt_required()
@admin_required()
def excluir_pedido(numero_pedido):
    """
    DELETE /api/pedidos/{numero}
    Remove o pedido (e custos/embalagens relacionados). Apenas ADMIN.
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()
        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404
        CustoFrete.query.filter_by(numero_pedido=numero).delete()
        PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).delete()
        db.session.delete(pedido)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/reservar', methods=['POST'])
@jwt_required()
def reservar_pedido(numero_pedido):
    """
    POST /api/pedidos/{numero}/reservar
    Reserva o pedido para o usuário autenticado.
    Retorna erro se o pedido já estiver reservado por outro usuário.
    """
    try:
        user_id = int(get_jwt_identity())
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        if pedido.status != 'aberto':
            return jsonify({'erro': 'Só é possível reservar pedidos em aberto'}), 400

        # Verificar se já está reservado por outro usuário
        if pedido.user_id_reservado is not None and pedido.user_id_reservado != user_id:
            usuario_reservado = Usuario.query.get(pedido.user_id_reservado)
            nome_reservado = usuario_reservado.nome if usuario_reservado else 'Outro usuário'
            return jsonify({
                'erro': f'Pedido já está reservado por {nome_reservado}',
                'usuario_reservado': usuario_reservado.to_dict() if usuario_reservado else None
            }), 409

        # Reservar o pedido
        pedido.user_id_reservado = user_id
        pedido.data_reserva = datetime.utcnow()

        db.session.commit()
        return jsonify({
            'mensagem': 'Pedido reservado com sucesso',
            'pedido': pedido.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/reservar', methods=['DELETE'])
@jwt_required()
def remover_reserva_pedido(numero_pedido):
    """
    DELETE /api/pedidos/{numero}/reservar
    Remove a reserva do pedido.
    Apenas o próprio usuário que reservou ou um ADMIN pode remover a reserva.
    """
    try:
        user_id = int(get_jwt_identity())
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        # Verificar se pode remover a reserva (próprio usuário ou admin)
        if pedido.user_id_reservado is None:
            return jsonify({'erro': 'Pedido não está reservado'}), 400

        if pedido.user_id_reservado != user_id and usuario.categoria != 'ADMIN':
            return jsonify({'erro': 'Apenas o usuário que reservou ou um administrador pode remover a reserva'}), 403

        # Remover reserva
        pedido.user_id_reservado = None
        pedido.data_reserva = None

        db.session.commit()
        return jsonify({
            'mensagem': 'Reserva removida com sucesso',
            'pedido': pedido.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_pedido(numero_pedido):
    """
    POST /api/pedidos/{numero}/finalizar
    Body: { "id_embalagem": 1, "observacoes": "..." }
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        # Suportar múltiplas embalagens (nova estrutura) ou uma única (compatibilidade)
        embalagens_data = data.get('embalagens', [])
        
        # Se não veio array de embalagens, tentar estrutura antiga (compatibilidade)
        if not embalagens_data or len(embalagens_data) == 0:
            id_embalagem = data.get('id_embalagem')
            if not id_embalagem:
                return jsonify({'erro': 'Adicione pelo menos uma embalagem'}), 400
            quantidade_embalagem = data.get('quantidade_embalagem', 1)
            try:
                quantidade_embalagem = int(quantidade_embalagem)
                if quantidade_embalagem < 1:
                    return jsonify({'erro': 'Quantidade de embalagens deve ser pelo menos 1'}), 400
            except (TypeError, ValueError):
                quantidade_embalagem = 1
            # Converter para formato de array
            embalagens_data = [{'embalagem_id': id_embalagem, 'quantidade': quantidade_embalagem}]
        
        # Validar e processar embalagens
        embalagens_validas = []
        for emb_data in embalagens_data:
            emb_id = emb_data.get('embalagem_id') or emb_data.get('id_embalagem')
            qtd = emb_data.get('quantidade', 1)
            
            if not emb_id:
                continue
            
            try:
                emb_id = int(emb_id)
                qtd = int(qtd)
                if qtd < 1:
                    continue
            except (TypeError, ValueError):
                continue
            
            embalagem = Embalagem.query.get(emb_id)
            if not embalagem:
                return jsonify({'erro': f'Embalagem ID {emb_id} não encontrada'}), 404
            
            embalagens_validas.append({
                'embalagem': embalagem,
                'quantidade': qtd
            })
        
        if len(embalagens_validas) == 0:
            return jsonify({'erro': 'Adicione pelo menos uma embalagem válida'}), 400

        # Para pedidos Tray, custo_mandae (gasto real do frete) é obrigatório
        marketplace_norm = (pedido.marketplace or '').strip().lower()
        custo_mandae = data.get('custo_mandae')
        if marketplace_norm == 'tray':
            if custo_mandae is None or custo_mandae == '':
                return jsonify({'erro': 'Para pedidos Tray, informe o custo Mandaê (gasto real do frete)'}), 400
            try:
                v = float(custo_mandae)
                if v < 0:
                    return jsonify({'erro': 'Custo Mandaê deve ser >= 0'}), 400
            except (TypeError, ValueError):
                return jsonify({'erro': 'Custo Mandaê inválido para Tray'}), 400
            custo_mandae = v  # normalizar para float para gravar depois

        pedido.observacoes = data.get('observacoes', '') or ''
        pedido.status = 'preenchimento'
        
        # Manter compatibilidade: salvar primeira embalagem nos campos antigos
        primeira_emb = embalagens_validas[0]
        pedido.id_embalagem = primeira_emb['embalagem'].id
        pedido.quantidade_embalagem = primeira_emb['quantidade']
        
        # Remover embalagens antigas do pedido
        PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).delete()
        
        # Adicionar todas as embalagens na tabela intermediária
        nomes_embalagens = []
        for emb_item in embalagens_validas:
            emb = emb_item['embalagem']
            qtd = emb_item['quantidade']
            
            # Criar registro na tabela intermediária
            pedido_emb = PedidoEmbalagem(
                pedido_id=pedido.id,
                embalagem_id=emb.id,
                quantidade=qtd
            )
            db.session.add(pedido_emb)
            
            # Baixa automática no estoque
            emb.estoque = (emb.estoque or 0) - qtd
            nomes_embalagens.append(f"{emb.nome} (x{qtd})")

        custo_resultado = CustoService.calcular_custo_pedido(numero_pedido)

        if not custo_resultado:
            return jsonify({'erro': 'Erro ao calcular custos'}), 500

        # Gravar custo_mandae quando informado (webhook preencherá depois se vazio)
        custo = CustoFrete.query.filter_by(numero_pedido=numero).first()
        if custo and custo_mandae is not None and custo_mandae != '':
            try:
                custo.custo_mandae = float(custo_mandae)
            except (TypeError, ValueError):
                pass

        pedido.status = 'finalizado'
        pedido.data_finalizacao = datetime.utcnow()
        
        # Remover reserva ao finalizar
        pedido.user_id_reservado = None
        pedido.data_reserva = None

        # Opcional: dar baixa no Bling
        # BlingService.dar_baixa_embalagem(pedido.id_bling, f"Embalagem: {embalagem.nome}")

        auditoria = Auditoria(
            user_id=user_id,
            acao='finalizar_pedido',
            recurso='pedido',
            numero_pedido=numero,
            dados_depois={'status': 'finalizado', 'embalagens': ', '.join(nomes_embalagens)}
        )
        db.session.add(auditoria)
        db.session.commit()

        return jsonify({
            'mensagem': 'Pedido finalizado com sucesso',
            'pedido': pedido.to_dict(),
            'custo': custo_resultado
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/editar-finalizado', methods=['PATCH', 'PUT'])
@jwt_required()
def editar_pedido_finalizado(numero_pedido):
    """
    PATCH /api/pedidos/{numero}/editar-finalizado
    Body: { "marketplace": "...", "frete_cliente": 0, "peso": 0, "transportadora": "...", "tracking_code": "...", "custo_mandae": 0 }
    Permite editar todos os campos de pedidos já finalizados.
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        if pedido.status != 'finalizado':
            return jsonify({'erro': 'Apenas pedidos finalizados podem ser editados aqui'}), 400

        data = request.get_json() or {}
        
        # Permitir editar todos os campos
        if data.get('marketplace') is not None:
            pedido.marketplace = str(data['marketplace']).strip() or 'site'
        if data.get('frete_cliente') is not None:
            try:
                pedido.frete_cliente = float(data['frete_cliente'])
            except (TypeError, ValueError):
                pass
        if data.get('peso') is not None:
            try:
                peso_val = data['peso']
                pedido.peso = float(peso_val) if peso_val != '' and peso_val is not None else None
            except (TypeError, ValueError):
                pass
        if data.get('transportadora') is not None:
            pedido.transportadora = str(data['transportadora']).strip() or None
        if data.get('tracking_code') is not None:
            pedido.tracking_code = str(data['tracking_code']).strip() or None
        if data.get('custo_mandae') is not None:
            try:
                v = float(data['custo_mandae'])
                if v < 0:
                    return jsonify({'erro': 'Custo Mandaê deve ser >= 0'}), 400
                custo = CustoFrete.query.filter_by(numero_pedido=numero).first()
                if custo:
                    custo.custo_mandae = v
                else:
                    # Criar registro de custo se não existir
                    custo = CustoFrete(
                        numero_pedido=numero,
                        frete_cliente=pedido.frete_cliente,
                        custo_mandae=v
                    )
                    db.session.add(custo)
            except (TypeError, ValueError):
                return jsonify({'erro': 'Custo Mandaê inválido'}), 400

        # Edição de embalagens: reverter estoque antigo, aplicar novo
        if 'embalagens' in data:
            embalagens_data = data.get('embalagens', [])
            if not embalagens_data:
                return jsonify({'erro': 'Informe pelo menos uma embalagem'}), 400

            embalagens_validas = []
            for emb_data in embalagens_data:
                emb_id = emb_data.get('embalagem_id') or emb_data.get('id_embalagem')
                qtd = emb_data.get('quantidade', 1)
                if not emb_id:
                    continue
                try:
                    emb_id = int(emb_id)
                    qtd = int(qtd)
                    if qtd < 1:
                        continue
                except (TypeError, ValueError):
                    continue
                embalagem = Embalagem.query.get(emb_id)
                if not embalagem:
                    return jsonify({'erro': f'Embalagem ID {emb_id} não encontrada'}), 404
                embalagens_validas.append({'embalagem': embalagem, 'quantidade': qtd})

            if not embalagens_validas:
                return jsonify({'erro': 'Informe pelo menos uma embalagem válida'}), 400

            # Reverter estoque das embalagens atuais do pedido
            for pe in PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all():
                if pe.embalagem:
                    pe.embalagem.estoque = (pe.embalagem.estoque or 0) + (pe.quantidade or 1)
            PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).delete()

            # Aplicar novas embalagens
            primeira = embalagens_validas[0]
            pedido.id_embalagem = primeira['embalagem'].id
            pedido.quantidade_embalagem = primeira['quantidade']
            for emb_item in embalagens_validas:
                emb = emb_item['embalagem']
                qtd = emb_item['quantidade']
                db.session.add(PedidoEmbalagem(
                    pedido_id=pedido.id,
                    embalagem_id=emb.id,
                    quantidade=qtd
                ))
                emb.estoque = (emb.estoque or 0) - qtd

            CustoService.calcular_custo_pedido(numero)

        db.session.commit()
        return jsonify(pedido.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/planilha-mandae', methods=['POST'])
@jwt_required()
def enviar_planilha_mandae():
    """
    POST /api/pedidos/planilha-mandae
    Envia arquivo CSV ou Excel com colunas Código_Rastreio e Frete_Real.
    Atualiza custo_mandae (frete real) dos pedidos finalizados cujo código de rastreio coincidir.
    """
    try:
        if 'planilha' not in request.files and 'arquivo' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado. Use o campo "planilha" ou "arquivo".'}), 400
        arquivo = request.files.get('planilha') or request.files.get('arquivo')
        if not arquivo or arquivo.filename == '':
            return jsonify({'erro': 'Selecione um arquivo CSV ou Excel (.xlsx, .xls).'}), 400
        nome = (arquivo.filename or '').strip().lower()
        if not (nome.endswith('.csv') or nome.endswith('.xlsx') or nome.endswith('.xls')):
            return jsonify({'erro': 'Formato não suportado. Use .csv, .xlsx ou .xls.'}), 400

        from utils.planilha_mandae import ler_planilha_mandae
        stream = io.BytesIO(arquivo.read())
        linhas = ler_planilha_mandae(stream, nome)
        if not linhas:
            return jsonify({
                'mensagem': 'Nenhuma linha válida encontrada. Verifique se a planilha tem as colunas Código_Rastreio e Frete_Real.',
                'atualizados': 0
            }), 200

        pedidos_finalizados = PedidoLogistica.query.filter_by(status='finalizado').all()
        atualizados = 0
        erros = []
        for item in linhas:
            codigo = (item.get('codigo_rastreio') or '').strip()
            frete_real = item.get('frete_real')
            if not codigo:
                continue
            try:
                frete_real = round(float(frete_real), 2)
            except (TypeError, ValueError):
                erros.append(f'Código {codigo}: valor de frete inválido')
                continue
            pedidos = [p for p in pedidos_finalizados if (p.tracking_code or '').strip() == codigo]
            if not pedidos:
                continue
            for pedido in pedidos:
                custo = CustoFrete.query.filter_by(numero_pedido=pedido.numero_pedido).first()
                if custo:
                    custo.custo_mandae = frete_real
                    custo_emb = round(float(custo.custo_embalagem or 0), 2)
                    custo.custo_total = round(frete_real + custo_emb, 2)
                    custo.ganho_perda = round(round(float(custo.frete_cliente or 0), 2) - custo.custo_total, 2)
                    custo.margem_percentual = round((custo.ganho_perda / custo.custo_total * 100), 2) if custo.custo_total > 0 else 0
                    atualizados += 1
                else:
                    frete_cliente = round(float(pedido.frete_cliente or 0), 2)
                    custo_emb = 0.0
                    for pe in PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all():
                        if pe.embalagem:
                            custo_emb = round(custo_emb + float(pe.embalagem.custo or 0) * (pe.quantidade or 1), 2)
                    if not PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).first() and pedido.embalagem:
                        custo_emb = round(float(pedido.embalagem.custo or 0) * (pedido.quantidade_embalagem or 1), 2)
                    custo_total = round(frete_real + custo_emb, 2)
                    ganho_perda = round(frete_cliente - custo_total, 2)
                    margem = round((ganho_perda / custo_total * 100), 2) if custo_total > 0 else 0
                    custo = CustoFrete(
                        numero_pedido=pedido.numero_pedido,
                        frete_cliente=frete_cliente,
                        custo_frete_mandae=frete_real,
                        custo_mandae=frete_real,
                        custo_embalagem=custo_emb,
                        custo_total=custo_total,
                        ganho_perda=ganho_perda,
                        margem_percentual=margem,
                        fonte_frete='planilha_mandae'
                    )
                    db.session.add(custo)
                    atualizados += 1

        db.session.commit()
        return jsonify({
            'mensagem': f'Planilha processada. {atualizados} pedido(s) atualizado(s) com o frete real.',
            'atualizados': atualizados,
            'erros': erros[:20]
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@pedidos_bp.route('/<numero_pedido>/sincronizar-rastreio', methods=['POST'])
@jwt_required()
def sincronizar_rastreio_finalizado(numero_pedido):
    """
    POST /api/pedidos/{numero}/sincronizar-rastreio
    Busca código de rastreio do pedido finalizado no Bling.
    """
    try:
        numero = (numero_pedido or '').strip()
        pedido = PedidoLogistica.query.filter_by(numero_pedido=numero).first()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        if pedido.status != 'finalizado':
            return jsonify({'erro': 'Apenas pedidos finalizados podem ter rastreio sincronizado'}), 400

        if not pedido.id_bling:
            return jsonify({'erro': 'ID do Bling não encontrado para este pedido'}), 400

        detalhes = BlingService.buscar_detalhes_pedido_para_finalizacao(pedido.id_bling)
        
        if detalhes is None:
            return jsonify({'erro': 'Erro ao buscar detalhes do pedido no Bling'}), 500

        codigo_rastreamento = detalhes.get('codigo_rastreamento')
        if codigo_rastreamento:
            pedido.tracking_code = codigo_rastreamento
            db.session.commit()
            return jsonify({
                'mensagem': 'Código de rastreio atualizado com sucesso',
                'tracking_code': codigo_rastreamento,
                'pedido': pedido.to_dict()
            }), 200
        else:
            return jsonify({
                'mensagem': 'Código de rastreio não encontrado no Bling',
                'tracking_code': None
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
