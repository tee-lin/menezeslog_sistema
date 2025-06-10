# MenezesLog SaaS v7.2 ULTRA-OTIMIZADO - PROCESSA 300K LINHAS
# OTIMIZADO PARA ARQUIVOS GRANDES SEM TIMEOUT

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
DATA_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
BATCH_SIZE = 1000  # Processar em lotes de 1000 linhas

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Tarifas padrão
TARIFAS_PADRAO = {
    0: 3.50,  # Encomendas
    9: 2.00,  # Cards
    6: 0.50,  # Revistas
    8: 0.50   # Revistas
}

# ==================== CACHE GLOBAL PARA PERFORMANCE ====================
_cache_tarifas = {}
_cache_motoristas = {}
_cache_timestamp = 0

def invalidate_cache():
    """Invalida cache quando dados são atualizados"""
    global _cache_timestamp
    _cache_timestamp = time.time()

def get_cached_tarifas(empresa_id=1):
    """Cache de tarifas para evitar carregamento repetitivo"""
    global _cache_tarifas, _cache_timestamp
    
    cache_key = f"tarifas_{empresa_id}"
    current_time = time.time()
    
    # Cache válido por 5 minutos
    if cache_key in _cache_tarifas and (current_time - _cache_timestamp) < 300:
        return _cache_tarifas[cache_key]
    
    # Carregar do disco
    tarifas = load_data('tarifas', empresa_id, default={})
    _cache_tarifas[cache_key] = tarifas
    return tarifas

def get_cached_motoristas(empresa_id=1):
    """Cache de motoristas para evitar carregamento repetitivo"""
    global _cache_motoristas, _cache_timestamp
    
    cache_key = f"motoristas_{empresa_id}"
    current_time = time.time()
    
    # Cache válido por 5 minutos
    if cache_key in _cache_motoristas and (current_time - _cache_timestamp) < 300:
        return _cache_motoristas[cache_key]
    
    # Carregar do disco
    motoristas = load_data('motoristas', empresa_id, default=[])
    _cache_motoristas[cache_key] = motoristas
    return motoristas

# ==================== PERSISTÊNCIA EM ARQUIVOS JSON ====================

def get_data_file_path(data_type, empresa_id=1):
    """Retorna caminho do arquivo de dados"""
    return os.path.join(DATA_FOLDER, f'{data_type}_{empresa_id}.json')

def load_data(data_type, empresa_id=1, default=None):
    """Carrega dados do arquivo JSON"""
    if default is None:
        default = []
    
    file_path = get_data_file_path(data_type, empresa_id)
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except Exception as e:
        app.logger.error(f"Erro ao carregar {data_type}: {str(e)}")
        return default

def save_data(data_type, data, empresa_id=1):
    """Salva dados no arquivo JSON"""
    file_path = get_data_file_path(data_type, empresa_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        invalidate_cache()  # Invalidar cache após salvar
        return True
    except Exception as e:
        app.logger.error(f"Erro ao salvar {data_type}: {str(e)}")
        return False

# Funções específicas para cada tipo de dados
def get_motoristas(empresa_id=1):
    return get_cached_motoristas(empresa_id)

def save_motoristas(motoristas, empresa_id=1):
    return save_data('motoristas', motoristas, empresa_id)

def get_prestadores(empresa_id=1):
    return load_data('prestadores', empresa_id, default=[])

def save_prestadores(prestadores, empresa_id=1):
    return save_data('prestadores', prestadores, empresa_id)

def get_tarifas(empresa_id=1):
    return get_cached_tarifas(empresa_id)

def save_tarifas(tarifas, empresa_id=1):
    return save_data('tarifas', tarifas, empresa_id)

def get_awbs(empresa_id=1):
    return load_data('awbs', empresa_id, default={})

def save_awbs(awbs, empresa_id=1):
    return save_data('awbs', awbs, empresa_id)

def get_entregas(empresa_id=1):
    return load_data('entregas', empresa_id, default=[])

def save_entregas(entregas, empresa_id=1):
    return save_data('entregas', entregas, empresa_id)

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
    # Usar cache em vez de carregar do disco
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
        motoristas = get_motoristas(empresa_id)
        
        return jsonify({
            'success': True,
            'data': motoristas,
            'total': len(motoristas)
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar motoristas: {str(e)}")
        return jsonify({'error': f'Erro ao buscar motoristas: {str(e)}'}), 500

@app.route('/api/motoristas/upload', methods=['POST'])
def upload_motoristas():
    """Upload da planilha DE-PARA de motoristas - VERSÃO ULTRA OTIMIZADA"""
    try:
        empresa_id = 1
        
        print("=== INÍCIO UPLOAD MOTORISTAS v7.2 ULTRA OTIMIZADO ===")
        
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
        motoristas = get_motoristas(empresa_id)
        
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
                
                # Processar dados em lotes
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
                            
                            # Inicializar tarifas padrão
                            tarifas = get_tarifas(empresa_id)
                            if str(id_motorista) not in tarifas:
                                tarifas[str(id_motorista)] = TARIFAS_PADRAO.copy()
                                save_tarifas(tarifas, empresa_id)
                        
                        motoristas_processados += 1
                        
                        # Salvar em lotes para evitar perda de dados
                        if motoristas_processados % BATCH_SIZE == 0:
                            save_motoristas(motoristas, empresa_id)
                            print(f"Lote salvo: {motoristas_processados} motoristas processados")
                        
                    except Exception as e:
                        motoristas_erro += 1
                        continue
                
            except Exception as e:
                return jsonify({'error': f'Erro ao processar Excel: {str(e)}'}), 500
        
        else:
            return jsonify({'error': 'Formato de arquivo não suportado para motoristas'}), 400
        
        # Salvar dados finais
        save_motoristas(motoristas, empresa_id)
        
        print(f"=== RESULTADO FINAL ===")
        print(f"Motoristas processados: {motoristas_processados}")
        print(f"Motoristas com erro: {motoristas_erro}")
        print(f"Total de motoristas no sistema: {len(motoristas)}")
        
        return jsonify({
            'success': True,
            'message': f'Planilha processada: {motoristas_processados} motoristas, {motoristas_erro} erros',
            'data': {
                'motoristas_processados': motoristas_processados,
                'motoristas_erro': motoristas_erro,
                'total_motoristas': len(motoristas)
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no upload de motoristas: {str(e)}")
        return jsonify({'error': f'Erro no upload: {str(e)}'}), 500

# ==================== API DE UPLOAD DE ENTREGAS ULTRA OTIMIZADA ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload de arquivo CSV/Excel de entregas - VERSÃO v7.2 ULTRA OTIMIZADA PARA 300K LINHAS"""
    try:
        empresa_id = 1
        
        print("=== INÍCIO UPLOAD ENTREGAS v7.2 ULTRA OTIMIZADO PARA 300K LINHAS ===")
        start_time = time.time()
        
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Carregar dados existentes UMA VEZ SÓ
        print("Carregando dados do sistema...")
        entregas = get_entregas(empresa_id)
        awbs = get_awbs(empresa_id)
        motoristas = get_motoristas(empresa_id)
        tarifas_cache = get_tarifas(empresa_id)  # CACHE GLOBAL
        
        # Criar dicionário de motoristas para busca rápida
        motoristas_dict = {m['id_motorista']: m for m in motoristas}
        print(f"Sistema carregado: {len(motoristas)} motoristas, {len(awbs)} AWBs existentes")
        
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
                        
                        # Adicionar à lista de entregas
                        entrega = {
                            'awb': awb,
                            'id_motorista': id_motorista,
                            'nome_motorista': motoristas_dict[id_motorista]['nome_motorista'],
                            'tipo_servico': tipo_servico,
                            'data_entrega': data_entrega,
                            'valor_entrega': valor_entrega,
                            'status': 'NAO_PAGA',
                            'created_at': datetime.now().isoformat()
                        }
                        entregas.append(entrega)
                        entregas_processadas += 1
                        
                    except Exception as e:
                        entregas_erro += 1
                        continue
                
                # SALVAR LOTE PARA EVITAR PERDA DE DADOS
                save_awbs(awbs, empresa_id)
                save_entregas(entregas, empresa_id)
                
                lote_tempo = time.time() - lote_inicio
                progresso = ((i + len(lote)) / total_linhas) * 100
                print(f"Lote {i//BATCH_SIZE + 1}: {len(lote)} linhas em {lote_tempo:.2f}s - Progresso: {progresso:.1f}%")
            
        except Exception as e:
            return jsonify({'error': f'Erro ao processar CSV: {str(e)}'}), 500
        
        # Salvar dados finais
        save_awbs(awbs, empresa_id)
        save_entregas(entregas, empresa_id)
        
        tempo_total = time.time() - start_time
        
        print(f"=== RESULTADO FINAL ===")
        print(f"Tempo total: {tempo_total:.2f} segundos")
        print(f"Entregas processadas: {entregas_processadas}")
        print(f"Entregas com erro: {entregas_erro}")
        print(f"AWBs novas: {awbs_novas}")
        print(f"Total de AWBs no sistema: {len(awbs)}")
        print(f"Performance: {entregas_processadas/tempo_total:.0f} linhas/segundo")
        
        return jsonify({
            'success': True,
            'message': f'Arquivo processado em {tempo_total:.1f}s: {entregas_processadas} entregas, {entregas_erro} erros',
            'data': {
                'entregas_processadas': entregas_processadas,
                'entregas_erro': entregas_erro,
                'awbs_novas': awbs_novas,
                'total_awbs': len(awbs),
                'tempo_processamento': tempo_total,
                'performance_linhas_por_segundo': round(entregas_processadas/tempo_total) if tempo_total > 0 else 0
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro no upload: {str(e)}")
        return jsonify({'error': f'Erro no upload: {str(e)}'}), 500

# ==================== DEMAIS APIs MANTIDAS ====================

@app.route('/api/prestadores', methods=['GET'])
def get_prestadores_api():
    """Lista todos os prestadores"""
    try:
        empresa_id = 1
        prestadores = get_prestadores(empresa_id)
        
        return jsonify({
            'success': True,
            'data': prestadores,
            'total': len(prestadores)
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar prestadores: {str(e)}")
        return jsonify({'error': f'Erro ao buscar prestadores: {str(e)}'}), 500

@app.route('/api/prestadores', methods=['POST'])
def create_prestador():
    """Criar novo prestador/grupo"""
    try:
        empresa_id = 1
        data = request.get_json()
        
        if not data or not data.get('nome_prestador') or not data.get('motorista_principal'):
            return jsonify({'error': 'Dados obrigatórios não fornecidos'}), 400
        
        # Carregar dados
        prestadores = get_prestadores(empresa_id)
        motoristas = get_motoristas(empresa_id)
        
        # Verificar se motorista principal existe
        motorista_principal = None
        for m in motoristas:
            if m['id_motorista'] == data['motorista_principal']:
                motorista_principal = m
                break
        
        if not motorista_principal:
            return jsonify({'error': 'Motorista principal não encontrado'}), 400
        
        # Verificar se já existe prestador com este motorista principal
        for p in prestadores:
            if p['motorista_principal'] == data['motorista_principal']:
                return jsonify({'error': 'Já existe um prestador com este motorista principal'}), 400
        
        # Criar prestador
        prestador_id = len(prestadores) + 1
        prestador = {
            'id': prestador_id,
            'motorista_principal': data['motorista_principal'],
            'nome_prestador': data['nome_prestador'],
            'motoristas_ajudantes': data.get('motoristas_ajudantes', []),
            'observacoes': data.get('observacoes', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        prestadores.append(prestador)
        
        # SALVAR PERMANENTEMENTE
        save_prestadores(prestadores, empresa_id)
        
        return jsonify({
            'success': True,
            'message': 'Prestador criado e salvo permanentemente',
            'data': prestador
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao criar prestador: {str(e)}")
        return jsonify({'error': f'Erro ao criar prestador: {str(e)}'}), 500

@app.route('/api/prestadores/<int:prestador_id>', methods=['DELETE'])
def delete_prestador(prestador_id):
    """Excluir prestador"""
    try:
        empresa_id = 1
        prestadores = get_prestadores(empresa_id)
        
        # Encontrar e remover prestador
        prestador_removido = None
        for i, p in enumerate(prestadores):
            if p['id'] == prestador_id:
                prestador_removido = prestadores.pop(i)
                break
        
        if not prestador_removido:
            return jsonify({'error': 'Prestador não encontrado'}), 404
        
        # Salvar dados atualizados
        save_prestadores(prestadores, empresa_id)
        
        return jsonify({
            'success': True,
            'message': 'Prestador excluído com sucesso'
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao excluir prestador: {str(e)}")
        return jsonify({'error': f'Erro ao excluir prestador: {str(e)}'}), 500

@app.route('/api/prestadores/estatisticas', methods=['GET'])
def get_prestadores_estatisticas():
    """Estatísticas dos prestadores"""
    try:
        empresa_id = 1
        
        # Carregar dados
        prestadores = get_prestadores(empresa_id)
        motoristas = get_motoristas(empresa_id)
        
        # Calcular estatísticas
        total_motoristas = len(motoristas)
        total_prestadores = len(prestadores)
        
        # Contar motoristas em grupos
        motoristas_em_grupos = set()
        for prestador in prestadores:
            motoristas_em_grupos.add(prestador['motorista_principal'])
            for ajudante in prestador.get('motoristas_ajudantes', []):
                motoristas_em_grupos.add(ajudante)
        
        motoristas_em_grupos_count = len(motoristas_em_grupos)
        motoristas_individuais = total_motoristas - motoristas_em_grupos_count
        
        return jsonify({
            'success': True,
            'data': {
                'total_motoristas': total_motoristas,
                'total_prestadores': total_prestadores,
                'motoristas_em_grupos': motoristas_em_grupos_count,
                'motoristas_individuais': motoristas_individuais
            }
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return jsonify({'error': f'Erro ao buscar estatísticas: {str(e)}'}), 500

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    print("🚀 MenezesLog SaaS v7.2 ULTRA OTIMIZADO iniciado!")
    print("🇧🇷 Suporte completo a encoding brasileiro")
    print("⚡ Otimizado para processar 300K linhas sem timeout")
    print("💾 Sistema de persistência em arquivos JSON")
    print("🎯 Cache inteligente para máxima performance")
    app.run(host='0.0.0.0', port=5000, debug=False)

