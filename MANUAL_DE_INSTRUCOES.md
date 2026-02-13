# Manual de Instruções – Sistema de Logística

## 1. Introdução

O **Sistema de Logística** é uma aplicação web (API REST) que automatiza o cálculo de custos de frete, integra com **Bling** e **Mandaê**, elimina planilhas manuais e oferece:

- Fila de pedidos em aberto (evitando F5 no Bling)
- Sistema de reserva de pedidos para evitar conflitos
- Busca e filtros avançados em pedidos em aberto e finalizados (número, canal, marketplace, transportadora, rastreio)
- Dashboard completo com métricas, gráficos interativos (pizza por canal, barras por dia do mês 1–31) e meta diária editável (ADMIN)
- Análise por canal de venda (loja) com tabela “Por Canal” e gráficos
- Cálculo de ganho/prejuízo por envio
- Relatórios diário e por período com interface em cards e tabelas (sem JSON); exportação em Excel com formatação em R$ e seções destacadas
- Automação via webhooks (Bling e Mandaê)
- Cadastro de embalagens e custos
- Integração com Bling (OAuth2 e extração automática de dados no modal de finalização)
- Interface web com header laranja, sidebar com ícones e layout responsivo

**Stack:** Flask (Python), SQLite, JWT para autenticação.

---

## 2. Requisitos e instalação

### 2.1 Requisitos

- **Python 3.10+**
- **pip** (gerenciador de pacotes Python)

### 2.2 Instalação

1. Abra o terminal na pasta do projeto:
   ```bash
   cd c:\Users\Lucas\Documents\Cursor_Projects\Python_Projects\sistema_logistica
   ```

2. (Opcional) Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Crie o arquivo de configuração a partir do exemplo:
   ```bash
   copy .env.example .env
   ```
   Depois edite o arquivo `.env` com suas chaves e configurações (veja a seção 3).

---

## 3. Configuração (.env)

O arquivo `.env` contém as variáveis de ambiente. Nunca compartilhe ou faça commit desse arquivo.

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `JWT_SECRET_KEY` | Sim | Chave secreta para assinatura dos tokens JWT (use uma string longa e aleatória em produção). |
| **Bling (OAuth2)** | | |
| `BLING_CLIENT_ID` | Para Bling | Client Id do aplicativo criado na Central de Extensões do Bling (developer.bling.com.br). |
| `BLING_CLIENT_SECRET` | Para Bling | Client Secret do aplicativo Bling. |
| `BLING_REDIRECT_URI` | Para Bling | URL de redirecionamento do app (ex.: `http://localhost:5000/api/bling/callback`). Deve ser a mesma cadastrada no aplicativo Bling. |
| **Mandaê** | Documentação: [docs.mandae.com.br/doc/intro](https://docs.mandae.com.br/doc/intro) | |
| `MANDAE_API_TOKEN` | Para Mandaê | Token da API. Obtido em **Configurações da conta → API** no aplicativo web da Mandaê. Deve ser enviado no cabeçalho **Authorization** em todas as requisições. |
| `MANDAE_API_URL` | Não | Base da API: Produção `https://api.mandae.com.br` \| Sandbox `https://sandbox.api.mandae.com.br`. Padrão: Produção. |
| `MANDAE_WEBHOOK_SECRET` | Opcional | Segredo para validar a assinatura do webhook Mandaê (se usar webhooks). |
| `DATABASE_URL` | Não | URI do banco. Padrão: `sqlite:///database/logistica.db`. |
| `LOG_LEVEL` | Não | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Padrão: `INFO`. |

**Exemplo de `.env`:**
```env
JWT_SECRET_KEY=minha-chave-secreta-com-pelo-menos-32-caracteres
BLING_CLIENT_ID=seu-client-id-bling
BLING_CLIENT_SECRET=seu-client-secret-bling
BLING_REDIRECT_URI=http://localhost:5000/api/bling/callback
MANDAE_API_TOKEN=seu-token-mandae
MANDAE_API_URL=https://api.mandae.com.br
MANDAE_WEBHOOK_SECRET=seu-webhook-secret-mandae
LOG_LEVEL=INFO
```

---

## 4. Iniciando o sistema

1. No terminal, na pasta do projeto:
   ```bash
   python app.py
   ```

2. A aplicação sobe em **http://localhost:5000**.

3. **Interface gráfica:** acesse **http://localhost:5000/app** no navegador para usar a interface web (login, dashboard, pedidos, embalagens, relatórios, Bling).

4. Para verificar se está no ar:
   - Navegador: `http://localhost:5000/health`
   - Ou no terminal: `curl http://localhost:5000/health`  
   Resposta esperada: `{"status":"ok"}`

5. **Usuários administradores** (criados/atualizados na inicialização do sistema):
   - **Admin 1:** `lucas.moraes@belezaruiva.com.br` (senha definida no código de inicialização)
   - **Admin 2:** `paulo.castro@belezaruiva.com.br` (senha definida no código de inicialização)  
   O usuário antigo `admin@logistica.local` é removido automaticamente. Em produção, evite senhas fixas no código; prefira variáveis de ambiente ou fluxo de alteração de senha.

---

## 4.1 Integração Bling (OAuth2)

A API do Bling usa **OAuth 2.0** (fluxo Authorization Code). Não há mais uso de API Key; é necessário criar um aplicativo no Bling e autorizar o sistema uma vez.

### Passos para conectar o Bling

1. **Criar um aplicativo** na [Central de Extensões do Bling](https://developer.bling.com.br/aplicativos) (área do integrador).
2. Anotar o **Client Id** e **Client Secret** e configurar no `.env` (`BLING_CLIENT_ID`, `BLING_CLIENT_SECRET`).
3. No cadastro do aplicativo, definir o **Link de redirecionamento** exatamente como:
   - Desenvolvimento: `http://localhost:5000/api/bling/callback`
   - Produção: `https://seu-dominio.com/api/bling/callback`
4. Configurar no `.env`: `BLING_REDIRECT_URI` com a mesma URL acima.
5. **Autorizar o app:** acessar no navegador:
   ```
   GET http://localhost:5000/api/bling/authorize
   ```
   O sistema redireciona para o Bling; faça login e autorize. O Bling redireciona de volta para `/api/bling/callback?code=...` e o sistema troca o `code` por **access_token** e **refresh_token**, salvando em `data/bling_tokens.json`. A partir daí, pedidos e sincronização passam a usar esse token (renovado automaticamente quando necessário).

### Endpoints Bling (OAuth)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/bling/authorize` | Redireciona para a tela de autorização OAuth2 do Bling. |
| GET | `/api/bling/callback` | URL de callback (configurada no app Bling). Troca o `code` por tokens e salva. |
| GET | `/api/bling/status` | Retorna se há tokens Bling configurados (`conectado`, `tem_token`). |

---

## 4.2 Integração Mandaê – Passo a passo detalhado

A integração com a Mandaê no sistema serve para: **consultar custo de frete** por envio (quando você finaliza um pedido) e, opcionalmente, **receber notificações** (webhooks) quando um item é processado. A documentação oficial está em [docs.mandae.com.br/doc/intro](https://docs.mandae.com.br/doc/intro).

### 4.2.1 Onde obter o token da API

A Mandaê **não usa login OAuth** na sua aplicação. Você só precisa de um **token** que é obtido no painel da Mandaê e colocado no `.env`.

**Passos:**

1. Acesse o **aplicativo web da Mandaê** (faça login na sua conta em [www.mandae.com.br](https://www.mandae.com.br) ou no painel que sua empresa usa).
2. No menu, vá em **Configurações** (ou **Configurações da conta**).
3. Procure a opção **API** (ou **Integrações / API**).
4. Nessa tela deve aparecer o **token da API** (uma chave longa, tipo `2fe6ed3b4100f65a59d2dc9eaacb934c`). Pode haver um botão para “Copiar” ou “Revelar”.
5. **Copie esse token** e guarde para colocar no `.env` (veja abaixo).

Cada **ambiente** (Sandbox e Produção) tem um token diferente. Use o token do ambiente em que você está trabalhando.

### 4.2.2 Ambientes: Sandbox (desenvolvimento) e Produção

| Ambiente   | URL da API                         | Uso                    |
|-----------|-------------------------------------|------------------------|
| **Sandbox**   | `https://sandbox.api.mandae.com.br` | Desenvolvimento e testes |
| **Produção**  | `https://api.mandae.com.br`         | Uso real, clientes     |

- Para **desenvolvimento no seu PC (localhost)**, use o ambiente **Sandbox** e o token do Sandbox.
- Para **produção**, use o ambiente **Produção** e o token de Produção (geralmente após contrato/homologação; em caso de dúvida, contate [integracao@nuvemshop.com.br](mailto:integracao@nuvemshop.com.br)).

### 4.2.3 Configurar o `.env` (localhost / desenvolvimento)

No arquivo `.env` na raiz do projeto, defina:

```env
# Token obtido em Configurações da conta → API no app Mandaê (use o token do Sandbox em dev)
MANDAE_API_TOKEN=seu-token-copiado-da-mandae

# Em desenvolvimento, use o ambiente Sandbox
MANDAE_API_URL=https://sandbox.api.mandae.com.br
```

- **`MANDAE_API_TOKEN`**: o token que você copiou no passo 4.2.1.  
- **`MANDAE_API_URL`**: em desenvolvimento com localhost, use a URL do **Sandbox** acima. Em produção, use `https://api.mandae.com.br`.

Reinicie o servidor (`python app.py`) após alterar o `.env`.

Com isso, **toda a parte da aplicação que chama a API da Mandaê** (por exemplo, consulta de custo de frete ao finalizar pedido) funciona normalmente em **localhost**, pois são **suas requisições saindo do seu PC** em direção aos servidores da Mandaê.

### 4.2.4 Webhooks: localhost x domínio HTTPS

**O que é webhook:** a Mandaê envia um **POST** para uma **URL sua** (por exemplo “quando um item for processado”). Ou seja, os **servidores da Mandaê** precisam conseguir acessar essa URL pela internet.

- **localhost** (`http://localhost:5000/...`) **não é acessível** pela internet. A Mandaê não consegue chamar `http://localhost:5000/api/webhooks/mandae`. Por isso, **em desenvolvimento puro com localhost, o webhook da Mandaê não será chamado**.
- Para o webhook **funcionar**, a URL cadastrada na Mandaê precisa ser **pública e acessível por HTTPS** (por exemplo `https://seu-dominio.com/api/webhooks/mandae`).

**Opções:**

1. **Desenvolvimento só em localhost (sem testar webhook)**  
   - Mantenha apenas `MANDAE_API_TOKEN` e `MANDAE_API_URL` no `.env` como acima.  
   - O resto da integração (consultar custos, etc.) funciona em localhost.  
   - Não cadastre webhook na Mandaê ou deixe para quando tiver um domínio.

2. **Testar webhook ainda no seu PC**  
   - Use um túnel que expõe seu localhost com uma URL HTTPS pública, por exemplo **[ngrok](https://ngrok.com)**.  
   - Exemplo: `ngrok http 5000` gera uma URL tipo `https://abc123.ngrok.io`.  
   - Na Mandaê, cadastre como URL do webhook: `https://abc123.ngrok.io/api/webhooks/mandae`.  
   - Assim a Mandaê consegue chamar sua aplicação rodando no seu PC.

3. **Produção**  
   - Suba a aplicação em um servidor com domínio e HTTPS.  
   - Cadastre na Mandaê a URL: `https://seu-dominio.com/api/webhooks/mandae`.

**Resumo:** você **pode continuar usando localhost** para desenvolver; só a **chamada da Mandaê para o seu sistema (webhook)** exige URL pública HTTPS (ou túnel como ngrok). O uso da API (token, consultas) funciona normalmente em localhost.

### 4.2.5 Webhook Mandaê no sistema (opcional)

- **Endpoint no sistema:** `POST /api/webhooks/mandae`  
- Se quiser validar a assinatura do webhook (recomendado em produção), configure no `.env` o **segredo** que a Mandaê fornecer na tela de configuração do webhook:  
  `MANDAE_WEBHOOK_SECRET=seu-segredo-fornecido-pela-mandae`

Documentação de webhooks da Mandaê: [docs.mandae.com.br](https://docs.mandae.com.br) (menu **Webhooks**).

### 4.2.6 Resumo rápido – Mandaê em desenvolvimento (localhost)

| O que fazer | Onde / Como |
|-------------|-------------|
| Obter token | Mandaê → Configurações da conta → API → copiar token |
| Colocar no projeto | `.env` → `MANDAE_API_TOKEN=...` e `MANDAE_API_URL=https://sandbox.api.mandae.com.br` |
| Reiniciar | `python app.py` |
| Webhook em localhost? | Não; use ngrok para testar ou só ative webhook em produção com HTTPS |

---

## 5. Autenticação (sistema – JWT)

Quase todas as rotas (exceto login, register, webhooks e health) exigem o **token JWT** no cabeçalho:

```
Authorization: Bearer <seu_token>
```

### 5.1 Login

- **URL:** `POST /api/auth/login`
- **Body (JSON):**
  ```json
  {
    "email": "lucas.moraes@belezaruiva.com.br",
    "senha": "sua_senha"
  }
  ```
  (Use um dos e-mails de administrador configurados no sistema.)
- **Resposta (200):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "email": "lucas.moraes@belezaruiva.com.br",
      "nome": "Lucas Moraes",
      "categoria": "ADMIN",
      "status": "ativo"
    }
  }
  ```
- Use o valor de `access_token` em todas as requisições protegidas.

### 5.2 Dados do usuário logado

- **URL:** `GET /api/auth/me`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Resposta (200):** objeto com `id`, `email`, `nome`, `categoria`, `status`.

### 5.3 Registrar novo usuário

- **URL:** `POST /api/auth/register`
- **Body (JSON):**
  ```json
  {
    "email": "novo@empresa.com",
    "senha": "senha123",
    "nome": "Nome do Usuário"
  }
  ```
- O **primeiro usuário** do sistema vira ADMIN. Os demais precisam ser criados por um usuário ADMIN (enviando o token no cabeçalho).
- **Resposta (201):** dados do usuário criado.

---

## 6. Pedidos

### 6.1 Listar pedidos em aberto (fila)

- **URL:** `GET /api/pedidos`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Query (opcional):** 
  - `?sincronizar=1` — força sincronização com o Bling antes de listar.
  - `?marketplace=<nome>` — filtra por loja (ex.: Shopee, Tray).
  - `?busca=<termo>` — busca por número do pedido, canal de venda (numero_loja), marketplace, transportadora ou código de rastreamento. Use sempre `?` antes do primeiro parâmetro (ex.: `?busca=123` ou `?status=finalizado&busca=termo`).
- **Resposta (200):** lista de pedidos com `numero_pedido`, `id_bling`, `marketplace`, `status`, `frete_cliente`, `transportadora`, `tracking_code`, `numero_loja`, `loja_id`, `loja_nome`, `embalagem`, `observacoes`, `user_id_reservado`, `data_reserva`, etc.
- **Campos adicionais:**
  - `numero_loja`: Canal de venda (numeroLoja do Bling)
  - `loja_id`: ID da loja no Bling
  - `loja_nome`: Nome da loja traduzido (TikTok, Shopee, Tray, etc.)
  - `user_id_reservado`: ID do usuário que reservou o pedido (se houver)
  - `data_reserva`: Data/hora da reserva (se houver)

### 6.2 Sincronizar pedidos com o Bling

- **URL:** `POST /api/pedidos/sincronizar`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Funcionalidade:** 
  - Busca pedidos em aberto no Bling com paginação automática (até 5 páginas, 100 itens por página)
  - Intervalo de 5 segundos entre requisições para evitar rate limiting
  - Filtra apenas pedidos com `situacao.id = 6` (pedidos em aberto)
  - Extrai e salva `numeroLoja` (canal de venda) e `loja.id` de cada pedido
  - Traduz `loja.id` para nome da loja usando mapeamento interno
- **Mapeamento de Lojas:** O sistema traduz os IDs do Bling para nomes das lojas:
  - `205483326` → TikTok
  - `204638501` → Shopee
  - `204701093` → Tray
  - `204638516` → Mercado Livre
  - `204786235` → Shein
  - `0` → Época
  - `205175249` → BLZWEB
  - `205315713` → Loja Física
  - `205513975` → Ifood
  - `AmazonMBS` → Amazon Serviços de Varejo do Brasil Ltda
- **Resposta (200):**
  ```json
  {
    "mensagem": "Sincronização concluída. N novo(s) pedido(s) inserido(s).",
    "inseridos": 5,
    "atualizados": 2
  }
  ```

### 6.3 Detalhes de um pedido

- **URL:** `GET /api/pedidos/<numero_pedido>/detalhes`  
  Exemplo: `GET /api/pedidos/12345/detalhes`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Funcionalidade:** 
  - Faz requisição ao Bling para buscar detalhes específicos do pedido
  - Extrai: `data.numeroLoja`, `loja.id`, `transporte.frete`, `volumes.servico`, `volumes.codigoRastreamento`
  - Atualiza dados do pedido no banco se não estiverem preenchidos
  - Retorna o pedido completo com informações do Bling
- **Resposta (200):** objeto do pedido com todos os campos atualizados

### 6.4 Reservar pedido

- **URL:** `POST /api/pedidos/<numero_pedido>/reservar`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Funcionalidade:** Reserva um pedido para o usuário logado, impedindo que outros usuários o finalizem
- **Resposta (200):** `{"mensagem": "Pedido reservado com sucesso"}`
- **Resposta (409):** Se o pedido já estiver reservado por outro usuário
- **Nota:** A reserva é automaticamente removida ao finalizar o pedido

### 6.5 Remover reserva de pedido

- **URL:** `DELETE /api/pedidos/<numero_pedido>/reservar`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Funcionalidade:** Remove a reserva de um pedido
- **Permissões:** Apenas o usuário que reservou ou um ADMIN pode remover a reserva
- **Resposta (200):** `{"mensagem": "Reserva removida com sucesso"}`

### 6.6 Finalizar pedido

- **URL:** `POST /api/pedidos/<numero_pedido>/finalizar`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Body (JSON):**
  ```json
  {
    "id_embalagem": 1,
    "observacoes": "Embalagem reforçada"
  }
  ```
- **Obrigatório:** `id_embalagem` (ID de uma embalagem cadastrada).
- **Funcionalidade:** 
  - O sistema calcula custo (frete + embalagem), ganho/perda e marca o pedido como finalizado
  - Remove automaticamente a reserva do pedido (se houver)
  - Opcionalmente pode ser configurada a baixa automática no Bling
- **Interface:** 
  - Ao clicar em "Finalizar pedido", o sistema reserva automaticamente o pedido para o usuário
  - Modal de finalização permite usar o botão "Obter informações do pedido" para buscar dados do Bling automaticamente
  - Campos de marketplace e transportadora são inputs de texto (não mais dropdowns) para facilitar preenchimento automático

---

## 7. Embalagens

Todas as rotas de embalagens exigem autenticação.

### 7.1 Listar embalagens

- **URL:** `GET /api/embalagens`
- **Query (opcional):** `?status=ativo` — apenas embalagens ativas.
- **Resposta (200):** lista com `id`, `nome`, `custo`, `altura`, `largura`, `comprimento`, `peso`, `status`.

### 7.2 Obter uma embalagem

- **URL:** `GET /api/embalagens/<id>`

### 7.3 Criar embalagem

- **URL:** `POST /api/embalagens`
- **Body (JSON):**
  ```json
  {
    "nome": "Caixa XL",
    "custo": 2.50,
    "altura": 25,
    "largura": 25,
    "comprimento": 25,
    "peso": 0.5
  }
  ```
- `peso` é opcional. **Resposta (201):** dados da embalagem criada.

### 7.4 Atualizar embalagem

- **URL:** `PUT /api/embalagens/<id>`
- **Body (JSON):** envie apenas os campos que deseja alterar (ex.: `nome`, `custo`, `status`).

### 7.5 Desativar embalagem

- **URL:** `DELETE /api/embalagens/<id>`
- Faz **soft delete** (marca como `status: inativo`), sem apagar o registro.

---

## 8. Relatórios

Todas as rotas de relatórios exigem autenticação.

### 8.1 Relatório diário (API JSON)

- **URL:** `GET /api/relatorios/diario/<data>`
- **Data:** formato `YYYY-MM-DD` (ex.: `2026-02-02`).
- **Resposta (200):** consolidação do dia, por exemplo:
  ```json
  {
    "data": "2026-02-02",
    "total_pedidos": 10,
    "custo_total": 150.00,
    "frete_total": 200.00,
    "ganho_total": 50.00,
    "perda_total": 0,
    "ticket_medio": 15.00,
    "margem_media": 25.5,
    "embalagens_utilizadas": [ ... ],
    "pedidos": [ ... ]
  }
  ```
- Se não houver custos na data, os totais vêm zerados (resposta 200).

### 8.2 Relatório diário (Excel)

- **URL:** `GET /api/relatorios/diario/<data>/excel`
- **Data:** `YYYY-MM-DD`.
- **Resposta (200):** download do arquivo `relatorio-logistica-YYYY-MM-DD.xlsx`.
- **Formato:** Planilha com resumo em destaque (valores em R$), tabela de detalhamento por pedido (colunas em moeda) e tabela de embalagens utilizadas no dia. Cabeçalhos com fundo cinza e formatação numérica padrão.

### 8.3 Relatório por período (API)

- **URL:** `GET /api/relatorios/periodo?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`
- **Query:** `inicio` e `fim` (se omitidos, usa últimos 30 dias até hoje).
- **Resposta (200):** totais do período, `embalagens_utilizadas` e detalhamento `por_dia`.

### 8.4 Relatório por período (Excel)

- **URL:** `GET /api/relatorios/periodo/excel?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`
- **Resposta (200):** download do arquivo Excel do período.
- **Formato:** Resumo do período com valores em R$, tabela de embalagens e detalhamento por dia, com colunas monetárias formatadas e cabeçalhos destacados.

### 8.5 Interface de Relatórios na Web

- Na aba **Relatórios** da interface web, os dados são exibidos em **cards e tabelas** (sem JSON bruto).
- **Relatório diário:** cards com Total de Pedidos, Custo Total, Pago Cliente, Frete Real, Ganho/Perda, Ticket Médio; tabelas de embalagens utilizadas e pedidos do dia.
- **Relatório por período:** cards com totais do período; tabelas de embalagens e detalhamento por dia.
- Botões **Ver relatório** e **Baixar Excel** para visualização e exportação.

---

## 9. Dashboard

- **URL:** `GET /api/dashboard`
- **Cabeçalho:** `Authorization: Bearer <token>`
- **Resposta (200):** resumo completo com métricas e dados para gráficos:
  ```json
  {
    "pedidos_abertos": 15,
    "hoje": {
      "data": "2026-02-02",
      "total_pedidos": 25,
      "custo_total": 150.00,
      "frete_total": 200.00,
      "frete_real_total": 180.00,
      "ganho_total": 50.00,
      "perda_total": 0.00
    },
    "ontem": {
      "total_pedidos": 20
    },
    "acumulado": {
      "total": 3505,
      "media_diaria": 201.0,
      "meta_diaria": 180,
      "percentual_meta": 111.6
    },
    "por_canal": [
      {"canal": "Shopee", "quantidade": 1708},
      {"canal": "Tray", "quantidade": 1222},
      {"canal": "Mercado Livre", "quantidade": 463},
      {"canal": "TikTok", "quantidade": 63},
      {"canal": "Shein", "quantidade": 46}
    ],
    "grafico_diario": [
      {"dia": 1, "quantidade": 158},
      {"dia": 2, "quantidade": 341},
      ...
    ],
    "embalagens": {
      "usadas_mes": 120,
      "total_disponiveis": 5
    }
  }
  ```
- **Métricas disponíveis:**
  - **Acumulado Total:** Total de pedidos finalizados no mês atual
  - **Média Diária:** Média de pedidos por dia no mês
  - **Dia Anterior:** Quantidade de pedidos do dia anterior
  - **Ideal Média Diária:** Meta configurável (padrão: 180)
  - **% Meta:** Percentual da meta atingida
  - **Por Canal:** Contagem de pedidos por loja/canal de venda
  - **Gráfico Diário (Pedidos Iniciados/Dia):** Dados do mês atual por **dia do mês** (1 a 31 em ordem sequencial), com linha da meta diária. Cada barra representa a quantidade de pedidos finalizados naquele dia do mês.
  - **Embalagens:** Quantidade usadas no mês e total disponível
- **Meta diária (editável):**
  - **GET** `/api/dashboard/meta` — retorna a meta diária atual.
  - **PUT** `/api/dashboard/meta` — atualiza a meta (apenas usuário ADMIN). Body: `{"meta_diaria": 233}`.
- **Interface:** O dashboard exibe gráficos interativos (pizza por canal e barras diárias) usando Chart.js, com layout que prioriza a tabela "Por Canal" (mais espaço) e cards com ícones e subtítulos.

---

## 10. Webhooks

Os webhooks **não** exigem token JWT. São chamados pelos sistemas externos (Bling, Mandaê).

### 10.1 Webhook Mandaê

- **URL:** `POST /api/webhooks/mandae`
- **Cabeçalho (recomendado):** `X-Mandae-Signature` com a assinatura do payload (validação usando `MANDAE_WEBHOOK_SECRET`).
- **Body (JSON):** payload enviado pela Mandaê (ex.: `partnerItemId`, `trackingCode`, `price`, etc.).
- O sistema registra o evento em log e atualiza o pedido correspondente (ex.: código de rastreio). **Resposta (202):** `{"status":"recebido"}`.

### 10.2 Webhook Bling

- **URL:** `POST /api/webhooks/bling`
- **Body (JSON):** payload enviado pelo Bling (novos pedidos ou atualizações).
- O sistema registra o evento em log. **Resposta (202):** `{"status":"recebido"}`.

**Configuração:** No painel do Bling e da Mandaê, cadastre as URLs acima como endpoints de webhook para os eventos desejados.

---

## 11. Resumo dos endpoints

| Método | Endpoint | Autenticação | Descrição |
|--------|----------|--------------|-----------|
| GET | `/health` | Não | Status do sistema |
| GET | `/api/bling/authorize` | Não | Redireciona para OAuth2 Bling |
| GET | `/api/bling/callback` | Não | Callback OAuth2 Bling (troca code por tokens) |
| GET | `/api/bling/status` | Não | Status da conexão Bling (tokens configurados?) |
| POST | `/api/auth/login` | Não | Login |
| GET | `/api/auth/me` | Sim | Dados do usuário logado |
| POST | `/api/auth/register` | Não* | Registrar usuário |
| GET | `/api/pedidos` | Sim | Listar pedidos em aberto (com busca opcional) |
| POST | `/api/pedidos/sincronizar` | Sim | Sincronizar com Bling (paginação automática) |
| GET | `/api/pedidos/<num>/detalhes` | Sim | Detalhes do pedido (busca dados do Bling) |
| POST | `/api/pedidos/<num>/reservar` | Sim | Reservar pedido para o usuário |
| DELETE | `/api/pedidos/<num>/reservar` | Sim | Remover reserva do pedido |
| POST | `/api/pedidos/<num>/finalizar` | Sim | Finalizar pedido (remove reserva automaticamente) |
| GET | `/api/embalagens` | Sim | Listar embalagens |
| GET | `/api/embalagens/<id>` | Sim | Obter embalagem |
| POST | `/api/embalagens` | Sim | Criar embalagem |
| PUT | `/api/embalagens/<id>` | Sim | Atualizar embalagem |
| DELETE | `/api/embalagens/<id>` | Sim | Desativar embalagem |
| GET | `/api/relatorios/diario/<data>` | Sim | Relatório diário (JSON) |
| GET | `/api/relatorios/diario/<data>/excel` | Sim | Relatório diário (Excel) |
| GET | `/api/relatorios/periodo` | Sim | Relatório por período |
| GET | `/api/relatorios/periodo/excel` | Sim | Relatório por período (Excel) |
| GET | `/api/dashboard` | Sim | Resumo (dashboard) |
| GET | `/api/dashboard/meta` | Sim | Meta diária atual |
| PUT | `/api/dashboard/meta` | Sim (ADMIN) | Atualizar meta diária |
| POST | `/api/webhooks/mandae` | Não | Webhook Mandaê |
| POST | `/api/webhooks/bling` | Não | Webhook Bling |

\* Register: primeiro usuário não precisa de token; demais precisam de token de ADMIN.

---

## 12. Exemplos de uso (cURL)

Substitua `SEU_TOKEN` pelo valor de `access_token` retornado no login.

**Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"lucas.moraes@belezaruiva.com.br\",\"senha\":\"sua_senha\"}"
```

**Listar pedidos (com token):**
```bash
curl -X GET http://localhost:5000/api/pedidos -H "Authorization: Bearer SEU_TOKEN"
```

**Listar pedidos e sincronizar com Bling:**
```bash
curl -X GET "http://localhost:5000/api/pedidos?sincronizar=1" -H "Authorization: Bearer SEU_TOKEN"
```

**Finalizar pedido:**
```bash
curl -X POST http://localhost:5000/api/pedidos/12345/finalizar -H "Authorization: Bearer SEU_TOKEN" -H "Content-Type: application/json" -d "{\"id_embalagem\":1,\"observacoes\":\"\"}"
```

**Relatório diário em Excel:**
```bash
curl -X GET "http://localhost:5000/api/relatorios/diario/2026-02-02/excel" -H "Authorization: Bearer SEU_TOKEN" -o relatorio.xlsx
```

---

## 13. Logs e solução de problemas

### 13.1 Logs

- Os logs da aplicação são gravados em **`logs/sistema.log`** e também exibidos no console.
- O nível de log é controlado por `LOG_LEVEL` no `.env` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

### 13.2 Erros comuns

| Situação | Possível causa | Ação |
|----------|----------------|------|
| 401 ao acessar rotas | Token ausente, expirado ou inválido | Fazer login novamente e usar o novo `access_token`. |
| 404 em pedido | Número de pedido inexistente no banco | Sincronizar com Bling (`POST /api/pedidos/sincronizar`) ou conferir o número. |
| 500 ao finalizar pedido | Falha ao calcular custo (ex.: API Mandaê indisponível) | Verificar `logs/sistema.log` e configuração. |
| Lista de pedidos vazia / erro Bling | Bling não conectado ou token expirado | Conectar Bling: acessar `/api/bling/authorize`, autorizar no Bling e completar o callback. Verificar `BLING_CLIENT_ID`, `BLING_CLIENT_SECRET` e `BLING_REDIRECT_URI` no `.env`. |
| "unable to open database file" | Caminho do SQLite incorreto ou permissão | O sistema cria a pasta `database/` automaticamente; verifique permissões da pasta do projeto. |
| Webhook retorna 401 | Assinatura Mandaê inválida | Conferir `MANDAE_WEBHOOK_SECRET` e formato do header `X-Mandae-Signature`. |
| 401 ao chamar API Mandaê | Token da API inválido ou ausente | Obter token em **Configurações da conta → API** no app Mandaê e configurar `MANDAE_API_TOKEN` no `.env`. Em desenvolvimento, usar `MANDAE_API_URL=https://sandbox.api.mandae.com.br` e o token do ambiente Sandbox. |

### 13.3 Testes automatizados

Para rodar os testes:

```bash
python -m pytest tests/ -v
```

---

## 14. Funcionalidades da Interface Web

### 14.0 Layout geral

- **Header (barra superior laranja):** Título "Sistema de Logística", abas de navegação (Dashboard, Pedidos, Finalizados, Embalagens, Relatórios, Bling), ícone de notificações, nome do usuário e botão "Sair". O fundo da barra é totalmente laranja (sem blocos brancos).
- **Sidebar (menu lateral):** Menu vertical com ícones e os mesmos itens do header. Itens não selecionados têm fundo cinza claro; o item ativo fica em laranja. Em telas pequenas (&lt; 768px) a sidebar é ocultada e a navegação fica apenas no header.
- **Área de conteúdo:** Largura máxima 1600px; o Dashboard e as tabelas utilizam melhor o espaço horizontal.

### 14.1 Aba Pedidos em Aberto

- **Busca:** Campo de busca com ícone; ao digitar, a lista é filtrada após 500 ms. A busca envia o parâmetro `?busca=<termo>` corretamente para a API (número do pedido, canal de venda, marketplace, transportadora ou rastreio).
- **Card de métrica:** Exibe "X pedidos em aberto" acima da tabela.
- **Colunas da tabela:** Nº Pedido, Canal de venda, Loja, Ações (Finalizar Pedido).
- **Filtro por Loja:** Clique no cabeçalho "Loja" para abrir dropdown e filtrar por canal.
- **Botões:** Adicionar Pedido Manual, Sincronizar com Bling, Atualizar lista (estilo laranja).
- **Texto informativo:** "Mostrando 1 até X de Y pedidos em aberto" abaixo da tabela.

### 14.2 Aba Finalizados

- **Busca:** Campo de busca em tempo real; a lista é filtrada pela API com `?status=finalizado&busca=<termo>` (número do pedido, marketplace, transportadora, rastreio, canal).
- **Visualização:** Lista de todos os pedidos finalizados com informações completas (Nº Pedido, Marketplace, Frete, Peso, Transportadora, Frete real, Embalagem, Rastreio, Data finalização, Ações).

### 14.3 Modal de Finalização

- **Reserva automática:** Ao abrir o modal, o pedido é automaticamente reservado para o usuário
- **Botão "Obter informações do pedido":** 
  - Faz requisição ao Bling para buscar detalhes específicos
  - Preenche automaticamente os campos: Marketplace (loja), Frete, Serviço/Transportadora, Código de rastreamento
  - Extrai dados de `volumes.servico` e `volumes.codigoRastreamento` do Bling
- **Campos:**
  - Marketplace e Transportadora são inputs de texto (não mais dropdowns) para facilitar preenchimento automático
  - Demais campos funcionam como antes

### 14.4 Dashboard

- **Métricas principais (cards grandes):**
  - Acumulado Total (verde), com subtítulo dinâmico "X pedidos em aberto"
  - Média Diária (laranja), subtítulo "Ritmo do mês atual"
  - Dia Anterior (vermelho), subtítulo "Finalizados ontem"
  - Ideal Média Diária (branco), editável via ícone de lápis (apenas ADMIN)
  - % Meta (verde claro), subtítulo "Aumente a média para atingir a meta"
- **Métricas secundárias (cards menores com ícones):**
  - Pedidos em Aberto (com ícone e subtítulo "Pendentes de finalização")
  - Ganho/Perda Hoje (R$), em verde ou vermelho conforme o valor
  - Frete Real (R$)
  - Embalagens Usadas
- **Tabela "Por Canal":** Ocupa mais espaço na tela; exibe Canal, Qtd, Pago Cliente (R$), Pago empresa (R$), Pago com embalagem (R$), Ganho/Perda (R$), Média Ganho/Perda (R$). Layout em grid prioriza esta tabela para exibir todas as colunas.
- **Gráficos:**
  - **Gráfico por Canal:** Gráfico de pizza com distribuição por loja (à direita da tabela Por Canal).
  - **Pedidos Iniciados/Dia:** Gráfico de barras com eixo X em ordem sequencial **1 a 31** (dia do mês) e linha da meta diária em verde.

## 15. Fluxo de uso sugerido

1. **Configurar** o `.env` e subir a aplicação (`python app.py`).
2. **Fazer login** na interface web ou via `POST /api/auth/login`.
3. **Sincronizar pedidos** com o botão "Sincronizar com Bling" ou `POST /api/pedidos/sincronizar`.
4. **Listar pedidos** em aberto na aba "Pedidos".
5. **Filtrar por loja** (opcional): clique no cabeçalho "Loja" para filtrar por canal de venda.
6. **Buscar pedidos** (opcional): use o campo de busca para encontrar pedidos específicos.
7. Para cada pedido:
   - Clique em "Finalizar Pedido" (o pedido será reservado automaticamente)
   - Use o botão "Obter informações do pedido" para preencher dados do Bling
   - Escolha a embalagem e finalize
8. **Dashboard:** Visualize métricas gerais, gráficos e análise por canal.
9. **Relatórios:** use `/api/relatorios/diario/<data>` ou `/excel` e `/api/relatorios/periodo` para análise detalhada.

---

**Versão do manual:** 2.1  
**Sistema de Logística** – API REST Flask + SQLite + Bling + Mandaê

---

## 16. Changelog

### Versão 2.1

#### Usuários e autenticação
- **Novos usuários administradores:** Substituição do usuário `admin@logistica.local` por dois admins configurados na inicialização: `lucas.moraes@belezaruiva.com.br` e `paulo.castro@belezaruiva.com.br`. Senhas definidas em `database/init_db.py`.

#### Interface web (layout e navegação)
- **Header:** Barra superior laranja contínua com título, abas (Dashboard, Pedidos, Finalizados, Embalagens, Relatórios, Bling), ícone de notificações, nome do usuário e botão Sair. Removido fundo branco do bloco central.
- **Sidebar:** Menu lateral com ícones (📊 Dashboard, 📋 Pedidos, ✓ Finalizados, 📦 Embalagens, 📈 Relatórios, ☁ Bling). Itens com fundo cinza claro; item ativo em laranja. Sidebar oculta em telas &lt; 768px.
- **Área de conteúdo:** Largura máxima aumentada para 1600px para melhor uso do espaço.

#### Dashboard
- **Gráfico Pedidos Iniciados/Dia:** Eixo X exibido em ordem sequencial **1 a 31** (dia do mês), em vez dos últimos 31 dias corridos. Dados referem-se ao mês atual.
- **Meta diária editável:** Endpoints GET/PUT `/api/dashboard/meta`; apenas ADMIN pode alterar. Interface com botão de editar (lápis) no card "Ideal Média Diária".
- **Cards:** Subtítulos nos cards principais (ex.: "Ritmo do mês atual", "Finalizados ontem"); card "Dia Anterior" em vermelho; ícones nos cards secundários; subtítulo dinâmico no Acumulado ("X pedidos em aberto").
- **Layout da área inferior:** Tabela "Por Canal" com mais espaço (grid 1.85fr / 1fr); gráficos "Gráfico por Canal" e "Pedidos Iniciados/Dia" com menos largura para que todas as colunas da tabela apareçam na tela.

#### Pedidos e Finalizados
- **Busca corrigida:** Montagem correta da URL com `?` no primeiro parâmetro (ex.: `?busca=123` ou `?status=finalizado&busca=termo`). Busca funciona em Pedidos em Aberto e em Finalizados.
- **Busca no backend:** Filtro por `numero_loja` (canal de venda) além de número do pedido, marketplace, transportadora e rastreio.
- **Aba Pedidos:** Card de métrica "X pedidos em aberto"; barra de busca com ícone; texto "Mostrando 1 até X de Y pedidos em aberto".

#### Relatórios
- **Interface:** Exibição em cards e tabelas (sem JSON bruto). Relatório diário e por período com cards de resumo e tabelas de embalagens e detalhamento.
- **Exportação Excel:** Formatação em moeda (R$), cabeçalhos com fundo cinza, seções claras (Resumo, Embalagens, Detalhamento). Relatório por período com endpoint `/api/relatorios/periodo/excel`.

---

### Versão 2.0

#### Novas Funcionalidades
- **Sistema de Reserva de Pedidos:** Pedidos podem ser reservados por usuários para evitar conflitos durante a finalização
- **Busca de Pedidos:** Campo de busca em tempo real nas abas "Pedidos em Aberto" e "Finalizados"
- **Paginação Automática no Bling:** Sincronização busca até 5 páginas (500 pedidos) com intervalo de 5 segundos
- **Filtro por Situação:** Apenas pedidos com `situacao.id = 6` são sincronizados
- **Coluna "Canal de Venda":** Exibe `numeroLoja` do Bling na tabela de pedidos
- **Coluna "Loja":** Exibe nome da loja traduzido (TikTok, Shopee, Tray, etc.) com filtro dropdown
- **Dashboard Completo:** Métricas principais, tabela por canal, gráficos interativos (pizza e barras), métricas financeiras e operacionais
- **Integração Melhorada com Bling:** Botão "Obter informações do pedido" no modal de finalização; extração automática de volumes e código de rastreamento; preenchimento automático de campos
- **Campos de Texto:** Marketplace e Transportadora como inputs de texto para facilitar preenchimento automático

#### Melhorias
- Interface mais intuitiva e responsiva
- Visualização de dados melhorada com gráficos
- Performance otimizada na sincronização com Bling
- Melhor organização de informações por canal de venda
