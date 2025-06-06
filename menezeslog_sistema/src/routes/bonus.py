from flask import Blueprint, request, jsonify
from src.models.models import db, BonusRule, Bonus, Payment, Delivery, Driver
from src.routes.auth import token_required
import datetime

bonus_bp = Blueprint('bonus', __name__)

# Rota para listar regras de bonificação
@bonus_bp.route('/rules', methods=['GET'])
@token_required
def list_bonus_rules(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter todas as regras de bonificação
    rules = BonusRule.query.all()
    
    return jsonify({
        'rules': [rule.to_dict() for rule in rules]
    }), 200

# Rota para criar regra de bonificação
@bonus_bp.route('/rules', methods=['POST'])
@token_required
def create_bonus_rule(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('name'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Criar regra de bonificação
    rule = BonusRule(
        name=data.get('name'),
        description=data.get('description'),
        service_type=data.get('service_type'),
        min_deliveries=data.get('min_deliveries', 0),
        value_type=data.get('value_type', 'fixed'),
        value=data.get('value', 0.0),
        active=data.get('active', True)
    )
    
    # Converter datas se fornecidas
    if data.get('start_date'):
        try:
            rule.start_date = datetime.datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        except:
            return jsonify({'message': 'Formato de data inválido para data de início! Use YYYY-MM-DD'}), 400
    
    if data.get('end_date'):
        try:
            rule.end_date = datetime.datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        except:
            return jsonify({'message': 'Formato de data inválido para data de fim! Use YYYY-MM-DD'}), 400
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de bonificação criada com sucesso!',
        'rule': rule.to_dict()
    }), 201

# Rota para obter detalhes de uma regra de bonificação
@bonus_bp.route('/rules/<int:rule_id>', methods=['GET'])
@token_required
def get_bonus_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra de bonificação
    rule = BonusRule.query.get_or_404(rule_id)
    
    return jsonify({
        'rule': rule.to_dict()
    }), 200

# Rota para atualizar regra de bonificação
@bonus_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
def update_bonus_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra de bonificação
    rule = BonusRule.query.get_or_404(rule_id)
    
    data = request.get_json()
    
    # Validar dados
    if not data:
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar campos
    if 'name' in data:
        rule.name = data.get('name')
    
    if 'description' in data:
        rule.description = data.get('description')
    
    if 'service_type' in data:
        rule.service_type = data.get('service_type')
    
    if 'min_deliveries' in data:
        rule.min_deliveries = data.get('min_deliveries')
    
    if 'value_type' in data:
        rule.value_type = data.get('value_type')
    
    if 'value' in data:
        rule.value = data.get('value')
    
    if 'active' in data:
        rule.active = data.get('active')
    
    # Converter datas se fornecidas
    if 'start_date' in data:
        if data.get('start_date'):
            try:
                rule.start_date = datetime.datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            except:
                return jsonify({'message': 'Formato de data inválido para data de início! Use YYYY-MM-DD'}), 400
        else:
            rule.start_date = None
    
    if 'end_date' in data:
        if data.get('end_date'):
            try:
                rule.end_date = datetime.datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            except:
                return jsonify({'message': 'Formato de data inválido para data de fim! Use YYYY-MM-DD'}), 400
        else:
            rule.end_date = None
    
    rule.updated_at = datetime.datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de bonificação atualizada com sucesso!',
        'rule': rule.to_dict()
    }), 200

# Rota para excluir regra de bonificação
@bonus_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@token_required
def delete_bonus_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra de bonificação
    rule = BonusRule.query.get_or_404(rule_id)
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de bonificação excluída com sucesso!'
    }), 200

# Rota para aplicar bonificações
@bonus_bp.route('/apply', methods=['POST'])
@token_required
def apply_bonuses(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('period'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    period = data.get('period')
    driver_id = data.get('driver_id')  # Opcional
    
    # Obter regras de bonificação ativas
    rules = BonusRule.query.filter_by(active=True).all()
    
    if not rules:
        return jsonify({'message': 'Nenhuma regra de bonificação ativa encontrada!'}), 404
    
    # Construir query para pagamentos
    query = Payment.query.filter_by(period=period)
    
    if driver_id:
        query = query.filter_by(driver_id=driver_id)
    
    payments = query.all()
    
    if not payments:
        return jsonify({'message': 'Nenhum pagamento encontrado para o período especificado!'}), 404
    
    # Aplicar bonificações
    results = []
    
    for payment in payments:
        # Obter entregas do motorista no período
        deliveries = Delivery.query.filter_by(driver_id=payment.driver_id, payment_period=period).all()
        
        if not deliveries:
            continue
        
        # Agrupar entregas por tipo de serviço
        deliveries_by_type = {}
        for delivery in deliveries:
            service_type = delivery.service_type
            if service_type not in deliveries_by_type:
                deliveries_by_type[service_type] = []
            
            deliveries_by_type[service_type].append(delivery)
        
        # Aplicar regras de bonificação
        total_bonus = 0.0
        bonuses = []
        
        for rule in rules:
            # Verificar se a regra está dentro do período válido
            today = datetime.date.today()
            if rule.start_date and rule.start_date > today:
                continue
            
            if rule.end_date and rule.end_date < today:
                continue
            
            # Verificar tipo de serviço
            if rule.service_type is not None:
                if rule.service_type not in deliveries_by_type:
                    continue
                
                deliveries_count = len(deliveries_by_type[rule.service_type])
                
                # Verificar mínimo de entregas
                if deliveries_count < rule.min_deliveries:
                    continue
                
                # Calcular valor da bonificação
                if rule.value_type == 'fixed':
                    bonus_value = rule.value * deliveries_count
                else:  # percentage
                    base_value = sum(delivery.base_value for delivery in deliveries_by_type[rule.service_type])
                    bonus_value = base_value * (rule.value / 100)
                
                # Criar bonificação
                bonus = Bonus(
                    driver_id=payment.driver_id,
                    period=period,
                    description=f"Bonificação: {rule.name} (Tipo {rule.service_type})",
                    value=bonus_value
                )
                
                db.session.add(bonus)
                bonuses.append(bonus)
                total_bonus += bonus_value
            else:
                # Regra para todos os tipos de serviço
                deliveries_count = len(deliveries)
                
                # Verificar mínimo de entregas
                if deliveries_count < rule.min_deliveries:
                    continue
                
                # Calcular valor da bonificação
                if rule.value_type == 'fixed':
                    bonus_value = rule.value * deliveries_count
                else:  # percentage
                    base_value = sum(delivery.base_value for delivery in deliveries)
                    bonus_value = base_value * (rule.value / 100)
                
                # Criar bonificação
                bonus = Bonus(
                    driver_id=payment.driver_id,
                    period=period,
                    description=f"Bonificação: {rule.name} (Todos os tipos)",
                    value=bonus_value
                )
                
                db.session.add(bonus)
                bonuses.append(bonus)
                total_bonus += bonus_value
        
        # Atualizar pagamento
        payment.bonus_value = total_bonus
        payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
        
        # Atualizar entregas
        if bonuses:
            # Distribuir bonificação entre as entregas proporcionalmente
            for delivery in deliveries:
                delivery_ratio = delivery.base_value / payment.base_value if payment.base_value > 0 else 1.0 / len(deliveries)
                delivery.bonus_value = total_bonus * delivery_ratio
                delivery.total_value = delivery.base_value + delivery.bonus_value
        
        # Adicionar resultado
        driver = Driver.query.filter_by(driver_id=payment.driver_id).first()
        results.append({
            'driver_id': payment.driver_id,
            'driver_name': driver.name if driver else f"Motorista {payment.driver_id}",
            'bonuses_count': len(bonuses),
            'total_bonus': total_bonus,
            'new_total': payment.total_value
        })
    
    # Commit das alterações
    db.session.commit()
    
    return jsonify({
        'message': 'Bonificações aplicadas com sucesso!',
        'results': results
    }), 200

# Rota para listar bonificações
@bonus_bp.route('/', methods=['GET'])
@token_required
def list_bonuses(current_user):
    # Verificar se o usuário é admin
    if current_user.role == 'admin':
        # Filtrar por período (opcional)
        period = request.args.get('period')
        
        # Filtrar por motorista (opcional)
        driver_id = request.args.get('driver_id')
        
        # Construir query
        query = Bonus.query
        
        if period:
            query = query.filter_by(period=period)
        
        if driver_id:
            query = query.filter_by(driver_id=driver_id)
        
        # Ordenar por data de criação (mais recente primeiro)
        bonuses = query.order_by(Bonus.created_at.desc()).all()
        
        # Incluir informações do motorista
        result = []
        for bonus in bonuses:
            driver = Driver.query.filter_by(driver_id=bonus.driver_id).first()
            bonus_dict = bonus.to_dict()
            bonus_dict['driver_name'] = driver.name if driver else f"Motorista {bonus.driver_id}"
            result.append(bonus_dict)
        
        return jsonify({
            'bonuses': result
        }), 200
    
    # Se for motorista, retornar apenas suas bonificações
    elif current_user.role == 'driver':
        # Filtrar por período (opcional)
        period = request.args.get('period')
        
        # Construir query
        query = Bonus.query.filter_by(driver_id=current_user.driver_id)
        
        if period:
            query = query.filter_by(period=period)
        
        # Ordenar por data de criação (mais recente primeiro)
        bonuses = query.order_by(Bonus.created_at.desc()).all()
        
        return jsonify({
            'bonuses': [bonus.to_dict() for bonus in bonuses]
        }), 200
    
    else:
        return jsonify({'message': 'Acesso não autorizado!'}), 403

# Rota para adicionar bonificação manual
@bonus_bp.route('/', methods=['POST'])
@token_required
def add_manual_bonus(current_user):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    # Validar dados
    if not data or not data.get('driver_id') or not data.get('period') or not data.get('value'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Verificar se o motorista existe
    driver = Driver.query.filter_by(driver_id=data.get('driver_id')).first()
    if not driver:
        return jsonify({'message': 'Motorista não encontrado!'}), 404
    
    # Verificar se o pagamento existe
    payment = Payment.query.filter_by(driver_id=data.get('driver_id'), period=data.get('period')).first()
    if not payment:
        return jsonify({'message': 'Pagamento não encontrado para o período especificado!'}), 404
    
    # Criar bonificação
    bonus = Bonus(
        driver_id=data.get('driver_id'),
        period=data.get('period'),
        description=data.get('description', 'Bonificação manual'),
        value=float(data.get('value'))
    )
    
    db.session.add(bonus)
    
    # Atualizar pagamento
    payment.bonus_value += bonus.value
    payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
    
    db.session.commit()
    
    return jsonify({
        'message': 'Bonificação adicionada com sucesso!',
        'bonus': bonus.to_dict(),
        'payment': payment.to_dict()
    }), 201

# Rota para excluir bonificação
@bonus_bp.route('/<int:bonus_id>', methods=['DELETE'])
@token_required
def delete_bonus(current_user, bonus_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a bonificação
    bonus = Bonus.query.get_or_404(bonus_id)
    
    # Obter o pagamento
    payment = Payment.query.filter_by(driver_id=bonus.driver_id, period=bonus.period).first()
    
    if payment:
        # Atualizar pagamento
        payment.bonus_value -= bonus.value
        payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
    
    db.session.delete(bonus)
    db.session.commit()
    
    return jsonify({
        'message': 'Bonificação excluída com sucesso!'
    }), 200
