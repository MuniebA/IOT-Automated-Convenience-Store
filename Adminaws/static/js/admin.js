// Admin Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tooltips if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Real-time updates simulation
    simulateRealTimeUpdates();
    
    // RFID Card Registration
    initializeCardRegistration();
});

function simulateRealTimeUpdates() {
    // Update stats every 30 seconds (in production, use WebSockets)
    setInterval(function() {
        updateDashboardStats();
    }, 30000);
}

function updateDashboardStats() {
    // Simulate real-time stat updates
    const activeSessionsElement = document.getElementById('activeSessions');
    if (activeSessionsElement) {
        const currentValue = parseInt(activeSessionsElement.textContent);
        const newValue = currentValue + Math.floor(Math.random() * 3) - 1;
        activeSessionsElement.textContent = Math.max(0, newValue);
    }
}

function initializeCardRegistration() {
    const registerForm = document.getElementById('registerCardForm');
    const simulateBtn = document.getElementById('simulateRfidScan');
    const rfidDisplay = document.getElementById('rfidUidDisplay');
    
    if (simulateBtn) {
        simulateBtn.addEventListener('click', function() {
            // Show loading state
            this.innerHTML = '<span class="loading"></span> Scanning...';
            this.disabled = true;
            
            // Simulate RFID scan
            fetch('/api/simulate-rfid-scan')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('rfidUid').value = data.rfid_uid;
                    if (rfidDisplay) {
                        rfidDisplay.textContent = data.rfid_uid;
                        rfidDisplay.parentElement.style.display = 'block';
                    }
                    showNotification('RFID card scanned successfully!', 'success');
                })
                .catch(error => {
                    showNotification('Error scanning RFID card', 'error');
                })
                .finally(() => {
                    this.innerHTML = '📡 Simulate RFID Scan';
                    this.disabled = false;
                });
        });
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                name: formData.get('name'),
                type: formData.get('type'),
                email: formData.get('email'),
                phone: formData.get('phone'),
                rfid_uid: formData.get('rfid_uid')
            };
            
            fetch('/api/register-card', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showNotification('Card registered successfully!', 'success');
                    this.reset();
                    if (rfidDisplay) {
                        rfidDisplay.parentElement.style.display = 'none';
                    }
                } else {
                    showNotification(result.message, 'error');
                }
            })
            .catch(error => {
                showNotification('Error registering card', 'error');
            });
        });
    }
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'error'} alert-custom`;
    notification.innerHTML = `
        <strong>${type === 'success' ? 'Success!' : 'Error!'}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.main-content');
    container.insertBefore(notification, container.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Chart initialization (will be called from templates)
function initializeDashboardCharts(salesData, fraudData) {
    // Sales Chart
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        new Chart(salesCtx, {
            type: 'line',
            data: {
                labels: salesData.map(item => new Date(item.date).toLocaleDateString()),
                datasets: [{
                    label: 'Daily Sales',
                    data: salesData.map(item => item.sales),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Fraud Events Chart
    const fraudCtx = document.getElementById('fraudChart');
    if (fraudCtx) {
        new Chart(fraudCtx, {
            type: 'doughnut',
            data: {
                labels: fraudData.map(item => item.type.replace('_', ' ').toUpperCase()),
                datasets: [{
                    data: fraudData.map(item => item.count),
                    backgroundColor: [
                        '#ef4444',
                        '#f59e0b',
                        '#10b981',
                        '#3b82f6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}