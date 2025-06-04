// Enhanced Admin Dashboard JavaScript for IoT Store
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 IoT Store Admin Dashboard Initialized');
    
    // Initialize all components
    initializeTooltips();
    initializeSidebar();
    initializeNotifications();
    initializeRealTimeUpdates();
    initializeFormEnhancements();
    initializeCharts();
    
    // Add fade-in animation to main content
    document.querySelector('.main-content')?.classList.add('fade-in');
});

// ============================================================================
// TOOLTIP INITIALIZATION
// ============================================================================
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        console.log('✅ Tooltips initialized');
    }
}

// ============================================================================
// SIDEBAR MANAGEMENT
// ============================================================================
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('adminSidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768 && 
                !sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        });
    }
    
    // Add active link highlighting
    highlightActiveNavLink();
    console.log('✅ Sidebar initialized');
}

function highlightActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.includes(href) && href !== '/') {
            link.classList.add('active');
        }
    });
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================
function initializeNotifications() {
    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(message => {
        setTimeout(() => {
            if (message.parentNode) {
                const alert = new bootstrap.Alert(message);
                alert.close();
            }
        }, 5000);
    });
    console.log('✅ Notifications initialized');
}

// Global notification function
function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'error' ? 'alert-danger' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                      type === 'error' ? 'exclamation-triangle' : 
                      type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show notification`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    notification.innerHTML = `
        <i class="fas fa-${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }
    }, duration);
}

// ============================================================================
// REAL-TIME UPDATES
// ============================================================================
function initializeRealTimeUpdates() {
    // Only start real-time updates on dashboard
    if (window.location.pathname.includes('dashboard')) {
        startRealTimeUpdates();
    }
}

function startRealTimeUpdates() {
    console.log('🔄 Starting real-time updates...');
    
    // Update every 30 seconds
    setInterval(updateDashboardData, 30000);
    
    // Update immediately
    updateDashboardData();
}

function updateDashboardData() {
    if (document.hidden) return; // Don't update if tab is not visible
    
    fetch('/api/dashboard/realtime')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
            updateLastUpdatedTime();
        })
        .catch(error => {
            console.error('Real-time update failed:', error);
        });
}

function updateDashboardStats(data) {
    // Update active customers
    const activeCustomersEl = document.getElementById('active-customers');
    if (activeCustomersEl) {
        activeCustomersEl.textContent = data.active_customers || 0;
        animateNumber(activeCustomersEl);
    }
    
    // Update sales today
    const salesTodayEl = document.getElementById('sales-today');
    if (salesTodayEl) {
        salesTodayEl.textContent = `${(data.total_sales_today || 0).toFixed(2)}`;
        animateNumber(salesTodayEl);
    }
    
    // Update fraud alerts
    const fraudAlertsEl = document.getElementById('fraud-alerts');
    if (fraudAlertsEl) {
        fraudAlertsEl.textContent = data.fraud_count || 0;
        animateNumber(fraudAlertsEl);
    }
    
    // Update system health
    const systemHealthEl = document.getElementById('system-health');
    if (systemHealthEl) {
        systemHealthEl.textContent = `${data.system_health || 0}%`;
        animateNumber(systemHealthEl);
    }
}

function updateLastUpdatedTime() {
    const timeEl = document.getElementById('last-updated');
    if (timeEl) {
        timeEl.textContent = new Date().toLocaleTimeString();
    }
}

function animateNumber(element) {
    element.style.transform = 'scale(1.05)';
    element.style.transition = 'transform 0.2s ease';
    setTimeout(() => {
        element.style.transform = 'scale(1)';
    }, 200);
}

// ============================================================================
// FORM ENHANCEMENTS
// ============================================================================
function initializeFormEnhancements() {
    // Add loading states to form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !form.hasAttribute('data-no-loading')) {
                addLoadingState(submitBtn);
            }
        });
    });
    
    // Enhanced form validation
    addFormValidation();
    
    // Auto-save drafts for longer forms
    initializeAutoSave();
    
    console.log('✅ Form enhancements initialized');
}

function addLoadingState(button) {
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="loading-spinner me-2"></span>Processing...';
    
    // Remove loading state after 10 seconds (fallback)
    setTimeout(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    }, 10000);
}

function addFormValidation() {
    const inputs = document.querySelectorAll('input[required], select[required], textarea[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    
    // Remove existing error states
    field.classList.remove('is-invalid');
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) existingError.remove();
    
    // Validate based on field type
    let isValid = true;
    let errorMessage = '';
    
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    } else if (field.type === 'email' && value && !isValidEmail(value)) {
        isValid = false;
        errorMessage = 'Please enter a valid email address';
    } else if (field.type === 'tel' && value && !isValidPhone(value)) {
        isValid = false;
        errorMessage = 'Please enter a valid phone number';
    }
    
    if (!isValid) {
        field.classList.add('is-invalid');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = errorMessage;
        field.parentNode.appendChild(errorDiv);
    }
}

function clearFieldError(e) {
    const field = e.target;
    field.classList.remove('is-invalid');
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) existingError.remove();
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidPhone(phone) {
    return /^[\+]?[1-9][\d]{0,15}$/.test(phone.replace(/[\s\-\(\)]/g, ''));
}

function initializeAutoSave() {
    const longForms = document.querySelectorAll('form[data-autosave]');
    longForms.forEach(form => {
        const formId = form.id || 'form_' + Date.now();
        
        // Load saved data
        loadFormData(form, formId);
        
        // Save data on input
        form.addEventListener('input', debounce(() => {
            saveFormData(form, formId);
        }, 1000));
    });
}

function saveFormData(form, formId) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    localStorage.setItem(`autosave_${formId}`, JSON.stringify(data));
}

function loadFormData(form, formId) {
    const savedData = localStorage.getItem(`autosave_${formId}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) field.value = data[key];
        });
    }
}

// ============================================================================
// CHART INITIALIZATION
// ============================================================================
function initializeCharts() {
    // Initialize charts if Chart.js is available
    if (typeof Chart !== 'undefined') {
        initializeDashboardCharts();
    }
    console.log('✅ Charts initialized');
}

function initializeDashboardCharts() {
    // Sales Chart
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        new Chart(salesCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Daily Sales',
                    data: [1200, 1450, 1800, 1650, 2100, 2400, 1950],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return ' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    // Device Status Chart
    const deviceCtx = document.getElementById('deviceStatusChart');
    if (deviceCtx) {
        new Chart(deviceCtx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline', 'Maintenance'],
                datasets: [{
                    data: [8, 2, 1],
                    backgroundColor: [
                        '#10b981',
                        '#ef4444',
                        '#f59e0b'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

function formatDate(dateString) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(dateString));
}

// ============================================================================
// DEVICE MANAGEMENT FUNCTIONS
// ============================================================================
function restartDevice(deviceId) {
    if (confirm(`Restart device ${deviceId}? This may interrupt active sessions.`)) {
        fetch('/api/admin/device-command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_id: deviceId, command: 'restart'})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Restart command sent to ${deviceId}`, 'success');
                // Update device status after 3 seconds
                setTimeout(() => updateDeviceStatus(deviceId, 'restarting'), 1000);
            } else {
                showNotification(`Failed to restart ${deviceId}`, 'error');
            }
        })
        .catch(error => {
            showNotification('Error sending restart command', 'error');
        });
    }
}

function wakeDevice(deviceId) {
    fetch('/api/admin/device-command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({device_id: deviceId, command: 'wake'})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Wake command sent to ${deviceId}`, 'success');
            setTimeout(() => updateDeviceStatus(deviceId, 'waking'), 1000);
        } else {
            showNotification(`Failed to wake ${deviceId}`, 'error');
        }
    })
    .catch(error => {
        showNotification('Error sending wake command', 'error');
    });
}

function updateDeviceStatus(deviceId, status) {
    const deviceCard = document.querySelector(`[data-device-id="${deviceId}"]`);
    if (deviceCard) {
        const statusBadge = deviceCard.querySelector('.device-status');
        if (statusBadge) {
            statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusBadge.className = `badge bg-warning device-status`;
        }
    }
}

// ============================================================================
// RFID MANAGEMENT FUNCTIONS
// ============================================================================
function simulateRfidScan() {
    const scanButton = document.getElementById('scanButton') || event.target;
    const originalText = scanButton.innerHTML;
    
    // Show scanning state
    scanButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Scanning...';
    scanButton.disabled = true;
    
    fetch('/api/simulate-rfid-scan')
        .then(response => response.json())
        .then(data => {
            // Update UI with scanned card
            const rfidDisplay = document.getElementById('scannedRfidUid');
            if (rfidDisplay) {
                rfidDisplay.textContent = data.rfid_uid;
                
                // Show scanned card section
                const scannedSection = document.getElementById('scannedCardDisplay');
                if (scannedSection) {
                    scannedSection.style.display = 'block';
                    scannedSection.classList.add('fade-in');
                }
                
                // Update assignment form
                const assignRfidInput = document.getElementById('assignRfidUid');
                if (assignRfidInput) assignRfidInput.value = data.rfid_uid;
                
                const displayRfidInput = document.getElementById('displayRfidUid');
                if (displayRfidInput) displayRfidInput.value = data.rfid_uid;
                
                // Show assignment section
                const assignmentSection = document.getElementById('assignmentSection');
                if (assignmentSection) {
                    assignmentSection.style.display = 'block';
                    assignmentSection.classList.add('slide-up');
                }
            }
            
            showNotification('RFID card scanned successfully!', 'success');
        })
        .catch(error => {
            console.error('RFID scan error:', error);
            showNotification('Error scanning RFID card', 'error');
        })
        .finally(() => {
            scanButton.innerHTML = originalText;
            scanButton.disabled = false;
        });
}

function assignRfidToCustomer() {
    const customerId = document.getElementById('customerSelect')?.value;
    const rfidUid = document.getElementById('assignRfidUid')?.value;
    
    if (!customerId) {
        showNotification('Please select a customer', 'error');
        return;
    }
    
    if (!rfidUid) {
        showNotification('No RFID card scanned', 'error');
        return;
    }
    
    const customerName = document.getElementById('customerSelect')?.selectedOptions[0]?.text;
    
    if (confirm(`Assign RFID card ${rfidUid} to ${customerName}?`)) {
        fetch('/api/admin/assign-rfid', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({customer_id: customerId, rfid_uid: rfidUid})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`RFID card successfully assigned to ${customerName}!`, 'success');
                
                // Reset form
                resetRfidAssignment();
                
                // Refresh page after delay
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification(data.message || 'Failed to assign RFID card', 'error');
            }
        })
        .catch(error => {
            console.error('Assignment error:', error);
            showNotification('Error assigning RFID card', 'error');
        });
    }
}

function resetRfidAssignment() {
    // Hide sections
    const scannedSection = document.getElementById('scannedCardDisplay');
    if (scannedSection) scannedSection.style.display = 'none';
    
    const assignmentSection = document.getElementById('assignmentSection');
    if (assignmentSection) assignmentSection.style.display = 'none';
    
    // Clear form
    const customerSelect = document.getElementById('customerSelect');
    if (customerSelect) customerSelect.value = '';
    
    const customerPreview = document.getElementById('customerPreview');
    if (customerPreview) customerPreview.style.display = 'none';
}

// ============================================================================
// EXPORT GLOBAL FUNCTIONS
// ============================================================================
window.showNotification = showNotification;
window.restartDevice = restartDevice;
window.wakeDevice = wakeDevice;
window.simulateRfidScan = simulateRfidScan;
window.assignRfidToCustomer = assignRfidToCustomer;
window.resetRfidAssignment = resetRfidAssignment;

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .loading-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid #f3f4f6;
        border-radius: 50%;
        border-top-color: currentColor;
        animation: spin 1s ease-in-out infinite;
    }
`;
document.head.appendChild(style);

console.log('✅ Admin Dashboard JavaScript fully loaded');