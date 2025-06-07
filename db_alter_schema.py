#!/usr/bin/env python3
"""
Script para modificar o esquema do banco de dados PostgreSQL no Heroku para o sistema MenezesLog.
Este script adiciona a coluna driver_id à tabela users existente.
"""

import os
import sys
import psycopg2

# Obter URL do banco de dados do Heroku
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("Erro: Variável de ambiente DATABASE_URL não encontrada.")
    print("Execute este script no Heroku com: heroku run python db_alter_schema.py")
    sys.exit(1)

def alter_schema():
    """Modifica o esquema do banco de dados, adicionando colunas faltantes."""
    try:
        print("Conectando ao banco de dados PostgreSQL do Heroku...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar se a coluna driver_id já existe na tabela users
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='driver_id';
        """)
        
        if cursor.fetchone() is None:
            print("Adicionando coluna driver_id à tabela users...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN driver_id INTEGER NULL;
            """)
            print("Coluna driver_id adicionada com sucesso!")
        else:
            print("A coluna driver_id já existe na tabela users.")
        
        # Commit das alterações
        conn.commit()
        
        print("Verificando outras tabelas necessárias...")
        
        # Verificar se a tabela drivers existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name='drivers'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("Criando tabela drivers...")
            cursor.execute("""
                CREATE TABLE drivers (
                    id SERIAL PRIMARY KEY,
                    driver_id VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(120),
                    phone VARCHAR(20),
                    document VARCHAR(20),
                    bank VARCHAR(50),
                    agency VARCHAR(20),
                    account VARCHAR(20),
                    pix VARCHAR(100),
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Tabela drivers criada com sucesso!")
        else:
            print("A tabela drivers já existe.")
        
        # Verificar se a tabela service_types existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name='service_types'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("Criando tabela service_types...")
            cursor.execute("""
                CREATE TABLE service_types (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(255),
                    base_value FLOAT NOT NULL DEFAULT 0.0,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Tabela service_types criada com sucesso!")
            
            # Inserir tipos de serviço padrão
            cursor.execute("""
                INSERT INTO service_types (name, description, base_value)
                VALUES 
                ('Entrega Local', 'Entrega dentro da cidade', 50.0),
                ('Entrega Regional', 'Entrega na região metropolitana', 100.0),
                ('Entrega Estadual', 'Entrega dentro do estado', 200.0),
                ('Entrega Interestadual', 'Entrega para outros estados', 500.0);
            """)
            print("Tipos de serviço padrão inseridos com sucesso!")
        else:
            print("A tabela service_types já existe.")
        
        # Commit das alterações
        conn.commit()
        
        # Verificar se existe um usuário admin
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM users 
                WHERE username='admin'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("Criando usuário admin...")
            # Senha 'admin' com hash
            password_hash = 'pbkdf2:sha256:260000$rTY0haIFJmAUhvIj$287d2113de0a4e9d65fb00d3d1e92b86b0bbf4078e9f3da7e2e1534648ba92e9'
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, name, active, first_access)
                VALUES ('admin', 'admin@menezeslog.com', %s, 'admin', 'Administrador', TRUE, TRUE);
            """, (password_hash,))
            print("Usuário admin criado com sucesso!")
        else:
            print("O usuário admin já existe.")
        
        # Commit das alterações finais
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Esquema do banco de dados atualizado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao modificar o esquema do banco de dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    alter_schema()
