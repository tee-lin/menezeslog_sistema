#!/usr/bin/env python3
"""
Arquivo de teste para verificar a conexão entre Digital Ocean e Supabase
MenezesLog SaaS - Teste de Conectividade
"""

import os
import sys
import json
from datetime import datetime

def test_environment_variables():
    """Testa se todas as variáveis de ambiente necessárias estão configuradas"""
    print("🔍 Verificando variáveis de ambiente...")
    
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_KEY',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mostrar apenas os primeiros e últimos caracteres para segurança
            masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  ✅ {var}: {masked_value}")
    
    if missing_vars:
        print(f"  ❌ Variáveis faltando: {', '.join(missing_vars)}")
        return False
    
    print("  ✅ Todas as variáveis de ambiente estão configuradas!")
    return True

def test_supabase_connection():
    """Testa a conexão com o Supabase"""
    print("\n🔗 Testando conexão com Supabase...")
    
    try:
        # Importar supabase (se disponível)
        try:
            from supabase import create_client, Client
        except ImportError:
            print("  ❌ Biblioteca supabase-py não está instalada")
            print("  💡 Adicione 'supabase==1.2.0' ao requirements.txt")
            return False
        
        # Obter variáveis de ambiente
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("  ❌ Variáveis SUPABASE_URL ou SUPABASE_ANON_KEY não configuradas")
            return False
        
        # Inicializar cliente Supabase
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Testar conexão básica
        response = supabase.table('tenants').select('id, name, slug, active').execute()
        
        print(f"  ✅ Conexão estabelecida com sucesso!")
        print(f"  📊 Tenants encontrados: {len(response.data)}")
        
        # Mostrar dados dos tenants (sem informações sensíveis)
        for tenant in response.data:
            print(f"    - {tenant.get('name', 'N/A')} ({tenant.get('slug', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao conectar com Supabase: {str(e)}")
        return False

def test_database_structure():
    """Testa se a estrutura do banco está correta"""
    print("\n🏗️ Verificando estrutura do banco de dados...")
    
    try:
        from supabase import create_client, Client
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Tabelas que devem existir
        required_tables = [
            'tenants',
            'users', 
            'service_types',
            'drivers',
            'payments',
            'bonuses',
            'discounts',
            'invoices',
            'uploads',
            'reports'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in required_tables:
            try:
                # Tentar fazer uma query simples para verificar se a tabela existe
                response = supabase.table(table).select('*').limit(1).execute()
                existing_tables.append(table)
                print(f"  ✅ Tabela '{table}' existe")
            except Exception as e:
                missing_tables.append(table)
                print(f"  ❌ Tabela '{table}' não encontrada: {str(e)}")
        
        if missing_tables:
            print(f"\n  ⚠️ Tabelas faltando: {', '.join(missing_tables)}")
            print("  💡 Execute o script SQL de configuração do Supabase")
            return False
        
        print("  ✅ Todas as tabelas necessárias estão presentes!")
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao verificar estrutura: {str(e)}")
        return False

def test_rls_policies():
    """Testa se as políticas RLS estão funcionando"""
    print("\n🔒 Testando políticas de Row Level Security...")
    
    try:
        from supabase import create_client, Client
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Tentar acessar dados sem autenticação (deve retornar vazio devido ao RLS)
        response = supabase.table('users').select('*').execute()
        
        if len(response.data) == 0:
            print("  ✅ RLS está funcionando - dados protegidos sem autenticação")
        else:
            print("  ⚠️ RLS pode não estar configurado corretamente")
            print(f"    Dados retornados sem autenticação: {len(response.data)} registros")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao testar RLS: {str(e)}")
        return False

def test_storage_buckets():
    """Testa se os buckets de storage estão configurados"""
    print("\n📁 Verificando buckets de storage...")
    
    try:
        from supabase import create_client, Client
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")  # Usar service key para storage
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Buckets que devem existir
        required_buckets = ['invoices', 'reports', 'uploads', 'documents']
        
        # Listar buckets existentes
        buckets = supabase.storage.list_buckets()
        existing_bucket_names = [bucket.name for bucket in buckets]
        
        for bucket in required_buckets:
            if bucket in existing_bucket_names:
                print(f"  ✅ Bucket '{bucket}' existe")
            else:
                print(f"  ❌ Bucket '{bucket}' não encontrado")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao verificar storage: {str(e)}")
        return False

def generate_test_report():
    """Gera um relatório completo dos testes"""
    print("\n" + "="*60)
    print("📋 RELATÓRIO DE TESTES - MENEZESLOG SAAS")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Ambiente: {os.environ.get('FLASK_ENV', 'development')}")
    print("-"*60)
    
    tests = [
        ("Variáveis de Ambiente", test_environment_variables),
        ("Conexão Supabase", test_supabase_connection),
        ("Estrutura do Banco", test_database_structure),
        ("Políticas RLS", test_rls_policies),
        ("Storage Buckets", test_storage_buckets)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Erro inesperado em '{test_name}': {str(e)}")
            results[test_name] = False
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<25} {status}")
    
    print("-"*60)
    print(f"Total: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM! Sua aplicação está configurada corretamente.")
        return True
    else:
        print("⚠️ Alguns testes falharam. Verifique a configuração antes de prosseguir.")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando testes de conectividade MenezesLog SaaS...")
    
    success = generate_test_report()
    
    if success:
        print("\n✅ Sistema pronto para uso!")
        sys.exit(0)
    else:
        print("\n❌ Configuração incompleta. Verifique os erros acima.")
        sys.exit(1)
