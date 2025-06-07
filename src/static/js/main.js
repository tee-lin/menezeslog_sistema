/**
 * MenezesLog - JavaScript Principal
 * Funções globais e utilitárias para o sistema
 */

// Configurações globais
const API_BASE_URL = '/api';
const TOKEN_KEY = 'menezeslog_token';
const USER_KEY = 'menezeslog_user';

// Funções de autenticação
function isAuthenticated() {
    return localStorage.getItem(TOKEN_KEY) !== null;
}

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
}

function setAuthData(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function logout() {
    clearAuthData();
    window.location.href = '/index.html';
}

// Funções de requisição HTTP
async function fetchAPI(endpoint, options = {}) {
    const token = getToken();
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, mergedOptions);
        
        // Verificar se o token expirou
        if (response.status === 401) {
            clearAuthData();
            window.location.href = '/index.html?expired=true';
            return null;
        }
        
        // Para respostas não-JSON
        if (response.headers.get('content-type')?.indexOf('application/json') === -1) {
            return response;
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Ocorreu um erro na requisição');
        }
        
        return data;
    } catch (error) {
        console.error('Erro na requisição:', error);
        showNotification(error.message || 'Ocorreu um erro na comunicação com o servidor', 'error');
        throw error;
    }
}

// Funções de manipulação de DOM
function showNotification(message, type = 'info', duration = 5000) {
    // Verificar se o container de notificações existe
    let notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }
    
    // Criar notificação
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    notification.style.minWidth = '250px';
    notification.style.marginBottom = '10px';
    notification.innerHTML = message;
    
    // Adicionar ao container
    notificationContainer.appendChild(notification);
    
    // Remover após o tempo especificado
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.5s';
        
        setTimeout(() => {
            notificationContainer.removeChild(notification);
        }, 500);
    }, duration);
}

function createLoadingSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'loader';
    return spinner;
}

function showLoading(container) {
    const loadingElement = createLoadingSpinner();
    container.innerHTML = '';
    container.appendChild(loadingElement);
}

function hideLoading(container) {
    const loader = container.querySelector('.loader');
    if (loader) {
        container.removeChild(loader);
    }
}

// Funções de formatação
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR').format(date);
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// Funções de validação
function validateRequired(value) {
    return value !== null && value !== undefined && value.toString().trim() !== '';
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

function validateCPF(cpf) {
    cpf = cpf.replace(/[^\d]/g, '');
    
    if (cpf.length !== 11) return false;
    
    // Verificar se todos os dígitos são iguais
    if (/^(\d)\1+$/.test(cpf)) return false;
    
    // Validação do primeiro dígito verificador
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    
    let remainder = sum % 11;
    let digit1 = remainder < 2 ? 0 : 11 - remainder;
    
    if (parseInt(cpf.charAt(9)) !== digit1) return false;
    
    // Validação do segundo dígito verificador
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    
    remainder = sum % 11;
    let digit2 = remainder < 2 ? 0 : 11 - remainder;
    
    return parseInt(cpf.charAt(10)) === digit2;
}

function validateCNPJ(cnpj) {
    cnpj = cnpj.replace(/[^\d]/g, '');
    
    if (cnpj.length !== 14) return false;
    
    // Verificar se todos os dígitos são iguais
    if (/^(\d)\1+$/.test(cnpj)) return false;
    
    // Validação do primeiro dígito verificador
    let size = cnpj.length - 2;
    let numbers = cnpj.substring(0, size);
    const digits = cnpj.substring(size);
    let sum = 0;
    let pos = size - 7;
    
    for (let i = size; i >= 1; i--) {
        sum += parseInt(numbers.charAt(size - i)) * pos--;
        if (pos < 2) pos = 9;
    }
    
    let result = sum % 11 < 2 ? 0 : 11 - (sum % 11);
    if (result !== parseInt(digits.charAt(0))) return false;
    
    // Validação do segundo dígito verificador
    size = size + 1;
    numbers = cnpj.substring(0, size);
    sum = 0;
    pos = size - 7;
    
    for (let i = size; i >= 1; i--) {
        sum += parseInt(numbers.charAt(size - i)) * pos--;
        if (pos < 2) pos = 9;
    }
    
    result = sum % 11 < 2 ? 0 : 11 - (sum % 11);
    
    return result === parseInt(digits.charAt(1));
}

// Funções de manipulação de tabelas
function createPagination(currentPage, totalPages, onPageChange) {
    const pagination = document.createElement('nav');
    pagination.setAttribute('aria-label', 'Navegação de páginas');
    
    const ul = document.createElement('ul');
    ul.className = 'pagination justify-content-center';
    
    // Botão Anterior
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.textContent = 'Anterior';
    
    if (currentPage > 1) {
        prevLink.addEventListener('click', (e) => {
            e.preventDefault();
            onPageChange(currentPage - 1);
        });
    }
    
    prevLi.appendChild(prevLink);
    ul.appendChild(prevLi);
    
    // Páginas numeradas
    const maxPagesToShow = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
    
    if (endPage - startPage + 1 < maxPagesToShow) {
        startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        
        if (i !== currentPage) {
            pageLink.addEventListener('click', (e) => {
                e.preventDefault();
                onPageChange(i);
            });
        }
        
        pageLi.appendChild(pageLink);
        ul.appendChild(pageLi);
    }
    
    // Botão Próximo
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.textContent = 'Próximo';
    
    if (currentPage < totalPages) {
        nextLink.addEventListener('click', (e) => {
            e.preventDefault();
            onPageChange(currentPage + 1);
        });
    }
    
    nextLi.appendChild(nextLink);
    ul.appendChild(nextLi);
    
    pagination.appendChild(ul);
    return pagination;
}

// Funções de exportação
function exportToCSV(data, filename) {
    if (!data || !data.length) {
        showNotification('Não há dados para exportar', 'warning');
        return;
    }
    
    // Obter cabeçalhos
    const headers = Object.keys(data[0]);
    
    // Criar linhas de dados
    const csvRows = [];
    
    // Adicionar cabeçalhos
    csvRows.push(headers.join(','));
    
    // Adicionar dados
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            // Escapar aspas e adicionar aspas em volta de strings
            return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
        });
        csvRows.push(values.join(','));
    }
    
    // Combinar em uma string CSV
    const csvString = csvRows.join('\n');
    
    // Criar blob e link para download
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    // Criar URL para o blob
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename || 'export.csv');
    link.style.visibility = 'hidden';
    
    // Adicionar ao DOM, clicar e remover
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    // Verificar autenticação em páginas protegidas
    const isLoginPage = window.location.pathname.includes('index.html') || window.location.pathname === '/';
    
    if (!isLoginPage && !isAuthenticated()) {
        window.location.href = '/index.html?redirect=' + encodeURIComponent(window.location.pathname);
        return;
    }
    
    // Verificar parâmetros de URL
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.get('expired') === 'true') {
        showNotification('Sua sessão expirou. Por favor, faça login novamente.', 'warning');
    }
    
    // Inicializar componentes comuns
    initializeSidebar();
    initializeUserInfo();
    
    // Verificar primeiro acesso para troca de senha
    const user = getUser();
    if (user && user.first_access && !window.location.pathname.includes('change-password.html')) {
        window.location.href = '/change-password.html';
    }
});

// Inicializar barra lateral
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    
    if (sidebarToggle && sidebar && mainContent) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('sidebar-collapsed');
            mainContent.classList.toggle('main-content-expanded');
        });
        
        // Marcar item de menu ativo
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href)) {
                link.classList.add('active');
            }
        });
    }
}

// Inicializar informações do usuário
function initializeUserInfo() {
    const userInfoElement = document.getElementById('user-info');
    const user = getUser();
    
    if (userInfoElement && user) {
        const userNameElement = userInfoElement.querySelector('.user-name');
        const userRoleElement = userInfoElement.querySelector('.user-role');
        const userAvatarElement = userInfoElement.querySelector('.avatar');
        
        if (userNameElement) {
            userNameElement.textContent = user.name || user.username;
        }
        
        if (userRoleElement) {
            userRoleElement.textContent = user.role === 'admin' ? 'Administrador' : 'Motorista';
        }
        
        if (userAvatarElement) {
            userAvatarElement.textContent = (user.name || user.username).charAt(0).toUpperCase();
        }
    }
    
    // Configurar botão de logout
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
}
