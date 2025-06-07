import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
import datetime
import secrets
import tempfile

# Criar aplicação Flask
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuração
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL', 'sqlite:///menezeslog.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)

# Configuração de upload de arquivos
if 'DYNO' in os.environ:  # Detecta ambiente Heroku
    base_dir = tempfile.gettempdir()
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')

# Criar diretórios necessários
dirs = ['uploads', 'invoices', 'reports', 'charts', 'exports']
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

# Rota raiz para redirecionar para a página de login
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Rota para servir arquivos estáticos
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Rota para verificar status da API
@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# Criar tabelas do banco de dados
with app.app_context():
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
