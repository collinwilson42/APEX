/**
 * IMPORT/EXPORT FUNCTIONALITY
 * Add these functions to your database.js file
 * Connects HTML buttons to Flask API endpoints
 */

// ============================================================================
// IMPORT FUNCTIONALITY
// ============================================================================

/**
 * Initialize import buttons for all tables
 * Call this in your DOMContentLoaded event
 */
function initializeImportButtons() {
    // Get all import buttons
    const importButtons = document.querySelectorAll('.icon-btn[title="Import Data"]');
    
    importButtons.forEach((button, index) => {
        button.addEventListener('click', function() {
            handleImportClick(index);
        });
    });
}

/**
 * Handle import button click
 * @param {number} tableIndex - Index of the table (0=core, 1=basic, 2=fib, 3=ath, 4=advanced)
 */
function handleImportClick(tableIndex) {
    const tableName = getTableName(tableIndex);
    
    // Show confirmation dialog
    const confirmed = confirm(
        `Import historical data for ${tableName}?\n\n` +
        `This will download 50,000 bars for both 1m and 15m timeframes.\n` +
        `Process may take several minutes.`
    );
    
    if (!confirmed) return;
    
    // Show loading notification
    showNotification('Starting import...', 'info');
    
    // Trigger import
    fetch('/api/import/trigger', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            bars_1m: 50000,
            bars_15m: 50000
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(
                `Import started! ${data.bars_1m.toLocaleString()} bars (1m), ${data.bars_15m.toLocaleString()} bars (15m)`,
                'success'
            );
            
            // Start polling import status
            pollImportStatus();
        } else {
            showNotification(`Import failed: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Import error:', error);
        showNotification(`Import error: ${error.message}`, 'error');
    });
}

/**
 * Poll import status every 5 seconds
 */
function pollImportStatus() {
    const interval = setInterval(() => {
        fetch('/api/import/status')
            .then(response => response.json())
            .then(data => {
                if (!data.import_running) {
                    clearInterval(interval);
                    showNotification('Import complete!', 'success');
                    
                    // Refresh data display
                    refreshAllData();
                }
            })
            .catch(error => {
                console.error('Status check error:', error);
                clearInterval(interval);
            });
    }, 5000); // Check every 5 seconds
}


// ============================================================================
// EXPORT FUNCTIONALITY
// ============================================================================

/**
 * Initialize export buttons for all tables
 * Call this in your DOMContentLoaded event
 */
function initializeExportButtons() {
    // Get all export buttons
    const exportButtons = document.querySelectorAll('.icon-btn[title="Export Data"]');
    
    exportButtons.forEach((button, index) => {
        button.addEventListener('click', function() {
            handleExportClick(index);
        });
    });
}

/**
 * Handle export button click
 * @param {number} tableIndex - Index of the table (0=core, 1=basic, 2=fib, 3=ath, 4=advanced)
 */
function handleExportClick(tableIndex) {
    const tableName = getTableName(tableIndex);
    const endpoint = getExportEndpoint(tableIndex);
    const currentTimeframe = getCurrentTimeframe(); // Your existing function
    
    // Show loading notification
    showNotification(`Exporting ${tableName} data...`, 'info');
    
    // Trigger download
    const url = `${endpoint}?timeframe=${currentTimeframe}`;
    
    // Create invisible anchor to trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = ''; // Filename is set by server
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success notification after short delay
    setTimeout(() => {
        showNotification(`${tableName} export started!`, 'success');
    }, 500);
}


// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get table name from index
 * @param {number} index - Table index
 * @returns {string} Table name
 */
function getTableName(index) {
    const names = [
        'Core Market Data',
        'Basic Indicators',
        'Fibonacci Data',
        'ATH Tracking',
        'Advanced Indicators'
    ];
    return names[index] || 'Unknown';
}

/**
 * Get export endpoint from table index
 * @param {number} index - Table index
 * @returns {string} API endpoint path
 */
function getExportEndpoint(index) {
    const endpoints = [
        '/api/export/core',
        '/api/export/basic',
        '/api/export/fibonacci',
        '/api/export/ath',
        '/api/export/all' // For advanced or complete export
    ];
    return endpoints[index] || '/api/export/all';
}

/**
 * Get current timeframe from UI
 * @returns {string} Current timeframe ('1m' or '15m')
 */
function getCurrentTimeframe() {
    // Check which timeframe button is active
    const activeButton = document.querySelector('.tf-btn.active');
    return activeButton ? activeButton.dataset.timeframe : '15m';
}

/**
 * Refresh all data displays after import
 */
function refreshAllData() {
    // Call your existing data refresh functions
    if (typeof loadCoreData === 'function') loadCoreData();
    if (typeof loadBasicData === 'function') loadBasicData();
    if (typeof loadFibonacciData === 'function') loadFibonacciData();
    if (typeof loadATHData === 'function') loadATHData();
    if (typeof loadAdvancedData === 'function') loadAdvancedData();
    
    console.log('[IMPORT/EXPORT] Data refreshed after import');
}


// ============================================================================
// NOTIFICATION SYSTEM (if not already exists)
// ============================================================================

/**
 * Show notification toast
 * @param {string} message - Notification message
 * @param {string} type - Type: 'info', 'success', 'error'
 */
function showNotification(message, type = 'info') {
    // Check if notification system already exists
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
        return;
    }
    
    // Create simple notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'success' ? '#2D5016' : type === 'error' ? '#8B0000' : '#283353'};
        color: ${type === 'success' ? '#90EE90' : type === 'error' ? '#FF6B6B' : '#F2F3F4'};
        padding: 12px 20px;
        border-radius: 6px;
        border: 1px solid ${type === 'success' ? '#90EE90' : type === 'error' ? '#FF6B6B' : '#C4B157'};
        z-index: 10000;
        animation: slideIn 0.3s ease;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}


// ============================================================================
// INITIALIZATION
// ============================================================================

// Add to your existing DOMContentLoaded event:
document.addEventListener('DOMContentLoaded', function() {
    // ... your existing initialization code ...
    
    // Initialize import/export buttons
    initializeImportButtons();
    initializeExportButtons();
    
    console.log('[IMPORT/EXPORT] Buttons initialized');
});


// ============================================================================
// EXPORT ALL (BONUS FEATURE)
// ============================================================================

/**
 * Export all data as complete JSON dump
 * Can add a dedicated button for this or use keyboard shortcut
 */
function exportAllData() {
    const currentTimeframe = getCurrentTimeframe();
    
    showNotification('Exporting complete database...', 'info');
    
    const link = document.createElement('a');
    link.href = `/api/export/all?timeframe=${currentTimeframe}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => {
        showNotification('Complete export started!', 'success');
    }, 500);
}

// Optional: Add keyboard shortcut (Ctrl+Shift+E) for complete export
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'E') {
        e.preventDefault();
        exportAllData();
    }
});


console.log('[IMPORT/EXPORT] Module loaded successfully');
