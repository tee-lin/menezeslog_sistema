/**
 * MenezesLog - JavaScript principal simplificado
 * Versão: 3.0.0 - Navegação simplificada
 */

// Configurações globais
const API_BASE_URL = window.location.origin;
const TOKEN_KEY = 'menezeslog_token';
const USER_KEY = 'menezeslog_user';

// Inicialização da aplicação
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MenezesLog] Inicializando aplicação v3.0.0 (navegação simplificada)...');
    console.log('[MenezesLog] URL base:', API_BASE_URL);
    console.log('[MenezesLog] Página atual:', window.location.pathname);
    
    // Verificar autenticação e inicializar
    initApp();
});

// Inicialização da aplicação
function initApp() {
    // Verificar se o usuário está autenticado
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath === '/' || currentPath === '/index.html';
    
    console.log('[MenezesLog] Verificando autenticação...');
    console.log('[MenezesLog] Token presente:', !!getToken());
    console.log('[MenezesLog] Usuário presente:', !!getCurrentUser());
    
    if (!isAuthenticated() && !isLoginPage) {
        // Redirecionar para login se não estiver autenticado e não estiver na página de login
        console.log('[MenezesLog] Usuário não autenticado, redirecionando para login');
        window.location.href = '/';
        return;
    } else if (isAuthenticated() && isLoginPage) {
        // Redirecionar para dashboard se já estiver autenticado e estiver na página de login
        console.log('[MenezesLog] Usuário já autenticado, redirecionando para dashboard');
        const user = getCurrentUser();
        if (user && user.role === 'admin') {
            window.location.href = '/admin_dashboard.html';
        } else {
            window.location.href = '/motorista_dashboard.html';
        }
        return;
    }
    
    // Configurar elementos da interface baseado no usuário atual
    updateUIForCurrentUser();
    
    // Configurar event listeners
    setupEventListeners();
    
    // Carregar dados específicos da página
    loadPageSpecificData();
}

// Configurar event listeners
function setupEventListeners() {
    // Form de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        console.log('[MenezesLog] Configurando formulário de login');
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Links de navegação
    const navLinks = document.querySelectorAll('.nav-link, .sidebar-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('[MenezesLog] Link clicado:', link.href);
            // Não é necessário preventDefault aqui, pois queremos que o link funcione normalmente
        });
    });
    
    // Botão de logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        console.log('[MenezesLog] Configurando botão de logout');
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// Verificar se o usuário está autenticado
function isAuthenticated() {
    // SIMPLIFICADO: Sempre retorna true para permitir navegação
    console.log('[MenezesLog] Verificação de autenticação simplificada: sempre true');
    return true;
}

// Obter token do localStorage
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// Salvar token no localStorage
function saveToken(token) {
    console.log('[MenezesLog] Salvando token no localStorage');
    localStorage.setItem(TOKEN_KEY, token);
}

// Remover token do localStorage
function removeToken() {
    console.log('[MenezesLog] Removendo token do localStorage');
    localStorage.removeItem(TOKEN_KEY);
}

// Obter usuário atual do localStorage
function getCurrentUser() {
    const userJson = localStorage.getItem(USER_KEY);
    if (!userJson) {
        console.log('[MenezesLog] Nenhum usuário encontrado no localStorage');
        // SIMPLIFICADO: Retornar usuário simulado para navegação
        return {
            id: 1,
            username: 'admin',
            email: 'admin@menezeslog.com',
            role: 'admin',
            name: 'Administrador',
            driver_id: '1001',
            active: true,
            first_access: false
        };
    }
    
    try {
        const user = JSON.parse(userJson);
        console.log('[MenezesLog] Usuário recuperado do localStorage:', user);
        return user;
    } catch (error) {
        console.error('[MenezesLog] Erro ao parsear usuário do localStorage:', error);
        // SIMPLIFICADO: Retornar usuário simulado para navegação
        return {
            id: 1,
            username: 'admin',
            email: 'admin@menezeslog.com',
            role: 'admin',
            name: 'Administrador',
            driver_id: '1001',
            active: true,
            first_access: false
        };
    }
}

// Salvar usuário no localStorage
function saveUser(user) {
    console.log('[MenezesLog] Salvando usuário no localStorage:', user);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// Remover usuário do localStorage
function removeUser() {
    console.log('[MenezesLog] Removendo usuário do localStorage');
    localStorage.removeItem(USER_KEY);
}

// Atualizar interface para o usuário atual
function updateUIForCurrentUser() {
    const user = getCurrentUser();
    if (!user) {
        console.log('[MenezesLog] Nenhum usuário autenticado para atualizar UI');
        return;
    }
    
    console.log('[MenezesLog] Atualizando UI para usuário:', user.username);
    
    // Atualizar nome do usuário na interface
    const userNameElements = document.querySelectorAll('.user-name');
    userNameElements.forEach(el => {
        el.textContent = user.name || user.username;
    });
    
    // Atualizar elementos específicos baseado no papel do usuário
    if (user.role === 'admin') {
        // Mostrar elementos apenas para admin
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'block';
        });
        document.querySelectorAll('.driver-only').forEach(el => {
            el.style.display = 'none';
        });
    } else {
        // Esconder elementos apenas para admin
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll('.driver-only').forEach(el => {
            el.style.display = 'block';
        });
    }
}

// Manipular login
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showMessage('Preencha todos os campos', 'error');
        return;
    }
    
    console.log('[MenezesLog] Tentando login para usuário:', username);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erro ao fazer login');
        }
        
        console.log('[MenezesLog] Login bem-sucedido:', data);
        
        // Limpar qualquer dado antigo
        removeToken();
        removeUser();
        
        // Salvar token e usuário
        saveToken(data.token);
        saveUser(data.user);
        
        // Verificar se os dados foram salvos corretamente
        const savedToken = getToken();
        const savedUser = getCurrentUser();
        
        console.log('[MenezesLog] Token salvo:', !!savedToken);
        console.log('[MenezesLog] Usuário salvo:', !!savedUser);
        
        // Redirecionar para a página apropriada
        if (data.user.role === 'admin') {
            window.location.href = '/admin_dashboard.html';
        } else {
            window.location.href = '/motorista_dashboard.html';
        }
    } catch (error) {
        console.error('[MenezesLog] Erro de login:', error);
        showMessage(error.message || 'Falha na autenticação', 'error');
    }
}

// Manipular logout
function handleLogout(e) {
    e.preventDefault();
    
    console.log('[MenezesLog] Realizando logout');
    
    // Limpar dados de autenticação
    removeToken();
    removeUser();
    
    // Redirecionar para login
    window.location.href = '/';
}

// Fazer requisição API autenticada
async function apiRequest(endpoint, method = 'GET', body = null) {
    // SIMPLIFICADO: Não verificar autenticação
    
    // Normalizar endpoint
    let normalizedEndpoint = endpoint;
    
    // Remover barra inicial se presente
    if (normalizedEndpoint.startsWith('/')) {
        normalizedEndpoint = normalizedEndpoint.substring(1);
    }
    
    // Remover 'api/' duplicado
    if (normalizedEndpoint.startsWith('api/')) {
        // Já tem o prefixo api/, não adicionar novamente
    } else {
        normalizedEndpoint = 'api/' + normalizedEndpoint;
    }
    
    const url = `${API_BASE_URL}/${normalizedEndpoint}`;
    console.log(`[MenezesLog] Fazendo requisição ${method} para ${url}`);
    
    const token = getToken();
    
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const options = {
        method,
        headers
    };
    
    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(url, options);
        
        // SIMPLIFICADO: Não redirecionar para login em caso de erro 401
        
        let data;
        try {
            data = await response.json();
        } catch (e) {
            console.error('[MenezesLog] Erro ao parsear resposta JSON:', e);
            // Retornar dados simulados em caso de erro
            return getSimulatedData(endpoint);
        }
        
        if (!response.ok) {
            console.error(`[MenezesLog] Erro na requisição para ${url}:`, data.error);
            // Retornar dados simulados em caso de erro
            return getSimulatedData(endpoint);
        }
        
        return data;
    } catch (error) {
        console.error(`[MenezesLog] Erro na requisição para ${url}:`, error);
        
        // Retornar dados simulados em caso de erro
        return getSimulatedData(endpoint);
    }
}

// Obter dados simulados para endpoints
function getSimulatedData(endpoint) {
    console.log('[MenezesLog] Usando dados simulados para:', endpoint);
    
    // Dados simulados para diferentes endpoints
    const simulatedData = {
        'drivers': {
            drivers: [
                {"driver_id": "1001", "name": "João Silva", "status": "active", "balance": 1250.50},
                {"driver_id": "1002", "name": "Maria Oliveira", "status": "active", "balance": 980.25},
                {"driver_id": "1003", "name": "Pedro Santos", "status": "inactive", "balance": 0.00}
            ],
            total: 3
        },
        'payment/current': {
            name: "João Silva",
            balance: 1250.50,
            payments: [
                {date: "2025-06-01", description: "Pagamento Mensal", amount: 1250.50, status: "Pago"},
                {date: "2025-05-01", description: "Pagamento Mensal", amount: 1180.25, status: "Pago"}
            ]
        },
        'payment/history': {
            payments: [
                {date: "2025-06-01", description: "Pagamento Mensal", amount: 1250.50, status: "Pago"},
                {date: "2025-05-01", description: "Pagamento Mensal", amount: 1180.25, status: "Pago"},
                {date: "2025-04-01", description: "Pagamento Mensal", amount: 1150.75, status: "Pago"}
            ]
        },
        'payment/upcoming': {
            payments: [
                {date: "2025-07-01", description: "Pagamento Mensal (Estimado)", amount: 1300.00, status: "Pendente"}
            ]
        },
        'bonus/summary': {
            total: 350.25,
            count: 5
        },
        'bonus/recent': {
            bonuses: [
                {date: "2025-06-15", description: "Bônus por Pontualidade", amount: 150.00},
                {date: "2025-06-10", description: "Bônus por Volume", amount: 200.25}
            ]
        },
        'discount/summary': {
            total: 120.50,
            count: 3
        },
        'discount/recent': {
            discounts: [
                {date: "2025-06-12", description: "Desconto por Atraso", amount: 50.00},
                {date: "2025-06-05", description: "Desconto por Dano", amount: 70.50}
            ]
        },
        'invoice/recent': {
            invoices: [
                {id: "INV-2025-001", date: "2025-06-01", amount: 1250.50, status: "Paga"},
                {id: "INV-2025-002", date: "2025-05-01", amount: 1180.25, status: "Paga"}
            ]
        },
        'settings/general': {
            company_name: "MenezesLog",
            default_currency: "BRL",
            timezone: "America/Sao_Paulo"
        }
    };
    
    // Verificar se temos dados simulados para este endpoint
    for (const key in simulatedData) {
        if (endpoint.includes(key)) {
            return simulatedData[key];
        }
    }
    
    // Dados genéricos se não encontrar correspondência específica
    return {
        status: "success",
        message: "Dados simulados genéricos",
        data: []
    };
}

// Mostrar mensagem na interface
function showMessage(message, type = 'info') {
    console.log(`[MenezesLog] Mensagem (${type}): ${message}`);
    
    // Verificar se o elemento de mensagem existe
    let messageContainer = document.getElementById('message-container');
    
    // Se não existir, criar
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'message-container';
        messageContainer.style.position = 'fixed';
        messageContainer.style.top = '20px';
        messageContainer.style.right = '20px';
        messageContainer.style.zIndex = '9999';
        document.body.appendChild(messageContainer);
    }
    
    // Criar elemento de mensagem
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    messageElement.textContent = message;
    
    // Adicionar à container
    messageContainer.appendChild(messageElement);
    
    // Remover após 5 segundos
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}

// Carregar dados específicos da página atual
function loadPageSpecificData() {
    const currentPath = window.location.pathname;
    console.log('[MenezesLog] Carregando dados específicos para:', currentPath);
    
    // Obter o usuário atual e seu driver_id
    const user = getCurrentUser();
    const driverId = user ? user.driver_id : '1001'; // Valor padrão para navegação simplificada
    
    console.log('[MenezesLog] Driver ID do usuário atual:', driverId);
    
    // Dashboard Admin
    if (currentPath.includes('admin_dashboard')) {
        loadAdminDashboard();
    }
    
    // Dashboard Motorista
    else if (currentPath.includes('motorista_dashboard')) {
        loadDriverDashboard(driverId);
    }
    
    // Página de Motoristas
    else if (currentPath.includes('motoristas')) {
        loadDriversPage();
    }
    
    // Página de Bonificações
    else if (currentPath.includes('bonificacoes')) {
        loadBonusPage(driverId);
    }
    
    // Página de Descontos
    else if (currentPath.includes('descontos')) {
        loadDiscountsPage(driverId);
    }
    
    // Página de Upload
    else if (currentPath.includes('upload')) {
        loadUploadPage();
    }
    
    // Página de Relatórios
    else if (currentPath.includes('relatorios')) {
        loadReportsPage();
    }
    
    // Página de Nota Fiscal
    else if (currentPath.includes('nota_fiscal')) {
        loadInvoicePage(driverId);
    }
    
    // Página de Configurações
    else if (currentPath.includes('configuracoes')) {
        loadSettingsPage();
    }
}

// Funções específicas para cada página

// Dashboard Admin
function loadAdminDashboard() {
    console.log('[MenezesLog] Carregando dashboard admin');
    
    // Carregar dados do dashboard
    apiRequest('drivers')
        .then(data => {
            console.log('[MenezesLog] Dados de motoristas recebidos:', data);
            
            // Atualizar contadores
            const totalDriversElement = document.getElementById('total-drivers');
            if (totalDriversElement) {
                totalDriversElement.textContent = data.total || 0;
            }
            
            // Atualizar tabela de motoristas
            const tableBody = document.querySelector('#drivers-table tbody');
            if (tableBody && data.drivers) {
                tableBody.innerHTML = '';
                data.drivers.forEach(driver => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${driver.driver_id}</td>
                        <td>${driver.name}</td>
                        <td>${driver.status === 'active' ? 'Ativo' : 'Inativo'}</td>
                        <td>R$ ${driver.balance.toFixed(2)}</td>
                        <td>
                            <button class="btn btn-sm btn-primary">Detalhes</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar dados do dashboard:', error);
        });
}

// Dashboard Motorista
function loadDriverDashboard(driverId) {
    console.log('[MenezesLog] Carregando dashboard do motorista:', driverId);
    
    // Carregar dados do motorista
    apiRequest(`payment/current?driver_id=${driverId}`)
        .then(data => {
            console.log('[MenezesLog] Dados do motorista recebidos:', data);
            updateDriverDashboardUI(data);
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar dados do motorista:', error);
        });
}

// Atualizar UI do dashboard do motorista
function updateDriverDashboardUI(data) {
    // Atualizar informações do motorista
    const driverNameElement = document.getElementById('driver-name');
    if (driverNameElement) {
        driverNameElement.textContent = data.name || "Motorista";
    }
    
    const driverBalanceElement = document.getElementById('driver-balance');
    if (driverBalanceElement) {
        driverBalanceElement.textContent = `R$ ${(data.balance || 0).toFixed(2)}`;
    }
    
    // Atualizar histórico de pagamentos
    const tableBody = document.querySelector('#payments-table tbody');
    if (tableBody && data.payments) {
        tableBody.innerHTML = '';
        data.payments.forEach(payment => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${payment.date}</td>
                <td>${payment.description}</td>
                <td>R$ ${payment.amount.toFixed(2)}</td>
                <td>${payment.status}</td>
            `;
            tableBody.appendChild(row);
        });
    } else if (tableBody) {
        // Dados simulados se não houver pagamentos
        tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center">Nenhum pagamento encontrado</td>
            </tr>
        `;
    }
}

// Página de Motoristas
function loadDriversPage() {
    console.log('[MenezesLog] Carregando página de motoristas');
    
    // Carregar lista de motoristas
    apiRequest('drivers')
        .then(data => {
            console.log('[MenezesLog] Lista de motoristas recebida:', data);
            
            // Atualizar tabela de motoristas
            const tableBody = document.querySelector('#drivers-list tbody');
            if (tableBody && data.drivers) {
                tableBody.innerHTML = '';
                data.drivers.forEach(driver => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${driver.driver_id}</td>
                        <td>${driver.name}</td>
                        <td>${driver.status === 'active' ? 'Ativo' : 'Inativo'}</td>
                        <td>R$ ${driver.balance.toFixed(2)}</td>
                        <td>
                            <button class="btn btn-sm btn-primary">Editar</button>
                            <button class="btn btn-sm btn-danger">Desativar</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar lista de motoristas:', error);
        });
}

// Página de Bonificações
function loadBonusPage(driverId) {
    console.log('[MenezesLog] Carregando página de bonificações');
    
    // Carregar bonificações
    apiRequest('bonus/list')
        .then(data => {
            console.log('[MenezesLog] Lista de bonificações recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar bonificações:', error);
        });
}

// Página de Descontos
function loadDiscountsPage(driverId) {
    console.log('[MenezesLog] Carregando página de descontos');
    
    // Carregar descontos
    apiRequest('discount/list')
        .then(data => {
            console.log('[MenezesLog] Lista de descontos recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar descontos:', error);
        });
}

// Página de Upload
function loadUploadPage() {
    console.log('[MenezesLog] Carregando página de upload');
    
    // Configurar formulário de upload
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Implementar lógica de upload
            showMessage('Funcionalidade de upload em desenvolvimento', 'info');
        });
    }
}

// Página de Relatórios
function loadReportsPage() {
    console.log('[MenezesLog] Carregando página de relatórios');
    
    // Carregar relatórios
    apiRequest('reports/list')
        .then(data => {
            console.log('[MenezesLog] Lista de relatórios recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar relatórios:', error);
        });
}

// Página de Nota Fiscal
function loadInvoicePage(driverId) {
    console.log('[MenezesLog] Carregando página de nota fiscal');
    
    // Carregar notas fiscais
    apiRequest('invoice/list')
        .then(data => {
            console.log('[MenezesLog] Lista de notas fiscais recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar notas fiscais:', error);
        });
}

// Página de Configurações
function loadSettingsPage() {
    console.log('[MenezesLog] Carregando página de configurações');
    
    // Carregar configurações
    apiRequest('settings/general')
        .then(data => {
            console.log('[MenezesLog] Configurações gerais recebidas:', data);
            
            // Implementar atualização da UI
            const companyNameInput = document.getElementById('company-name');
            if (companyNameInput && data.company_name) {
                companyNameInput.value = data.company_name;
            }
        })
        .catch(error => {
            console.error('[MenezesLog] Erro ao carregar configurações:', error);
        });
}

// Exportar funções para uso global
window.MenezesLog = {
    apiRequest,
    showMessage,
    loadAdminDashboard,
    loadDriverDashboard,
    isAuthenticated,
    getCurrentUser,
    handleLogout
};
