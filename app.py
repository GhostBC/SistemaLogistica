import os

# Carregar .env antes de qualquer import que use os.getenv (config, utils, etc.)
from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)
load_dotenv()

import logging
from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from database.models import db
from database.init_db import init_db
from config import Config
from middleware.errors import register_error_handlers


def setup_logging(app):
    """Configura logging para arquivo logs/sistema.log e console."""
    os.makedirs(app.config.get('LOG_DIR', 'logs'), exist_ok=True)
    log_file = app.config.get('LOG_FILE', 'logs/sistema.log')
    log_level = getattr(logging, (app.config.get('LOG_LEVEL') or 'INFO').upper(), logging.INFO)

    fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    # Arquivo
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(log_level)
    fh.setFormatter(fmt)
    app.logger.addHandler(fh)
    # Console
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(fmt)
    app.logger.addHandler(ch)
    app.logger.setLevel(log_level)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Garantir diretório e caminho absoluto para SQLite (evitar "unable to open database file")
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if uri and 'sqlite' in uri and ':memory:' not in uri and 'database' in uri:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(base_dir, 'database')
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'logistica.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path.replace('\\', '/')

    setup_logging(app)

    db.init_app(app)
    JWTManager(app)
    CORS(app)

    from routes.auth import auth_bp
    from routes.pedidos import pedidos_bp
    from routes.embalagens import embalagens_bp
    from routes.webhooks import webhooks_bp
    from routes.relatorios import relatorios_bp
    from routes.dashboard import dashboard_bp
    from routes.bling_oauth import bling_oauth_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(embalagens_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bling_oauth_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)

    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'ok'}, 200

    @app.route('/', methods=['GET'])
    def index():
        return {
            'sistema': 'Sistema de Logística',
            'health': '/health',
            'app': '/app (interface gráfica)',
            'bling_oauth_authorize': '/api/bling/authorize',
            'bling_oauth_callback': '/api/bling/callback',
            'bling_status': '/api/bling/status',
            'login': 'POST /api/auth/login',
        }, 200

    @app.route('/app', methods=['GET'])
    def app_interface():
        """Interface gráfica do sistema (login, dashboard, pedidos, etc.)."""
        return render_template('index.html')

    with app.app_context():
        init_db(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
