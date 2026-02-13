from database.models import db, CustoFrete, PedidoLogistica, Embalagem, PedidoEmbalagem
from services.mandae_service import MandaeService
from services.marketplace_service import MarketplaceService
from datetime import datetime
from sqlalchemy import func


class CustoService:

    @staticmethod
    def calcular_custo_pedido(numero_pedido):
        """
        Calcular ganho/prejuízo de um pedido específico.
        custo_total = custo_frete_real + custo_embalagem
        ganho_perda = frete_cliente - custo_total
        """
        try:
            pedido = PedidoLogistica.query.filter_by(numero_pedido=numero_pedido).first()

            if not pedido:
                return None

            frete_cliente = float(pedido.frete_cliente or 0)
            
            # Calcular custo total de todas as embalagens do pedido
            custo_embalagem = 0.0
            pedido_embalagens = PedidoEmbalagem.query.filter_by(pedido_id=pedido.id).all()
            
            if pedido_embalagens and len(pedido_embalagens) > 0:
                # Usar nova estrutura de múltiplas embalagens
                for ped_emb in pedido_embalagens:
                    if ped_emb.embalagem:
                        custo_unitario = round(float(ped_emb.embalagem.custo or 0), 2)
                        quantidade = ped_emb.quantidade or 1
                        custo_embalagem = round(custo_embalagem + (custo_unitario * quantidade), 2)
            else:
                # Compatibilidade com estrutura antiga
                quantidade_embalagem = pedido.quantidade_embalagem or 1
                custo_unitario_embalagem = pedido.embalagem.custo if pedido.embalagem else 0
                custo_embalagem = round(custo_unitario_embalagem * quantidade_embalagem, 2)

            custo_frete_real = 0.0
            fonte_frete = (pedido.marketplace or 'outro').lower().strip() or 'outro'

            # Quando o cliente não pagou frete (frete_cliente = 0), não atribuímos custo de frete
            # ao pedido no relatório (evita custo fictício de R$ 12 para Shopee etc.).
            if frete_cliente and frete_cliente > 0:
                if pedido.marketplace == 'site':
                    dados_mandae = MandaeService.buscar_custo_frete(str(pedido.id_bling))
                    if dados_mandae:
                        custo_frete_real = dados_mandae['custo_frete']
                        fonte_frete = 'mandae'
                    else:
                        fonte_frete = 'mandae'

                elif (pedido.marketplace or '').lower() == 'mercado_livre':
                    custo_frete_real = 11.00
                    fonte_frete = 'mercado_livre'

                else:
                    dados = MarketplaceService.buscar_custo_frete(
                        numero_pedido=numero_pedido,
                        marketplace=pedido.marketplace
                    )
                    if dados:
                        custo_frete_real = dados['custo_frete']
                        fonte_frete = (pedido.marketplace or 'outro').lower()
                    else:
                        fonte_frete = (pedido.marketplace or 'outro').lower()

            # Arredondar valores para 2 casas decimais antes de calcular
            custo_frete_real = round(float(custo_frete_real), 2)
            custo_embalagem = round(float(custo_embalagem), 2)
            frete_cliente = round(float(frete_cliente), 2)
            
            custo_total = round(custo_frete_real + custo_embalagem, 2)
            ganho_perda = round(frete_cliente - custo_total, 2)
            margem_percentual = round((ganho_perda / custo_total * 100) if custo_total > 0 else 0, 2)

            # Evitar duplicar CustoFrete para o mesmo pedido (atualizar se já existir)
            custo = CustoFrete.query.filter_by(numero_pedido=numero_pedido).first()
            if custo:
                custo.frete_cliente = frete_cliente
                custo.custo_frete_mandae = custo_frete_real
                custo.custo_embalagem = custo_embalagem
                custo.custo_total = custo_total
                custo.ganho_perda = ganho_perda
                custo.margem_percentual = margem_percentual
                custo.fonte_frete = fonte_frete
            else:
                custo = CustoFrete(
                    numero_pedido=numero_pedido,
                    frete_cliente=frete_cliente,
                    custo_frete_mandae=custo_frete_real,
                    custo_embalagem=custo_embalagem,
                    custo_total=custo_total,
                    ganho_perda=ganho_perda,
                    margem_percentual=margem_percentual,
                    fonte_frete=fonte_frete
                )
                db.session.add(custo)

            db.session.commit()
            return custo.to_dict()

        except Exception as e:
            print(f"Erro ao calcular custo do pedido {numero_pedido}: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def consolidar_custo_diario(data):
        """
        Consolidar custos de um dia.
        data: date
        Retorna: dict com total_pedidos, custo_total, ganho_total, perda_total, ticket_medio, etc
        """
        try:
            custos = CustoFrete.query.filter(
                func.date(CustoFrete.created_at) == data
            ).all()

            # Uso de embalagens no dia (pedidos finalizados no dia, agrupado por embalagem)
            pedidos_com_embalagem = PedidoLogistica.query.filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) == data
            ).all()
            
            # Agrupar por id_embalagem e somar quantidades
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
                custo_unitario = round(float(emb.custo or 0), 2) if emb else 0.0
                valor_total = round(custo_unitario * qtd_total, 2)
                embalagens_utilizadas.append({
                    'id': id_emb,
                    'nome': emb.nome if emb else '-',
                    'quantidade': qtd_total,
                    'custo_unitario': custo_unitario,
                    'valor_total': valor_total
                })

            if not custos:
                return {
                    'data': data.isoformat(),
                    'total_pedidos': 0,
                    'custo_total': 0,
                    'frete_total': 0,
                    'frete_real_total': 0,
                    'ganho_total': 0,
                    'perda_total': 0,
                    'margem_media': 0,
                    'embalagens_utilizadas': embalagens_utilizadas,
                    'pedidos': []
                }

            total_pedidos = len(custos)
            # Arredondar cada valor para 2 casas decimais antes de somar
            custo_total = round(sum(round(c._custo_total_efetivo(), 2) for c in custos), 2)
            frete_total = round(sum(round(float(c.frete_cliente or 0), 2) for c in custos), 2)
            frete_real_total = round(sum(round(c._custo_frete_efetivo(), 2) for c in custos), 2)
            ganho_total = round(sum(round(c._ganho_perda_efetivo(), 2) for c in custos if c._ganho_perda_efetivo() > 0), 2)
            perda_total = round(sum(round(abs(c._ganho_perda_efetivo()), 2) for c in custos if c._ganho_perda_efetivo() < 0), 2)
            margens = [round((c._ganho_perda_efetivo() / c._custo_total_efetivo() * 100) if c._custo_total_efetivo() > 0 else 0, 2) for c in custos]
            margem_media = round(sum(margens) / total_pedidos if total_pedidos > 0 else 0, 2)

            # Calcular meta diária: soma da quantidade de pedidos por marketplace, depois média
            pedidos_dia = PedidoLogistica.query.filter(
                PedidoLogistica.status == 'finalizado',
                func.date(PedidoLogistica.data_finalizacao) == data
            ).all()
            
            # Agrupar por marketplace e contar
            pedidos_por_marketplace = {}
            for pedido in pedidos_dia:
                marketplace = pedido.marketplace or 'outro'
                pedidos_por_marketplace[marketplace] = pedidos_por_marketplace.get(marketplace, 0) + 1
            
            # Soma total de pedidos por marketplace
            soma_marketplaces = sum(pedidos_por_marketplace.values())
            # Média diária (soma dividida pelo número de marketplaces)
            num_marketplaces = len(pedidos_por_marketplace) if pedidos_por_marketplace else 1
            meta_diaria_calculada = round(soma_marketplaces / num_marketplaces, 1) if num_marketplaces > 0 else 0

            return {
                'data': data.isoformat(),
                'total_pedidos': total_pedidos,
                'meta_diaria': meta_diaria_calculada,
                'custo_total': round(custo_total, 2),
                'frete_total': round(frete_total, 2),
                'frete_real_total': round(frete_real_total, 2),
                'ganho_total': round(ganho_total, 2),
                'perda_total': round(perda_total, 2),
                'margem_media': round(margem_media, 2),
                'embalagens_utilizadas': embalagens_utilizadas,
                'pedidos': [c.to_dict() for c in custos]
            }

        except Exception as e:
            print(f"Erro ao consolidar custo diário {data}: {str(e)}")
            return None
