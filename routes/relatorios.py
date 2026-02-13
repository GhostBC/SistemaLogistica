from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from services.custo_service import CustoService
from services.relatorio_service import RelatorioService
from datetime import datetime, timedelta

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/api/relatorios')


@relatorios_bp.route('/diario/<data>', methods=['GET'])
@jwt_required()
def relatorio_diario(data):
    """GET /api/relatorios/diario/2026-01-30 - Consolidação de custos do dia em JSON (zeros se sem dados)."""
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        resultado = CustoService.consolidar_custo_diario(data_obj)
        if resultado is None:
            return jsonify({'erro': 'Erro ao gerar relatório'}), 500
        return jsonify(resultado), 200
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido (use YYYY-MM-DD)'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@relatorios_bp.route('/diario/<data>/excel', methods=['GET'])
@jwt_required()
def relatorio_diario_excel(data):
    """GET /api/relatorios/diario/2026-01-30/excel - Arquivo Excel com dados do dia."""
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        arquivo = RelatorioService.exportar_relatorio_excel(data_obj)
        return send_file(
            arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio-logistica-{data}.xlsx'
        ), 200
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido (use YYYY-MM-DD)'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@relatorios_bp.route('/periodo', methods=['GET'])
@jwt_required()
def relatorio_periodo():
    """GET /api/relatorios/periodo?inicio=2026-01-01&fim=2026-01-31 - Consolidação do período."""
    try:
        inicio_str = request.args.get('inicio')
        fim_str = request.args.get('fim')
        
        if not inicio_str or not fim_str:
            return jsonify({'erro': 'Parâmetros inicio e fim são obrigatórios (formato YYYY-MM-DD)'}), 400
        
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d').date()
        fim = datetime.strptime(fim_str, '%Y-%m-%d').date()
        
        resultado = RelatorioService.consolidar_periodo(inicio, fim)
        if resultado is None:
            return jsonify({'erro': 'Erro ao consolidar período'}), 500
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@relatorios_bp.route('/periodo/excel', methods=['GET'])
@jwt_required()
def relatorio_periodo_excel():
    """GET /api/relatorios/periodo/excel?inicio=2026-01-01&fim=2026-01-31 - Arquivo Excel do período."""
    try:
        inicio_str = request.args.get('inicio')
        fim_str = request.args.get('fim')
        
        if not inicio_str or not fim_str:
            return jsonify({'erro': 'Parâmetros inicio e fim são obrigatórios (formato YYYY-MM-DD)'}), 400
        
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d').date()
        fim = datetime.strptime(fim_str, '%Y-%m-%d').date()
        
        resultado = RelatorioService.consolidar_periodo(inicio, fim)
        if resultado is None:
            return jsonify({'erro': 'Erro ao consolidar período'}), 500
        
        # Usar o mesmo exportador de Excel (pode precisar de ajustes)
        arquivo = RelatorioService.exportar_relatorio_periodo_excel(inicio, fim, resultado)
        return send_file(
            arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio-logistica-{inicio_str}-{fim_str}.xlsx'
        ), 200
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@relatorios_bp.route('/por-canal', methods=['GET'])
@jwt_required()
def relatorio_por_canal():
    """GET /api/relatorios/por-canal?inicio=2026-01-01&fim=2026-01-31 - Relatório por canal com consumo de caixa por canal."""
    try:
        inicio_str = request.args.get('inicio')
        fim_str = request.args.get('fim')
        if not inicio_str or not fim_str:
            return jsonify({'erro': 'Parâmetros inicio e fim são obrigatórios (formato YYYY-MM-DD)'}), 400
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d').date()
        fim = datetime.strptime(fim_str, '%Y-%m-%d').date()
        resultado = RelatorioService.consolidar_por_canal(inicio, fim)
        if resultado is None:
            return jsonify({'erro': 'Erro ao gerar relatório por canal'}), 500
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@relatorios_bp.route('/por-canal/excel', methods=['GET'])
@jwt_required()
def relatorio_por_canal_excel():
    """GET /api/relatorios/por-canal/excel?inicio=2026-01-01&fim=2026-01-31 - Arquivo Excel do relatório por canal."""
    try:
        inicio_str = request.args.get('inicio')
        fim_str = request.args.get('fim')
        if not inicio_str or not fim_str:
            return jsonify({'erro': 'Parâmetros inicio e fim são obrigatórios (formato YYYY-MM-DD)'}), 400
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d').date()
        fim = datetime.strptime(fim_str, '%Y-%m-%d').date()
        resultado = RelatorioService.consolidar_por_canal(inicio, fim)
        if resultado is None:
            return jsonify({'erro': 'Erro ao gerar relatório por canal'}), 500
        from utils.excel_exporter import exportar_relatorio_por_canal
        arquivo = exportar_relatorio_por_canal(inicio, fim, resultado)
        return send_file(
            arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio-por-canal-{inicio_str}-{fim_str}.xlsx'
        ), 200
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
