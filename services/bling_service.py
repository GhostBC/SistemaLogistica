"""
Integração com a API do Bling via OAuth2.
Autenticação: OAuth 2.0 (Authorization Code). Uso do access_token Bearer na API v3.
"""
import requests
import os

# API v3 do Bling (documentação: developer.bling.com.br)
BLING_API_BASE = os.getenv('BLING_API_BASE', 'https://api.bling.com.br/Api/v3')


def _get_access_token():
    """Obtém o access_token OAuth2 (do arquivo de tokens, renovando se necessário)."""
    from utils.bling_oauth import get_access_token
    return get_access_token()


def _headers():
    """Headers com Bearer token para requisições à API v3."""
    token = _get_access_token()
    if not token:
        return None
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }


class BlingService:

    @staticmethod
    def _listar_ids_pedidos_abertos():
        """
        GET /pedidos/vendas com filtro situacao=aberto.
        Busca até 11 páginas com intervalo de 5 segundos entre requisições.
        Retorna apenas lista de { 'id': id_bling, 'numero': numero }.
        """
        import time
        h = _headers()
        if not h:
            return []

        url = f"{BLING_API_BASE}/pedidos/vendas"
        resultado = []
        limite_por_pagina = 100
        max_paginas = 11
        intervalo_segundos = 5
        total_processados = 0
        total_filtrados = 0

        for pagina in range(1, max_paginas + 1):
            try:
                params = {
                    'situacao': 'aberto',
                    'limite': limite_por_pagina,
                    'pagina': pagina
                }
                response = requests.get(url, params=params, headers=h, timeout=15)
                response.raise_for_status()
                data = response.json()

                items = []
                if isinstance(data.get('data'), list):
                    items = data['data']
                elif isinstance(data.get('retorno'), dict) and 'pedidos' in data.get('retorno', {}):
                    for item in data['retorno'].get('pedidos', []):
                        items.append(item.get('pedido', item))
                elif isinstance(data.get('retorno'), list):
                    items = data['retorno']

                # Se não retornou itens, não há mais páginas
                if not items:
                    break

                for item in items:
                    pedido = item.get('pedido', item) if isinstance(item, dict) else item
                    if not isinstance(pedido, dict):
                        continue
                    
                    total_processados += 1
                    
                    # Filtrar apenas pedidos com situacao.id = 6 (API pode retornar 6 ou "6")
                    situacao = pedido.get('situacao') or {}
                    if not isinstance(situacao, dict):
                        situacao_id_raw = (
                            pedido.get('situacaoId') or
                            pedido.get('situacao_id') or
                            pedido.get('idSituacao') or
                            pedido.get('id_situacao')
                        )
                    else:
                        situacao_id_raw = (
                            situacao.get('id') or
                            situacao.get('Id') or
                            situacao.get('ID')
                        )
                    try:
                        situacao_id = int(situacao_id_raw) if situacao_id_raw is not None else None
                    except (TypeError, ValueError):
                        situacao_id = None
                    # Se não tiver situacao.id ou se for diferente de 6, pular este pedido
                    if situacao_id != 6:
                        total_filtrados += 1
                        continue
                    
                    # API v3 pode retornar id, idPedidoVenda ou id_pedido como identificador do pedido no Bling
                    id_bling = (
                        pedido.get('id') or pedido.get('idPedidoVenda') or
                        pedido.get('id_pedido') or pedido.get('idPedido')
                    )
                    numero = pedido.get('numero') or pedido.get('numeroPedido') or pedido.get('numero_pedido')
                    
                    # Extrair numeroLoja se disponível na lista inicial
                    numero_loja = None
                    data_pedido = pedido.get('data')
                    if isinstance(data_pedido, dict):
                        numero_loja = data_pedido.get('numeroLoja') or data_pedido.get('numero_loja')
                    if numero_loja is None:
                        numero_loja = pedido.get('numeroLoja') or pedido.get('numero_loja')
                    
                    # Extrair loja.id
                    loja_id = None
                    loja = pedido.get('loja') or {}
                    if isinstance(loja, dict):
                        loja_id = loja.get('id')
                    if loja_id is None:
                        loja_id = pedido.get('lojaId') or pedido.get('loja_id') or pedido.get('idLoja')
                    
                    if id_bling is not None or numero is not None:
                        resultado.append({
                            'id': id_bling if id_bling is not None else numero,
                            'numero': numero if numero is not None else id_bling,
                            'numero_loja': numero_loja,
                            'loja_id': loja_id,
                        })

                # Se retornou menos que o limite, é a última página
                if len(items) < limite_por_pagina:
                    break

                # Aguardar intervalo antes da próxima requisição (exceto na última iteração)
                if pagina < max_paginas:
                    print(f"[Bling] Página {pagina} processada. Aguardando {intervalo_segundos}s antes da próxima...")
                    time.sleep(intervalo_segundos)

            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    from utils.bling_oauth import refresh_access_token
                    if refresh_access_token():
                        h = _headers()
                        if not h:
                            break
                        continue
                print(f"Erro ao buscar página {pagina} do Bling: {e}")
                break
            except Exception as e:
                print(f"Erro ao buscar página {pagina} do Bling: {str(e)}")
                break

        print(f"[Bling] Total de pedidos processados: {total_processados}")
        print(f"[Bling] Total de pedidos filtrados (situacao.id != 6): {total_filtrados}")
        print(f"[Bling] Total de pedidos com situacao.id = 6: {len(resultado)}")
        return resultado

    @staticmethod
    def buscar_pedidos_abertos():
        """
        Apenas GET /pedidos/vendas com situacao=aberto → retorna só id e numero.
        Detalhes (frete, transportadora, tracking) são obtidos sob demanda quando o
        usuário visualiza o pedido (GET /pedidos/vendas/{id}), evitando 429 Too Many Requests.
        Retorna: list de { numero_pedido, id_bling, frete=0, transportadora=None, tracking_code=None, numero_loja=None }
        """
        try:
            ids_lista = BlingService._listar_ids_pedidos_abertos()
            pedidos = []
            for par in ids_lista:
                id_bling = par.get('id') or par.get('numero')
                numero = par.get('numero') or par.get('id')
                if id_bling is None:
                    continue
                pedidos.append({
                    'numero_pedido': str(numero) if numero is not None else str(id_bling),
                    'id_bling': str(id_bling),
                    'frete': 0,
                    'transportadora': None,
                    'tracking_code': None,
                    'numero_loja': par.get('numero_loja'),
                    'loja_id': par.get('loja_id'),
                })
            return pedidos

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                from utils.bling_oauth import refresh_access_token
                if refresh_access_token():
                    return BlingService.buscar_pedidos_abertos()
            print(f"Erro ao buscar pedidos do Bling: {e}")
            return []
        except Exception as e:
            print(f"Erro ao buscar pedidos do Bling: {str(e)}")
            return []

    @staticmethod
    def buscar_detalhes_pedido(id_bling):
        """
        GET /pedidos/vendas/{id} (ou equivalente na v3).
        id_bling deve ser o id interno do pedido no Bling (não o número do pedido).
        Retorna: { numero_pedido, id_bling, transportadora, modo_envio, frete_cliente, tracking_code, ... }
        """
        try:
            if id_bling is None:
                return None
            id_str = str(id_bling).strip()
            if not id_str:
                return None

            h = _headers()
            if not h:
                return None

            url = f"{BLING_API_BASE}/pedidos/vendas/{id_str}"
            response = requests.get(url, headers=h, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Resposta pode vir em data ou retorno
            raw = data.get('data') or data.get('retorno')
            if isinstance(raw, list) and len(raw) > 0:
                pedido = raw[0].get('pedido', raw[0])
            elif isinstance(raw, dict):
                pedido = raw.get('pedido', raw)
            else:
                pedido = data

            if not isinstance(pedido, dict):
                return None

            transporte = pedido.get('transporte') or pedido.get('frete') or {}
            if not isinstance(transporte, dict):
                transporte = {}
            valor_frete = transporte.get('valor') or transporte.get('valor_frete') or 0
            tracking = transporte.get('codigo_rastreamento') or transporte.get('codigoRastreamento')
            # Codigo de rastreamento pode vir em volumes (API v3)
            if not tracking and isinstance(pedido.get('volumes'), list) and pedido['volumes']:
                codigos = []
                for vol in pedido['volumes']:
                    if isinstance(vol, dict):
                        c = vol.get('codigoRastreamento') or vol.get('codigo_rastreamento')
                        if c:
                            codigos.append(str(c))
                if codigos:
                    tracking = codigos[0] if len(codigos) == 1 else ', '.join(codigos)
            data_pedido = pedido.get('data') or {}
            if not isinstance(data_pedido, dict):
                data_pedido = {}
            numero_loja = data_pedido.get('numeroLoja') or data_pedido.get('numero_loja') or pedido.get('numeroLoja') or pedido.get('numero_loja')
            loja = pedido.get('loja') or {}
            if not isinstance(loja, dict):
                loja = {}
            loja_id = loja.get('id')
            return {
                'numero_pedido': str(pedido.get('numero') or pedido.get('id') or ''),
                'id_bling': str(pedido.get('id') or pedido.get('numero') or ''),
                'transportadora': transporte.get('nome') or transporte.get('transportadora'),
                'modo_envio': transporte.get('tipo') or transporte.get('servico'),
                'frete_cliente': float(valor_frete) if valor_frete is not None else 0,
                'tracking_code': tracking,
                'cliente': (pedido.get('contato') or {}).get('nome') if isinstance(pedido.get('contato'), dict) else pedido.get('cliente'),
                'data': pedido.get('data') or pedido.get('dataCriacao'),
                'numero_loja': numero_loja,
                'loja_id': loja_id,
            }

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                from utils.bling_oauth import refresh_access_token
                if refresh_access_token():
                    return BlingService.buscar_detalhes_pedido(id_bling)
            print(f"Erro ao buscar detalhes do pedido {id_bling}: {e}")
            return None
        except Exception as e:
            print(f"Erro ao buscar detalhes do pedido {id_bling}: {str(e)}")
            return None

    @staticmethod
    def buscar_detalhes_pedido_para_finalizacao(id_bling):
        """
        GET /pedidos/vendas/{id} para buscar detalhes específicos do pedido.
        Retorna apenas os campos necessários para finalização:
        - data.numeroLoja (ou data.numero_loja)
        - loja.id
        - transporte.frete (ou transporte.valor)
        - volumes.servico (ou volumes[].servico)
        - volumes.codigoRastreamento (ou volumes[].codigoRastreamento)
        
        Retorna None se algum erro ocorrer, ou um dict com os campos (podendo ser None se não encontrados).
        """
        try:
            if id_bling is None:
                return None
            id_str = str(id_bling).strip()
            if not id_str:
                return None

            h = _headers()
            if not h:
                return None

            url = f"{BLING_API_BASE}/pedidos/vendas/{id_str}"
            response = requests.get(url, headers=h, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Resposta pode vir em data ou retorno
            raw = data.get('data') or data.get('retorno')
            if isinstance(raw, list) and len(raw) > 0:
                pedido = raw[0].get('pedido', raw[0])
            elif isinstance(raw, dict):
                pedido = raw.get('pedido', raw)
            else:
                pedido = data

            if not isinstance(pedido, dict):
                return None

            # Extrair data.numeroLoja - pode estar em pedido.data.numeroLoja ou pedido.numeroLoja
            numero_loja = None
            data_pedido = pedido.get('data')
            if isinstance(data_pedido, dict):
                numero_loja = data_pedido.get('numeroLoja') or data_pedido.get('numero_loja')
            # Também verificar diretamente no pedido
            if numero_loja is None:
                numero_loja = pedido.get('numeroLoja') or pedido.get('numero_loja')

            # Extrair loja.id
            loja = pedido.get('loja') or {}
            if not isinstance(loja, dict):
                loja = {}
            loja_id = loja.get('id')

            # Extrair transporte.frete (ou transporte.valor)
            transporte = pedido.get('transporte') or {}
            if not isinstance(transporte, dict):
                transporte = {}
            frete = transporte.get('frete') or transporte.get('valor') or transporte.get('valor_frete')

            # Extrair volumes.servico e volumes.codigoRastreamento
            # Os volumes estão dentro de transporte.volumes, não em pedido.volumes
            import json
            volumes = transporte.get('volumes') or pedido.get('volumes') or []
            codigo_rastreamento = None
            servico = None
            
            # Debug: verificar estrutura completa dos volumes e transporte
            if isinstance(volumes, list) and len(volumes) > 0:
                print(f"[DEBUG] Volumes encontrados: {len(volumes)} volume(s)")
                print(f"[DEBUG] Estrutura completa do primeiro volume: {json.dumps(volumes[0], indent=2, ensure_ascii=False)}")
            else:
                print(f"[DEBUG] Nenhum volume encontrado ou volumes não é uma lista")
                print(f"[DEBUG] Tipo de volumes: {type(volumes)}, Valor: {volumes}")
            
            # Verificar também na estrutura de transporte
            print(f"[DEBUG] Estrutura completa de transporte: {json.dumps(transporte, indent=2, ensure_ascii=False)}")
            
            # Primeiro, tentar buscar nos volumes
            if isinstance(volumes, list) and len(volumes) > 0:
                # Pega o primeiro volume que tiver codigoRastreamento e/ou servico
                for vol in volumes:
                    if isinstance(vol, dict):
                        # Buscar código de rastreamento - verificar várias variações possíveis
                        if codigo_rastreamento is None:
                            cod = (vol.get('codigoRastreamento') or 
                                   vol.get('codigo_rastreamento') or 
                                   vol.get('codigoRastreio') or
                                   vol.get('codigo_rastreio') or
                                   vol.get('rastreamento') or
                                   vol.get('tracking') or
                                   vol.get('codRastreamento') or
                                   vol.get('cod_rastreamento'))
                            if cod and str(cod).strip():
                                codigo_rastreamento = str(cod).strip()
                                print(f"[DEBUG] Código de rastreamento encontrado no volume: {codigo_rastreamento}")
                        # Buscar serviço - verificar várias variações possíveis
                        if servico is None:
                            s = (vol.get('servico') or 
                                 vol.get('serviço') or
                                 vol.get('servicoNome') or
                                 vol.get('servico_nome') or
                                 vol.get('nomeServico') or
                                 vol.get('nome_servico') or
                                 vol.get('servicoDescricao') or
                                 vol.get('servico_descricao') or
                                 vol.get('descricaoServico') or
                                 vol.get('descricao_servico'))
                            if s and str(s).strip():
                                servico = str(s).strip()
                                print(f"[DEBUG] Serviço encontrado no volume: {servico}")
                        # Se já encontrou ambos, pode parar
                        if codigo_rastreamento and servico:
                            break
            
            # Se não encontrou nos volumes, tentar buscar em outras estruturas
            # Verificar se está diretamente no transporte
            if codigo_rastreamento is None and isinstance(transporte, dict):
                cod = (transporte.get('codigoRastreamento') or 
                       transporte.get('codigo_rastreamento') or
                       transporte.get('codigoRastreio') or
                       transporte.get('rastreamento'))
                if cod and str(cod).strip():
                    codigo_rastreamento = str(cod).strip()
                    print(f"[DEBUG] Código de rastreamento encontrado no transporte: {codigo_rastreamento}")
            
            if servico is None and isinstance(transporte, dict):
                s = (transporte.get('servico') or 
                     transporte.get('serviço') or
                     transporte.get('servicoNome') or
                     transporte.get('nome') or
                     transporte.get('transportadora'))
                if s and str(s).strip():
                    servico = str(s).strip()
                    print(f"[DEBUG] Serviço encontrado no transporte: {servico}")
            
            # Verificar também diretamente no pedido
            if codigo_rastreamento is None:
                cod = (pedido.get('codigoRastreamento') or 
                       pedido.get('codigo_rastreamento') or
                       pedido.get('rastreamento'))
                if cod and str(cod).strip():
                    codigo_rastreamento = str(cod).strip()
                    print(f"[DEBUG] Código de rastreamento encontrado no pedido: {codigo_rastreamento}")
            
            if servico is None:
                s = (pedido.get('servico') or 
                     pedido.get('serviço') or
                     pedido.get('servicoNome'))
                if s and str(s).strip():
                    servico = str(s).strip()
                    print(f"[DEBUG] Serviço encontrado no pedido: {servico}")

            return {
                'numero_loja': numero_loja if numero_loja is not None else None,
                'loja_id': loja_id if loja_id is not None else None,
                'frete': float(frete) if frete is not None else None,
                'contato_nome': servico if servico is not None else None,  # Usando volumes.servico ao invés de transporte.contato.nome
                'codigo_rastreamento': codigo_rastreamento if codigo_rastreamento is not None else None,
            }

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                from utils.bling_oauth import refresh_access_token
                if refresh_access_token():
                    return BlingService.buscar_detalhes_pedido_para_finalizacao(id_bling)
            print(f"Erro ao buscar detalhes do pedido {id_bling} para finalização: {e}")
            return None
        except Exception as e:
            print(f"Erro ao buscar detalhes do pedido {id_bling} para finalização: {str(e)}")
            return None

    @staticmethod
    def dar_baixa_embalagem(id_bling, observacao=""):
        """
        PATCH ou PUT do pedido para situação 'Expedido' (conforme API v3).
        """
        try:
            h = _headers()
            if not h:
                return False

            url = f"{BLING_API_BASE}/pedidos/vendas/{id_bling}"
            body = {
                'situacao': 'Expedido',
                'observacoes': observacao,
            }
            response = requests.patch(url, json=body, headers=h, timeout=10)
            response.raise_for_status()
            return True

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                from utils.bling_oauth import refresh_access_token
                if refresh_access_token():
                    return BlingService.dar_baixa_embalagem(id_bling, observacao)
            print(f"Erro ao dar baixa no pedido {id_bling}: {e}")
            return False
        except Exception as e:
            print(f"Erro ao dar baixa no pedido {id_bling}: {str(e)}")
            return False
