import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Criar uma aplicação Flask mínima
app = Flask(__name__)

# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL', 'sqlite:///menezeslog.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
db = SQLAlchemy(app)

# Definir modelos
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    name = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    first_access = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.Integer, unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    base_value = db.Column(db.Float, nullable=False)

# Criar tabelas e usuário admin
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
    print("Tabelas e dados iniciais criados com sucesso!")
