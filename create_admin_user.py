#!/usr/bin/env python3
import os
import sys
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import datetime

# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://')

# Verificar se a URL do banco de dados está definida
if not database_url:
    print("Erro: Variável de ambiente DATABASE_URL não está definida.")
    print("Execute este script no Heroku com: heroku run python create_admin_user.py")
    sys.exit(1)

# Configuração da aplicação Flask
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Definição do modelo User
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
        self.password_hash = generate_password_hash(password)

def create_admin_user():
    """Cria ou atualiza o usuário admin no banco de dados"""
    with app.app_context():
        try:
            # Verificar se o usuário admin já existe
            admin = User.query.filter_by(username='admin').first()
            
            if admin:
                print("Usuário admin já existe. Atualizando senha...")
                admin.set_password('admin123')
                admin.email = 'admin@menezeslog.com'
                admin.role = 'admin'
                admin.name = 'Administrador'
                admin.active = True
                admin.first_access = True
                db.session.commit()
                print("Senha do usuário admin atualizada com sucesso!")
            else:
                print("Criando novo usuário admin...")
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
            
            # Verificar se o usuário foi criado/atualizado corretamente
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print("\nDetalhes do usuário admin:")
                print(f"ID: {admin.id}")
                print(f"Username: {admin.username}")
                print(f"Email: {admin.email}")
                print(f"Role: {admin.role}")
                print(f"Active: {admin.active}")
                print(f"First Access: {admin.first_access}")
                return True
            else:
                print("Erro: Falha ao verificar usuário admin após criação/atualização.")
                return False
                
        except Exception as e:
            print(f"Erro ao criar/atualizar usuário admin: {str(e)}")
            return False

if __name__ == "__main__":
    success = create_admin_user()
    if success:
        print("\nCredenciais para login:")
        print("Username: admin")
        print("Password: admin123")
        print("\nAgora você pode fazer login no sistema MenezesLog!")
        sys.exit(0)
    else:
        print("\nOcorreu um erro durante a criação/atualização do usuário admin.")
        sys.exit(1)
