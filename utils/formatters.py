"""Formatação de dados para respostas da API."""
from datetime import datetime, date


def format_datetime(dt):
    """Retorna datetime em ISO ou None."""
    if dt is None:
        return None
    if isinstance(dt, (datetime, date)):
        return dt.isoformat()
    return str(dt)


def format_pedido_response(pedido, incluir_custos=False):
    """Formata um PedidoLogistica para resposta JSON."""
    return pedido.to_dict(incluir_custos=incluir_custos) if pedido else None
