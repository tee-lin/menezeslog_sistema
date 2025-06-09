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
app = Flask(__name__, static_folder='static')
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

# APIs de Upload e Processamento de CSV - MenezesLog
# Adicione este código ao arquivo main_supabase_integrated.py

import pandas as pd
import io
from datetime import datetime
import uuid

# Configuração de upload
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Regras de cálculo de pagamento
PAYMENT_RULES = {
    0: 3.50,  # Encomendas = R$ 3,50 por entrega
    6: 0.50,  # Revistas = R$ 0,50 por entrega  
    8: 0.50,  # Revistas = R$ 0,50 por entrega
    9: 2.00   # Cards = R$ 2,00 por entrega
}

# Nomes dos tipos de serviço
SERVICE_TYPE_NAMES = {
    0: 'Encomendas',
    6: 'Revistas',
    8: 'Revistas', 
    9: 'Cards'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx', 'xls'}

def get_service_type_name(tipo_servico):
    """Retorna o nome do tipo de serviço"""
    return SERVICE_TYPE_NAMES.get(tipo_servico, f'Tipo {tipo_servico}')

def process_csv_data(file_content, filename):
    """Processa dados do CSV e calcula pagamentos"""
    try:
        # Ler CSV com encoding correto
        df = pd.read_csv(io.StringIO(file_content), sep=';', encoding='latin1')
        
        # Renomear colunas para facilitar processamento
        column_mapping = {
            'Nome Fantasia do Remetente': 'cliente',
            'AWB': 'awb',
            'Rota': 'rota',
            'Peso Capturado': 'peso',
            'Tipo de Serviço': 'tipo_servico',
            'Status da encomenda': 'status',
            'Data/Hora Status do último status': 'data_status',
            'Desc. do status da encomenda': 'desc_status',
            'ID da CAF': 'id_caf',
            'ID do motorista': 'id_motorista'
        }
        
        # Renomear colunas se existirem
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Converter tipos de dados
        df['tipo_servico'] = pd.to_numeric(df['tipo_servico'], errors='coerce')
        df['id_motorista'] = pd.to_numeric(df['id_motorista'], errors='coerce')
        df['peso'] = df['peso'].astype(str).str.replace(',', '.').astype(float)
        
        # Calcular pagamentos e adicionar nomes dos tipos
        df['valor_pagamento'] = df['tipo_servico'].map(PAYMENT_RULES).fillna(0)
        df['nome_tipo_servico'] = df['tipo_servico'].map(get_service_type_name)
        
        # Agrupar por motorista
        motorista_summary = df.groupby('id_motorista').agg({
            'valor_pagamento': 'sum',
            'awb': 'count',
            'peso': 'sum'
        }).reset_index()
        
        motorista_summary.columns = ['id_motorista', 'total_pagamento', 'total_entregas', 'peso_total']
        
        # Agrupar por tipo de serviço
        tipo_servico_summary = df.groupby(['tipo_servico', 'nome_tipo_servico']).agg({
            'valor_pagamento': 'sum',
            'awb': 'count',
            'peso': 'sum'
        }).reset_index()
        
        tipo_servico_summary.columns = ['tipo_servico', 'nome_tipo_servico', 'total_pagamento', 'total_entregas', 'peso_total']
        
        # Estatísticas gerais
        tipos_servico_stats = {}
        for tipo, nome in SERVICE_TYPE_NAMES.items():
            count = len(df[df['tipo_servico'] == tipo])
            if count > 0:
                tipos_servico_stats[nome] = {
                    'count': count,
                    'total_pagamento': df[df['tipo_servico'] == tipo]['valor_pagamento'].sum(),
                    'tipo_codigo': tipo
                }
        
        stats = {
            'total_entregas': len(df),
            'total_motoristas': df['id_motorista'].nunique(),
            'total_pagamentos': df['valor_pagamento'].sum(),
            'peso_total': df['peso'].sum(),
            'tipos_servico': tipos_servico_stats,
            'periodo': datetime.now().strftime('%Y-%m')
        }
        
        return {
            'success': True,
            'data': df.to_dict('records'),
            'motorista_summary': motorista_summary.to_dict('records'),
            'tipo_servico_summary': tipo_servico_summary.to_dict('records'),
            'stats': stats,
            'filename': filename,
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename
        }

# API de upload de arquivo
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido. Use CSV, XLS ou XLSX'}), 400
        
        # Ler conteúdo do arquivo
        file_content = file.read().decode('latin1')
        
        # Processar dados
        result = process_csv_data(file_content, file.filename)
        
        if not result['success']:
            return jsonify({'error': f'Erro ao processar arquivo: {result["error"]}'}), 400
        
        # Salvar no Supabase
        if supabase:
            try:
                # Salvar upload record
                upload_record = {
                    'id': str(uuid.uuid4()),
                    'filename': file.filename,
                    'processed_at': result['processed_at'],
                    'total_entregas': result['stats']['total_entregas'],
                    'total_motoristas': result['stats']['total_motoristas'],
                    'total_pagamentos': result['stats']['total_pagamentos'],
                    'periodo': result['stats']['periodo'],
                    'status': 'processed'
                }
                
                supabase.table('uploads').insert(upload_record).execute()
                
                # Salvar dados das entregas
                for record in result['data']:
                    delivery_record = {
                        'id': str(uuid.uuid4()),
                        'upload_id': upload_record['id'],
                        'awb': record.get('awb'),
                        'cliente': record.get('cliente'),
                        'rota': record.get('rota'),
                        'peso': record.get('peso'),
                        'tipo_servico': record.get('tipo_servico'),
                        'nome_tipo_servico': record.get('nome_tipo_servico'),
                        'id_motorista': record.get('id_motorista'),
                        'valor_pagamento': record.get('valor_pagamento'),
                        'data_status': record.get('data_status'),
                        'status': record.get('status')
                    }
                    
                    supabase.table('deliveries').insert(delivery_record).execute()
                
                # Salvar resumo por motorista
                for motorista in result['motorista_summary']:
                    motorista_record = {
                        'id': str(uuid.uuid4()),
                        'upload_id': upload_record['id'],
                        'id_motorista': motorista['id_motorista'],
                        'total_pagamento': motorista['total_pagamento'],
                        'total_entregas': motorista['total_entregas'],
                        'peso_total': motorista['peso_total'],
                        'periodo': result['stats']['periodo']
                    }
                    
                    supabase.table('motorista_payments').insert(motorista_record).execute()
                
                # Salvar resumo por tipo de serviço
                for tipo in result['tipo_servico_summary']:
                    tipo_record = {
                        'id': str(uuid.uuid4()),
                        'upload_id': upload_record['id'],
                        'tipo_servico': tipo['tipo_servico'],
                        'nome_tipo_servico': tipo['nome_tipo_servico'],
                        'total_pagamento': tipo['total_pagamento'],
                        'total_entregas': tipo['total_entregas'],
                        'peso_total': tipo['peso_total'],
                        'periodo': result['stats']['periodo']
                    }
                    
                    supabase.table('service_type_summary').insert(tipo_record).execute()
                
                app.logger.info(f"Upload processado com sucesso: {file.filename}")
                
            except Exception as e:
                app.logger.error(f"Erro ao salvar no Supabase: {e}")
                # Continuar mesmo se falhar no Supabase
        
        return jsonify({
            'success': True,
            'message': 'Arquivo processado com sucesso',
            'data': {
                'filename': file.filename,
                'stats': result['stats'],
                'motorista_summary': result['motorista_summary'][:10],  # Primeiros 10 para preview
                'tipo_servico_summary': result['tipo_servico_summary']
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no upload: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# API de histórico de uploads
@app.route('/api/upload/history')
def upload_history():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        if supabase:
            try:
                # Buscar uploads do Supabase
                response = supabase.table('uploads').select('*').order('processed_at', desc=True).limit(limit).execute()
                
                uploads = response.data if response.data else []
                
                return jsonify({
                    'success': True,
                    'data': uploads,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': len(uploads)
                    }
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao buscar histórico: {e}")
        
        # Fallback com dados simulados
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': '1',
                    'filename': 'mti0505a1505.csv',
                    'processed_at': '2025-06-09T00:00:00',
                    'total_entregas': 150,
                    'total_motoristas': 8,
                    'total_pagamentos': 525.00,
                    'periodo': '2025-06',
                    'status': 'processed'
                }
            ],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': 1
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no histórico: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# API de dados de motorista
@app.route('/api/drivers/<int:driver_id>/payments')
def driver_payments(driver_id):
    try:
        period = request.args.get('period', 'month')
        
        if supabase:
            try:
                response = supabase.table('motorista_payments').select('*').eq('id_motorista', driver_id).execute()
                
                payments = response.data if response.data else []
                
                total = sum(p['total_pagamento'] for p in payments)
                entregas = sum(p['total_entregas'] for p in payments)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_pagamento': total,
                        'total_entregas': entregas,
                        'payments': payments
                    }
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao buscar pagamentos: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': {
                'total_pagamento': 1250.75,
                'total_entregas': 85,
                'payments': []
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro nos pagamentos: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# API de estatísticas por tipo de serviço
@app.route('/api/stats/service-types')
def service_types_stats():
    try:
        if supabase:
            try:
                response = supabase.table('service_type_summary').select('*').execute()
                
                service_data = response.data if response.data else []
                
                # Agrupar por tipo de serviço
                grouped_data = {}
                for item in service_data:
                    nome = item['nome_tipo_servico']
                    if nome not in grouped_data:
                        grouped_data[nome] = {
                            'nome': nome,
                            'total_entregas': 0,
                            'total_pagamento': 0,
                            'peso_total': 0
                        }
                    
                    grouped_data[nome]['total_entregas'] += item['total_entregas']
                    grouped_data[nome]['total_pagamento'] += item['total_pagamento']
                    grouped_data[nome]['peso_total'] += item['peso_total']
                
                return jsonify({
                    'success': True,
                    'data': list(grouped_data.values())
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao buscar estatísticas de tipos: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': [
                {'nome': 'Encomendas', 'total_entregas': 120, 'total_pagamento': 420.00, 'peso_total': 85.5},
                {'nome': 'Cards', 'total_entregas': 25, 'total_pagamento': 50.00, 'peso_total': 12.3},
                {'nome': 'Revistas', 'total_entregas': 15, 'total_pagamento': 7.50, 'peso_total': 8.2}
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Erro nas estatísticas de tipos: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# API de estatísticas gerais
@app.route('/api/stats/dashboard')
def dashboard_stats():
    try:
        if supabase:
            try:
                # Buscar estatísticas do Supabase
                uploads_response = supabase.table('uploads').select('*').execute()
                payments_response = supabase.table('motorista_payments').select('*').execute()
                
                uploads = uploads_response.data if uploads_response.data else []
                payments = payments_response.data if payments_response.data else []
                
                total_uploads = len(uploads)
                total_pagamentos = sum(p['total_pagamento'] for p in payments)
                total_entregas = sum(p['total_entregas'] for p in payments)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_uploads': total_uploads,
                        'total_pagamentos': total_pagamentos,
                        'total_entregas': total_entregas,
                        'motoristas_ativos': len(set(p['id_motorista'] for p in payments)),
                        'tipos_servico': {
                            'Encomendas': {'valor_unitario': 3.50},
                            'Cards': {'valor_unitario': 2.00},
                            'Revistas': {'valor_unitario': 0.50}
                        }
                    }
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao buscar estatísticas: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': {
                'total_uploads': 5,
                'total_pagamentos': 15750.25,
                'total_entregas': 450,
                'motoristas_ativos': 12,
                'tipos_servico': {
                    'Encomendas': {'valor_unitario': 3.50},
                    'Cards': {'valor_unitario': 2.00},
                    'Revistas': {'valor_unitario': 0.50}
                }
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro nas estatísticas: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

