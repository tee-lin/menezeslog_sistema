import os
import sys
import datetime
import logging
import traceback
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    # Verificar a estrutura de diretórios
    logger.info(f"Diretório atual: {os.getcwd()}")
    logger.info(f"Conteúdo do diretório: {os.listdir('.')}")
    
    if os.path.exists('src'):
        logger.info(f"Conteúdo do diretório src: {os.listdir('src')}")
        if os.path.exists('src/static'):
            logger.info(f"Conteúdo do diretório src/static: {os.listdir('src/static')}")
    
    # Inicializar aplicação Flask com caminho correto para static_folder
    static_folder = 'src/static'
    if not os.path.exists(static_folder):
        logger.warning(f"Diretório static_folder '{static_folder}' não encontrado. Tentando criar...")
        os.makedirs(static_folder, exist_ok=True)
        
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    CORS(app)  # Habilitar CORS para todas as rotas
    
    # Configuração do banco de dados
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'menezeslog-secret-key')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'menezeslog-jwt-secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=30)
    
    # Configuração de upload de arquivos
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
    app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xls', 'xlsx'}
    
    # Criar diretórios necessários
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = ['uploads', 'temp', 'reports', 'invoices']
    for dir_name in dirs:
        os.makedirs(os.path.join(base_dir, dir_name), exist_ok=True)
    
    # Inicializar banco de dados
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    
    # Definir modelos diretamente aqui para evitar problemas de importação
    class User(db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(128))
        role = db.Column(db.String(20), default='user')
        name = db.Column(db.String(100))
        driver_id = db.Column(db.String(20))
        active = db.Column(db.Boolean, default=True)
        first_access = db.Column(db.Boolean, default=True)
        
        def set_password(self, password):
            from werkzeug.security import generate_password_hash
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
        
        def to_dict(self):
            return {
                'id': self.id,
                'username': self.username,
                'email': self.email,
                'role': self.role,
                'name': self.name,
                'driver_id': self.driver_id,
                'active': self.active,
                'first_access': self.first_access
            }
    
    class ServiceType(db.Model):
        __tablename__ = 'service_types'
        id = db.Column(db.Integer, primary_key=True)
        type_code = db.Column(db.Integer, unique=True, nullable=False)
        name = db.Column(db.String(100), nullable=False)  # Adicionado campo name
        description = db.Column(db.String(100), nullable=False)
        base_value = db.Column(db.Float, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
        
        def to_dict(self):
            return {
                'id': self.id,
                'type_code': self.type_code,
                'name': self.name,
                'description': self.description,
                'base_value': self.base_value,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
    
    # Importar rotas com tratamento de erros
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        logger.info("Registrado blueprint: auth_bp")
    except Exception as e:
        logger.error(f"Erro ao importar auth_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from src.routes.upload import upload_bp
        app.register_blueprint(upload_bp, url_prefix='/api/upload')
        logger.info("Registrado blueprint: upload_bp")
    except Exception as e:
        logger.error(f"Erro ao importar upload_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from src.routes.bonus import bonus_bp
        app.register_blueprint(bonus_bp, url_prefix='/api/bonus')
        logger.info("Registrado blueprint: bonus_bp")
    except Exception as e:
        logger.error(f"Erro ao importar bonus_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from src.routes.discount import discount_bp
        app.register_blueprint(discount_bp, url_prefix='/api/discount')
        logger.info("Registrado blueprint: discount_bp")
    except Exception as e:
        logger.error(f"Erro ao importar discount_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from src.routes.payment import payment_bp
        app.register_blueprint(payment_bp, url_prefix='/api/payment')
        logger.info("Registrado blueprint: payment_bp")
    except Exception as e:
        logger.error(f"Erro ao importar payment_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    try:
        from src.routes.invoice import invoice_bp
        app.register_blueprint(invoice_bp, url_prefix='/api/invoice')
        logger.info("Registrado blueprint: invoice_bp")
    except Exception as e:
        logger.error(f"Erro ao importar invoice_bp: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Rotas para servir o frontend - MODIFICADO PARA PRIORIDADE MÁXIMA
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve o frontend com prioridade máxima"""
        try:
            logger.info(f"Acessando rota: /{path}")
            
            # Verificar se é uma rota de API
            if path.startswith('api/'):
                return jsonify({"error": "Endpoint not found"}), 404
                
            # Verificar se é uma página HTML específica
            if path in ['admin_dashboard', 'motorista_dashboard', 'motoristas', 
                       'bonificacoes', 'descontos', 'upload', 'relatorios', 
                       'nota_fiscal', 'configuracoes']:
                html_file = f"{path}.html"
                if os.path.exists(os.path.join(app.static_folder, html_file)):
                    logger.info(f"Servindo página específica: {html_file}")
                    return send_from_directory(app.static_folder, html_file)
            
            # Verificar se é um arquivo estático
            if path and os.path.exists(os.path.join(app.static_folder, path)):
                logger.info(f"Servindo arquivo estático: {path}")
                return send_from_directory(app.static_folder, path)
            
            # Se não for nada específico, servir o index.html
            logger.info("Servindo index.html")
            return send_from_directory(app.static_folder, 'index.html')
            
        except Exception as e:
            logger.error(f"Erro ao servir frontend: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao carregar página", "details": str(e)}), 500
    
    # Rota para verificar status da API
    @app.route('/api/status')
    def status():
        """Retorna o status da API"""
        try:
            logger.info("Verificando status da API")
            static_files = os.listdir(app.static_folder) if os.path.exists(app.static_folder) else []
            return jsonify({
                'status': 'online',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'environment': os.environ.get('FLASK_ENV', 'production'),
                'database_connected': db.engine.connect() is not None,
                'static_folder': app.static_folder,
                'static_folder_exists': os.path.exists(app.static_folder),
                'static_files': static_files[:10]  # Listar até 10 arquivos para diagnóstico
            })
        except Exception as e:
            logger.error(f"Erro ao verificar status da API: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao verificar status", "details": str(e)}), 500
    
    # Rota para drivers
    @app.route('/api/drivers', methods=['GET'])
    def get_drivers():
        """Endpoint temporário para listar motoristas (deve ser substituído por um blueprint adequado)"""
        try:
            logger.info("Listando motoristas")
            # Simulação de dados para teste do frontend
            drivers = [
                {"driver_id": "1001", "name": "João Silva", "status": "active", "balance": 1250.50},
                {"driver_id": "1002", "name": "Maria Oliveira", "status": "active", "balance": 980.25},
                {"driver_id": "1003", "name": "Pedro Santos", "status": "inactive", "balance": 0.00}
            ]
            return jsonify({"drivers": drivers, "total": len(drivers)})
        except Exception as e:
            logger.error(f"Erro ao listar motoristas: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao listar motoristas", "details": str(e)}), 500
    
    # Rota para configurações
    @app.route('/api/settings/<path:setting_type>', methods=['GET'])
    def get_settings(setting_type):
        """Endpoint temporário para configurações (deve ser substituído por um blueprint adequado)"""
        try:
            logger.info(f"Obtendo configurações: {setting_type}")
            # Simulação de dados para teste do frontend
            settings = {
                "general": {
                    "company_name": "MenezesLog",
                    "default_currency": "BRL",
                    "timezone": "America/Sao_Paulo"
                },
                "payment": {
                    "payment_cycle": "monthly",
                    "payment_day": 5,
                    "invoice_due_days": 7,
                    "auto_generate_invoices": False
                },
                "notification": {
                    "notify_payment_processed": True,
                    "notify_invoice_generated": True,
                    "notify_driver_registered": False,
                    "admin_email": "admin@menezeslog.com"
                },
                "integration": {
                    "accounting_software": "none",
                    "api_key": ""
                }
            }
            
            if setting_type in settings:
                return jsonify(settings[setting_type])
            else:
                logger.warning(f"Tipo de configuração não encontrado: {setting_type}")
                return jsonify({"error": "Setting type not found"}), 404
        except Exception as e:
            logger.error(f"Erro ao obter configurações {setting_type}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao obter configurações", "details": str(e)}), 500
    
    # Rota para usuários
    @app.route('/api/users', methods=['GET'])
    def get_users():
        """Endpoint temporário para listar usuários (deve ser substituído por um blueprint adequado)"""
        try:
            logger.info("Listando usuários")
            # Simulação de dados para teste do frontend
            users = [
                {"id": 1, "name": "Administrador", "email": "admin@menezeslog.com", "role": "admin", "active": True},
                {"id": 2, "name": "Operador", "email": "operador@menezeslog.com", "role": "operator", "active": True}
            ]
            return jsonify({"users": users})
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao listar usuários", "details": str(e)}), 500
    
    # Inicialização do banco de dados e dados iniciais
    @app.before_first_request
    def initialize_database():
        """Inicializa o banco de dados e cria dados iniciais"""
        try:
            logger.info("Inicializando banco de dados")
            db.create_all()
            
            # Criar usuário admin padrão se não existir
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@menezeslog.com',
                    role='admin',
                    name='Administrador',
                    active=True,
                    first_access=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                logger.info("Usuário admin criado com sucesso!")
            
            # Criar tipos de serviço padrão
            service_types = {
                0: ('Entrega Padrão', 'Serviço de entrega padrão', 3.50),
                9: ('Entrega Expressa', 'Serviço de entrega expressa', 2.00),
                6: ('Entrega Especial', 'Serviço de entrega especial', 0.50),
                8: ('Entrega Econômica', 'Serviço de entrega econômica', 0.50)
            }
            
            # Usar session.no_autoflush para evitar problemas de autoflush
            with db.session.no_autoflush:
                for type_code, (name, description, base_value) in service_types.items():
                    service_type = ServiceType.query.filter_by(type_code=type_code).first()
                    if not service_type:
                        service_type = ServiceType(
                            type_code=type_code,
                            name=name,  # Adicionado campo name
                            description=description,
                            base_value=base_value
                        )
                        db.session.add(service_type)
            
            db.session.commit()
            logger.info("Tipos de serviço criados com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
            logger.error(traceback.format_exc())
            # Não propagar a exceção para permitir que a aplicação continue funcionando
            # mesmo se a inicialização do banco falhar
    
    # Tratamento de erros
    @app.errorhandler(404)
    def not_found(error):
        """Tratamento de erro 404"""
        try:
            logger.warning(f"Rota não encontrada: {request.path}")
            if request.path.startswith('/api/'):
                return jsonify({"error": "Endpoint not found"}), 404
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Erro ao tratar 404 para {request.path}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro ao processar requisição", "details": str(e)}), 500
    
    @app.errorhandler(500)
    def server_error(error):
        """Tratamento de erro 500"""
        try:
            logger.error(f"Erro 500: {str(error)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Internal server error", "details": str(error)}), 500
        except Exception as e:
            logger.error(f"Erro ao tratar 500: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Erro crítico no servidor", "details": str(e)}), 500

except Exception as e:
    logger.critical(f"Erro fatal na inicialização da aplicação: {str(e)}")
    logger.critical(traceback.format_exc())
    
    # Criar uma aplicação mínima para reportar o erro
    app = Flask(__name__)
    
    @app.route('/')
    def error_index():
        return jsonify({
            "error": "Erro crítico na inicialização da aplicação",
            "details": str(e),
            "traceback": traceback.format_exc()
        }), 500
    
    @app.route('/<path:path>')
    def error_catch_all(path):
        return jsonify({
            "error": "Erro crítico na inicialização da aplicação",
            "details": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Iniciar aplicação
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
