from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import os
import pandas as pd
import datetime
from src.models.models import db, Driver, Delivery, Payment, ServiceType, FileUpload
from src.routes.auth import token_required
import uuid

upload_bp = Blueprint('upload', __name__)

# Configurações para upload de arquivos
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
UPLOAD_FOLDER = os.path.join(current_app.root_path, 'uploads')

# Verificar se o diretório de uploads existe, senão criar
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rota para upload de arquivo CSV de entregas
@upload_bp.route('/deliveries', methods=['POST'])
@token_required
def upload_deliveries(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o arquivo foi enviado
    if 'file' not in request.files:
        return jsonify({'message': 'Nenhum arquivo enviado!'}), 400
    
    file = request.files['file']
    
    # Verificar se o arquivo tem nome
    if file.filename == '':
        return jsonify({'message': 'Nenhum arquivo selecionado!'}), 400
    
    # Verificar se o arquivo é permitido
    if not allowed_file(file.filename):
        return jsonify({'message': f'Formato de arquivo não permitido! Formatos aceitos: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Gerar nome único para o arquivo
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Salvar o arquivo
    file.save(file_path)
    
    # Registrar o upload no banco de dados
    file_upload = FileUpload(
        filename=filename,
        file_path=file_path,
        file_type='csv' if filename.endswith('.csv') else 'excel',
        uploaded_by=current_user.id
    )
    
    db.session.add(file_upload)
    db.session.commit()
    
    # Iniciar processamento do arquivo em background
    # Em uma implementação real, isso seria feito com uma tarefa assíncrona (Celery, etc.)
    # Para simplificar, vamos processar diretamente
    try:
        result = process_delivery_file(file_path, file_upload.id)
        return jsonify({
            'message': 'Arquivo enviado e processado com sucesso!',
            'file_id': file_upload.id,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'message': f'Erro ao processar arquivo: {str(e)}',
            'file_id': file_upload.id
        }), 500

# Rota para upload de arquivo Excel com nomes de motoristas
@upload_bp.route('/drivers', methods=['POST'])
@token_required
def upload_drivers(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o arquivo foi enviado
    if 'file' not in request.files:
        return jsonify({'message': 'Nenhum arquivo enviado!'}), 400
    
    file = request.files['file']
    
    # Verificar se o arquivo tem nome
    if file.filename == '':
        return jsonify({'message': 'Nenhum arquivo selecionado!'}), 400
    
    # Verificar se o arquivo é permitido
    if not allowed_file(file.filename):
        return jsonify({'message': f'Formato de arquivo não permitido! Formatos aceitos: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    # Gerar nome único para o arquivo
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Salvar o arquivo
    file.save(file_path)
    
    # Registrar o upload no banco de dados
    file_upload = FileUpload(
        filename=filename,
        file_path=file_path,
        file_type='excel',
        uploaded_by=current_user.id
    )
    
    db.session.add(file_upload)
    db.session.commit()
    
    # Processar o arquivo de motoristas
    try:
        result = process_drivers_file(file_path, file_upload.id)
        return jsonify({
            'message': 'Arquivo enviado e processado com sucesso!',
            'file_id': file_upload.id,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'message': f'Erro ao processar arquivo: {str(e)}',
            'file_id': file_upload.id
        }), 500

# Função para processar arquivo de entregas
def process_delivery_file(file_path, file_upload_id):
    # Determinar o tipo de arquivo
    if file_path.endswith('.csv'):
        try:
            # Tentar com encoding latin1 (comum para arquivos brasileiros)
            df = pd.read_csv(file_path, encoding='latin1', sep=';')
        except:
            # Se falhar, tentar com UTF-8
            df = pd.read_csv(file_path, encoding='utf-8', sep=';')
    else:
        # Excel
        df = pd.read_excel(file_path)
    
    # Verificar colunas necessárias
    required_columns = ['ID do motorista', 'Peso Capturado', 'Status da encomenda', 'Desc. do status da encomenda', 'Tipo de serviço']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
    
    # Obter período de pagamento (quinzena atual)
    today = datetime.date.today()
    if today.day <= 15:
        start_date = datetime.date(today.year, today.month, 1)
        end_date = datetime.date(today.year, today.month, 15)
    else:
        start_date = datetime.date(today.year, today.month, 16)
        end_date = (datetime.date(today.year, today.month + 1, 1) if today.month < 12 else datetime.date(today.year + 1, 1, 1)) - datetime.timedelta(days=1)
    
    period = f"{start_date.isoformat()}_{end_date.isoformat()}"
    
    # Obter valores base por tipo de serviço
    service_types = {
        0: 3.50,  # Tipo 0 = R$ 3,50
        9: 2.00,  # Tipo 9 = R$ 2,00
        6: 0.50,  # Tipo 6 = R$ 0,50
        8: 0.50   # Tipo 8 = R$ 0,50
    }
    
    # Inicializar contadores
    processed_count = 0
    error_count = 0
    driver_deliveries = {}
    
    # Processar cada linha do arquivo
    for _, row in df.iterrows():
        try:
            driver_id = str(row['ID do motorista'])
            service_type = int(row['Tipo de serviço'])
            status = str(row['Status da encomenda'])
            
            # Verificar se o motorista existe
            driver = Driver.query.filter_by(driver_id=driver_id).first()
            if not driver:
                # Criar motorista com nome temporário
                driver = Driver(
                    driver_id=driver_id,
                    name=f"Motorista {driver_id}"
                )
                db.session.add(driver)
                db.session.commit()
            
            # Verificar se o tipo de serviço é válido
            if service_type not in service_types:
                error_count += 1
                continue
            
            # Calcular valor base
            base_value = service_types[service_type]
            
            # Criar entrega
            delivery = Delivery(
                driver_id=driver_id,
                awb=str(row.get('AWB', '')),
                sender=str(row.get('Remetente', '')),
                service_type=service_type,
                weight=float(row.get('Peso Capturado', 0)),
                status=status,
                status_description=str(row.get('Desc. do status da encomenda', '')),
                delivery_date=datetime.date.today(),
                payment_period=period,
                base_value=base_value,
                bonus_value=0.0,  # Será calculado posteriormente
                total_value=base_value  # Inicialmente igual ao valor base
            )
            
            db.session.add(delivery)
            processed_count += 1
            
            # Atualizar contagem por motorista
            if driver_id not in driver_deliveries:
                driver_deliveries[driver_id] = {
                    'count': 0,
                    'total': 0.0,
                    'by_type': {0: 0, 9: 0, 6: 0, 8: 0}
                }
            
            driver_deliveries[driver_id]['count'] += 1
            driver_deliveries[driver_id]['total'] += base_value
            driver_deliveries[driver_id]['by_type'][service_type] += 1
            
        except Exception as e:
            error_count += 1
            continue
    
    # Commit das entregas
    db.session.commit()
    
    # Atualizar ou criar pagamentos para cada motorista
    for driver_id, data in driver_deliveries.items():
        # Verificar se já existe pagamento para este período
        payment = Payment.query.filter_by(driver_id=driver_id, period=period).first()
        
        if payment:
            # Atualizar pagamento existente
            payment.deliveries_count += data['count']
            payment.base_value += data['total']
            payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
        else:
            # Criar novo pagamento
            payment = Payment(
                driver_id=driver_id,
                period=period,
                start_date=start_date,
                end_date=end_date,
                deliveries_count=data['count'],
                base_value=data['total'],
                bonus_value=0.0,  # Será calculado posteriormente
                discount_value=0.0,  # Será calculado posteriormente
                total_value=data['total']  # Inicialmente igual ao valor base
            )
            db.session.add(payment)
        
    # Commit dos pagamentos
    db.session.commit()
    
    # Atualizar status do upload
    file_upload = FileUpload.query.get(file_upload_id)
    file_upload.processed = True
    file_upload.process_date = datetime.datetime.utcnow()
    file_upload.process_result = f"Processadas {processed_count} entregas com {error_count} erros."
    db.session.commit()
    
    return {
        'processed': processed_count,
        'errors': error_count,
        'drivers': len(driver_deliveries),
        'period': period
    }

# Função para processar arquivo de motoristas
def process_drivers_file(file_path, file_upload_id):
    # Determinar o tipo de arquivo
    if file_path.endswith('.csv'):
        try:
            # Tentar com encoding latin1 (comum para arquivos brasileiros)
            df = pd.read_csv(file_path, encoding='latin1')
        except:
            # Se falhar, tentar com UTF-8
            df = pd.read_csv(file_path, encoding='utf-8')
    else:
        # Excel
        df = pd.read_excel(file_path)
    
    # Verificar colunas necessárias
    if len(df.columns) < 2:
        raise ValueError("O arquivo deve ter pelo menos duas colunas: ID do motorista e Nome")
    
    # Renomear colunas para padronizar
    df.columns = ['driver_id', 'name'] + list(df.columns[2:])
    
    # Inicializar contadores
    processed_count = 0
    updated_count = 0
    error_count = 0
    
    # Processar cada linha do arquivo
    for _, row in df.iterrows():
        try:
            driver_id = str(row['driver_id'])
            name = str(row['name'])
            
            # Verificar se o motorista já existe
            driver = Driver.query.filter_by(driver_id=driver_id).first()
            
            if driver:
                # Atualizar nome
                driver.name = name
                updated_count += 1
            else:
                # Criar novo motorista
                driver = Driver(
                    driver_id=driver_id,
                    name=name
                )
                db.session.add(driver)
                processed_count += 1
                
        except Exception as e:
            error_count += 1
            continue
    
    # Commit das alterações
    db.session.commit()
    
    # Atualizar status do upload
    file_upload = FileUpload.query.get(file_upload_id)
    file_upload.processed = True
    file_upload.process_date = datetime.datetime.utcnow()
    file_upload.process_result = f"Processados {processed_count} novos motoristas, atualizados {updated_count} existentes, com {error_count} erros."
    db.session.commit()
    
    return {
        'new_drivers': processed_count,
        'updated_drivers': updated_count,
        'errors': error_count
    }

# Rota para listar uploads
@upload_bp.route('/list', methods=['GET'])
@token_required
def list_uploads(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter todos os uploads ordenados por data
    uploads = FileUpload.query.order_by(FileUpload.upload_date.desc()).all()
    
    return jsonify({
        'uploads': [upload.to_dict() for upload in uploads]
    }), 200

# Rota para baixar arquivo
@upload_bp.route('/download/<int:file_id>', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter o upload
    file_upload = FileUpload.query.get_or_404(file_id)
    
    # Verificar se o arquivo existe
    if not os.path.exists(file_upload.file_path):
        return jsonify({'message': 'Arquivo não encontrado!'}), 404
    
    # Retornar o arquivo
    return send_from_directory(
        os.path.dirname(file_upload.file_path),
        os.path.basename(file_upload.file_path),
        as_attachment=True,
        download_name=file_upload.filename
    )
