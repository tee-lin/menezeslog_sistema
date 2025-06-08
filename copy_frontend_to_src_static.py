#!/usr/bin/env python3
import os
import shutil
import sys

def copy_frontend_files():
    """
    Script para copiar todos os arquivos do frontend para a pasta src/static
    """
    print("Iniciando cópia dos arquivos do frontend para src/static...")
    
    # Verificar se a pasta static existe
    if not os.path.exists('static'):
        print("Erro: A pasta 'static' não foi encontrada no diretório atual.")
        return False
    
    # Verificar se a pasta src/static existe, criar se não existir
    if not os.path.exists('src/static'):
        print("Criando diretório src/static...")
        os.makedirs('src/static', exist_ok=True)
    
    # Listar arquivos na pasta static
    static_files = os.listdir('static')
    print(f"Encontrados {len(static_files)} arquivos/pastas em 'static'")
    
    # Copiar todos os arquivos e pastas de static para src/static
    for item in static_files:
        src_path = os.path.join('static', item)
        dst_path = os.path.join('src/static', item)
        
        if os.path.isdir(src_path):
            print(f"Copiando diretório: {item}...")
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            print(f"Copiando arquivo: {item}...")
            shutil.copy2(src_path, dst_path)
    
    # Verificar se a cópia foi bem-sucedida
    if os.path.exists('src/static'):
        copied_files = os.listdir('src/static')
        print(f"Cópia concluída! {len(copied_files)} arquivos/pastas copiados para src/static")
        print("Arquivos copiados:")
        for item in copied_files:
            print(f"  - {item}")
        return True
    else:
        print("Erro: Falha ao copiar arquivos para src/static")
        return False

if __name__ == "__main__":
    success = copy_frontend_files()
    if success:
        print("\nPróximos passos:")
        print("1. Adicione os arquivos ao git:")
        print("   git add src/static")
        print("2. Faça o commit:")
        print("   git commit -m \"Adiciona arquivos do frontend\"")
        print("3. Envie para o Heroku:")
        print("   git push heroku master")
        sys.exit(0)
    else:
        print("\nOcorreu um erro durante a cópia dos arquivos.")
        sys.exit(1)
