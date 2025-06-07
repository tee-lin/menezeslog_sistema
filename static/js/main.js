/**
 * MenezesLog - JavaScript principal com correção de autenticação e URLs de API
 * Este arquivo contém as funções necessárias para o funcionamento do sistema
 * incluindo autenticação, requisições API e manipulação de DOM
 */

// Configurações globais
const API_BASE_URL = window.location.origin;
const TOKEN_KEY = 'menezeslog_token';
const USER_KEY = 'menezeslog_user';

// Inicialização da aplicação
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando aplicação MenezesLog...');
    initApp();
    setupEventListeners();
});

// Inicialização da aplicação
function initApp() {
    console.log('Verificando autenticação...');
    // Verificar se o usuário está autenticado
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath === '/' || currentPath === '/index.html';
    
    if (!isAuthenticated() && !isLoginPage) {
        // Redirecionar para login se não estiver autenticado e não estiver na página de login
        console.log('Usuário não autenticado, redirecionando para login');
        window.location.href = '/';
        return;
    } else if (isAuthenticated() && isLoginPage) {
        // Redirecionar para dashboard se já estiver autenticado e estiver na página de login
        console.log('Usuário já autenticado, redirecionando para dashboard');
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
    
    // Carregar dados específicos da página
    loadPageSpecificData();
}

// Configurar event listeners
function setupEventListeners() {
    // Form de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        console.log('Configurando formulário de login');
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Links de navegação
    const navLinks = document.querySelectorAll('.nav-link, .sidebar-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Não é necessário preventDefault aqui, pois queremos que o link funcione normalmente
            console.log('Link clicado: ' + link.href);
        });
    });
    
    // Botão de logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        console.log('Configurando botão de logout');
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// Verificar se o usuário está autenticado
function isAuthenticated() {
    const token = getToken();
    console.log('Verificando token: ' + (token ? 'Presente' : 'Ausente'));
    return !!token;
}

// Obter token do localStorage
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// Salvar token no localStorage
function saveToken(token) {
    console.log('Salvando token no localStorage');
    localStorage.setItem(TOKEN_KEY, token);
}

// Remover token do localStorage
function removeToken() {
    console.log('Removendo token do localStorage');
    localStorage.removeItem(TOKEN_KEY);
}

// Obter usuário atual do localStorage
function getCurrentUser() {
    const userJson = localStorage.getItem(USER_KEY);
    const user = userJson ? JSON.parse(userJson) : null;
    console.log('Usuário atual:', user);
    return user;
}

// Salvar usuário no localStorage
function saveUser(user) {
    console.log('Salvando usuário no localStorage:', user);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// Remover usuário do localStorage
function removeUser() {
    console.log('Removendo usuário do localStorage');
    localStorage.removeItem(USER_KEY);
}

// Atualizar interface para o usuário atual
function updateUIForCurrentUser() {
    const user = getCurrentUser();
    if (!user) {
        console.log('Nenhum usuário autenticado para atualizar UI');
        return;
    }
    
    console.log('Atualizando UI para usuário:', user.username);
    
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
    
    console.log('Tentando login para usuário:', username);
    
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
        
        console.log('Login bem-sucedido:', data);
        
        // Salvar token e usuário
        saveToken(data.token);
        saveUser(data.user);
        
        // Redirecionar para a página apropriada
        if (data.user.role === 'admin') {
            window.location.href = '/admin_dashboard.html';
        } else {
            window.location.href = '/motorista_dashboard.html';
        }
    } catch (error) {
        console.error('Erro de login:', error);
        showMessage(error.message || 'Falha na autenticação', 'error');
    }
}

// Manipular logout
function handleLogout(e) {
    e.preventDefault();
    
    console.log('Realizando logout');
    
    // Limpar dados de autenticação
    removeToken();
    removeUser();
    
    // Redirecionar para login
    window.location.href = '/';
}

// Fazer requisição API autenticada
async function apiRequest(endpoint, method = 'GET', body = null) {
    // Remover barra inicial se presente para evitar duplicação
    if (endpoint.startsWith('/')) {
        endpoint = endpoint.substring(1);
    }
    
    // Garantir que o endpoint não tenha 'api/' duplicado
    if (endpoint.startsWith('api/')) {
        endpoint = endpoint;
    } else {
        endpoint = 'api/' + endpoint;
    }
    
    const token = getToken();
    console.log(`Fazendo requisição ${method} para ${endpoint}`);
    
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
        const response = await fetch(`${API_BASE_URL}/${endpoint}`, options);
        
        // Se a resposta for 401 (Não autorizado), fazer logout
        if (response.status === 401) {
            console.error('Erro 401: Não autorizado');
            removeToken();
            removeUser();
            window.location.href = '/';
            throw new Error('Sessão expirada. Por favor, faça login novamente.');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erro na requisição');
        }
        
        return data;
    } catch (error) {
        console.error(`Erro na requisição para ${endpoint}:`, error);
        throw error;
    }
}

// Mostrar mensagem na interface
function showMessage(message, type = 'info') {
    console.log(`Mensagem (${type}): ${message}`);
    
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
    console.log('Carregando dados específicos para:', currentPath);
    
    // Obter o usuário atual e seu driver_id
    const user = getCurrentUser();
    const driverId = user ? user.driver_id : null;
    
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
    if (!isAuthenticated()) return;
    
    console.log('Carregando dashboard admin');
    
    // Carregar dados do dashboard
    apiRequest('drivers')
        .then(data => {
            console.log('Dados de motoristas recebidos:', data);
            
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
            console.error('Erro ao carregar dados do dashboard:', error);
            showMessage('Erro ao carregar dados do dashboard', 'error');
        });
}

// Dashboard Motorista
function loadDriverDashboard(driverId) {
    if (!isAuthenticated()) return;
    
    console.log('Carregando dashboard do motorista:', driverId);
    
    if (!driverId) {
        console.warn('Driver ID não disponível, usando dados simulados');
        // Dados simulados para teste
        updateDriverDashboardUI({
            name: "Motorista",
            balance: 1250.50,
            payments: [
                {date: "2025-06-01", description: "Pagamento Mensal", amount: 1250.50, status: "Pago"},
                {date: "2025-05-01", description: "Pagamento Mensal", amount: 1180.25, status: "Pago"}
            ]
        });
        return;
    }
    
    // Carregar dados do motorista
    apiRequest(`payment/current?driver_id=${driverId}`)
        .then(data => {
            console.log('Dados do motorista recebidos:', data);
            updateDriverDashboardUI(data);
        })
        .catch(error => {
            console.error('Erro ao carregar dados do motorista:', error);
            showMessage('Erro ao carregar dados do motorista', 'error');
            
            // Usar dados simulados em caso de erro
            updateDriverDashboardUI({
                name: "Motorista",
                balance: 1250.50,
                payments: [
                    {date: "2025-06-01", description: "Pagamento Mensal", amount: 1250.50, status: "Pago"},
                    {date: "2025-05-01", description: "Pagamento Mensal", amount: 1180.25, status: "Pago"}
                ]
            });
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
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de motoristas');
    
    // Carregar lista de motoristas
    apiRequest('drivers')
        .then(data => {
            console.log('Lista de motoristas recebida:', data);
            
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
            console.error('Erro ao carregar lista de motoristas:', error);
            showMessage('Erro ao carregar lista de motoristas', 'error');
        });
}

// Página de Bonificações
function loadBonusPage(driverId) {
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de bonificações');
    
    // Carregar bonificações
    apiRequest('bonus/list')
        .then(data => {
            console.log('Lista de bonificações recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('Erro ao carregar bonificações:', error);
            showMessage('Erro ao carregar bonificações', 'error');
        });
}

// Página de Descontos
function loadDiscountsPage(driverId) {
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de descontos');
    
    // Carregar descontos
    apiRequest('discount/list')
        .then(data => {
            console.log('Lista de descontos recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('Erro ao carregar descontos:', error);
            showMessage('Erro ao carregar descontos', 'error');
        });
}

// Página de Upload
function loadUploadPage() {
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de upload');
    
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
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de relatórios');
    
    // Carregar relatórios
    apiRequest('reports/list')
        .then(data => {
            console.log('Lista de relatórios recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('Erro ao carregar relatórios:', error);
            showMessage('Erro ao carregar relatórios', 'error');
        });
}

// Página de Nota Fiscal
function loadInvoicePage(driverId) {
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de nota fiscal');
    
    // Carregar notas fiscais
    apiRequest('invoice/list')
        .then(data => {
            console.log('Lista de notas fiscais recebida:', data);
            
            // Implementar atualização da UI
        })
        .catch(error => {
            console.error('Erro ao carregar notas fiscais:', error);
            showMessage('Erro ao carregar notas fiscais', 'error');
        });
}

// Página de Configurações
function loadSettingsPage() {
    if (!isAuthenticated()) return;
    
    console.log('Carregando página de configurações');
    
    // Carregar configurações
    apiRequest('settings/general')
        .then(data => {
            console.log('Configurações gerais recebidas:', data);
            
            // Implementar atualização da UI
            const companyNameInput = document.getElementById('company-name');
            if (companyNameInput && data.company_name) {
                companyNameInput.value = data.company_name;
            }
        })
        .catch(error => {
            console.error('Erro ao carregar configurações:', error);
            showMessage('Erro ao carregar configurações', 'error');
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
