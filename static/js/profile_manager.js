/* ═══════════════════════════════════════════════════════════════════════════
   APEX PROFILE MANAGER V1.0
   
   Manages API profiles for sentiment engine
   - Stores profiles in localStorage
   - Supports Anthropic, Google, OpenAI
   - Test connection functionality
   ═══════════════════════════════════════════════════════════════════════════ */

const ProfileManager = {
    
    // ═══════════════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════════════
    
    profiles: [],
    activeProfileId: null,
    selectedProfileId: null,
    currentTab: 'config', // 'config' | 'stats'
    
    // Provider configurations
    providers: {
        anthropic: {
            name: 'Anthropic',
            icon: 'A',
            models: [
                { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', default: true },
                { id: 'claude-opus-4-20250514', name: 'Claude Opus 4' },
                { id: 'claude-haiku-4-20250514', name: 'Claude Haiku 4' }
            ],
            keyPrefix: 'sk-ant-',
            keyPlaceholder: 'sk-ant-api03-...'
        },
        google: {
            name: 'Google AI',
            icon: 'G',
            models: [
                { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', default: true },
                { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
                { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
            ],
            keyPrefix: 'AIza',
            keyPlaceholder: 'AIza...'
        },
        openai: {
            name: 'OpenAI',
            icon: 'O',
            models: [
                { id: 'gpt-4o', name: 'GPT-4o', default: true },
                { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
                { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' }
            ],
            keyPrefix: 'sk-',
            keyPlaceholder: 'sk-proj-...'
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════
    
    init() {
        this.loadProfiles();
        this.render();
        this.bindEvents();
        console.log('[ProfileManager] Initialized with', this.profiles.length, 'profiles');
    },
    
    loadProfiles() {
        try {
            const stored = localStorage.getItem('apex_profiles');
            this.profiles = stored ? JSON.parse(stored) : [];
            
            const activeId = localStorage.getItem('apex_active_profile');
            if (activeId && this.profiles.find(p => p.id === activeId)) {
                this.activeProfileId = activeId;
            }
        } catch (e) {
            console.error('[ProfileManager] Failed to load profiles:', e);
            this.profiles = [];
        }
    },
    
    saveProfiles() {
        try {
            localStorage.setItem('apex_profiles', JSON.stringify(this.profiles));
            if (this.activeProfileId) {
                localStorage.setItem('apex_active_profile', this.activeProfileId);
            }
        } catch (e) {
            console.error('[ProfileManager] Failed to save profiles:', e);
        }
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
            status: 'inactive',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            stats: {
                totalCalls: 0,
                successRate: 0,
                avgLatency: 0,
                lastUsed: null
            },
            config: {
                maxTokens: 1500,
                temperature: 0.7,
                screenshotRegion: null,
                schedule: {
                    tf15m: [1, 16, 31, 46],
                    tf1mInterval: 2
                }
            }
        };
        
        this.profiles.push(profile);
        this.saveProfiles();
        this.selectedProfileId = profile.id;
        this.render();
        
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
        
        this.saveProfiles();
        this.render();
        
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
            this.selectedProfileId = this.profiles[0]?.id || null;
        }
        
        this.saveProfiles();
        this.render();
        
        return true;
    },
    
    setActiveProfile(id) {
        const profile = this.profiles.find(p => p.id === id);
        if (!profile) return false;
        
        // Deactivate all others
        this.profiles.forEach(p => p.status = 'inactive');
        
        // Activate this one
        profile.status = 'active';
        this.activeProfileId = id;
        
        this.saveProfiles();
        this.render();
        
        // Notify sentiment engine (will be wired later)
        this.notifyProfileChange(profile);
        
        return true;
    },
    
    getDefaultModel(provider) {
        const providerConfig = this.providers[provider];
        if (!providerConfig) return null;
        const defaultModel = providerConfig.models.find(m => m.default);
        return defaultModel ? defaultModel.id : providerConfig.models[0].id;
    },
    
    getSelectedProfile() {
        return this.profiles.find(p => p.id === this.selectedProfileId);
    },
    
    getActiveProfile() {
        return this.profiles.find(p => p.id === this.activeProfileId);
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // RENDER
    // ═══════════════════════════════════════════════════════════════════════
    
    render() {
        const container = document.getElementById('profile-manager');
        if (!container) return;
        
        container.innerHTML = `
            <div class="pm-panel">
                <div class="pm-panel__header">
                    <div class="pm-panel__title">Profiles</div>
                    <button class="pm-btn pm-btn--small pm-btn--primary" onclick="ProfileManager.showCreateForm()">
                        + New
                    </button>
                </div>
                <div class="pm-panel__content">
                    ${this.renderProfileList()}
                </div>
            </div>
            
            <div class="pm-panel">
                <div class="pm-panel__header">
                    <div class="pm-panel__title">${this.selectedProfileId ? 'Edit Profile' : 'Create Profile'}</div>
                </div>
                <div class="pm-panel__content">
                    ${this.renderProfileForm()}
                </div>
            </div>
            
            <div class="pm-panel">
                <div class="pm-panel__header">
                    <div class="pm-tabs">
                        <button class="pm-tab ${this.currentTab === 'config' ? 'pm-tab--active' : ''}" 
                                onclick="ProfileManager.switchTab('config')">Config</button>
                        <button class="pm-tab ${this.currentTab === 'stats' ? 'pm-tab--active' : ''}" 
                                onclick="ProfileManager.switchTab('stats')">Stats</button>
                    </div>
                </div>
                <div class="pm-panel__content">
                    ${this.currentTab === 'config' ? this.renderJsonConfig() : this.renderStats()}
                </div>
            </div>
        `;
    },
    
    renderProfileList() {
        if (this.profiles.length === 0) {
            return `
                <div class="pm-empty">
                    <div class="pm-empty__icon">🔑</div>
                    <div class="pm-empty__text">No profiles yet</div>
                    <div class="pm-empty__hint">Create a profile to connect your API</div>
                </div>
            `;
        }
        
        return `
            <div class="pm-profile-list">
                ${this.profiles.map(profile => this.renderProfileCard(profile)).join('')}
            </div>
        `;
    },
    
    renderProfileCard(profile) {
        const provider = this.providers[profile.provider];
        const isSelected = profile.id === this.selectedProfileId;
        const isActive = profile.status === 'active';
        
        return `
            <div class="pm-profile-card ${isSelected ? 'pm-profile-card--active' : ''}" 
                 onclick="ProfileManager.selectProfile('${profile.id}')">
                <div class="pm-profile-card__header">
                    <div class="pm-profile-card__name">${profile.name}</div>
                    <div class="pm-profile-card__status pm-profile-card__status--${isActive ? 'active' : 'inactive'}">
                        ${isActive ? '● Active' : 'Inactive'}
                    </div>
                </div>
                <div class="pm-profile-card__meta">
                    <div class="pm-profile-card__provider">
                        <div class="pm-profile-card__provider-icon pm-profile-card__provider-icon--${profile.provider}">
                            ${provider?.icon || '?'}
                        </div>
                        <span>${provider?.name || profile.provider}</span>
                    </div>
                    <span>${this.getModelShortName(profile.model)}</span>
                </div>
            </div>
        `;
    },
    
    renderProfileForm() {
        const profile = this.getSelectedProfile();
        const provider = profile?.provider || 'google';
        const providerConfig = this.providers[provider];
        
        return `
            <div class="pm-form">
                <div class="pm-form-group">
                    <label class="pm-label">Profile Name</label>
                    <input type="text" class="pm-input" id="pm-name" 
                           value="${profile?.name || ''}" 
                           placeholder="My Sentiment Profile">
                </div>
                
                <div class="pm-form-group">
                    <label class="pm-label">Provider</label>
                    <div class="pm-provider-select">
                        ${Object.entries(this.providers).map(([key, prov]) => `
                            <button class="pm-provider-btn ${provider === key ? 'pm-provider-btn--active' : ''}"
                                    onclick="ProfileManager.selectProvider('${key}')">
                                <div class="pm-provider-btn__icon pm-provider-btn__icon--${key}">${prov.icon}</div>
                                <div class="pm-provider-btn__label">${prov.name}</div>
                            </button>
                        `).join('')}
                    </div>
                </div>
                
                <div class="pm-form-group">
                    <label class="pm-label">Model</label>
                    <select class="pm-select" id="pm-model">
                        ${providerConfig.models.map(model => `
                            <option value="${model.id}" ${profile?.model === model.id ? 'selected' : ''}>
                                ${model.name}
                            </option>
                        `).join('')}
                    </select>
                </div>
                
                <div class="pm-form-group">
                    <label class="pm-label">API Key</label>
                    <div class="pm-key-field">
                        <input type="password" class="pm-input pm-input--password" id="pm-apikey"
                               value="${profile?.apiKey || ''}"
                               placeholder="${providerConfig.keyPlaceholder}">
                        <button class="pm-key-toggle" onclick="ProfileManager.toggleKeyVisibility()">👁</button>
                    </div>
                </div>
                
                <div id="pm-connection-status"></div>
                
                <div class="pm-btn-group">
                    ${profile ? `
                        <button class="pm-btn pm-btn--primary" onclick="ProfileManager.saveProfile()">
                            Save Changes
                        </button>
                        <button class="pm-btn pm-btn--secondary" onclick="ProfileManager.testConnection()">
                            Test
                        </button>
                        ${profile.status !== 'active' ? `
                            <button class="pm-btn pm-btn--secondary" onclick="ProfileManager.setActiveProfile('${profile.id}')">
                                Activate
                            </button>
                        ` : ''}
                        <button class="pm-btn pm-btn--danger pm-btn--small" onclick="ProfileManager.confirmDelete('${profile.id}')">
                            🗑
                        </button>
                    ` : `
                        <button class="pm-btn pm-btn--primary" onclick="ProfileManager.createFromForm()">
                            Create Profile
                        </button>
                    `}
                </div>
            </div>
        `;
    },
    
    renderJsonConfig() {
        const profile = this.getSelectedProfile();
        
        if (!profile) {
            return `
                <div class="pm-empty">
                    <div class="pm-empty__text">Select a profile to view config</div>
                </div>
            `;
        }
        
        const config = {
            id: profile.id,
            name: profile.name,
            provider: profile.provider,
            model: profile.model,
            apiKey: profile.apiKey ? '***' + profile.apiKey.slice(-4) : null,
            config: profile.config
        };
        
        return `
            <div class="pm-json-editor">
                <pre>${this.syntaxHighlight(JSON.stringify(config, null, 2))}</pre>
            </div>
        `;
    },
    
    renderStats() {
        const profile = this.getSelectedProfile();
        
        if (!profile) {
            return `
                <div class="pm-empty">
                    <div class="pm-empty__text">Select a profile to view stats</div>
                </div>
            `;
        }
        
        const stats = profile.stats || {};
        
        return `
            <div class="pm-stats">
                <div class="pm-stat-card">
                    <div class="pm-stat-card__label">Total API Calls</div>
                    <div class="pm-stat-card__value pm-stat-card__value--teal">${stats.totalCalls || 0}</div>
                </div>
                <div class="pm-stat-card">
                    <div class="pm-stat-card__label">Success Rate</div>
                    <div class="pm-stat-card__value pm-stat-card__value--mint">${stats.successRate || 0}%</div>
                </div>
                <div class="pm-stat-card">
                    <div class="pm-stat-card__label">Avg Latency</div>
                    <div class="pm-stat-card__value">${stats.avgLatency || 0}ms</div>
                </div>
                <div class="pm-stat-card">
                    <div class="pm-stat-card__label">Last Used</div>
                    <div class="pm-stat-card__sub">${stats.lastUsed ? this.formatTime(stats.lastUsed) : 'Never'}</div>
                </div>
            </div>
        `;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EVENTS & ACTIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    bindEvents() {
        // Keyboard shortcuts, etc.
    },
    
    selectProfile(id) {
        this.selectedProfileId = id;
        this.render();
    },
    
    selectProvider(provider) {
        const profile = this.getSelectedProfile();
        if (profile) {
            profile.provider = provider;
            profile.model = this.getDefaultModel(provider);
        }
        this.render();
    },
    
    showCreateForm() {
        this.selectedProfileId = null;
        this.render();
    },
    
    createFromForm() {
        const name = document.getElementById('pm-name')?.value || 'New Profile';
        const model = document.getElementById('pm-model')?.value;
        const apiKey = document.getElementById('pm-apikey')?.value;
        
        // Determine provider from selected button
        const activeBtn = document.querySelector('.pm-provider-btn--active');
        const provider = activeBtn ? activeBtn.getAttribute('onclick').match(/'(\w+)'/)[1] : 'google';
        
        this.createProfile({ name, provider, model, apiKey });
    },
    
    saveProfile() {
        const profile = this.getSelectedProfile();
        if (!profile) return;
        
        const name = document.getElementById('pm-name')?.value;
        const model = document.getElementById('pm-model')?.value;
        const apiKey = document.getElementById('pm-apikey')?.value;
        
        // Get provider from active button
        const activeBtn = document.querySelector('.pm-provider-btn--active');
        const provider = activeBtn ? activeBtn.getAttribute('onclick').match(/'(\w+)'/)[1] : profile.provider;
        
        this.updateProfile(profile.id, { name, provider, model, apiKey });
    },
    
    confirmDelete(id) {
        const profile = this.profiles.find(p => p.id === id);
        if (!profile) return;
        
        if (confirm(`Delete profile "${profile.name}"?`)) {
            this.deleteProfile(id);
        }
    },
    
    switchTab(tab) {
        this.currentTab = tab;
        this.render();
    },
    
    toggleKeyVisibility() {
        const input = document.getElementById('pm-apikey');
        if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    },
    
    async testConnection() {
        const profile = this.getSelectedProfile();
        if (!profile) return;
        
        const statusEl = document.getElementById('pm-connection-status');
        if (!statusEl) return;
        
        // Get current form values
        const apiKey = document.getElementById('pm-apikey')?.value;
        const model = document.getElementById('pm-model')?.value;
        
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
                body: JSON.stringify({
                    provider: profile.provider,
                    apiKey: apiKey,
                    model: model
                })
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
    
    notifyProfileChange(profile) {
        // Dispatch custom event for other components to listen
        window.dispatchEvent(new CustomEvent('apex:profile:change', {
            detail: { profile }
        }));
        
        console.log('[ProfileManager] Active profile changed:', profile.name);
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════════════════
    
    getModelShortName(modelId) {
        if (!modelId) return '';
        
        // Extract meaningful part
        if (modelId.includes('claude')) return modelId.split('-').slice(0, 2).join(' ');
        if (modelId.includes('gemini')) return modelId.replace('gemini-', 'Gemini ');
        if (modelId.includes('gpt')) return modelId.toUpperCase();
        
        return modelId;
    },
    
    formatTime(isoString) {
        if (!isoString) return 'Never';
        const date = new Date(isoString);
        return date.toLocaleString();
    },
    
    syntaxHighlight(json) {
        return json
            .replace(/("[\w-]+")\s*:/g, '<span class="pm-json-key">$1</span>:')
            .replace(/:\s*(".*?")/g, ': <span class="pm-json-string">$1</span>')
            .replace(/:\s*(\d+\.?\d*)/g, ': <span class="pm-json-number">$1</span>')
            .replace(/:\s*(true|false|null)/g, ': <span class="pm-json-bool">$1</span>');
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EXPORT FOR SENTIMENT ENGINE
    // ═══════════════════════════════════════════════════════════════════════
    
    getActiveConfig() {
        const profile = this.getActiveProfile();
        if (!profile) return null;
        
        return {
            provider: profile.provider,
            model: profile.model,
            apiKey: profile.apiKey,
            config: profile.config
        };
    }
};

// Auto-init when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ProfileManager.init();
});
