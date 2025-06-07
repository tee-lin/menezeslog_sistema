import os
import sys
import datetime
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar aplicação Flask
app = Flask(__name__, static_folder='src/static')
CORS(app)  # Habilitar CORS para todas as rotas

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
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
    description = db.Column(db.String(100), nullable=False)
    base_value = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type_code': self.type_code,
            'description': self.description,
            'base_value': self.base_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Importar rotas
from src.routes.auth import auth_bp
from src.routes.upload import upload_bp
from src.routes.bonus import bonus_bp
from src.routes.discount import discount_bp
from src.routes.payment import payment_bp
from src.routes.invoice import invoice_bp

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(upload_bp, url_prefix='/api/upload')
app.register_blueprint(bonus_bp, url_prefix='/api/bonus')
app.register_blueprint(discount_bp, url_prefix='/api/discount')
app.register_blueprint(payment_bp, url_prefix='/api/payment')
app.register_blueprint(invoice_bp, url_prefix='/api/invoice')

# Rotas para servir o frontend
@app.route('/')
def index():
    """Rota raiz que serve a página de login"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos do frontend"""
    if os.path.exists(os.path.join(app.static_folder, filename)):
        return send_from_directory(app.static_folder, filename)
    else:
        # Para rotas não encontradas, retornar a página principal (SPA)
        return send_from_directory(app.static_folder, 'index.html')

# Rotas para páginas específicas do frontend
@app.route('/admin_dashboard')
@app.route('/motorista_dashboard')
@app.route('/motoristas')
@app.route('/bonificacoes')
@app.route('/descontos')
@app.route('/upload')
@app.route('/relatorios')
@app.route('/nota_fiscal')
@app.route('/configuracoes')
def serve_spa_routes():
    """Serve as páginas específicas do frontend"""
    path = request.path.lstrip('/')
    if os.path.exists(os.path.join(app.static_folder, f"{path}.html")):
        return send_from_directory(app.static_folder, f"{path}.html")
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Rota para verificar status da API
@app.route('/api/status')
def status():
    """Retorna o status da API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# Rota para drivers
@app.route('/api/drivers', methods=['GET'])
def get_drivers():
    """Endpoint temporário para listar motoristas (deve ser substituído por um blueprint adequado)"""
    # Simulação de dados para teste do frontend
    drivers = [
        {"driver_id": "1001", "name": "João Silva", "status": "active", "balance": 1250.50},
        {"driver_id": "1002", "name": "Maria Oliveira", "status": "active", "balance": 980.25},
        {"driver_id": "1003", "name": "Pedro Santos", "status": "inactive", "balance": 0.00}
    ]
    return jsonify({"drivers": drivers, "total": len(drivers)})

# Rota para configurações
@app.route('/api/settings/<path:setting_type>', methods=['GET'])
def get_settings(setting_type):
    """Endpoint temporário para configurações (deve ser substituído por um blueprint adequado)"""
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
        return jsonify({"error": "Setting type not found"}), 404

# Rota para usuários
@app.route('/api/users', methods=['GET'])
def get_users():
    """Endpoint temporário para listar usuários (deve ser substituído por um blueprint adequado)"""
    # Simulação de dados para teste do frontend
    users = [
        {"id": 1, "name": "Administrador", "email": "admin@menezeslog.com", "role": "admin", "active": True},
        {"id": 2, "name": "Operador", "email": "operador@menezeslog.com", "role": "operator", "active": True}
    ]
    return jsonify({"users": users})

# Inicialização do banco de dados e dados iniciais
@app.before_first_request
def initialize_database():
    """Inicializa o banco de dados e cria dados iniciais"""
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
        print("Usuário admin criado com sucesso!")
    
    # Criar tipos de serviço padrão
    service_types = {
        0: ('Entrega Padrão', 3.50),
        9: ('Entrega Expressa', 2.00),
        6: ('Entrega Especial', 0.50),
        8: ('Entrega Econômica', 0.50)
    }
    
    for type_code, (description, base_value) in service_types.items():
        service_type = ServiceType.query.filter_by(type_code=type_code).first()
        if not service_type:
            service_type = ServiceType(
                type_code=type_code,
                description=description,
                base_value=base_value
            )
            db.session.add(service_type)
    
    db.session.commit()
    print("Tipos de serviço criados com sucesso!")

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    """Tratamento de erro 404"""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(500)
def server_error(error):
    """Tratamento de erro 500"""
    return jsonify({"error": "Internal server error", "details": str(error)}), 500

# Iniciar aplicação
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
