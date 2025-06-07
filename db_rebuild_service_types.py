#!/usr/bin/env python3
"""
Script para reconstruir completamente a tabela service_types no banco de dados PostgreSQL do Heroku.
Este script exclui a tabela existente e cria uma nova com o esquema correto.
"""

import os
import sys
import psycopg2
from datetime import datetime

# Obter URL do banco de dados do Heroku
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("Erro: Variável de ambiente DATABASE_URL não encontrada.")
    print("Execute este script no Heroku com: heroku run python db_rebuild_service_types.py")
    sys.exit(1)

def rebuild_service_types_table():
    """Reconstrói completamente a tabela service_types com o esquema correto."""
    try:
        print("Conectando ao banco de dados PostgreSQL do Heroku...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar se a tabela service_types existe
        print("\nVerificando se a tabela service_types existe:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name='service_types'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A tabela service_types existe.")
            
            # Excluir a tabela service_types existente
            print("\nExcluindo a tabela service_types existente...")
            cursor.execute("""
                DROP TABLE service_types CASCADE;
            """)
            conn.commit()
            print("✓ Tabela service_types excluída com sucesso!")
        else:
            print("✗ A tabela service_types NÃO existe!")
        
        # Criar a tabela service_types com o esquema correto
        print("\nCriando a tabela service_types com o esquema correto...")
        cursor.execute("""
            CREATE TABLE service_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                base_value FLOAT NOT NULL DEFAULT 0.0,
                type_code INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("✓ Tabela service_types criada com sucesso!")
        
        # Inserir dados iniciais
        print("\nInserindo tipos de serviço padrão...")
        cursor.execute("""
            INSERT INTO service_types (name, description, base_value, type_code)
            VALUES 
            ('Entrega Local', 'Entrega dentro da cidade', 50.0, 1),
            ('Entrega Regional', 'Entrega na região metropolitana', 100.0, 2),
            ('Entrega Estadual', 'Entrega dentro do estado', 200.0, 3),
            ('Entrega Interestadual', 'Entrega para outros estados', 500.0, 4);
        """)
        conn.commit()
        print("✓ Tipos de serviço padrão inseridos com sucesso!")
        
        # Verificar se a tabela foi criada corretamente
        print("\nVerificando se a tabela service_types foi criada corretamente:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='service_types';
        """)
        columns = cursor.fetchall()
        for column in columns:
            print(f"- {column[0]} ({column[1]})")
        
        # Verificar se os dados foram inseridos corretamente
        print("\nVerificando se os dados foram inseridos corretamente:")
        cursor.execute("""
            SELECT id, name, description, base_value, type_code
            FROM service_types;
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f"- ID: {row[0]}, Nome: {row[1]}, Valor Base: {row[3]}, Tipo: {row[4]}")
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        print("\nTabela service_types reconstruída com sucesso!")
        
    except Exception as e:
        print(f"Erro ao reconstruir a tabela service_types: {e}")
        sys.exit(1)

if __name__ == "__main__":
    rebuild_service_types_table()
