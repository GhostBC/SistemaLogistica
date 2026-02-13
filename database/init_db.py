import os
from database.models import db, Usuario, Embalagem, CustoFrete, ConfiguracaoSistema


def init_db(app):
    """Inicializar banco de dados com dados padrão"""
    db.create_all()
    # Migrações: colunas adicionadas depois
    with app.app_context():
        try:
            from sqlalchemy import text, inspect
            insp = inspect(db.engine)
            if 'custos_frete' in insp.get_table_names():
                cols = [c['name'] for c in insp.get_columns('custos_frete')]
                if 'custo_mandae' not in cols:
                    db.session.execute(text('ALTER TABLE custos_frete ADD COLUMN custo_mandae FLOAT'))
                    db.session.commit()
            if 'embalagens' in insp.get_table_names():
                cols_emb = [c['name'] for c in insp.get_columns('embalagens')]
                if 'estoque' not in cols_emb:
                    db.session.execute(text('ALTER TABLE embalagens ADD COLUMN estoque INTEGER DEFAULT 0 NOT NULL'))
                    db.session.commit()
            if 'pedidos_logistica' in insp.get_table_names():
                cols_ped = [c['name'] for c in insp.get_columns('pedidos_logistica')]
                if 'user_id_reservado' not in cols_ped:
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN user_id_reservado INTEGER'))
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN data_reserva DATETIME'))
                    db.session.execute(text('CREATE INDEX IF NOT EXISTS ix_pedidos_logistica_user_id_reservado ON pedidos_logistica(user_id_reservado)'))
                    db.session.commit()
                if 'numero_loja' not in cols_ped:
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN numero_loja VARCHAR(50)'))
                    db.session.commit()
                if 'loja_id' not in cols_ped:
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN loja_id VARCHAR(50)'))
                    db.session.commit()
                if 'quantidade_embalagem' not in cols_ped:
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN quantidade_embalagem INTEGER DEFAULT 1 NOT NULL'))
                    db.session.commit()
                if 'peso' not in cols_ped:
                    db.session.execute(text('ALTER TABLE pedidos_logistica ADD COLUMN peso FLOAT'))
                    db.session.commit()
            
            # Criar tabela pedido_embalagens se não existir
            if 'pedido_embalagens' not in insp.get_table_names():
                db.session.execute(text('''
                    CREATE TABLE pedido_embalagens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pedido_id INTEGER NOT NULL,
                        embalagem_id INTEGER NOT NULL,
                        quantidade INTEGER NOT NULL DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (pedido_id) REFERENCES pedidos_logistica(id),
                        FOREIGN KEY (embalagem_id) REFERENCES embalagens(id)
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS ix_pedido_embalagens_pedido_id ON pedido_embalagens(pedido_id)'))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS ix_pedido_embalagens_embalagem_id ON pedido_embalagens(embalagem_id)'))
                db.session.commit()
            
            # Criar tabela de configurações se não existir
            if 'configuracoes_sistema' not in insp.get_table_names():
                db.session.execute(text('''
                    CREATE TABLE configuracoes_sistema (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave VARCHAR(50) UNIQUE NOT NULL,
                        valor VARCHAR(255) NOT NULL,
                        descricao VARCHAR(255),
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                db.session.commit()
        except Exception:
            db.session.rollback()

    # Remover usuário admin antigo (admin@logistica.local)
    admin_antigo = Usuario.query.filter_by(email='admin@logistica.local').first()
    if admin_antigo:
        db.session.delete(admin_antigo)

    # Admin: lucas.moraes@belezaruiva.com.br (substitui o admin anterior)
    lucas = Usuario.query.filter_by(email='lucas.moraes@belezaruiva.com.br').first()
    if not lucas:
        lucas = Usuario(
            email='lucas.moraes@belezaruiva.com.br',
            nome='Lucas Moraes',
            categoria='ADMIN',
            status='ativo'
        )
        db.session.add(lucas)
    # Set Password
    lucas.categoria = 'ADMIN'
    lucas.status = 'ativo'

    # Admin: paulo.castro@belezaruiva.com.br
    paulo = Usuario.query.filter_by(email='paulo.castro@belezaruiva.com.br').first()
    if not paulo:
        paulo = Usuario(
            email='paulo.castro@belezaruiva.com.br',
            nome='Paulo Castro',
            categoria='ADMIN',
            status='ativo'
        )
        db.session.add(paulo)
    # Set password
    paulo.categoria = 'ADMIN'
    paulo.status = 'ativo'

    # Criar embalagens padrão
    embalagens_padrao = [
        {'nome': 'Caixa P', 'custo': 1.00, 'altura': 10, 'largura': 10, 'comprimento': 10},
        {'nome': 'Caixa M', 'custo': 1.50, 'altura': 15, 'largura': 15, 'comprimento': 15},
        {'nome': 'Caixa G', 'custo': 2.00, 'altura': 20, 'largura': 20, 'comprimento': 20},
        {'nome': 'Envelope', 'custo': 0.50, 'altura': 5, 'largura': 20, 'comprimento': 30},
    ]

    for emb_data in embalagens_padrao:
        existe = Embalagem.query.filter_by(nome=emb_data['nome']).first()
        if not existe:
            embalagem = Embalagem(**emb_data)
            db.session.add(embalagem)

    # Criar configuração padrão de meta diária se não existir
    meta_diaria = ConfiguracaoSistema.query.filter_by(chave='meta_diaria').first()
    if not meta_diaria:
        meta_diaria = ConfiguracaoSistema(
            chave='meta_diaria',
            valor='180',
            descricao='Meta diária de pedidos'
        )
        db.session.add(meta_diaria)

    db.session.commit()
    print("Banco de dados inicializado com sucesso.")
