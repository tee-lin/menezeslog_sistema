import sys
import os
import tempfile
import datetime
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask_cors import CORS

# Importar modelos com uma única instância de SQLAlchemy
from src.models.models import db, User
# Não precisamos mais importar User separadamente, pois já está em models.py

# Importar rotas
from src.routes.auth import auth_bp
from src.routes.upload import upload_bp
from src.routes.bonus import bonus_bp
from src.routes.discount import discount_bp
from src.routes.payment import payment_bp
from src.routes.invoice import invoice_bp

# Criar aplicação Flask
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuração
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)

# Configuração do banco de dados - Adaptado para Heroku PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///menezeslog.db')
# Correção para URL do PostgreSQL no Heroku
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de upload de arquivos - Adaptado para Heroku
if 'DYNO' in os.environ:  # Detecta ambiente Heroku
    base_dir = tempfile.gettempdir()
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')

# Criar diretórios necessários
dirs = ['uploads', 'invoices', 'reports', 'charts', 'exports']
for dir_name in dirs:
    os.makedirs(os.path.join(base_dir, dir_name), exist_ok=True)

# Inicializar banco de dados (uma única instância)
db.init_app(app)

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
        'version': '1.0.0',
        'environment': 'Heroku' if 'DYNO' in os.environ else 'Local'
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
    from src.models.models import ServiceType
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
    # Configuração para rodar tanto localmente quanto no Heroku
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
