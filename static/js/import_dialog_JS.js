// ============================================================================
// IMPORT DATA SYSTEM - JAVASCRIPT (V1.1)
// Add to database.js or create import_manager.js
// ============================================================================

// Import System State
const importSystem = {
    isImporting: false,
    pollInterval: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

function initImportSystem() {
    console.log('[IMPORT SYSTEM] Initializing...');
    
    // Import button click
    const importBtn = document.getElementById('importDataBtn');
    if (importBtn) {
        importBtn.addEventListener('click', openImportModal);
    }
    
    // Modal close buttons
    const modalClose = document.getElementById('importModalClose');
    const modalOverlay = document.getElementById('importModalOverlay');
    const cancelBtn = document.getElementById('importBtnCancel');
    
    if (modalClose) modalClose.addEventListener('click', closeImportModal);
    if (modalOverlay) modalOverlay.addEventListener('click', closeImportModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeImportModal);
    
    // Start import button
    const startBtn = document.getElementById('importBtnStart');
    if (startBtn) {
        startBtn.addEventListener('click', startImport);
    }
    
    console.log('[IMPORT SYSTEM] Ready');
}

// ============================================================================
// MODAL CONTROLS
// ============================================================================

function openImportModal() {
    const modal = document.getElementById('importModal');
    if (modal) {
        modal.style.display = 'flex';
        // Reset form
        document.getElementById('importBarCount').value = 50000;
        document.getElementById('import1m').checked = true;
        document.getElementById('import15m').checked = true;
        document.getElementById('importClearData').checked = false;
        hideProgress();
    }
}

function closeImportModal() {
    const modal = document.getElementById('importModal');
    if (modal && !importSystem.isImporting) {
        modal.style.display = 'none';
    }
}

// ============================================================================
// IMPORT EXECUTION
// ============================================================================

async function startImport() {
    // Get form values
    const barCount = parseInt(document.getElementById('importBarCount').value);
    const import1m = document.getElementById('import1m').checked;
    const import15m = document.getElementById('import15m').checked;
    const clearData = document.getElementById('importClearData').checked;
    
    // Validation
    if (!import1m && !import15m) {
        showNotification('Please select at least one timeframe', 'error');
        return;
    }
    
    if (barCount < 1000 || barCount > 100000) {
        showNotification('Bar count must be between 1,000 and 100,000', 'error');
        return;
    }
    
    // Confirmation for clear data
    if (clearData) {
        const confirmed = confirm(
            '⚠️ WARNING: This will delete ALL existing data.\n\n' +
            'This action cannot be undone.\n\n' +
            'Are you sure you want to continue?'
        );
        if (!confirmed) return;
    }
    
    // Disable buttons
    document.getElementById('importBtnStart').disabled = true;
    document.getElementById('importBtnCancel').disabled = true;
    importSystem.isImporting = true;
    
    // Show progress
    showProgress('Preparing import...');
    
    try {
        // Call Flask API to start import
        const response = await fetch('/api/import/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                bars: barCount,
                timeframes: {
                    '1m': import1m,
                    '15m': import15m
                },
                clear_existing: clearData
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Import started successfully', 'success');
            updateProgress(5, 'Connecting to MT5...');
            
            // Start polling for progress
            startProgressPolling();
        } else {
            throw new Error(data.error || 'Failed to start import');
        }
        
    } catch (error) {
        console.error('[IMPORT SYSTEM] Error:', error);
        showNotification(`Import failed: ${error.message}`, 'error');
        resetImportUI();
    }
}

// ============================================================================
// PROGRESS TRACKING
// ============================================================================

function showProgress(message) {
    const progressDiv = document.getElementById('importProgress');
    if (progressDiv) {
        progressDiv.style.display = 'block';
        updateProgress(0, message);
    }
}

function hideProgress() {
    const progressDiv = document.getElementById('importProgress');
    if (progressDiv) {
        progressDiv.style.display = 'none';
    }
}

function updateProgress(percent, message) {
    const fill = document.getElementById('importProgressFill');
    const text = document.getElementById('importProgressText');
    
    if (fill) {
        fill.style.width = `${percent}%`;
        if (percent > 10) {
            fill.textContent = `${percent}%`;
        }
    }
    
    if (text) {
        text.textContent = message;
    }
}

// ============================================================================
// PROGRESS POLLING
// ============================================================================

function startProgressPolling() {
    // Poll every 2 seconds
    importSystem.pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/import/status');
            const data = await response.json();
            
            if (data.importing) {
                // Update progress
                const percent = Math.round(data.progress || 0);
                const message = data.message || 'Importing data...';
                updateProgress(percent, message);
                
            } else if (data.complete) {
                // Import finished
                updateProgress(100, 'Import complete!');
                clearInterval(importSystem.pollInterval);
                
                setTimeout(() => {
                    closeImportModal();
                    resetImportUI();
                    showNotification(
                        `Successfully imported ${data.total_bars || 0} bars across ${data.timeframes || 0} timeframe(s)`,
                        'success'
                    );
                    
                    // Reload data tables
                    if (typeof loadAllData === 'function') {
                        loadAllData();
                    }
                }, 2000);
                
            } else if (data.error) {
                // Import error
                clearInterval(importSystem.pollInterval);
                showNotification(`Import error: ${data.error}`, 'error');
                resetImportUI();
            }
            
        } catch (error) {
            console.error('[IMPORT SYSTEM] Polling error:', error);
            clearInterval(importSystem.pollInterval);
            resetImportUI();
        }
    }, 2000);
}

function resetImportUI() {
    importSystem.isImporting = false;
    document.getElementById('importBtnStart').disabled = false;
    document.getElementById('importBtnCancel').disabled = false;
    hideProgress();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showNotification(message, type = 'info') {
    // Use existing notification system or create simple alert
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // If you have a notification div in your HTML:
    // const notif = document.getElementById('notification');
    // notif.textContent = message;
    // notif.className = `notification notification-${type}`;
    // notif.style.display = 'block';
    // setTimeout(() => { notif.style.display = 'none'; }, 5000);
}

// ============================================================================
// INITIALIZE ON PAGE LOAD
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initImportSystem();
});

// ============================================================================
// END OF IMPORT SYSTEM
// ============================================================================
