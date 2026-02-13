# Deploy do Sistemalogistica na KingHost – Passo a passo

Você já acessou o FTP e viu a pasta **apps_wsgi** e dentro dela a pasta **sistemalogistica**. Seguem os passos para deixar o sistema no ar.

---

## O que você vai fazer em resumo

1. Enviar todo o código do projeto para dentro de **apps_wsgi/sistemalogistica**.
2. Criar um arquivo **sistema.wsgi** na pasta **apps_wsgi** (fora da pasta sistemalogistica).
3. No Painel KingHost, ativar a aplicação Python e apontar para esse arquivo.
4. (Se tiver SSH) Criar o ambiente virtual e instalar dependências; se for só FTP, a KingHost pode fazer isso pelo painel.

---

## Passo 1 – Enviar os arquivos do projeto por FTP

Na sua máquina você tem a pasta do projeto (onde está **app.py**, **requirements.txt**, etc.).

**Pelo FTP:**

1. Entre na pasta **apps_wsgi**.
2. Entre na pasta **sistemalogistica** (se não existir, crie).
3. Envie **todos** os arquivos e pastas do projeto **para dentro** de **sistemalogistica**.

No servidor deve ficar assim:

```
apps_wsgi/
├── sistemalogistica/     ← aqui dentro vai todo o projeto
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── env.txt           (configurações – passo 3; ou .env se o FTP permitir)
│   ├── wsgi.py           (pode enviar, mas não é esse que o Apache usa)
│   ├── database/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── utils/
│   └── ... (tudo que tem no projeto)
```

---

## Se o FTP der erro em alguns arquivos (.env, app.js, etc.)

Muitos FTPs bloqueiam arquivos que começam com ponto (como **.env**) ou dão erro em certos arquivos. Use estas alternativas:

### 1. Em vez de .env → use env.txt

A aplicação aceita as variáveis de ambiente em um arquivo chamado **env.txt** (sem o ponto na frente).

**O que fazer:**

1. No seu computador, na pasta do projeto, **copie** o conteúdo do seu arquivo **.env**.
2. Crie um arquivo novo chamado **env.txt** (não .env) na mesma pasta.
3. Cole o mesmo conteúdo que está no .env e salve.
4. Envie o **env.txt** por FTP para dentro de **apps_wsgi/sistemalogistica/** (na mesma pasta do **app.py**).

O sistema lê **.env** ou **env.txt**; se o .env não existir no servidor, usa o env.txt. Assim você não precisa criar .env pelo FTP.

### 2. app.js ou outros arquivos que dão erro

- **Opção A – Gerenciador de arquivos do Painel:** No Painel KingHost, procure “Gerenciador de arquivos”, “File Manager” ou “Arquivos”. Entre em **apps_wsgi/sistemalogistica/** e crie/edite o arquivo lá (copiar e colar o conteúdo do app.js, por exemplo). Muitos painéis permitem criar qualquer arquivo.
- **Opção B – Enviar em ZIP:** Na sua máquina, compacte a pasta **static** (ou só a pasta **js** com o app.js dentro) em um arquivo **static.zip**. Envie o **static.zip** por FTP para **sistemalogistica**. Se o painel tiver opção “Extrair” ou “Descompactar”, use para extrair o ZIP no mesmo lugar; assim os arquivos são criados pelo servidor e não pelo FTP.
- **Opção C – Outro cliente FTP:** Use o **FileZilla** (gratuito): em “Servidor” → “Forçar exibição de arquivos ocultos”, e tente enviar de novo. Às vezes o cliente padrão que dá problema.
- **Opção D – Renomear para enviar:** Se só o **app.js** falhar, renomeie no seu PC para **app_js.txt**, envie por FTP para **sistemalogistica/static/js/**. Depois, pelo **Gerenciador de arquivos do Painel** KingHost, renomeie **app_js.txt** para **app.js**.

### 3. Resumo

| Problema     | Solução                                      |
|-------------|-----------------------------------------------|
| Não consigo criar .env | Crie **env.txt** com o mesmo conteúdo e envie. |
| Erro ao enviar app.js  | Use o Gerenciador de arquivos do painel ou envie em ZIP e descompacte. |

---

## Passo 2 – Criar o arquivo .wsgi na pasta apps_wsgi

O arquivo **.wsgi** fica na pasta **apps_wsgi**, **fora** da pasta sistemalogistica. Ele é o que o servidor usa para rodar sua aplicação.

**Pelo FTP:**

1. Volte para a pasta **apps_wsgi** (não fique dentro de sistemalogistica).
2. Crie um arquivo novo chamado **sistema.wsgi** (ou o nome que o Painel KingHost pedir, ex.: **sistemalogistica.wsgi**).
3. Abra esse arquivo para editar e cole o conteúdo abaixo.

**Conteúdo do arquivo sistema.wsgi:**

```python
# -*- coding: utf-8 -*-
import sys
import os

# Caminho da pasta da aplicação (nome da pasta = sistemalogistica)
APP_DIR = '/home/SEU_USUARIO/apps_wsgi/sistemalogistica'
VIRTUALENV_ACTIVATE = os.path.join(APP_DIR, 'virtual_env', 'bin', 'activate_this.py')

if os.path.exists(VIRTUALENV_ACTIVATE):
    with open(VIRTUALENV_ACTIVATE) as f:
        exec(f.read(), dict(__file__=VIRTUALENV_ACTIVATE))

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.chdir(APP_DIR)

from app import create_app
application = create_app()
```

**Uma coisa que você precisa ajustar:**  
Troque **SEU_USUARIO** pelo seu usuário de FTP/SSH da KingHost (é o nome da sua conta de hospedagem, às vezes aparece no caminho quando você está no FTP, por exemplo `/home/meuusuario/...`).  
Exemplo: se seu usuário for **belaruiva**, a linha fica:

```python
APP_DIR = '/home/belaruiva/apps_wsgi/sistemalogistica'
```

Salve o arquivo.

---

## Passo 3 – Arquivo de configuração (env.txt ou .env) dentro de sistemalogistica

Na pasta **sistemalogistica** (junto do **app.py**), use **um** dos dois:

- **env.txt** (recomendado no FTP: não tem ponto no nome e o app aceita)
- **.env** (se o seu FTP/painel deixar criar)

Crie o arquivo **env.txt** (ou .env) com o seguinte (ajuste o que for seu):

```ini
FLASK_ENV=production
FLASK_DEBUG=False

# Se a URL do sistema for www.belaruiva.com.br/sistema
APPLICATION_ROOT=/sistema

# Chave secreta (gere uma nova em produção)
JWT_SECRET_KEY=c01b4e9c701e4d2373ceab164d641c99bb66a8ae32c481b78d34e4646c1017c7

DATABASE_URL=sqlite:///database/logistica.db
LOG_LEVEL=INFO

# Bling – coloque seus dados e a URL de produção
BLING_CLIENT_ID=seu_client_id
BLING_CLIENT_SECRET=seu_client_secret
BLING_REDIRECT_URI=https://www.belaruiva.com.br/sistema/api/bling/callback

# Mandaê (se usar)
MANDAE_API_TOKEN=seu_token
MANDAE_API_URL=https://api.mandae.com.br
```

Se a aplicação for acessada em **www.belaruiva.com.br/sistema**, mantenha **APPLICATION_ROOT=/sistema**. Se for em outra URL, ajuste conforme o Painel KingHost.

---

## Passo 4 – Painel KingHost (Python)

1. Acesse o **Painel de Controle** da KingHost.
2. Selecione o **domínio** (ex.: belaruiva.com.br).
3. Procure a seção **Python** (ou **Aplicações Python**).
4. Crie uma nova aplicação:
   - **Nome:** por exemplo **sistemalogistica** ou **sistema**.
   - **Framework:** escolha **Outros** (não Django).
   - O painel deve pedir o arquivo **.wsgi**: use **sistema.wsgi** (ou o nome que você deu no Passo 2).
   - Se pedir **caminho/URL**, use **/sistema** para ficar em **www.belaruiva.com.br/sistema**.

Se a KingHost pedir o caminho do arquivo .wsgi, será algo como:  
`/home/SEU_USUARIO/apps_wsgi/sistema.wsgi`

---

## Passo 5 – Ambiente virtual e dependências (Python)

A aplicação precisa do **virtualenv** e dos pacotes do **requirements.txt**.

**Se você tiver acesso SSH:**

```bash
cd /home/SEU_USUARIO/apps_wsgi/sistemalogistica
python3 -m venv virtual_env
source virtual_env/bin/activate
pip install -r requirements.txt
```

**Se usar só FTP:**  
Algumas hospedagens criam o ambiente pelo Painel (opção tipo “Instalar dependências” ou “Criar ambiente”). Se não houver, será necessário abrir um chamado na KingHost pedindo para ativar o ambiente Python na pasta **apps_wsgi/sistemalogistica** e rodar `pip install -r requirements.txt` dentro do virtualenv.

---

## Passo 6 – Testar

Depois de salvar o .wsgi e configurar no painel:

- **Interface:** **https://www.belaruiva.com.br/sistema/app**
- **Login da API:** **POST** **https://www.belaruiva.com.br/sistema/api/auth/login**

Se der erro 500, veja o **error.log** no FTP (geralmente na pasta do usuário) ou os logs que o Painel KingHost mostrar.

---

## Resumo rápido

| O quê              | Onde                          |
|--------------------|--------------------------------|
| Código do projeto  | **apps_wsgi/sistemalogistica/** |
| Arquivo .wsgi      | **apps_wsgi/sistema.wsgi**      |
| Arquivo de config | **apps_wsgi/sistemalogistica/env.txt** (ou .env) |
| Ajustar no .wsgi   | Só a linha do **APP_DIR** com seu usuário |

Nome do sistema em todo o projeto: **Sistemalogistica**.  
Pasta no servidor: **sistemalogistica** (dentro de **apps_wsgi**).
