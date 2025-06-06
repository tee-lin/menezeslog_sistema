from flask import Blueprint, request, jsonify, current_app, send_file
import os
import pandas as pd
from src.models.models import db, Driver, Payment, ServiceType
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import numpy as np
import io
import json

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/api/payments', methods=['GET'])
def get_payments():
    try:
        # Obter todos os pagamentos com informações do motorista
        payments = db.session.query(Payment, Driver).join(Driver).all()
        
        result = []
        for payment, driver in payments:
            result.append({
                'id': payment.id,
                'driver_id': driver.driver_id,
                'driver_name': driver.name,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                'reference': payment.reference,
                'status': payment.status,
                'invoice_received': payment.invoice_received
            })
        
        return jsonify({'success': True, 'payments': result}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/api/payments/<int:payment_id>', methods=['GET'])
def get_payment(payment_id):
    try:
        # Obter pagamento específico com informações do motorista
        payment_data = db.session.query(Payment, Driver).join(Driver).filter(Payment.id == payment_id).first()
        
        if not payment_data:
            return jsonify({'success': False, 'error': 'Pagamento não encontrado'}), 404
        
        payment, driver = payment_data
        
        # Converter detalhes de string para dicionário
        details = {}
        if payment.details:
            try:
                details = eval(payment.details)
            except:
                details = {}
        
        result = {
            'id': payment.id,
            'driver_id': driver.driver_id,
            'driver_name': driver.name,
            'amount': float(payment.amount),
            'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
            'reference': payment.reference,
            'status': payment.status,
            'invoice_received': payment.invoice_received,
            'details': details
        }
        
        return jsonify({'success': True, 'payment': result}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/api/payments/<int:payment_id>/status', methods=['PUT'])
def update_payment_status(payment_id):
    try:
        data = request.json
        
        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Status não fornecido'}), 400
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'success': False, 'error': 'Pagamento não encontrado'}), 404
        
        payment.status = data['status']
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Status atualizado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/api/payments/<int:payment_id>/invoice', methods=['PUT'])
def update_payment_invoice(payment_id):
    try:
        data = request.json
        
        if 'invoice_received' not in data:
            return jsonify({'success': False, 'error': 'Status de nota fiscal não fornecido'}), 400
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'success': False, 'error': 'Pagamento não encontrado'}), 404
        
        payment.invoice_received = data['invoice_received']
        
        if data['invoice_received']:
            payment.invoice_date = datetime.now()
        else:
            payment.invoice_date = None
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Status de nota fiscal atualizado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/api/payments/driver/<driver_id>', methods=['GET'])
def get_driver_payments(driver_id):
    try:
        # Obter motorista pelo ID
        driver = Driver.query.filter_by(driver_id=driver_id).first()
        
        if not driver:
            return jsonify({'success': False, 'error': 'Motorista não encontrado'}), 404
        
        # Obter pagamentos do motorista
        payments = Payment.query.filter_by(driver_id=driver.id).all()
        
        result = []
        for payment in payments:
            # Converter detalhes de string para dicionário
            details = {}
            if payment.details:
                try:
                    details = eval(payment.details)
                except:
                    details = {}
            
            result.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                'reference': payment.reference,
                'status': payment.status,
                'invoice_received': payment.invoice_received,
                'details': details
            })
        
        return jsonify({'success': True, 'driver': {'id': driver.driver_id, 'name': driver.name}, 'payments': result}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/api/payments/<int:payment_id>/pdf', methods=['GET'])
def generate_payment_pdf(payment_id):
    try:
        # Obter pagamento específico com informações do motorista
        payment_data = db.session.query(Payment, Driver).join(Driver).filter(Payment.id == payment_id).first()
        
        if not payment_data:
            return jsonify({'success': False, 'error': 'Pagamento não encontrado'}), 404
        
        payment, driver = payment_data
        
        # Criar diretório para relatórios se não existir
        reports_dir = os.path.join(current_app.config['REPORTS_FOLDER'], 'pdf')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Nome do arquivo PDF
        pdf_filename = f"Relatorio_Pagamento_{driver.driver_id}_{driver.name.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        
        # Gerar PDF
        generate_pdf_report(payment, driver, pdf_path)
        
        # Enviar arquivo PDF
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_pdf_report(payment, driver, output_path):
    # Configurar documento PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Criar estilo personalizado para título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Centralizado
        spaceAfter=12
    )
    
    # Criar estilo personalizado para subtítulo
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=1,  # Centralizado
        spaceAfter=12
    )
    
    # Criar estilo personalizado para texto normal
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Elementos do PDF
    elements = []
    
    # Logo da empresa (se disponível)
    logo_path = os.path.join(current_app.config['STATIC_FOLDER'], 'assets', 'MENEZESLOG-MarcaAzulH.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 0.75 * inch
        logo.drawWidth = 2.5 * inch
        elements.append(logo)
        elements.append(Spacer(1, 0.25 * inch))
    
    # Título
    elements.append(Paragraph("DEMONSTRATIVO DE PAGAMENTO", title_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    # Informações do motorista
    elements.append(Paragraph(f"Motorista: {driver.name}", subtitle_style))
    elements.append(Paragraph(f"ID: {driver.driver_id}", normal_style))
    elements.append(Paragraph(f"Referência: {payment.reference}", normal_style))
    elements.append(Paragraph(f"Data: {payment.payment_date.strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 0.25 * inch))
    
    # Converter detalhes de string para dicionário
    details = {}
    if payment.details:
        try:
            details = eval(payment.details)
        except:
            details = {}
    
    # Obter tipos de serviço
    service_types = {}
    for st in ServiceType.query.all():
        service_types[st.type_id] = st.description
    
    # Tabela de detalhes por tipo de serviço
    if details:
        # Cabeçalho da tabela
        table_data = [['Tipo de Serviço', 'Descrição', 'Quantidade', 'Valor Unitário (R$)', 'Total (R$)']]
        
        # Dados da tabela
        for service_type, service_data in details.items():
            service_type_int = int(service_type)
            description = service_types.get(service_type_int, f"Tipo {service_type}")
            count = service_data['count']
            value_per_item = service_data['value_per_item']
            total = service_data['total']
            
            table_data.append([
                service_type,
                description,
                count,
                f"{value_per_item:.2f}",
                f"{total:.2f}"
            ])
        
        # Adicionar linha de total
        table_data.append(['', '', '', 'TOTAL', f"{payment.amount:.2f}"])
        
        # Criar tabela
        table = Table(table_data, colWidths=[0.75*inch, 2*inch, 1*inch, 1.25*inch, 1*inch])
        
        # Estilo da tabela
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 0.25 * inch))
    
    # Gerar gráfico de distribuição por tipo de serviço
    if details:
        # Criar gráfico
        plt.figure(figsize=(8, 4))
        
        # Dados para o gráfico
        service_types_labels = []
        service_counts = []
        service_amounts = []
        
        for service_type, service_data in details.items():
            service_type_int = int(service_type)
            description = service_types.get(service_type_int, f"Tipo {service_type}")
            service_types_labels.append(f"{description} ({service_type})")
            service_counts.append(service_data['count'])
            service_amounts.append(service_data['total'])
        
        # Criar subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        # Gráfico de quantidade por tipo de serviço
        ax1.bar(service_types_labels, service_counts, color='skyblue')
        ax1.set_title('Quantidade por Tipo de Serviço')
        ax1.set_ylabel('Quantidade')
        ax1.tick_params(axis='x', rotation=45)
        
        # Gráfico de valor por tipo de serviço
        ax2.bar(service_types_labels, service_amounts, color='lightgreen')
        ax2.set_title('Valor por Tipo de Serviço')
        ax2.set_ylabel('Valor (R$)')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Salvar gráfico em buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300)
        buf.seek(0)
        
        # Adicionar gráfico ao PDF
        img = Image(buf)
        img.drawHeight = 3 * inch
        img.drawWidth = 6 * inch
        elements.append(img)
        
        # Fechar figura para liberar memória
        plt.close(fig)
    
    # Adicionar informações de pagamento
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph("Informações de Pagamento", subtitle_style))
    elements.append(Paragraph(f"Status: {payment.status.upper()}", normal_style))
    
    if payment.invoice_received:
        invoice_status = "Recebida"
        if payment.invoice_date:
            invoice_status += f" em {payment.invoice_date.strftime('%d/%m/%Y')}"
    else:
        invoice_status = "Pendente"
    
    elements.append(Paragraph(f"Nota Fiscal: {invoice_status}", normal_style))
    elements.append(Spacer(1, 0.25 * inch))
    
    # Rodapé
    elements.append(Paragraph("Este é um documento gerado automaticamente pelo sistema MenezesLog.", normal_style))
    elements.append(Paragraph(f"Data de emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
    
    # Construir PDF
    doc.build(elements)
    
    return output_path
