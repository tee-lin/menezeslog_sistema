// MenezesLog - Sistema de Gestão de Motoristas
// Versão 2.1.0 - Integração Digital Ocean + Supabase
// Data: 2025-06-08

console.log('[MenezesLog] Inicializando aplicação v2.1.0...');

// Configurações globais
const API_BASE_URL = '/api';
const VERSION = '2.1.0';

// Função para mostrar alertas
function showAlert(message, type = 'info') {
    console.log(`[MenezesLog] Alert ${type}:`, message);
    
    // Remover alertas existentes
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Criar novo alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        z-index: 10000;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    // Cores baseadas no tipo
    const colors = {
        'success': '#28a745',
        'error': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8'
    };
    
    alertDiv.style.backgroundColor = colors[type] || colors.info;
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    
    // Remover após 5 segundos
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Função para fazer requisições à API
async function fetchAPI(endpoint, options = {}) {
    try {
        const token = localStorage.getItem('token');
        const url = endpoint.startsWith('/') ? endpoint : `${API_BASE_URL}/${endpoint}`;
        
        // Normalizar URL para evitar duplicação de /api/
        const normalizedUrl = url.replace('/api/api/', '/api/');
        
        console.log(`[MenezesLog] Fazendo requisição para: ${normalizedUrl}`);
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            }
        };
        
        const response = await fetch(normalizedUrl, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`[MenezesLog] Resposta recebida de ${normalizedUrl}:`, data);
        return data;
        
    } catch (error) {
        console.error(`[MenezesLog] Erro na requisição para ${endpoint}:`, error);
        throw new Error('Ocorreu um erro na requisição');
    }
}

// Função de login corrigida
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    console.log('[MenezesLog] Iniciando login para:', email);
    
    if (!email || !password) {
        showAlert('Por favor, preencha email e senha', 'error');
        return;
    }
    
    try {
        console.log('[MenezesLog] Enviando requisição de login...');
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email: email, 
                password: password 
            })
        });
        
        console.log('[MenezesLog] Resposta recebida, status:', response.status);
        
        const data = await response.json();
        console.log('[MenezesLog] Dados da resposta:', data);
        
        if (response.ok && data.success && data.user && data.token) {
            console.log('[MenezesLog] Login bem-sucedido!');
            
            // FORÇAR salvamento no localStorage
            try {
                localStorage.clear(); // Limpar dados antigos
                
                localStorage.setItem('user', JSON.stringify(data.user));
                localStorage.setItem('token', data.token);
                
                // Verificar se foi salvo
                const savedUser = localStorage.getItem('user');
                const savedToken = localStorage.getItem('token');
                
                console.log('[MenezesLog] Dados salvos no localStorage:');
                console.log('User:', savedUser);
                console.log('Token:', savedToken);
                
                if (!savedUser || !savedToken) {
                    throw new Error('Falha ao salvar dados no localStorage');
                }
                
                // Redirecionar baseado no role
                console.log('[MenezesLog] Redirecionando usuário, role:', data.user.role);
                
                if (data.user.role === 'admin' || data.user.role === 'manager') {
                    console.log('[MenezesLog] Redirecionando para dashboard admin');
                    window.location.href = '/admin_dashboard.html';
                } else {
                    console.log('[MenezesLog] Redirecionando para dashboard motorista');
                    window.location.href = '/motorista_dashboard.html';
                }
                
            } catch (storageError) {
                console.error('[MenezesLog] Erro ao salvar no localStorage:', storageError);
                showAlert('Erro ao salvar dados de login', 'error');
            }
            
        } else {
            console.error('[MenezesLog] Erro no login:', data.error);
            showAlert(data.error || 'Credenciais inválidas', 'error');
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro na requisição de login:', error);
        showAlert('Erro de conexão. Tente novamente.', 'error');
    }
}

// Função para verificar autenticação
function checkAuthentication() {
    console.log('[MenezesLog] Verificando autenticação...');
    
    try {
        const userStr = localStorage.getItem('user');
        const token = localStorage.getItem('token');
        
        console.log('[MenezesLog] Dados do localStorage:');
        console.log('User string:', userStr);
        console.log('Token:', token);
        
        if (!userStr || !token) {
            console.log('[MenezesLog] Dados de autenticação não encontrados');
            window.location.href = '/';
            return false;
        }
        
        const user = JSON.parse(userStr);
        console.log('[MenezesLog] Usuário autenticado:', user);
        
        if (!user || !user.id) {
            console.log('[MenezesLog] Dados de usuário inválidos');
            localStorage.clear();
            window.location.href = '/';
            return false;
        }
        
        console.log('[MenezesLog] Autenticação válida para:', user.email, 'Role:', user.role);
        return true;
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao verificar autenticação:', error);
        localStorage.clear();
        window.location.href = '/';
        return false;
    }
}

// Função para inicializar informações do usuário
function initializeUserInfo() {
    console.log('[MenezesLog] Inicializando informações do usuário...');
    
    if (!checkAuthentication()) {
        return;
    }
    
    try {
        const user = JSON.parse(localStorage.getItem('user'));
        
        console.log('[MenezesLog] Inicializando interface para usuário:', user);
        
        // Atualizar nome do usuário
        const userNameElement = document.getElementById('user-name');
        if (userNameElement) {
            const displayName = user.first_name && user.last_name 
                ? `${user.first_name} ${user.last_name}` 
                : user.username || user.email;
            userNameElement.textContent = displayName;
            console.log('[MenezesLog] Nome definido:', displayName);
        }
        
        // Atualizar role do usuário
        const userRoleElement = document.getElementById('user-role');
        if (userRoleElement) {
            const roleNames = {
                'admin': 'Administrador',
                'manager': 'Gerente', 
                'driver': 'Motorista',
                'user': 'Usuário'
            };
            
            const roleName = roleNames[user.role] || user.role || 'Usuário';
            userRoleElement.textContent = roleName;
            console.log('[MenezesLog] Role definido:', roleName);
        }
        
        // Configurar driver_id
        if (user.role === 'driver') {
            localStorage.setItem('driver_id', user.id.toString());
        } else {
            localStorage.setItem('driver_id', '1'); // ID padrão para admin
        }
        
        console.log('[MenezesLog] Driver ID definido:', localStorage.getItem('driver_id'));
        console.log('[MenezesLog] Inicialização concluída com sucesso');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao inicializar usuário:', error);
        localStorage.clear();
        window.location.href = '/';
    }
}

// Função para logout
function handleLogout() {
    console.log('[MenezesLog] Fazendo logout...');
    localStorage.clear();
    window.location.href = '/';
}

// Função para carregar dados do dashboard
async function loadDashboardData() {
    console.log('[MenezesLog] Carregando dados do dashboard...');
    
    if (!checkAuthentication()) {
        return;
    }
    
    try {
        const user = JSON.parse(localStorage.getItem('user'));
        const driverId = localStorage.getItem('driver_id') || user.id;
        
        console.log('[MenezesLog] Carregando dados para driver ID:', driverId);
        
        // Carregar dados em paralelo com fallback para dados simulados
        const promises = [
            loadPaymentData(driverId),
            loadBonusData(driverId),
            loadDiscountData(driverId),
            loadRecentInvoices(driverId)
        ];
        
        await Promise.allSettled(promises);
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar dados do dashboard:', error);
        showAlert('Erro ao carregar dados do dashboard', 'warning');
    }
}

// Função para carregar dados de pagamento
async function loadPaymentData(driverId) {
    try {
        console.log('[MenezesLog] Carregando dados de pagamento...');
        
        // Tentar carregar dados reais da API
        try {
            const data = await fetchAPI(`payment/current?driver_id=${driverId}`);
            updatePaymentUI(data);
        } catch (apiError) {
            console.log('[MenezesLog] API não disponível, usando dados simulados');
            // Dados simulados para demonstração
            const simulatedData = {
                current_month: {
                    gross_amount: 5500.00,
                    bonuses: 300.00,
                    discounts: 150.00,
                    net_amount: 5650.00
                },
                last_payment: {
                    date: '2024-11-15',
                    amount: 5200.00
                }
            };
            updatePaymentUI(simulatedData);
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar dados de pagamento:', error);
    }
}

// Função para atualizar UI de pagamento
function updatePaymentUI(data) {
    try {
        const elements = {
            'gross-amount': data.current_month?.gross_amount,
            'bonus-amount': data.current_month?.bonuses,
            'discount-amount': data.current_month?.discounts,
            'net-amount': data.current_month?.net_amount,
            'last-payment-date': data.last_payment?.date,
            'last-payment-amount': data.last_payment?.amount
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                if (id.includes('amount')) {
                    element.textContent = `R$ ${value.toFixed(2).replace('.', ',')}`;
                } else if (id.includes('date')) {
                    element.textContent = new Date(value).toLocaleDateString('pt-BR');
                } else {
                    element.textContent = value;
                }
            }
        });
        
        console.log('[MenezesLog] UI de pagamento atualizada');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao atualizar UI de pagamento:', error);
    }
}

// Função para carregar dados de bonificação
async function loadBonusData(driverId) {
    try {
        console.log('[MenezesLog] Carregando dados de bonificação...');
        
        try {
            const data = await fetchAPI(`bonus/summary?driver_id=${driverId}&period=month`);
            updateBonusUI(data);
        } catch (apiError) {
            // Dados simulados
            const simulatedData = {
                total_bonuses: 300.00,
                bonuses: [
                    { type: 'Pontualidade', amount: 150.00 },
                    { type: 'Economia de Combustível', amount: 100.00 },
                    { type: 'Avaliação do Cliente', amount: 50.00 }
                ]
            };
            updateBonusUI(simulatedData);
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar dados de bonificação:', error);
    }
}

// Função para atualizar UI de bonificação
function updateBonusUI(data) {
    try {
        const totalElement = document.getElementById('total-bonus');
        if (totalElement && data.total_bonuses) {
            totalElement.textContent = `R$ ${data.total_bonuses.toFixed(2).replace('.', ',')}`;
        }
        
        const listElement = document.getElementById('bonus-list');
        if (listElement && data.bonuses) {
            listElement.innerHTML = data.bonuses.map(bonus => 
                `<div class="bonus-item">
                    <span>${bonus.type}</span>
                    <span>R$ ${bonus.amount.toFixed(2).replace('.', ',')}</span>
                </div>`
            ).join('');
        }
        
        console.log('[MenezesLog] UI de bonificação atualizada');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao atualizar UI de bonificação:', error);
    }
}

// Função para carregar dados de desconto
async function loadDiscountData(driverId) {
    try {
        console.log('[MenezesLog] Carregando dados de desconto...');
        
        try {
            const data = await fetchAPI(`discount/summary?driver_id=${driverId}`);
            updateDiscountUI(data);
        } catch (apiError) {
            // Dados simulados
            const simulatedData = {
                total_discounts: 150.00,
                discounts: [
                    { type: 'Multa de Trânsito', amount: 100.00 },
                    { type: 'Manutenção', amount: 50.00 }
                ]
            };
            updateDiscountUI(simulatedData);
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar dados de desconto:', error);
    }
}

// Função para atualizar UI de desconto
function updateDiscountUI(data) {
    try {
        const totalElement = document.getElementById('total-discount');
        if (totalElement && data.total_discounts) {
            totalElement.textContent = `R$ ${data.total_discounts.toFixed(2).replace('.', ',')}`;
        }
        
        const listElement = document.getElementById('discount-list');
        if (listElement && data.discounts) {
            listElement.innerHTML = data.discounts.map(discount => 
                `<div class="discount-item">
                    <span>${discount.type}</span>
                    <span>R$ ${discount.amount.toFixed(2).replace('.', ',')}</span>
                </div>`
            ).join('');
        }
        
        console.log('[MenezesLog] UI de desconto atualizada');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao atualizar UI de desconto:', error);
    }
}

// Função para carregar notas fiscais recentes
async function loadRecentInvoices(driverId) {
    try {
        console.log('[MenezesLog] Carregando notas fiscais recentes...');
        
        try {
            const data = await fetchAPI(`invoice/recent?driver_id=${driverId}&limit=5`);
            updateInvoicesUI(data);
        } catch (apiError) {
            // Dados simulados
            const simulatedData = {
                invoices: [
                    { id: 1, number: 'NF-001', date: '2024-11-01', amount: 1200.00, status: 'Emitida' },
                    { id: 2, number: 'NF-002', date: '2024-11-15', amount: 1350.00, status: 'Emitida' },
                    { id: 3, number: 'NF-003', date: '2024-11-30', amount: 1100.00, status: 'Pendente' }
                ]
            };
            updateInvoicesUI(simulatedData);
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar notas fiscais:', error);
    }
}

// Função para atualizar UI de notas fiscais
function updateInvoicesUI(data) {
    try {
        const listElement = document.getElementById('recent-invoices');
        if (listElement && data.invoices) {
            listElement.innerHTML = data.invoices.map(invoice => 
                `<div class="invoice-item">
                    <div class="invoice-number">${invoice.number}</div>
                    <div class="invoice-date">${new Date(invoice.date).toLocaleDateString('pt-BR')}</div>
                    <div class="invoice-amount">R$ ${invoice.amount.toFixed(2).replace('.', ',')}</div>
                    <div class="invoice-status status-${invoice.status.toLowerCase()}">${invoice.status}</div>
                </div>`
            ).join('');
        }
        
        console.log('[MenezesLog] UI de notas fiscais atualizada');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao atualizar UI de notas fiscais:', error);
    }
}

// Função para carregar lista de motoristas
async function loadDriversList() {
    try {
        console.log('[MenezesLog] Carregando lista de motoristas...');
        
        try {
            const data = await fetchAPI('drivers');
            updateDriversListUI(data);
        } catch (apiError) {
            // Dados simulados
            const simulatedData = {
                drivers: [
                    { id: 1, name: 'João Silva', cpf: '123.456.789-00', status: 'active', phone: '(11) 99999-9999' },
                    { id: 2, name: 'Maria Santos', cpf: '987.654.321-00', status: 'active', phone: '(11) 88888-8888' },
                    { id: 3, name: 'Pedro Oliveira', cpf: '456.789.123-00', status: 'inactive', phone: '(11) 77777-7777' }
                ]
            };
            updateDriversListUI(simulatedData);
        }
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao carregar lista de motoristas:', error);
    }
}

// Função para atualizar UI da lista de motoristas
function updateDriversListUI(data) {
    try {
        const tableBody = document.getElementById('drivers-table-body');
        if (tableBody && data.drivers) {
            tableBody.innerHTML = data.drivers.map(driver => 
                `<tr>
                    <td>${driver.name}</td>
                    <td>${driver.cpf}</td>
                    <td>${driver.phone || 'N/A'}</td>
                    <td>
                        <span class="status-badge status-${driver.status}">
                            ${driver.status === 'active' ? 'Ativo' : 'Inativo'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editDriver(${driver.id})">Editar</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteDriver(${driver.id})">Excluir</button>
                    </td>
                </tr>`
            ).join('');
        }
        
        console.log('[MenezesLog] UI da lista de motoristas atualizada');
        
    } catch (error) {
        console.error('[MenezesLog] Erro ao atualizar UI da lista de motoristas:', error);
    }
}

// Funções para gerenciamento de motoristas
function editDriver(driverId) {
    console.log('[MenezesLog] Editando motorista:', driverId);
    showAlert('Funcionalidade de edição em desenvolvimento', 'info');
}

function deleteDriver(driverId) {
    console.log('[MenezesLog] Excluindo motorista:', driverId);
    if (confirm('Tem certeza que deseja excluir este motorista?')) {
        showAlert('Funcionalidade de exclusão em desenvolvimento', 'info');
    }
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MenezesLog] DOM carregado, inicializando aplicação...');
    
    // Verificar se estamos na página de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        console.log('[MenezesLog] Página de login detectada');
        loginForm.addEventListener('submit', handleLogin);
        return;
    }
    
    // Para outras páginas, verificar autenticação e inicializar
    if (checkAuthentication()) {
        initializeUserInfo();
        
        // Carregar dados específicos da página
        const currentPage = window.location.pathname;
        console.log('[MenezesLog] Página atual:', currentPage);
        
        if (currentPage.includes('dashboard')) {
            loadDashboardData();
        } else if (currentPage.includes('motoristas')) {
            loadDriversList();
        }
        
        // Configurar botão de logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }
    }
});

// Exportar funções para uso global
window.MenezesLog = {
    version: VERSION,
    showAlert,
    fetchAPI,
    handleLogin,
    handleLogout,
    checkAuthentication,
    initializeUserInfo,
    loadDashboardData,
    loadDriversList,
    editDriver,
    deleteDriver
};

console.log('[MenezesLog] Aplicação inicializada com sucesso!');

