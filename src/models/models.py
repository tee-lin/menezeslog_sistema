from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

db = SQLAlchemy()

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), unique=True, nullable=False)  # ID do motorista no sistema externo
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    payments = db.relationship('Payment', backref='driver', lazy=True)
    invoices = db.relationship('Invoice', backref='driver', lazy=True)
    bonuses = db.relationship('Bonus', backref='driver', lazy=True)
    discounts = db.relationship('Discount', backref='driver', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'name': self.name,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Delivery(db.Model):
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    awb = db.Column(db.String(50), nullable=False)  # Código de rastreamento
    sender = db.Column(db.String(100), nullable=True)  # Remetente
    service_type = db.Column(db.Integer, nullable=False)  # Tipo de serviço (0, 9, 6, 8)
    weight = db.Column(db.Float, nullable=True)  # Peso capturado
    status = db.Column(db.String(50), nullable=False)  # Status da entrega
    status_description = db.Column(db.String(100), nullable=True)  # Descrição do status
    delivery_date = db.Column(db.Date, nullable=True)  # Data da entrega
    payment_period = db.Column(db.String(20), nullable=False)  # Período de pagamento (ex: "2025-06-01_2025-06-15")
    base_value = db.Column(db.Float, nullable=False)  # Valor base por tipo de serviço
    bonus_value = db.Column(db.Float, default=0.0)  # Valor de bonificação
    total_value = db.Column(db.Float, nullable=False)  # Valor total
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'awb': self.awb,
            'sender': self.sender,
            'service_type': self.service_type,
            'weight': self.weight,
            'status': self.status,
            'status_description': self.status_description,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'payment_period': self.payment_period,
            'base_value': self.base_value,
            'bonus_value': self.bonus_value,
            'total_value': self.total_value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    period = db.Column(db.String(20), nullable=False)  # Período de pagamento (ex: "2025-06-01_2025-06-15")
    start_date = db.Column(db.Date, nullable=False)  # Data de início do período
    end_date = db.Column(db.Date, nullable=False)  # Data de fim do período
    deliveries_count = db.Column(db.Integer, default=0)  # Quantidade de entregas
    base_value = db.Column(db.Float, default=0.0)  # Valor base
    bonus_value = db.Column(db.Float, default=0.0)  # Valor de bonificações
    discount_value = db.Column(db.Float, default=0.0)  # Valor de descontos
    total_value = db.Column(db.Float, default=0.0)  # Valor total
    status = db.Column(db.String(20), default='pending')  # Status: pending, invoice_received, approved, paid
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)  # Nota fiscal associada
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'period': self.period,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'deliveries_count': self.deliveries_count,
            'base_value': self.base_value,
            'bonus_value': self.bonus_value,
            'discount_value': self.discount_value,
            'total_value': self.total_value,
            'status': self.status,
            'invoice_id': self.invoice_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=True)  # Número da nota fiscal
    issue_date = db.Column(db.Date, nullable=True)  # Data de emissão
    file_path = db.Column(db.String(255), nullable=True)  # Caminho do arquivo
    period = db.Column(db.String(20), nullable=False)  # Período de pagamento
    value = db.Column(db.Float, nullable=False)  # Valor da nota fiscal
    status = db.Column(db.String(20), default='pending')  # Status: pending, approved, rejected
    comments = db.Column(db.Text, nullable=True)  # Observações
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamento com Payment é definido na classe Payment
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'invoice_number': self.invoice_number,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'file_path': self.file_path,
            'period': self.period,
            'value': self.value,
            'status': self.status,
            'comments': self.comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BonusRule(db.Model):
    __tablename__ = 'bonus_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nome da regra
    description = db.Column(db.Text, nullable=True)  # Descrição
    service_type = db.Column(db.Integer, nullable=True)  # Tipo de serviço (0, 9, 6, 8) ou None para regras de volume
    bonus_type = db.Column(db.String(20), nullable=False)  # fixed (valor fixo) ou percentage (percentual)
    value = db.Column(db.Float, nullable=False)  # Valor da bonificação
    condition_type = db.Column(db.String(20), nullable=True)  # volume, service_type
    condition_value = db.Column(db.String(100), nullable=True)  # Valor da condição (ex: "100" para volume > 100)
    active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date, nullable=True)  # Data de início (para campanhas temporárias)
    end_date = db.Column(db.Date, nullable=True)  # Data de fim (para campanhas temporárias)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'service_type': self.service_type,
            'bonus_type': self.bonus_type,
            'value': self.value,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'active': self.active,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Bonus(db.Model):
    __tablename__ = 'bonuses'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    bonus_rule_id = db.Column(db.Integer, db.ForeignKey('bonus_rules.id'), nullable=False)
    period = db.Column(db.String(20), nullable=False)  # Período de pagamento
    value = db.Column(db.Float, nullable=False)  # Valor da bonificação
    description = db.Column(db.Text, nullable=True)  # Descrição
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relacionamento com BonusRule
    bonus_rule = db.relationship('BonusRule', backref='bonuses', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'bonus_rule_id': self.bonus_rule_id,
            'period': self.period,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'bonus_rule': self.bonus_rule.to_dict() if self.bonus_rule else None
        }

class DiscountRule(db.Model):
    __tablename__ = 'discount_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nome da regra
    description = db.Column(db.Text, nullable=True)  # Descrição
    discount_type = db.Column(db.String(20), nullable=False)  # loss (extravio), advance (adiantamento), loan (empréstimo)
    max_value = db.Column(db.Float, nullable=True)  # Valor máximo permitido
    max_installments = db.Column(db.Integer, default=1)  # Número máximo de parcelas
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'discount_type': self.discount_type,
            'max_value': self.max_value,
            'max_installments': self.max_installments,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Discount(db.Model):
    __tablename__ = 'discounts'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    discount_rule_id = db.Column(db.Integer, db.ForeignKey('discount_rules.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Descrição
    total_value = db.Column(db.Float, nullable=False)  # Valor total
    installments = db.Column(db.Integer, default=1)  # Número de parcelas
    installment_value = db.Column(db.Float, nullable=False)  # Valor da parcela
    current_installment = db.Column(db.Integer, default=1)  # Parcela atual
    status = db.Column(db.String(20), default='pending')  # Status: pending, in_progress, completed
    reference = db.Column(db.String(100), nullable=True)  # Referência (ex: AWB do extravio)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamento com DiscountRule
    discount_rule = db.relationship('DiscountRule', backref='discounts', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'discount_rule_id': self.discount_rule_id,
            'description': self.description,
            'total_value': self.total_value,
            'installments': self.installments,
            'installment_value': self.installment_value,
            'current_installment': self.current_installment,
            'status': self.status,
            'reference': self.reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'discount_rule': self.discount_rule.to_dict() if self.discount_rule else None
        }

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.Integer, unique=True, nullable=False)  # Código do tipo de serviço (0, 9, 6, 8)
    description = db.Column(db.String(100), nullable=False)  # Descrição
    base_value = db.Column(db.Float, nullable=False)  # Valor base
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type_code': self.type_code,
            'description': self.description,
            'base_value': self.base_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class FileUpload(db.Model):
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Nome do arquivo
    file_path = db.Column(db.String(255), nullable=False)  # Caminho do arquivo
    file_type = db.Column(db.String(20), nullable=False)  # Tipo: csv, excel, invoice
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)  # Se o arquivo foi processado
    process_date = db.Column(db.DateTime, nullable=True)  # Data de processamento
    process_result = db.Column(db.Text, nullable=True)  # Resultado do processamento
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Usuário que fez o upload
    
    # Relacionamento com User
    user = db.relationship('User', backref='uploads', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'processed': self.processed,
            'process_date': self.process_date.isoformat() if self.process_date else None,
            'process_result': self.process_result,
            'uploaded_by': self.uploaded_by
        }
