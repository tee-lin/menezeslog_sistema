#!/usr/bin/env python3
"""
Script para verificar e copiar arquivos estáticos para o diretório correto no Heroku.
Este script cria o diretório static se não existir e copia os arquivos HTML necessários.
"""

import os
import sys
import shutil

def deploy_static_files():
    """Verifica e copia arquivos estáticos para o diretório correto."""
    try:
        print("Verificando diretório static...")
        
        # Verificar se o diretório static existe na raiz
        if not os.path.exists('static'):
            print("Criando diretório static na raiz...")
            os.makedirs('static', exist_ok=True)
        
        # Verificar se os arquivos HTML existem no diretório src/static
        src_static_dir = 'src/static'
        if not os.path.exists(src_static_dir):
            print(f"Erro: Diretório {src_static_dir} não encontrado!")
            return
        
        # Listar arquivos HTML no diretório src/static
        html_files = [f for f in os.listdir(src_static_dir) if f.endswith('.html')]
        if not html_files:
            print(f"Erro: Nenhum arquivo HTML encontrado em {src_static_dir}!")
            return
        
        print(f"Encontrados {len(html_files)} arquivos HTML em {src_static_dir}:")
        for html_file in html_files:
            print(f"- {html_file}")
        
        # Copiar arquivos HTML para o diretório static na raiz
        print("\nCopiando arquivos HTML para o diretório static na raiz...")
        for html_file in html_files:
            src_path = os.path.join(src_static_dir, html_file)
            dst_path = os.path.join('static', html_file)
            shutil.copy2(src_path, dst_path)
            print(f"✓ Copiado: {src_path} -> {dst_path}")
        
        # Verificar se há arquivos CSS e JS para copiar
        css_files = [f for f in os.listdir(src_static_dir) if f.endswith('.css')]
        js_files = [f for f in os.listdir(src_static_dir) if f.endswith('.js')]
        
        # Copiar arquivos CSS
        if css_files:
            print("\nCopiando arquivos CSS...")
            for css_file in css_files:
                src_path = os.path.join(src_static_dir, css_file)
                dst_path = os.path.join('static', css_file)
                shutil.copy2(src_path, dst_path)
                print(f"✓ Copiado: {src_path} -> {dst_path}")
        
        # Copiar arquivos JS
        if js_files:
            print("\nCopiando arquivos JS...")
            for js_file in js_files:
                src_path = os.path.join(src_static_dir, js_file)
                dst_path = os.path.join('static', js_file)
                shutil.copy2(src_path, dst_path)
                print(f"✓ Copiado: {src_path} -> {dst_path}")
        
        # Verificar se há subdiretórios (como css, js, img) para copiar
        subdirs = [d for d in os.listdir(src_static_dir) if os.path.isdir(os.path.join(src_static_dir, d))]
        if subdirs:
            print("\nCopiando subdiretórios...")
            for subdir in subdirs:
                src_subdir = os.path.join(src_static_dir, subdir)
                dst_subdir = os.path.join('static', subdir)
                
                # Criar subdiretório se não existir
                if not os.path.exists(dst_subdir):
                    os.makedirs(dst_subdir, exist_ok=True)
                
                # Copiar arquivos do subdiretório
                for file in os.listdir(src_subdir):
                    src_path = os.path.join(src_subdir, file)
                    dst_path = os.path.join(dst_subdir, file)
                    
                    if os.path.isfile(src_path):
                        shutil.copy2(src_path, dst_path)
                        print(f"✓ Copiado: {src_path} -> {dst_path}")
        
        print("\nArquivos estáticos copiados com sucesso!")
        print("Agora você deve adicionar, commitar e enviar estes arquivos para o Heroku:")
        print("git add static/")
        print("git commit -m \"Adiciona arquivos estáticos\"")
        print("git push heroku master")
        
    except Exception as e:
        print(f"Erro ao copiar arquivos estáticos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    deploy_static_files()
