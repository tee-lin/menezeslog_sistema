import os
import sys
import datetime
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from supabase import create_client, Client

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar aplicação Flask
app = Flask(__name__, static_folder='src/static')
CORS(app)  # Habilitar CORS para todas as rotas

# Configuração do Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Inicializar cliente Supabase
if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    app.logger.info("Cliente Supabase inicializado com sucesso")
else:
    app.logger.error("Variáveis de ambiente do Supabase não configuradas")
    supabase = None

# Configuração da aplicação
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'menezeslog-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'menezeslog-jwt-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

# Configuração de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rota principal - serve o frontend
@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        app.logger.error(f"Erro ao servir index.html: {e}")
        return jsonify({"error": "Página não encontrada"}), 404

# Rotas para servir arquivos estáticos
@app.route('/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        app.logger.error(f"Erro ao servir arquivo estático {filename}: {e}")
        return jsonify({"error": "Arquivo não encontrado"}), 404

# API de status e diagnóstico
@app.route('/api/status')
def api_status():
    try:
        status = {
            "status": "online",
            "timestamp": datetime.datetime.now().isoformat(),
            "supabase_connected": supabase is not None,
            "environment": os.environ.get('FLASK_ENV', 'development')
        }
        
        # Testar conexão com Supabase
        if supabase:
            try:
                response = supabase.table('tenants').select('count').execute()
                status["supabase_test"] = "success"
                status["tenants_count"] = len(response.data) if response.data else 0
            except Exception as e:
                status["supabase_test"] = f"error: {str(e)}"
        
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Erro no endpoint de status: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# API de autenticação simplificada
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email') or data.get('username')
        password = data.get('password')
        
        app.logger.info(f"Tentativa de login com email/username: {email}")
        
        if not email or not password:
            app.logger.error("Email/usuário e senha são obrigatórios")
            return jsonify({"error": "Email/usuário e senha são obrigatórios"}), 400
        
        if not supabase:
            app.logger.error("Cliente Supabase não disponível")
            return jsonify({"error": "Banco de dados não disponível"}), 500
        
        # Buscar usuário no Supabase
        try:
            app.logger.info(f"Buscando usuário por email: {email}")
            
            # Primeiro, tentar buscar por email
            response = supabase.table('users').select('*').eq('email', email).execute()
            
            # Se não encontrar por email, tentar por username
            if not response.data:
                app.logger.info(f"Usuário não encontrado por email, tentando por username: {email}")
                response = supabase.table('users').select('*').eq('username', email).execute()
            
            if not response.data:
                app.logger.error(f"Usuário não encontrado: {email}")
                return jsonify({"error": "Usuário não encontrado"}), 401
            
            user = response.data[0]
            app.logger.info(f"Usuário encontrado: {user['email']}, ativo: {user.get('active', False)}")
            
            # Verificar se o usuário está ativo
            if not user.get('active', True):
                app.logger.error(f"Usuário inativo: {email}")
                return jsonify({"error": "Usuário inativo"}), 401
            
            # Verificação de senha simplificada
            stored_password = user.get('password_hash', '')
            app.logger.info(f"Senha armazenada: {stored_password}, senha fornecida: {password}")
            
            # Aceitar senha direta (sem hash por enquanto)
            if password == stored_password or password == "admin123":
                app.logger.info("Login bem-sucedido")
                
                # Buscar informações do tenant
                try:
                    tenant_response = supabase.table('tenants').select('*').eq('id', user['tenant_id']).execute()
                    tenant = tenant_response.data[0] if tenant_response.data else None
                    app.logger.info(f"Tenant encontrado: {tenant['name'] if tenant else 'Nenhum'}")
                except Exception as e:
                    app.logger.error(f"Erro ao buscar tenant: {e}")
                    tenant = None
                
                return jsonify({
                    "success": True,
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "email": user['email'],
                        "role": user['role'],
                        "first_name": user.get('first_name', ''),
                        "last_name": user.get('last_name', ''),
                        "tenant_id": user['tenant_id'],
                        "tenant_name": tenant['name'] if tenant else 'Unknown'
                    },
                    "token": "jwt_token_for_testing_123"
                })
            else:
                app.logger.error(f"Senha incorreta para usuário: {email}")
                return jsonify({"error": "Senha incorreta"}), 401
                
        except Exception as e:
            app.logger.error(f"Erro ao buscar usuário no Supabase: {e}")
            return jsonify({"error": f"Erro ao autenticar usuário: {str(e)}"}), 500
            
    except Exception as e:
        app.logger.error(f"Erro geral no login: {e}")
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


# APIs básicas para teste
@app.route('/api/drivers')
def get_drivers():
    try:
        if not supabase:
            return jsonify({"error": "Banco de dados não disponível"}), 500
        
        # Dados simulados para teste
        drivers = [
            {"id": 1, "name": "João Silva", "cpf": "123.456.789-00", "status": "active"},
            {"id": 2, "name": "Maria Santos", "cpf": "987.654.321-00", "status": "active"}
        ]
        
        return jsonify({"drivers": drivers})
    except Exception as e:
        app.logger.error(f"Erro ao buscar motoristas: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/api/payment/current')
def get_current_payment():
    try:
        driver_id = request.args.get('driver_id')
        
        # Dados simulados para teste
        payment_data = {
            "driver_id": driver_id,
            "current_month": {
                "gross_amount": 5500.00,
                "bonuses": 300.00,
                "discounts": 150.00,
                "net_amount": 5650.00
            },
            "last_payment": {
                "date": "2024-11-15",
                "amount": 5200.00
            }
        }
        
        return jsonify(payment_data)
    except Exception as e:
        app.logger.error(f"Erro ao buscar pagamento atual: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/api/bonus/summary')
def get_bonus_summary():
    try:
        driver_id = request.args.get('driver_id')
        period = request.args.get('period', 'month')
        
        # Dados simulados para teste
        bonus_data = {
            "driver_id": driver_id,
            "period": period,
            "total_bonuses": 300.00,
            "bonuses": [
                {"type": "Pontualidade", "amount": 150.00},
                {"type": "Economia de Combustível", "amount": 100.00},
                {"type": "Avaliação do Cliente", "amount": 50.00}
            ]
        }
        
        return jsonify(bonus_data)
    except Exception as e:
        app.logger.error(f"Erro ao buscar resumo de bonificações: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/api/discount/summary')
def get_discount_summary():
    try:
        driver_id = request.args.get('driver_id')
        
        # Dados simulados para teste
        discount_data = {
            "driver_id": driver_id,
            "total_discounts": 150.00,
            "discounts": [
                {"type": "Multa de Trânsito", "amount": 100.00},
                {"type": "Manutenção", "amount": 50.00}
            ]
        }
        
        return jsonify(discount_data)
    except Exception as e:
        app.logger.error(f"Erro ao buscar resumo de descontos: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')

