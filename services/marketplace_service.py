"""
Serviço para custos de frete de marketplaces (Mercado Livre, Shopee, etc).
Valores fixos ou integração futura com APIs.
"""
from database.models import CustoFrete
from datetime import datetime
from sqlalchemy import func


# Custos fixos por marketplace (podem vir de config/banco no futuro)
CUSTO_FLEX_ML = 11.00
CUSTO_SHOPEE = 12.00  # exemplo
CUSTO_TIKTOK = 12.00
CUSTO_SHEIN = 10.00
CUSTO_CORREIOS = 15.00  # exemplo


class MarketplaceService:

    @staticmethod
    def buscar_custo_frete(numero_pedido, marketplace):
        """
        Retorna custo de frete para o marketplace.
        numero_pedido: str
        marketplace: str ('mercado_livre', 'shopee', etc)
        Retorna: { 'custo_frete': float } ou None
        """
        custos = {
            'mercado_livre': CUSTO_FLEX_ML,
            'shopee': CUSTO_SHOPEE,
            'tiktok': CUSTO_TIKTOK,
            'shein': CUSTO_SHEIN,
            'correios': CUSTO_CORREIOS,
        }
        valor = custos.get((marketplace or '').lower().strip())
        if valor is not None:
            return {'custo_frete': valor}
        return None
