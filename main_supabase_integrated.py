# MenezesLog SaaS v7.8 PRO TIER - PERFORMANCE MÁXIMA
# Sistema otimizado para Supabase Pro Tier ($25/mês)
# Performance máxima com processamento paralelo e batch inserts grandes

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

# Configurações otimizadas para Supabase PRO TIER
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# OTIMIZAÇÕES PARA SUPABASE PRO TIER
BATCH_SIZE = 500  # Aumentado para 500 (Pro tier suporta)
MAX_WORKERS = 3   # 3 threads paralelas (200 conexões disponíveis)
BATCH_DELAY = 0.05  # 50ms entre batches (muito mais rápido)
MAX_RETRIES = 5   # Mais tentativas para garantir sucesso
CHUNK_SIZE = 2000  # Chunks maiores para processamento

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
        print("✅ Conexão com Supabase PRO estabelecida")
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")

# Cache global para performance máxima
cache_motoristas = {}
cache_tarifas = {}
cache_awbs_existentes = set()
cache_timestamp = 0
CACHE_DURATION = 900  # 15 minutos (Pro tier permite cache mais longo)

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
    'duplicates_discarded': 0,
    'new_awbs_saved': 0,
    'start_time': None,
    'estimated_time': None,
    'performance_stats': {}
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

def carregar_awbs_existentes_pro():
    """Carrega AWBs existentes de forma otimizada para Pro tier"""
    global cache_awbs_existentes
    
    if not supabase:
        return set()
    
    try:
        # Pro tier permite consultas maiores - carregar em lotes
        awbs_set = set()
        page_size = 1000
        page = 0
        
        while True:
            start = page * page_size
            end = start + page_size - 1
            
            response = supabase.table('awbs').select('awb').range(start, end).execute()
            
            if not response.data:
                break
                
            for item in response.data:
                awbs_set.add(item['awb'])
            
            if len(response.data) < page_size:
                break
                
            page += 1
        
        cache_awbs_existentes = awbs_set
        print(f"✅ Cache AWBs PRO: {len(cache_awbs_existentes)} AWBs existentes carregadas")
        return cache_awbs_existentes
        
    except Exception as e:
        print(f"❌ Erro ao carregar AWBs existentes: {e}")
        return set()

def carregar_dados_supabase_pro():
    """Carrega dados do Supabase com cache otimizado para Pro tier"""
    global cache_motoristas, cache_tarifas, cache_timestamp
    
    current_time = time.time()
    if current_time - cache_timestamp < CACHE_DURATION and cache_motoristas:
        return cache_motoristas, cache_tarifas
    
    motoristas = {}
    tarifas = {}
    
    if supabase:
        try:
            # Pro tier permite consultas maiores
            response = supabase.table('motoristas').select('*').limit(10000).execute()
            if response.data:
                for motorista in response.data:
                    motoristas[motorista['id_motorista']] = motorista['nome_motorista']
            
            # Carregar tarifas customizadas se existirem
            try:
                tarifas_response = supabase.table('tarifas').select('*').execute()
                tarifas_custom = {}
                if tarifas_response.data:
                    for tarifa in tarifas_response.data:
                        id_mot = tarifa['id_motorista']
                        tipo_serv = tarifa['tipo_servico']
                        valor = tarifa['valor']
                        
                        if id_mot not in tarifas_custom:
                            tarifas_custom[id_mot] = TARIFAS_PADRAO.copy()
                        tarifas_custom[id_mot][tipo_serv] = valor
                
                # Aplicar tarifas customizadas ou usar padrão
                for id_motorista in motoristas.keys():
                    tarifas[id_motorista] = tarifas_custom.get(id_motorista, TARIFAS_PADRAO.copy())
                    
            except:
                # Se não tiver tarifas customizadas, usar padrão
                for id_motorista in motoristas.keys():
                    tarifas[id_motorista] = TARIFAS_PADRAO.copy()
            
            cache_motoristas = motoristas
            cache_tarifas = tarifas
            cache_timestamp = current_time
            
            print(f"✅ Dados PRO carregados: {len(motoristas)} motoristas, tarifas customizadas")
            
        except Exception as e:
            print(f"❌ Erro ao carregar dados do Supabase: {e}")
    
    return motoristas, tarifas

def calcular_valor_entrega_pro(tipo_servico, id_motorista, tarifas_cache):
    """Versão Pro do cálculo de valor com tarifas customizadas"""
    try:
        tipo_servico = int(tipo_servico)
        id_motorista = int(id_motorista)
        
        # Buscar tarifa específica do motorista (Pro tier suporta tarifas customizadas)
        if id_motorista in tarifas_cache:
            return tarifas_cache[id_motorista].get(tipo_servico, TARIFAS_PADRAO.get(tipo_servico, 0))
        
        # Usar tarifa padrão
        return TARIFAS_PADRAO.get(tipo_servico, 0)
    except:
        return 0

def salvar_lote_supabase_pro(awbs_lote, chunk_id):
    """Salva lote de AWBs no Supabase Pro com performance máxima"""
    if not supabase or not awbs_lote:
        return 0, 0
    
    try:
        # Filtrar duplicatas ANTES de tentar inserir
        awbs_existentes = cache_awbs_existentes
        awbs_novas = []
        duplicatas_descartadas = 0
        
        for awb in awbs_lote:
            if awb['awb'] not in awbs_existentes:
                awbs_novas.append({
                    'empresa_id': 1,
                    'awb': awb['awb'],
                    'id_motorista': awb['id_motorista'],
                    'nome_motorista': awb['nome_motorista'],
                    'tipo_servico': awb['tipo_servico'],
                    'data_entrega': awb.get('data_entrega', ''),
                    'valor_entrega': float(awb['valor_entrega']),
                    'status': 'NAO_PAGA'
                })
                # Adicionar ao cache para evitar duplicatas no mesmo upload
                awbs_existentes.add(awb['awb'])
            else:
                duplicatas_descartadas += 1
        
        if not awbs_novas:
            print(f"📦 Chunk {chunk_id}: Todas as {len(awbs_lote)} AWBs já existem - descartadas")
            return 0, duplicatas_descartadas
        
        # Pro tier: Salvar em lotes maiores com menos delay
        total_salvos = 0
        for i in range(0, len(awbs_novas), BATCH_SIZE):
            lote = awbs_novas[i:i+BATCH_SIZE]
            
            # Retry com backoff otimizado para Pro tier
            for tentativa in range(MAX_RETRIES):
                try:
                    # INSERT com ON CONFLICT para Pro tier (mais eficiente)
                    response = supabase.table('awbs').insert(lote).execute()
                    if response.data:
                        total_salvos += len(lote)
                        print(f"💾 PRO Chunk {chunk_id}: {min(i+BATCH_SIZE, len(awbs_novas))}/{len(awbs_novas)} AWBs salvas")
                    break
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        # Se for duplicata, contar como descartada e continuar
                        duplicatas_descartadas += len(lote)
                        break
                    elif tentativa < MAX_RETRIES - 1:
                        wait_time = (tentativa + 1) * 0.1  # Backoff mais rápido para Pro
                        print(f"⚠️ PRO Tentativa {tentativa + 1} falhou, aguardando {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Erro após {MAX_RETRIES} tentativas: {e}")
                        raise e
            
            # Delay menor entre batches (Pro tier suporta mais throughput)
            if i + BATCH_SIZE < len(awbs_novas):
                time.sleep(BATCH_DELAY)
        
        return total_salvos, duplicatas_descartadas
        
    except Exception as e:
        print(f"❌ Erro ao salvar lote no Supabase PRO: {e}")
        return 0, 0

def processar_chunk_pro(chunk_data, chunk_id, motoristas_cache, tarifas_cache):
    """Processa um chunk de dados com performance Pro tier"""
    awbs_processadas = []
    erros = 0
    
    for _, row in chunk_data.iterrows():
        try:
            # Extrair dados da linha
            awb = str(row.get('AWB', '')).strip()
            if not awb:  # Pular linhas sem AWB
                erros += 1
                continue
                
            id_motorista = int(row.get('ID do motorista', 0))
            tipo_servico = int(row.get('Tipo de Serviço', 0))
            data_entrega = str(row.get('Data/Hora Status do último status', ''))
            
            # Verificar se motorista existe
            if id_motorista not in motoristas_cache:
                erros += 1
                continue
            
            # Calcular valor com tarifas Pro
            valor_entrega = calcular_valor_entrega_pro(tipo_servico, id_motorista, tarifas_cache)
            
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
    
    # Salvar no Supabase Pro com performance máxima
    salvos, duplicatas = salvar_lote_supabase_pro(awbs_processadas, chunk_id)
    
    return len(awbs_processadas), erros, salvos, duplicatas

def processar_csv_pro_tier(file_path):
    """Processa CSV com performance máxima do Pro tier"""
    global processing_status
    
    try:
        processing_status.update({
            'active': True,
            'progress': 0,
            'message': 'Iniciando processamento PRO TIER...',
            'start_time': time.time(),
            'duplicates_discarded': 0,
            'new_awbs_saved': 0,
            'performance_stats': {}
        })
        
        # Detectar encoding e delimitador
        encoding = detectar_encoding(file_path)
        delimitador = detectar_delimitador_csv(file_path, encoding)
        
        processing_status['message'] = f'PRO: Encoding {encoding}, Delimitador {delimitador}'
        
        # Carregar dados e AWBs existentes (Pro tier permite cache maior)
        motoristas_cache, tarifas_cache = carregar_dados_supabase_pro()
        carregar_awbs_existentes_pro()
        
        processing_status['message'] = f'PRO: {len(motoristas_cache)} motoristas, {len(cache_awbs_existentes)} AWBs em cache'
        
        # Ler CSV
        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimitador)
        total_linhas = len(df)
        
        processing_status.update({
            'total_lines': total_linhas,
            'message': f'PRO: CSV carregado - {total_linhas} linhas'
        })
        
        # Dividir em chunks maiores para Pro tier
        chunks = [df[i:i+CHUNK_SIZE] for i in range(0, len(df), CHUNK_SIZE)]
        
        processing_status['message'] = f'PRO: Processando {len(chunks)} chunks com {MAX_WORKERS} threads paralelas'
        
        # Processar chunks em PARALELO (Pro tier suporta múltiplas conexões)
        total_processadas = 0
        total_erros = 0
        total_salvos = 0
        total_duplicatas = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for i, chunk in enumerate(chunks):
                future = executor.submit(
                    processar_chunk_pro, 
                    chunk, i+1, motoristas_cache, tarifas_cache
                )
                futures.append(future)
            
            # Coletar resultados com timeout maior para Pro tier
            for i, future in enumerate(futures):
                try:
                    processadas, erros, salvos, duplicatas = future.result(timeout=600)  # 10 minutos por chunk
                    total_processadas += processadas
                    total_erros += erros
                    total_salvos += salvos
                    total_duplicatas += duplicatas
                    
                    # Atualizar progresso
                    progress = ((i + 1) / len(chunks)) * 100
                    processing_status.update({
                        'progress': progress,
                        'processed_lines': total_processadas,
                        'errors': total_erros,
                        'duplicates_discarded': total_duplicatas,
                        'new_awbs_saved': total_salvos,
                        'message': f'PRO: Chunk {i+1}/{len(chunks)} - {salvos} novas, {duplicatas} duplicatas'
                    })
                    
                except Exception as e:
                    print(f"❌ Erro no chunk {i+1}: {e}")
                    total_erros += len(chunks[i])
        
        # Finalizar com estatísticas Pro
        tempo_total = time.time() - processing_status['start_time']
        performance = total_processadas / tempo_total if tempo_total > 0 else 0
        
        processing_status.update({
            'active': False,
            'progress': 100,
            'message': 'PRO: Processamento concluído com performance máxima!',
            'performance_stats': {
                'linhas_por_segundo': round(performance, 2),
                'tempo_total': round(tempo_total, 2),
                'chunks_paralelos': len(chunks),
                'workers_utilizados': MAX_WORKERS,
                'batch_size': BATCH_SIZE
            }
        })
        
        return {
            'success': True,
            'data': {
                'entregas_processadas': total_processadas,
                'entregas_erro': total_erros,
                'awbs_novas_salvas': total_salvos,
                'duplicatas_descartadas': total_duplicatas,
                'tempo_processamento': round(tempo_total, 2),
                'performance_linhas_por_segundo': round(performance, 2),
                'tier': 'PRO',
                'workers_paralelos': MAX_WORKERS,
                'batch_size': BATCH_SIZE
            },
            'message': f'PRO TIER: {total_salvos} AWBs novas salvas, {total_duplicatas} duplicatas descartadas em {round(tempo_total, 2)}s!'
        }
        
    except Exception as e:
        processing_status.update({
            'active': False,
            'message': f'PRO: Erro - {str(e)}'
        })
        return {
            'success': False,
            'error': str(e)
        }

# ROTAS DA API OTIMIZADAS PARA PRO TIER

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

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
    """Status do sistema Pro tier"""
    return jsonify({
        'success': True,
        'data': {
            'supabase_connected': supabase is not None,
            'supabase_url': SUPABASE_URL is not None,
            'version': 'v7.8 PRO TIER',
            'processing_active': processing_status['active'],
            'tier': 'PRO ($25/mês)',
            'optimization_level': 'Performance Máxima',
            'batch_size': BATCH_SIZE,
            'max_workers': MAX_WORKERS,
            'chunk_size': CHUNK_SIZE,
            'cache_duration': f'{CACHE_DURATION//60} minutos'
        }
    })

@app.route('/api/estatisticas')
def api_estatisticas():
    """Estatísticas gerais do sistema Pro"""
    try:
        motoristas, _ = carregar_dados_supabase_pro()
        
        # Pro tier permite consultas mais complexas
        total_awbs = 0
        awbs_pagas = 0
        awbs_pendentes = 0
        valor_total = 0
        
        if supabase:
            try:
                # Contar total
                response = supabase.table('awbs').select('id', count='exact').execute()
                total_awbs = response.count if response.count else 0
                
                # Estatísticas por status (Pro tier suporta)
                pagas_response = supabase.table('awbs').select('id', count='exact').eq('status', 'PAGA').execute()
                awbs_pagas = pagas_response.count if pagas_response.count else 0
                
                pendentes_response = supabase.table('awbs').select('id', count='exact').eq('status', 'NAO_PAGA').execute()
                awbs_pendentes = pendentes_response.count if pendentes_response.count else 0
                
                # Valor total (Pro tier permite agregações)
                valor_response = supabase.table('awbs').select('valor_entrega').execute()
                if valor_response.data:
                    valor_total = sum(float(item['valor_entrega']) for item in valor_response.data)
                
            except Exception as e:
                print(f"Erro ao carregar estatísticas: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_motoristas': len(motoristas),
                'total_prestadores': 0,  # Implementar quando tiver grupos
                'total_awbs': total_awbs,
                'awbs_pagas': awbs_pagas,
                'awbs_pendentes': awbs_pendentes,
                'valor_total': round(valor_total, 2),
                'supabase_connected': supabase is not None,
                'awbs_cache_size': len(cache_awbs_existentes),
                'tier': 'PRO'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/motoristas')
def api_motoristas():
    """Lista todos os motoristas (Pro tier)"""
    try:
        motoristas, _ = carregar_dados_supabase_pro()
        
        motoristas_list = []
        for id_motorista, nome in motoristas.items():
            # Pro tier permite consultas por motorista
            total_awbs = 0
            valor_total = 0
            
            if supabase:
                try:
                    awbs_response = supabase.table('awbs').select('valor_entrega', count='exact').eq('id_motorista', id_motorista).execute()
                    total_awbs = awbs_response.count if awbs_response.count else 0
                    
                    if awbs_response.data:
                        valor_total = sum(float(item['valor_entrega']) for item in awbs_response.data)
                except:
                    pass
            
            motoristas_list.append({
                'id_motorista': id_motorista,
                'nome_motorista': nome,
                'total_awbs': total_awbs,
                'valor_total': round(valor_total, 2),
                'created_at': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': motoristas_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/awbs')
def api_awbs():
    """Lista AWBs com paginação otimizada para Pro tier"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 100)), 500)  # Pro tier: até 500 por página
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        motorista_filter = request.args.get('motorista', '').strip()
        
        if not supabase:
            return jsonify({'success': False, 'error': 'Supabase não conectado'})
        
        # Construir query com filtros avançados (Pro tier suporta)
        query = supabase.table('awbs').select('*')
        
        if search:
            query = query.or_(f'awb.ilike.%{search}%,nome_motorista.ilike.%{search}%')
        
        if status_filter:
            query = query.eq('status', status_filter)
            
        if motorista_filter:
            query = query.eq('nome_motorista', motorista_filter)
        
        # Paginação
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        response = query.range(start, end).order('created_at', desc=True).execute()
        
        # Contar total com filtros
        count_query = supabase.table('awbs').select('id', count='exact')
        if search:
            count_query = count_query.or_(f'awb.ilike.%{search}%,nome_motorista.ilike.%{search}%')
        if status_filter:
            count_query = count_query.eq('status', status_filter)
        if motorista_filter:
            count_query = count_query.eq('nome_motorista', motorista_filter)
            
        count_response = count_query.execute()
        total = count_response.count if count_response.count else 0
        
        return jsonify({
            'success': True,
            'data': {
                'awbs': response.data if response.data else [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                },
                'filters': {
                    'search': search,
                    'status': status_filter,
                    'motorista': motorista_filter
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload de arquivo CSV otimizado para Pro tier"""
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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Processar com performance Pro tier
        def processar_async():
            return processar_csv_pro_tier(file_path)
        
        # Executar processamento
        resultado = processar_async()
        
        # Limpar arquivo temporário
        try:
            os.remove(file_path)
        except:
            pass
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload/status')
def api_upload_status():
    """Status do processamento em tempo real Pro tier"""
    return jsonify({
        'success': True,
        'data': processing_status
    })

@app.route('/api/prestadores/upload', methods=['POST'])
def api_prestadores_upload():
    """Upload de planilha DE-PARA de motoristas (Pro tier)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'})
        
        # Salvar arquivo temporário
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, f"temp_{filename}")
        file.save(file_path)
        
        # Processar planilha DE-PARA
        encoding = detectar_encoding(file_path)
        
        if filename.endswith('.csv'):
            delimitador = detectar_delimitador_csv(file_path, encoding)
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimitador)
        else:
            df = pd.read_excel(file_path)
        
        # Processar motoristas em lotes (Pro tier suporta)
        motoristas_processados = 0
        motoristas_atualizados = 0
        
        if supabase:
            # Preparar dados para upsert em lote
            motoristas_data = []
            
            for _, row in df.iterrows():
                try:
                    id_motorista = int(row.get('ID do motorista', 0))
                    nome_motorista = str(row.get('Nome do motorista', '')).strip()
                    
                    if id_motorista and nome_motorista:
                        motoristas_data.append({
                            'empresa_id': 1,
                            'id_motorista': id_motorista,
                            'nome_motorista': nome_motorista
                        })
                        
                except Exception as e:
                    continue
            
            # Upsert em lotes (Pro tier permite)
            if motoristas_data:
                try:
                    response = supabase.table('motoristas').upsert(motoristas_data).execute()
                    if response.data:
                        motoristas_processados = len(response.data)
                except Exception as e:
                    print(f"Erro no upsert: {e}")
        
        # Limpar arquivo temporário
        try:
            os.remove(file_path)
        except:
            pass
        
        # Invalidar cache
        global cache_timestamp
        cache_timestamp = 0
        
        return jsonify({
            'success': True,
            'data': {
                'motoristas_processados': motoristas_processados,
                'total_linhas': len(df),
                'tier': 'PRO'
            },
            'message': f'PRO TIER: {motoristas_processados} motoristas processados com upsert em lote!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prestadores/estatisticas')
def api_prestadores_estatisticas():
    """Estatísticas dos prestadores (Pro tier)"""
    try:
        motoristas, _ = carregar_dados_supabase_pro()
        
        return jsonify({
            'success': True,
            'data': {
                'total_motoristas': len(motoristas),
                'motoristas_em_grupos': 0,  # Implementar quando tiver grupos
                'motoristas_individuais': len(motoristas),
                'total_prestadores': 1 if len(motoristas) > 0 else 0,
                'tier': 'PRO'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tarifas')
def api_tarifas():
    """Lista tarifas por motorista (Pro tier com tarifas customizadas)"""
    try:
        motoristas, tarifas = carregar_dados_supabase_pro()
        
        tarifas_list = []
        for id_motorista, nome in motoristas.items():
            tarifa_motorista = tarifas.get(id_motorista, TARIFAS_PADRAO)
            tarifas_list.append({
                'id_motorista': id_motorista,
                'nome_motorista': nome,
                'tarifas': tarifa_motorista,
                'customizada': id_motorista in tarifas and tarifas[id_motorista] != TARIFAS_PADRAO
            })
        
        return jsonify({
            'success': True,
            'data': tarifas_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tarifas/update', methods=['POST'])
def api_tarifas_update():
    """Atualizar tarifas customizadas (Pro tier)"""
    try:
        data = request.get_json()
        id_motorista = data.get('id_motorista')
        tarifas_novas = data.get('tarifas')
        
        if not supabase or not id_motorista or not tarifas_novas:
            return jsonify({'success': False, 'error': 'Dados inválidos'})
        
        # Salvar tarifas customizadas (Pro tier suporta)
        for tipo_servico, valor in tarifas_novas.items():
            try:
                supabase.table('tarifas').upsert({
                    'empresa_id': 1,
                    'id_motorista': int(id_motorista),
                    'tipo_servico': int(tipo_servico),
                    'valor': float(valor)
                }).execute()
            except Exception as e:
                print(f"Erro ao salvar tarifa: {e}")
        
        # Invalidar cache
        global cache_timestamp
        cache_timestamp = 0
        
        return jsonify({
            'success': True,
            'message': 'Tarifas customizadas salvas com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Configuração otimizada para Pro tier
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

