/**
 * MT5 META AGENT V11 - SETTINGS PAGE JAVASCRIPT
 * V11.2 - V2.032 & V2.033: Profile system integration
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    modifiedSettings: new Set(),
    originalValues: {},
    currentTier: 1,
    currentProfile: 'default',
    profiles: []
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[SETTINGS] Initializing settings interface V11.2...');
    
    // Initialize UI components
    initializeUI();
    
    // Load profiles list
    loadProfiles();
    
    // Load settings from server
    loadSettings();
    
    console.log('[SETTINGS] Initialization complete');
});

// ============================================================================
// UI INITIALIZATION
// ============================================================================

function initializeUI() {
    // Tier tabs
    document.querySelectorAll('.tier-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchTier(parseInt(this.dataset.tier));
        });
    });
    
    // Section collapse buttons
    document.querySelectorAll('.section-collapse').forEach(btn => {
        btn.addEventListener('click', function() {
            const section = this.dataset.section;
            toggleSection(section);
        });
    });
    
    // Setting inputs - track changes
    document.querySelectorAll('.setting-input, .setting-slider').forEach(input => {
        input.addEventListener('change', function() {
            markAsModified(this.id);
            updateModifiedCount();
        });
    });
    
    // Toggle switches
    document.querySelectorAll('.toggle-switch input').forEach(toggle => {
        toggle.addEventListener('change', function() {
            markAsModified(this.id);
            updateModifiedCount();
        });
    });
    
    // Sliders - update display value
    document.querySelectorAll('.setting-slider').forEach(slider => {
        slider.addEventListener('input', function() {
            const valueDisplay = this.parentElement.querySelector('.slider-value');
            if (valueDisplay) {
                const value = this.id === 'auto_refresh_interval' ? 
                    Math.round(this.value / 1000) : this.value;
                const unit = this.id === 'auto_refresh_interval' ? 's' : '';
                valueDisplay.textContent = value + unit;
            }
        });
    });
    
    // Reset buttons
    document.querySelectorAll('.reset-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const key = this.dataset.key;
            resetSetting(key);
        });
    });
    
    // Save buttons (both hero and bottom)
    document.getElementById('saveConfigHero').addEventListener('click', saveSettings);
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    
    // Reset all button
    document.getElementById('resetAll').addEventListener('click', resetAllSettings);
    
    // Export button
    document.getElementById('exportConfig').addEventListener('click', exportConfiguration);
    
    // Import button
    document.getElementById('importConfig').addEventListener('click', importConfiguration);
    
    // V2.032: Profiles dropdown toggle
    document.getElementById('profilesDropdown').addEventListener('click', function(e) {
        e.stopPropagation();
        toggleProfilesDropdown();
    });
    
    // V2.033: Create profile button
    document.getElementById('createProfileBtn').addEventListener('click', function() {
        showProfileCreationModal();
    });
    
    // V2.033: Modal controls
    document.getElementById('cancelProfileBtn').addEventListener('click', hideProfileCreationModal);
    document.getElementById('confirmCreateBtn').addEventListener('click', createNewProfile);
    
    // V2.033: Profile name input validation
    document.getElementById('profileName').addEventListener('input', validateProfileName);
    
    // V2.033: Enter key in modal
    document.getElementById('profileName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            createNewProfile();
        }
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        const dropdown = document.querySelector('.profile-dropdown-container');
        if (dropdown && !dropdown.contains(e.target)) {
            closeProfilesDropdown();
        }
    });
    
    // Close modal when clicking overlay
    document.getElementById('profileModal').addEventListener('click', function(e) {
        if (e.target === this) {
            hideProfileCreationModal();
        }
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
// TIER SWITCHING
// ============================================================================

function switchTier(tier) {
    document.querySelectorAll('.tier-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tier="${tier}"]`).classList.add('active');
    
    document.querySelectorAll('.tier-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tier${tier}`).classList.add('active');
    
    CONFIG.currentTier = tier;
}

// ============================================================================
// SECTION COLLAPSE
// ============================================================================

function toggleSection(sectionName) {
    const body = document.getElementById(`${sectionName}-settings`);
    const icon = document.querySelector(`[data-section="${sectionName}"] .section-extendo`);
    
    if (!body) return;
    
    if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        icon.setAttribute('data-state', 'up');
    } else {
        body.classList.add('collapsed');
        icon.setAttribute('data-state', 'down');
    }
}

// ============================================================================
// PROFILE MANAGEMENT - V2.032 & V2.033
// ============================================================================

async function loadProfiles() {
    try {
        const response = await fetch('/api/profiles/list');
        const data = await response.json();
        
        if (data.success) {
            CONFIG.profiles = data.profiles;
            CONFIG.currentProfile = data.active_profile || 'default';
            renderProfilesList();
            console.log('[PROFILES] Loaded profiles:', CONFIG.profiles);
        } else {
            console.error('[PROFILES] Failed to load profiles:', data.message);
            // Show default profile only
            CONFIG.profiles = [{ id: 'default', name: 'Default' }];
            renderProfilesList();
        }
    } catch (error) {
        console.error('[PROFILES] Error loading profiles:', error);
        // Show default profile only
        CONFIG.profiles = [{ id: 'default', name: 'Default' }];
        renderProfilesList();
    }
}

function renderProfilesList() {
    const profileList = document.getElementById('profileList');
    if (!profileList) return;
    
    profileList.innerHTML = '';
    
    CONFIG.profiles.forEach(profile => {
        const item = document.createElement('div');
        item.className = 'profile-item';
        if (profile.id === CONFIG.currentProfile) {
            item.classList.add('active');
        }
        item.dataset.profileId = profile.id;
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = profile.name;
        item.appendChild(nameSpan);
        
        if (profile.id === CONFIG.currentProfile) {
            const badge = document.createElement('span');
            badge.className = 'profile-badge';
            badge.textContent = 'ACTIVE';
            item.appendChild(badge);
        }
        
        item.addEventListener('click', function() {
            switchProfile(profile.id);
        });
        
        profileList.appendChild(item);
    });
}

function toggleProfilesDropdown() {
    const container = document.querySelector('.profile-dropdown-container');
    const menu = document.getElementById('profileMenu');
    
    if (container.classList.contains('open')) {
        closeProfilesDropdown();
    } else {
        container.classList.add('open');
        menu.classList.add('show');
    }
}

function closeProfilesDropdown() {
    const container = document.querySelector('.profile-dropdown-container');
    const menu = document.getElementById('profileMenu');
    
    container.classList.remove('open');
    menu.classList.remove('show');
}

async function switchProfile(profileId) {
    if (profileId === CONFIG.currentProfile) {
        closeProfilesDropdown();
        return;
    }
    
    try {
        const response = await fetch('/api/profiles/switch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ profile_id: profileId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            CONFIG.currentProfile = profileId;
            
            // Load settings for this profile
            populateSettings(data.settings);
            
            // Update UI
            renderProfilesList();
            closeProfilesDropdown();
            
            // Clear modified indicators
            CONFIG.modifiedSettings.clear();
            document.querySelectorAll('.setting-item.modified').forEach(item => {
                item.classList.remove('modified');
            });
            document.querySelectorAll('.setting-input.modified').forEach(input => {
                input.classList.remove('modified');
            });
            updateModifiedCount();
            
            const profile = CONFIG.profiles.find(p => p.id === profileId);
            showStatusMessage('success', `Loaded profile: ${profile.name}`);
        } else {
            showStatusMessage('error', data.message || 'Failed to switch profile');
        }
        
    } catch (error) {
        console.error('[PROFILES] Error switching profile:', error);
        showStatusMessage('error', 'Failed to switch profile');
    }
}

// ============================================================================
// PROFILE CREATION - V2.033
// ============================================================================

function showProfileCreationModal() {
    const modal = document.getElementById('profileModal');
    const input = document.getElementById('profileName');
    const errorDiv = document.getElementById('profileError');
    
    // Clear previous state
    input.value = '';
    errorDiv.classList.remove('show');
    errorDiv.textContent = '';
    
    // Show modal
    modal.classList.add('show');
    
    // Focus input
    setTimeout(() => input.focus(), 100);
    
    // Close dropdown
    closeProfilesDropdown();
}

function hideProfileCreationModal() {
    const modal = document.getElementById('profileModal');
    modal.classList.remove('show');
}

function validateProfileName() {
    const input = document.getElementById('profileName');
    const errorDiv = document.getElementById('profileError');
    const createBtn = document.getElementById('confirmCreateBtn');
    const name = input.value.trim();
    
    // Clear previous error
    errorDiv.classList.remove('show');
    errorDiv.textContent = '';
    createBtn.disabled = false;
    
    // Check length
    if (name.length < 3) {
        if (name.length > 0) {
            errorDiv.textContent = 'Profile name must be at least 3 characters';
            errorDiv.classList.add('show');
            createBtn.disabled = true;
        }
        return false;
    }
    
    // Check for duplicates
    const duplicate = CONFIG.profiles.find(p => 
        p.name.toLowerCase() === name.toLowerCase()
    );
    if (duplicate) {
        errorDiv.textContent = 'A profile with this name already exists';
        errorDiv.classList.add('show');
        createBtn.disabled = true;
        return false;
    }
    
    // Check valid characters
    const validPattern = /^[a-zA-Z0-9\s\-_]+$/;
    if (!validPattern.test(name)) {
        errorDiv.textContent = 'Use only letters, numbers, spaces, hyphens, and underscores';
        errorDiv.classList.add('show');
        createBtn.disabled = true;
        return false;
    }
    
    return true;
}

async function createNewProfile() {
    const input = document.getElementById('profileName');
    const name = input.value.trim();
    
    // Validate
    if (!validateProfileName()) {
        return;
    }
    
    // Disable button during creation
    const createBtn = document.getElementById('confirmCreateBtn');
    createBtn.disabled = true;
    createBtn.textContent = 'CREATING...';
    
    try {
        // Capture current settings
        const currentSettings = captureAllSettings();
        
        // Send to backend
        const response = await fetch('/api/profiles/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                settings: currentSettings
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Add to profiles list
            CONFIG.profiles.push(data.profile);
            
            // Update UI
            renderProfilesList();
            hideProfileCreationModal();
            
            showStatusMessage('success', `Profile "${name}" created successfully`);
        } else {
            const errorDiv = document.getElementById('profileError');
            errorDiv.textContent = data.message || 'Failed to create profile';
            errorDiv.classList.add('show');
        }
        
    } catch (error) {
        console.error('[PROFILES] Error creating profile:', error);
        const errorDiv = document.getElementById('profileError');
        errorDiv.textContent = 'Connection error - profile not created';
        errorDiv.classList.add('show');
    } finally {
        // Re-enable button
        createBtn.disabled = false;
        createBtn.textContent = 'CREATE PROFILE';
    }
}

function captureAllSettings() {
    const settings = {};
    
    document.querySelectorAll('.setting-input, .setting-slider').forEach(input => {
        let value;
        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'number' || input.type === 'range') {
            value = parseFloat(input.value);
        } else {
            value = input.value;
        }
        settings[input.id] = value;
    });
    
    // Capture toggle switches separately
    document.querySelectorAll('.toggle-switch input').forEach(toggle => {
        settings[toggle.id] = toggle.checked;
    });
    
    return settings;
}

// ============================================================================
// LOAD SETTINGS FROM SERVER
// ============================================================================

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        
        if (data.success) {
            populateSettings(data.settings);
            storeOriginalValues(data.settings);
            console.log('[SETTINGS] Loaded settings from server');
        } else {
            showStatusMessage('error', 'Failed to load settings');
        }
    } catch (error) {
        console.error('[SETTINGS] Error loading settings:', error);
        showStatusMessage('error', 'Connection error');
    }
}

function populateSettings(settings) {
    Object.entries(settings).forEach(([key, value]) => {
        const element = document.getElementById(key);
        if (!element) return;
        
        if (element.type === 'checkbox') {
            element.checked = value === true || value === 'true';
        } else if (element.type === 'range') {
            element.value = value;
            // Update slider display
            const valueDisplay = element.parentElement.querySelector('.slider-value');
            if (valueDisplay) {
                const displayValue = key === 'auto_refresh_interval' ? 
                    Math.round(value / 1000) : value;
                const unit = key === 'auto_refresh_interval' ? 's' : '';
                valueDisplay.textContent = displayValue + unit;
            }
        } else {
            element.value = value;
        }
    });
}

function storeOriginalValues(settings) {
    CONFIG.originalValues = { ...settings };
}

// ============================================================================
// SAVE SETTINGS TO SERVER
// ============================================================================

async function saveSettings() {
    const modifiedSettings = {};
    
    // Collect all modified settings
    CONFIG.modifiedSettings.forEach(key => {
        const element = document.getElementById(key);
        if (!element) return;
        
        let value;
        if (element.type === 'checkbox') {
            value = element.checked;
        } else if (element.type === 'number' || element.type === 'range') {
            value = parseFloat(element.value);
        } else {
            value = element.value;
        }
        
        modifiedSettings[key] = value;
    });
    
    if (Object.keys(modifiedSettings).length === 0) {
        showStatusMessage('error', 'No changes to save');
        return;
    }
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                profile_id: CONFIG.currentProfile,
                settings: modifiedSettings
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Clear modified indicators
            CONFIG.modifiedSettings.clear();
            document.querySelectorAll('.setting-item.modified').forEach(item => {
                item.classList.remove('modified');
            });
            document.querySelectorAll('.setting-input.modified').forEach(input => {
                input.classList.remove('modified');
            });
            
            // Update last saved time
            const now = new Date();
            document.getElementById('lastSaved').textContent = 
                now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            
            // Update modified count
            updateModifiedCount();
            
            // Show success message
            showStatusMessage('success', `Successfully saved ${Object.keys(modifiedSettings).length} settings`);
            
            // Update original values
            storeOriginalValues({ ...CONFIG.originalValues, ...modifiedSettings });
            
        } else {
            showStatusMessage('error', data.message || 'Failed to save settings');
        }
        
    } catch (error) {
        console.error('[SETTINGS] Error saving settings:', error);
        showStatusMessage('error', 'Connection error - settings not saved');
    }
}

// ============================================================================
// RESET SETTINGS
// ============================================================================

async function resetSetting(key) {
    try {
        const response = await fetch(`/api/settings/reset/${key}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = data.value === true || data.value === 'true';
                } else {
                    element.value = data.value;
                }
                
                CONFIG.modifiedSettings.delete(key);
                element.classList.remove('modified');
                element.closest('.setting-item').classList.remove('modified');
                updateModifiedCount();
            }
            
            showStatusMessage('success', `Reset ${key} to default`);
        }
        
    } catch (error) {
        console.error('[SETTINGS] Error resetting setting:', error);
        showStatusMessage('error', 'Failed to reset setting');
    }
}

async function resetAllSettings() {
    if (!confirm('Reset ALL settings to defaults? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/settings/reset', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadSettings();
            
            CONFIG.modifiedSettings.clear();
            document.querySelectorAll('.setting-item.modified').forEach(item => {
                item.classList.remove('modified');
            });
            document.querySelectorAll('.setting-input.modified').forEach(input => {
                input.classList.remove('modified');
            });
            updateModifiedCount();
            
            showStatusMessage('success', 'All settings reset to defaults');
        }
        
    } catch (error) {
        console.error('[SETTINGS] Error resetting all settings:', error);
        showStatusMessage('error', 'Failed to reset settings');
    }
}

// ============================================================================
// EXPORT/IMPORT CONFIGURATION
// ============================================================================

async function exportConfiguration() {
    try {
        const response = await fetch('/api/settings/export');
        const data = await response.json();
        
        if (data.success) {
            const blob = new Blob([data.config], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mt5_config_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showStatusMessage('success', 'Configuration exported successfully');
        }
        
    } catch (error) {
        console.error('[SETTINGS] Error exporting config:', error);
        showStatusMessage('error', 'Failed to export configuration');
    }
}

function importConfiguration() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const config = e.target.result;
                
                const response = await fetch('/api/settings/import', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: config
                });
                
                const data = await response.json();
                
                if (data.success) {
                    await loadSettings();
                    showStatusMessage('success', data.message);
                } else {
                    showStatusMessage('error', data.message || 'Import failed');
                }
                
            } catch (error) {
                console.error('[SETTINGS] Error importing config:', error);
                showStatusMessage('error', 'Failed to import configuration');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function markAsModified(key) {
    CONFIG.modifiedSettings.add(key);
    
    const element = document.getElementById(key);
    if (element) {
        element.classList.add('modified');
        const settingItem = element.closest('.setting-item');
        if (settingItem) {
            settingItem.classList.add('modified');
        }
    }
}

function updateModifiedCount() {
    document.getElementById('modifiedCount').textContent = CONFIG.modifiedSettings.size;
}

function showStatusMessage(type, message) {
    const statusDiv = document.getElementById('statusMessage');
    const iconSpan = statusDiv.querySelector('.status-icon');
    const textSpan = statusDiv.querySelector('.status-text');
    
    iconSpan.textContent = type === 'success' ? '✓' : '⚠';
    textSpan.textContent = message;
    
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'flex';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

// ============================================================================
// EXPORT FOR CONSOLE DEBUGGING
// ============================================================================

window.SettingsDebug = {
    loadSettings,
    saveSettings,
    resetAllSettings,
    exportConfiguration,
    loadProfiles,
    switchProfile,
    captureAllSettings,
    modifiedSettings: () => Array.from(CONFIG.modifiedSettings),
    originalValues: () => CONFIG.originalValues,
    currentProfile: () => CONFIG.currentProfile,
    profiles: () => CONFIG.profiles
};

console.log('[SETTINGS] Debug functions available: window.SettingsDebug');
