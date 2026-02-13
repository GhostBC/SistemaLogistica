"""Funções auxiliares."""
from datetime import datetime, date


def parse_date(value, fmt='%Y-%m-%d'):
    """Converte string para date. Retorna None se inválido."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), fmt).date()
    except (ValueError, TypeError):
        return None


def format_currency(value):
    """Formata valor como moeda BRL."""
    if value is None:
        return 'R$ 0,00'
    return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
