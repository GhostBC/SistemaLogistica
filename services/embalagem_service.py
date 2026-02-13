from database.models import db, Embalagem


class EmbalagemService:

    @staticmethod
    def listar(status=None):
        """Lista embalagens. status='ativo' filtra apenas ativas."""
        q = Embalagem.query
        if status:
            q = q.filter_by(status=status)
        return q.order_by(Embalagem.nome).all()

    @staticmethod
    def obter(id_embalagem):
        return Embalagem.query.get(id_embalagem)

    @staticmethod
    def obter_por_nome(nome):
        return Embalagem.query.filter_by(nome=nome.strip()).first()

    @staticmethod
    def criar(nome, custo, altura, largura, comprimento, peso=None, estoque=0):
        if Embalagem.query.filter_by(nome=nome.strip()).first():
            return None, 'Já existe embalagem com este nome'
        try:
            estoque_int = int(estoque) if estoque is not None else 0
        except (TypeError, ValueError):
            estoque_int = 0
        emb = Embalagem(
            nome=nome.strip(),
            custo=float(custo),
            altura=float(altura),
            largura=float(largura),
            comprimento=float(comprimento),
            peso=float(peso) if peso is not None else None,
            estoque=estoque_int,
            status='ativo'
        )
        db.session.add(emb)
        db.session.commit()
        return emb, None

    @staticmethod
    def atualizar(id_embalagem, **kwargs):
        emb = Embalagem.query.get(id_embalagem)
        if not emb:
            return None, 'Embalagem não encontrada'
        allowed = {'nome', 'custo', 'altura', 'largura', 'comprimento', 'peso', 'estoque', 'status'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if k in ('custo', 'altura', 'largura', 'comprimento', 'peso'):
                    setattr(emb, k, float(v))
                elif k == 'estoque':
                    try:
                        setattr(emb, k, int(v))
                    except (TypeError, ValueError):
                        pass
                else:
                    setattr(emb, k, v)
        db.session.commit()
        return emb, None

    @staticmethod
    def excluir(id_embalagem):
        emb = Embalagem.query.get(id_embalagem)
        if not emb:
            return False, 'Embalagem não encontrada'
        # Soft delete
        emb.status = 'inativo'
        db.session.commit()
        return True, None
