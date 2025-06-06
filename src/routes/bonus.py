from flask import Blueprint, request, jsonify, current_app
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
    if not data or not data.get('name') or not data.get('bonus_type') or not data.get('value'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Criar regra
    rule = BonusRule(
        name=data.get('name'),
        description=data.get('description'),
        service_type=data.get('service_type'),
        bonus_type=data.get('bonus_type'),
        value=float(data.get('value')),
        condition_type=data.get('condition_type'),
        condition_value=data.get('condition_value'),
        active=data.get('active', True),
        start_date=datetime.datetime.strptime(data.get('start_date'), '%Y-%m-%d').date() if data.get('start_date') else None,
        end_date=datetime.datetime.strptime(data.get('end_date'), '%Y-%m-%d').date() if data.get('end_date') else None
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de bonificação criada com sucesso!',
        'rule': rule.to_dict()
    }), 201

# Rota para atualizar regra de bonificação
@bonus_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
def update_bonus_rule(current_user, rule_id):
    # Verificar se o usuário é admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Obter a regra
    rule = BonusRule.query.get_or_404(rule_id)
    
    data = request.get_json()
    
    # Atualizar campos
    if 'name' in data:
        rule.name = data['name']
    if 'description' in data:
        rule.description = data['description']
    if 'service_type' in data:
        rule.service_type = data['service_type']
    if 'bonus_type' in data:
        rule.bonus_type = data['bonus_type']
    if 'value' in data:
        rule.value = float(data['value'])
    if 'condition_type' in data:
        rule.condition_type = data['condition_type']
    if 'condition_value' in data:
        rule.condition_value = data['condition_value']
    if 'active' in data:
        rule.active = data['active']
    if 'start_date' in data:
        rule.start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
    if 'end_date' in data:
        rule.end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None
    
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
    
    # Obter a regra
    rule = BonusRule.query.get_or_404(rule_id)
    
    # Verificar se a regra está sendo usada
    if Bonus.query.filter_by(bonus_rule_id=rule_id).first():
        return jsonify({'message': 'Esta regra está sendo usada e não pode ser excluída!'}), 400
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Regra de bonificação excluída com sucesso!'
    }), 200

# Rota para aplicar bonificações ao período atual
@bonus_bp.route('/apply', methods=['POST'])
@token_required
def apply_bonuses(current_user):
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
    
    # Obter regras de bonificação ativas
    active_rules = BonusRule.query.filter_by(active=True).all()
    
    # Inicializar contadores
    applied_count = 0
    driver_count = 0
    
    # Obter todos os pagamentos do período
    payments = Payment.query.filter_by(period=period).all()
    
    for payment in payments:
        driver_id = payment.driver_id
        
        # Limpar bonificações anteriores
        Bonus.query.filter_by(driver_id=driver_id, period=period).delete()
        
        # Resetar valor de bonificação no pagamento
        payment.bonus_value = 0.0
        
        # Aplicar bonificações por tipo de serviço
        for rule in active_rules:
            if rule.condition_type == 'service_type' and rule.service_type is not None:
                # Contar entregas deste tipo
                deliveries = Delivery.query.filter_by(
                    driver_id=driver_id,
                    payment_period=period,
                    service_type=rule.service_type
                ).all()
                
                if deliveries:
                    # Calcular valor da bonificação
                    if rule.bonus_type == 'fixed':
                        # Valor fixo por entrega
                        bonus_value = rule.value * len(deliveries)
                    else:
                        # Percentual sobre o valor base
                        base_value = sum(d.base_value for d in deliveries)
                        bonus_value = base_value * (rule.value / 100)
                    
                    # Criar bonificação
                    bonus = Bonus(
                        driver_id=driver_id,
                        bonus_rule_id=rule.id,
                        period=period,
                        value=bonus_value,
                        description=f"Bonificação por {len(deliveries)} entregas do tipo {rule.service_type}"
                    )
                    
                    db.session.add(bonus)
                    payment.bonus_value += bonus_value
                    applied_count += 1
            
            elif rule.condition_type == 'volume':
                # Bonificação por volume
                try:
                    min_volume = int(rule.condition_value)
                    if payment.deliveries_count >= min_volume:
                        # Calcular valor da bonificação
                        if rule.bonus_type == 'fixed':
                            # Valor fixo
                            bonus_value = rule.value
                        else:
                            # Percentual sobre o valor base
                            bonus_value = payment.base_value * (rule.value / 100)
                        
                        # Criar bonificação
                        bonus = Bonus(
                            driver_id=driver_id,
                            bonus_rule_id=rule.id,
                            period=period,
                            value=bonus_value,
                            description=f"Bonificação por volume: {payment.deliveries_count} entregas"
                        )
                        
                        db.session.add(bonus)
                        payment.bonus_value += bonus_value
                        applied_count += 1
                except:
                    continue
        
        # Atualizar valor total do pagamento
        payment.total_value = payment.base_value + payment.bonus_value - payment.discount_value
        driver_count += 1
    
    # Commit das alterações
    db.session.commit()
    
    return jsonify({
        'message': 'Bonificações aplicadas com sucesso!',
        'applied_count': applied_count,
        'driver_count': driver_count,
        'period': period
    }), 200

# Rota para listar bonificações de um motorista
@bonus_bp.route('/driver/<string:driver_id>', methods=['GET'])
@token_required
def list_driver_bonuses(current_user, driver_id):
    # Verificar se o usuário é admin ou o próprio motorista
    if current_user.role != 'admin' and (current_user.role != 'driver' or current_user.driver_id != driver_id):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o motorista existe
    driver = Driver.query.filter_by(driver_id=driver_id).first()
    if not driver:
        return jsonify({'message': 'Motorista não encontrado!'}), 404
    
    # Obter período (opcional)
    period = request.args.get('period')
    
    # Filtrar bonificações
    query = Bonus.query.filter_by(driver_id=driver_id)
    if period:
        query = query.filter_by(period=period)
    
    bonuses = query.order_by(Bonus.created_at.desc()).all()
    
    return jsonify({
        'driver': driver.to_dict(),
        'bonuses': [bonus.to_dict() for bonus in bonuses]
    }), 200
