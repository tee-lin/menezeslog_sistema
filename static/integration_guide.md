# Guia de Integração do Frontend com o Backend MenezesLog

Este documento fornece instruções detalhadas para integrar o frontend desenvolvido com o backend Flask existente do sistema MenezesLog.

## Estrutura de Arquivos

O frontend completo está organizado na pasta `/static` com a seguinte estrutura:

```
/static
├── assets/            # Imagens e recursos estáticos
├── css/               # Arquivos de estilo
│   └── styles.css     # Estilos globais do sistema
├── js/                # Scripts JavaScript
│   └── main.js        # Funções globais e utilitárias
├── index.html         # Página de login
├── admin_dashboard.html
├── motorista_dashboard.html
├── motoristas.html
├── bonificacoes.html
├── descontos.html
├── upload.html
├── relatorios.html
├── nota_fiscal.html
└── configuracoes.html
```

## Passos para Integração

### 1. Copiar Arquivos para o Projeto

Copie todos os arquivos da pasta `/static` para a pasta `/menezeslog_sistema/src/static` do seu projeto:

```bash
cp -r /home/ubuntu/static/* /home/ubuntu/menezeslog_sistema/src/static/
```

### 2. Configurar o Flask para Servir Arquivos Estáticos

Verifique se o arquivo `main.py` do seu projeto Flask está configurado para servir arquivos estáticos. O código deve conter algo similar a:

```python
from flask import Flask, render_template, send_from_directory

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')
```

### 3. Configurar Rotas para Páginas HTML

Adicione rotas para cada página HTML no arquivo `main.py`:

```python
@app.route('/<path:path>')
def serve_static(path):
    if path.endswith('.html'):
        return send_from_directory('static', path)
    return send_from_directory('static', 'index.html')
```

### 4. Verificar Endpoints da API

Certifique-se de que todos os endpoints da API estão implementados no backend. O frontend espera os seguintes endpoints:

#### Autenticação
- `POST /api/auth/login` - Login de usuário
- `POST /api/auth/logout` - Logout de usuário

#### Motoristas
- `GET /api/drivers` - Listar motoristas
- `GET /api/drivers/<id>` - Obter detalhes de um motorista
- `POST /api/drivers` - Criar novo motorista
- `PUT /api/drivers/<id>` - Atualizar motorista
- `DELETE /api/drivers/<id>` - Excluir motorista

#### Bonificações
- `GET /api/bonus/types` - Listar tipos de bonificação
- `POST /api/bonus/types` - Criar tipo de bonificação
- `PUT /api/bonus/types/<id>` - Atualizar tipo de bonificação
- `DELETE /api/bonus/types/<id>` - Excluir tipo de bonificação
- `GET /api/bonus/applied` - Listar bonificações aplicadas
- `POST /api/bonus/applied` - Aplicar bonificação
- `PUT /api/bonus/applied/<id>` - Atualizar bonificação aplicada
- `DELETE /api/bonus/applied/<id>` - Excluir bonificação aplicada

#### Descontos
- `GET /api/discount/types` - Listar tipos de desconto
- `POST /api/discount/types` - Criar tipo de desconto
- `PUT /api/discount/types/<id>` - Atualizar tipo de desconto
- `DELETE /api/discount/types/<id>` - Excluir tipo de desconto
- `GET /api/discount/applied` - Listar descontos aplicados
- `POST /api/discount/applied` - Aplicar desconto
- `PUT /api/discount/applied/<id>` - Atualizar desconto aplicado
- `DELETE /api/discount/applied/<id>` - Excluir desconto aplicado

#### Upload
- `GET /api/upload/history` - Listar histórico de uploads
- `POST /api/upload` - Enviar arquivo
- `GET /api/upload/<id>` - Obter detalhes do upload
- `DELETE /api/upload/<id>` - Excluir upload
- `POST /api/upload/<id>/process` - Processar arquivo
- `GET /api/upload/<id>/download` - Baixar arquivo
- `GET /api/upload/<id>/preview` - Visualizar prévia do arquivo

#### Relatórios
- `POST /api/reports/generate` - Gerar relatório
- `POST /api/reports/export` - Exportar relatório
- `GET /api/reports/history` - Listar histórico de relatórios
- `GET /api/reports/<id>` - Obter relatório específico
- `DELETE /api/reports/history/<id>` - Excluir relatório do histórico

#### Notas Fiscais
- `GET /api/invoices` - Listar notas fiscais
- `POST /api/invoices` - Gerar nota fiscal
- `GET /api/invoices/<id>` - Obter detalhes da nota fiscal
- `GET /api/invoices/<id>/pdf` - Baixar PDF da nota fiscal
- `POST /api/invoices/<id>/cancel` - Cancelar nota fiscal
- `POST /api/invoices/<id>/send-email` - Enviar nota fiscal por email
- `POST /api/invoices/preview` - Visualizar prévia da nota fiscal

#### Configurações
- `GET /api/settings/general` - Obter configurações gerais
- `POST /api/settings/general` - Atualizar configurações gerais
- `GET /api/settings/payment` - Obter configurações de pagamento
- `POST /api/settings/payment` - Atualizar configurações de pagamento
- `GET /api/settings/notification` - Obter configurações de notificação
- `POST /api/settings/notification` - Atualizar configurações de notificação
- `GET /api/settings/integration` - Obter configurações de integração
- `POST /api/settings/integration` - Atualizar configurações de integração

#### Usuários
- `GET /api/users` - Listar usuários
- `POST /api/users` - Criar usuário
- `GET /api/users/<id>` - Obter detalhes do usuário
- `PUT /api/users/<id>` - Atualizar usuário
- `DELETE /api/users/<id>` - Excluir usuário

### 5. Implementar Autenticação

O sistema utiliza autenticação baseada em token JWT. Certifique-se de que o backend está configurado para:

1. Gerar tokens JWT no login
2. Validar tokens em requisições protegidas
3. Renovar tokens quando necessário
4. Invalidar tokens no logout

### 6. Testar a Integração

Após a implementação, teste a integração acessando:

1. Página de login: `https://seu-app.herokuapp.com/`
2. Verifique se o login funciona corretamente
3. Teste cada página e funcionalidade do sistema
4. Verifique se as chamadas de API estão funcionando
5. Teste em diferentes dispositivos para garantir responsividade

## Adaptações Necessárias

Se algum endpoint da API não estiver implementado exatamente como esperado pelo frontend, você tem duas opções:

1. **Adaptar o Backend**: Implementar os endpoints conforme esperado pelo frontend
2. **Adaptar o Frontend**: Modificar as chamadas de API no frontend para corresponder aos endpoints existentes

### Exemplo de Adaptação no Frontend

Se o endpoint para listar motoristas for `/api/motoristas` em vez de `/api/drivers`, você pode modificar o arquivo JavaScript:

```javascript
// Antes
fetchAPI('/api/drivers')
    .then(data => {
        // Processar dados
    });

// Depois
fetchAPI('/api/motoristas')
    .then(data => {
        // Processar dados
    });
```

## Considerações de Segurança

1. **CORS**: Configure o backend para permitir requisições do frontend
2. **Proteção CSRF**: Implemente proteção contra ataques CSRF
3. **Validação de Entrada**: Valide todas as entradas no backend
4. **Sanitização de Saída**: Sanitize todas as saídas para evitar XSS

## Solução de Problemas

### Erro 404 em Chamadas de API

Verifique se:
- O endpoint está implementado no backend
- A URL está correta no frontend
- As rotas estão registradas corretamente no Flask

### Erro de CORS

Adicione os cabeçalhos CORS necessários no backend:

```python
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)
```

### Problemas de Autenticação

Verifique se:
- O token JWT está sendo armazenado corretamente
- O token está sendo enviado em todas as requisições
- O backend está validando o token corretamente

## Conclusão

Seguindo este guia, você deve conseguir integrar com sucesso o frontend desenvolvido com o backend Flask existente do sistema MenezesLog. Se encontrar algum problema durante a integração, revise os passos acima e verifique se todas as configurações estão corretas.
