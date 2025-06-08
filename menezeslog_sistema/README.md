# Sistema de Pagamento para Motoristas - MenezesLog

Este sistema foi desenvolvido para automatizar o processo de cálculo de pagamentos para motoristas da MenezesLog, com base nos tipos de serviço realizados, incluindo funcionalidades de bonificações e descontos.

## Funcionalidades Principais

- **Autenticação de Usuários**: Sistema de login para administradores e motoristas
- **Upload de Arquivos**: Processamento de arquivos CSV de entregas e Excel com dados dos motoristas
- **Cálculo de Pagamentos**: Processamento automático baseado nos tipos de serviço
- **Bonificações**: Configuração flexível de bonificações por tipo de serviço e volume
- **Descontos**: Sistema para gerenciar extravios e adiantamentos/empréstimos
- **Relatórios em PDF**: Geração de demonstrativos detalhados para cada motorista
- **Upload de Notas Fiscais**: Interface para motoristas enviarem suas notas fiscais

## Regras de Pagamento

O sistema calcula os pagamentos com base nos seguintes valores por tipo de serviço:

- **Tipo 0**: R$ 3,50 por item
- **Tipo 9**: R$ 2,00 por item
- **Tipos 6 e 8**: R$ 0,50 por item

## Estrutura do Projeto

```
menezeslog_sistema/
├── venv/                  # Ambiente virtual Python
├── src/                   # Código-fonte do sistema
│   ├── models/            # Modelos de dados
│   │   ├── user.py        # Modelo de usuário
│   │   └── models.py      # Outros modelos (motoristas, entregas, etc.)
│   ├── routes/            # Rotas da API
│   │   ├── auth.py        # Autenticação
│   │   ├── upload.py      # Upload de arquivos
│   │   ├── bonus.py       # Bonificações
│   │   ├── discount.py    # Descontos
│   │   ├── payment.py     # Pagamentos
│   │   └── invoice.py     # Notas fiscais
│   ├── static/            # Arquivos estáticos (frontend)
│   │   ├── css/           # Estilos
│   │   ├── js/            # JavaScript
│   │   └── images/        # Imagens
│   └── main.py            # Ponto de entrada da aplicação
└── requirements.txt       # Dependências do projeto
```

## Instalação e Execução

### Pré-requisitos

- Python 3.11 ou superior
- MySQL 5.7 ou superior

### Configuração do Ambiente

1. Clone o repositório:
   ```
   git clone [URL_DO_REPOSITORIO]
   cd menezeslog_sistema
   ```

2. Crie e ative o ambiente virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Configure o banco de dados:
   - Crie um banco de dados MySQL
   - Configure as variáveis de ambiente:
     ```
     export DB_USERNAME=seu_usuario
     export DB_PASSWORD=sua_senha
     export DB_HOST=localhost
     export DB_PORT=3306
     export DB_NAME=nome_do_banco
     ```

5. Execute a aplicação:
   ```
   python src/main.py
   ```

6. Acesse o sistema em `http://localhost:5000`

## Credenciais Iniciais

- **Usuário**: admin
- **Senha**: admin123

## Fluxo de Trabalho

1. **Administrador**:
   - Faz upload dos arquivos CSV de entregas
   - Configura bonificações e descontos
   - Aprova notas fiscais enviadas pelos motoristas
   - Gera relatórios de pagamento

2. **Motorista**:
   - Visualiza seus pagamentos e entregas
   - Envia notas fiscais
   - Acompanha status de pagamentos

## Suporte

Para suporte técnico ou dúvidas sobre o sistema, entre em contato com a equipe de desenvolvimento.

---

Desenvolvido para MenezesLog © 2025
