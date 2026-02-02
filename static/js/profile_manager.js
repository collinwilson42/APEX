/* ═══════════════════════════════════════════════════════════════════════════
   APEX PROFILE MANAGER V2.0 - Quadrant Grid + Leaderboard
   
   Features:
   - Single-pane toggle between List and Form views
   - Profile image upload with circular avatar
   - North Star ranking: (Net Profit / Normalized Signals) * Profit Factor
   - Rank badges with leaderboard aesthetic
   - Normalized signals: 1 lot = 1 signal
   ═══════════════════════════════════════════════════════════════════════════ */

const ProfileManager = {
    
    // ═══════════════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════════════
    
    profiles: [],
    activeProfileId: null,
    selectedProfileId: null,
    currentView: 'list', // 'list' | 'form'
    editingProfileId: null, // null = creating new
    pendingImageFile: null,
    pendingImagePreview: null,
    
    // Provider configurations
    providers: {
        anthropic: {
            name: 'Anthropic',
            shortName: 'Claude',
            icon: 'A',
            models: [
                { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', short: 'Sonnet 4', default: true },
                { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', short: 'Opus 4' },
                { id: 'claude-haiku-4-20250514', name: 'Claude Haiku 4', short: 'Haiku 4' }
            ],
            keyPlaceholder: 'sk-ant-api03-...'
        },
        google: {
            name: 'Google AI',
            shortName: 'Gemini',
            icon: 'G',
            models: [
                { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', short: '2.0 Flash', default: true },
                { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', short: '2.5 Pro' },
                { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', short: '1.5 Flash' }
            ],
            keyPlaceholder: 'AIza...'
        },
        openai: {
            name: 'OpenAI',
            shortName: 'GPT',
            icon: 'O',
            models: [
                { id: 'gpt-4o', name: 'GPT-4o', short: '4o', default: true },
                { id: 'gpt-4o-mini', name: 'GPT-4o Mini', short: '4o Mini' },
                { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', short: '4 Turbo' }
            ],
            keyPlaceholder: 'sk-proj-...'
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════
    
    init() {
        this.loadProfiles();
        this.render();
        console.log('[ProfileManager] V2 Initialized with', this.profiles.length, 'profiles');
    },
    
    loadProfiles() {
        try {
            const stored = localStorage.getItem('apex_profiles_v2');
            this.profiles = stored ? JSON.parse(stored) : [];
            
            const activeId = localStorage.getItem('apex_active_profile');
            if (activeId && this.profiles.find(p => p.id === activeId)) {
                this.activeProfileId = activeId;
            }
            
            // Sort by North Star score
            this.sortProfilesByNorthStar();
        } catch (e) {
            console.error('[ProfileManager] Failed to load profiles:', e);
            this.profiles = [];
        }
    },
    
    saveProfiles() {
        try {
            localStorage.setItem('apex_profiles_v2', JSON.stringify(this.profiles));
            if (this.activeProfileId) {
                localStorage.setItem('apex_active_profile', this.activeProfileId);
            }
        } catch (e) {
            console.error('[ProfileManager] Failed to save profiles:', e);
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // NORTH STAR CALCULATION
    // ═══════════════════════════════════════════════════════════════════════
    
    /**
     * Calculate North Star score: (Net Profit / Normalized Signals) * Profit Factor
     * Normalized Signals = Total Lots traded (1 lot = 1 signal)
     */
    calculateNorthStar(profile) {
        const stats = profile.stats || {};
        const netProfit = stats.netProfit || 0;
        const totalLots = stats.totalLots || 0; // Normalized signals
        const profitFactor = stats.profitFactor || 0;
        
        if (totalLots === 0 || profitFactor === 0) return 0;
        
        return (netProfit / totalLots) * profitFactor;
    },
    
    sortProfilesByNorthStar() {
        this.profiles.sort((a, b) => {
            const scoreA = this.calculateNorthStar(a);
            const scoreB = this.calculateNorthStar(b);
            return scoreB - scoreA; // Descending
        });
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // PROFILE CRUD
    // ═══════════════════════════════════════════════════════════════════════
    
    createProfile(data) {
        const profile = {
            id: 'profile_' + Date.now(),
            name: data.name || 'New Profile',
            provider: data.provider || 'google',
            model: data.model || this.getDefaultModel(data.provider || 'google'),
            apiKey: data.apiKey || '',
            imagePath: data.imagePath || null,
            status: 'inactive',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            stats: {
                netProfit: 0,
                totalLots: 0,      // Normalized signals (1 lot = 1 signal)
                profitFactor: 0,
                totalCalls: 0,
                successRate: 0,
                avgLatency: 0,
                lastUsed: null
            }
        };
        
        this.profiles.push(profile);
        this.sortProfilesByNorthStar();
        this.saveProfiles();
        
        return profile;
    },
    
    updateProfile(id, updates) {
        const index = this.profiles.findIndex(p => p.id === id);
        if (index === -1) return null;
        
        this.profiles[index] = {
            ...this.profiles[index],
            ...updates,
            updatedAt: new Date().toISOString()
        };
        
        this.sortProfilesByNorthStar();
        this.saveProfiles();
        
        return this.profiles[index];
    },
    
    deleteProfile(id) {
        const index = this.profiles.findIndex(p => p.id === id);
        if (index === -1) return false;
        
        this.profiles.splice(index, 1);
        
        if (this.activeProfileId === id) {
            this.activeProfileId = null;
        }
        if (this.selectedProfileId === id) {
            this.selectedProfileId = null;
        }
        
        this.saveProfiles();
        return true;
    },
    
    setActiveProfile(id) {
        const profile = this.profiles.find(p => p.id === id);
        if (!profile) return false;
        
        this.profiles.forEach(p => p.status = 'inactive');
        profile.status = 'active';
        this.activeProfileId = id;
        
        this.saveProfiles();
        this.render();
        
        window.dispatchEvent(new CustomEvent('apex:profile:change', { detail: { profile } }));
        console.log('[ProfileManager] Active profile changed:', profile.name);
        
        return true;
    },
    
    getDefaultModel(provider) {
        const config = this.providers[provider];
        if (!config) return null;
        const defaultModel = config.models.find(m => m.default);
        return defaultModel ? defaultModel.id : config.models[0].id;
    },
    
    getModelShortName(provider, modelId) {
        const config = this.providers[provider];
        if (!config) return modelId;
        const model = config.models.find(m => m.id === modelId);
        return model ? model.short : modelId;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // VIEW MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════
    
    showListView() {
        this.currentView = 'list';
        this.editingProfileId = null;
        this.pendingImageFile = null;
        this.pendingImagePreview = null;
        this.render();
    },
    
    showCreateForm() {
        this.currentView = 'form';
        this.editingProfileId = null;
        this.pendingImageFile = null;
        this.pendingImagePreview = null;
        this.render();
    },
    
    showEditForm(profileId) {
        this.currentView = 'form';
        this.editingProfileId = profileId;
        this.pendingImageFile = null;
        this.pendingImagePreview = null;
        this.render();
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // RENDER
    // ═══════════════════════════════════════════════════════════════════════
    
    render() {
        const container = document.getElementById('profile-manager');
        if (!container) return;
        
        const isFormView = this.currentView === 'form';
        const editingProfile = this.editingProfileId 
            ? this.profiles.find(p => p.id === this.editingProfileId) 
            : null;
        
        container.innerHTML = `
            <div class="pm-header">
                <div class="pm-header__title">
                    ${isFormView ? (editingProfile ? 'Edit Profile' : 'New Profile') : 'Profiles'}
                </div>
                <div class="pm-header__actions">
                    ${isFormView ? `
                        <button class="pm-btn pm-btn--secondary pm-btn--small" onclick="ProfileManager.showListView()">
                            ← Back
                        </button>
                    ` : `
                        <button class="pm-btn pm-btn--primary pm-btn--small" onclick="ProfileManager.showCreateForm()">
                            + New
                        </button>
                    `}
                </div>
            </div>
            <div class="pm-body ${isFormView ? 'pm-slide-enter' : 'pm-fade-enter'}">
                ${isFormView ? this.renderForm(editingProfile) : this.renderLeaderboard()}
            </div>
        `;
    },
    
    renderLeaderboard() {
        if (this.profiles.length === 0) {
            return `
                <div class="pm-empty">
                    <div class="pm-empty__icon">🏆</div>
                    <div class="pm-empty__text">No profiles yet</div>
                    <div class="pm-empty__hint">Create a profile to start tracking performance</div>
                </div>
            `;
        }
        
        return `
            <div class="pm-leaderboard">
                ${this.profiles.map((profile, index) => this.renderProfileRow(profile, index + 1)).join('')}
            </div>
        `;
    },
    
    renderProfileRow(profile, rank) {
        const provider = this.providers[profile.provider];
        const isActive = profile.status === 'active';
        const isSelected = profile.id === this.selectedProfileId;
        const northStar = this.calculateNorthStar(profile);
        const modelShort = this.getModelShortName(profile.provider, profile.model);
        
        return `
            <div class="pm-profile-row ${isSelected ? 'pm-profile-row--selected' : ''} ${isActive ? 'pm-profile-row--active' : ''}"
                 onclick="ProfileManager.selectProfile('${profile.id}')"
                 ondblclick="ProfileManager.showEditForm('${profile.id}')"
                 oncontextmenu="event.preventDefault(); ProfileManager.showContextMenu(event, '${profile.id}')">
                
                <div class="pm-avatar-container">
                    ${profile.imagePath 
                        ? `<img class="pm-avatar" src="${profile.imagePath}" alt="${profile.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                           <div class="pm-avatar pm-avatar--placeholder" style="display:none;">${provider?.icon || '?'}</div>`
                        : `<div class="pm-avatar pm-avatar--placeholder">${provider?.icon || '?'}</div>`
                    }
                    <div class="pm-rank-badge pm-rank-badge--${rank <= 3 ? rank : ''}">${rank}</div>
                </div>
                
                <div class="pm-profile-info">
                    <div class="pm-profile-name">${profile.name}</div>
                    <div class="pm-profile-provider">
                        <span class="pm-provider-dot pm-provider-dot--${profile.provider}"></span>
                        <span>${provider?.shortName || profile.provider} ${modelShort}</span>
                    </div>
                </div>
                
                <div class="pm-profile-score">
                    <div class="pm-score-value">${northStar.toFixed(2)}</div>
                    <div class="pm-score-label">North Star</div>
                </div>
                
                <div class="pm-status-dot pm-status-dot--${isActive ? 'active' : 'inactive'}" 
                     title="${isActive ? 'Active' : 'Inactive'}"></div>
            </div>
        `;
    },
    
    renderForm(profile) {
        const provider = profile?.provider || 'google';
        const providerConfig = this.providers[provider];
        const imageSrc = this.pendingImagePreview || profile?.imagePath;
        
        return `
            <form class="pm-form" onsubmit="event.preventDefault(); return false;">
                <!-- Avatar Upload -->
                <div class="pm-form-group">
                    <label class="pm-label">Profile Image</label>
                    <div class="pm-avatar-upload">
                        <div class="pm-avatar-preview" onclick="event.stopPropagation(); document.getElementById('pm-image-input').click()">
                            ${imageSrc 
                                ? `<img src="${imageSrc}" alt="Preview" />`
                                : `<span class="pm-avatar-preview__placeholder">📷</span>`
                            }
                        </div>
                        <input type="file" id="pm-image-input" accept="image/*" 
                               style="display: none;" onclick="event.stopPropagation()" onchange="ProfileManager.handleImageSelect(event)" />
                        <div class="pm-avatar-upload__text">
                            <button type="button" class="pm-btn pm-btn--secondary pm-btn--small" 
                                    onclick="event.stopPropagation(); document.getElementById('pm-image-input').click()">
                                Choose Image
                            </button>
                            <div class="pm-avatar-upload__hint">PNG, JPG up to 2MB</div>
                        </div>
                    </div>
                </div>
                
                <!-- Profile Name -->
                <div class="pm-form-group">
                    <label class="pm-label">Profile Name</label>
                    <input type="text" class="pm-input" id="pm-name" 
                           value="${profile?.name || ''}" 
                           placeholder="My Trading Profile"
                           onclick="event.stopPropagation()"
                           onkeydown="event.stopPropagation()">
                </div>
                
                <!-- Provider -->
                <div class="pm-form-group">
                    <label class="pm-label">Provider</label>
                    <div class="pm-provider-select">
                        ${Object.entries(this.providers).map(([key, prov]) => `
                            <button type="button" class="pm-provider-btn ${provider === key ? 'pm-provider-btn--active' : ''}"
                                    onclick="event.stopPropagation(); ProfileManager.selectProvider('${key}')">
                                <div class="pm-provider-btn__icon pm-provider-btn__icon--${key}">${prov.icon}</div>
                                <div class="pm-provider-btn__label">${prov.shortName}</div>
                            </button>
                        `).join('')}
                    </div>
                </div>
                
                <!-- Model -->
                <div class="pm-form-group">
                    <label class="pm-label">Model</label>
                    <select class="pm-select" id="pm-model" onclick="event.stopPropagation()">
                        ${providerConfig.models.map(model => `
                            <option value="${model.id}" ${profile?.model === model.id ? 'selected' : ''}>
                                ${model.name}
                            </option>
                        `).join('')}
                    </select>
                </div>
                
                <!-- API Key -->
                <div class="pm-form-group">
                    <label class="pm-label">API Key</label>
                    <div class="pm-key-field">
                        <input type="password" class="pm-input" id="pm-apikey"
                               value="${profile?.apiKey || ''}"
                               placeholder="${providerConfig.keyPlaceholder}"
                               onclick="event.stopPropagation()"
                               onkeydown="event.stopPropagation()">
                        <button type="button" class="pm-key-toggle" onclick="event.stopPropagation(); ProfileManager.toggleKeyVisibility()">👁</button>
                    </div>
                </div>
                
                <div id="pm-connection-status"></div>
                
                <!-- Actions -->
                <div class="pm-form-actions">
                    <button type="button" class="pm-btn pm-btn--primary" onclick="event.stopPropagation(); ProfileManager.saveFromForm()">
                        ${profile ? 'Save Changes' : 'Create Profile'}
                    </button>
                    <button type="button" class="pm-btn pm-btn--secondary" onclick="event.stopPropagation(); ProfileManager.testConnection()">
                        Test
                    </button>
                    ${profile ? `
                        ${profile.status !== 'active' ? `
                            <button type="button" class="pm-btn pm-btn--secondary" onclick="event.stopPropagation(); ProfileManager.setActiveProfile('${profile.id}')">
                                Activate
                            </button>
                        ` : ''}
                        <button type="button" class="pm-btn pm-btn--danger pm-btn--icon" onclick="event.stopPropagation(); ProfileManager.confirmDelete('${profile.id}')" title="Delete">
                            🗑
                        </button>
                    ` : ''}
                </div>
            </form>
        `;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════════
    
    selectProfile(id) {
        this.selectedProfileId = id;
        this.render();
        
        // Emit event for Profile Details panel (Q2)
        window.dispatchEvent(new CustomEvent('apex:profile:selected', {
            detail: { profileId: id, profile: this.profiles.find(p => p.id === id) }
        }));
    },
    
    selectProvider(provider) {
        // Re-render form with new provider
        const nameInput = document.getElementById('pm-name');
        const currentName = nameInput?.value || '';
        
        // Temporarily store form data
        const tempProfile = this.editingProfileId 
            ? { ...this.profiles.find(p => p.id === this.editingProfileId), provider, model: this.getDefaultModel(provider) }
            : { provider, model: this.getDefaultModel(provider), name: currentName };
        
        // Update form
        const container = document.querySelector('.pm-body');
        if (container) {
            container.innerHTML = this.renderForm(tempProfile);
            // Restore name
            const newNameInput = document.getElementById('pm-name');
            if (newNameInput && currentName) {
                newNameInput.value = currentName;
            }
        }
    },
    
    handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Validate size (2MB max)
        if (file.size > 2 * 1024 * 1024) {
            alert('Image must be less than 2MB');
            return;
        }
        
        // Validate type
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }
        
        this.pendingImageFile = file;
        
        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
            this.pendingImagePreview = e.target.result;
            const preview = document.querySelector('.pm-avatar-preview');
            if (preview) {
                preview.innerHTML = `<img src="${e.target.result}" alt="Preview" />`;
            }
        };
        reader.readAsDataURL(file);
    },
    
    async uploadImage(profileId) {
        if (!this.pendingImageFile) return null;
        
        const formData = new FormData();
        formData.append('image', this.pendingImageFile);
        formData.append('profile_id', profileId);
        
        try {
            const response = await fetch('/api/profile/upload-image', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (result.success) {
                return result.imagePath;
            } else {
                console.error('[ProfileManager] Image upload failed:', result.error);
                return null;
            }
        } catch (e) {
            console.error('[ProfileManager] Image upload error:', e);
            return null;
        }
    },
    
    async saveFromForm() {
        const name = document.getElementById('pm-name')?.value || 'New Profile';
        const model = document.getElementById('pm-model')?.value;
        const apiKey = document.getElementById('pm-apikey')?.value;
        
        const activeBtn = document.querySelector('.pm-provider-btn--active');
        const provider = activeBtn 
            ? activeBtn.getAttribute('onclick').match(/'(\w+)'/)?.[1] 
            : 'google';
        
        if (this.editingProfileId) {
            // Update existing
            let imagePath = this.profiles.find(p => p.id === this.editingProfileId)?.imagePath;
            
            // Upload new image if pending
            if (this.pendingImageFile) {
                const uploadedPath = await this.uploadImage(this.editingProfileId);
                if (uploadedPath) imagePath = uploadedPath;
            }
            
            this.updateProfile(this.editingProfileId, { name, provider, model, apiKey, imagePath });
        } else {
            // Create new
            const newProfile = this.createProfile({ name, provider, model, apiKey });
            
            // Upload image if pending
            if (this.pendingImageFile) {
                const uploadedPath = await this.uploadImage(newProfile.id);
                if (uploadedPath) {
                    this.updateProfile(newProfile.id, { imagePath: uploadedPath });
                }
            }
        }
        
        this.showListView();
    },
    
    confirmDelete(id) {
        const profile = this.profiles.find(p => p.id === id);
        if (!profile) return;
        
        if (confirm(`Delete profile "${profile.name}"?`)) {
            this.deleteProfile(id);
            this.showListView();
        }
    },
    
    toggleKeyVisibility() {
        const input = document.getElementById('pm-apikey');
        if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    },
    
    async testConnection() {
        const profile = this.editingProfileId 
            ? this.profiles.find(p => p.id === this.editingProfileId)
            : null;
        
        const statusEl = document.getElementById('pm-connection-status');
        if (!statusEl) return;
        
        const apiKey = document.getElementById('pm-apikey')?.value;
        const model = document.getElementById('pm-model')?.value;
        const activeBtn = document.querySelector('.pm-provider-btn--active');
        const provider = activeBtn 
            ? activeBtn.getAttribute('onclick').match(/'(\w+)'/)?.[1] 
            : profile?.provider || 'google';
        
        statusEl.innerHTML = `
            <div class="pm-connection-test">
                <div class="pm-connection-test__indicator pm-connection-test__indicator--testing"></div>
                <div class="pm-connection-test__text">Testing connection...</div>
            </div>
        `;
        
        try {
            const response = await fetch('/api/profile/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, apiKey, model })
            });
            
            const result = await response.json();
            
            if (result.success) {
                statusEl.innerHTML = `
                    <div class="pm-connection-test">
                        <div class="pm-connection-test__indicator pm-connection-test__indicator--success"></div>
                        <div class="pm-connection-test__text pm-connection-test__text--success">
                            ✓ Connected (${result.latency}ms)
                        </div>
                    </div>
                `;
            } else {
                throw new Error(result.error || 'Connection failed');
            }
        } catch (e) {
            statusEl.innerHTML = `
                <div class="pm-connection-test">
                    <div class="pm-connection-test__indicator pm-connection-test__indicator--error"></div>
                    <div class="pm-connection-test__text pm-connection-test__text--error">
                        ✗ ${e.message}
                    </div>
                </div>
            `;
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EXPORT FOR OTHER COMPONENTS
    // ═══════════════════════════════════════════════════════════════════════
    
    getActiveConfig() {
        const profile = this.profiles.find(p => p.id === this.activeProfileId);
        if (!profile) return null;
        
        return {
            id: profile.id,
            provider: profile.provider,
            model: profile.model,
            apiKey: profile.apiKey
        };
    },
    
    /**
     * Update profile stats (called by trading engine)
     * @param {string} profileId 
     * @param {object} stats { netProfit, totalLots, profitFactor }
     */
    updateStats(profileId, stats) {
        const profile = this.profiles.find(p => p.id === profileId);
        if (!profile) return;
        
        profile.stats = { ...profile.stats, ...stats };
        this.sortProfilesByNorthStar();
        this.saveProfiles();
        
        if (this.currentView === 'list') {
            this.render();
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // CONTEXT MENU
    // ═══════════════════════════════════════════════════════════════════════
    
    showContextMenu(event, profileId) {
        // Remove any existing context menu
        this.hideContextMenu();
        
        const profile = this.profiles.find(p => p.id === profileId);
        if (!profile) return;
        
        const menu = document.createElement('div');
        menu.className = 'pm-context-menu';
        menu.id = 'pm-context-menu';
        menu.innerHTML = `
            <div class="pm-context-menu__item" onclick="ProfileManager.quickRename('${profileId}')">
                <span>✏️</span> Rename
            </div>
            <div class="pm-context-menu__item" onclick="ProfileManager.quickChangeImage('${profileId}')">
                <span>🖼️</span> Change Image
            </div>
            <div class="pm-context-menu__divider"></div>
            <div class="pm-context-menu__item" onclick="ProfileManager.showEditForm('${profileId}'); ProfileManager.hideContextMenu();">
                <span>⚙️</span> Edit Profile
            </div>
            ${profile.status !== 'active' ? `
                <div class="pm-context-menu__item" onclick="ProfileManager.setActiveProfile('${profileId}'); ProfileManager.hideContextMenu();">
                    <span>✓</span> Set Active
                </div>
            ` : ''}
            <div class="pm-context-menu__divider"></div>
            <div class="pm-context-menu__item pm-context-menu__item--danger" onclick="ProfileManager.confirmDelete('${profileId}'); ProfileManager.hideContextMenu();">
                <span>🗑️</span> Delete
            </div>
        `;
        
        // Position menu at cursor
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        
        document.body.appendChild(menu);
        
        // Close menu on click outside
        setTimeout(() => {
            document.addEventListener('click', this.hideContextMenu, { once: true });
        }, 10);
    },
    
    hideContextMenu() {
        const menu = document.getElementById('pm-context-menu');
        if (menu) menu.remove();
    },
    
    quickRename(profileId) {
        this.hideContextMenu();
        const profile = this.profiles.find(p => p.id === profileId);
        if (!profile) return;
        
        const newName = prompt('Enter new profile name:', profile.name);
        if (newName && newName.trim() !== '') {
            this.updateProfile(profileId, { name: newName.trim() });
            this.render();
        }
    },
    
    quickChangeImage(profileId) {
        this.hideContextMenu();
        
        // Create a temporary file input
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = async (event) => {
            const file = event.target.files[0];
            if (!file) return;
            
            // Validate
            if (file.size > 2 * 1024 * 1024) {
                alert('Image must be less than 2MB');
                return;
            }
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file');
                return;
            }
            
            // Upload directly
            const formData = new FormData();
            formData.append('image', file);
            formData.append('profile_id', profileId);
            
            try {
                const response = await fetch('/api/profile/upload-image', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (result.success) {
                    this.updateProfile(profileId, { imagePath: result.imagePath });
                    this.render();
                    console.log('[ProfileManager] Image updated:', result.imagePath);
                } else {
                    alert('Failed to upload image: ' + result.error);
                }
            } catch (e) {
                console.error('[ProfileManager] Image upload error:', e);
                alert('Failed to upload image');
            }
        };
        input.click();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only init if container exists
    if (document.getElementById('profile-manager')) {
        ProfileManager.init();
    }
});

// Expose to window
window.ProfileManager = ProfileManager;
