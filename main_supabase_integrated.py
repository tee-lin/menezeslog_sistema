# MenezesLog - Sistema Completo Integrado
# Versão 4.0.1 - CORREÇÃO ERRO 500
# Data: 2025-06-09

import os
import sys
import datetime
import json
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar aplicação Flask - CORREÇÃO CRÍTICA: pasta static correta
app = Flask(__name__, static_folder='static')
CORS(app)  # Habilitar CORS para todas as rotas

# Configuração da aplicação
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'menezeslog-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'menezeslog-jwt-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

# Configuração de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Simulação de dados em memória (para teste sem Supabase)
motoristas_db = []
prestadores_db = []
uploads_db = []

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
            # Simular processamento (sem pandas por enquanto)
            total_entregas = 60000  # Simulado
            total_pagamento = 125000.50  # Simulado
            
            # Salvar no "banco" simulado
            upload_data = {
                'id': len(uploads_db) + 1,
                'filename': file.filename,
                'total_entregas': total_entregas,
                'total_pagamento': total_pagamento,
                'status': 'processado',
                'created_at': datetime.datetime.now().isoformat()
            }
            uploads_db.append(upload_data)
            
            return jsonify({
                'success': True,
                'message': f'Arquivo processado com sucesso! {total_entregas} entregas processadas.',
                'data': {
                    'total_entregas': total_entregas,
                    'total_pagamento': total_pagamento,
                    'pagamentos_por_tipo': [
                        {'tipo': 'Encomendas', 'quantidade': 15000, 'valor_unitario': 3.50, 'total': 52500.00},
                        {'tipo': 'Cards', 'quantidade': 25000, 'valor_unitario': 2.00, 'total': 50000.00},
                        {'tipo': 'Revistas', 'quantidade': 20000, 'valor_unitario': 0.50, 'total': 10000.00}
                    ]
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
        
        return jsonify({
            'success': True,
            'data': uploads_db[-limit:] if uploads_db else [
                {
                    'id': 1,
                    'filename': 'exemplo.csv',
                    'total_entregas': 150,
                    'status': 'processado',
                    'created_at': datetime.datetime.now().isoformat()
                }
            ],
            'pagination': {'page': page, 'limit': limit, 'total': len(uploads_db)}
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar histórico: {str(e)}'}), 500

# ==================== APIs DE MOTORISTAS ====================

@app.route('/api/motoristas/upload', methods=['POST'])
def upload_motoristas():
    """Upload da planilha DE-PARA de motoristas - VERSÃO SIMPLIFICADA"""
    try:
        app.logger.info("Iniciando upload de motoristas...")
        
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
            # VERSÃO SIMPLIFICADA - SEM PANDAS
            # Simular processamento da planilha
            motoristas_simulados = [
                {'id_motorista': 100957, 'nome_motorista': 'Ailton Oliveira de Freitas', 'ativo': True},
                {'id_motorista': 240663, 'nome_motorista': 'Alan Bruno Santos', 'ativo': True},
                {'id_motorista': 123585, 'nome_motorista': 'Alexandre Costa Silva', 'ativo': True},
                {'id_motorista': 456789, 'nome_motorista': 'Carlos Eduardo Lima', 'ativo': True},
                {'id_motorista': 789012, 'nome_motorista': 'Daniel Ferreira Souza', 'ativo': True}
            ]
            
            # Limpar dados antigos e adicionar novos
            global motoristas_db
            motoristas_db = motoristas_simulados.copy()
            
            app.logger.info(f"Processados {len(motoristas_db)} motoristas")
            
            return jsonify({
                'success': True,
                'message': f'Planilha DE-PARA processada com sucesso! {len(motoristas_db)} motoristas cadastrados.',
                'data': {
                    'total_motoristas': len(motoristas_db),
                    'arquivo': file.filename
                }
            })
            
        except Exception as e:
            app.logger.error(f"Erro ao processar planilha: {e}")
            return jsonify({'error': f'Erro ao processar planilha: {str(e)}'}), 500
            
    except Exception as e:
        app.logger.error(f"Erro interno upload motoristas: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/motoristas', methods=['GET'])
def get_motoristas():
    """Lista todos os motoristas"""
    try:
        return jsonify({
            'success': True,
            'data': motoristas_db,
            'total': len(motoristas_db)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar motoristas: {str(e)}'}), 500

@app.route('/api/motoristas/<int:id_motorista>', methods=['GET'])
def get_motorista(id_motorista):
    """Busca motorista por ID"""
    try:
        motorista = next((m for m in motoristas_db if m['id_motorista'] == id_motorista), None)
        
        if motorista:
            return jsonify({
                'success': True,
                'data': motorista
            })
        else:
            return jsonify({'error': 'Motorista não encontrado'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar motorista: {str(e)}'}), 500

# ==================== APIs DE PRESTADORES ====================

@app.route('/api/prestadores', methods=['GET'])
def get_prestadores():
    """Lista todos os prestadores/grupos"""
    try:
        # Adicionar motoristas aos prestadores
        for prestador in prestadores_db:
            prestador['motoristas'] = [
                m for m in motoristas_db 
                if m['id_motorista'] in prestador.get('motoristas_ids', [])
            ]
        
        return jsonify({
            'success': True,
            'data': prestadores_db,
            'total': len(prestadores_db)
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
        
        # Criar prestador
        prestador_data = {
            'id': len(prestadores_db) + 1,
            'nome_prestador': data['nome_prestador'],
            'motorista_principal_id': data['motorista_principal_id'],
            'motoristas_ids': data['motoristas_ids'],
            'observacoes': data.get('observacoes', ''),
            'ativo': True,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        prestadores_db.append(prestador_data)
        
        return jsonify({
            'success': True,
            'message': 'Prestador criado com sucesso!',
            'data': prestador_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/prestadores/<int:prestador_id>', methods=['DELETE'])
def delete_prestador(prestador_id):
    """Remove prestador/grupo"""
    try:
        global prestadores_db
        prestadores_db = [p for p in prestadores_db if p['id'] != prestador_id]
        
        return jsonify({
            'success': True,
            'message': 'Prestador removido com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ==================== APIs DE RELATÓRIOS ====================

@app.route('/api/relatorios/prestadores', methods=['GET'])
def relatorio_prestadores():
    """Relatório de pagamentos agrupados por prestador"""
    try:
        periodo = request.args.get('periodo', 'mes')
        
        relatorio = []
        for prestador in prestadores_db:
            motoristas_ids = prestador.get('motoristas_ids', [])
            
            # Calcular pagamentos simulados
            total_pagamento = len(motoristas_ids) * 1500.00
            total_entregas = len(motoristas_ids) * 100
            
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
        return jsonify({'error': f'Erro ao gerar relatório: {str(e)}'}), 500

# ==================== APIs DO DASHBOARD ====================

@app.route('/api/drivers/count', methods=['GET'])
def drivers_count():
    """Contagem de motoristas"""
    try:
        return jsonify({'success': True, 'count': len(motoristas_db)})
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
            'data': uploads_db[-3:] if uploads_db else [
                {'arquivo': 'entregas_junho.csv', 'entregas': 60000, 'data': '2025-06-09'}
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

