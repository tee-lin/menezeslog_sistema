# MenezesLog SaaS v7.6 DEFINITIVO - TIMEOUT CONFIGURADO + PROCESSAMENTO ASSÍNCRONO
# Sistema completo com Supabase, timeout estendido e background tasks

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import pandas as pd
import chardet
import csv
from datetime import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging
from werkzeug.utils import secure_filename

# Configurar logging
logging.basicConfig(level=logging.WARNING)

# Configuração do Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
    print("✅ Biblioteca supabase-py disponível")
except ImportError:
    SUPABASE_AVAILABLE = False
    print("❌ Biblioteca supabase-py não encontrada")

app = Flask(__name__, static_folder='static')
CORS(app)

# Configurações
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Criar pastas necessárias
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# Configuração do Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

supabase = None
if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Conexão com Supabase estabelecida")
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")

# Cache global para performance
cache_motoristas = {}
cache_tarifas = {}
cache_timestamp = 0
CACHE_DURATION = 600  # 10 minutos

# Tarifas padrão do sistema
TARIFAS_PADRAO = {
    0: 3.50,  # Encomendas
    9: 2.00,  # Cards
    6: 0.50,  # Revistas
    8: 0.50   # Revistas
}

# Status de processamento global
processing_status = {
    'active': False,
    'progress': 0,
    'message': '',
    'total_lines': 0,
    'processed_lines': 0,
    'errors': 0,
    'start_time': None,
    'estimated_time': None
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detectar_encoding(file_path):
    """Detecta o encoding do arquivo"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            
        # Fallbacks para encodings brasileiros
        encodings_to_try = [encoding, 'iso-8859-1', 'windows-1252', 'latin-1', 'utf-8']
        
        for enc in encodings_to_try:
            if enc:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        f.read(1000)
                    return enc
                except:
                    continue
        
        return 'utf-8'
    except:
        return 'utf-8'

def detectar_delimitador_csv(file_path, encoding):
    """Detecta o delimitador do CSV"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            primeira_linha = f.readline()
            
        delimitadores = {
            ';': primeira_linha.count(';'),
            ',': primeira_linha.count(','),
            '\t': primeira_linha.count('\t'),
            '|': primeira_linha.count('|')
        }
        
        delimitador = max(delimitadores, key=delimitadores.get)
        return delimitador if delimitadores[delimitador] > 0 else ','
    except:
        return ';'

def carregar_dados_supabase():
    """Carrega dados do Supabase com cache inteligente"""
    global cache_motoristas, cache_tarifas, cache_timestamp
    
    current_time = time.time()
    if current_time - cache_timestamp < CACHE_DURATION and cache_motoristas:
        return cache_motoristas, cache_tarifas
    
    motoristas = {}
    tarifas = {}
    
    if supabase:
        try:
            # Carregar motoristas
            response = supabase.table('motoristas').select('*').execute()
            if response.data:
                for motorista in response.data:
                    motoristas[motorista['id_motorista']] = motorista['nome_motorista']
            
            # Carregar tarifas (usar padrão se não existir)
            for id_motorista in motoristas.keys():
                tarifas[id_motorista] = TARIFAS_PADRAO.copy()
            
            cache_motoristas = motoristas
            cache_tarifas = tarifas
            cache_timestamp = current_time
            
            print(f"✅ Dados carregados do Supabase: {len(motoristas)} motoristas")
            
        except Exception as e:
            print(f"❌ Erro ao carregar dados do Supabase: {e}")
    
    return motoristas, tarifas

def calcular_valor_entrega_otimizado(tipo_servico, id_motorista, tarifas_cache):
    """Versão otimizada do cálculo de valor"""
    try:
        tipo_servico = int(tipo_servico)
        id_motorista = int(id_motorista)
        
        # Buscar tarifa específica do motorista
        if id_motorista in tarifas_cache:
            return tarifas_cache[id_motorista].get(tipo_servico, TARIFAS_PADRAO.get(tipo_servico, 0))
        
        # Usar tarifa padrão
        return TARIFAS_PADRAO.get(tipo_servico, 0)
    except:
        return 0

def salvar_lote_supabase(awbs_lote, chunk_id):
    """Salva lote de AWBs no Supabase"""
    if not supabase or not awbs_lote:
        return 0
    
    try:
        # Preparar dados para upsert
        dados_para_salvar = []
        for awb in awbs_lote:
            dados_para_salvar.append({
                'empresa_id': 1,
                'awb': awb['awb'],
                'id_motorista': awb['id_motorista'],
                'nome_motorista': awb['nome_motorista'],
                'tipo_servico': awb['tipo_servico'],
                'data_entrega': awb.get('data_entrega', ''),
                'valor_entrega': float(awb['valor_entrega']),
                'status': 'NAO_PAGA'
            })
        
        # Salvar em lotes de 1000
        total_salvos = 0
        for i in range(0, len(dados_para_salvar), 1000):
            lote = dados_para_salvar[i:i+1000]
            
            response = supabase.table('awbs').upsert(lote).execute()
            if response.data:
                total_salvos += len(lote)
                print(f"💾 Lote Supabase: {min(i+1000, len(dados_para_salvar))}/{len(dados_para_salvar)} AWBs salvas")
        
        return total_salvos
    except Exception as e:
        print(f"❌ Erro ao salvar lote no Supabase: {e}")
        return 0

def processar_chunk_assincronamente(chunk_data, chunk_id, motoristas_cache, tarifas_cache):
    """Processa um chunk de dados de forma assíncrona"""
    awbs_processadas = []
    erros = 0
    
    for _, row in chunk_data.iterrows():
        try:
            # Extrair dados da linha
            awb = str(row.get('AWB', '')).strip()
            id_motorista = int(row.get('ID do motorista', 0))
            tipo_servico = int(row.get('Tipo de Serviço', 0))
            data_entrega = str(row.get('Data/Hora Status do último status', ''))
            
            # Verificar se motorista existe
            if id_motorista not in motoristas_cache:
                erros += 1
                continue
            
            # Calcular valor
            valor_entrega = calcular_valor_entrega_otimizado(tipo_servico, id_motorista, tarifas_cache)
            
            # Criar AWB
            awb_data = {
                'awb': awb,
                'id_motorista': id_motorista,
                'nome_motorista': motoristas_cache[id_motorista],
                'tipo_servico': tipo_servico,
                'data_entrega': data_entrega,
                'valor_entrega': valor_entrega
            }
            
            awbs_processadas.append(awb_data)
            
        except Exception as e:
            erros += 1
            continue
    
    # Salvar no Supabase
    salvos = salvar_lote_supabase(awbs_processadas, chunk_id)
    
    return len(awbs_processadas), erros, salvos

def processar_csv_assincronamente(file_path):
    """Processa CSV de forma assíncrona com feedback em tempo real"""
    global processing_status
    
    try:
        processing_status.update({
            'active': True,
            'progress': 0,
            'message': 'Iniciando processamento...',
            'start_time': time.time()
        })
        
        # Detectar encoding e delimitador
        encoding = detectar_encoding(file_path)
        delimitador = detectar_delimitador_csv(file_path, encoding)
        
        processing_status['message'] = f'Encoding: {encoding}, Delimitador: {delimitador}'
        
        # Carregar dados
        motoristas_cache, tarifas_cache = carregar_dados_supabase()
        
        processing_status['message'] = f'Carregados: {len(motoristas_cache)} motoristas'
        
        # Ler CSV
        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimitador)
        total_linhas = len(df)
        
        processing_status.update({
            'total_lines': total_linhas,
            'message': f'CSV carregado: {total_linhas} linhas'
        })
        
        # Dividir em chunks para processamento paralelo
        chunk_size = 5000
        chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
        
        processing_status['message'] = f'Processando {len(chunks)} chunks com 3 threads'
        
        # Processar chunks em paralelo
        total_processadas = 0
        total_erros = 0
        total_salvos = 0
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for i, chunk in enumerate(chunks):
                future = executor.submit(
                    processar_chunk_assincronamente, 
                    chunk, i+1, motoristas_cache, tarifas_cache
                )
                futures.append(future)
            
            # Coletar resultados
            for i, future in enumerate(futures):
                try:
                    processadas, erros, salvos = future.result(timeout=300)  # 5 minutos por chunk
                    total_processadas += processadas
                    total_erros += erros
                    total_salvos += salvos
                    
                    # Atualizar progresso
                    progress = ((i + 1) / len(chunks)) * 100
                    processing_status.update({
                        'progress': progress,
                        'processed_lines': total_processadas,
                        'errors': total_erros,
                        'message': f'Chunk {i+1}/{len(chunks)} concluído'
                    })
                    
                except Exception as e:
                    print(f"❌ Erro no chunk {i+1}: {e}")
                    total_erros += len(chunks[i])
        
        # Finalizar
        tempo_total = time.time() - processing_status['start_time']
        performance = total_processadas / tempo_total if tempo_total > 0 else 0
        
        processing_status.update({
            'active': False,
            'progress': 100,
            'message': 'Processamento concluído!',
            'performance_linhas_por_segundo': round(performance, 2)
        })
        
        return {
            'success': True,
            'data': {
                'entregas_processadas': total_processadas,
                'entregas_erro': total_erros,
                'awbs_salvas_supabase': total_salvos,
                'tempo_processamento': round(tempo_total, 2),
                'performance_linhas_por_segundo': round(performance, 2)
            },
            'message': f'Processamento concluído! {total_processadas} entregas processadas, {total_salvos} salvas no Supabase.'
        }
        
    except Exception as e:
        processing_status.update({
            'active': False,
            'message': f'Erro: {str(e)}'
        })
        return {
            'success': False,
            'error': str(e)
        }

# ROTAS DA API

@app.route('/')
def index():
    return send_from_directory('static', 'admin_dashboard.html')

@app.route('/admin_dashboard.html')
def admin_dashboard():
    return send_from_directory('static', 'admin_dashboard.html')

@app.route('/prestadores.html')
def prestadores():
    return send_from_directory('static', 'prestadores.html')

@app.route('/upload.html')
def upload():
    return send_from_directory('static', 'upload.html')

@app.route('/tarifas.html')
def tarifas():
    return send_from_directory('static', 'tarifas.html')

@app.route('/ciclos.html')
def ciclos():
    return send_from_directory('static', 'ciclos.html')

@app.route('/awbs.html')
def awbs():
    return send_from_directory('static', 'awbs.html')

@app.route('/api/status')
def api_status():
    """Status do sistema"""
    return jsonify({
        'success': True,
        'data': {
            'supabase_connected': supabase is not None,
            'supabase_url': SUPABASE_URL is not None,
            'version': 'v7.6 DEFINITIVO',
            'processing_active': processing_status['active']
        }
    })

@app.route('/api/estatisticas')
def api_estatisticas():
    """Estatísticas gerais do sistema"""
    try:
        motoristas, _ = carregar_dados_supabase()
        
        # Contar AWBs no Supabase
        total_awbs = 0
        if supabase:
            try:
                response = supabase.table('awbs').select('id', count='exact').execute()
                total_awbs = response.count if response.count else 0
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'total_motoristas': len(motoristas),
                'total_prestadores': 0,  # Implementar quando tiver grupos
                'total_awbs': total_awbs,
                'supabase_connected': supabase is not None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/motoristas')
def api_motoristas():
    """Lista todos os motoristas"""
    try:
        motoristas, _ = carregar_dados_supabase()
        
        motoristas_list = []
        for id_motorista, nome in motoristas.items():
            motoristas_list.append({
                'id_motorista': id_motorista,
                'nome_motorista': nome,
                'created_at': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': motoristas_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/motoristas/count')
def api_motoristas_count():
    """Contagem de motoristas"""
    try:
        motoristas, _ = carregar_dados_supabase()
        return jsonify({
            'success': True,
            'count': len(motoristas)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prestadores/estatisticas')
def api_prestadores_estatisticas():
    """Estatísticas de prestadores"""
    try:
        motoristas, _ = carregar_dados_supabase()
        
        return jsonify({
            'success': True,
            'data': {
                'total_motoristas': len(motoristas),
                'total_prestadores': 0,
                'motoristas_em_grupos': 0,
                'motoristas_individuais': len(motoristas)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tarifas')
def api_tarifas():
    """Lista tarifas por motorista"""
    try:
        motoristas, tarifas = carregar_dados_supabase()
        
        tarifas_list = []
        for id_motorista, nome in motoristas.items():
            tarifa_motorista = tarifas.get(id_motorista, TARIFAS_PADRAO)
            tarifas_list.append({
                'id_motorista': id_motorista,
                'nome_motorista': nome,
                'tarifas': tarifa_motorista
            })
        
        return jsonify({
            'success': True,
            'data': tarifas_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/motoristas/upload', methods=['POST'])
def api_upload_motoristas():
    """Upload da planilha DE-PARA de motoristas"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'})
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Processar Excel
        df = pd.read_excel(file_path)
        
        motoristas_processados = 0
        motoristas_erro = 0
        
        # Salvar no Supabase
        if supabase:
            for _, row in df.iterrows():
                try:
                    id_motorista = int(row.iloc[0])
                    nome_motorista = str(row.iloc[1]).strip()
                    
                    # Upsert no Supabase
                    supabase.table('motoristas').upsert({
                        'empresa_id': 1,
                        'id_motorista': id_motorista,
                        'nome_motorista': nome_motorista
                    }).execute()
                    
                    motoristas_processados += 1
                except:
                    motoristas_erro += 1
        
        # Invalidar cache
        global cache_timestamp
        cache_timestamp = 0
        
        # Limpar arquivo
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'data': {
                'motoristas_processados': motoristas_processados,
                'motoristas_erro': motoristas_erro,
                'total_motoristas': motoristas_processados,
                'saved_to_supabase': supabase is not None
            },
            'message': f'Planilha processada! {motoristas_processados} motoristas cadastrados.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload de CSV de entregas - VERSÃO ASSÍNCRONA"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'})
        
        # Verificar se já há processamento ativo
        if processing_status['active']:
            return jsonify({'success': False, 'error': 'Já há um processamento em andamento'})
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        print(f"=== INÍCIO UPLOAD ENTREGAS v7.6 DEFINITIVO - ASSÍNCRONO ===")
        print(f"Arquivo recebido: {filename} ({os.path.getsize(file_path)} bytes)")
        
        # Iniciar processamento em background
        thread = threading.Thread(target=processar_csv_assincronamente, args=(file_path,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Processamento iniciado em background. Use /api/upload/status para acompanhar.',
            'data': {
                'processing_id': int(time.time()),
                'status_endpoint': '/api/upload/status'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload/status')
def api_upload_status():
    """Status do processamento assíncrono"""
    return jsonify({
        'success': True,
        'data': processing_status.copy()
    })

if __name__ == '__main__':
    # Configuração para desenvolvimento
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

