# Sistema de Pagamento para Motoristas - MenezesLog

## Visão Geral

O Sistema de Pagamento para Motoristas da MenezesLog é uma plataforma web completa para gerenciamento de pagamentos de motoristas, processamento de entregas, cálculo de bonificações e descontos, e geração de relatórios detalhados.

## Funcionalidades Principais

- **Upload e Processamento de Arquivos CSV**: Importação automática de dados de entregas
- **Cálculo de Pagamentos**: Baseado em tipos de serviço com valores configuráveis
- **Bonificações**: Sistema flexível para configuração de bonificações por tipo de serviço e volume
- **Descontos**: Gerenciamento de extravios e adiantamentos/empréstimos
- **Relatórios em PDF**: Geração de demonstrativos detalhados por motorista
- **Área do Motorista**: Interface para motoristas visualizarem pagamentos e enviarem notas fiscais
- **Gestão de Usuários**: Controle de acesso com diferentes níveis de permissão

## Requisitos Técnicos

- Python 3.11 ou superior
- Flask (framework web)
- SQLAlchemy (ORM para banco de dados)
- MySQL (banco de dados)
- Bibliotecas Python: pandas, reportlab, matplotlib, pyjwt, flask-cors

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o banco de dados:
```bash
# Edite as configurações de banco de dados em src/main.py
# Descomente e ajuste a linha com SQLALCHEMY_DATABASE_URI
```

5. Inicie o servidor:
```bash
python src/main.py
```

## Estrutura do Projeto

```
menezeslog_sistema/
├── src/                    # Código-fonte principal
│   ├── models/             # Modelos de dados
│   │   ├── models.py       # Definições de tabelas e relações
│   │   └── user.py         # Modelo de usuário e autenticação
│   ├── routes/             # Rotas da API
│   │   ├── auth.py         # Autenticação
│   │   ├── bonus.py        # Bonificações
│   │   ├── discount.py     # Descontos
│   │   ├── invoice.py      # Notas fiscais
│   │   ├── payment.py      # Pagamentos
│   │   └── upload.py       # Upload de arquivos
│   ├── static/             # Arquivos estáticos (HTML, CSS, JS)
│   │   ├── assets/         # Imagens e recursos
│   │   ├── admin_dashboard.html
│   │   ├── bonificacoes.html
│   │   ├── configuracoes.html
│   │   ├── descontos.html
│   │   ├── index.html      # Página de login
│   │   ├── motoristas.html
│   │   ├── relatorios.html
│   │   └── upload.html
│   ├── uploads/            # Diretório para arquivos enviados
│   │   ├── csv/            # Arquivos CSV de entregas
│   │   └── excel/          # Planilhas de referência
│   ├── reports/            # Relatórios gerados
│   │   └── pdf/            # PDFs de pagamento
│   └── main.py             # Ponto de entrada da aplicação
├── requirements.txt        # Dependências do projeto
└── README.md               # Documentação
```

## Configuração

### Valores por Tipo de Serviço

Os valores padrão por tipo de serviço são:
- Tipo 0: R$ 3,50 por item
- Tipo 9: R$ 2,00 por item
- Tipos 6 e 8: R$ 0,50 por item

Estes valores podem ser ajustados na página de Configurações do sistema.

### Usuários Padrão

O sistema é inicializado com um usuário administrador:
- **Usuário**: admin
- **Senha**: admin123

Recomenda-se alterar esta senha após o primeiro acesso.

## Uso do Sistema

### Fluxo de Trabalho Administrativo

1. Faça login como administrador
2. Acesse "Upload de Arquivos" para importar dados de entregas (CSV) e motoristas (Excel)
3. Configure bonificações e descontos conforme necessário
4. Visualize e aprove os pagamentos gerados
5. Gere relatórios detalhados por motorista

### Fluxo de Trabalho do Motorista

1. Faça login com credenciais de motorista
2. Visualize pagamentos disponíveis e histórico
3. Envie nota fiscal quando solicitado
4. Acompanhe status de pagamento

## Manutenção

### Backup do Banco de Dados

Recomenda-se configurar backups automáticos do banco de dados MySQL:

```bash
# Exemplo de comando para backup
mysqldump -u [usuario] -p [senha] menezeslog_db > backup_$(date +%Y%m%d).sql
```

### Rotação de Logs

O sistema mantém logs de operações importantes. Configure a rotação de logs para evitar arquivos muito grandes:

```bash
# Exemplo de configuração para logrotate
/path/to/menezeslog/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

## Suporte

Para suporte técnico ou dúvidas sobre o sistema, entre em contato com:
- Email: suporte@menezeslog.com
- Telefone: (XX) XXXX-XXXX

## Licença

Este software é propriedade da MenezesLog e seu uso é restrito conforme os termos do contrato de licença.

---

Desenvolvido por Manus AI © 2025
