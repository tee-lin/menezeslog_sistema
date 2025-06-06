from flask import Blueprint, request, jsonify
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
    if not data or not data.get('name'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Criar regra de desconto
    rule = DiscountRule(
        name=data.get('name'),
        description=data.get('description'),
        discount_type=data.get('discount_type', 'extravio'),
        value_type=data.get('value_type', 'fixed'),
        value=data.get('value', 0.0),
        max_installments=data.get('max_installments', 1),
        active=data.get('active', True)
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de desconto criada com sucesso!',
        'rule': rule.to_dict()
    }), 201

# Rota para obter detalhes de uma regra de desconto
@discount_bp.route('/rules/<int:rule_id>', methods=['GET'])
@token_required
def get_discount_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra de desconto
    rule = DiscountRule.query.get_or_404(rule_id)
    
    return jsonify({
        'rule': rule.to_dict()
    }), 200

# Rota para atualizar regra de desconto
@discount_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
def update_discount_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra de desconto
    rule = DiscountRule.query.get_or_404(rule_id)
    
    data = request.get_json()
    
    # Validar dados
    if not data:
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar campos
    if 'name' in data:
        rule.name = data.get('name')
    
    if 'description' in data:
        rule.description = data.get('description')
    
    if 'discount_type' in data:
        rule.discount_type = data.get('discount_type')
    
    if 'value_type' in data:
        rule.value_type = data.get('value_type')
    
    if 'value' in data:
        rule.value = data.get('value')
    
    if 'max_installments' in data:
        rule.max_installments = data.get('max_installments')
    
    if 'active' in data:
        rule.active = data.get('active')
    
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
    
    # Obter a regra de desconto
    rule = DiscountRule.query.get_or_404(rule_id)
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de desconto excluída com sucesso!'
    }), 200

# Rota para listar descontos
@discount_bp.route('/', methods=['GET'])
@token_required
def list_discounts(current_user):
    # Verificar se o usuário é admin
    if current_user.role == 'admin':
        # Filtrar por status (opcional)
        status = request.args.get('status')
        
        # Filtrar por motorista (opcional)
        driver_id = request.args.get('driver_id')
        
        # Construir query
        query = Discount.query
        
        if status:
            query = query.filter_by(status=status)
        
        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        
        # Ordenar por data de criação (mais recente primeiro)
        discounts = query.order_by(Discount.created_at.desc()).all()
        
        # Incluir informações do motorista
        result = []
        for discount in discounts:
            driver = Driver.query.filter_by(driver_id=discount.driver_id).first()
            discount_dict = discount.to_dict()
            discount_dict['driver_name'] = driver.name if driver else f"Motorista {discount.driver_id}"
            result.append(discount_dict)
        
        return jsonify({
            'discounts': result
        }), 200
    
    # Se for motorista, retornar apenas seus descontos
    elif current_user.role == 'driver':
        # Filtrar por status (opcional)
        status = request.args.get('status')
        
        # Construir query
        query = Discount.query.filter_by(driver_id=current_user.driver_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Ordenar por data de criação (mais recente primeiro)
        discounts = query.order_by(Discount.created_at.desc()).all()
        
        return jsonify({
            'discounts': [discount.to_dict() for discount in discounts]
        }), 200
    
    else:
        return jsonify({'message': 'Acesso não autorizado!'}), 403

# Rota para adicionar desconto
@discount_bp.route('/', methods=['POST'])
@token_required
def add_discount(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('driver_id') or not data.get('total_value'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Verificar se o motorista existe
    driver = Driver.query.filter_by(driver_id=data.get('driver_id')).first()
    if not driver:
        return jsonify({'message': 'Motorista não encontrado!'}), 404
    
    # Calcular valor da parcela
    total_value = float(data.get('total_value'))
    installments = int(data.get('installments', 1))
    installment_value = total_value / installments
    
    # Criar desconto
    discount = Discount(
        driver_id=data.get('driver_id'),
        description=data.get('description', 'Desconto'),
        total_value=total_value,
        installments=installments,
        installment_value=installment_value,
        current_installment=1,
        status='pending',
        start_date=datetime.date.today()
    )
    
    db.session.add(discount)
    db.session.commit()
    
    return jsonify({
        'message': 'Desconto adicionado com sucesso!',
        'discount': discount.to_dict()
    }), 201

# Rota para atualizar status de desconto
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

# Rota para aplicar descontos ao período atual
@discount_bp.route('/apply', methods=['POST'])
@token_required
def apply_discounts(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('period'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    period = data.get('period')
    driver_id = data.get('driver_id')  # Opcional
    
    # Obter descontos ativos
    query = Discount.query.filter(Discount.status.in_(['pending', 'in_progress']))
    
    if driver_id:
        query = query.filter_by(driver_id=driver_id)
    
    discounts = query.all()
    
    if not discounts:
        return jsonify({'message': 'Nenhum desconto ativo encontrado!'}), 404
    
    # Construir query para pagamentos
    payment_query = Payment.query.filter_by(period=period)
    
    if driver_id:
        payment_query = payment_query.filter_by(driver_id=driver_id)
    
    payments = payment_query.all()
    
    if not payments:
        return jsonify({'message': 'Nenhum pagamento encontrado para o período especificado!'}), 404
    
    # Aplicar descontos
    results = []
    
    for payment in payments:
        # Obter descontos do motorista
        driver_discounts = [d for d in discounts if d.driver_id == payment.driver_id]
        
        if not driver_discounts:
            continue
        
        # Aplicar descontos
        total_discount = 0.0
        applied_discounts = []
        
        for discount in driver_discounts:
            # Verificar se já foi aplicado o número máximo de parcelas
            if discount.current_installment > discount.installments:
                # Marcar como concluído
                discount.status = 'completed'
                continue
            
            # Aplicar parcela
            total_discount += discount.installment_value
            
            # Atualizar desconto
            discount.current_installment += 1
            discount.status = 'in_progress'
            
            if discount.current_installment > discount.installments:
                discount.status = 'completed'
            
            applied_discounts.append(discount)
        
        # Atualizar pagamento
        payment.discount_value = total_discount
        payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
        
        # Adicionar resultado
        driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
        results.append({
            'driver_id': payment.driver_id,
            'driver_name': driver.name if driver else f"Motorista {payment.driver_id}",
            'discounts_count': len(applied_discounts),
            'total_discount': total_discount,
            'new_total': payment.total_value
        })
    
    # Commit das alterações
    db.session.commit()
    
    return jsonify({
        'message': 'Descontos aplicados com sucesso!',
        'results': results
    }), 200

# Rota para excluir desconto
@discount_bp.route('/<int:discount_id>', methods=['DELETE'])
@token_required
def delete_discount(current_user, discount_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter o desconto
    discount = Discount.query.get_or_404(discount_id)
    
    # Verificar se o desconto já foi aplicado
    if discount.status != 'pending':
        return jsonify({'message': 'Não é possível excluir um desconto que já foi aplicado!'}), 400
    
    db.session.delete(discount)
    db.session.commit()
    
    return jsonify({
        'message': 'Desconto excluído com sucesso!'
    }), 200
