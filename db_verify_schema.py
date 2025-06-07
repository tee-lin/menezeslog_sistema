#!/usr/bin/env python3
"""
Script para verificar e corrigir o esquema do banco de dados PostgreSQL no Heroku para o sistema MenezesLog.
Este script verifica a conexão com o banco de dados e confirma se a coluna driver_id existe na tabela users.
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
    print("Execute este script no Heroku com: heroku run python db_verify_schema.py")
    sys.exit(1)

def verify_schema():
    """Verifica o esquema do banco de dados e confirma se a coluna driver_id existe."""
    try:
        print("Conectando ao banco de dados PostgreSQL do Heroku...")
        print(f"DATABASE_URL: {DATABASE_URL[:20]}...{DATABASE_URL[-5:]}")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Listar todas as tabelas
        print("\nListando todas as tabelas no banco de dados:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public';
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        
        # Verificar se a tabela users existe
        print("\nVerificando se a tabela users existe:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name='users'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A tabela users existe.")
        else:
            print("✗ A tabela users NÃO existe!")
            return
        
        # Listar todas as colunas da tabela users
        print("\nListando todas as colunas da tabela users:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='users';
        """)
        columns = cursor.fetchall()
        for column in columns:
            print(f"- {column[0]} ({column[1]})")
        
        # Verificar se a coluna driver_id existe na tabela users
        print("\nVerificando se a coluna driver_id existe na tabela users:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='driver_id'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A coluna driver_id existe na tabela users.")
        else:
            print("✗ A coluna driver_id NÃO existe na tabela users!")
            
            # Adicionar a coluna driver_id se não existir
            print("\nAdicionando a coluna driver_id à tabela users...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN driver_id INTEGER NULL;
            """)
            conn.commit()
            print("✓ Coluna driver_id adicionada com sucesso!")
        
        # Verificar se a coluna driver_id foi adicionada corretamente
        print("\nVerificando novamente se a coluna driver_id existe:")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='driver_id'
            );
        """)
        if cursor.fetchone()[0]:
            print("✓ A coluna driver_id existe na tabela users.")
        else:
            print("✗ A coluna driver_id ainda NÃO existe na tabela users!")
        
        # Fechar conexão
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao verificar o esquema do banco de dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_schema()
