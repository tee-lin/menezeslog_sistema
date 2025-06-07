from flask import Blueprint, request, jsonify, current_app, send_file
import os
import pandas as pd
from src.models.models import db, Driver, Payment, ServiceType
from datetime import datetime
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
        
        # Temporariamente desativado devido a problemas de dependência no Heroku
        return jsonify({
            'success': False, 
            'error': 'Geração de PDF temporariamente indisponível. Estamos trabalhando para resolver este problema.'
        }), 503
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
