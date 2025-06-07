#!/usr/bin/env python3
"""
Script para corrigir o esquema da tabela service_types no banco de dados PostgreSQL do Heroku.
Este script adiciona as colunas created_at e updated_at à tabela service_types.
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
    print("Execute este script no Heroku com: heroku run python db_fix_service_types.py")
    sys.exit(1)

def fix_service_types_schema():
    """Corrige o esquema da tabela service_types, adicionando colunas faltantes."""
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
        else:
            print("✗ A tabela service_types NÃO existe!")
            return
        
        # Listar todas as colunas da tabela service_types
        print("\nListando todas as colunas da tabela service_types:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='service_types';
        """)
        columns = cursor.fetchall()
        for column in columns:
            print(f"- {column[0]} ({column[1]})")
        
        # Verificar se a coluna created_at existe na tabela service_types
        print("\nVerificando se a coluna created_at existe na tabela service_types:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='service_types' AND column_name='created_at'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A coluna created_at existe na tabela service_types.")
        else:
            print("✗ A coluna created_at NÃO existe na tabela service_types!")
            
            # Adicionar a coluna created_at se não existir
            print("\nAdicionando a coluna created_at à tabela service_types...")
            cursor.execute("""
                ALTER TABLE service_types 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            conn.commit()
            print("✓ Coluna created_at adicionada com sucesso!")
        
        # Verificar se a coluna updated_at existe na tabela service_types
        print("\nVerificando se a coluna updated_at existe na tabela service_types:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='service_types' AND column_name='updated_at'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A coluna updated_at existe na tabela service_types.")
        else:
            print("✗ A coluna updated_at NÃO existe na tabela service_types!")
            
            # Adicionar a coluna updated_at se não existir
            print("\nAdicionando a coluna updated_at à tabela service_types...")
            cursor.execute("""
                ALTER TABLE service_types 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            conn.commit()
            print("✓ Coluna updated_at adicionada com sucesso!")
        
        # Verificar se a coluna type_code existe na tabela service_types
        print("\nVerificando se a coluna type_code existe na tabela service_types:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='service_types' AND column_name='type_code'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A coluna type_code existe na tabela service_types.")
        else:
            print("✗ A coluna type_code NÃO existe na tabela service_types!")
            
            # Adicionar a coluna type_code se não existir
            print("\nAdicionando a coluna type_code à tabela service_types...")
            cursor.execute("""
                ALTER TABLE service_types 
                ADD COLUMN type_code INTEGER DEFAULT 0;
            """)
            
            # Atualizar os valores de type_code com base no id
            print("Atualizando valores de type_code com base no id...")
            cursor.execute("""
                UPDATE service_types 
                SET type_code = id;
            """)
            conn.commit()
            print("✓ Coluna type_code adicionada e atualizada com sucesso!")
        
        # Verificar se as colunas foram adicionadas corretamente
        print("\nVerificando novamente as colunas da tabela service_types:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='service_types';
        """)
        columns = cursor.fetchall()
        for column in columns:
            print(f"- {column[0]} ({column[1]})")
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
        print("\nEsquema da tabela service_types corrigido com sucesso!")
        
    except Exception as e:
        print(f"Erro ao corrigir o esquema da tabela service_types: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_service_types_schema()
