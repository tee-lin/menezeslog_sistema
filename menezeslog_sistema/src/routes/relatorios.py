from flask import Blueprint, request, jsonify, current_app, send_file
import os
import pandas as pd
from src.models.models import db, Driver, Payment, ServiceType
from datetime import datetime
import zipfile
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/api/relatorios/todos', methods=['GET'])
def get_all_reports():
    try:
        # Criar diretório para relatórios se não existir
        reports_dir = os.path.join(current_app.config['REPORTS_FOLDER'], 'pdf')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Obter todos os pagamentos com informações do motorista
        payments = db.session.query(Payment, Driver).join(Driver).all()
        
        # Criar arquivo ZIP em memória
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Gerar relatório para cada pagamento
            for payment, driver in payments:
                # Nome do arquivo PDF
                pdf_filename = f"Relatorio_Pagamento_{driver.driver_id}_{driver.name.replace(' ', '_')}.pdf"
                pdf_path = os.path.join(reports_dir, pdf_filename)
                
                # Gerar PDF
                generate_pdf_report(payment, driver, pdf_path)
                
                # Adicionar ao ZIP
                zf.write(pdf_path, pdf_filename)
        
        # Mover o ponteiro para o início do arquivo
        memory_file.seek(0)
        
        # Enviar arquivo ZIP
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='Relatorios_Pagamento_Motoristas.zip'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@relatorios_bp.route('/api/relatorios/motorista/<driver_id>', methods=['GET'])
def get_driver_report(driver_id):
    try:
        # Obter motorista pelo ID
        driver = Driver.query.filter_by(driver_id=driver_id).first()
        
        if not driver:
            return jsonify({'success': False, 'error': 'Motorista não encontrado'}), 404
        
        # Obter último pagamento do motorista
        payment = Payment.query.filter_by(driver_id=driver.id).order_by(Payment.payment_date.desc()).first()
        
        if not payment:
            return jsonify({'success': False, 'error': 'Nenhum pagamento encontrado para este motorista'}), 404
        
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

@relatorios_bp.route('/api/relatorios/resumo', methods=['GET'])
def get_summary_report():
    try:
        # Obter todos os pagamentos com informações do motorista
        payments = db.session.query(Payment, Driver).join(Driver).all()
        
        # Criar diretório para relatórios se não existir
        reports_dir = os.path.join(current_app.config['REPORTS_FOLDER'], 'pdf')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Nome do arquivo PDF
        pdf_filename = f"Resumo_Pagamentos_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        
        # Gerar PDF de resumo
        generate_summary_report(payments, pdf_path)
        
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

def generate_summary_report(payments_data, output_path):
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
    elements.append(Paragraph("RESUMO DE PAGAMENTOS", title_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    # Data do relatório
    elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 0.25 * inch))
    
    # Tabela de resumo
    table_data = [['ID', 'Nome do Motorista', 'Valor (R$)', 'Status', 'Nota Fiscal']]
    
    total_amount = 0
    
    for payment, driver in payments_data:
        status = payment.status.upper()
        
        if payment.invoice_received:
            invoice_status = "Recebida"
        else:
            invoice_status = "Pendente"
        
        table_data.append([
            driver.driver_id,
            driver.name,
            f"{payment.amount:.2f}",
            status,
            invoice_status
        ])
        
        total_amount += float(payment.amount)
    
    # Adicionar linha de total
    table_data.append(['', 'TOTAL', f"{total_amount:.2f}", '', ''])
    
    # Criar tabela
    table = Table(table_data, colWidths=[0.75*inch, 2.5*inch, 1*inch, 1*inch, 1*inch])
    
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
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.25 * inch))
    
    # Estatísticas
    elements.append(Paragraph("Estatísticas", subtitle_style))
    elements.append(Paragraph(f"Total de Motoristas: {len(payments_data)}", normal_style))
    elements.append(Paragraph(f"Valor Total: R$ {total_amount:.2f}", normal_style))
    
    # Contar status
    status_counts = {}
    invoice_counts = {'Recebida': 0, 'Pendente': 0}
    
    for payment, _ in payments_data:
        status = payment.status.upper()
        if status not in status_counts:
            status_counts[status] = 0
        status_counts[status] += 1
        
        if payment.invoice_received:
            invoice_counts['Recebida'] += 1
        else:
            invoice_counts['Pendente'] += 1
    
    elements.append(Paragraph("Status de Pagamento:", normal_style))
    for status, count in status_counts.items():
        elements.append(Paragraph(f"- {status}: {count}", normal_style))
    
    elements.append(Paragraph("Status de Nota Fiscal:", normal_style))
    for status, count in invoice_counts.items():
        elements.append(Paragraph(f"- {status}: {count}", normal_style))
    
    elements.append(Spacer(1, 0.25 * inch))
    
    # Rodapé
    elements.append(Paragraph("Este é um documento gerado automaticamente pelo sistema MenezesLog.", normal_style))
    elements.append(Paragraph(f"Data de emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
    
    # Construir PDF
    doc.build(elements)
    
    return output_path
