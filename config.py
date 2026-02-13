import os
from datetime import timedelta

# Diretório base do projeto (pasta onde está app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'sistema.log')


class Config:
    # JWT (em produção use uma chave forte gerada com: python -c "import secrets; print(secrets.token_hex(32))")
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'sua-chave-secreta-mudeme')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database/logistica.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # APIs
    # Bling: autenticação OAuth2 (developer.bling.com.br)
    BLING_CLIENT_ID = os.getenv('BLING_CLIENT_ID')
    BLING_CLIENT_SECRET = os.getenv('BLING_CLIENT_SECRET')
    BLING_REDIRECT_URI = os.getenv('BLING_REDIRECT_URI')
    BLING_OAUTH_AUTHORIZE_URL = os.getenv('BLING_OAUTH_AUTHORIZE_URL', 'https://www.bling.com.br/Api/v3/oauth/authorize')
    BLING_OAUTH_TOKEN_URL = os.getenv('BLING_OAUTH_TOKEN_URL', 'https://www.bling.com.br/Api/v3/oauth/token')
    # Mandaê: token no header Authorization (docs.mandae.com.br/doc/intro)
    MANDAE_API_TOKEN = os.getenv('MANDAE_API_TOKEN') or os.getenv('MANDAE_API_KEY')
    MANDAE_API_URL = os.getenv('MANDAE_API_URL', 'https://api.mandae.com.br')  # Sandbox: https://sandbox.api.mandae.com.br
    MANDAE_WEBHOOK_SECRET = os.getenv('MANDAE_WEBHOOK_SECRET')

    # Logs
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = LOG_FILE
    LOG_DIR = LOG_DIR

    # Bling: ids das lojas → nome (para filtro e submenu Pedidos)
    BLING_LOJAS = {
        205483326: 'TikTok',
        204638501: 'Shopee',
        204701093: 'Tray',
        204786235: 'Shein',
        0: 'Época',
        205175249: 'BLZWEB',
        205315713: 'Loja Física',
        205513975: 'Ifood',
        'AmazonMBS': 'Amazon Serviços de Varejo do Brasil Ltda',
    }
