from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import os
import datetime
from src.models.models import db, Invoice, Payment, Driver
from src.routes.auth import token_required
import uuid

invoice_bp = Blueprint('invoice', __name__)

# Configurações para upload de arquivos
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rota para upload de nota fiscal
@invoice_bp.route('/', methods=['POST'])
@token_required
def upload_invoice(current_user):
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
    
    # Obter dados do formulário
    payment_id = request.form.get('payment_id')
    invoice_number = request.form.get('invoice_number')
    issue_date_str = request.form.get('issue_date')
    
    # Validar dados
    if not payment_id or not invoice_number or not issue_date_str:
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Obter o pagamento
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({'message': 'Pagamento não encontrado!'}), 404
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != payment.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Converter data
    try:
        issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date()
    except:
        return jsonify({'message': 'Formato de data inválido! Use YYYY-MM-DD'}), 400
    
    # Criar diretório de invoices se não existir
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'invoices')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Gerar nome único para o arquivo
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Salvar o arquivo
    file.save(file_path)
    
    # Criar ou atualizar nota fiscal
    invoice = Invoice.query.filter_by(driver_id=payment.driver_id, period=payment.period).first()
    
    if invoice:
        # Atualizar nota fiscal existente
        invoice.invoice_number = invoice_number
        invoice.issue_date = issue_date
        invoice.file_path = file_path
        invoice.value = payment.total_value
        invoice.status = 'pending'
        invoice.updated_at = datetime.datetime.utcnow()
    else:
        # Criar nova nota fiscal
        invoice = Invoice(
            driver_id=payment.driver_id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            file_path=file_path,
            period=payment.period,
            value=payment.total_value,
            status='pending'
        )
        db.session.add(invoice)
    
    # Atualizar pagamento
    payment.invoice_id = invoice.id if invoice.id else None
    payment.status = 'invoice_received'
    
    db.session.commit()
    
    return jsonify({
        'message': 'Nota fiscal enviada com sucesso!',
        'invoice': invoice.to_dict()
    }), 201

# Rota para listar notas fiscais
@invoice_bp.route('/', methods=['GET'])
@token_required
def list_invoices(current_user):
    # Verificar se o usuário é admin
    if current_user.role == 'admin':
        # Filtrar por status (opcional)
        status = request.args.get('status')
        
        # Filtrar por motorista (opcional)
        driver_id = request.args.get('driver_id')
        
        # Construir query
        query = Invoice.query
        
        if status:
            query = query.filter_by(status=status)
        
        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        
        # Ordenar por data de criação (mais recente primeiro)
        invoices = query.order_by(Invoice.created_at.desc()).all()
        
        # Incluir informações do motorista
        result = []
        for invoice in invoices:
            driver = Driver.query.filter_by(driver_id=invoice.driver_id).first()
            invoice_dict = invoice.to_dict()
            invoice_dict['driver_name'] = driver.name if driver else f"Motorista {invoice.driver_id}"
            result.append(invoice_dict)
        
        return jsonify({
            'invoices': result
        }), 200
    
    # Se for motorista, retornar apenas suas notas fiscais
    elif current_user.role == 'driver':
        # Filtrar por status (opcional)
        status = request.args.get('status')
        
        # Construir query
        query = Invoice.query.filter_by(driver_id=current_user.driver_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Ordenar por data de criação (mais recente primeiro)
        invoices = query.order_by(Invoice.created_at.desc()).all()
        
        return jsonify({
            'invoices': [invoice.to_dict() for invoice in invoices]
        }), 200
    
    else:
        return jsonify({'message': 'Acesso não autorizado!'}), 403

# Rota para obter detalhes de uma nota fiscal
@invoice_bp.route('/<int:invoice_id>', methods=['GET'])
@token_required
def get_invoice(current_user, invoice_id):
    # Obter a nota fiscal
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != invoice.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter motorista
    driver = Driver.query.filter_by(driver_id=invoice.driver_id).first()
    
    # Obter pagamento
    payment = Payment.query.filter_by(invoice_id=invoice.id).first()
    
    return jsonify({
        'invoice': invoice.to_dict(),
        'driver': driver.to_dict() if driver else None,
        'payment': payment.to_dict() if payment else None
    }), 200

# Rota para baixar arquivo da nota fiscal
@invoice_bp.route('/<int:invoice_id>/download', methods=['GET'])
@token_required
def download_invoice(current_user, invoice_id):
    # Obter a nota fiscal
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != invoice.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o arquivo existe
    if not os.path.exists(invoice.file_path):
        return jsonify({'message': 'Arquivo não encontrado!'}), 404
    
    # Retornar o arquivo
    return send_file(
        invoice.file_path,
        as_attachment=True,
        download_name=f"NF_{invoice.invoice_number}_{invoice.driver_id}.{invoice.file_path.split('.')[-1]}"
    )

# Rota para atualizar status de uma nota fiscal
@invoice_bp.route('/<int:invoice_id>/status', methods=['PUT'])
@token_required
def update_invoice_status(current_user, invoice_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a nota fiscal
    invoice = Invoice.query.get_or_404(invoice_id)
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('status'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar status
    invoice.status = data.get('status')
    
    # Adicionar comentários (opcional)
    if 'comments' in data:
        invoice.comments = data.get('comments')
    
    invoice.updated_at = datetime.datetime.utcnow()
    
    # Atualizar status do pagamento associado
    payment = Payment.query.filter_by(invoice_id=invoice.id).first()
    if payment:
        if data.get('status') == 'approved':
            payment.status = 'approved'
        elif data.get('status') == 'rejected':
            payment.status = 'pending'
            payment.invoice_id = None
    
    db.session.commit()
    
    return jsonify({
        'message': 'Status da nota fiscal atualizado com sucesso!',
        'invoice': invoice.to_dict()
    }), 200
