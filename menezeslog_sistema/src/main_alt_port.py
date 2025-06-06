import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
import datetime
import secrets

# Criar aplicação Flask
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuração
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///menezeslog.db'  # Usando SQLite para demonstração
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)

# Configuração de upload de arquivos
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')

# Criar diretórios necessários
base_dir = os.path.dirname(os.path.abspath(__file__))
dirs = ['uploads', 'invoices', 'reports', 'charts', 'exports']
for dir_name in dirs:
    os.makedirs(os.path.join(base_dir, dir_name), exist_ok=True)

# Rota raiz para teste
@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Sistema MenezesLog funcionando!"})

# Rota para verificar status da API
@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
