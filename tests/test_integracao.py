import pytest
from datetime import date
from app import create_app
from database.models import db, PedidoLogistica, Embalagem, CustoFrete
from services.custo_service import CustoService
from services.relatorio_service import RelatorioService


@pytest.fixture
def app_db():
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    return app


def test_consolidar_custo_diario_vazio(app_db):
    with app_db.app_context():
        res = CustoService.consolidar_custo_diario(date(2026, 1, 15))
        assert res is not None
        assert res['total_pedidos'] == 0
        assert res['custo_total'] == 0
        assert 'pedidos' in res


def test_consolidar_periodo(app_db):
    with app_db.app_context():
        res = RelatorioService.consolidar_periodo(
            date(2026, 1, 1),
            date(2026, 1, 31)
        )
        assert res is not None
        assert 'total_pedidos' in res
        assert 'por_dia' in res
        assert res['inicio'] == '2026-01-01'
        assert res['fim'] == '2026-01-31'
