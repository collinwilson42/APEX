// ============================================================================
// PROFILE MANAGEMENT SYSTEM - JAVASCRIPT (V1.1-1.6)
// Add this to database.js or create new profile_manager.js
// ============================================================================

// Profile Management State
const profileManager = {
    selectedFolder: null,
    currentFiles: [],
    searchTerm: ''
};

// ============================================================================
// INITIALIZATION
// ============================================================================

function initProfileManagement() {
    console.log('[PROFILE MANAGEMENT] Initializing...');
    
    // Initialize file windows
    initFileWindows();
    
    // Initialize search functionality
    initProfileSearch();
    
    // Initialize save button
    initSaveButton();
    
    // Load initial file counts
    loadFileCounts();
    
    console.log('[PROFILE MANAGEMENT] Ready');
}

// ============================================================================
// FILE WINDOWS (V1.3)
// ============================================================================

function initFileWindows() {
    const windows = document.querySelectorAll('.pm-file-window');
    
    windows.forEach(window => {
        window.addEventListener('click', () => {
            selectFileWindow(window);
        });
    });
}

function selectFileWindow(window) {
    // Remove selection from all windows
    document.querySelectorAll('.pm-file-window').forEach(w => {
        w.classList.remove('selected');
    });
    
    // Add selection to clicked window
    window.classList.add('selected');
    
    // Get folder name
    const folder = window.dataset.folder;
    profileManager.selectedFolder = folder;
    
    // Update search bar placeholder
    const searchBar = document.getElementById('pmSearchBar');
    searchBar.placeholder = `Search ${capitalizeFirst(folder)}...`;
    
    // Load files for this folder
    loadFolderFiles(folder);
}

// ============================================================================
// SEARCH FUNCTIONALITY (V1.211 + V1.31)
// ============================================================================

function initProfileSearch() {
    const searchBar = document.getElementById('pmSearchBar');
    const searchBtn = document.getElementById('pmSearchBtn');
    
    // Search on button click
    searchBtn.addEventListener('click', performSearch);
    
    // Search on Enter key
    searchBar.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Real-time search (debounced)
    let searchTimeout;
    searchBar.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            profileManager.searchTerm = e.target.value;
            filterResults();
        }, 300);
    });
}

function performSearch() {
    const searchTerm = document.getElementById('pmSearchBar').value;
    profileManager.searchTerm = searchTerm;
    filterResults();
}

function filterResults() {
    const term = profileManager.searchTerm.toLowerCase();
    const resultsPanel = document.getElementById('pmSearchResults');
    
    if (!profileManager.selectedFolder) {
        resultsPanel.innerHTML = '<div class="pm-empty-state"><p>Select a file category first</p></div>';
        return;
    }
    
    // Filter files
    const filtered = profileManager.currentFiles.filter(file => 
        file.name.toLowerCase().includes(term)
    );
    
    // Display results
    displaySearchResults(filtered);
}

// ============================================================================
// FILE LOADING (Backend Integration)
// ============================================================================

async function loadFileCounts() {
    try {
        const response = await fetch('/api/files/counts');
        const data = await response.json();
        
        document.getElementById('profileCount').textContent = `${data.profiles || 0} files`;
        document.getElementById('inputCount').textContent = `${data.inputs || 0} files`;
        document.getElementById('promptCount').textContent = `${data.prompts || 0} files`;
        document.getElementById('skillCount').textContent = `${data.skills || 0} files`;
        
    } catch (error) {
        console.error('[PROFILE MANAGEMENT] Error loading file counts:', error);
    }
}

async function loadFolderFiles(folder) {
    try {
        const response = await fetch(`/api/files/list?folder=${folder}`);
        const data = await response.json();
        
        profileManager.currentFiles = data.files || [];
        displaySearchResults(profileManager.currentFiles);
        
    } catch (error) {
        console.error('[PROFILE MANAGEMENT] Error loading files:', error);
        displayError('Failed to load files');
    }
}

// ============================================================================
// RESULTS DISPLAY (V1.31)
// ============================================================================

function displaySearchResults(files) {
    const resultsPanel = document.getElementById('pmSearchResults');
    
    if (files.length === 0) {
        resultsPanel.innerHTML = `
            <div class="pm-empty-state">
                <p>No files found</p>
            </div>
        `;
        return;
    }
    
    const html = files.map(file => `
        <div class="pm-file-item" data-file="${file.name}" onclick="selectFile('${file.name}', '${profileManager.selectedFolder}')">
            <div class="pm-file-icon">📄</div>
            <div class="pm-file-info">
                <div class="pm-file-name">${file.name}</div>
                <div class="pm-file-meta">
                    <span>${formatDate(file.modified)}</span>
                    <span>${formatSize(file.size)}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    resultsPanel.innerHTML = html;
}

function displayError(message) {
    const resultsPanel = document.getElementById('pmSearchResults');
    resultsPanel.innerHTML = `
        <div class="pm-empty-state">
            <p style="color: #ef4444;">${message}</p>
        </div>
    `;
}

// ============================================================================
// FILE SELECTION
// ============================================================================

async function selectFile(filename, folder) {
    console.log(`[PROFILE MANAGEMENT] Selected: ${folder}/${filename}`);
    
    try {
        const response = await fetch(`/api/files/content?folder=${folder}&file=${filename}`);
        const data = await response.json();
        
        // TODO: Display file content or trigger appropriate action
        console.log('[PROFILE MANAGEMENT] File content:', data);
        
        showNotification(`Loaded: ${filename}`, 'success');
        
    } catch (error) {
        console.error('[PROFILE MANAGEMENT] Error loading file:', error);
        showNotification('Failed to load file', 'error');
    }
}

// ============================================================================
// SAVE BUTTON (V1.2111)
// ============================================================================

function initSaveButton() {
    const saveBtn = document.getElementById('pmSaveBtn');
    
    saveBtn.addEventListener('click', async () => {
        // TODO: Implement save current profile logic
        console.log('[PROFILE MANAGEMENT] Save profile clicked');
        showNotification('Profile save functionality coming soon', 'info');
    });
}

// ============================================================================
// RISK MANAGEMENT CONTROLS (V1.4)
// ============================================================================

function initRiskManagement() {
    const drawdownSlider = document.getElementById('rmMaxDrawdown');
    const drawdownValue = document.getElementById('rmDrawdownValue');
    
    // Update value display
    drawdownSlider.addEventListener('input', (e) => {
        drawdownValue.textContent = `${e.target.value}%`;
    });
    
    // Save on change
    drawdownSlider.addEventListener('change', (e) => {
        saveRiskSettings();
    });
    
    // Take profit inputs
    const tpValues = document.querySelectorAll('.rm-tp-value');
    tpValues.forEach(input => {
        input.addEventListener('change', saveRiskSettings);
    });
}

async function saveRiskSettings() {
    const settings = {
        maxDrawdown: document.getElementById('rmMaxDrawdown').value,
        takeProfits: Array.from(document.querySelectorAll('.rm-tp-value')).map(input => ({
            type: input.previousElementSibling.value,
            value: input.value
        }))
    };
    
    try {
        const response = await fetch('/api/risk/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            showNotification('Risk settings saved', 'success');
        }
    } catch (error) {
        console.error('[RISK MANAGEMENT] Save error:', error);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showNotification(message, type = 'info') {
    // TODO: Implement notification system
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// ============================================================================
// INITIALIZE ON LOAD
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initProfileManagement();
    initRiskManagement();
});

// ============================================================================
// END OF PROFILE MANAGEMENT SYSTEM
// ============================================================================
