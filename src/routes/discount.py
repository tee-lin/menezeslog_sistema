from flask import Blueprint, request, jsonify, current_app
from src.models.models import db, DiscountRule, Discount, Payment, Driver
from src.routes.auth import token_required
import datetime

discount_bp = Blueprint('discount', __name__)

# Rota para listar regras de desconto
@discount_bp.route('/rules', methods=['GET'])
@token_required
def list_discount_rules(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter todas as regras de desconto
    rules = DiscountRule.query.all()
    
    return jsonify({
        'rules': [rule.to_dict() for rule in rules]
    }), 200

# Rota para criar regra de desconto
@discount_bp.route('/rules', methods=['POST'])
@token_required
def create_discount_rule(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('name') or not data.get('discount_type'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Criar regra
    rule = DiscountRule(
        name=data.get('name'),
        description=data.get('description'),
        discount_type=data.get('discount_type'),
        max_value=float(data.get('max_value')) if data.get('max_value') else None,
        max_installments=int(data.get('max_installments', 1)),
        active=data.get('active', True)
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de desconto criada com sucesso!',
        'rule': rule.to_dict()
    }), 201

# Rota para atualizar regra de desconto
@discount_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
def update_discount_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra
    rule = DiscountRule.query.get_or_404(rule_id)
    
    data = request.get_json()
    
    # Atualizar campos
    if 'name' in data:
        rule.name = data['name']
    if 'description' in data:
        rule.description = data['description']
    if 'discount_type' in data:
        rule.discount_type = data['discount_type']
    if 'max_value' in data:
        rule.max_value = float(data['max_value']) if data['max_value'] else None
    if 'max_installments' in data:
        rule.max_installments = int(data['max_installments'])
    if 'active' in data:
        rule.active = data['active']
    
    rule.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de desconto atualizada com sucesso!',
        'rule': rule.to_dict()
    }), 200

# Rota para excluir regra de desconto
@discount_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@token_required
def delete_discount_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra
    rule = DiscountRule.query.get_or_404(rule_id)
    
    # Verificar se a regra está sendo usada
    if Discount.query.filter_by(discount_rule_id=rule_id).first():
        return jsonify({'message': 'Esta regra está sendo usada e não pode ser excluída!'}), 400
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de desconto excluída com sucesso!'
    }), 200

# Rota para criar desconto para um motorista
@discount_bp.route('/', methods=['POST'])
@token_required
def create_discount(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('driver_id') or not data.get('discount_rule_id') or not data.get('total_value'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Verificar se o motorista existe
    driver = Driver.query.filter_by(driver_id=data.get('driver_id')).first()
    if not driver:
        return jsonify({'message': 'Motorista não encontrado!'}), 404
    
    # Verificar se a regra existe
    rule = DiscountRule.query.get(data.get('discount_rule_id'))
    if not rule:
        return jsonify({'message': 'Regra de desconto não encontrada!'}), 404
    
    # Validar valor máximo
    total_value = float(data.get('total_value'))
    if rule.max_value and total_value > rule.max_value:
        return jsonify({'message': f'Valor excede o máximo permitido para esta regra ({rule.max_value})!'}), 400
    
    # Validar número de parcelas
    installments = int(data.get('installments', 1))
    if installments > rule.max_installments:
        return jsonify({'message': f'Número de parcelas excede o máximo permitido para esta regra ({rule.max_installments})!'}), 400
    
    # Calcular valor da parcela
    installment_value = total_value / installments
    
    # Criar desconto
    discount = Discount(
        driver_id=data.get('driver_id'),
        discount_rule_id=data.get('discount_rule_id'),
        description=data.get('description'),
        total_value=total_value,
        installments=installments,
        installment_value=installment_value,
        current_installment=1,
        status='pending',
        reference=data.get('reference')
    )
    
    db.session.add(discount)
    
    # Obter período atual
    today = datetime.date.today()
    if today.day <= 15:
        start_date = datetime.date(today.year, today.month, 1)
        end_date = datetime.date(today.year, today.month, 15)
    else:
        start_date = datetime.date(today.year, today.month, 16)
        end_date = (datetime.date(today.year, today.month + 1, 1) if today.month < 12 else datetime.date(today.year + 1, 1, 1)) - datetime.timedelta(days=1)
    
    period = f"{start_date.isoformat()}_{end_date.isoformat()}"
    
    # Verificar se existe pagamento para o período atual
    payment = Payment.query.filter_by(driver_id=data.get('driver_id'), period=period).first()
    
    if payment:
        # Aplicar primeira parcela do desconto
        payment.discount_value += installment_value
        payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
        
        # Atualizar status do desconto
        if installments == 1:
            discount.status = 'completed'
        else:
            discount.status = 'in_progress'
    
    db.session.commit()
    
    return jsonify({
        'message': 'Desconto criado com sucesso!',
        'discount': discount.to_dict()
    }), 201

# Rota para listar descontos de um motorista
@discount_bp.route('/driver/<string:driver_id>', methods=['GET'])
@token_required
def list_driver_discounts(current_user, driver_id):
    # Verificar se o usuário é admin ou o próprio motorista
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o motorista existe
    driver = Driver.query.filter_by(driver_id=driver_id).first()
    if not driver:
        return jsonify({'message': 'Motorista não encontrado!'}), 404
    
    # Filtrar por status (opcional)
    status = request.args.get('status')
    
    # Filtrar descontos
    query = Discount.query.filter_by(driver_id=driver_id)
    if status:
        query = query.filter_by(status=status)
    
    discounts = query.order_by(Discount.created_at.desc()).all()
    
    return jsonify({
        'driver': driver.to_dict(),
        'discounts': [discount.to_dict() for discount in discounts]
    }), 200

# Rota para atualizar status de um desconto
@discount_bp.route('/<int:discount_id>/status', methods=['PUT'])
@token_required
def update_discount_status(current_user, discount_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter o desconto
    discount = Discount.query.get_or_404(discount_id)
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('status'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar status
    discount.status = data.get('status')
    discount.updated_at = datetime.datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Status do desconto atualizado com sucesso!',
        'discount': discount.to_dict()
    }), 200

# Rota para processar parcelas de descontos
@discount_bp.route('/process-installments', methods=['POST'])
@token_required
def process_discount_installments(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter período atual
    today = datetime.date.today()
    if today.day <= 15:
        start_date = datetime.date(today.year, today.month, 1)
        end_date = datetime.date(today.year, today.month, 15)
    else:
        start_date = datetime.date(today.year, today.month, 16)
        end_date = (datetime.date(today.year, today.month + 1, 1) if today.month < 12 else datetime.date(today.year + 1, 1, 1)) - datetime.timedelta(days=1)
    
    period = f"{start_date.isoformat()}_{end_date.isoformat()}"
    
    # Obter descontos em andamento
    discounts = Discount.query.filter_by(status='in_progress').all()
    
    # Inicializar contadores
    processed_count = 0
    completed_count = 0
    
    for discount in discounts:
        # Verificar se existe pagamento para o período atual
        payment = Payment.query.filter_by(driver_id=discount.driver_id, period=period).first()
        
        if payment:
            # Aplicar parcela do desconto
            payment.discount_value += discount.installment_value
            payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
            
            # Atualizar parcela atual
            discount.current_installment += 1
            
            # Verificar se é a última parcela
            if discount.current_installment > discount.installments:
                discount.status = 'completed'
                completed_count += 1
            
            processed_count += 1
    
    db.session.commit()
    
    return jsonify({
        'message': 'Parcelas de descontos processadas com sucesso!',
        'processed_count': processed_count,
        'completed_count': completed_count,
        'period': period
    }), 200
