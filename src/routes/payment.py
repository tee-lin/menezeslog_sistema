from flask import Blueprint, request, jsonify, current_app, send_file
from src.models.models import db, Payment, Driver, Delivery, Bonus, Discount, Invoice
from src.routes.auth import token_required
import datetime
import os
import pandas as pd
from fpdf2 import FPDF
import matplotlib.pyplot as plt
import io

payment_bp = Blueprint('payment', __name__)

# Rota para listar pagamentos
@payment_bp.route('/', methods=['GET'])
@token_required
def list_payments(current_user):
    # Verificar se o usuário é admin
    if current_user.role == 'admin':
        # Filtrar por período (opcional)
        period = request.args.get('period')
        
        # Filtrar por motorista (opcional)
        driver_id = request.args.get('driver_id')
        
        # Construir query
        query = Payment.query
        
        if period:
            query = query.filter_by(period=period)
        
        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        
        # Ordenar por período (mais recente primeiro)
        payments = query.order_by(Payment.period.desc()).all()
        
        # Incluir informações do motorista
        result = []
        for payment in payments:
            driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
            payment_dict = payment.to_dict()
            payment_dict['driver_name'] = driver.name if driver else f"Motorista {payment.driver_id}"
            result.append(payment_dict)
        
        return jsonify({
            'payments': result
        }), 200
    
    # Se for motorista, retornar apenas seus pagamentos
    elif current_user.role == 'driver':
        # Filtrar por período (opcional)
        period = request.args.get('period')
        
        # Construir query
        query = Payment.query.filter_by(driver_id=current_user.driver_id)
        
        if period:
            query = query.filter_by(period=period)
        
        # Ordenar por período (mais recente primeiro)
        payments = query.order_by(Payment.period.desc()).all()
        
        return jsonify({
            'payments': [payment.to_dict() for payment in payments]
        }), 200
    
    else:
        return jsonify({'message': 'Acesso não autorizado!'}), 403

# Rota para obter detalhes de um pagamento
@payment_bp.route('/<int:payment_id>', methods=['GET'])
@token_required
def get_payment(current_user, payment_id):
    # Obter o pagamento
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != payment.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter motorista
    driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
    
    # Obter entregas
    deliveries = Delivery.query.filter_by(driver_id=payment.driver_id, payment_period=payment.period).all()
    
    # Obter bonificações
    bonuses = Bonus.query.filter_by(driver_id=payment.driver_id, period=payment.period).all()
    
    # Obter descontos
    discounts = Discount.query.filter(
        Discount.driver_id == payment.driver_id,
        Discount.status.in_(['in_progress', 'completed'])
    ).all()
    
    # Obter nota fiscal
    invoice = Invoice.query.filter_by(id=payment.invoice_id).first() if payment.invoice_id else None
    
    # Agrupar entregas por tipo de serviço
    deliveries_by_type = {}
    for delivery in deliveries:
        service_type = delivery.service_type
        if service_type not in deliveries_by_type:
            deliveries_by_type[service_type] = {
                'count': 0,
                'base_value': 0.0,
                'bonus_value': 0.0,
                'total_value': 0.0
            }
        
        deliveries_by_type[service_type]['count'] += 1
        deliveries_by_type[service_type]['base_value'] += delivery.base_value
        deliveries_by_type[service_type]['bonus_value'] += delivery.bonus_value
        deliveries_by_type[service_type]['total_value'] += delivery.total_value
    
    return jsonify({
        'payment': payment.to_dict(),
        'driver': driver.to_dict() if driver else None,
        'deliveries_count': len(deliveries),
        'deliveries_by_type': deliveries_by_type,
        'bonuses': [bonus.to_dict() for bonus in bonuses],
        'discounts': [discount.to_dict() for discount in discounts],
        'invoice': invoice.to_dict() if invoice else None
    }), 200

# Rota para gerar relatório de pagamento em PDF
@payment_bp.route('/<int:payment_id>/report', methods=['GET'])
@token_required
def generate_payment_report(current_user, payment_id):
    # Obter o pagamento
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != payment.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter motorista
    driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
    
    # Obter entregas
    deliveries = Delivery.query.filter_by(driver_id=payment.driver_id, payment_period=payment.period).all()
    
    # Obter bonificações
    bonuses = Bonus.query.filter_by(driver_id=payment.driver_id, period=payment.period).all()
    
    # Obter descontos
    discounts = Discount.query.filter(
        Discount.driver_id == payment.driver_id,
        Discount.status.in_(['in_progress', 'completed'])
    ).all()
    
    # Agrupar entregas por tipo de serviço
    deliveries_by_type = {}
    for delivery in deliveries:
        service_type = delivery.service_type
        if service_type not in deliveries_by_type:
            deliveries_by_type[service_type] = {
                'count': 0,
                'base_value': 0.0,
                'bonus_value': 0.0,
                'total_value': 0.0
            }
        
        deliveries_by_type[service_type]['count'] += 1
        deliveries_by_type[service_type]['base_value'] += delivery.base_value
        deliveries_by_type[service_type]['bonus_value'] += delivery.bonus_value
        deliveries_by_type[service_type]['total_value'] += delivery.total_value
    
    # Criar diretório para relatórios se não existir
    reports_dir = os.path.join(current_app.root_path, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Gerar nome do arquivo
    driver_name = driver.name.replace(' ', '_') if driver else f"Motorista_{payment.driver_id}"
    filename = f"Relatorio_Pagamento_{payment.driver_id}_{driver_name}.pdf"
    file_path = os.path.join(reports_dir, filename)
    
    # Criar PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'MenezesLog - Relatório de Pagamento', 0, 1, 'C')
    
    # Informações do motorista
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Motorista: {driver.name if driver else 'Desconhecido'} (ID: {payment.driver_id})", 0, 1)
    
    # Informações do período
    pdf.set_font('Arial', '', 12)
    start_date, end_date = payment.period.split('_')
    pdf.cell(0, 10, f"Período: {start_date} a {end_date}", 0, 1)
    
    # Resumo
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Resumo do Pagamento", 0, 1)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(90, 8, f"Total de Entregas: {payment.deliveries_count}", 0, 0)
    pdf.cell(90, 8, f"Valor Base: R$ {payment.base_value:.2f}", 0, 1)
    pdf.cell(90, 8, f"Bonificações: R$ {payment.bonus_value:.2f}", 0, 0)
    pdf.cell(90, 8, f"Descontos: R$ {payment.discount_value:.2f}", 0, 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Valor Total: R$ {payment.total_value:.2f}", 0, 1)
    
    # Entregas por tipo de serviço
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Entregas por Tipo de Serviço", 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(20, 8, "Tipo", 1, 0, 'C')
    pdf.cell(30, 8, "Quantidade", 1, 0, 'C')
    pdf.cell(40, 8, "Valor Base", 1, 0, 'C')
    pdf.cell(40, 8, "Bonificação", 1, 0, 'C')
    pdf.cell(40, 8, "Total", 1, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    for service_type, data in deliveries_by_type.items():
        pdf.cell(20, 8, str(service_type), 1, 0, 'C')
        pdf.cell(30, 8, str(data['count']), 1, 0, 'C')
        pdf.cell(40, 8, f"R$ {data['base_value']:.2f}", 1, 0, 'C')
        pdf.cell(40, 8, f"R$ {data['bonus_value']:.2f}", 1, 0, 'C')
        pdf.cell(40, 8, f"R$ {data['total_value']:.2f}", 1, 1, 'C')
    
    # Bonificações
    if bonuses:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Bonificações", 0, 1)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(100, 8, "Descrição", 1, 0, 'C')
        pdf.cell(70, 8, "Valor", 1, 1, 'C')
        
        pdf.set_font('Arial', '', 10)
        for bonus in bonuses:
            pdf.cell(100, 8, bonus.description or "Bonificação", 1, 0)
            pdf.cell(70, 8, f"R$ {bonus.value:.2f}", 1, 1, 'C')
    
    # Descontos
    if discounts:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Descontos", 0, 1)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(80, 8, "Descrição", 1, 0, 'C')
        pdf.cell(30, 8, "Parcela", 1, 0, 'C')
        pdf.cell(30, 8, "Total", 1, 0, 'C')
        pdf.cell(30, 8, "Valor", 1, 1, 'C')
        
        pdf.set_font('Arial', '', 10)
        for discount in discounts:
            pdf.cell(80, 8, discount.description or "Desconto", 1, 0)
            pdf.cell(30, 8, f"{discount.current_installment-1}/{discount.installments}", 1, 0, 'C')
            pdf.cell(30, 8, f"R$ {discount.total_value:.2f}", 1, 0, 'C')
            pdf.cell(30, 8, f"R$ {discount.installment_value:.2f}", 1, 1, 'C')
    
    # Salvar PDF
    pdf.output(file_path)
    
    # Retornar o arquivo
    return send_file(file_path, as_attachment=True, download_name=filename)

# Rota para gerar gráfico de entregas por tipo de serviço
@payment_bp.route('/<int:payment_id>/chart', methods=['GET'])
@token_required
def generate_payment_chart(current_user, payment_id):
    # Obter o pagamento
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar permissão
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != payment.driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter entregas
    deliveries = Delivery.query.filter_by(driver_id=payment.driver_id, payment_period=payment.period).all()
    
    # Agrupar entregas por tipo de serviço
    deliveries_by_type = {}
    for delivery in deliveries:
        service_type = delivery.service_type
        if service_type not in deliveries_by_type:
            deliveries_by_type[service_type] = 0
        
        deliveries_by_type[service_type] += 1
    
    # Criar gráfico
    plt.figure(figsize=(10, 6))
    
    # Gráfico de barras
    plt.bar(deliveries_by_type.keys(), deliveries_by_type.values(), color='#0046AD')
    
    # Adicionar rótulos
    plt.title('Entregas por Tipo de Serviço')
    plt.xlabel('Tipo de Serviço')
    plt.ylabel('Quantidade de Entregas')
    
    # Adicionar valores nas barras
    for i, v in enumerate(deliveries_by_type.values()):
        plt.text(i, v + 0.1, str(v), ha='center')
    
    # Salvar gráfico em memória
    img_data = io.BytesIO()
    plt.savefig(img_data, format='png')
    img_data.seek(0)
    
    # Criar diretório para gráficos se não existir
    charts_dir = os.path.join(current_app.root_path, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    # Gerar nome do arquivo
    filename = f"chart_payment_{payment_id}.png"
    file_path = os.path.join(charts_dir, filename)
    
    # Salvar gráfico em arquivo
    with open(file_path, 'wb') as f:
        f.write(img_data.getvalue())
    
    # Retornar o arquivo
    return send_file(file_path, mimetype='image/png')

# Rota para exportar pagamentos para Excel
@payment_bp.route('/export', methods=['GET'])
@token_required
def export_payments(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Filtrar por período (opcional)
    period = request.args.get('period')
    
    # Construir query
    query = Payment.query
    
    if period:
        query = query.filter_by(period=period)
    
    # Ordenar por período (mais recente primeiro)
    payments = query.order_by(Payment.period.desc()).all()
    
    # Criar DataFrame
    data = []
    for payment in payments:
        driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
        data.append({
            'ID': payment.id,
            'ID do Motorista': payment.driver_id,
            'Nome do Motorista': driver.name if driver else f"Motorista {payment.driver_id}",
            'Período': payment.period,
            'Data Início': payment.start_date,
            'Data Fim': payment.end_date,
            'Entregas': payment.deliveries_count,
            'Valor Base': payment.base_value,
            'Bonificações': payment.bonus_value,
            'Descontos': payment.discount_value,
            'Valor Total': payment.total_value,
            'Status': payment.status,
            'Data de Criação': payment.created_at
        })
    
    df = pd.DataFrame(data)
    
    # Criar diretório para exportações se não existir
    exports_dir = os.path.join(current_app.root_path, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    # Gerar nome do arquivo
    filename = f"pagamentos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(exports_dir, filename)
    
    # Salvar Excel
    df.to_excel(file_path, index=False)
    
    # Retornar o arquivo
    return send_file(file_path, as_attachment=True, download_name=filename)

# Rota para atualizar status de pagamento
@payment_bp.route('/<int:payment_id>/status', methods=['PUT'])
@token_required
def update_payment_status(current_user, payment_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter o pagamento
    payment = Payment.query.get_or_404(payment_id)
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('status'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar status
    payment.status = data.get('status')
    payment.updated_at = datetime.datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Status do pagamento atualizado com sucesso!',
        'payment': payment.to_dict()
    }), 200
