/**
 * MenezesLog - JavaScript principal com correção de autenticação
 * Este arquivo contém as funções necessárias para o funcionamento do sistema
 * incluindo autenticação, requisições API e manipulação de DOM
 */

// Configurações globais
const API_BASE_URL = window.location.origin;
const TOKEN_KEY = 'menezeslog_token';
const USER_KEY = 'menezeslog_user';

// Inicialização da aplicação
document.addEventListener('DOMContentLoaded', function() {
    initApp();
    setupEventListeners();
});

// Inicialização da aplicação
function initApp() {
    // Verificar se o usuário está autenticado
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath === '/' || currentPath === '/index.html';
    
    if (!isAuthenticated() && !isLoginPage) {
        // Redirecionar para login se não estiver autenticado e não estiver na página de login
        window.location.href = '/';
        return;
    } else if (isAuthenticated() && isLoginPage) {
        // Redirecionar para dashboard se já estiver autenticado e estiver na página de login
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
}

// Configurar event listeners
function setupEventListeners() {
    // Form de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Links de navegação
    const navLinks = document.querySelectorAll('.nav-link, .sidebar-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Não é necessário preventDefault aqui, pois queremos que o link funcione normalmente
            // Apenas garantimos que o token está sendo enviado nas requisições
        });
    });
    
    // Botão de logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// Verificar se o usuário está autenticado
function isAuthenticated() {
    return !!getToken();
}

// Obter token do localStorage
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// Salvar token no localStorage
function saveToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

// Remover token do localStorage
function removeToken() {
    localStorage.removeItem(TOKEN_KEY);
}

// Obter usuário atual do localStorage
function getCurrentUser() {
    const userJson = localStorage.getItem(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
}

// Salvar usuário no localStorage
function saveUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// Remover usuário do localStorage
function removeUser() {
    localStorage.removeItem(USER_KEY);
}

// Atualizar interface para o usuário atual
function updateUIForCurrentUser() {
    const user = getCurrentUser();
    if (!user) return;
    
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
    } else {
        // Esconder elementos apenas para admin
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'none';
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
    
    // Limpar dados de autenticação
    removeToken();
    removeUser();
    
    // Redirecionar para login
    window.location.href = '/';
}

// Fazer requisição API autenticada
async function apiRequest(endpoint, method = 'GET', body = null) {
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
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        // Se a resposta for 401 (Não autorizado), fazer logout
        if (response.status === 401) {
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

// Funções específicas para cada página

// Dashboard Admin
function loadAdminDashboard() {
    if (!isAuthenticated()) return;
    
    // Carregar dados do dashboard
    apiRequest('/api/drivers')
        .then(data => {
            // Atualizar contadores
            document.getElementById('total-drivers').textContent = data.total || 0;
            
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
            showMessage('Erro ao carregar dados do dashboard', 'error');
        });
}

// Dashboard Motorista
function loadDriverDashboard() {
    if (!isAuthenticated()) return;
    
    const user = getCurrentUser();
    if (!user || !user.driver_id) return;
    
    // Carregar dados do motorista
    apiRequest(`/api/drivers/${user.driver_id}`)
        .then(data => {
            // Atualizar informações do motorista
            document.getElementById('driver-name').textContent = data.name;
            document.getElementById('driver-balance').textContent = `R$ ${data.balance.toFixed(2)}`;
            
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
            }
        })
        .catch(error => {
            showMessage('Erro ao carregar dados do motorista', 'error');
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
