/* ============================================
   Mini App JavaScript - إدارة الأزرار
   ============================================ */

// State
let currentParentId = null;
let currentPath = [];
let editingButtonId = null;
let deleteButtonId = null;

// API Base URL
const API_BASE = '/api';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Telegram WebApp if available
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
    
    refreshTree();
});

// API Helper
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    // Add Telegram init data if available
    if (window.Telegram && window.Telegram.WebApp) {
        options.headers['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData;
    }
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error_ar || result.error || 'حدث خطأ');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Refresh Tree
async function refreshTree() {
    showLoading(true);
    
    try {
        if (currentParentId === null) {
            const result = await apiRequest('/buttons/root?lang=ar');
            renderButtons(result.buttons);
        } else {
            const result = await apiRequest(`/buttons/${currentParentId}/children?lang=ar`);
            renderButtons(result.children);
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Render Buttons
function renderButtons(buttons) {
    const container = document.getElementById('buttonList');
    
    if (!buttons || buttons.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>لا توجد أزرار هنا</p>
                <p>اضغط على ➕ لإضافة زر جديد</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = buttons.map(button => `
        <div class="button-item ${button.is_enabled ? '' : 'disabled'}" 
             onclick="handleButtonClick(${button.id}, '${button.button_type}')"
             data-id="${button.id}">
            <div class="button-icon">${button.icon || '📌'}</div>
            <div class="button-info">
                <div class="button-text">${button.text}</div>
                <div class="button-meta">
                    <span class="button-type ${button.button_type}">${button.button_type === 'menu' ? 'قائمة' : 'خدمة'}</span>
                    ${button.price ? `<span>$${button.price}</span>` : ''}
                    ${!button.is_enabled ? '<span>❌ معطّل</span>' : ''}
                </div>
            </div>
            <div class="button-actions">
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); editButton(${button.id})">✏️</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); toggleButton(${button.id})">${button.is_enabled ? '🔴' : '🟢'}</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); showDeleteConfirm(${button.id})">🗑️</button>
            </div>
            ${button.button_type === 'menu' ? '<span class="button-arrow">›</span>' : ''}
        </div>
    `).join('');
}

// Handle Button Click
function handleButtonClick(buttonId, buttonType) {
    if (buttonType === 'menu') {
        navigateToButton(buttonId);
    } else {
        editButton(buttonId);
    }
}

// Navigate to Button
async function navigateToButton(buttonId) {
    try {
        const result = await apiRequest(`/buttons/${buttonId}?lang=ar`);
        const button = result.button;
        
        currentParentId = buttonId;
        currentPath.push({ id: buttonId, text: button.text });
        
        updateBreadcrumb();
        refreshTree();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Go to Root
function goToRoot() {
    currentParentId = null;
    currentPath = [];
    updateBreadcrumb();
    refreshTree();
}

// Go to Path Index
function goToPath(index) {
    if (index < 0) {
        goToRoot();
        return;
    }
    
    currentPath = currentPath.slice(0, index + 1);
    currentParentId = currentPath[index].id;
    updateBreadcrumb();
    refreshTree();
}

// Update Breadcrumb
function updateBreadcrumb() {
    const breadcrumb = document.getElementById('breadcrumb');
    
    let html = `<span class="breadcrumb-item ${currentPath.length === 0 ? 'active' : ''}" onclick="goToRoot()">🏠 الرئيسية</span>`;
    
    currentPath.forEach((item, index) => {
        const isLast = index === currentPath.length - 1;
        html += `<span class="breadcrumb-separator">/</span>`;
        html += `<span class="breadcrumb-item ${isLast ? 'active' : ''}" onclick="goToPath(${index})">${item.text}</span>`;
    });
    
    breadcrumb.innerHTML = html;
}

// Show Add Button Modal
function showAddButtonModal() {
    editingButtonId = null;
    document.getElementById('modalTitle').textContent = 'إضافة زر جديد';
    document.getElementById('buttonForm').reset();
    document.getElementById('buttonId').value = '';
    document.getElementById('parentId').value = currentParentId || '';
    toggleServiceFields();
    openModal('buttonModal');
}

// Edit Button
async function editButton(buttonId) {
    try {
        const result = await apiRequest(`/buttons/${buttonId}?lang=ar`);
        const button = result.button;
        
        editingButtonId = buttonId;
        document.getElementById('modalTitle').textContent = 'تعديل الزر';
        
        document.getElementById('buttonId').value = button.id;
        document.getElementById('parentId').value = button.parent_id || '';
        document.getElementById('buttonKey').value = button.button_key;
        document.getElementById('textAr').value = button.text_ar || button.text;
        document.getElementById('textEn').value = button.text_en || '';
        document.getElementById('icon').value = button.icon || '';
        document.getElementById('buttonType').value = button.button_type;
        document.getElementById('isEnabled').value = button.is_enabled ? '1' : '0';
        document.getElementById('price').value = button.price || 0;
        document.getElementById('defaultQuantity').value = button.default_quantity || 1;
        document.getElementById('askQuantity').checked = button.ask_quantity || false;
        document.getElementById('messageAr').value = button.message_ar || '';
        document.getElementById('messageEn').value = button.message_en || '';
        
        toggleServiceFields();
        openModal('buttonModal');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Toggle Service Fields
function toggleServiceFields() {
    const buttonType = document.getElementById('buttonType').value;
    const serviceFields = document.getElementById('serviceFields');
    
    if (buttonType === 'service') {
        serviceFields.classList.remove('hidden');
    } else {
        serviceFields.classList.add('hidden');
    }
}

// Save Button
async function saveButton(event) {
    event.preventDefault();
    
    const data = {
        button_key: document.getElementById('buttonKey').value,
        text_ar: document.getElementById('textAr').value,
        text_en: document.getElementById('textEn').value,
        icon: document.getElementById('icon').value || null,
        button_type: document.getElementById('buttonType').value,
        is_enabled: document.getElementById('isEnabled').value === '1',
        parent_id: document.getElementById('parentId').value ? parseInt(document.getElementById('parentId').value) : null,
        message_ar: document.getElementById('messageAr').value || null,
        message_en: document.getElementById('messageEn').value || null
    };
    
    if (data.button_type === 'service') {
        data.price = parseFloat(document.getElementById('price').value) || 0;
        data.default_quantity = parseInt(document.getElementById('defaultQuantity').value) || 1;
        data.ask_quantity = document.getElementById('askQuantity').checked;
    }
    
    try {
        if (editingButtonId) {
            await apiRequest(`/buttons/${editingButtonId}`, 'PUT', data);
            showToast('تم تحديث الزر بنجاح', 'success');
        } else {
            await apiRequest('/buttons', 'POST', data);
            showToast('تم إضافة الزر بنجاح', 'success');
        }
        
        closeModal('buttonModal');
        refreshTree();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Toggle Button Enable/Disable
async function toggleButton(buttonId) {
    try {
        await apiRequest(`/buttons/${buttonId}/toggle`, 'POST');
        showToast('تم تغيير حالة الزر', 'success');
        refreshTree();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Show Delete Confirm
function showDeleteConfirm(buttonId) {
    deleteButtonId = buttonId;
    openModal('deleteModal');
}

// Confirm Delete
async function confirmDelete() {
    if (!deleteButtonId) return;
    
    try {
        await apiRequest(`/buttons/${deleteButtonId}`, 'DELETE');
        showToast('تم حذف الزر بنجاح', 'success');
        closeModal('deleteModal');
        refreshTree();
    } catch (error) {
        showToast(error.message, 'error');
    }
    
    deleteButtonId = null;
}

// Export/Import Modal
function showExportImport() {
    openModal('exportImportModal');
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');
    document.getElementById(`${tab}Tab`).classList.add('active');
}

// Export Tree
async function exportTree() {
    try {
        const result = await apiRequest('/buttons/export');
        document.getElementById('exportData').value = JSON.stringify(result.data, null, 2);
        showToast('تم التصدير بنجاح', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Import Tree
async function importTree() {
    const importData = document.getElementById('importData').value;
    
    if (!importData) {
        showToast('الرجاء لصق بيانات JSON', 'error');
        return;
    }
    
    try {
        const treeData = JSON.parse(importData);
        await apiRequest('/buttons/import', 'POST', { tree: treeData });
        showToast('تم الاستيراد بنجاح', 'success');
        closeModal('exportImportModal');
        goToRoot();
    } catch (error) {
        showToast(error.message || 'خطأ في تنسيق JSON', 'error');
    }
}

// Modal Functions
function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Loading
function showLoading(show) {
    const loading = document.getElementById('loading');
    const buttonList = document.getElementById('buttonList');
    
    if (show) {
        loading.style.display = 'flex';
        buttonList.style.display = 'none';
    } else {
        loading.style.display = 'none';
        buttonList.style.display = 'flex';
    }
}

// Toast
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}
