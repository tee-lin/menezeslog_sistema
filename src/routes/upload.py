from flask import Blueprint, request, jsonify, current_app
import os
import pandas as pd
from werkzeug.utils import secure_filename
from src.models.models import db, FileUpload, Driver, Payment, ServiceType
from datetime import datetime
import uuid

upload_bp = Blueprint('upload', __name__)

# Configurações de upload
ALLOWED_EXTENSIONS_CSV = {'csv'}
ALLOWED_EXTENSIONS_EXCEL = {'xlsx', 'xls'}

def allowed_file_csv(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_CSV

def allowed_file_excel(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_EXCEL

@upload_bp.route('/api/upload', methods=['POST'])
def upload_files():
    # Verificar se os diretórios de upload existem, se não, criá-los
    UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
    csv_dir = os.path.join(UPLOAD_FOLDER, 'csv')
    excel_dir = os.path.join(UPLOAD_FOLDER, 'excel')
    
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(excel_dir, exist_ok=True)
    
    # Verificar se os arquivos foram enviados
    if 'csv_file' not in request.files or 'excel_file' not in request.files:
        return jsonify({'success': False, 'error': 'Arquivos CSV e Excel são obrigatórios'}), 400
    
    csv_file = request.files['csv_file']
    excel_file = request.files['excel_file']
    
    # Verificar se os arquivos têm nomes
    if csv_file.filename == '' or excel_file.filename == '':
        return jsonify({'success': False, 'error': 'Nomes de arquivos inválidos'}), 400
    
    # Verificar se os arquivos são do tipo permitido
    if not allowed_file_csv(csv_file.filename):
        return jsonify({'success': False, 'error': 'Arquivo CSV inválido. Use apenas arquivos .csv'}), 400
    
    if not allowed_file_excel(excel_file.filename):
        return jsonify({'success': False, 'error': 'Arquivo Excel inválido. Use apenas arquivos .xlsx ou .xls'}), 400
    
    # Salvar os arquivos com nomes seguros
    csv_filename = secure_filename(csv_file.filename)
    excel_filename = secure_filename(excel_file.filename)
    
    # Adicionar timestamp para evitar sobrescrever arquivos
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    csv_filename = f"{timestamp}_{csv_filename}"
    excel_filename = f"{timestamp}_{excel_filename}"
    
    csv_path = os.path.join(csv_dir, csv_filename)
    excel_path = os.path.join(excel_dir, excel_filename)
    
    csv_file.save(csv_path)
    excel_file.save(excel_path)
    
    # Registrar os uploads no banco de dados
    try:
        # Criar registros de upload
        csv_upload = FileUpload(
            filename=csv_filename,
            filepath=csv_path,
            filetype='csv',
            upload_date=datetime.now(),
            user_id=1  # Assumindo ID 1 para o admin por enquanto
        )
        
        excel_upload = FileUpload(
            filename=excel_filename,
            filepath=excel_path,
            filetype='excel',
            upload_date=datetime.now(),
            user_id=1  # Assumindo ID 1 para o admin por enquanto
        )
        
        db.session.add(csv_upload)
        db.session.add(excel_upload)
        db.session.commit()
        
        # Processar os arquivos
        process_result = process_files(csv_path, excel_path)
        
        if process_result['success']:
            return jsonify({
                'success': True,
                'message': 'Arquivos enviados e processados com sucesso',
                'csv_id': csv_upload.id,
                'excel_id': excel_upload.id,
                'stats': process_result['stats']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': process_result['error'],
                'csv_id': csv_upload.id,
                'excel_id': excel_upload.id
            }), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def process_files(csv_path, excel_path):
    try:
        # Carregar arquivo CSV com dados de entregas
        deliveries_df = pd.read_csv(csv_path, encoding='latin1', sep=';')
        
        # Carregar arquivo Excel com dados dos motoristas
        drivers_df = pd.read_excel(excel_path)
        
        # Verificar se as colunas necessárias existem
        required_csv_columns = ['ID do motorista', 'Tipo de serviço']
        required_excel_columns = ['ID do motorista', 'Nome do motorista']
        
        for col in required_csv_columns:
            if col not in deliveries_df.columns:
                return {'success': False, 'error': f'Coluna obrigatória não encontrada no CSV: {col}'}
        
        for col in required_excel_columns:
            if col not in drivers_df.columns:
                return {'success': False, 'error': f'Coluna obrigatória não encontrada no Excel: {col}'}
        
        # Processar dados dos motoristas
        for _, row in drivers_df.iterrows():
            driver_id = str(row['ID do motorista'])
            driver_name = row['Nome do motorista']
            
            # Verificar se o motorista já existe no banco de dados
            driver = Driver.query.filter_by(driver_id=driver_id).first()
            
            if not driver:
                # Criar novo motorista
                driver = Driver(
                    driver_id=driver_id,
                    name=driver_name,
                    active=True
                )
                db.session.add(driver)
        
        # Commit para salvar os motoristas
        db.session.commit()
        
        # Obter valores de pagamento por tipo de serviço
        service_types = ServiceType.query.all()
        service_type_values = {}
        
        # Se não existirem tipos de serviço, criar os padrões
        if not service_types:
            default_types = [
                {'type_id': 0, 'value': 3.50, 'description': 'Tipo 0'},
                {'type_id': 6, 'value': 0.50, 'description': 'Tipo 6'},
                {'type_id': 8, 'value': 0.50, 'description': 'Tipo 8'},
                {'type_id': 9, 'value': 2.00, 'description': 'Tipo 9'}
            ]
            
            for type_data in default_types:
                service_type = ServiceType(
                    type_id=type_data['type_id'],
                    value=type_data['value'],
                    description=type_data['description']
                )
                db.session.add(service_type)
                service_type_values[type_data['type_id']] = type_data['value']
            
            db.session.commit()
        else:
            for st in service_types:
                service_type_values[st.type_id] = st.value
        
        # Processar pagamentos
        payment_data = {}
        
        # Agrupar entregas por motorista e tipo de serviço
        for _, row in deliveries_df.iterrows():
            driver_id = str(row['ID do motorista'])
            service_type = int(row['Tipo de serviço'])
            
            if driver_id not in payment_data:
                payment_data[driver_id] = {}
            
            if service_type not in payment_data[driver_id]:
                payment_data[driver_id][service_type] = 0
            
            payment_data[driver_id][service_type] += 1
        
        # Calcular pagamentos e salvar no banco de dados
        total_payments = 0
        payment_date = datetime.now()
        payment_reference = f"PAG-{payment_date.strftime('%Y%m%d')}"
        
        for driver_id, service_counts in payment_data.items():
            driver = Driver.query.filter_by(driver_id=driver_id).first()
            
            if not driver:
                continue
            
            total_driver_payment = 0
            payment_details = {}
            
            for service_type, count in service_counts.items():
                if service_type in service_type_values:
                    value_per_item = service_type_values[service_type]
                    payment_amount = count * value_per_item
                    total_driver_payment += payment_amount
                    payment_details[service_type] = {
                        'count': count,
                        'value_per_item': value_per_item,
                        'total': payment_amount
                    }
            
            # Criar registro de pagamento
            payment = Payment(
                driver_id=driver.id,
                amount=total_driver_payment,
                payment_date=payment_date,
                reference=payment_reference,
                status='pending',
                details=str(payment_details)
            )
            
            db.session.add(payment)
            total_payments += total_driver_payment
        
        # Commit para salvar os pagamentos
        db.session.commit()
        
        # Gerar estatísticas
        stats = {
            'total_deliveries': deliveries_df.shape[0],
            'total_drivers': len(payment_data),
            'total_payments': round(total_payments, 2)
        }
        
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

@upload_bp.route('/api/uploads', methods=['GET'])
def get_uploads():
    try:
        uploads = FileUpload.query.order_by(FileUpload.upload_date.desc()).all()
        
        result = []
        for upload in uploads:
            result.append({
                'id': upload.id,
                'filename': upload.filename,
                'filetype': upload.filetype,
                'upload_date': upload.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': upload.user_id
            })
        
        return jsonify({'success': True, 'uploads': result}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
