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
        console.log('[ProfileManager] V2 Initialized (DB-backed)');
    },
    
    async loadProfiles() {
        try {
            const response = await fetch('/api/profile/list');
            const result = await response.json();
            
            if (result.success) {
                this.profiles = result.profiles.map(p => {
                    // Merge API key from localStorage (never stored in DB)
                    const localKey = localStorage.getItem(`apex_apikey_${p.id}`) || '';
                    return { ...p, apiKey: localKey };
                });
            } else {
                console.error('[ProfileManager] Failed to load from DB:', result.error);
                this.profiles = [];
            }
            
            const activeId = localStorage.getItem('apex_active_profile');
            if (activeId && this.profiles.find(p => p.id === activeId)) {
                this.activeProfileId = activeId;
                const active = this.profiles.find(p => p.id === activeId);
                if (active) active.status = 'active';
            }
            
            this.sortProfilesByNorthStar();
            this.render();
        } catch (e) {
            console.error('[ProfileManager] Failed to load profiles:', e);
            this.profiles = [];
            this.render();
        }
    },
    
    saveApiKeyLocally(profileId, apiKey) {
        /* API keys stay in localStorage only — never sent to DB */
        if (apiKey) {
            localStorage.setItem(`apex_apikey_${profileId}`, apiKey);
        }
    },
    
    saveActiveProfileLocally() {
        if (this.activeProfileId) {
            localStorage.setItem('apex_active_profile', this.activeProfileId);
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
        // DB uses snake_case, legacy used camelCase nested stats object
        const netProfit = profile.total_pnl || profile.stats?.netProfit || 0;
        const totalLots = profile.total_lots || profile.stats?.totalLots || 0;
        const profitFactor = profile.profit_factor || profile.stats?.profitFactor || 0;
        
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
    
    async createProfile(data) {
        try {
            const payload = {
                name: data.name || 'New Profile',
                symbol: data.symbol || this.getCurrentSymbol(),
                provider: data.provider || 'google',
                sentiment_model: data.model || this.getDefaultModel(data.provider || 'google'),
            };
            
            // Include trading_config if provided
            if (data.trading_config) {
                payload.trading_config = data.trading_config;
            }
            
            const response = await fetch('/api/profile/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            
            const profile = { ...result.profile, apiKey: data.apiKey || '' };
            
            // Store API key locally
            this.saveApiKeyLocally(profile.id, data.apiKey);
            
            this.profiles.push(profile);
            this.sortProfilesByNorthStar();
            
            console.log('[ProfileManager] Created profile:', profile.name, profile.id);
            return profile;
        } catch (e) {
            console.error('[ProfileManager] Create failed:', e);
            return null;
        }
    },
    
    /** Get the current symbol from the active tab or default */
    getCurrentSymbol() {
        // Try ApexTabs active symbol
        if (typeof ApexTabs !== 'undefined' && ApexTabs.activeTab) {
            return ApexTabs.activeTab.toUpperCase();
        }
        // Try active symbol global
        if (typeof ACTIVE_SYMBOL !== 'undefined') {
            return ACTIVE_SYMBOL;
        }
        return 'XAUJ26';
    },
    
    async updateProfile(id, updates) {
        try {
            // Separate API key from DB updates
            if (updates.apiKey !== undefined) {
                this.saveApiKeyLocally(id, updates.apiKey);
            }
            
            // Map frontend field names to DB field names
            const dbUpdates = {};
            if (updates.name) dbUpdates.name = updates.name;
            if (updates.provider) dbUpdates.provider = updates.provider;
            if (updates.model) dbUpdates.sentiment_model = updates.model;
            if (updates.imagePath) dbUpdates.image_path = updates.imagePath;
            if (updates.image_path) dbUpdates.image_path = updates.image_path;
            if (updates.symbol) dbUpdates.symbol = updates.symbol;
            if (updates.trading_config) dbUpdates.trading_config = updates.trading_config;
            
            // Only call API if there are DB-level updates
            if (Object.keys(dbUpdates).length > 0) {
                const response = await fetch(`/api/profile/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dbUpdates)
                });
                
                const result = await response.json();
                if (!result.success) throw new Error(result.error);
            }
            
            // Update local cache
            const index = this.profiles.findIndex(p => p.id === id);
            if (index !== -1) {
                this.profiles[index] = {
                    ...this.profiles[index],
                    ...updates,
                    updatedAt: new Date().toISOString()
                };
            }
            
            this.sortProfilesByNorthStar();
            return this.profiles[index] || null;
        } catch (e) {
            console.error('[ProfileManager] Update failed:', e);
            return null;
        }
    },
    
    async deleteProfile(id) {
        try {
            const response = await fetch(`/api/profile/${id}`, { method: 'DELETE' });
            const result = await response.json();
            if (!result.success) throw new Error(result.error);
            
            // Clean up localStorage
            localStorage.removeItem(`apex_apikey_${id}`);
            
            const index = this.profiles.findIndex(p => p.id === id);
            if (index !== -1) this.profiles.splice(index, 1);
            
            if (this.activeProfileId === id) {
                this.activeProfileId = null;
            }
            if (this.selectedProfileId === id) {
                this.selectedProfileId = null;
            }
            
            console.log('[ProfileManager] Deleted profile:', id);
            return true;
        } catch (e) {
            console.error('[ProfileManager] Delete failed:', e);
            return false;
        }
    },
    
    setActiveProfile(id) {
        const profile = this.profiles.find(p => p.id === id);
        if (!profile) return false;
        
        this.profiles.forEach(p => p.status = 'inactive');
        profile.status = 'active';
        this.activeProfileId = id;
        
        this.saveActiveProfileLocally();
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
        
        // When entering form view, auto-switch right panel to Config tab (Seed 22)
        if (isFormView && typeof ApexViewRenderer !== 'undefined') {
            setTimeout(() => {
                ApexViewRenderer.switchDetailsTab('config');
                ApexViewRenderer.updateProfileDetails();
            }, 50);
        }
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
        const modelId = profile.sentiment_model || profile.model;
        const modelShort = this.getModelShortName(profile.provider, modelId);
        const imageSrc = profile.image_path || profile.imagePath;
        
        return `
            <div class="pm-profile-row ${isSelected ? 'pm-profile-row--selected' : ''} ${isActive ? 'pm-profile-row--active' : ''}"
                 onclick="ProfileManager.selectProfile('${profile.id}')"
                 ondblclick="ProfileManager.showEditForm('${profile.id}')"
                 oncontextmenu="event.preventDefault(); ProfileManager.showContextMenu(event, '${profile.id}')">
                
                <div class="pm-avatar-container">
                    ${imageSrc 
                        ? `<img class="pm-avatar" src="${imageSrc}" alt="${profile.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
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
        const imageSrc = this.pendingImagePreview || profile?.image_path || profile?.imagePath;
        const currentModel = profile?.sentiment_model || profile?.model;
        
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
                
                <!-- Asset / Symbol -->
                <div class="pm-form-group">
                    <label class="pm-label">Asset</label>
                    <select class="pm-select" id="pm-symbol" onclick="event.stopPropagation()">
                        ${['XAUJ26', 'US100H26', 'US30H26', 'US500H26', 'BTCF26', 'USOILH26'].map(s => {
                            const names = { XAUJ26: 'Gold (XAUJ26)', US100H26: 'US100 (NAS)', US30H26: 'US30 (DOW)', US500H26: 'US500 (SPX)', BTCF26: 'BTC', USOILH26: 'Oil (CL)' };
                            const selected = (profile?.symbol || this.getCurrentSymbol()) === s ? 'selected' : '';
                            return `<option value="${s}" ${selected}>${names[s] || s}</option>`;
                        }).join('')}
                    </select>
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
                            <option value="${model.id}" ${currentModel === model.id ? 'selected' : ''}>
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
        const symbol = document.getElementById('pm-symbol')?.value || this.getCurrentSymbol();
        
        const activeBtn = document.querySelector('.pm-provider-btn--active');
        const provider = activeBtn 
            ? activeBtn.getAttribute('onclick').match(/'(\w+)'/)?.[1] 
            : 'google';
        
        // Read trading config from the structured panel
        let trading_config = null;
        if (typeof TradingConfigPanel !== 'undefined') {
            trading_config = TradingConfigPanel.getConfig();
        }
        
        if (this.editingProfileId) {
            // Update existing
            let imagePath = this.profiles.find(p => p.id === this.editingProfileId)?.imagePath 
                         || this.profiles.find(p => p.id === this.editingProfileId)?.image_path;
            
            // Upload new image if pending
            if (this.pendingImageFile) {
                const uploadedPath = await this.uploadImage(this.editingProfileId);
                if (uploadedPath) imagePath = uploadedPath;
            }
            
            const updates = { name, provider, model, apiKey, symbol, image_path: imagePath };
            if (trading_config) updates.trading_config = trading_config;
            await this.updateProfile(this.editingProfileId, updates);
        } else {
            // Create new
            const createData = { name, provider, model, apiKey, symbol };
            if (trading_config) createData.trading_config = trading_config;
            const newProfile = await this.createProfile(createData);
            
            // Upload image if pending
            if (newProfile && this.pendingImageFile) {
                const uploadedPath = await this.uploadImage(newProfile.id);
                if (uploadedPath) {
                    await this.updateProfile(newProfile.id, { image_path: uploadedPath });
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
    
    /** Parse trading config from a profile into a plain object */
    _parseProfileTradingConfig(profile) {
        const fallback = (typeof TorraTraderBridge !== 'undefined')
            ? TorraTraderBridge.DEFAULT_TRADING_CONFIG
            : { sentiment_weights: {}, timeframe_weights: {}, thresholds: {}, risk: {} };
        if (!profile) return { ...fallback };
        let tc = profile.trading_config;
        if (tc) {
            try {
                const parsed = typeof tc === 'string' ? JSON.parse(tc) : tc;
                if (parsed.sentiment_weights) return parsed;
            } catch (e) { /* fall through */ }
        }
        return { ...fallback };
    },

    getActiveConfig() {
        const profile = this.profiles.find(p => p.id === this.activeProfileId);
        if (!profile) return null;
        
        // Parse trading_config from DB (stored as JSON string)
        let tradingConfig = null;
        try {
            if (typeof profile.trading_config === 'string') {
                tradingConfig = JSON.parse(profile.trading_config);
            } else if (typeof profile.trading_config === 'object' && profile.trading_config) {
                tradingConfig = profile.trading_config;
            }
        } catch (e) { /* ignore parse errors */ }
        
        return {
            id: profile.id,
            symbol: profile.symbol,
            provider: profile.provider,
            model: profile.sentiment_model || profile.model,
            apiKey: profile.apiKey || localStorage.getItem(`apex_apikey_${profile.id}`) || '',
            tradingConfig: tradingConfig
        };
    },
    
    /**
     * Update profile stats (called by trading engine)
     * Persists to DB via PATCH
     * @param {string} profileId 
     * @param {object} stats { total_pnl, total_lots, profit_factor, ... }
     */
    async updateStats(profileId, stats) {
        try {
            await this.updateProfile(profileId, stats);
            
            // Update local cache
            const profile = this.profiles.find(p => p.id === profileId);
            if (profile) {
                Object.assign(profile, stats);
            }
            
            this.sortProfilesByNorthStar();
            
            if (this.currentView === 'list') {
                this.render();
            }
        } catch (e) {
            console.error('[ProfileManager] Stats update failed:', e);
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

// ═══════════════════════════════════════════════════════════════════
// AUTO-SAVE: Config panel changes → DB (debounced)
// ═══════════════════════════════════════════════════════════════════

let _configSaveTimer = null;
window.addEventListener('tcp:change', (e) => {
    // Debounce: save 800ms after last change
    if (_configSaveTimer) clearTimeout(_configSaveTimer);
    _configSaveTimer = setTimeout(async () => {
        const profileId = ProfileManager.editingProfileId || ProfileManager.activeProfileId;
        if (!profileId) return;
        
        const config = e.detail?.config;
        if (!config) return;
        
        try {
            await ProfileManager.updateProfile(profileId, { trading_config: config });
            
            // Visual feedback
            const badge = document.getElementById('tcp-save-badge');
            if (badge) {
                badge.textContent = 'Saved \u2713';
                badge.classList.add('tcp-save-badge--visible');
                setTimeout(() => badge.classList.remove('tcp-save-badge--visible'), 2000);
            }
            console.log('[TCP] Auto-saved config to profile', profileId);
        } catch (err) {
            console.error('[TCP] Auto-save failed:', err);
        }
    }, 800);
});

// Expose to window
window.ProfileManager = ProfileManager;
