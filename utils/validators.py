"""Validações reutilizáveis."""
import re


def is_valid_email(email):
    """Valida formato de e-mail."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def is_valid_numero_pedido(numero):
    """Valida número de pedido (não vazio, alfanumérico)."""
    if not numero or not isinstance(numero, str):
        return False
    return len(numero.strip()) > 0
