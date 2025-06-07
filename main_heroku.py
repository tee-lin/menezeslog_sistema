import os
import sys
import datetime
from flask import Flask, jsonify, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# Configuração do Flask
app = Flask(__name__)
CORS(app)

# Configuração do banco de dados
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///menezeslog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_12345')

# Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# Definição dos modelos
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    name = db.Column(db.String(100), nullable=True)
    driver_id = db.Column(db.Integer, nullable=True)
    active = db.Column(db.Boolean, default=True)
    first_access = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    base_value = db.Column(db.Float, nullable=False, default=0.0)
    type_code = db.Column(db.Integer, nullable=True, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<ServiceType {self.name}>'

# Configuração de rotas para arquivos estáticos
@app.route('/')
def index():
    return redirect('/static/index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Rota de login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        token = jwt.encode({
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'first_access': user.first_access
        })
    
    return jsonify({'message': 'Invalid credentials'}), 401

# Rota para verificar se o servidor está rodando
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

# Inicialização de dados
with app.app_context():
    # Criar tabelas se não existirem
    db.create_all()
    
    # Verificar se já existe um usuário admin
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@menezeslog.com',
            password_hash=generate_password_hash('admin'),
            role='admin',
            name='Administrador',
            active=True,
            first_access=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado com sucesso!")
    
    # Verificar se já existem tipos de serviço
    service_type = ServiceType.query.first()
    if not service_type:
        service_types = [
            ServiceType(name='Entrega Local', description='Entrega dentro da cidade', base_value=50.0, type_code=1),
            ServiceType(name='Entrega Regional', description='Entrega na região metropolitana', base_value=100.0, type_code=2),
            ServiceType(name='Entrega Estadual', description='Entrega dentro do estado', base_value=200.0, type_code=3),
            ServiceType(name='Entrega Interestadual', description='Entrega para outros estados', base_value=500.0, type_code=4)
        ]
        db.session.add_all(service_types)
        db.session.commit()
        print("Tipos de serviço criados com sucesso!")

# Importar blueprints
try:
    from src.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
except ImportError:
    print("Aviso: Não foi possível importar auth_bp")

try:
    from src.routes.drivers import drivers_bp
    app.register_blueprint(drivers_bp)
except ImportError:
    print("Aviso: Não foi possível importar drivers_bp")

try:
    from src.routes.payment import payment_bp
    app.register_blueprint(payment_bp)
except ImportError:
    print("Aviso: Não foi possível importar payment_bp")

try:
    from src.routes.invoice import invoice_bp
    app.register_blueprint(invoice_bp)
except ImportError:
    print("Aviso: Não foi possível importar invoice_bp")

try:
    from src.routes.upload import upload_bp
    app.register_blueprint(upload_bp)
except ImportError:
    print("Aviso: Não foi possível importar upload_bp")

try:
    from src.routes.service_types import service_types_bp
    app.register_blueprint(service_types_bp)
except ImportError:
    print("Aviso: Não foi possível importar service_types_bp")

try:
    from src.routes.bonus import bonus_bp
    app.register_blueprint(bonus_bp)
except ImportError:
    print("Aviso: Não foi possível importar bonus_bp")

try:
    from src.routes.discount import discount_bp
    app.register_blueprint(discount_bp)
except ImportError:
    print("Aviso: Não foi possível importar discount_bp")

# Iniciar o servidor se executado diretamente
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
