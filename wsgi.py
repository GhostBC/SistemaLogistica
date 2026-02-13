# -*- coding: utf-8 -*-
# Arquivo WSGI para deploy na KingHost (mod_wsgi + Apache)
# Guia: https://king.host/wiki/artigo/flask-na-kinghost/
#
# No servidor:
# 1. Coloque este arquivo em /home/SEU_USUARIO/apps_wsgi/ (ex.: sistema.wsgi)
# 2. Ajuste os caminhos abaixo para o seu usuário e nome da pasta da aplicação
# 3. A aplicação deve estar em /home/SEU_USUARIO/apps_wsgi/sistemalogistica/
# 4. Crie o virtualenv dentro da pasta da app: python3 -m venv virtual_env
# 5. Ative e instale: source NOME_DA_APP/virtual_env/bin/activate && pip install -r requirements.txt
# 6. No Painel KingHost: Sessão Python > criar app, Framework "Outros"
# 7. Após alterações, recarregue: touch /home/SEU_USUARIO/apps_wsgi/sistema.wsgi

import sys
import os

# Caminho completo da pasta da aplicação no servidor (OBRIGATÓRIO ajustar antes do deploy)
# Substitua SEU_USUARIO pelo seu usuário FTP/SSH e o nome da pasta onde está o projeto
APP_DIR = '/home/SEU_USUARIO/apps_wsgi/sistemalogistica'
if not os.path.isdir(APP_DIR):
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
VIRTUALENV_ACTIVATE = os.path.join(APP_DIR, 'virtual_env', 'bin', 'activate_this.py')

if os.path.exists(VIRTUALENV_ACTIVATE):
    with open(VIRTUALENV_ACTIVATE) as f:
        exec(f.read(), dict(__file__=VIRTUALENV_ACTIVATE))

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Diretório de trabalho = pasta da aplicação (para .env e database/)
os.chdir(APP_DIR)

from app import create_app
application = create_app()
