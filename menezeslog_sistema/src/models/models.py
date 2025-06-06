from flask_sqlalchemy import SQLAlchemy
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Definição do modelo User primeiro para resolver dependências
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='driver')  # admin, driver
    name = db.Column(db.String(100))
    driver_id = db.Column(db.String(20))  # Para usuários motoristas
    active = db.Column(db.Boolean, default=True)
    first_access = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'driver_id': self.driver_id,
            'active': self.active,
            'first_access': self.first_access
        }

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    file_path = db.Column(db.String(255))
    period = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
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

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    period = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    deliveries_count = db.Column(db.Integer, default=0)
    base_value = db.Column(db.Float, default=0.0)
    bonus_value = db.Column(db.Float, default=0.0)
    discount_value = db.Column(db.Float, default=0.0)
    total_value = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='pending')
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
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

class Delivery(db.Model):
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    awb = db.Column(db.String(50))
    sender = db.Column(db.String(100))
    service_type = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float)
    status = db.Column(db.String(50))
    status_description = db.Column(db.String(200))
    delivery_date = db.Column(db.Date)
    payment_period = db.Column(db.String(50), nullable=False)
    base_value = db.Column(db.Float, default=0.0)
    bonus_value = db.Column(db.Float, default=0.0)
    total_value = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Bonus(db.Model):
    __tablename__ = 'bonuses'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    period = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    value = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'period': self.period,
            'description': self.description,
            'value': self.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BonusRule(db.Model):
    __tablename__ = 'bonus_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    service_type = db.Column(db.Integer)  # Tipo de serviço (0, 9, 6, 8) ou None para todos
    min_deliveries = db.Column(db.Integer, default=0)  # Mínimo de entregas para ativar
    value_type = db.Column(db.String(20), default='fixed')  # fixed, percentage
    value = db.Column(db.Float, default=0.0)  # Valor fixo ou percentual
    active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'service_type': self.service_type,
            'min_deliveries': self.min_deliveries,
            'value_type': self.value_type,
            'value': self.value,
            'active': self.active,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DiscountRule(db.Model):
    __tablename__ = 'discount_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    discount_type = db.Column(db.String(50), default='extravio')  # extravio, adiantamento, emprestimo
    value_type = db.Column(db.String(20), default='fixed')  # fixed, percentage
    value = db.Column(db.Float, default=0.0)  # Valor fixo ou percentual
    max_installments = db.Column(db.Integer, default=1)  # Máximo de parcelas
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'discount_type': self.discount_type,
            'value_type': self.value_type,
            'value': self.value,
            'max_installments': self.max_installments,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Discount(db.Model):
    __tablename__ = 'discounts'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(20), db.ForeignKey('drivers.driver_id'), nullable=False)
    description = db.Column(db.String(200))
    total_value = db.Column(db.Float, default=0.0)
    installments = db.Column(db.Integer, default=1)
    installment_value = db.Column(db.Float, default=0.0)
    current_installment = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, cancelled
    start_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'description': self.description,
            'total_value': self.total_value,
            'installments': self.installments,
            'installment_value': self.installment_value,
            'current_installment': self.current_installment,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.Integer, unique=True, nullable=False)
    description = db.Column(db.String(100))
    base_value = db.Column(db.Float, default=0.0)
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
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))  # csv, excel, etc.
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    process_date = db.Column(db.DateTime)
    process_result = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'uploaded_by': self.uploaded_by,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'processed': self.processed,
            'process_date': self.process_date.isoformat() if self.process_date else None,
            'process_result': self.process_result
        }
