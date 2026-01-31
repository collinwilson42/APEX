/* ============================================================================
   MASTER DATA CONTROLS - JavaScript Functionality
   Add this to settings.js
   ============================================================================ */

// Master Import Button
document.getElementById('masterImportBtn')?.addEventListener('click', async function() {
    const bars = parseInt(document.getElementById('master_import_bars').value);
    const statusEl = document.getElementById('importStatus');
    const btn = this;
    
    // Validation
    if (!bars || bars < 100 || bars > 10000) {
        statusEl.textContent = 'Invalid bar count (100-10000)';
        statusEl.className = 'status-text error';
        return;
    }
    
    // Confirm
    const confirmed = confirm(`Import ${bars} bars of historical data into ALL tables?\n\nThis will:\n- Load Core Market Data\n- Load Basic Indicators\n- Load Fibonacci Data\n- Load ATH Tracking\n\nContinue?`);
    
    if (!confirmed) return;
    
    // Start loading
    btn.classList.add('loading');
    btn.disabled = true;
    statusEl.textContent = 'Importing data from MT5...';
    statusEl.className = 'status-text loading';
    
    try {
        const response = await fetch('/api/master-import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bars: bars })
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusEl.textContent = `✓ Imported ${data.total_records || bars} records successfully`;
            statusEl.className = 'status-text success';
            
            // Show detailed breakdown if available
            if (data.breakdown) {
                setTimeout(() => {
                    statusEl.textContent = `Core: ${data.breakdown.core}, Indicators: ${data.breakdown.basic}, Fib: ${data.breakdown.fibonacci}, ATH: ${data.breakdown.ath}`;
                }, 2000);
            }
        } else {
            throw new Error(data.error || 'Import failed');
        }
        
    } catch (error) {
        console.error('Import error:', error);
        statusEl.textContent = `✗ Error: ${error.message}`;
        statusEl.className = 'status-text error';
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
});

// Master Clear Button
document.getElementById('masterClearBtn')?.addEventListener('click', async function() {
    const statusEl = document.getElementById('clearStatus');
    const btn = this;
    
    // Double confirm (this is dangerous!)
    const confirmed1 = confirm('⚠️ WARNING ⚠️\n\nYou are about to DELETE ALL DATA from ALL database tables.\n\nThis includes:\n- Core Market Data\n- Basic Indicators\n- Fibonacci Data\n- ATH Tracking\n- Price Spike Data\n\nThis CANNOT be undone!\n\nAre you sure?');
    
    if (!confirmed1) return;
    
    // Second confirmation
    const confirmed2 = confirm('FINAL WARNING!\n\nAll historical data will be permanently deleted.\n\nType YES in your mind and click OK to confirm.');
    
    if (!confirmed2) return;
    
    // Start clearing
    btn.classList.add('loading');
    btn.disabled = true;
    statusEl.textContent = 'Clearing all data...';
    statusEl.className = 'status-text loading';
    
    try {
        const response = await fetch('/api/master-clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusEl.textContent = `✓ Cleared ${data.total_deleted || 0} records from all tables`;
            statusEl.className = 'status-text success';
            
            // Show breakdown
            if (data.breakdown) {
                setTimeout(() => {
                    statusEl.textContent = `Deleted - Core: ${data.breakdown.core}, Basic: ${data.breakdown.basic}, Fib: ${data.breakdown.fibonacci}, ATH: ${data.breakdown.ath}`;
                }, 2000);
            }
        } else {
            throw new Error(data.error || 'Clear failed');
        }
        
    } catch (error) {
        console.error('Clear error:', error);
        statusEl.textContent = `✗ Error: ${error.message}`;
        statusEl.className = 'status-text error';
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
});

// Section collapse for Master Data Controls
document.querySelector('[data-section="master-data"]')?.addEventListener('click', function() {
    const section = document.getElementById('master-data-controls');
    const extendo = this.querySelector('.section-extendo');
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        extendo.dataset.state = 'up';
        extendo.style.transform = 'rotate(0deg)';
    } else {
        section.style.display = 'none';
        extendo.dataset.state = 'down';
        extendo.style.transform = 'rotate(180deg)';
    }
});
