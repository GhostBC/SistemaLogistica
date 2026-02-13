"""
Integração com a API da Mandaê.
Documentação: https://docs.mandae.com.br/doc/intro

Autenticação: é preciso enviar um token válido em todas as requisições através do
cabeçalho HTTP Authorization. O token é obtido em Configurações da conta → API no app Mandaê.
Ambientes: Sandbox (sandbox.api.mandae.com.br) e Produção (api.mandae.com.br).
"""
import requests
import hmac
import hashlib
import json
import os

# Base URL: use MANDAE_API_URL no .env (Sandbox ou Produção)
MANDAE_API_BASE = os.getenv('MANDAE_API_URL', 'https://api.mandae.com.br')


def _get_token():
    """Token da API Mandaê (Configurações da conta → API)."""
    return os.getenv('MANDAE_API_TOKEN') or os.getenv('MANDAE_API_KEY') or ''


def _get_webhook_secret():
    s = os.getenv('MANDAE_WEBHOOK_SECRET') or ''
    return s.encode('utf-8') if s else b''


def _headers():
    """Headers com Authorization para requisições à API Mandaê."""
    token = _get_token()
    if not token:
        return {'Content-Type': 'application/json'}
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }


class MandaeService:

    @staticmethod
    def buscar_custo_frete(partner_item_id):
        """
        Consulta envio por partnerItemId (conforme documentação Mandaê).
        Retorna: { custo_frete, peso, dimensoes, tracking_code } ou None.
        Requer token no header Authorization (401 se token inválido).
        """
        try:
            token = _get_token()
            if not token:
                return None

            # Base conforme docs: Sandbox https://sandbox.api.mandae.com.br | Produção https://api.mandae.com.br
            base = MANDAE_API_BASE.rstrip('/')
            params = {'partnerItemId': partner_item_id}
            # Endpoint de envios (ajuste o path conforme documentação Mandaê para o recurso desejado)
            url = f"{base}/v2/shipments"
            response = requests.get(
                url,
                params=params,
                headers=_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            items = data if isinstance(data, list) else data.get('data', data.get('shipments', []))
            if not items:
                return None
            shipment = items[0] if isinstance(items[0], dict) else {}
            dims = shipment.get('dimensions', {})

            return {
                'custo_frete': float(shipment.get('price', shipment.get('valor', 0)) or 0),
                'tracking_code': shipment.get('trackingCode', shipment.get('tracking_code')),
                'peso': dims.get('weight', dims.get('peso')),
                'altura': dims.get('height', dims.get('altura')),
                'largura': dims.get('width', dims.get('largura')),
                'comprimento': dims.get('length', dims.get('comprimento')),
            }

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print("Mandaê: token da API inválido ou ausente. Configure MANDAE_API_TOKEN no .env (Configurações da conta → API).")
            else:
                print(f"Erro ao buscar custo frete da Mandaê: {e}")
            return None
        except Exception as e:
            print(f"Erro ao buscar custo frete da Mandaê: {str(e)}")
            return None

    @staticmethod
    def validar_webhook(payload, assinatura):
        """
        Validar assinatura do webhook usando MANDAE_WEBHOOK_SECRET (se configurado).
        Retorna: boolean
        """
        try:
            secret = _get_webhook_secret()
            if not secret:
                return True  # Se não configurado, aceita

            payload_str = json.dumps(payload, sort_keys=True)
            esperada = hmac.new(
                secret,
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(assinatura, esperada)

        except Exception as e:
            print(f"Erro ao validar webhook Mandaê: {str(e)}")
            return False
