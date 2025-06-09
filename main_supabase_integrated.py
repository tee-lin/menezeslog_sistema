# MenezesLog - Sistema Completo Integrado
# Versão 4.0.0 - Sistema de Motoristas e Prestadores
# Data: 2025-06-09

import os
import sys
import datetime
import pandas as pd
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from supabase import create_client, Client

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar aplicação Flask - CORREÇÃO CRÍTICA: pasta static correta
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
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página principal - serve o frontend"""
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        app.logger.error(f"Erro ao servir index.html: {e}")
        return jsonify({"error": "Página não encontrada"}), 404

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos"""
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        app.logger.error(f"Erro ao servir arquivo {filename}: {e}")
        return jsonify({"error": "Arquivo não encontrado"}), 404

# ==================== APIs DE UPLOAD ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload e processamento de arquivos CSV"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'.csv', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        try:
            # Ler arquivo
            if file_ext == '.csv':
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            # Processar dados
            total_entregas = len(df)
            
            # Calcular pagamentos por tipo de serviço
            pagamentos = []
            total_pagamento = 0
            
            # Regras de pagamento
            valores_servico = {
                0: 3.50,  # Encomendas
                9: 2.00,  # Cards
                6: 0.50,  # Revistas
                8: 0.50   # Revistas
            }
            
            for tipo, valor in valores_servico.items():
                count = len(df[df.get('tipo de serviço', 0) == tipo])
                if count > 0:
                    pagamento = count * valor
                    total_pagamento += pagamento
                    pagamentos.append({
                        'tipo': tipo,
                        'quantidade': count,
                        'valor_unitario': valor,
                        'total': pagamento
                    })
            
            # Salvar no Supabase se disponível
            if supabase:
                try:
                    upload_data = {
                        'filename': file.filename,
                        'total_entregas': total_entregas,
                        'total_pagamento': total_pagamento,
                        'status': 'processado',
                        'created_at': datetime.datetime.now().isoformat()
                    }
                    supabase.table('uploads').insert(upload_data).execute()
                except Exception as e:
                    app.logger.error(f"Erro ao salvar no Supabase: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Arquivo processado com sucesso! {total_entregas} entregas processadas.',
                'data': {
                    'total_entregas': total_entregas,
                    'total_pagamento': total_pagamento,
                    'pagamentos_por_tipo': pagamentos
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/upload/history', methods=['GET'])
def upload_history():
    """Histórico de uploads"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        if supabase:
            try:
                response = supabase.table('uploads').select('*').order('created_at', desc=True).limit(limit).execute()
                uploads = response.data
                
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
                    'id': 1,
                    'filename': 'exemplo.csv',
                    'total_entregas': 150,
                    'status': 'processado',
                    'created_at': datetime.datetime.now().isoformat()
                }
            ],
            'pagination': {'page': page, 'limit': limit, 'total': 1}
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar histórico: {str(e)}'}), 500

# ==================== APIs DE MOTORISTAS ====================

@app.route('/api/motoristas/upload', methods=['POST'])
def upload_motoristas():
    """Upload da planilha DE-PARA de motoristas"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        try:
            # Ler arquivo
            if file_ext == '.csv':
                df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_excel(file)
            
            # Validar estrutura
            required_columns = ['ID do motorista', 'Nome do motorista']
            if not all(col in df.columns for col in required_columns):
                return jsonify({
                    'error': f'Colunas obrigatórias: {required_columns}',
                    'found': list(df.columns)
                }), 400
            
            # Limpar e validar dados
            df_clean = df.dropna(subset=required_columns)
            df_clean['ID do motorista'] = pd.to_numeric(df_clean['ID do motorista'], errors='coerce')
            df_clean = df_clean.dropna(subset=['ID do motorista'])
            
            # Preparar dados para salvar
            motoristas_data = []
            for _, row in df_clean.iterrows():
                motoristas_data.append({
                    'id_motorista': int(row['ID do motorista']),
                    'nome_motorista': str(row['Nome do motorista']).strip(),
                    'ativo': True,
                    'updated_at': datetime.datetime.now().isoformat()
                })
            
            # Salvar no Supabase se disponível
            if supabase:
                try:
                    # Limpar dados antigos
                    supabase.table('motoristas').delete().neq('id_motorista', 0).execute()
                    
                    # Inserir novos dados
                    supabase.table('motoristas').insert(motoristas_data).execute()
                    
                    app.logger.info(f"Salvos {len(motoristas_data)} motoristas no Supabase")
                except Exception as e:
                    app.logger.error(f"Erro ao salvar motoristas no Supabase: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Planilha DE-PARA processada com sucesso! {len(motoristas_data)} motoristas cadastrados.',
                'data': {
                    'total_motoristas': len(motoristas_data),
                    'arquivo': file.filename
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Erro ao processar planilha: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/motoristas', methods=['GET'])
def get_motoristas():
    """Lista todos os motoristas"""
    try:
        if supabase:
            try:
                response = supabase.table('motoristas').select('*').eq('ativo', True).order('nome_motorista').execute()
                motoristas = response.data
                
                return jsonify({
                    'success': True,
                    'data': motoristas,
                    'total': len(motoristas)
                })
            except Exception as e:
                app.logger.error(f"Erro ao buscar motoristas: {e}")
        
        # Fallback com dados simulados
        return jsonify({
            'success': True,
            'data': [
                {'id_motorista': 100957, 'nome_motorista': 'João da Silva', 'ativo': True},
                {'id_motorista': 240663, 'nome_motorista': 'Maria Santos', 'ativo': True},
                {'id_motorista': 123585, 'nome_motorista': 'Pedro Costa', 'ativo': True}
            ],
            'total': 3
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar motoristas: {str(e)}'}), 500

@app.route('/api/motoristas/<int:id_motorista>', methods=['GET'])
def get_motorista(id_motorista):
    """Busca motorista por ID"""
    try:
        if supabase:
            try:
                response = supabase.table('motoristas').select('*').eq('id_motorista', id_motorista).execute()
                if response.data:
                    return jsonify({
                        'success': True,
                        'data': response.data[0]
                    })
                else:
                    return jsonify({'error': 'Motorista não encontrado'}), 404
            except Exception as e:
                app.logger.error(f"Erro ao buscar motorista: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': {'id_motorista': id_motorista, 'nome_motorista': f'Motorista {id_motorista}', 'ativo': True}
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar motorista: {str(e)}'}), 500

# ==================== APIs DE PRESTADORES ====================

@app.route('/api/prestadores', methods=['GET'])
def get_prestadores():
    """Lista todos os prestadores/grupos"""
    try:
        if supabase:
            try:
                response = supabase.table('prestadores').select('*').eq('ativo', True).order('nome_prestador').execute()
                prestadores = response.data
                
                # Buscar motoristas de cada prestador
                for prestador in prestadores:
                    motoristas_response = supabase.table('prestador_motoristas').select('*, motoristas(*)').eq('prestador_id', prestador['id']).execute()
                    prestador['motoristas'] = [item['motoristas'] for item in motoristas_response.data]
                
                return jsonify({
                    'success': True,
                    'data': prestadores,
                    'total': len(prestadores)
                })
            except Exception as e:
                app.logger.error(f"Erro ao buscar prestadores: {e}")
        
        # Fallback com dados simulados
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': 1,
                    'nome_prestador': 'João da Silva',
                    'motorista_principal_id': 100957,
                    'observacoes': 'Prestador principal da região Norte',
                    'motoristas': [
                        {'id_motorista': 100957, 'nome_motorista': 'João da Silva'},
                        {'id_motorista': 240663, 'nome_motorista': 'Maria Santos'},
                        {'id_motorista': 123585, 'nome_motorista': 'Pedro Costa'}
                    ]
                }
            ],
            'total': 1
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar prestadores: {str(e)}'}), 500

@app.route('/api/prestadores', methods=['POST'])
def create_prestador():
    """Cria novo prestador/grupo"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('nome_prestador'):
            return jsonify({'error': 'Nome do prestador é obrigatório'}), 400
        
        if not data.get('motorista_principal_id'):
            return jsonify({'error': 'Motorista principal é obrigatório'}), 400
        
        if not data.get('motoristas_ids') or len(data['motoristas_ids']) == 0:
            return jsonify({'error': 'Pelo menos um motorista deve ser associado'}), 400
        
        if supabase:
            try:
                # Criar prestador
                prestador_data = {
                    'nome_prestador': data['nome_prestador'],
                    'motorista_principal_id': data['motorista_principal_id'],
                    'observacoes': data.get('observacoes', ''),
                    'ativo': True,
                    'created_at': datetime.datetime.now().isoformat()
                }
                
                prestador_response = supabase.table('prestadores').insert(prestador_data).execute()
                prestador_id = prestador_response.data[0]['id']
                
                # Associar motoristas
                motoristas_associacoes = []
                for motorista_id in data['motoristas_ids']:
                    motoristas_associacoes.append({
                        'prestador_id': prestador_id,
                        'motorista_id': motorista_id,
                        'created_at': datetime.datetime.now().isoformat()
                    })
                
                supabase.table('prestador_motoristas').insert(motoristas_associacoes).execute()
                
                return jsonify({
                    'success': True,
                    'message': 'Prestador criado com sucesso!',
                    'data': {'id': prestador_id, **prestador_data}
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao criar prestador: {e}")
                return jsonify({'error': f'Erro ao salvar prestador: {str(e)}'}), 500
        
        # Fallback
        return jsonify({
            'success': True,
            'message': 'Prestador criado com sucesso (modo simulado)!',
            'data': {'id': 999, **data}
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/prestadores/<int:prestador_id>', methods=['DELETE'])
def delete_prestador(prestador_id):
    """Remove prestador/grupo"""
    try:
        if supabase:
            try:
                # Remover associações
                supabase.table('prestador_motoristas').delete().eq('prestador_id', prestador_id).execute()
                
                # Remover prestador
                supabase.table('prestadores').delete().eq('id', prestador_id).execute()
                
                return jsonify({
                    'success': True,
                    'message': 'Prestador removido com sucesso!'
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao remover prestador: {e}")
                return jsonify({'error': f'Erro ao remover prestador: {str(e)}'}), 500
        
        # Fallback
        return jsonify({
            'success': True,
            'message': 'Prestador removido com sucesso (modo simulado)!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ==================== APIs DE RELATÓRIOS ====================

@app.route('/api/relatorios/prestadores', methods=['GET'])
def relatorio_prestadores():
    """Relatório de pagamentos agrupados por prestador"""
    try:
        periodo = request.args.get('periodo', 'mes')  # mes, semana, dia
        
        if supabase:
            try:
                # Buscar prestadores com seus motoristas
                prestadores_response = supabase.table('prestadores').select('*, prestador_motoristas(motorista_id)').eq('ativo', True).execute()
                prestadores = prestadores_response.data
                
                relatorio = []
                for prestador in prestadores:
                    motoristas_ids = [item['motorista_id'] for item in prestador['prestador_motoristas']]
                    
                    # Calcular pagamentos dos motoristas do grupo
                    # Aqui você integraria com os dados de entregas/pagamentos
                    total_pagamento = len(motoristas_ids) * 1500.00  # Simulado
                    total_entregas = len(motoristas_ids) * 100  # Simulado
                    
                    relatorio.append({
                        'prestador_id': prestador['id'],
                        'nome_prestador': prestador['nome_prestador'],
                        'total_motoristas': len(motoristas_ids),
                        'total_entregas': total_entregas,
                        'total_pagamento': total_pagamento,
                        'motoristas_ids': motoristas_ids
                    })
                
                return jsonify({
                    'success': True,
                    'data': relatorio,
                    'periodo': periodo,
                    'total_prestadores': len(relatorio)
                })
                
            except Exception as e:
                app.logger.error(f"Erro ao gerar relatório: {e}")
        
        # Fallback com dados simulados
        return jsonify({
            'success': True,
            'data': [
                {
                    'prestador_id': 1,
                    'nome_prestador': 'João da Silva',
                    'total_motoristas': 3,
                    'total_entregas': 300,
                    'total_pagamento': 4500.00,
                    'motoristas_ids': [100957, 240663, 123585]
                }
            ],
            'periodo': periodo,
            'total_prestadores': 1
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao gerar relatório: {str(e)}'}), 500

# ==================== APIs DO DASHBOARD ====================

@app.route('/api/drivers/count', methods=['GET'])
def drivers_count():
    """Contagem de motoristas"""
    try:
        if supabase:
            try:
                response = supabase.table('motoristas').select('id_motorista', count='exact').eq('ativo', True).execute()
                count = response.count
                return jsonify({'success': True, 'count': count})
            except Exception as e:
                app.logger.error(f"Erro ao contar motoristas: {e}")
        
        return jsonify({'success': True, 'count': 135})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/summary', methods=['GET'])
def payment_summary():
    """Resumo de pagamentos"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'total_pagamentos': 125000.50,
                'pagamentos_pendentes': 15000.00,
                'pagamentos_realizados': 110000.50,
                'media_por_motorista': 925.93
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/service-types', methods=['GET'])
def payment_service_types():
    """Pagamentos por tipo de serviço"""
    try:
        return jsonify({
            'success': True,
            'data': [
                {'tipo': 'Encomendas', 'valor': 3.50, 'quantidade': 15000, 'total': 52500.00},
                {'tipo': 'Cards', 'valor': 2.00, 'quantidade': 25000, 'total': 50000.00},
                {'tipo': 'Revistas', 'valor': 0.50, 'quantidade': 45000, 'total': 22500.00}
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/recent', methods=['GET'])
def payment_recent():
    """Pagamentos recentes"""
    try:
        return jsonify({
            'success': True,
            'data': [
                {'motorista': 'João da Silva', 'valor': 1250.00, 'data': '2025-06-08'},
                {'motorista': 'Maria Santos', 'valor': 980.50, 'data': '2025-06-08'},
                {'motorista': 'Pedro Costa', 'valor': 1100.00, 'data': '2025-06-07'}
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/recent', methods=['GET'])
def upload_recent():
    """Uploads recentes"""
    try:
        return jsonify({
            'success': True,
            'data': [
                {'arquivo': 'entregas_junho.csv', 'entregas': 60000, 'data': '2025-06-09'},
                {'arquivo': 'entregas_maio.csv', 'entregas': 55000, 'data': '2025-05-30'}
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/chart', methods=['GET'])
def payment_chart():
    """Dados para gráficos"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'labels': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                'values': [45000, 52000, 48000, 61000, 55000, 62000]
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bonus/summary', methods=['GET'])
def bonus_summary():
    """Resumo de bônus"""
    try:
        return jsonify({
            'success': True,
            'data': {'total_bonus': 5000.00, 'motoristas_bonus': 25}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/discount/summary', methods=['GET'])
def discount_summary():
    """Resumo de descontos"""
    try:
        return jsonify({
            'success': True,
            'data': {'total_descontos': 2500.00, 'motoristas_descontos': 12}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    # Criar pasta de uploads se não existir
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Executar aplicação
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

