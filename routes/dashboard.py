from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import db, PedidoLogistica, CustoFrete, Embalagem, ConfiguracaoSistema, Usuario, PedidoEmbalagem
from datetime import datetime, timedelta, date
from calendar import monthrange
from sqlalchemy import func
from collections import defaultdict

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# Mapeamento de loja.id para nome da loja (mesmo do pedidos.py)
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
    try:
        loja_id_int = int(loja_id)
        return LOJA_ID_TO_NOME.get(loja_id_int)
    except (ValueError, TypeError):
        pass
    return LOJA_ID_TO_NOME.get(str(loja_id)) or LOJA_ID_TO_NOME.get(loja_id)


def canal_para_dashboard(pedido):
    """
    Retorna o nome do canal/card para a dashboard.
    - Pedidos com loja_id 0 e marketplace 'influencer' → Pedidos Internos.
    - Pedidos com loja_id 0 e outro marketplace (ex.: Época) → Época.
    - Demais: tradução pelo loja_id.
    """
    loja_id = getattr(pedido, 'loja_id', None)
    marketplace = (getattr(pedido, 'marketplace', None) or '').strip().lower()
    is_loja_zero = loja_id is None or str(loja_id).strip() == '' or str(loja_id).strip() == '0'
    if is_loja_zero and marketplace == 'influencer':
        return 'Pedidos Internos'
    if is_loja_zero:
        return 'Época'
    nome = traduzir_loja_id(loja_id)
    return nome if nome else 'Não identificado'


def _build_dashboard_data():
    """Monta o dict com todos os dados da dashboard (usado por GET e por export Excel)."""
    try:
        hoje = datetime.now().date()
        ontem = hoje - timedelta(days=1)
        inicio_mes = hoje.replace(day=1)
        
        # Meta diária (ajuste manual) e captura automática às 7:50
        config_meta = ConfiguracaoSistema.query.filter_by(chave='meta_diaria').first()
        META_DIARIA = int(config_meta.valor) if config_meta else 180

        # Pedidos em aberto
        abertos = PedidoLogistica.query.filter_by(status='aberto').count()

        # Ideal Média Diária: gravar primeiro valor do dia às 7:50 (quando o sistema estiver ativo)
        now = datetime.now()
        ja_passou_750 = (now.hour > 7) or (now.hour == 7 and now.minute >= 50)
        config_captura_data = ConfiguracaoSistema.query.filter_by(chave='meta_captura_data').first()
        config_captura_valor = ConfiguracaoSistema.query.filter_by(chave='meta_captura_valor').first()
        data_captura_hoje = config_captura_data.valor if config_captura_data else None
        if ja_passou_750 and data_captura_hoje != hoje.isoformat():
            # Primeira requisição do dia após 7:50: capturar pedidos em aberto como meta do dia
            if not config_captura_data:
                config_captura_data = ConfiguracaoSistema(chave='meta_captura_data', valor=hoje.isoformat(), descricao='Data da última captura da meta (7:50)')
                db.session.add(config_captura_data)
            else:
                config_captura_data.valor = hoje.isoformat()
            if not config_captura_valor:
                config_captura_valor = ConfiguracaoSistema(chave='meta_captura_valor', valor=str(abertos), descricao='Meta diária capturada às 7:50')
                db.session.add(config_captura_valor)
            else:
                config_captura_valor.valor = str(abertos)
            db.session.commit()
        ideal_meta = int(config_captura_valor.valor) if config_captura_valor else META_DIARIA

        # Dados de hoje (usar data_finalizacao do pedido, não created_at do CustoFrete)
        pedidos_hoje = PedidoLogistica.query.filter(
            PedidoLogistica.status == 'finalizado',
            func.date(PedidoLogistica.data_finalizacao) == hoje
        ).all()
        
        # Buscar custos correspondentes
        numeros_hoje = [p.numero_pedido for p in pedidos_hoje]
        custos_hoje = CustoFrete.query.filter(
            CustoFrete.numero_pedido.in_(numeros_hoje)
        ).all() if numeros_hoje else []

        total_pedidos_hoje = len(pedidos_hoje)
        # Arredondar cada valor para 2 casas decimais antes de somar
        custo_total_hoje = round(sum(round(c._custo_total_efetivo(), 2) for c in custos_hoje), 2)
        frete_total_hoje = round(sum(round(float(c.frete_cliente or 0), 2) for c in custos_hoje), 2)
        frete_real_hoje = round(sum(round(c._custo_frete_efetivo(), 2) for c in custos_hoje), 2)
        # Ganho/Perda líquido: soma de todos os valores (positivos e negativos) com arredondamento
        ganho_perda_liquido_hoje = round(sum(round(c._ganho_perda_efetivo(), 2) for c in custos_hoje), 2)

        # Dados de ontem (usar data_finalizacao do pedido)
        pedidos_ontem = PedidoLogistica.query.filter(
            PedidoLogistica.status == 'finalizado',
            func.date(PedidoLogistica.data_finalizacao) == ontem
        ).all()
        total_pedidos_ontem = len(pedidos_ontem)

        # Acumulado do mês (usar data_finalizacao do pedido); no dia 01 zerar
        pedidos_mes = PedidoLogistica.query.filter(
            PedidoLogistica.status == 'finalizado',
            func.date(PedidoLogistica.data_finalizacao) >= inicio_mes
        ).all()
        acumulado_total = 0 if hoje.day == 1 else len(pedidos_mes)

        # Buscar custos correspondentes para cálculos financeiros (mês)
        numeros_mes = [p.numero_pedido for p in pedidos_mes]
        custos_mes = CustoFrete.query.filter(
            CustoFrete.numero_pedido.in_(numeros_mes)
        ).all() if numeros_mes else []

        # Dias decorridos no mês
        dias_decorridos = (hoje - inicio_mes).days + 1
        # Média diária conforme planilha: AVERAGEIF(diários, ">1") — média só dos dias com mais de 1 pedido
        totais_por_dia = (
            db.session.query(
                func.date(PedidoLogistica.data_finalizacao).label('dia'),
                func.count(PedidoLogistica.id).label('total')
            )
            .filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) >= inicio_mes,
                func.date(PedidoLogistica.data_finalizacao) <= hoje
            )
            .group_by(func.date(PedidoLogistica.data_finalizacao))
            .all()
        )
        valores_diarios = [t.total for t in totais_por_dia]
        maiores_que_um = [v for v in valores_diarios if v > 1]
        total_para_media = acumulado_total if hoje.day != 1 else 0
        if maiores_que_um:
            media_diaria = round(sum(maiores_que_um) / len(maiores_que_um), 1)
        elif dias_decorridos > 0 and total_para_media > 0:
            media_diaria = round(total_para_media / dias_decorridos, 1)
        else:
            media_diaria = 0

        # Percentual da meta: divisão da Média Diária pela Ideal (capturada às 7:50 ou manual)
        percentual_meta = round((media_diaria / ideal_meta * 100), 1) if ideal_meta > 0 else 0

        # Por canal e Gráfico por canal: dados do MÊS inteiro (reset no dia 1)
        metricas_por_canal = defaultdict(lambda: {
            'quantidade': 0,
            'frete_total': 0.0,
            'frete_real_total': 0.0,
            'custo_embalagem_total': 0.0,
            'ganho_perda_liquido': 0.0
        })

        for custo in custos_mes:
            pedido = PedidoLogistica.query.filter_by(numero_pedido=custo.numero_pedido).first()
            if pedido:
                loja_nome = canal_para_dashboard(pedido)
                metricas_por_canal[loja_nome]['quantidade'] += 1
                if loja_nome == 'Tray':
                    metricas_por_canal[loja_nome]['frete_total'] = round(
                        metricas_por_canal[loja_nome]['frete_total'] + round(float(custo.frete_cliente or 0), 2), 2
                    )
                metricas_por_canal[loja_nome]['frete_real_total'] = round(
                    metricas_por_canal[loja_nome]['frete_real_total'] + round(custo._custo_frete_efetivo(), 2), 2
                )
                custo_emb = round(float(custo.custo_embalagem or 0), 2)
                metricas_por_canal[loja_nome]['custo_embalagem_total'] = round(
                    metricas_por_canal[loja_nome]['custo_embalagem_total'] + custo_emb, 2
                )
                ganho_perda = round(custo._ganho_perda_efetivo(), 2)
                metricas_por_canal[loja_nome]['ganho_perda_liquido'] = round(
                    metricas_por_canal[loja_nome]['ganho_perda_liquido'] + ganho_perda, 2
                )

        # Ordenar canais por quantidade (maior para menor)
        canais_ordenados = sorted(
            metricas_por_canal.items(),
            key=lambda x: x[1]['quantidade'],
            reverse=True
        )

        por_canal = []
        for canal, metricas in canais_ordenados:
            qtd = metricas['quantidade']
            ganho_perda = metricas['ganho_perda_liquido']
            ganho_perda_medio = round(ganho_perda / qtd, 2) if qtd and qtd > 0 else 0
            por_canal.append({
                'canal': canal,
                'quantidade': qtd,
                'frete_total': metricas['frete_total'],
                'frete_real_total': metricas['frete_real_total'],
                'custo_embalagem_total': metricas['custo_embalagem_total'],
                'ganho_perda_liquido': ganho_perda,
                'ganho_perda_medio': ganho_perda_medio,
            })

        # Dados para gráfico diário: mês atual, um ponto por dia do mês (1 a 28/29/30/31)
        ultimo_dia_mes = monthrange(hoje.year, hoje.month)[1]
        dados_diarios = []
        for dia in range(1, ultimo_dia_mes + 1):
            data_dia = date(hoje.year, hoje.month, dia)
            pedidos_dia = PedidoLogistica.query.filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) == data_dia
            ).count()
            dados_diarios.append({
                'dia': dia,
                'data': data_dia.isoformat(),
                'quantidade': pedidos_dia
            })

        # Embalagens: dados do MÊS inteiro (reset no dia 1)
        if hoje.day == 1:
            embalagens_dict_mes = {}
        else:
            embalagens_dict_mes = {}
            for pedido in pedidos_mes:
                pedido_embalagens = PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all()
                if pedido_embalagens and len(pedido_embalagens) > 0:
                    for ped_emb in pedido_embalagens:
                        id_emb = ped_emb.embalagem_id
                        qtd = ped_emb.quantidade or 1
                        if id_emb not in embalagens_dict_mes:
                            embalagens_dict_mes[id_emb] = 0
                        embalagens_dict_mes[id_emb] += qtd
                elif pedido.id_embalagem:
                    id_emb = pedido.id_embalagem
                    qtd = pedido.quantidade_embalagem or 1
                    if id_emb not in embalagens_dict_mes:
                        embalagens_dict_mes[id_emb] = 0
                    embalagens_dict_mes[id_emb] += qtd

        embalagens_detalhadas = []
        total_embalagens_usadas = 0
        valor_total_embalagens = 0.0

        for id_emb, qtd_total in embalagens_dict_mes.items():
            emb = Embalagem.query.get(id_emb)
            if emb:
                custo_unitario = round(float(emb.custo or 0), 2)
                valor_total = round(custo_unitario * qtd_total, 2)
                total_embalagens_usadas += qtd_total
                valor_total_embalagens = round(valor_total_embalagens + valor_total, 2)
                embalagens_detalhadas.append({
                    'id': id_emb,
                    'nome': emb.nome,
                    'quantidade': qtd_total,
                    'custo_unitario': custo_unitario,
                    'valor_total': valor_total
                })

        # Total de embalagens disponíveis
        total_embalagens = Embalagem.query.count()

        return {
            'pedidos_abertos': abertos,
            'hoje': {
                'data': hoje.isoformat(),
                'total_pedidos': total_pedidos_hoje,
                'custo_total': round(custo_total_hoje, 2),
                'frete_total': round(frete_total_hoje, 2),
                'frete_real_total': round(frete_real_hoje, 2),
                'ganho_perda_liquido': round(ganho_perda_liquido_hoje, 2),
            },
            'ontem': {
                'total_pedidos': total_pedidos_ontem,
            },
            'acumulado': {
                'total': acumulado_total,
                'media_diaria': media_diaria,
                'meta_diaria': ideal_meta,
                'percentual_meta': percentual_meta,
            },
            'por_canal': por_canal,
            'por_canal_data': inicio_mes.strftime('%Y-%m'),
            'grafico_diario': dados_diarios,
            'custo_embalagem_total_geral': 0 if hoje.day == 1 else round(sum(item.get('custo_embalagem_total', 0) or 0 for item in por_canal), 2),
            'embalagens': {
                'usadas_mes': 0 if hoje.day == 1 else total_embalagens_usadas,
                'total_disponiveis': total_embalagens,
                'valor_total_mes': 0 if hoje.day == 1 else round(valor_total_embalagens, 2),
                'detalhadas': embalagens_detalhadas
            },
            'embalagens_mes_ref': inicio_mes.strftime('%Y-%m'),
        }
    except Exception:
        return None


@dashboard_bp.route('', methods=['GET'])
@jwt_required()
def resumo():
    """
    GET /api/dashboard
    Retorna resumo completo: métricas gerais, por canal, gráficos, etc.
    """
    data = _build_dashboard_data()
    if data is None:
        return jsonify({'erro': 'Erro ao carregar dashboard'}), 500
    return jsonify(data), 200


@dashboard_bp.route('/excel', methods=['GET'])
@jwt_required()
def exportar_excel():
    """GET /api/dashboard/excel - Exporta a dashboard para Excel (reconstruindo todos os dados)."""
    data = _build_dashboard_data()
    if data is None:
        return jsonify({'erro': 'Erro ao carregar dashboard'}), 500
    from utils.excel_exporter import exportar_dashboard
    buffer = exportar_dashboard(data)
    hoje_str = (data.get('hoje') or {}).get('data', datetime.now().date().isoformat())
    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'dashboard-{hoje_str}.xlsx'
    ), 200


@dashboard_bp.route('/meta', methods=['GET', 'PUT'])
@jwt_required()
def meta_diaria():
    """
    GET /api/dashboard/meta - Retorna a meta diária atual
    PUT /api/dashboard/meta - Atualiza a meta diária (apenas ADMIN)
    """
    try:
        if request.method == 'GET':
            config = ConfiguracaoSistema.query.filter_by(chave='meta_diaria').first()
            if config:
                return jsonify({
                    'meta_diaria': int(config.valor),
                    'descricao': config.descricao
                }), 200
            return jsonify({'meta_diaria': 180}), 200
        
        elif request.method == 'PUT':
            # Verificar se é admin
            user_id = get_jwt_identity()
            usuario = Usuario.query.get(user_id)
            if not usuario or usuario.categoria != 'ADMIN':
                return jsonify({'erro': 'Apenas administradores podem alterar a meta'}), 403
            
            data = request.get_json()
            nova_meta = data.get('meta_diaria')
            
            if nova_meta is None or not isinstance(nova_meta, int) or nova_meta < 1:
                return jsonify({'erro': 'Meta diária deve ser um número inteiro positivo'}), 400

            hoje = datetime.now().date().isoformat()
            config = ConfiguracaoSistema.query.filter_by(chave='meta_diaria').first()
            if config:
                config.valor = str(nova_meta)
            else:
                config = ConfiguracaoSistema(
                    chave='meta_diaria',
                    valor=str(nova_meta),
                    descricao='Meta diária de pedidos'
                )
                db.session.add(config)
            # Gravar também como captura de hoje para o card Ideal Média Diária exibir este valor
            for chave, valor, desc in [
                ('meta_captura_data', hoje, 'Data da última captura da meta (7:50)'),
                ('meta_captura_valor', str(nova_meta), 'Meta diária capturada às 7:50'),
            ]:
                c = ConfiguracaoSistema.query.filter_by(chave=chave).first()
                if c:
                    c.valor = valor
                else:
                    db.session.add(ConfiguracaoSistema(chave=chave, valor=valor, descricao=desc))
            db.session.commit()
            return jsonify({
                'meta_diaria': nova_meta,
                'mensagem': 'Meta diária atualizada com sucesso'
            }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
