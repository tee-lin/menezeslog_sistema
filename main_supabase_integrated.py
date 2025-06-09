# MenezesLog SaaS - Sistema Completo DEFINITIVO
# Versão 6.2.0 - TODAS AS APIs IMPLEMENTADAS
# Data: 2025-06-09

import os
import sys
import datetime
import json
import csv
import io
import uuid
from flask import Flask, jsonify, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import openpyxl
from openpyxl import load_workbook

# Configurar caminhos de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar aplicação Flask
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

# ==================== BANCO DE DADOS EM MEMÓRIA ====================

# Estrutura do banco de dados SaaS
empresas_db = {}  # {empresa_id: {nome, ciclo_pagamento, config}}
motoristas_db = {}  # {empresa_id: [motoristas]}
tarifas_db = {}  # {empresa_id: {id_motorista: {tipo_servico: valor}}}
prestadores_db = {}  # {empresa_id: [prestadores]}

# Tabela principal de AWBs - USANDO DATA DE ENTREGA
awbs_db = {}  # {awb: {dados_completos, empresa_id, status, ciclo_pagamento_id, data_entrega_real}}

# Tabela de ciclos de pagamento
ciclos_pagamento_db = {}  # {ciclo_id: {empresa_id, periodo, data_inicio, data_fim, status, awbs}}

# Tabela de uploads
uploads_db = {}  # {empresa_id: [uploads]}

# Empresa padrão para desenvolvimento
EMPRESA_DEFAULT = 'menezeslog_default'

# Tarifas padrão por tipo de serviço
TARIFAS_PADRAO = {
    0: 3.50,  # Encomendas
    9: 2.00,  # Cards
    6: 0.50,  # Revistas
    8: 0.50   # Revistas
}

# ==================== FUNÇÕES AUXILIARES ====================

def get_empresa_id():
    """Retorna ID da empresa (por enquanto usa padrão)"""
    return EMPRESA_DEFAULT

def inicializar_empresa(empresa_id):
    """Inicializa estruturas para uma empresa"""
    if empresa_id not in empresas_db:
        empresas_db[empresa_id] = {
            'nome': 'MenezesLog',
            'ciclo_pagamento': 'mensal',  # semanal, quinzenal, mensal
            'config': {
                'dia_fechamento': 15,  # Dia do mês para fechamento mensal
                'dia_semana_fechamento': 5,  # Sexta-feira para semanal
                'auto_fechar': False
            },
            'created_at': datetime.datetime.now().isoformat()
        }
    
    if empresa_id not in motoristas_db:
        motoristas_db[empresa_id] = []
    
    if empresa_id not in tarifas_db:
        tarifas_db[empresa_id] = {}
    
    if empresa_id not in prestadores_db:
        prestadores_db[empresa_id] = []
    
    if empresa_id not in uploads_db:
        uploads_db[empresa_id] = []

def get_tarifa_motorista(empresa_id, id_motorista, tipo_servico):
    """Retorna a tarifa específica do motorista ou a padrão"""
    if (empresa_id in tarifas_db and 
        id_motorista in tarifas_db[empresa_id] and 
        tipo_servico in tarifas_db[empresa_id][id_motorista]):
        return tarifas_db[empresa_id][id_motorista][tipo_servico]
    return TARIFAS_PADRAO.get(tipo_servico, 0.0)

def gerar_ciclo_id():
    """Gera ID único para ciclo de pagamento"""
    return str(uuid.uuid4())

def parse_data_entrega(data_str):
    """Converte string de data/hora para datetime"""
    if not data_str:
        return None
    
    # Formatos comuns de data/hora
    formatos = [
        '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d'
    ]
    
    for formato in formatos:
        try:
            return datetime.datetime.strptime(str(data_str).strip(), formato)
        except ValueError:
            continue
    
    app.logger.warning(f"Formato de data não reconhecido: {data_str}")
    return None

def calcular_periodo_ciclo(empresa_id, data_referencia=None):
    """Calcula período do ciclo baseado na configuração da empresa"""
    if data_referencia is None:
        data_referencia = datetime.datetime.now()
    
    empresa = empresas_db.get(empresa_id, {})
    ciclo = empresa.get('ciclo_pagamento', 'mensal')
    config = empresa.get('config', {})
    
    if ciclo == 'semanal':
        # Semana de segunda a domingo
        inicio_semana = data_referencia - datetime.timedelta(days=data_referencia.weekday())
        data_inicio = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = data_inicio + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        
    elif ciclo == 'quinzenal':
        # Primeira ou segunda quinzena do mês
        if data_referencia.day <= 15:
            data_inicio = data_referencia.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            data_fim = data_referencia.replace(day=15, hour=23, minute=59, second=59, microsecond=999999)
        else:
            data_inicio = data_referencia.replace(day=16, hour=0, minute=0, second=0, microsecond=0)
            # Último dia do mês
            if data_referencia.month == 12:
                proximo_mes = data_referencia.replace(year=data_referencia.year + 1, month=1, day=1)
            else:
                proximo_mes = data_referencia.replace(month=data_referencia.month + 1, day=1)
            data_fim = proximo_mes - datetime.timedelta(microseconds=1)
    
    else:  # mensal
        data_inicio = data_referencia.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Último dia do mês
        if data_referencia.month == 12:
            proximo_mes = data_referencia.replace(year=data_referencia.year + 1, month=1, day=1)
        else:
            proximo_mes = data_referencia.replace(month=data_referencia.month + 1, day=1)
        data_fim = proximo_mes - datetime.timedelta(microseconds=1)
    
    return data_inicio, data_fim

def processar_csv_entregas_com_awb(file_content, empresa_id):
    """Processa CSV de entregas com controle de AWBs únicos - USANDO DATA/HORA DA ENTREGA"""
    try:
        app.logger.info(f"Processando CSV para empresa {empresa_id}")
        
        # Ler CSV
        csv_reader = csv.DictReader(io.StringIO(file_content))
        entregas = list(csv_reader)
        
        app.logger.info(f"CSV carregado com {len(entregas)} linhas")
        
        # Estatísticas
        total_linhas = len(entregas)
        awbs_novas = 0
        awbs_duplicadas = 0
        awbs_ja_pagas = 0
        entregas_com_erro = 0
        
        for i, entrega in enumerate(entregas):
            try:
                # Extrair AWB
                awb = None
                for col in ['AWB', 'awb', 'Awb', 'codigo', 'codigo_rastreio']:
                    if col in entrega and entrega[col]:
                        awb = str(entrega[col]).strip()
                        break
                
                if not awb:
                    entregas_com_erro += 1
                    if i < 5:
                        app.logger.warning(f"Linha {i+1}: AWB não encontrado")
                    continue

                # EXTRAIR DATA/HORA DA ENTREGA - CAMPO PRINCIPAL
                data_entrega_real = None
                for col in ['data_entrega', 'data/hora', 'data_hora', 'data', 'hora_entrega', 'timestamp']:
                    if col in entrega and entrega[col]:
                        data_entrega_real = parse_data_entrega(entrega[col])
                        if data_entrega_real:
                            break
                
                if not data_entrega_real:
                    entregas_com_erro += 1
                    if i < 5:
                        app.logger.warning(f"Linha {i+1}: Data/hora da entrega não encontrada ou inválida")
                    continue

                # Verificar se AWB já existe
                if awb in awbs_db:
                    awb_existente = awbs_db[awb]
                    
                    # Se já foi paga, ignorar
                    if awb_existente.get('status') == 'PAGA':
                        awbs_ja_pagas += 1
                        continue
                    
                    # Se é duplicata da mesma empresa, ignorar
                    if awb_existente.get('empresa_id') == empresa_id:
                        awbs_duplicadas += 1
                        continue
                
                # Extrair outros dados
                id_motorista = None
                tipo_servico = None
                
                # Buscar ID do motorista
                for col in ['id_motorista', 'ID do motorista', 'motorista_id', 'id motorista']:
                    if col in entrega and entrega[col]:
                        try:
                            id_motorista = int(entrega[col])
                            break
                        except ValueError:
                            continue
                
                # Buscar tipo de serviço
                for col in ['tipo de serviço', 'tipo_servico', 'tipo servico', 'tipo']:
                    if col in entrega and entrega[col]:
                        try:
                            tipo_servico = int(entrega[col])
                            break
                        except ValueError:
                            continue
                
                if id_motorista is None or tipo_servico is None:
                    entregas_com_erro += 1
                    if i < 5:
                        app.logger.warning(f"Linha {i+1}: ID motorista={id_motorista}, Tipo serviço={tipo_servico}")
                    continue
                
                # Buscar tarifa específica do motorista
                tarifa = get_tarifa_motorista(empresa_id, id_motorista, tipo_servico)
                
                # Criar registro da AWB - COM DATA DE ENTREGA REAL
                awb_data = {
                    'awb': awb,
                    'empresa_id': empresa_id,
                    'id_motorista': id_motorista,
                    'tipo_servico': tipo_servico,
                    'tarifa': tarifa,
                    'valor_pagamento': tarifa,
                    'status': 'NAO_PAGA',
                    'ciclo_pagamento_id': None,
                    'data_entrega_real': data_entrega_real.isoformat(),  # DATA PRINCIPAL
                    'endereco': entrega.get('endereco', ''),
                    'dados_originais': entrega,
                    'created_at': datetime.datetime.now().isoformat(),
                    'updated_at': datetime.datetime.now().isoformat()
                }
                
                # Salvar AWB
                awbs_db[awb] = awb_data
                awbs_novas += 1
                
            except Exception as e:
                entregas_com_erro += 1
                if i < 5:
                    app.logger.warning(f"Erro ao processar linha {i+1}: {e}")
                continue
        
        app.logger.info(f"Processamento concluído: {awbs_novas} AWBs novas, {awbs_duplicadas} duplicadas, {awbs_ja_pagas} já pagas, {entregas_com_erro} com erro")
        
        return {
            'total_linhas': total_linhas,
            'awbs_novas': awbs_novas,
            'awbs_duplicadas': awbs_duplicadas,
            'awbs_ja_pagas': awbs_ja_pagas,
            'entregas_com_erro': entregas_com_erro,
            'sucesso': awbs_novas > 0
        }
        
    except Exception as e:
        app.logger.error(f"Erro ao processar CSV: {e}")
        raise

def processar_planilha_motoristas(file_path, file_extension, empresa_id):
    """Processa planilha DE-PARA de motoristas"""
    try:
        app.logger.info(f"Processando planilha de motoristas para empresa {empresa_id}: {file_extension}")
        motoristas = []
        
        if file_extension.lower() == '.csv':
            # Processar CSV
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for i, row in enumerate(csv_reader):
                    try:
                        # Tentar diferentes nomes de colunas
                        id_motorista = None
                        nome_motorista = None
                        
                        # Buscar ID
                        for col in ['ID do motorista', 'id_motorista', 'motorista_id', 'id motorista', 'ID']:
                            if col in row and row[col]:
                                try:
                                    id_motorista = int(row[col])
                                    break
                                except ValueError:
                                    continue
                        
                        # Buscar nome
                        for col in ['Nome do motorista', 'nome_motorista', 'motorista_nome', 'nome motorista', 'Nome', 'nome']:
                            if col in row and row[col]:
                                nome_motorista = str(row[col]).strip()
                                if nome_motorista:
                                    break
                        
                        if id_motorista and nome_motorista:
                            motoristas.append({
                                'id_motorista': id_motorista,
                                'nome_motorista': nome_motorista,
                                'empresa_id': empresa_id,
                                'ativo': True,
                                'created_at': datetime.datetime.now().isoformat(),
                                'updated_at': datetime.datetime.now().isoformat()
                            })
                        else:
                            if i < 5:
                                app.logger.warning(f"Linha {i+1}: ID={id_motorista}, Nome='{nome_motorista}'")
                            
                    except Exception as e:
                        if i < 5:
                            app.logger.warning(f"Erro ao processar linha {i+1}: {e}")
                        continue
        
        elif file_extension.lower() in ['.xlsx', '.xls']:
            # Processar Excel
            workbook = load_workbook(file_path)
            sheet = workbook.active
            
            # Encontrar cabeçalhos
            headers = {}
            for col in range(1, sheet.max_column + 1):
                cell_value = sheet.cell(row=1, column=col).value
                if cell_value:
                    cell_value = str(cell_value).strip().lower()
                    if 'id' in cell_value and 'motorista' in cell_value:
                        headers['id'] = col
                    elif 'nome' in cell_value and 'motorista' in cell_value:
                        headers['nome'] = col
            
            app.logger.info(f"Headers encontrados: {headers}")
            
            # Processar linhas
            for row in range(2, sheet.max_row + 1):
                try:
                    if 'id' in headers and 'nome' in headers:
                        id_cell = sheet.cell(row=row, column=headers['id']).value
                        nome_cell = sheet.cell(row=row, column=headers['nome']).value
                        
                        if id_cell and nome_cell:
                            id_motorista = int(id_cell)
                            nome_motorista = str(nome_cell).strip()
                            
                            if id_motorista and nome_motorista:
                                motoristas.append({
                                    'id_motorista': id_motorista,
                                    'nome_motorista': nome_motorista,
                                    'empresa_id': empresa_id,
                                    'ativo': True,
                                    'created_at': datetime.datetime.now().isoformat(),
                                    'updated_at': datetime.datetime.now().isoformat()
                                })
                    
                except Exception as e:
                    if row < 7:
                        app.logger.warning(f"Erro ao processar linha {row}: {e}")
                    continue
        
        app.logger.info(f"Processados {len(motoristas)} motoristas válidos")
        return motoristas
        
    except Exception as e:
        app.logger.error(f"Erro ao processar planilha: {e}")
        raise

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página principal"""
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

# ==================== APIs DE EMPRESA ====================

@app.route('/api/empresa/config', methods=['GET'])
def get_empresa_config():
    """Configuração da empresa"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        return jsonify({
            'success': True,
            'data': empresas_db[empresa_id]
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar configuração: {str(e)}'}), 500

@app.route('/api/empresa/config', methods=['PUT'])
def update_empresa_config():
    """Atualizar configuração da empresa"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        
        # Validar ciclo de pagamento
        ciclos_validos = ['semanal', 'quinzenal', 'mensal']
        if data.get('ciclo_pagamento') not in ciclos_validos:
            return jsonify({'error': 'Ciclo de pagamento inválido'}), 400
        
        # Atualizar configuração
        empresas_db[empresa_id].update({
            'ciclo_pagamento': data.get('ciclo_pagamento', empresas_db[empresa_id]['ciclo_pagamento']),
            'config': {
                **empresas_db[empresa_id]['config'],
                **data.get('config', {})
            },
            'updated_at': datetime.datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Configuração atualizada com sucesso!',
            'data': empresas_db[empresa_id]
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ==================== APIs DE UPLOAD ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload e processamento de arquivos CSV de entregas com controle de AWBs"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
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
            # Salvar arquivo temporariamente
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            # Ler conteúdo do arquivo
            if file_ext == '.csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            else:
                # Para Excel, converter para CSV primeiro
                workbook = load_workbook(file_path)
                sheet = workbook.active
                
                # Converter para CSV em memória
                csv_content = []
                for row in sheet.iter_rows(values_only=True):
                    csv_content.append(','.join([str(cell) if cell is not None else '' for cell in row]))
                file_content = '\n'.join(csv_content)
            
            # Processar CSV de entregas com controle de AWBs
            resultado = processar_csv_entregas_com_awb(file_content, empresa_id)
            
            # Limpar arquivo temporário
            os.remove(file_path)
            
            # Salvar no histórico
            upload_data = {
                'id': len(uploads_db[empresa_id]) + 1,
                'filename': file.filename,
                'empresa_id': empresa_id,
                'total_linhas': resultado['total_linhas'],
                'awbs_novas': resultado['awbs_novas'],
                'awbs_duplicadas': resultado['awbs_duplicadas'],
                'awbs_ja_pagas': resultado['awbs_ja_pagas'],
                'entregas_com_erro': resultado['entregas_com_erro'],
                'status': 'processado' if resultado['sucesso'] else 'erro',
                'created_at': datetime.datetime.now().isoformat(),
                'dados': resultado
            }
            uploads_db[empresa_id].append(upload_data)
            
            return jsonify({
                'success': True,
                'message': f'Arquivo processado! {resultado["awbs_novas"]} AWBs novas de {resultado["total_linhas"]} linhas.',
                'data': {
                    'total_linhas': resultado['total_linhas'],
                    'awbs_novas': resultado['awbs_novas'],
                    'awbs_duplicadas': resultado['awbs_duplicadas'],
                    'awbs_ja_pagas': resultado['awbs_ja_pagas'],
                    'entregas_com_erro': resultado['entregas_com_erro'],
                    'detalhes': f'✅ {resultado["awbs_novas"]} novas | 🔄 {resultado["awbs_duplicadas"]} duplicadas | 💰 {resultado["awbs_ja_pagas"]} já pagas | ❌ {resultado["entregas_com_erro"]} com erro'
                }
            })
            
        except Exception as e:
            # Limpar arquivo em caso de erro
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/upload/history', methods=['GET'])
def upload_history():
    """Histórico de uploads"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        uploads = uploads_db[empresa_id]
        
        return jsonify({
            'success': True,
            'data': uploads[-limit:] if uploads else [],
            'pagination': {'page': page, 'limit': limit, 'total': len(uploads)}
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar histórico: {str(e)}'}), 500

# ==================== APIs DE AWBs ====================

@app.route('/api/awbs', methods=['GET'])
def get_awbs():
    """Lista AWBs com filtros - USANDO DATA DE ENTREGA"""
    try:
        empresa_id = get_empresa_id()
        status = request.args.get('status', '')  # NAO_PAGA, PAGA
        motorista_id = request.args.get('motorista_id', '')
        data_inicio = request.args.get('data_inicio', '')  # NOVO: Filtro por data de entrega
        data_fim = request.args.get('data_fim', '')  # NOVO: Filtro por data de entrega
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        # Filtrar AWBs da empresa
        awbs_empresa = []
        for awb, dados in awbs_db.items():
            if dados.get('empresa_id') == empresa_id:
                if status and dados.get('status') != status:
                    continue
                if motorista_id and str(dados.get('id_motorista')) != motorista_id:
                    continue
                
                # FILTRO POR DATA DE ENTREGA
                if data_inicio or data_fim:
                    data_entrega_str = dados.get('data_entrega_real')
                    if data_entrega_str:
                        try:
                            data_entrega = datetime.datetime.fromisoformat(data_entrega_str)
                            
                            if data_inicio:
                                data_inicio_dt = datetime.datetime.fromisoformat(data_inicio)
                                if data_entrega < data_inicio_dt:
                                    continue
                            
                            if data_fim:
                                data_fim_dt = datetime.datetime.fromisoformat(data_fim)
                                if data_entrega > data_fim_dt:
                                    continue
                        except:
                            continue
                
                awbs_empresa.append(dados)
        
        # Ordenar por data de entrega (mais recentes primeiro)
        awbs_empresa.sort(key=lambda x: x.get('data_entrega_real', ''), reverse=True)
        
        # Paginação
        start = (page - 1) * limit
        end = start + limit
        awbs_pagina = awbs_empresa[start:end]
        
        return jsonify({
            'success': True,
            'data': awbs_pagina,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(awbs_empresa),
                'pages': (len(awbs_empresa) + limit - 1) // limit
            },
            'estatisticas': {
                'total_awbs': len(awbs_empresa),
                'nao_pagas': len([a for a in awbs_empresa if a.get('status') == 'NAO_PAGA']),
                'pagas': len([a for a in awbs_empresa if a.get('status') == 'PAGA'])
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar AWBs: {str(e)}'}), 500

@app.route('/api/awbs/estatisticas', methods=['GET'])
def get_awbs_estatisticas():
    """Estatísticas das AWBs"""
    try:
        empresa_id = get_empresa_id()
        
        # Contar AWBs da empresa
        total_awbs = 0
        awbs_nao_pagas = 0
        awbs_pagas = 0
        valor_total_nao_pago = 0.0
        valor_total_pago = 0.0
        
        for awb, dados in awbs_db.items():
            if dados.get('empresa_id') == empresa_id:
                total_awbs += 1
                valor = dados.get('valor_pagamento', 0.0)
                
                if dados.get('status') == 'NAO_PAGA':
                    awbs_nao_pagas += 1
                    valor_total_nao_pago += valor
                elif dados.get('status') == 'PAGA':
                    awbs_pagas += 1
                    valor_total_pago += valor
        
        return jsonify({
            'success': True,
            'data': {
                'total_awbs': total_awbs,
                'awbs_nao_pagas': awbs_nao_pagas,
                'awbs_pagas': awbs_pagas,
                'valor_total_nao_pago': valor_total_nao_pago,
                'valor_total_pago': valor_total_pago,
                'percentual_pagas': (awbs_pagas / max(total_awbs, 1)) * 100
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao calcular estatísticas: {str(e)}'}), 500

# ==================== APIs DE CICLOS DE PAGAMENTO ====================

@app.route('/api/ciclos', methods=['GET'])
def get_ciclos_pagamento():
    """Lista ciclos de pagamento"""
    try:
        empresa_id = get_empresa_id()
        
        # Filtrar ciclos da empresa
        ciclos_empresa = []
        for ciclo_id, dados in ciclos_pagamento_db.items():
            if dados.get('empresa_id') == empresa_id:
                ciclos_empresa.append({
                    'ciclo_id': ciclo_id,
                    **dados
                })
        
        # Ordenar por data de criação (mais recentes primeiro)
        ciclos_empresa.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'data': ciclos_empresa,
            'total': len(ciclos_empresa)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar ciclos: {str(e)}'}), 500

@app.route('/api/ciclos/gerar', methods=['POST'])
def gerar_ciclo_pagamento():
    """Gera novo ciclo de pagamento com AWBs não pagas do período - BASEADO NA DATA DE ENTREGA"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        data_referencia = data.get('data_referencia')
        
        if data_referencia:
            data_ref = datetime.datetime.fromisoformat(data_referencia)
        else:
            data_ref = datetime.datetime.now()
        
        # Calcular período do ciclo
        data_inicio, data_fim = calcular_periodo_ciclo(empresa_id, data_ref)
        
        # Buscar AWBs não pagas da empresa NO PERÍODO DE ENTREGA
        awbs_periodo = []
        valor_total = 0.0
        
        for awb, dados in awbs_db.items():
            if (dados.get('empresa_id') == empresa_id and 
                dados.get('status') == 'NAO_PAGA'):
                
                # VERIFICAR SE A DATA DE ENTREGA ESTÁ NO PERÍODO
                data_entrega_str = dados.get('data_entrega_real')
                if data_entrega_str:
                    try:
                        data_entrega = datetime.datetime.fromisoformat(data_entrega_str)
                        
                        # Verificar se está no período do ciclo
                        if data_inicio <= data_entrega <= data_fim:
                            awbs_periodo.append(awb)
                            valor_total += dados.get('valor_pagamento', 0.0)
                    except:
                        continue
        
        if not awbs_periodo:
            return jsonify({'error': f'Nenhuma AWB não paga encontrada para o período de {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}'}), 400
        
        # Criar ciclo de pagamento
        ciclo_id = gerar_ciclo_id()
        ciclo_data = {
            'ciclo_id': ciclo_id,
            'empresa_id': empresa_id,
            'periodo': empresas_db[empresa_id]['ciclo_pagamento'],
            'data_inicio': data_inicio.isoformat(),
            'data_fim': data_fim.isoformat(),
            'status': 'ABERTO',
            'awbs': awbs_periodo,
            'total_awbs': len(awbs_periodo),
            'valor_total': valor_total,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        ciclos_pagamento_db[ciclo_id] = ciclo_data
        
        # Associar AWBs ao ciclo (mas ainda não marcar como pagas)
        for awb in awbs_periodo:
            if awb in awbs_db:
                awbs_db[awb]['ciclo_pagamento_id'] = ciclo_id
                awbs_db[awb]['updated_at'] = datetime.datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': f'Ciclo de pagamento gerado com {len(awbs_periodo)} AWBs do período {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}!',
            'data': ciclo_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/ciclos/<ciclo_id>/fechar', methods=['POST'])
def fechar_ciclo_pagamento(ciclo_id):
    """Fecha ciclo de pagamento e marca AWBs como pagas"""
    try:
        if ciclo_id not in ciclos_pagamento_db:
            return jsonify({'error': 'Ciclo não encontrado'}), 404
        
        ciclo = ciclos_pagamento_db[ciclo_id]
        
        if ciclo['status'] != 'ABERTO':
            return jsonify({'error': 'Ciclo já foi fechado'}), 400
        
        # Marcar AWBs como pagas
        awbs_fechadas = 0
        for awb in ciclo['awbs']:
            if awb in awbs_db and awbs_db[awb]['status'] == 'NAO_PAGA':
                awbs_db[awb]['status'] = 'PAGA'
                awbs_db[awb]['data_pagamento'] = datetime.datetime.now().isoformat()
                awbs_db[awb]['updated_at'] = datetime.datetime.now().isoformat()
                awbs_fechadas += 1
        
        # Fechar ciclo
        ciclo['status'] = 'FECHADO'
        ciclo['data_fechamento'] = datetime.datetime.now().isoformat()
        ciclo['awbs_fechadas'] = awbs_fechadas
        ciclo['updated_at'] = datetime.datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': f'Ciclo fechado! {awbs_fechadas} AWBs marcadas como pagas.',
            'data': ciclo
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/ciclos/<ciclo_id>', methods=['GET'])
def get_ciclo_detalhes(ciclo_id):
    """Detalhes de um ciclo específico"""
    try:
        if ciclo_id not in ciclos_pagamento_db:
            return jsonify({'error': 'Ciclo não encontrado'}), 404
        
        ciclo = ciclos_pagamento_db[ciclo_id]
        
        # Buscar detalhes das AWBs do ciclo
        awbs_detalhes = []
        pagamentos_por_motorista = {}
        
        for awb in ciclo['awbs']:
            if awb in awbs_db:
                awb_data = awbs_db[awb]
                awbs_detalhes.append(awb_data)
                
                # Agrupar por motorista
                id_motorista = awb_data['id_motorista']
                if id_motorista not in pagamentos_por_motorista:
                    pagamentos_por_motorista[id_motorista] = {
                        'id_motorista': id_motorista,
                        'total_awbs': 0,
                        'valor_total': 0.0,
                        'awbs': []
                    }
                
                pagamentos_por_motorista[id_motorista]['total_awbs'] += 1
                pagamentos_por_motorista[id_motorista]['valor_total'] += awb_data['valor_pagamento']
                pagamentos_por_motorista[id_motorista]['awbs'].append(awb)
        
        return jsonify({
            'success': True,
            'data': {
                'ciclo': ciclo,
                'awbs_detalhes': awbs_detalhes,
                'pagamentos_por_motorista': list(pagamentos_por_motorista.values())
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ==================== APIs DE MOTORISTAS ====================

@app.route('/api/motoristas/upload', methods=['POST'])
def upload_motoristas():
    """Upload da planilha DE-PARA de motoristas"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
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
            # Salvar arquivo temporariamente
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(file_path)
            
            # Processar planilha
            motoristas_novos = processar_planilha_motoristas(file_path, file_ext, empresa_id)
            
            # Limpar arquivo temporário
            os.remove(file_path)
            
            if not motoristas_novos:
                return jsonify({'error': 'Nenhum motorista válido encontrado na planilha. Verifique se as colunas estão nomeadas corretamente.'}), 400
            
            # Atualizar banco de dados
            motoristas_db[empresa_id] = motoristas_novos.copy()
            
            app.logger.info(f"Processados {len(motoristas_db[empresa_id])} motoristas")
            
            return jsonify({
                'success': True,
                'message': f'Planilha DE-PARA processada com sucesso! {len(motoristas_db[empresa_id])} motoristas cadastrados.',
                'data': {
                    'total_motoristas': len(motoristas_db[empresa_id]),
                    'arquivo': file.filename,
                    'amostra': motoristas_db[empresa_id][:3]
                }
            })
            
        except Exception as e:
            # Limpar arquivo em caso de erro
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            app.logger.error(f"Erro ao processar planilha: {e}")
            return jsonify({'error': f'Erro ao processar planilha: {str(e)}'}), 500
            
    except Exception as e:
        app.logger.error(f"Erro interno upload motoristas: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/motoristas', methods=['GET'])
def get_motoristas():
    """Lista todos os motoristas"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        return jsonify({
            'success': True,
            'data': motoristas_db[empresa_id],
            'total': len(motoristas_db[empresa_id])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar motoristas: {str(e)}'}), 500

# ==================== APIs DE PRESTADORES ====================

@app.route('/api/prestadores', methods=['GET'])
def get_prestadores():
    """Lista todos os prestadores"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        return jsonify({
            'success': True,
            'data': prestadores_db[empresa_id],
            'total': len(prestadores_db[empresa_id])
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar prestadores: {str(e)}'}), 500

@app.route('/api/prestadores', methods=['POST'])
def create_prestador():
    """Criar novo prestador/grupo"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('nome_prestador'):
            return jsonify({'error': 'Nome do prestador é obrigatório'}), 400
        
        if not data.get('motorista_principal'):
            return jsonify({'error': 'Motorista principal é obrigatório'}), 400
        
        # Verificar se motorista principal existe
        motorista_principal = None
        for motorista in motoristas_db[empresa_id]:
            if motorista['id_motorista'] == data['motorista_principal']:
                motorista_principal = motorista
                break
        
        if not motorista_principal:
            return jsonify({'error': 'Motorista principal não encontrado'}), 400
        
        # Criar prestador
        prestador_id = len(prestadores_db[empresa_id]) + 1
        prestador = {
            'id': prestador_id,
            'nome_prestador': data['nome_prestador'],
            'motorista_principal': data['motorista_principal'],
            'motoristas_ajudantes': data.get('motoristas_ajudantes', []),
            'observacoes': data.get('observacoes', ''),
            'empresa_id': empresa_id,
            'ativo': True,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        prestadores_db[empresa_id].append(prestador)
        
        return jsonify({
            'success': True,
            'message': 'Prestador criado com sucesso!',
            'data': prestador
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/prestadores/<int:prestador_id>', methods=['PUT'])
def update_prestador(prestador_id):
    """Atualizar prestador"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        
        # Encontrar prestador
        prestador = None
        for p in prestadores_db[empresa_id]:
            if p['id'] == prestador_id:
                prestador = p
                break
        
        if not prestador:
            return jsonify({'error': 'Prestador não encontrado'}), 404
        
        # Atualizar dados
        prestador.update({
            'nome_prestador': data.get('nome_prestador', prestador['nome_prestador']),
            'motorista_principal': data.get('motorista_principal', prestador['motorista_principal']),
            'motoristas_ajudantes': data.get('motoristas_ajudantes', prestador['motoristas_ajudantes']),
            'observacoes': data.get('observacoes', prestador['observacoes']),
            'ativo': data.get('ativo', prestador['ativo']),
            'updated_at': datetime.datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Prestador atualizado com sucesso!',
            'data': prestador
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/prestadores/<int:prestador_id>', methods=['DELETE'])
def delete_prestador(prestador_id):
    """Deletar prestador"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        # Encontrar e remover prestador
        prestador_removido = None
        for i, p in enumerate(prestadores_db[empresa_id]):
            if p['id'] == prestador_id:
                prestador_removido = prestadores_db[empresa_id].pop(i)
                break
        
        if not prestador_removido:
            return jsonify({'error': 'Prestador não encontrado'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Prestador removido com sucesso!',
            'data': prestador_removido
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/prestadores/estatisticas', methods=['GET'])
def get_prestadores_estatisticas():
    """Estatísticas dos prestadores"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        total_prestadores = len(prestadores_db[empresa_id])
        total_motoristas = len(motoristas_db[empresa_id])
        
        # Contar motoristas em grupos
        motoristas_em_grupos = set()
        for prestador in prestadores_db[empresa_id]:
            if prestador.get('ativo', True):
                motoristas_em_grupos.add(prestador['motorista_principal'])
                for ajudante in prestador.get('motoristas_ajudantes', []):
                    motoristas_em_grupos.add(ajudante)
        
        motoristas_individuais = total_motoristas - len(motoristas_em_grupos)
        
        return jsonify({
            'success': True,
            'data': {
                'total_prestadores': total_prestadores,
                'total_motoristas': total_motoristas,
                'motoristas_em_grupos': len(motoristas_em_grupos),
                'motoristas_individuais': motoristas_individuais
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao calcular estatísticas: {str(e)}'}), 500

# ==================== APIs DE TARIFAS ====================

@app.route('/api/tarifas', methods=['GET'])
def get_tarifas():
    """Lista tarifas personalizadas"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        # Organizar tarifas por motorista
        tarifas_organizadas = []
        
        for motorista in motoristas_db[empresa_id]:
            id_motorista = motorista['id_motorista']
            nome_motorista = motorista['nome_motorista']
            
            # Buscar tarifas personalizadas
            tarifas_motorista = tarifas_db[empresa_id].get(id_motorista, {})
            
            # Criar objeto com tarifas (personalizadas ou padrão)
            tarifa_data = {
                'id_motorista': id_motorista,
                'nome_motorista': nome_motorista,
                'tarifas': {
                    0: tarifas_motorista.get(0, TARIFAS_PADRAO[0]),  # Encomendas
                    9: tarifas_motorista.get(9, TARIFAS_PADRAO[9]),  # Cards
                    6: tarifas_motorista.get(6, TARIFAS_PADRAO[6]),  # Revistas
                    8: tarifas_motorista.get(8, TARIFAS_PADRAO[8])   # Revistas
                },
                'tem_personalizacao': len(tarifas_motorista) > 0,
                'grupo': 'Personalizado' if len(tarifas_motorista) > 0 else 'Padrão'
            }
            
            # Determinar se é Premium (todas as tarifas acima do padrão)
            if len(tarifas_motorista) > 0:
                todas_acima = all(
                    tarifas_motorista.get(tipo, TARIFAS_PADRAO[tipo]) > TARIFAS_PADRAO[tipo]
                    for tipo in [0, 9, 6, 8]
                    if tipo in tarifas_motorista
                )
                if todas_acima:
                    tarifa_data['grupo'] = 'Premium'
            
            tarifas_organizadas.append(tarifa_data)
        
        return jsonify({
            'success': True,
            'data': tarifas_organizadas,
            'tarifas_padrao': TARIFAS_PADRAO
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar tarifas: {str(e)}'}), 500

@app.route('/api/tarifas/grupos', methods=['GET'])
def get_tarifas_grupos():
    """Grupos de tarifas (Premium, Personalizado, Padrão)"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        grupos = {
            'Premium': [],
            'Personalizado': [],
            'Padrão': []
        }
        
        for motorista in motoristas_db[empresa_id]:
            id_motorista = motorista['id_motorista']
            nome_motorista = motorista['nome_motorista']
            
            # Buscar tarifas personalizadas
            tarifas_motorista = tarifas_db[empresa_id].get(id_motorista, {})
            
            if len(tarifas_motorista) == 0:
                grupos['Padrão'].append({'id_motorista': id_motorista, 'nome_motorista': nome_motorista})
            else:
                # Verificar se é Premium
                todas_acima = all(
                    tarifas_motorista.get(tipo, TARIFAS_PADRAO[tipo]) > TARIFAS_PADRAO[tipo]
                    for tipo in [0, 9, 6, 8]
                    if tipo in tarifas_motorista
                )
                
                if todas_acima:
                    grupos['Premium'].append({'id_motorista': id_motorista, 'nome_motorista': nome_motorista})
                else:
                    grupos['Personalizado'].append({'id_motorista': id_motorista, 'nome_motorista': nome_motorista})
        
        return jsonify({
            'success': True,
            'data': grupos
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar grupos: {str(e)}'}), 500

@app.route('/api/tarifas/<int:id_motorista>', methods=['PUT'])
def update_tarifa_motorista(id_motorista):
    """Atualizar tarifa de um motorista"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        
        # Validar se motorista existe
        motorista_existe = any(
            m['id_motorista'] == id_motorista 
            for m in motoristas_db[empresa_id]
        )
        
        if not motorista_existe:
            return jsonify({'error': 'Motorista não encontrado'}), 404
        
        # Validar dados
        tipo_servico = data.get('tipo_servico')
        valor = data.get('valor')
        
        if tipo_servico not in [0, 6, 8, 9]:
            return jsonify({'error': 'Tipo de serviço inválido'}), 400
        
        if not isinstance(valor, (int, float)) or valor < 0:
            return jsonify({'error': 'Valor inválido'}), 400
        
        # Inicializar tarifas do motorista se não existir
        if id_motorista not in tarifas_db[empresa_id]:
            tarifas_db[empresa_id][id_motorista] = {}
        
        # Atualizar tarifa
        tarifas_db[empresa_id][id_motorista][tipo_servico] = float(valor)
        
        return jsonify({
            'success': True,
            'message': f'Tarifa atualizada! Tipo {tipo_servico}: R$ {valor:.2f}',
            'data': {
                'id_motorista': id_motorista,
                'tipo_servico': tipo_servico,
                'valor': float(valor)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/tarifas/<int:id_motorista>/<int:tipo_servico>', methods=['PUT'])
def update_tarifa_motorista_tipo(id_motorista, tipo_servico):
    """Atualizar tarifa específica de um motorista (formato alternativo)"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        data = request.get_json()
        
        # Validar se motorista existe
        motorista_existe = any(
            m['id_motorista'] == id_motorista 
            for m in motoristas_db[empresa_id]
        )
        
        if not motorista_existe:
            return jsonify({'error': 'Motorista não encontrado'}), 404
        
        # Validar dados
        valor = data.get('valor')
        
        if tipo_servico not in [0, 6, 8, 9]:
            return jsonify({'error': 'Tipo de serviço inválido'}), 400
        
        if not isinstance(valor, (int, float)) or valor < 0:
            return jsonify({'error': 'Valor inválido'}), 400
        
        # Inicializar tarifas do motorista se não existir
        if id_motorista not in tarifas_db[empresa_id]:
            tarifas_db[empresa_id][id_motorista] = {}
        
        # Atualizar tarifa
        tarifas_db[empresa_id][id_motorista][tipo_servico] = float(valor)
        
        return jsonify({
            'success': True,
            'message': f'Tarifa atualizada! Tipo {tipo_servico}: R$ {valor:.2f}',
            'data': {
                'id_motorista': id_motorista,
                'tipo_servico': tipo_servico,
                'valor': float(valor)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/tarifas/<int:id_motorista>/reset', methods=['POST'])
def reset_tarifa_motorista(id_motorista):
    """Resetar tarifas de um motorista para o padrão"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        # Validar se motorista existe
        motorista_existe = any(
            m['id_motorista'] == id_motorista 
            for m in motoristas_db[empresa_id]
        )
        
        if not motorista_existe:
            return jsonify({'error': 'Motorista não encontrado'}), 404
        
        # Remover tarifas personalizadas
        if id_motorista in tarifas_db[empresa_id]:
            del tarifas_db[empresa_id][id_motorista]
        
        return jsonify({
            'success': True,
            'message': 'Tarifas resetadas para o padrão!',
            'data': {
                'id_motorista': id_motorista,
                'tarifas_padrao': TARIFAS_PADRAO
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ==================== APIs DO DASHBOARD ====================

@app.route('/api/drivers/count', methods=['GET'])
def drivers_count():
    """Contagem de motoristas"""
    try:
        empresa_id = get_empresa_id()
        inicializar_empresa(empresa_id)
        
        return jsonify({'success': True, 'count': len(motoristas_db[empresa_id])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment/summary', methods=['GET'])
def payment_summary():
    """Resumo de pagamentos"""
    try:
        empresa_id = get_empresa_id()
        
        # Calcular totais das AWBs
        total_pagamentos = 0.0
        pagamentos_pendentes = 0.0
        pagamentos_realizados = 0.0
        
        for awb, dados in awbs_db.items():
            if dados.get('empresa_id') == empresa_id:
                valor = dados.get('valor_pagamento', 0.0)
                total_pagamentos += valor
                
                if dados.get('status') == 'PAGA':
                    pagamentos_realizados += valor
                else:
                    pagamentos_pendentes += valor
        
        total_motoristas = len(motoristas_db.get(empresa_id, []))
        media_por_motorista = total_pagamentos / max(total_motoristas, 1)
        
        return jsonify({
            'success': True,
            'data': {
                'total_pagamentos': total_pagamentos,
                'pagamentos_pendentes': pagamentos_pendentes,
                'pagamentos_realizados': pagamentos_realizados,
                'media_por_motorista': media_por_motorista
            }
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

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    # Criar pasta de uploads se não existir
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Inicializar empresa padrão
    inicializar_empresa(EMPRESA_DEFAULT)
    
    # Executar aplicação
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

