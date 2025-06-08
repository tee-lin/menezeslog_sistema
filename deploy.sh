#!/bin/bash

# Digital Ocean Deploy Script for MenezesLog SaaS
# Este script automatiza o deploy da aplicação no Digital Ocean

set -e

echo "🚀 Iniciando deploy do MenezesLog no Digital Ocean..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se o doctl está instalado
if ! command -v doctl &> /dev/null; then
    print_error "doctl CLI não está instalado. Instale com:"
    echo "  # macOS"
    echo "  brew install doctl"
    echo "  # Linux"
    echo "  wget https://github.com/digitalocean/doctl/releases/download/v1.94.0/doctl-1.94.0-linux-amd64.tar.gz"
    echo "  tar xf doctl-1.94.0-linux-amd64.tar.gz"
    echo "  sudo mv doctl /usr/local/bin"
    exit 1
fi

# Verificar se o Terraform está instalado
if ! command -v terraform &> /dev/null; then
    print_error "Terraform não está instalado. Instale com:"
    echo "  # macOS"
    echo "  brew install terraform"
    echo "  # Linux"
    echo "  wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip"
    echo "  unzip terraform_1.6.6_linux_amd64.zip"
    echo "  sudo mv terraform /usr/local/bin/"
    exit 1
fi

# Verificar autenticação do Digital Ocean
print_status "Verificando autenticação do Digital Ocean..."
if ! doctl account get &> /dev/null; then
    print_error "Você não está autenticado no Digital Ocean."
    echo "Execute: doctl auth init"
    exit 1
fi

print_status "✅ Autenticação verificada!"

# Solicitar informações do Supabase
echo ""
print_status "Configuração do Supabase:"
read -p "Digite a URL do seu projeto Supabase: " SUPABASE_URL
read -p "Digite a chave anônima do Supabase: " SUPABASE_ANON_KEY
read -s -p "Digite a chave de serviço do Supabase: " SUPABASE_SERVICE_KEY
echo ""

# Gerar chave secreta para Flask
SECRET_KEY=$(openssl rand -hex 32)

# Obter token do Digital Ocean
DO_TOKEN=$(doctl auth list --format Token --no-header)

# Criar arquivo terraform.tfvars
print_status "Criando arquivo de configuração Terraform..."
cat > terraform.tfvars << EOF
do_token = "$DO_TOKEN"
project_name = "menezeslog"
environment = "prod"
supabase_url = "$SUPABASE_URL"
supabase_anon_key = "$SUPABASE_ANON_KEY"
supabase_service_key = "$SUPABASE_SERVICE_KEY"
app_secret_key = "$SECRET_KEY"
EOF

# Inicializar Terraform
print_status "Inicializando Terraform..."
terraform init

# Planejar deploy
print_status "Planejando infraestrutura..."
terraform plan

# Confirmar deploy
echo ""
read -p "Deseja prosseguir com o deploy? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    print_warning "Deploy cancelado pelo usuário."
    exit 0
fi

# Aplicar configuração
print_status "Aplicando configuração no Digital Ocean..."
terraform apply -auto-approve

# Obter URL da aplicação
APP_URL=$(terraform output -raw app_url)

print_status "✅ Deploy concluído com sucesso!"
echo ""
echo "🌐 Sua aplicação está disponível em: $APP_URL"
echo ""
print_status "Próximos passos:"
echo "1. Aguarde alguns minutos para o build completar"
echo "2. Acesse a URL da aplicação"
echo "3. Configure seu domínio personalizado (opcional)"
echo "4. Configure SSL/TLS (automático no Digital Ocean)"
echo ""
print_warning "Guarde as seguintes informações:"
echo "- URL da aplicação: $APP_URL"
echo "- Chave secreta: $SECRET_KEY"
echo ""
print_status "Para monitorar o deploy:"
echo "doctl apps list"
echo "doctl apps logs \$(terraform output -raw app_id)"
