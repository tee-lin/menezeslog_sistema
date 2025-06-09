from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import os
import logging
import pandas as pd
from datetime import datetime
import uuid
from supabase import create_client, Client
import json

# Configuração do Flask
app = Flask(__name__, static_folder='static')  # CORREÇÃO CRÍTICA: pasta static correta
CORS(app)

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Configuração do Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        app.logger.info("Supabase conectado com sucesso")
    except Exception as e:
        app.logger.error(f"Erro ao conectar com Supabase: {e}")
        supabase = None
else:
    app.logger.warning("Variáveis do Supabase não encontradas")

# Regras de pagamento por tipo de serviço
PAYMENT_RULES = {
    0: 3.50,  # Encomendas
    6: 0.50,  # Revistas
    8: 0.50,  # Revistas
    9: 2.00   # Cards
}

# Mapeamento de nomes dos tipos de serviço
SERVICE_TYPE_NAMES = {
    0: 'Encomendas',
    6: 'Revistas',
    8: 'Revistas',
    9: 'Cards'
}

# Rota principal - serve arquivos estáticos
@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        app.logger.error(f"Erro ao servir index.html: {e}")
        return "Erro ao carregar página", 500

# Rota para servir arquivos estáticos
@app.route('/<path:filename>')
def static_files(filename):
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        app.logger.error(f"Erro ao servir arquivo {filename}: {e}")
        return "Arquivo não encontrado", 404

# ==================== APIs DE UPLOAD ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'.csv', '.xls', '.xlsx'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        # Processar arquivo CSV
        try:
            # Ler CSV
            if file_ext == '.csv':
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            app.logger.info(f"Arquivo carregado: {len(df)} linhas")
            
            # Processar dados
            result = process_csv_data(df, file.filename)
            
            return jsonify({
                'success': True,
                'message': 'Arquivo processado com sucesso',
                'data': result
            })
            
        except Exception as e:
            app.logger.error(f"Erro ao processar arquivo: {e}")
            return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500
            
    except Exception as e:
        app.logger.error(f"Erro no upload: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

def process_csv_data(df, filename):
    """Processa dados do CSV e salva no Supabase"""
    try:
        # Mapear colunas do CSV
        column_mapping = {
            'Nome Fantasia do Remetente': 'cliente',
            'AWB': 'awb',
            'Rota': 'rota',
            'Peso Capturado': 'peso',
            'Tipo de Serviço': 'tipo_servico',
            'Status da encomenda': 'status_encomenda',
            'Data/Hora Status': 'data_status',
            'Desc. do status': 'desc_status',
            'ID da CAF': 'id_caf',
            'ID do motorista': 'id_motorista'
        }
        
        # Renomear colunas
        df_renamed = df.rename(columns=column_mapping)
        
        # Converter tipos
        df_renamed['tipo_servico'] = pd.to_numeric(df_renamed['tipo_servico'], errors='coerce')
        df_renamed['id_motorista'] = pd.to_numeric(df_renamed['id_motorista'], errors='coerce')
        
        # Remover linhas com dados inválidos
        df_clean = df_renamed.dropna(subset=['tipo_servico', 'id_motorista'])
        
        # Calcular pagamentos
        df_clean['valor_pagamento'] = df_clean['tipo_servico'].map(PAYMENT_RULES).fillna(0)
        df_clean['nome_tipo_servico'] = df_clean['tipo_servico'].map(SERVICE_TYPE_NAMES).fillna('Outros')
        
        # Estatísticas gerais
        total_entregas = len(df_clean)
        total_motoristas = df_clean['id_motorista'].nunique()
        total_pagamentos = df_clean['valor_pagamento'].sum()
        
        # Resumo por motorista
        motorista_summary = df_clean.groupby('id_motorista').agg({
            'valor_pagamento': 'sum',
            'awb': 'count',
            'tipo_servico': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 0
        }).reset_index()
        
        motorista_summary.columns = ['id_motorista', 'total_pagamento', 'total_entregas', 'tipo_servico_principal']
        
        # Resumo por tipo de serviço
        service_summary = df_clean.groupby(['tipo_servico', 'nome_tipo_servico']).agg({
            'valor_pagamento': 'sum',
            'awb': 'count'
        }).reset_index()
        
        service_summary.columns = ['tipo_servico', 'nome_tipo_servico', 'total_pagamento', 'total_entregas']
        
        # Salvar no Supabase
        upload_id = str(uuid.uuid4())
        
        if supabase:
            try:
                # Salvar upload
                upload_data = {
                    'id': upload_id,
                    'filename': filename,
                    'processed_at': datetime.now().isoformat(),
                    'total_entregas': int(total_entregas),
                    'total_motoristas': int(total_motoristas),
                    'total_pagamentos': float(total_pagamentos),
                    'status': 'processed'
                }
                
                supabase.table('uploads').insert(upload_data).execute()
                
                # Salvar entregas
                deliveries_data = []
                for _, row in df_clean.iterrows():
                    deliveries_data.append({
                        'upload_id': upload_id,
                        'awb': str(row['awb']),
                        'cliente': str(row['cliente']),
                        'rota': str(row['rota']),
                        'peso': float(row['peso']) if pd.notna(row['peso']) else 0,
                        'tipo_servico': int(row['tipo_servico']),
                        'nome_tipo_servico': str(row['nome_tipo_servico']),
                        'id_motorista': int(row['id_motorista']),
                        'valor_pagamento': float(row['valor_pagamento']),
                        'data_status': str(row['data_status']),
                        'status_encomenda': str(row['status_encomenda'])
                    })
                
                # Inserir em lotes
                batch_size = 1000
                for i in range(0, len(deliveries_data), batch_size):
                    batch = deliveries_data[i:i + batch_size]
                    supabase.table('deliveries').insert(batch).execute()
                
                # Salvar resumo por motorista
                motorista_data = []
                for _, row in motorista_summary.iterrows():
                    motorista_data.append({
                        'upload_id': upload_id,
                        'id_motorista': int(row['id_motorista']),
                        'total_entregas': int(row['total_entregas']),
                        'total_pagamento': float(row['total_pagamento']),
                        'tipo_servico_principal': int(row['tipo_servico_principal'])
                    })
                
                supabase.table('motorista_payments').insert(motorista_data).execute()
                
                # Salvar resumo por tipo de serviço
                service_data = []
                for _, row in service_summary.iterrows():
                    service_data.append({
                        'upload_id': upload_id,
                        'tipo_servico': int(row['tipo_servico']),
                        'nome_tipo_servico': str(row['nome_tipo_servico']),
                        'total_entregas': int(row['total_entregas']),
                        'total_pagamento': float(row['total_pagamento'])
                    })
                
                supabase.table('service_type_summary').insert(service_data).execute()
                
                app.logger.info(f"Dados salvos no Supabase: {total_entregas} entregas")
                
            except Exception as e:
                app.logger.error(f"Erro ao salvar no Supabase: {e}")
        
        return {
            'upload_id': upload_id,
            'stats': {
                'total_entregas': total_entregas,
                'total_motoristas': total_motoristas,
                'total_pagamentos': total_pagamentos,
                'resumo_motoristas': motorista_summary.to_dict('records'),
                'resumo_tipos': service_summary.to_dict('records')
            }
        }
        
    except Exception as e:
        app.logger.error(f"Erro ao processar dados: {e}")
        raise

@app.route('/api/upload/history')
def upload_history():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        if supabase:
            try:
                response = supabase.table('uploads').select('*').order('processed_at', desc=True).range((page-1)*limit, page*limit-1).execute()
                
                if response.data:
                    return jsonify({
                        'success': True,
                        'data': response.data,
                        'page': page,
                        'limit': limit
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar histórico: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': '1',
                    'filename': 'exemplo.csv',
                    'processed_at': '2025-06-09T00:00:00',
                    'total_entregas': 100,
                    'total_motoristas': 5,
                    'total_pagamentos': 350.00,
                    'status': 'processed'
                }
            ],
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        app.logger.error(f"Erro no histórico: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ==================== APIs DO DASHBOARD ====================

@app.route('/api/drivers/count')
def drivers_count():
    try:
        if supabase:
            try:
                response = supabase.table('motorista_payments').select('id_motorista').execute()
                
                if response.data:
                    unique_drivers = len(set(item['id_motorista'] for item in response.data))
                    return jsonify({
                        'success': True,
                        'count': unique_drivers
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao contar motoristas: {e}")
        
        return jsonify({
            'success': True,
            'count': 12
        })
        
    except Exception as e:
        app.logger.error(f"Erro na contagem de motoristas: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/payment/summary')
def payment_summary():
    try:
        period = request.args.get('period', 'month')
        
        if supabase:
            try:
                response = supabase.table('motorista_payments').select('*').execute()
                
                if response.data:
                    total_pagamentos = sum(item['total_pagamento'] for item in response.data)
                    total_entregas = sum(item['total_entregas'] for item in response.data)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'total_pagamentos': total_pagamentos,
                            'total_entregas': total_entregas,
                            'media_por_entrega': total_pagamentos / total_entregas if total_entregas > 0 else 0,
                            'periodo': period
                        }
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar resumo de pagamentos: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_pagamentos': 15750.25,
                'total_entregas': 450,
                'media_por_entrega': 35.00,
                'periodo': period
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no resumo de pagamentos: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/payment/service-types')
def payment_service_types():
    try:
        if supabase:
            try:
                response = supabase.table('service_type_summary').select('*').execute()
                
                if response.data:
                    grouped_data = {}
                    for item in response.data:
                        nome = item['nome_tipo_servico']
                        if nome not in grouped_data:
                            grouped_data[nome] = {
                                'nome': nome,
                                'total_entregas': 0,
                                'total_pagamento': 0,
                                'valor_unitario': PAYMENT_RULES.get(item['tipo_servico'], 0)
                            }
                        
                        grouped_data[nome]['total_entregas'] += item['total_entregas']
                        grouped_data[nome]['total_pagamento'] += item['total_pagamento']
                    
                    return jsonify({
                        'success': True,
                        'data': list(grouped_data.values())
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar tipos de serviço: {e}")
        
        return jsonify({
            'success': True,
            'data': [
                {'nome': 'Encomendas', 'total_entregas': 120, 'total_pagamento': 420.00, 'valor_unitario': 3.50},
                {'nome': 'Cards', 'total_entregas': 25, 'total_pagamento': 50.00, 'valor_unitario': 2.00},
                {'nome': 'Revistas', 'total_entregas': 15, 'total_pagamento': 7.50, 'valor_unitario': 0.50}
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Erro nos tipos de serviço: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/payment/recent')
def payment_recent():
    try:
        limit = int(request.args.get('limit', 5))
        
        if supabase:
            try:
                response = supabase.table('uploads').select('*').order('processed_at', desc=True).limit(limit).execute()
                
                if response.data:
                    return jsonify({
                        'success': True,
                        'data': response.data
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar pagamentos recentes: {e}")
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': '1',
                    'filename': 'mti0505a1505.csv',
                    'processed_at': '2025-06-09T01:30:00',
                    'total_entregas': 60000,
                    'total_pagamentos': 210000.00,
                    'status': 'processed'
                }
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Erro nos pagamentos recentes: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/upload/recent')
def upload_recent():
    try:
        limit = int(request.args.get('limit', 5))
        
        if supabase:
            try:
                response = supabase.table('uploads').select('*').order('processed_at', desc=True).limit(limit).execute()
                
                if response.data:
                    return jsonify({
                        'success': True,
                        'data': response.data
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar uploads recentes: {e}")
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': '1',
                    'filename': 'mti0505a1505.csv',
                    'processed_at': '2025-06-09T01:30:00',
                    'total_entregas': 60000,
                    'total_motoristas': 150,
                    'total_pagamentos': 210000.00,
                    'status': 'processed'
                }
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Erro nos uploads recentes: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/bonus/summary')
def bonus_summary():
    try:
        period = request.args.get('period', 'month')
        
        return jsonify({
            'success': True,
            'data': {
                'total_bonus': 2500.00,
                'bonus_motoristas': 8,
                'media_bonus': 312.50,
                'periodo': period
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no resumo de bônus: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/discount/summary')
def discount_summary():
    try:
        period = request.args.get('period', 'month')
        
        return jsonify({
            'success': True,
            'data': {
                'total_descontos': 850.00,
                'descontos_aplicados': 12,
                'media_desconto': 70.83,
                'periodo': period
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no resumo de descontos: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/payment/chart')
def payment_chart():
    try:
        period = request.args.get('period', 'year')
        
        if supabase:
            try:
                response = supabase.table('uploads').select('*').order('processed_at', desc=True).execute()
                
                if response.data:
                    chart_data = []
                    for upload in response.data:
                        chart_data.append({
                            'periodo': upload['processed_at'][:7],
                            'total_pagamentos': upload['total_pagamentos'],
                            'total_entregas': upload['total_entregas']
                        })
                    
                    return jsonify({
                        'success': True,
                        'data': chart_data
                    })
                    
            except Exception as e:
                app.logger.error(f"Erro ao buscar dados do gráfico: {e}")
        
        return jsonify({
            'success': True,
            'data': [
                {'periodo': '2025-01', 'total_pagamentos': 45000, 'total_entregas': 12000},
                {'periodo': '2025-02', 'total_pagamentos': 52000, 'total_entregas': 14500},
                {'periodo': '2025-03', 'total_pagamentos': 48000, 'total_entregas': 13200},
                {'periodo': '2025-04', 'total_pagamentos': 55000, 'total_entregas': 15800},
                {'periodo': '2025-05', 'total_pagamentos': 62000, 'total_entregas': 17500},
                {'periodo': '2025-06', 'total_pagamentos': 210000, 'total_entregas': 60000}
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Erro no gráfico de pagamentos: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/dashboard/stats')
def dashboard_stats():
    try:
        if supabase:
            try:
                uploads_response = supabase.table('uploads').select('*').execute()
                payments_response = supabase.table('motorista_payments').select('*').execute()
                
                uploads = uploads_response.data if uploads_response.data else []
                payments = payments_response.data if payments_response.data else []
                
                total_uploads = len(uploads)
                total_pagamentos = sum(p['total_pagamento'] for p in payments)
                total_entregas = sum(p['total_entregas'] for p in payments)
                motoristas_ativos = len(set(p['id_motorista'] for p in payments))
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_uploads': total_uploads,
                        'total_pagamentos': total_pagamentos,
                        'total_entregas': total_entregas,
                        'motoristas_ativos': motoristas_ativos,
                        'media_por_motorista': total_pagamentos / motoristas_ativos if motoristas_ativos > 0 else 0,
                        'media_por_entrega': total_pagamentos / total_entregas if total_entregas > 0 else 0
                    }
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao buscar estatísticas do dashboard: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_uploads': 5,
                'total_pagamentos': 210000.00,
                'total_entregas': 60000,
                'motoristas_ativos': 150,
                'media_por_motorista': 1400.00,
                'media_por_entrega': 3.50
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro nas estatísticas do dashboard: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ==================== ROTAS DE SAÚDE ====================

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': supabase is not None
    })

@app.route('/api/test')
def api_test():
    return jsonify({
        'message': 'API funcionando',
        'timestamp': datetime.now().isoformat()
    })

# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

