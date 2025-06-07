#!/usr/bin/env python3
"""
Script para inicializar o banco de dados PostgreSQL no Heroku para o sistema MenezesLog.
Este script cria todas as tabelas necessárias e insere dados iniciais.
"""

import os
import sys
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash

# Obter URL do banco de dados do Heroku
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("Erro: Variável de ambiente DATABASE_URL não encontrada.")
    print("Execute este script no Heroku com: heroku run python db_init_heroku.py")
    sys.exit(1)

# Configurar SQLAlchemy
Base = declarative_base()

# Definir modelos
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False, default='user')
    name = Column(String(100), nullable=True)
    driver_id = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    first_access = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Driver(Base):
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(20), nullable=True)
    document = Column(String(20), nullable=True)
    bank = Column(String(50), nullable=True)
    agency = Column(String(20), nullable=True)
    account = Column(String(20), nullable=True)
    pix = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Driver {self.driver_id}>'

class ServiceType(Base):
    __tablename__ = 'service_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    base_value = Column(Float, nullable=False, default=0.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<ServiceType {self.name}>'

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.datetime.utcnow)
    reference = Column(String(100), nullable=True)
    status = Column(String(20), default='pending')
    invoice_received = Column(Boolean, default=False)
    invoice_date = Column(DateTime, nullable=True)
    details = Column(Text, nullable=True)
    period = Column(String(20), nullable=True)
    total_value = Column(Float, nullable=True)
    invoice_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    driver = relationship('Driver', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.driver_id}>'

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, nullable=False)
    invoice_number = Column(String(50), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    file_path = Column(String(255), nullable=True)
    period = Column(String(20), nullable=True)
    value = Column(Float, nullable=True)
    status = Column(String(20), default='pending')
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class Bonus(Base):
    __tablename__ = 'bonuses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    value = Column(Float, nullable=False)
    type = Column(String(20), default='fixed')  # fixed, percentage
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Bonus {self.name}>'

class Discount(Base):
    __tablename__ = 'discounts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    value = Column(Float, nullable=False)
    type = Column(String(20), default='fixed')  # fixed, percentage
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Discount {self.name}>'

def init_db():
    """Inicializa o banco de dados, criando tabelas e inserindo dados iniciais."""
    print("Conectando ao banco de dados PostgreSQL do Heroku...")
    engine = create_engine(DATABASE_URL)
    
    print("Criando tabelas...")
    Base.metadata.create_all(engine)
    
    # Criar sessão
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Verificar se já existe um usuário admin
    admin = session.query(User).filter_by(username='admin').first()
    if not admin:
        print("Criando usuário admin...")
        admin = User(
            username='admin',
            email='admin@menezeslog.com',
            password_hash=generate_password_hash('admin'),
            role='admin',
            name='Administrador',
            active=True,
            first_access=True
        )
        session.add(admin)
    
    # Verificar se já existem tipos de serviço
    service_type = session.query(ServiceType).first()
    if not service_type:
        print("Criando tipos de serviço padrão...")
        service_types = [
            ServiceType(name='Entrega Local', description='Entrega dentro da cidade', base_value=50.0),
            ServiceType(name='Entrega Regional', description='Entrega na região metropolitana', base_value=100.0),
            ServiceType(name='Entrega Estadual', description='Entrega dentro do estado', base_value=200.0),
            ServiceType(name='Entrega Interestadual', description='Entrega para outros estados', base_value=500.0)
        ]
        session.add_all(service_types)
    
    # Verificar se já existem bonificações
    bonus = session.query(Bonus).first()
    if not bonus:
        print("Criando bonificações padrão...")
        bonuses = [
            Bonus(name='Entrega Rápida', description='Bonificação por entrega antes do prazo', value=20.0, type='fixed'),
            Bonus(name='Cliente Satisfeito', description='Bonificação por avaliação positiva do cliente', value=15.0, type='fixed'),
            Bonus(name='Volume Extra', description='Bonificação por volume acima do esperado', value=10.0, type='percentage')
        ]
        session.add_all(bonuses)
    
    # Verificar se já existem descontos
    discount = session.query(Discount).first()
    if not discount:
        print("Criando descontos padrão...")
        discounts = [
            Discount(name='Atraso', description='Desconto por atraso na entrega', value=20.0, type='fixed'),
            Discount(name='Avaria', description='Desconto por avaria na carga', value=30.0, type='fixed'),
            Discount(name='Combustível', description='Desconto para combustível fornecido pela empresa', value=15.0, type='percentage')
        ]
        session.add_all(discounts)
    
    # Commit das alterações
    session.commit()
    session.close()
    
    print("Banco de dados inicializado com sucesso!")

if __name__ == "__main__":
    init_db()
