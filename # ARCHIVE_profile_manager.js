// ============================================================================
// PROFILE MANAGEMENT SYSTEM V2.0 - JAVASCRIPT
// Handles file browsing, search, selection, and risk management
// ============================================================================

// Profile Management State
const pmState = {
    selectedFolder: null,
    currentFiles: [],
    selectedFile: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[PROFILE MANAGER V2] Initializing...');
    
    initProfileManagement();
    initRiskManagement();
    loadFileCounts();
    
    console.log('[PROFILE MANAGER V2] Ready');
});

// ============================================================================
// PROFILE MANAGEMENT
// ============================================================================

function initProfileManagement() {
    // File window click handlers
    const fileWindows = document.querySelectorAll('.file-window-vertical');
    fileWindows.forEach(window => {
        window.addEventListener('click', () => selectFileWindow(window));
    });
    
    // Search button
    const searchBtn = document.getElementById('pmSearchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    // Search bar enter key
    const searchBar = document.getElementById('pmSearchBar');
    if (searchBar) {
        searchBar.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }
}

// ============================================================================
// FILE WINDOW SELECTION
// ============================================================================

function selectFileWindow(window) {
    const folder = window.getAttribute('data-folder');
    
    // Remove selected class from all windows
    document.querySelectorAll('.file-window-vertical').forEach(w => {
        w.classList.remove('selected');
    });
    
    // Add selected class to clicked window
    window.classList.add('selected');
    
    // Update state
    pmState.selectedFolder = folder;
    
    // Update search bar placeholder
    const searchBar = document.getElementById('pmSearchBar');
    if (searchBar) {
        const folderName = folder.charAt(0).toUpperCase() + folder.slice(1);
        searchBar.placeholder = `Search ${folderName}...`;
    }
    
    // Load files from folder
    loadFolderFiles(folder);
}

// ============================================================================
// FILE LOADING
// ============================================================================

async function loadFileCounts() {
    try {
        const response = await fetch('/api/files/counts');
        const counts = await response.json();
        
        // Update file counts
        if (counts.profiles !== undefined) {
            document.getElementById('profileCount').textContent = `${counts.profiles} files`;
        }
        if (counts.inputs !== undefined) {
            document.getElementById('inputCount').textContent = `${counts.inputs} files`;
        }
        if (counts.prompts !== undefined) {
            document.getElementById('promptCount').textContent = `${counts.prompts} files`;
        }
        if (counts.skills !== undefined) {
            document.getElementById('skillCount').textContent = `${counts.skills} files`;
        }
        
    } catch (error) {
        console.error('[PROFILE MANAGER] Error loading file counts:', error);
    }
}

async function loadFolderFiles(folder) {
    try {
        const response = await fetch(`/api/files/list?folder=${folder}`);
        const files = await response.json();
        
        pmState.currentFiles = files;
        displaySearchResults(files);
        
    } catch (error) {
        console.error('[PROFILE MANAGER] Error loading files:', error);
        displayError('Failed to load files');
    }
}

// ============================================================================
// SEARCH RESULTS DISPLAY
// ============================================================================

function displaySearchResults(files) {
    const resultsPanel = document.getElementById('pmSearchResults');
    
    if (!files || files.length === 0) {
        resultsPanel.innerHTML = `
            <div class="results-empty-state">
                <p>No files found</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    files.forEach(file => {
        html += `
            <div class="pm-file-item" data-filename="${file.name}">
                <div class="pm-file-info">
                    <div class="pm-file-name">${file.name}</div>
                    <div class="pm-file-meta">${file.modified} • ${formatFileSize(file.size)}</div>
                </div>
            </div>
        `;
    });
    
    resultsPanel.innerHTML = html;
    
    // Add click handlers to file items
    resultsPanel.querySelectorAll('.pm-file-item').forEach(item => {
        item.addEventListener('click', () => {
            const filename = item.getAttribute('data-filename');
            selectFile(filename);
        });
    });
}

function displayError(message) {
    const resultsPanel = document.getElementById('pmSearchResults');
    resultsPanel.innerHTML = `
        <div class="results-empty-state">
            <p style="color: #ef4444;">${message}</p>
        </div>
    `;
}

// ============================================================================
// FILE SELECTION
// ============================================================================

async function selectFile(filename) {
    try {
        const response = await fetch(`/api/files/content?folder=${pmState.selectedFolder}&file=${filename}`);
        const data = await response.json();
        
        pmState.selectedFile = data;
        
        console.log('[PROFILE MANAGER] File loaded:', filename);
        showNotification(`Loaded: ${filename}`);
        
        // TODO: Display file content in editor/viewer
        
    } catch (error) {
        console.error('[PROFILE MANAGER] Error loading file:', error);
        showNotification('Error loading file', 'error');
    }
}

// ============================================================================
// SEARCH
// ============================================================================

function performSearch() {
    const searchBar = document.getElementById('pmSearchBar');
    const searchTerm = searchBar.value.toLowerCase().trim();
    
    if (!pmState.selectedFolder) {
        showNotification('Please select a file category first', 'warning');
        return;
    }
    
    if (!searchTerm) {
        // Show all files
        displaySearchResults(pmState.currentFiles);
        return;
    }
    
    // Filter files
    const filtered = pmState.currentFiles.filter(file => 
        file.name.toLowerCase().includes(searchTerm)
    );
    
    displaySearchResults(filtered);
}

// ============================================================================
// SAVE PROFILE
// ============================================================================

async function saveProfile() {
    // TODO: Implement profile saving
    console.log('[PROFILE MANAGER] Save profile clicked');
    showNotification('Save profile functionality coming soon', 'info');
}

// ============================================================================
// RISK MANAGEMENT
// ============================================================================

function initRiskManagement() {
    // Risk/Reward slider
    const rrSlider = document.getElementById('rmRiskRewardLevel');
    const rrValue = document.getElementById('rmRiskRewardValue');
    
    if (rrSlider && rrValue) {
        rrSlider.addEventListener('input', (e) => {
            rrValue.textContent = e.target.value;
        });
    }
    
    // Drawdown slider
    const ddSlider = document.getElementById('rmMaxDrawdown');
    const ddValue = document.getElementById('rmDrawdownValue');
    
    if (ddSlider && ddValue) {
        ddSlider.addEventListener('input', (e) => {
            ddValue.textContent = `${e.target.value}%`;
        });
    }
    
    // Load saved settings
    loadRiskSettings();
    
    // Auto-save on change (debounced)
    let saveTimeout;
    const autoSave = () => {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveRiskSettings, 1000);
    };
    
    if (rrSlider) rrSlider.addEventListener('input', autoSave);
    if (ddSlider) ddSlider.addEventListener('input', autoSave);
    
    // Save on SL/TP changes
    document.querySelectorAll('.rm-tp-type-v2, .rm-tp-value-v2').forEach(element => {
        element.addEventListener('change', autoSave);
    });
}

async function loadRiskSettings() {
    try {
        const response = await fetch('/api/risk/load');
        const settings = await response.json();
        
        // Apply settings
        if (settings.riskRewardLevel) {
            const slider = document.getElementById('rmRiskRewardLevel');
            const value = document.getElementById('rmRiskRewardValue');
            if (slider && value) {
                slider.value = settings.riskRewardLevel;
                value.textContent = settings.riskRewardLevel;
            }
        }
        
        if (settings.maxDrawdown) {
            const slider = document.getElementById('rmMaxDrawdown');
            const value = document.getElementById('rmDrawdownValue');
            if (slider && value) {
                slider.value = settings.maxDrawdown;
                value.textContent = `${settings.maxDrawdown}%`;
            }
        }
        
        console.log('[RISK MANAGER] Settings loaded');
        
    } catch (error) {
        console.error('[RISK MANAGER] Error loading settings:', error);
    }
}

async function saveRiskSettings() {
    try {
        const settings = {
            riskRewardLevel: parseInt(document.getElementById('rmRiskRewardLevel')?.value || 50),
            maxDrawdown: parseInt(document.getElementById('rmMaxDrawdown')?.value || 3),
            stopLoss: [],
            takeProfit: []
        };
        
        // Collect SL values
        document.querySelectorAll('.rm-sl-column-v2 .rm-tp-row-v2').forEach(row => {
            const type = row.querySelector('.rm-tp-type-v2')?.value;
            const value = parseFloat(row.querySelector('.rm-tp-value-v2')?.value || 0);
            settings.stopLoss.push({ type, value });
        });
        
        // Collect TP values
        document.querySelectorAll('.rm-tp-column-v2 .rm-tp-row-v2').forEach(row => {
            const type = row.querySelector('.rm-tp-type-v2')?.value;
            const value = parseFloat(row.querySelector('.rm-tp-value-v2')?.value || 0);
            settings.takeProfit.push({ type, value });
        });
        
        const response = await fetch('/api/risk/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            console.log('[RISK MANAGER] Settings saved');
        }
        
    } catch (error) {
        console.error('[RISK MANAGER] Error saving settings:', error);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // TODO: Add visual notification system
}

// ============================================================================
// END OF PROFILE MANAGEMENT SYSTEM V2.0
// ============================================================================
