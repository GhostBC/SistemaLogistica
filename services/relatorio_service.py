from database.models import db, CustoFrete, PedidoLogistica, Embalagem, PedidoEmbalagem
from services.custo_service import CustoService
from utils.excel_exporter import exportar_relatorio_diario
from datetime import datetime, date, timedelta
from sqlalchemy import func
from collections import defaultdict

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


def _traduzir_loja_id(loja_id):
    if loja_id is None:
        return 'Não identificado'
    try:
        return LOJA_ID_TO_NOME.get(int(loja_id)) or LOJA_ID_TO_NOME.get(str(loja_id)) or 'Não identificado'
    except (ValueError, TypeError):
        return LOJA_ID_TO_NOME.get(str(loja_id)) or 'Não identificado'


class RelatorioService:

    @staticmethod
    def gerar_relatorio_diario(data_relatorio):
        """Retorna o mesmo que CustoService.consolidar_custo_diario."""
        return CustoService.consolidar_custo_diario(data_relatorio)

    @staticmethod
    def exportar_relatorio_excel(data_relatorio):
        """
        Gera arquivo Excel do relatório diário.
        data_relatorio: date
        Retorna: BytesIO com o arquivo .xlsx
        """
        resultado = CustoService.consolidar_custo_diario(data_relatorio)
        if not resultado or resultado.get('total_pedidos', 0) == 0:
            # Retornar Excel vazio com resumo zerado
            return exportar_relatorio_diario(
                data_relatorio,
                {
                    'data': data_relatorio.isoformat(),
                    'total_pedidos': 0,
                    'custo_total': 0,
                    'frete_total': 0,
                    'frete_real_total': 0,
                    'ganho_total': 0,
                    'perda_total': 0,
                    'margem_media': 0,
                    'embalagens_utilizadas': resultado.get('embalagens_utilizadas', []) if resultado else [],
                },
                []
            )

        return exportar_relatorio_diario(
            data_relatorio,
            resultado,
            resultado.get('pedidos', [])
        )

    @staticmethod
    def consolidar_periodo(inicio, fim):
        """
        Consolida custos entre duas datas (inclusive).
        inicio, fim: date
        Retorna: dict com totais e lista por dia
        """
        try:
            # Validar período (máximo 90 dias)
            dias = (fim - inicio).days + 1
            if dias > 90:
                raise ValueError('Período máximo permitido é de 90 dias')
            if dias < 1:
                raise ValueError('Data fim deve ser maior ou igual à data início')
            
            custos = CustoFrete.query.filter(
                func.date(CustoFrete.created_at) >= inicio,
                func.date(CustoFrete.created_at) <= fim
            ).all()

            # Arredondar valores para 2 casas decimais
            por_dia = {}
            for c in custos:
                d = c.created_at.date() if c.created_at else None
                if d is None:
                    continue
                key = d.isoformat()
                if key not in por_dia:
                    por_dia[key] = {
                        'data': key,
                        'total_pedidos': 0,
                        'custo_total': 0.0,
                        'frete_total': 0.0,
                        'frete_real_total': 0.0,
                        'ganho_perda_liquido': 0.0,
                    }
                por_dia[key]['total_pedidos'] += 1
                por_dia[key]['custo_total'] = round(por_dia[key]['custo_total'] + round(c._custo_total_efetivo(), 2), 2)
                por_dia[key]['frete_total'] = round(por_dia[key]['frete_total'] + round(float(c.frete_cliente or 0), 2), 2)
                por_dia[key]['frete_real_total'] = round(por_dia[key]['frete_real_total'] + round(c._custo_frete_efetivo(), 2), 2)
                ganho_perda = round(c._ganho_perda_efetivo(), 2)
                por_dia[key]['ganho_perda_liquido'] = round(por_dia[key]['ganho_perda_liquido'] + ganho_perda, 2)

            # Totais do período
            total_pedidos = len(custos)
            custo_total = round(sum(round(c._custo_total_efetivo(), 2) for c in custos), 2)
            frete_total = round(sum(round(float(c.frete_cliente or 0), 2) for c in custos), 2)
            frete_real_total = round(sum(round(c._custo_frete_efetivo(), 2) for c in custos), 2)
            ganho_perda_liquido = round(sum(round(c._ganho_perda_efetivo(), 2) for c in custos), 2)
            
            # Embalagens utilizadas no período
            pedidos_com_embalagem = PedidoLogistica.query.filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) >= inicio,
                func.date(PedidoLogistica.data_finalizacao) <= fim
            ).all()
            
            embalagens_dict = {}
            for pedido in pedidos_com_embalagem:
                # Usar nova estrutura de múltiplas embalagens
                pedido_embalagens = PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all()
                
                if pedido_embalagens and len(pedido_embalagens) > 0:
                    for ped_emb in pedido_embalagens:
                        id_emb = ped_emb.embalagem_id
                        qtd = ped_emb.quantidade or 1
                        if id_emb not in embalagens_dict:
                            embalagens_dict[id_emb] = 0
                        embalagens_dict[id_emb] += qtd
                elif pedido.id_embalagem:
                    # Compatibilidade com estrutura antiga
                    id_emb = pedido.id_embalagem
                    qtd = pedido.quantidade_embalagem or 1
                    if id_emb not in embalagens_dict:
                        embalagens_dict[id_emb] = 0
                    embalagens_dict[id_emb] += qtd
            
            embalagens_utilizadas = []
            for id_emb, qtd_total in embalagens_dict.items():
                emb = Embalagem.query.get(id_emb)
                if emb:
                    custo_unitario = round(float(emb.custo or 0), 2)
                    valor_total = round(custo_unitario * qtd_total, 2)
                    embalagens_utilizadas.append({
                        'id': id_emb,
                        'nome': emb.nome,
                        'quantidade': qtd_total,
                        'custo_unitario': custo_unitario,
                        'valor_total': valor_total
                    })

            return {
                'inicio': inicio.isoformat(),
                'fim': fim.isoformat(),
                'dias': dias,
                'total_pedidos': total_pedidos,
                'custo_total': custo_total,
                'frete_total': frete_total,
                'frete_real_total': frete_real_total,
                'ganho_perda_liquido': ganho_perda_liquido,
                'embalagens_utilizadas': embalagens_utilizadas,
                'por_dia': list(por_dia.values())
            }

        except ValueError as e:
            raise e
        except Exception as e:
            print(f"Erro ao consolidar período: {str(e)}")
            return None

    @staticmethod
    def exportar_relatorio_periodo_excel(inicio, fim, resultado):
        """
        Gera arquivo Excel do relatório por período.
        inicio, fim: date
        resultado: dict retornado por consolidar_periodo
        Retorna: BytesIO com o arquivo .xlsx
        """
        from utils.excel_exporter import exportar_relatorio_periodo
        return exportar_relatorio_periodo(inicio, fim, resultado)

    @staticmethod
    def consolidar_por_canal(inicio, fim):
        """
        Relatório individual por canal e consumo de caixa por canal.
        inicio, fim: date
        Retorna: list de { canal, total_pedidos, custo_total, frete_total, frete_real_total,
                  ganho_perda_liquido, caixas: [ { nome, quantidade, custo_unitario, valor_total } ] }
        """
        try:
            dias = (fim - inicio).days + 1
            if dias > 90:
                raise ValueError('Período máximo permitido é de 90 dias')
            if dias < 1:
                raise ValueError('Data fim deve ser maior ou igual à data início')
            pedidos = PedidoLogistica.query.filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) >= inicio,
                func.date(PedidoLogistica.data_finalizacao) <= fim
            ).all()
            numeros = [p.numero_pedido for p in pedidos]
            custos = CustoFrete.query.filter(CustoFrete.numero_pedido.in_(numeros)).all() if numeros else []
            custo_por_numero = {c.numero_pedido: c for c in custos}
            # Por canal: métricas + caixas
            por_canal = defaultdict(lambda: {
                'total_pedidos': 0,
                'custo_total': 0.0,
                'frete_total': 0.0,
                'frete_real_total': 0.0,
                'ganho_perda_liquido': 0.0,
                'caixas': defaultdict(lambda: {'quantidade': 0, 'custo_unitario': 0.0})
            })
            for pedido in pedidos:
                canal = _traduzir_loja_id(pedido.loja_id)
                por_canal[canal]['total_pedidos'] += 1
                c = custo_por_numero.get(pedido.numero_pedido)
                if c:
                    por_canal[canal]['custo_total'] = round(por_canal[canal]['custo_total'] + round(c._custo_total_efetivo(), 2), 2)
                    por_canal[canal]['frete_total'] = round(por_canal[canal]['frete_total'] + round(float(c.frete_cliente or 0), 2), 2)
                    por_canal[canal]['frete_real_total'] = round(por_canal[canal]['frete_real_total'] + round(c._custo_frete_efetivo(), 2), 2)
                    por_canal[canal]['ganho_perda_liquido'] = round(por_canal[canal]['ganho_perda_liquido'] + round(c._ganho_perda_efetivo(), 2), 2)
                # Embalagens do pedido
                pedido_embs = PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all()
                if pedido_embs:
                    for pe in pedido_embs:
                        emb = Embalagem.query.get(pe.embalagem_id)
                        nome = emb.nome if emb else '-'
                        qtd = pe.quantidade or 1
                        custo_u = round(float(emb.custo or 0), 2) if emb else 0
                        por_canal[canal]['caixas'][nome]['quantidade'] += qtd
                        por_canal[canal]['caixas'][nome]['custo_unitario'] = custo_u
                elif pedido.id_embalagem:
                    emb = Embalagem.query.get(pedido.id_embalagem)
                    nome = emb.nome if emb else '-'
                    qtd = pedido.quantidade_embalagem or 1
                    custo_u = round(float(emb.custo or 0), 2) if emb else 0
                    por_canal[canal]['caixas'][nome]['quantidade'] += qtd
                    por_canal[canal]['caixas'][nome]['custo_unitario'] = custo_u
            resultado = []
            for canal, d in sorted(por_canal.items(), key=lambda x: -x[1]['total_pedidos']):
                caixas_list = []
                for nome, v in d['caixas'].items():
                    qtd = v['quantidade']
                    custo_u = v['custo_unitario']
                    caixas_list.append({
                        'nome': nome,
                        'quantidade': qtd,
                        'custo_unitario': custo_u,
                        'valor_total': round(custo_u * qtd, 2)
                    })
                resultado.append({
                    'canal': canal,
                    'total_pedidos': d['total_pedidos'],
                    'custo_total': d['custo_total'],
                    'frete_total': d['frete_total'],
                    'frete_real_total': d['frete_real_total'],
                    'ganho_perda_liquido': d['ganho_perda_liquido'],
                    'caixas': caixas_list
                })
            return {'inicio': inicio.isoformat(), 'fim': fim.isoformat(), 'canais': resultado}
        except ValueError as e:
            raise e
        except Exception as e:
            print(f"Erro ao consolidar por canal: {str(e)}")
            return None
