from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(20), nullable=False, default='USER_LOGISTICA')  # ADMIN, USER_LOGISTICA
    status = db.Column(db.String(20), nullable=False, default='ativo')  # ativo, inativo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nome': self.nome,
            'categoria': self.categoria,
            'status': self.status
        }


class Embalagem(db.Model):
    __tablename__ = 'embalagens'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)  # "Caixa P", "Envelope", etc
    custo = db.Column(db.Float, nullable=False)  # R$
    altura = db.Column(db.Float, nullable=False)  # cm
    largura = db.Column(db.Float, nullable=False)  # cm
    comprimento = db.Column(db.Float, nullable=False)  # cm
    peso = db.Column(db.Float, nullable=True)  # kg (opcional)
    estoque = db.Column(db.Integer, nullable=False, default=0)  # saldo atual; baixa automática ao finalizar pedido
    status = db.Column(db.String(20), nullable=False, default='ativo')  # ativo, inativo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'custo': self.custo,
            'altura': self.altura,
            'largura': self.largura,
            'comprimento': self.comprimento,
            'peso': self.peso,
            'estoque': getattr(self, 'estoque', 0) or 0,
            'status': self.status
        }


class PedidoLogistica(db.Model):
    __tablename__ = 'pedidos_logistica'

    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(50), unique=True, nullable=False, index=True)
    id_bling = db.Column(db.String(50), nullable=False, index=True)
    marketplace = db.Column(db.String(50), nullable=False)  # 'site', 'mercado_livre', 'shopee', etc
    status = db.Column(db.String(20), nullable=False, default='aberto')  # aberto, preenchimento, finalizado

    # Dados do pedido
    frete_cliente = db.Column(db.Float, nullable=False)  # R$ pago pelo cliente
    transportadora = db.Column(db.String(120), nullable=True)
    tracking_code = db.Column(db.String(120), nullable=True)
    peso = db.Column(db.Float, nullable=True)  # Peso do pedido em kg
    numero_loja = db.Column(db.String(50), nullable=True)  # Canal de venda (numeroLoja do Bling)
    loja_id = db.Column(db.String(50), nullable=True)  # ID da loja no Bling (para traduzir para nome)

    # Dados preenchidos pelo operador
    id_embalagem = db.Column(db.Integer, db.ForeignKey('embalagens.id'), nullable=True)
    quantidade_embalagem = db.Column(db.Integer, nullable=False, default=1)  # Quantidade de embalagens usadas (padrão: 1)
    observacoes = db.Column(db.Text, nullable=True)

    # Reserva de pedido
    user_id_reservado = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)
    data_reserva = db.Column(db.DateTime, nullable=True)

    # Timestamps
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_finalizacao = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    embalagem = db.relationship('Embalagem', backref='pedidos')  # Mantido para compatibilidade (padrão: 1 embalagem)
    embalagens = db.relationship('PedidoEmbalagem', backref='pedido', cascade='all, delete-orphan', lazy='dynamic')
    usuario_reservado = db.relationship('Usuario', foreign_keys=[user_id_reservado], backref='pedidos_reservados')

    def to_dict(self, incluir_custos=False):
        resultado = {
            'id': self.id,
            'numero_pedido': self.numero_pedido,
            'id_bling': self.id_bling,
            'marketplace': self.marketplace,
            'status': self.status,
            'frete_cliente': self.frete_cliente,
            'transportadora': self.transportadora,
            'tracking_code': self.tracking_code,
            'peso': self.peso,
            'numero_loja': self.numero_loja,
            'loja_id': self.loja_id,
            'embalagem': self.embalagem.to_dict() if self.embalagem else None,  # Mantido para compatibilidade
            'quantidade_embalagem': self.quantidade_embalagem or 1,  # Mantido para compatibilidade
            'embalagens': [pe.to_dict() for pe in self.embalagens.all()] if self.embalagens else [],  # Lista de todas as embalagens
            'observacoes': self.observacoes,
            'data_abertura': self.data_abertura.isoformat() if self.data_abertura else None,
            'data_finalizacao': self.data_finalizacao.isoformat() if self.data_finalizacao else None,
            'user_id_reservado': self.user_id_reservado,
            'data_reserva': self.data_reserva.isoformat() if self.data_reserva else None,
            'usuario_reservado': self.usuario_reservado.to_dict() if self.usuario_reservado else None,
        }
        return resultado


class CustoFrete(db.Model):
    __tablename__ = 'custos_frete'

    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(50), db.ForeignKey('pedidos_logistica.numero_pedido'), nullable=False, index=True)

    # Custos
    frete_cliente = db.Column(db.Float, nullable=False)  # O quanto cliente pagou
    custo_frete_mandae = db.Column(db.Float, nullable=True)  # Custo estimado (API ou fixo por marketplace)
    custo_mandae = db.Column(db.Float, nullable=True)  # Gasto real do frete (webhook Mandaê); quando preenchido, usado no cálculo
    custo_embalagem = db.Column(db.Float, nullable=True)  # Custo da embalagem selecionada
    custo_total = db.Column(db.Float, nullable=False)  # custo_frete_efetivo + custo_embalagem (armazenado)
    ganho_perda = db.Column(db.Float, nullable=False)  # frete_cliente - custo_total (armazenado)
    margem_percentual = db.Column(db.Float, nullable=True)  # (ganho_perda / custo_total) * 100

    # Metadata
    fonte_frete = db.Column(db.String(50), nullable=False)  # 'mandae', 'mercado_livre', 'shopee', etc

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _custo_frete_efetivo(self):
        """Frete real: custo_mandae quando preenchido (webhook), senão custo_frete_mandae."""
        if self.custo_mandae is not None:
            return round(float(self.custo_mandae), 2)
        return round(float(self.custo_frete_mandae or 0), 2)

    def _custo_total_efetivo(self):
        """custo_frete_efetivo + custo_embalagem."""
        custo_frete = self._custo_frete_efetivo()
        custo_emb = round(float(self.custo_embalagem or 0), 2)
        return round(custo_frete + custo_emb, 2)

    def _ganho_perda_efetivo(self):
        """frete_cliente - custo_total_efetivo."""
        frete_cliente = round(float(self.frete_cliente or 0), 2)
        custo_total = self._custo_total_efetivo()
        return round(frete_cliente - custo_total, 2)

    def to_dict(self):
        custo_frete_efetivo = self._custo_frete_efetivo()
        custo_total_efetivo = self._custo_total_efetivo()
        ganho_perda_efetivo = self._ganho_perda_efetivo()
        margem = (ganho_perda_efetivo / custo_total_efetivo * 100) if custo_total_efetivo > 0 else 0
        return {
            'id': self.id,
            'numero_pedido': self.numero_pedido,
            'frete_cliente': self.frete_cliente,
            'custo_frete_mandae': self.custo_frete_mandae,
            'custo_mandae': self.custo_mandae,
            'frete_real': round(custo_frete_efetivo, 2),  # gasto real do frete (custo_mandae ou custo_frete_mandae)
            'custo_embalagem': self.custo_embalagem,
            'custo_total': round(custo_total_efetivo, 2),
            'ganho_perda': round(ganho_perda_efetivo, 2),
            'margem_percentual': round(margem, 2),
            'fonte_frete': self.fonte_frete
        }


class WebhookLog(db.Model):
    __tablename__ = 'webhooks_log'

    id = db.Column(db.Integer, primary_key=True)
    origem = db.Column(db.String(50), nullable=False, index=True)  # 'bling', 'mandae'
    payload = db.Column(db.JSON, nullable=False)
    status_processamento = db.Column(db.String(20), nullable=False, default='pendente')  # pendente, processado, erro
    numero_pedido = db.Column(db.String(50), nullable=True, index=True)
    mensagem_erro = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processado_em = db.Column(db.DateTime, nullable=True)


class Auditoria(db.Model):
    __tablename__ = 'auditoria'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    acao = db.Column(db.String(120), nullable=False)  # 'finalizar_pedido', 'criar_embalagem', etc
    recurso = db.Column(db.String(120), nullable=False)  # 'pedido', 'embalagem', etc
    numero_pedido = db.Column(db.String(50), nullable=True)
    dados_antes = db.Column(db.JSON, nullable=True)
    dados_depois = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PedidoEmbalagem(db.Model):
    """Tabela intermediária para relacionar pedido com múltiplas embalagens e suas quantidades."""
    __tablename__ = 'pedido_embalagens'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos_logistica.id'), nullable=False, index=True)
    embalagem_id = db.Column(db.Integer, db.ForeignKey('embalagens.id'), nullable=False, index=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    embalagem = db.relationship('Embalagem', backref='pedido_embalagens')

    def to_dict(self):
        return {
            'id': self.id,
            'embalagem_id': self.embalagem_id,
            'embalagem': self.embalagem.to_dict() if self.embalagem else None,
            'quantidade': self.quantidade
        }


class CacheSincronizacao(db.Model):
    __tablename__ = 'cache_sincronizacao'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), unique=True, nullable=False)  # 'pedidos_abertos'
    ultima_sincronizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfiguracaoSistema(db.Model):
    __tablename__ = 'configuracoes_sistema'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)  # 'meta_diaria'
    valor = db.Column(db.String(255), nullable=False)  # Valor como string (pode ser convertido conforme necessário)
    descricao = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'chave': self.chave,
            'valor': self.valor,
            'descricao': self.descricao
        }
