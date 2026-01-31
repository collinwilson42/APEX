/**
 * MT5 META AGENT V11 - INTELLIGENCE DATABASE JAVASCRIPT
 * V11.2 - EPIC 540° Spin Animation + Bug Fixes
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    refreshInterval: 10000,  // 10 seconds
    currentTimeframe: '15m',
    autoRefresh: false
};

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let sectionStates = {
    core: 'partial',
    basic: 'partial',
    fibonacci: 'partial',
    ath: 'partial'
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[DATABASE] Initializing Intelligence Database interface...');
    
    // Initialize UI
    initializeUI();
    
    // Initialize import/export buttons
    initializeImportButtons();
    initializeExportButtons();
    
    // Load initial data
    loadAllData();
    
    // Start auto-refresh if enabled
    if (CONFIG.autoRefresh) {
        setInterval(loadAllData, CONFIG.refreshInterval);
    }
    
    console.log('[DATABASE] Initialization complete');
});

// ============================================================================
// UI INITIALIZATION
// ============================================================================

function initializeUI() {
    // Timeframe toggle
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            CONFIG.currentTimeframe = this.dataset.timeframe;
            loadAllData();
        });
    });
    
    // FIX #1: Settings icon click handler
    document.querySelectorAll('img[src*="settings.png"]').forEach(icon => {
        icon.style.cursor = 'pointer';
        icon.addEventListener('click', function(e) {
            e.stopPropagation();
            window.location.href = '/settings';
        });
    });
    
    // FIX #2: Master expand with EPIC 540° SPIN ANIMATION
    const masterExpand = document.getElementById('masterExpand');
    if (masterExpand) {
        masterExpand.addEventListener('click', function() {
            handleMasterExpand();
            performEpicSpin(this.querySelector('.main-extendo'));
        });
    }
    
    // Section expand buttons
    document.querySelectorAll('.section-expand-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const section = this.dataset.section;
            toggleSection(section);
            updateMainExtendoDirection();
        });
    });
    
    // Menu toggle
    const menuToggle = document.getElementById('menuToggle');
    const dropdownMenu = document.getElementById('dropdownMenu');
    if (menuToggle && dropdownMenu) {
        menuToggle.addEventListener('click', function() {
            dropdownMenu.classList.toggle('show');
        });
    }
}

// ============================================================================
// 🎪✨ THE EPIC 540° SPIN ANIMATION ✨🎪
// ============================================================================

function performEpicSpin(element) {
    if (!element || element.classList.contains('spinning')) return;
    
    element.classList.add('spinning');
    element.style.transition = 'transform 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55), scale 0.4s ease';
    
    // Get current rotation
    const currentRotation = element.style.transform.match(/rotate\(([^)]+)\)/);
    const currentDeg = currentRotation ? parseFloat(currentRotation[1]) : 0;
    
    // Determine target (down if any section open, up if all closed)
    const anyOpen = Object.values(sectionStates).some(state => state !== 'collapsed');
    const targetRotation = anyOpen ? 180 : 0;
    
    // Calculate 540° spin to target
    const spinDegrees = currentDeg + 540 + (targetRotation - (currentDeg % 360));
    
    // Start spin
    element.style.transform = `rotate(${spinDegrees}deg)`;
    
    // Shrink to 30% at start
    setTimeout(() => element.style.scale = '0.3', 0);
    
    // Expand back to 100% at midpoint (400ms)
    setTimeout(() => element.style.scale = '1.0', 400);
    
    // Cleanup after animation
    setTimeout(() => {
        element.classList.remove('spinning');
        element.style.transition = 'none';
        element.style.transform = `rotate(${targetRotation}deg)`;
        setTimeout(() => {
            element.style.transition = 'transform 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55), scale 0.4s ease';
        }, 50);
    }, 800);
}

// ============================================================================
// MAIN EXTENDO DIRECTION UPDATE
// ============================================================================

function updateMainExtendoDirection() {
    const mainExtendo = document.querySelector('.main-extendo');
    if (!mainExtendo) return;
    
    // Check if ANY section is open (not collapsed)
    const anyOpen = Object.values(sectionStates).some(state => state !== 'collapsed');
    
    // Point down (180deg) if any section is open, up (0deg) if all collapsed
    const targetRotation = anyOpen ? 180 : 0;
    
    // Get current rotation
    const currentTransform = mainExtendo.style.transform || 'rotate(0deg)';
    const currentRotation = parseFloat(currentTransform.match(/rotate\(([^)]+)\)/)?.[1] || 0);
    
    // Normalize to 0-360
    const normalizedCurrent = ((currentRotation % 360) + 360) % 360;
    
    // Only update if different
    if (Math.abs(normalizedCurrent - targetRotation) > 5) {
        mainExtendo.style.transform = `rotate(${targetRotation}deg)`;
    }
}

// ============================================================================
// MASTER EXPAND/COLLAPSE
// ============================================================================

function handleMasterExpand() {
    const allPartial = Object.values(sectionStates).every(state => state === 'partial');
    const allCollapsed = Object.values(sectionStates).every(state => state === 'collapsed');
    
    if (allPartial || allCollapsed) {
        // Expand all to full
        Object.keys(sectionStates).forEach(section => {
            setSectionState(section, 'expanded');
        });
    } else {
        // Collapse all
        Object.keys(sectionStates).forEach(section => {
            setSectionState(section, 'partial');
        });
    }
    
    updateMasterExpandIcon();
}

function updateMasterExpandIcon() {
    const masterGif = document.getElementById('masterExpandGif');
    if (!masterGif) return;
    
    const anyOpen = Object.values(sectionStates).some(state => state !== 'collapsed');
    masterGif.setAttribute('data-state', anyOpen ? 'up' : 'down');
}

// ============================================================================
// SECTION EXPAND/COLLAPSE
// ============================================================================

function toggleSection(sectionName) {
    const currentState = sectionStates[sectionName];
    
    if (currentState === 'partial') {
        setSectionState(sectionName, 'collapsed');
    } else if (currentState === 'collapsed') {
        setSectionState(sectionName, 'partial');
    } else {
        setSectionState(sectionName, 'collapsed');
    }
    
    updateMasterExpandIcon();
}

function setSectionState(sectionName, state) {
    sectionStates[sectionName] = state;
    
    const body = document.getElementById(`${sectionName}Body`);
    const icon = document.querySelector(`[data-section="${sectionName}"] .section-extendo`);
    
    if (!body) return;
    
    // Update body classes
    body.classList.remove('collapsed', 'partial', 'expanded');
    body.classList.add(state);
    
    // Update icon rotation
    if (icon) {
        icon.setAttribute('data-state', state === 'collapsed' ? 'down' : 'up');
    }
}

// ============================================================================
// DATA FETCHING
// ============================================================================

async function loadAllData() {
    console.log(`[DATABASE] Loading data for timeframe: ${CONFIG.currentTimeframe}`);
    
    try {
        await Promise.all([
            loadCoreData(),
            loadBasicData(),
            loadFibonacciData(),
            loadATHData(),
            loadStats()
        ]);
        
        updateLastUpdateTime();
    } catch (error) {
        console.error('[DATABASE] Error loading data:', error);
    }
}

async function loadCoreData() {
    try {
        const response = await fetch(`/api/core?timeframe=${CONFIG.currentTimeframe}&limit=10`);
        const data = await response.json();
        
        if (data.success) {
            updateCoreTable(data.data);
            if (data.data.length > 0) {
                document.getElementById('corePrice').textContent = data.data[0].close.toFixed(2);
            }
        }
    } catch (error) {
        console.error('[DATABASE] Error loading core data:', error);
        document.getElementById('coreTableBody').innerHTML = '<tr><td colspan="7" class="no-data">Error loading data</td></tr>';
    }
}

async function loadBasicData() {
    try {
        const response = await fetch(`/api/basic?timeframe=${CONFIG.currentTimeframe}&limit=10`);
        const data = await response.json();
        
        if (data.success) {
            updateBasicTable(data.data);
            if (data.data.length > 0) {
                document.getElementById('basicPrice').textContent = data.data[0].ema_short.toFixed(2);
            }
        }
    } catch (error) {
        console.error('[DATABASE] Error loading basic data:', error);
        document.getElementById('basicTableBody').innerHTML = '<tr><td colspan="8" class="no-data">Error loading data</td></tr>';
    }
}

async function loadFibonacciData() {
    try {
        const response = await fetch(`/api/fibonacci?timeframe=${CONFIG.currentTimeframe}&limit=10`);
        const data = await response.json();
        
        if (data.success) {
            updateFibonacciTable(data.data);
            if (data.data.length > 0) {
                const zone = data.data[0].current_fib_zone;
                const isGolden = data.data[0].in_golden_zone;
                const zoneText = isGolden ? `Zone ${zone} 🏆` : `Zone ${zone}`;
                document.getElementById('fibonacciZone').textContent = zoneText;
            }
        }
    } catch (error) {
        console.error('[DATABASE] Error loading fibonacci data:', error);
        document.getElementById('fibonacciTableBody').innerHTML = '<tr><td colspan="10" class="no-data">Error loading data</td></tr>';
    }
}

async function loadATHData() {
    try {
        const response = await fetch(`/api/ath?timeframe=${CONFIG.currentTimeframe}&limit=10`);
        const data = await response.json();
        
        if (data.success) {
            updateATHTable(data.data);
            if (data.data.length > 0) {
                const zone = data.data[0].ath_zone;
                const mult = data.data[0].ath_multiplier;
                const statusEmoji = getATHEmoji(zone);
                document.getElementById('athStatus').textContent = `${statusEmoji} ${mult.toFixed(1)}x`;
            }
        }
    } catch (error) {
        console.error('[DATABASE] Error loading ATH data:', error);
        document.getElementById('athTableBody').innerHTML = '<tr><td colspan="8" class="no-data">Error loading data</td></tr>';
    }
}

async function loadStats() {
    try {
        const response = await fetch(`/api/stats?timeframe=${CONFIG.currentTimeframe}`);
        const data = await response.json();
        
        if (data.success && data.stats) {
            document.getElementById('totalRecords').textContent = data.stats.total_records || 0;
            document.getElementById('collections').textContent = data.stats.successful_collections || 0;
            document.getElementById('errors').textContent = data.stats.failed_collections || 0;
            
            if (data.stats.last_collection) {
                document.getElementById('lastUpdate').textContent = formatTime(data.stats.last_collection);
            }
        }
    } catch (error) {
        console.error('[DATABASE] Error loading stats:', error);
    }
}

// ============================================================================
// TABLE UPDATES
// ============================================================================

function updateCoreTable(data) {
    const tbody = document.getElementById('coreTableBody');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => `
        <tr>
            <td>${formatTimestamp(row.timestamp)}</td>
            <td>${row.symbol}</td>
            <td>${row.open.toFixed(2)}</td>
            <td>${row.high.toFixed(2)}</td>
            <td>${row.low.toFixed(2)}</td>
            <td>${row.close.toFixed(2)}</td>
            <td>${row.volume}</td>
        </tr>
    `).join('');
}

function updateBasicTable(data) {
    const tbody = document.getElementById('basicTableBody');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => `
        <tr>
            <td>${formatTimestamp(row.timestamp)}</td>
            <td>${row.atr_14.toFixed(2)}</td>
            <td>${row.atr_50_avg.toFixed(2)}</td>
            <td>${row.atr_ratio.toFixed(3)}</td>
            <td>${row.ema_short.toFixed(2)}</td>
            <td>${row.ema_medium.toFixed(2)}</td>
            <td>${row.ema_distance.toFixed(2)}</td>
            <td>${row.supertrend}</td>
        </tr>
    `).join('');
}

function updateFibonacciTable(data) {
    const tbody = document.getElementById('fibonacciTableBody');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="no-data">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => {
        const goldenBadge = row.in_golden_zone ? '<span style="color: #C4B157;">🏆</span>' : '';
        const zoneClass = row.in_golden_zone ? 'golden-zone' : '';
        
        return `
        <tr class="${zoneClass}">
            <td>${formatTimestamp(row.timestamp)}</td>
            <td><strong>Zone ${row.current_fib_zone}</strong> ${goldenBadge}</td>
            <td>${row.in_golden_zone ? 'YES' : 'NO'}</td>
            <td><strong>${row.zone_multiplier.toFixed(1)}x</strong></td>
            <td>${row.pivot_high.toFixed(2)}</td>
            <td>${row.pivot_low.toFixed(2)}</td>
            <td>${row.fib_level_0382.toFixed(2)}</td>
            <td>${row.fib_level_0618.toFixed(2)}</td>
            <td>${row.fib_level_0786.toFixed(2)}</td>
            <td>${row.distance_to_next_level ? row.distance_to_next_level.toFixed(2) : 'N/A'}</td>
        </tr>
    `}).join('');
}

function updateATHTable(data) {
    const tbody = document.getElementById('athTableBody');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => {
        const zoneClass = getATHZoneClass(row.ath_zone);
        const statusEmoji = getATHEmoji(row.ath_zone);
        const percentileText = row.distance_from_ath_percentile ? 
            `${row.distance_from_ath_percentile.toFixed(0)}th` : 'N/A';
        
        return `
        <tr class="${zoneClass}">
            <td>${formatTimestamp(row.timestamp)}</td>
            <td>${row.current_ath.toFixed(2)}</td>
            <td>${row.current_close.toFixed(2)}</td>
            <td>${row.ath_distance_points.toFixed(2)}</td>
            <td><strong>${row.ath_distance_pct.toFixed(2)}%</strong></td>
            <td><strong>${row.ath_multiplier.toFixed(2)}x</strong></td>
            <td>${percentileText}</td>
            <td>${statusEmoji} <strong>${row.ath_zone.replace('_', ' ')}</strong></td>
        </tr>
    `}).join('');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', { 
            month: '2-digit', 
            day: '2-digit', 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    } catch (e) {
        return timestamp;
    }
}

function formatTime(timestamp) {
    if (!timestamp) return '--:--:--';
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false 
        });
    } catch (e) {
        return timestamp;
    }
}

function getATHEmoji(zone) {
    if (zone === 'NEAR_ATH') return '🟢';
    if (zone === 'MID_RANGE') return '🟡';
    if (zone === 'FAR_ATH') return '🔴';
    return '⚪';
}

function getATHZoneClass(zone) {
    if (zone === 'NEAR_ATH') return 'ath-near';
    if (zone === 'MID_RANGE') return 'ath-mid';
    if (zone === 'FAR_ATH') return 'ath-far';
    return '';
}

function updateLastUpdateTime() {
    const now = new Date();
    document.getElementById('footerUpdate').textContent = formatTime(now.toISOString());
}

// ============================================================================
// IMPORT/EXPORT FUNCTIONALITY
// ============================================================================

/**
 * Initialize import buttons for all tables
 */
function initializeImportButtons() {
    const importButtons = document.querySelectorAll('.icon-btn[title="Import Data"]');
    
    importButtons.forEach((button, index) => {
        button.addEventListener('click', function() {
            handleImportClick(index);
        });
    });
    
    console.log(`[IMPORT/EXPORT] Initialized ${importButtons.length} import buttons`);
}

/**
 * Initialize export buttons for all tables
 */
function initializeExportButtons() {
    const exportButtons = document.querySelectorAll('.icon-btn[title="Export Data"]');
    
    exportButtons.forEach((button, index) => {
        button.addEventListener('click', function() {
            handleExportClick(index);
        });
    });
    
    console.log(`[IMPORT/EXPORT] Initialized ${exportButtons.length} export buttons`);
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
        `Process may take several minutes.\n\n` +
        `Continue?`
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
        console.error('[IMPORT/EXPORT] Import error:', error);
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
                    showNotification('Import complete! Refreshing data...', 'success');
                    
                    // Refresh data display after short delay
                    setTimeout(() => {
                        loadAllData();
                    }, 1000);
                }
            })
            .catch(error => {
                console.error('[IMPORT/EXPORT] Status check error:', error);
                clearInterval(interval);
            });
    }, 5000); // Check every 5 seconds
}

/**
 * Handle export button click
 * @param {number} tableIndex - Index of the table (0=core, 1=basic, 2=fib, 3=ath, 4=advanced)
 */
function handleExportClick(tableIndex) {
    const tableName = getTableName(tableIndex);
    const endpoint = getExportEndpoint(tableIndex);
    const currentTimeframe = CONFIG.currentTimeframe;
    
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
        '/api/export/all'
    ];
    return endpoints[index] || '/api/export/all';
}

/**
 * Export all data as complete JSON dump
 * Bonus feature - keyboard shortcut: Ctrl+Shift+E
 */
function exportAllData() {
    const currentTimeframe = CONFIG.currentTimeframe;
    
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

// Keyboard shortcut for complete export
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'E') {
        e.preventDefault();
        exportAllData();
    }
});

// ============================================================================
// AUTO-REFRESH TOGGLE
// ============================================================================

function toggleAutoRefresh() {
    CONFIG.autoRefresh = !CONFIG.autoRefresh;
    
    if (CONFIG.autoRefresh) {
        console.log('[DATABASE] Auto-refresh enabled');
        setInterval(loadAllData, CONFIG.refreshInterval);
    } else {
        console.log('[DATABASE] Auto-refresh disabled');
    }
}

// ============================================================================
// EXPORT FUNCTIONS FOR CONSOLE DEBUGGING
// ============================================================================

window.DatabaseDebug = {
    loadAllData,
    loadCoreData,
    loadBasicData,
    loadFibonacciData,
    toggleAutoRefresh,
    currentConfig: () => CONFIG,
    epicSpin: () => {
        const extendo = document.querySelector('.main-extendo');
        if (extendo) performEpicSpin(extendo);
    }
};

console.log('[DATABASE] Debug functions available: window.DatabaseDebug');
console.log('[DATABASE] 🎪 Try: DatabaseDebug.epicSpin() for the EPIC SPIN!');
// ═══════════════════════════════════════════════════════════════════════════
// PROFILE CONTROL PANEL JavaScript
// ═══════════════════════════════════════════════════════════════════════════

(function() {
    const profileState = {
        currentProfile: null,
        isActive: false,
        settings: {},
        autoSaveTimeout: null
    };

    function initProfilePanel() {
        initProfileSearch();
        initProfileSliders();
        initPowerIcon();
        initProfileNav();
        initSLTPInputs();
    }

    function initProfileSearch() {
        const searchInput = document.getElementById('profileSearch');
        const searchResults = document.getElementById('profileSearchResults');
        
        if (!searchInput) return;
        
        searchInput.addEventListener('input', debounceProfile(function(e) {
            const query = e.target.value.trim();
            if (query.length >= 2) {
                console.log('Searching for:', query);
                // TODO: API call
            } else {
                searchResults.classList.remove('show');
            }
        }, 300));
    }

    function initProfileSliders() {
        const riskSlider = document.getElementById('riskRewardLevel');
        if (riskSlider) {
            const riskValue = riskSlider.nextElementSibling;
            riskSlider.addEventListener('input', function() {
                riskValue.textContent = this.value;
                triggerAutoSave();
            });
        }
        
        const drawdownSlider = document.getElementById('maxDrawdown');
        if (drawdownSlider) {
            const drawdownValue = drawdownSlider.nextElementSibling;
            drawdownSlider.addEventListener('input', function() {
                drawdownValue.textContent = this.value + '%';
                if (parseInt(this.value) > 10) {
                    drawdownValue.style.color = '#FF6B6B';
                } else {
                    drawdownValue.style.color = 'var(--gold)';
                }
                triggerAutoSave();
            });
        }
    }

    function initPowerIcon() {
        const powerIcon = document.getElementById('activateIcon');
        if (!powerIcon) return;
        
        powerIcon.addEventListener('click', function() {
            const isActive = powerIcon.classList.contains('active');
            if (!isActive) {
                powerIcon.classList.remove('inactive');
                powerIcon.classList.add('active');
                powerIcon.setAttribute('data-tooltip', 'Profile active');
                profileState.isActive = true;
                console.log('Profile activated');
            }
        });
    }

    function initProfileNav() {
        const prevBtn = document.getElementById('prevRankBtn');
        const nextBtn = document.getElementById('nextRankBtn');
        const newBtn = document.getElementById('newProfileBtn');
        const dupBtn = document.getElementById('duplicateProfileBtn');
        
        if (prevBtn) prevBtn.addEventListener('click', () => console.log('Previous rank'));
        if (nextBtn) nextBtn.addEventListener('click', () => console.log('Next rank'));
        if (newBtn) newBtn.addEventListener('click', () => console.log('New profile'));
        if (dupBtn) dupBtn.addEventListener('click', () => console.log('Duplicate profile'));
    }

    function initSLTPInputs() {
        const selects = document.querySelectorAll('.sl-tp-select');
        const inputs = document.querySelectorAll('.sl-tp-input');
        
        selects.forEach(select => select.addEventListener('change', triggerAutoSave));
        inputs.forEach(input => input.addEventListener('change', triggerAutoSave));
    }

    function triggerAutoSave() {
        if (profileState.autoSaveTimeout) {
            clearTimeout(profileState.autoSaveTimeout);
        }
        
        profileState.autoSaveTimeout = setTimeout(() => {
            console.log('Auto-saving profile...');
            // TODO: API call to save
        }, 2000);
    }

    function debounceProfile(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initProfilePanel);
    } else {
        initProfilePanel();
    }

    console.log('Profile Control Panel JS loaded ⚡');
})();

// ============================================================================
// API COMPLEX - UNIFIED DECISION ENGINE JAVASCRIPT V1.0
// Module management, configuration, and screenshot integration
// ============================================================================

// API Complex State
const apiComplexState = {
    modules: {
        1: { active: true, name: 'API #1 - FREQUENCY', config: {} },
        2: { active: false, name: null, config: {} },
        3: { active: false, name: null, config: {} },
        4: { active: false, name: null, config: {} }
    },
    currentConfigModule: null,
    decisionEngine: {
        direction: 'NEUTRAL',
        confidence: 0
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[API COMPLEX] Initializing...');
    
    initAPIComplex();
    initModuleSliders();
    
    console.log('[API COMPLEX] Ready');
});

function initAPIComplex() {
    // Module 1 sliders
    const freq1Slider = document.getElementById('frequency1Slider');
    const rr1Slider = document.getElementById('riskReward1Slider');
    
    if (freq1Slider) {
        freq1Slider.addEventListener('input', function() {
            document.getElementById('frequency1Display').textContent = this.value;
            document.getElementById('frequency1Value').textContent = this.value;
            updateDecisionEngine();
        });
    }
    
    if (rr1Slider) {
        rr1Slider.addEventListener('input', function() {
            document.getElementById('riskReward1Display').textContent = this.value;
            updateDecisionEngine();
        });
    }
    
    // Execute button
    const executeBtn = document.getElementById('apiExecuteBtn');
    if (executeBtn) {
        executeBtn.addEventListener('click', executeDecision);
    }
}

function initModuleSliders() {
    // Initialize all active module sliders
    document.querySelectorAll('.module-slider').forEach(slider => {
        slider.addEventListener('input', function() {
            const displayId = this.id.replace('Slider', 'Display');
            const valueId = this.id.replace('Slider', 'Value');
            
            document.getElementById(displayId).textContent = this.value;
            if (document.getElementById(valueId)) {
                document.getElementById(valueId).textContent = this.value;
            }
            
            updateDecisionEngine();
        });
    });
}

// ============================================================================
// MODULE MANAGEMENT
// ============================================================================

function addAPIModule(moduleNum) {
    console.log(`[API COMPLEX] Adding module ${moduleNum}`);
    
    apiComplexState.currentConfigModule = moduleNum;
    
    // Open configuration modal
    document.getElementById('apiConfigTitle').textContent = `CONFIGURE API MODULE #${moduleNum}`;
    document.getElementById('apiConfigName').value = '';
    document.getElementById('apiConfigScreenshot').checked = true;
    document.getElementById('apiConfigFrequency').value = '15min';
    
    document.getElementById('apiModuleConfigModal').style.display = 'flex';
}

function closeAPIConfigModal() {
    document.getElementById('apiModuleConfigModal').style.display = 'none';
    apiComplexState.currentConfigModule = null;
}

function saveAPIModuleConfig() {
    const moduleNum = apiComplexState.currentConfigModule;
    if (!moduleNum) return;
    
    const moduleName = document.getElementById('apiConfigName').value || `API #${moduleNum}`;
    const useScreenshot = document.getElementById('apiConfigScreenshot').checked;
    const frequency = document.getElementById('apiConfigFrequency').value;
    
    // Save configuration
    apiComplexState.modules[moduleNum] = {
        active: true,
        name: moduleName,
        config: {
            useScreenshot: useScreenshot,
            frequency: frequency
        }
    };
    
    // Activate the module in UI
    activateModule(moduleNum, moduleName);
    
    // Update status
    updateAPIStatus();
    
    // Close modal
    closeAPIConfigModal();
    
    console.log(`[API COMPLEX] Module ${moduleNum} activated:`, apiComplexState.modules[moduleNum]);
}

function activateModule(moduleNum, moduleName) {
    const moduleDiv = document.getElementById(`apiModule${moduleNum}`);
    if (!moduleDiv) return;
    
    // Remove placeholder class, add active
    moduleDiv.classList.remove('placeholder');
    moduleDiv.classList.add('active');
    
    // Replace content with active module template
    moduleDiv.innerHTML = `
        <div class="module-header">
            <div class="module-title-row">
                <h4 class="module-title">${moduleName}</h4>
                <button class="module-config-btn" onclick="configureModule(${moduleNum})" title="Configure">⚙</button>
            </div>
            <span class="module-value" id="frequency${moduleNum}Value">50</span>
        </div>
        <div class="module-body">
            <div class="slider-row">
                <label class="slider-label">Frequency</label>
                <input type="range" class="module-slider" id="frequency${moduleNum}Slider" min="0" max="100" value="50">
                <span class="slider-value" id="frequency${moduleNum}Display">50</span>
            </div>
            <div class="slider-row">
                <label class="slider-label">Risk/Reward</label>
                <input type="range" class="module-slider" id="riskReward${moduleNum}Slider" min="0" max="100" value="50">
                <span class="slider-value" id="riskReward${moduleNum}Display">50</span>
            </div>
            <div class="module-status">
                <div class="status-dot active"></div>
                <span class="status-text">ACTIVE</span>
            </div>
        </div>
    `;
    
    // Re-initialize sliders for this module
    initModuleSliders();
}

function configureModule(moduleNum) {
    console.log(`[API COMPLEX] Configuring module ${moduleNum}`);
    
    apiComplexState.currentConfigModule = moduleNum;
    const module = apiComplexState.modules[moduleNum];
    
    // Pre-fill modal with existing config
    document.getElementById('apiConfigTitle').textContent = `CONFIGURE ${module.name}`;
    document.getElementById('apiConfigName').value = module.name || '';
    document.getElementById('apiConfigScreenshot').checked = module.config.useScreenshot !== false;
    document.getElementById('apiConfigFrequency').value = module.config.frequency || '15min';
    
    document.getElementById('apiModuleConfigModal').style.display = 'flex';
}

function updateAPIStatus() {
    const activeCount = Object.values(apiComplexState.modules).filter(m => m.active).length;
    document.getElementById('apiStatus').textContent = `${activeCount} ACTIVE`;
}

// ============================================================================
// DECISION ENGINE
// ============================================================================

function updateDecisionEngine() {
    // Collect values from all active modules
    const activeModules = Object.entries(apiComplexState.modules)
        .filter(([num, mod]) => mod.active);
    
    if (activeModules.length === 0) {
        apiComplexState.decisionEngine.direction = 'NEUTRAL';
        apiComplexState.decisionEngine.confidence = 0;
    } else {
        // Calculate weighted average
        let totalFreq = 0;
        let totalRR = 0;
        
        activeModules.forEach(([num]) => {
            const freqSlider = document.getElementById(`frequency${num}Slider`);
            const rrSlider = document.getElementById(`riskReward${num}Slider`);
            
            if (freqSlider) totalFreq += parseInt(freqSlider.value);
            if (rrSlider) totalRR += parseInt(rrSlider.value);
        });
        
        const avgFreq = totalFreq / activeModules.length;
        const avgRR = totalRR / activeModules.length;
        
        // Determine direction
        if (avgFreq > 60) {
            apiComplexState.decisionEngine.direction = 'BULLISH';
        } else if (avgFreq < 40) {
            apiComplexState.decisionEngine.direction = 'BEARISH';
        } else {
            apiComplexState.decisionEngine.direction = 'NEUTRAL';
        }
        
        // Calculate confidence (0-100)
        apiComplexState.decisionEngine.confidence = Math.round((avgFreq + avgRR) / 2);
    }
    
    // Update UI
    updateDecisionUI();
}

function updateDecisionUI() {
    const { direction, confidence } = apiComplexState.decisionEngine;
    
    document.getElementById('apiDecisionValue').textContent = direction;
    document.getElementById('apiConfidenceText').textContent = `${confidence}%`;
    document.getElementById('apiConfidenceFill').style.width = `${confidence}%`;
    
    // Color based on direction
    const valueEl = document.getElementById('apiDecisionValue');
    if (direction === 'BULLISH') {
        valueEl.style.color = '#5cb85c';
    } else if (direction === 'BEARISH') {
        valueEl.style.color = '#ef4444';
    } else {
        valueEl.style.color = '#F2F3F4';
    }
}

async function executeDecision() {
    console.log('[API COMPLEX] Executing decision...', apiComplexState.decisionEngine);
    
    const btn = document.getElementById('apiExecuteBtn');
    btn.disabled = true;
    btn.innerHTML = '<span>EXECUTING...</span>';
    
    try {
        // Gather all active module configurations
        const activeModules = Object.entries(apiComplexState.modules)
            .filter(([num, mod]) => mod.active)
            .map(([num, mod]) => ({
                module: num,
                name: mod.name,
                frequency: parseInt(document.getElementById(`frequency${num}Slider`)?.value || 50),
                riskReward: parseInt(document.getElementById(`riskReward${num}Slider`)?.value || 50),
                useScreenshot: mod.config.useScreenshot
            }));
        
        // Call API to execute
        const response = await fetch('/api/complex/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                decision: apiComplexState.decisionEngine,
                modules: activeModules
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('[API COMPLEX] Execution successful:', data);
            showNotification('Decision executed successfully', 'success');
        } else {
            throw new Error(data.error || 'Execution failed');
        }
        
    } catch (error) {
        console.error('[API COMPLEX] Execution error:', error);
        showNotification(`Execution failed: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>EXECUTE</span>';
    }
}

// ============================================================================
// SCREENSHOT INTEGRATION
// ============================================================================

async function analyzeScreenshot(moduleNum) {
    console.log(`[API COMPLEX] Analyzing screenshot for module ${moduleNum}`);
    
    try {
        const response = await fetch('/api/vision/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                module: moduleNum,
                config: apiComplexState.modules[moduleNum].config
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`[API COMPLEX] Vision analysis complete for module ${moduleNum}:`, data.analysis);
            return data.analysis;
        } else {
            throw new Error(data.error || 'Vision analysis failed');
        }
        
    } catch (error) {
        console.error(`[API COMPLEX] Vision analysis error for module ${moduleNum}:`, error);
        return null;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // TODO: Add visual notification system
}

// ============================================================================
// END OF API COMPLEX JAVASCRIPT
// ============================================================================
