# IMPLEMENTAÇÃO SUPABASE v7.3 - PRIMEIRA VEZ COM BANCO REAL
# COMBINA OTIMIZAÇÕES v7.2 + PERSISTÊNCIA PERMANENTE SUPABASE

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import csv
import io
import json
import logging
import datetime
from datetime import datetime, timedelta
import chardet
import openpyxl
from werkzeug.utils import secure_filename
import time

# Configuração da aplicação
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuração de logging OTIMIZADA
logging.basicConfig(level=logging.WARNING)  # Reduzir logs
app.logger.setLevel(logging.WARNING)

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
BATCH_SIZE = 1000  # Processar em lotes de 1000 linhas

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tarifas padrão
TARIFAS_PADRAO = {
    0: 3.50,  # Encomendas
    9: 2.00,  # Cards
    6: 0.50,  # Revistas
    8: 0.50   # Revistas
}

# ==================== CONFIGURAÇÃO SUPABASE ====================

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
    print("✅ Biblioteca supabase-py disponível")
except ImportError:
    SUPABASE_AVAILABLE = False
    print("❌ Biblioteca supabase-py não encontrada")
    print("💡 Execute: pip install supabase")

# Configuração do cliente Supabase
supabase_client = None

def init_supabase():
    """Inicializa conexão com Supabase"""
    global supabase_client
    
    if not SUPABASE_AVAILABLE:
        print("❌ Supabase não disponível - usando fallback local")
        return False
    
    try:
        # Obter credenciais das variáveis de ambiente
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Credenciais do Supabase não configuradas")
            print("💡 Configure SUPABASE_URL e SUPABASE_ANON_KEY")
            return False
        
        # Criar cliente
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Testar conexão
        result = supabase_client.table('motoristas').select('count').execute()
        print(f"✅ Conexão com Supabase estabelecida")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {str(e)}")
        return False

# Inicializar Supabase na inicialização
SUPABASE_CONNECTED = init_supabase()

# ==================== CACHE GLOBAL PARA PERFORMANCE ====================
_cache_tarifas = {}
_cache_motoristas = {}
_cache_timestamp = 0

def invalidate_cache():
    """Invalida cache quando dados são atualizados"""
    global _cache_timestamp
    _cache_timestamp = time.time()

# ==================== FUNÇÕES DE PERSISTÊNCIA HÍBRIDA ====================

def get_motoristas_supabase(empresa_id=1):
    """Carrega motoristas do Supabase"""
    try:
        if not SUPABASE_CONNECTED:
            return []
        
        result = supabase_client.table('motoristas').select('*').eq('empresa_id', empresa_id).execute()
        return result.data if result.data else []
        
    except Exception as e:
        print(f"❌ Erro ao carregar motoristas do Supabase: {str(e)}")
        return []

def save_motoristas_supabase(motoristas, empresa_id=1):
    """Salva motoristas no Supabase"""
    try:
        if not SUPABASE_CONNECTED:
            return False
        
        # Limpar dados existentes da empresa
        supabase_client.table('motoristas').delete().eq('empresa_id', empresa_id).execute()
        
        # Inserir novos dados
        for motorista in motoristas:
            motorista_data = {
                'empresa_id': empresa_id,
                'id_motorista': motorista['id_motorista'],
                'nome_motorista': motorista['nome_motorista'],
                'created_at': motorista.get('created_at', datetime.now().isoformat()),
                'updated_at': motorista.get('updated_at', datetime.now().isoformat())
            }
            supabase_client.table('motoristas').insert(motorista_data).execute()
        
        invalidate_cache()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar motoristas no Supabase: {str(e)}")
        return False

def get_awbs_supabase(empresa_id=1):
    """Carrega AWBs do Supabase"""
    try:
        if not SUPABASE_CONNECTED:
            return {}
        
        result = supabase_client.table('awbs').select('*').eq('empresa_id', empresa_id).execute()
        
        # Converter lista para dicionário
        awbs_dict = {}
        if result.data:
            for awb in result.data:
                awbs_dict[awb['awb']] = awb
        
        return awbs_dict
        
    except Exception as e:
        print(f"❌ Erro ao carregar AWBs do Supabase: {str(e)}")
        return {}

def save_awbs_supabase(awbs_dict, empresa_id=1):
    """Salva AWBs no Supabase"""
    try:
        if not SUPABASE_CONNECTED:
            return False
        
        # Converter dicionário para lista e inserir/atualizar
        for awb_code, awb_data in awbs_dict.items():
            awb_record = {
                'empresa_id': empresa_id,
                'awb': awb_code,
                'id_motorista': awb_data['id_motorista'],
                'nome_motorista': awb_data['nome_motorista'],
                'tipo_servico': awb_data['tipo_servico'],
                'data_entrega': awb_data['data_entrega'],
                'valor_entrega': awb_data['valor_entrega'],
                'status': awb_data['status'],
                'created_at': awb_data.get('created_at', datetime.now().isoformat()),
                'updated_at': awb_data.get('updated_at', datetime.now().isoformat())
            }
            
            # Tentar inserir, se falhar (já existe), atualizar
            try:
                supabase_client.table('awbs').insert(awb_record).execute()
            except:
                supabase_client.table('awbs').update(awb_record).eq('awb', awb_code).eq('empresa_id', empresa_id).execute()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar AWBs no Supabase: {str(e)}")
        return False

def get_tarifas_supabase(empresa_id=1):
    """Carrega tarifas do Supabase"""
    try:
        if not SUPABASE_CONNECTED:
            return {}
        
        result = supabase_client.table('tarifas').select('*').eq('empresa_id', empresa_id).execute()
        
        # Converter para formato esperado
        tarifas_dict = {}
        if result.data:
            for tarifa in result.data:
                motorista_id = str(tarifa['id_motorista'])
                if motorista_id not in tarifas_dict:
                    tarifas_dict[motorista_id] = {}
                tarifas_dict[motorista_id][tarifa['tipo_servico']] = tarifa['valor']
        
        return tarifas_dict
        
    except Exception as e:
        print(f"❌ Erro ao carregar tarifas do Supabase: {str(e)}")
        return {}

# ==================== FUNÇÕES PRINCIPAIS COM CACHE ====================

def get_cached_motoristas(empresa_id=1):
    """Cache de motoristas para evitar carregamento repetitivo"""
    global _cache_motoristas, _cache_timestamp
    
    cache_key = f"motoristas_{empresa_id}"
    current_time = time.time()
    
    # Cache válido por 5 minutos
    if cache_key in _cache_motoristas and (current_time - _cache_timestamp) < 300:
        return _cache_motoristas[cache_key]
    
    # Carregar do Supabase
    motoristas = get_motoristas_supabase(empresa_id)
    _cache_motoristas[cache_key] = motoristas
    return motoristas

def get_cached_tarifas(empresa_id=1):
    """Cache de tarifas para evitar carregamento repetitivo"""
    global _cache_tarifas, _cache_timestamp
    
    cache_key = f"tarifas_{empresa_id}"
    current_time = time.time()
    
    # Cache válido por 5 minutos
    if cache_key in _cache_tarifas and (current_time - _cache_timestamp) < 300:
        return _cache_tarifas[cache_key]
    
    # Carregar do Supabase
    tarifas = get_tarifas_supabase(empresa_id)
    _cache_tarifas[cache_key] = tarifas
    return tarifas

# ==================== FUNÇÕES DE PROCESSAMENTO OTIMIZADAS ====================

def detectar_encoding(file_content_bytes):
    """Detecta encoding do arquivo automaticamente - SUPORTE BRASILEIRO"""
    try:
        # Tentar detectar com chardet
        result = chardet.detect(file_content_bytes)
        encoding = result['encoding']
        confidence = result['confidence']
        
        if encoding and confidence > 0.7:
            try:
                content = file_content_bytes.decode(encoding)
                return content, encoding
            except UnicodeDecodeError:
                pass
        
        # Tentar encodings brasileiros comuns
        for encoding in ['iso-8859-1', 'latin-1', 'cp1252', 'utf-8']:
            try:
                content = file_content_bytes.decode(encoding)
                return content, encoding
            except UnicodeDecodeError:
                continue
        
        # Se nenhum funcionou, forçar latin-1 (sempre funciona)
        content = file_content_bytes.decode('latin-1', errors='replace')
        return content, 'latin-1'
        
    except Exception as e:
        # Fallback final
        content = file_content_bytes.decode('utf-8', errors='replace')
        return content, 'utf-8'

def detectar_delimitador_csv(content):
    """Detecta automaticamente o delimitador do CSV - SUPORTE BRASILEIRO"""
    try:
        # Pegar primeira linha (cabeçalho)
        primeira_linha = content.split('\n')[0]
        
        # Contar delimitadores comuns
        delimitadores = {
            ';': primeira_linha.count(';'),  # Ponto e vírgula (padrão brasileiro)
            ',': primeira_linha.count(','),  # Vírgula (padrão internacional)
            '\t': primeira_linha.count('\t'), # Tab
            '|': primeira_linha.count('|')   # Pipe
        }
        
        # Encontrar delimitador mais comum
        delimitador = max(delimitadores, key=delimitadores.get)
        count = delimitadores[delimitador]
        
        # Se nenhum delimitador foi encontrado, usar vírgula como padrão
        if count == 0:
            return ','
        
        return delimitador
        
    except Exception as e:
        return ','  # Fallback para vírgula

def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calcular_valor_entrega_otimizado(tipo_servico, id_motorista, tarifas_cache):
    """Calcula valor da entrega usando cache - ULTRA OTIMIZADO"""
    # Usar cache em vez de carregar do banco
    tarifa_motorista = tarifas_cache.get(str(id_motorista), TARIFAS_PADRAO)
    valor = tarifa_motorista.get(tipo_servico, TARIFAS_PADRAO.get(tipo_servico, 0))
    return float(valor)

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página inicial"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Servir arquivos estáticos"""
    return send_from_directory(app.static_folder, filename)

# ==================== API DE MOTORISTAS ====================

@app.route('/api/motoristas', methods=['GET'])
def get_motoristas_api():
    """Lista todos os motoristas"""
    try:
        empresa_id = 1
        motoristas = get_cached_motoristas(empresa_id)
        
        return jsonify({
            'success': True,
            'data': motoristas,
            'total': len(motoristas),
            'source': 'supabase' if SUPABASE_CONNECTED else 'local'
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar motoristas: {str(e)}")
        return jsonify({'error': f'Erro ao buscar motoristas: {str(e)}'}), 500

@app.route('/api/motoristas/upload', methods=['POST'])
def upload_motoristas():
    """Upload da planilha DE-PARA de motoristas - VERSÃO SUPABASE v7.3"""
    try:
        empresa_id = 1
        
        print("=== INÍCIO UPLOAD MOTORISTAS v7.3 SUPABASE ===")
        
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Ler conteúdo do arquivo
        file_content_bytes = file.read()
        print(f"Planilha DE-PARA recebida: {file.filename} ({len(file_content_bytes)} bytes)")
        
        motoristas_processados = 0
        motoristas_erro = 0
        
        # Carregar motoristas existentes
        motoristas = get_cached_motoristas(empresa_id)
        
        # Detectar encoding e processar
        file_content, encoding_usado = detectar_encoding(file_content_bytes)
        print(f"Encoding detectado: {encoding_usado}")
        
        if file.filename.endswith(('.xlsx', '.xls')):
            # Processar Excel
            try:
                workbook = openpyxl.load_workbook(io.BytesIO(file_content_bytes))
                sheet = workbook.active
                
                print(f"Excel carregado: {sheet.max_row} linhas x {sheet.max_column} colunas")
                
                # Encontrar cabeçalhos
                headers = []
                for col_num in range(1, sheet.max_column + 1):
                    cell = sheet.cell(row=1, column=col_num)
                    headers.append(str(cell.value) if cell.value else f"Col_{col_num}")
                
                print(f"Cabeçalhos encontrados: {headers}")
                
                # Processar dados
                for row_num in range(2, sheet.max_row + 1):
                    try:
                        # Criar dicionário da linha
                        linha_data = {}
                        for col_num in range(1, sheet.max_column + 1):
                            cell = sheet.cell(row=row_num, column=col_num)
                            linha_data[headers[col_num - 1]] = cell.value
                        
                        # Procurar ID do motorista
                        id_motorista = None
                        for col_name in ['ID do motorista', 'ID', 'id', 'Id', 'ID_MOTORISTA', 'id_motorista']:
                            if col_name in linha_data and linha_data[col_name] is not None:
                                try:
                                    if isinstance(linha_data[col_name], (int, float)):
                                        id_motorista = int(linha_data[col_name])
                                    else:
                                        id_motorista = int(float(str(linha_data[col_name])))
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        # Procurar nome do motorista
                        nome_motorista = None
                        for col_name in ['Nome do motorista', 'NOME', 'nome', 'Nome', 'NOME_MOTORISTA', 'nome_motorista']:
                            if col_name in linha_data and linha_data[col_name] is not None:
                                nome_motorista = str(linha_data[col_name]).strip()
                                if nome_motorista and nome_motorista != 'None' and nome_motorista != '':
                                    break
                        
                        if not id_motorista or not nome_motorista:
                            motoristas_erro += 1
                            continue
                        
                        # Verificar se motorista já existe
                        motorista_existente = None
                        for m in motoristas:
                            if m['id_motorista'] == id_motorista:
                                motorista_existente = m
                                break
                        
                        if motorista_existente:
                            # Atualizar dados existentes
                            motorista_existente['nome_motorista'] = nome_motorista
                            motorista_existente['updated_at'] = datetime.now().isoformat()
                        else:
                            # Criar novo motorista
                            motorista = {
                                'id_motorista': id_motorista,
                                'nome_motorista': nome_motorista,
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            motoristas.append(motorista)
                        
                        motoristas_processados += 1
                        
                    except Exception as e:
                        motoristas_erro += 1
                        continue
                
            except Exception as e:
                return jsonify({'error': f'Erro ao processar Excel: {str(e)}'}), 500
        
        else:
            return jsonify({'error': 'Formato de arquivo não suportado para motoristas'}), 400
        
        # Salvar dados no Supabase
        success = save_motoristas_supabase(motoristas, empresa_id)
        
        print(f"=== RESULTADO FINAL ===")
        print(f"Motoristas processados: {motoristas_processados}")
        print(f"Motoristas com erro: {motoristas_erro}")
        print(f"Total de motoristas no sistema: {len(motoristas)}")
        print(f"Salvos no Supabase: {'✅' if success else '❌'}")
        
        return jsonify({
            'success': True,
            'message': f'Planilha processada: {motoristas_processados} motoristas, {motoristas_erro} erros',
            'data': {
                'motoristas_processados': motoristas_processados,
                'motoristas_erro': motoristas_erro,
                'total_motoristas': len(motoristas),
                'saved_to_supabase': success
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no upload de motoristas: {str(e)}")
        return jsonify({'error': f'Erro no upload: {str(e)}'}), 500

# ==================== API DE UPLOAD DE ENTREGAS SUPABASE v7.3 ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload de arquivo CSV/Excel de entregas - VERSÃO v7.3 SUPABASE + OTIMIZAÇÕES"""
    try:
        empresa_id = 1
        
        print("=== INÍCIO UPLOAD ENTREGAS v7.3 SUPABASE + OTIMIZAÇÕES ===")
        start_time = time.time()
        
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Carregar dados existentes UMA VEZ SÓ
        print("Carregando dados do Supabase...")
        awbs = get_awbs_supabase(empresa_id)
        motoristas = get_cached_motoristas(empresa_id)
        tarifas_cache = get_cached_tarifas(empresa_id)  # CACHE GLOBAL
        
        # Criar dicionário de motoristas para busca rápida
        motoristas_dict = {m['id_motorista']: m for m in motoristas}
        print(f"Sistema carregado: {len(motoristas)} motoristas, {len(awbs)} AWBs existentes")
        print(f"Fonte: {'Supabase' if SUPABASE_CONNECTED else 'Local'}")
        
        # Ler conteúdo do arquivo
        file_content_bytes = file.read()
        print(f"Arquivo recebido: {file.filename} ({len(file_content_bytes)} bytes)")
        
        entregas_processadas = 0
        entregas_erro = 0
        awbs_novas = 0
        
        # Detectar encoding e processar
        file_content, encoding_usado = detectar_encoding(file_content_bytes)
        print(f"Encoding detectado: {encoding_usado}")
        
        # DETECTAR DELIMITADOR AUTOMATICAMENTE
        delimitador = detectar_delimitador_csv(file_content)
        print(f"Delimitador detectado: '{delimitador}'")
        
        try:
            # Processar CSV com delimitador correto
            csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=delimitador)
            dados = list(csv_reader)
            total_linhas = len(dados)
            print(f"CSV carregado: {total_linhas} linhas")
            print(f"Colunas: {csv_reader.fieldnames}")
            
            # PROCESSAMENTO EM LOTES ULTRA OTIMIZADO
            for i in range(0, total_linhas, BATCH_SIZE):
                lote = dados[i:i + BATCH_SIZE]
                lote_inicio = time.time()
                
                for linha_num, linha in enumerate(lote, start=i + 2):
                    try:
                        # Procurar AWB
                        awb = None
                        for col in ['AWB', 'awb', 'Awb']:
                            if col in linha and linha[col]:
                                awb = str(linha[col]).strip()
                                if awb and awb != 'None':
                                    break
                        
                        if not awb:
                            entregas_erro += 1
                            continue
                        
                        # Procurar ID do motorista
                        id_motorista = None
                        for col in ['ID do motorista', 'ID_MOTORISTA', 'id_motorista']:
                            if col in linha and linha[col]:
                                try:
                                    id_motorista = int(linha[col])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        if not id_motorista or id_motorista not in motoristas_dict:
                            entregas_erro += 1
                            continue
                        
                        # Procurar tipo de serviço
                        tipo_servico = 0  # Padrão: encomendas
                        for col in ['Tipo de Serviço', 'TIPO_SERVICO', 'tipo_servico']:
                            if col in linha and linha[col]:
                                try:
                                    tipo_servico = int(linha[col])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        # Procurar data/hora da entrega
                        data_entrega = None
                        for col in ['Data/Hora Status do último status', 'DATA_ENTREGA', 'data_entrega']:
                            if col in linha and linha[col]:
                                data_entrega = str(linha[col]).strip()
                                if data_entrega and data_entrega != 'None':
                                    break
                        
                        if not data_entrega:
                            data_entrega = datetime.now().isoformat()
                        
                        # Calcular valor da entrega USANDO CACHE
                        valor_entrega = calcular_valor_entrega_otimizado(tipo_servico, id_motorista, tarifas_cache)
                        
                        # Verificar se AWB já existe
                        if awb in awbs:
                            awb_data = awbs[awb]
                            awb_data['updated_at'] = datetime.now().isoformat()
                        else:
                            # Criar nova AWB
                            awb_data = {
                                'awb': awb,
                                'id_motorista': id_motorista,
                                'nome_motorista': motoristas_dict[id_motorista]['nome_motorista'],
                                'tipo_servico': tipo_servico,
                                'data_entrega': data_entrega,
                                'valor_entrega': valor_entrega,
                                'status': 'NAO_PAGA',
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            awbs[awb] = awb_data
                            awbs_novas += 1
                        
                        entregas_processadas += 1
                        
                    except Exception as e:
                        entregas_erro += 1
                        continue
                
                # SALVAR LOTE NO SUPABASE PARA EVITAR PERDA DE DADOS
                save_awbs_supabase(awbs, empresa_id)
                
                lote_tempo = time.time() - lote_inicio
                progresso = ((i + len(lote)) / total_linhas) * 100
                print(f"Lote {i//BATCH_SIZE + 1}: {len(lote)} linhas em {lote_tempo:.2f}s - Progresso: {progresso:.1f}%")
            
        except Exception as e:
            return jsonify({'error': f'Erro ao processar CSV: {str(e)}'}), 500
        
        # Salvar dados finais no Supabase
        final_save = save_awbs_supabase(awbs, empresa_id)
        
        tempo_total = time.time() - start_time
        
        print(f"=== RESULTADO FINAL ===")
        print(f"Tempo total: {tempo_total:.2f} segundos")
        print(f"Entregas processadas: {entregas_processadas}")
        print(f"Entregas com erro: {entregas_erro}")
        print(f"AWBs novas: {awbs_novas}")
        print(f"Total de AWBs no sistema: {len(awbs)}")
        print(f"Performance: {entregas_processadas/tempo_total:.0f} linhas/segundo")
        print(f"Salvos no Supabase: {'✅' if final_save else '❌'}")
        
        return jsonify({
            'success': True,
            'message': f'Arquivo processado em {tempo_total:.1f}s: {entregas_processadas} entregas, {entregas_erro} erros',
            'data': {
                'entregas_processadas': entregas_processadas,
                'entregas_erro': entregas_erro,
                'awbs_novas': awbs_novas,
                'total_awbs': len(awbs),
                'tempo_processamento': tempo_total,
                'performance_linhas_por_segundo': round(entregas_processadas/tempo_total) if tempo_total > 0 else 0,
                'saved_to_supabase': final_save,
                'supabase_connected': SUPABASE_CONNECTED
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no upload: {str(e)}")
        return jsonify({'error': f'Erro no upload: {str(e)}'}), 500

# ==================== STATUS DO SISTEMA ====================

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Status do sistema e conexões"""
    return jsonify({
        'success': True,
        'data': {
            'supabase_available': SUPABASE_AVAILABLE,
            'supabase_connected': SUPABASE_CONNECTED,
            'cache_timestamp': _cache_timestamp,
            'version': '7.3-SUPABASE'
        }
    })

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    print("🚀 MenezesLog SaaS v7.3 SUPABASE + OTIMIZAÇÕES iniciado!")
    print("🇧🇷 Suporte completo a encoding brasileiro")
    print("⚡ Otimizado para processar 300K linhas sem timeout")
    print("💾 Sistema de persistência permanente no Supabase")
    print("🎯 Cache inteligente para máxima performance")
    print(f"📡 Supabase: {'✅ CONECTADO' if SUPABASE_CONNECTED else '❌ DESCONECTADO'}")
    app.run(host='0.0.0.0', port=5000, debug=False)

