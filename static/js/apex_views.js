/* ═══════════════════════════════════════════════════════════════════════════
   APEX VIEWS V3.5 - 4-Quadrant Database Layout + Profile Controller
   
   Database Layout:
   ┌──────────────────────┬──────────────────────┐
   │ Q1: Profile Manager  │ Q2: Profile Details  │  ← View Panel (Top 50%)
   │ (Ranks/Create)       │ (Stats/Config JSON)  │
   ├──────────────────────┼──────────────────────┤
   │ Q3: Instance Browser │ Q4: Data Table       │  ← Control Center (Bottom 50%)
   │ (Algorithms List)    │ (CORE/BASIC/etc)     │
   └──────────────────────┴──────────────────────┘
   
   Trading View Profile Controller:
   - Orb shows: Profile image + Time overlay + Rank badge (gold/silver/bronze/matte)
   - Arrow buttons: Pause execution & switch profile by rank
   - Click orb: Swap calendar with Profile Directory
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexViewRenderer = {
    viewPanel: null,
    controlBody: null,
    charts: { '15m': null, '1h': null },
    chartData: { '15m': null, '1h': null },
    matrices: { '15m': null, '1h': null },
    calendar: null,
    replayTime: 0,
    clockInterval: null,
    refreshIntervals: { '15m': null, '1h': null },
    replayMode: 'inactive',
    activeSymbol: 'XAUJ26',
    availableSymbols: [],
    priceRange: { min: null, max: null },
    
    // Mode states
    isTraderRunning: false,
    isReplayRunning: false,
    
    // Calendar state
    calendarDate: new Date(),
    calendarStartDate: null,
    calendarEndDate: null,
    calendarStartTime: '00:00:00',
    calendarEndTime: '23:59:59',
    
    // Performance data
    dayPerformance: {},
    
    // Database view state
    profiles: [],
    currentSource: 'profiles',
    currentTable: 'core',
    currentTimeframe: '15m',
    hyperspheres: [],
    selectedProfileId: null,
    currentDetailsTab: 'stats',
    
    // Trading view profile controller state
    tradingProfileId: null,
    tradingProfileIndex: 0,
    showProfileDirectory: false,
    
    init() {
        this.viewPanel = document.getElementById('view-panel-content');
        this.controlBody = document.getElementById('control-center-body');
        this.loadSymbols();
        this.generateMockPerformanceData();
        ApexState.subscribe(state => this.onStateChange(state));
        this.onStateChange(ApexState.getState());
        
        // Listen for profile selection events
        window.addEventListener('apex:profile:selected', (e) => {
            this.selectedProfileId = e.detail.profileId;
            this.updateProfileDetails();
        });
        
        // Listen for trading profile selection (from directory in trading view)
        window.addEventListener('apex:trading:profile:selected', (e) => {
            this.selectTradingProfile(e.detail.profileId);
        });
        
        window.addEventListener('apex-chart-refresh', (e) => {
            const tf = e.detail.timeframe;
            // Re-fetch data with new bar count from API
            const symbolKey = this.activeSymbol;
            this.loadChartData(tf, false, symbolKey);
        });
    },
    
    generateMockPerformanceData() {
        const today = new Date();
        for (let i = 0; i < 60; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const key = this.getDateKey(date);
            this.dayPerformance[key] = Math.random() * 0.75 + 0.2;
        }
    },
    
    getDateKey(date) {
        return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
    },
    
    async loadSymbols() {
        try {
            const response = await fetch('/api/symbols');
            const result = await response.json();
            if (result.success) {
                this.availableSymbols = result.symbols;
                this.activeSymbol = result.active_symbol;
            }
        } catch (e) {
            console.warn('[APEX] Failed to load symbols:', e.message);
        }
    },
    
    async loadProfiles(symbolId) {
        try {
            const response = await fetch(`/api/profiles?symbol=${symbolId}`);
            const result = await response.json();
            if (result.success) this.profiles = result.profiles || [];
        } catch (e) {
            this.profiles = [];
        }
    },
    
    async loadHyperspheres(symbolId) {
        try {
            const response = await fetch(`/api/hyperspheres?symbol=${symbolId}`);
            const result = await response.json();
            if (result.success) this.hyperspheres = result.hyperspheres || [];
        } catch (e) {
            this.hyperspheres = [];
        }
    },
    
    onStateChange(state) {
        const activeTab = state.tabs.find(t => t.id === state.activeTabId);
        if (!activeTab) {
            this.renderEmptyState();
            return;
        }
        
        if (activeTab.instanceType === 'trading') {
            this.renderTradingView(activeTab);
        } else if (activeTab.instanceType === 'metatron') {
            this.renderMetatronView(activeTab);
        } else {
            this.renderDatabaseView(activeTab);
        }
    },
    
    renderMetatronView(tab) {
        this.cleanup();
        // CytoBase is full-screen with its own control panel — hide Apex control center entirely
        this.viewPanel.innerHTML = `<iframe src="/cytobase" style="width: 100%; height: 100%; border: none; background: #0a0b0d;" title="CytoBase"></iframe>`;
        this.controlBody.innerHTML = '';
        
        // Hide the Apex control center + divider so CytoBase iframe fills full height
        const controlCenter = document.getElementById('apex-control-center');
        const divider = document.getElementById('apex-divider');
        const viewPanel = document.getElementById('apex-view-panel');
        if (controlCenter) controlCenter.style.display = 'none';
        if (divider) divider.style.display = 'none';
        if (viewPanel) viewPanel.style.flex = '1';
    },
    
    restoreApexLayout() {
        // Restore Apex control center + divider when leaving CytoBase
        const controlCenter = document.getElementById('apex-control-center');
        const divider = document.getElementById('apex-divider');
        const viewPanel = document.getElementById('apex-view-panel');
        if (controlCenter) controlCenter.style.display = '';
        if (divider) divider.style.display = '';
        if (viewPanel) viewPanel.style.flex = '';
    },

    renderEmptyState() {
        this.restoreApexLayout();
        this.viewPanel.innerHTML = `<div class="view-panel__placeholder"><div class="view-panel__placeholder-icon">◎</div><div class="view-panel__placeholder-text">Select a symbol database to view</div></div>`;
        this.controlBody.innerHTML = `<div class="control-center__placeholder">Click the APEX logo to open a database or trading view</div>`;
        this.cleanup();
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       DATABASE VIEW - 4-QUADRANT GRID
       ═══════════════════════════════════════════════════════════════════════ */
    async renderDatabaseView(tab) {
        this.cleanup();
        this.restoreApexLayout();
        const symbolKey = tab.dbKey || tab.instanceId || this.activeSymbol;
        this.activeSymbol = symbolKey;
        
        await Promise.all([this.loadProfiles(symbolKey), this.loadHyperspheres(symbolKey)]);
        
        this.viewPanel.innerHTML = `
            <div class="database-quadrant-grid">
                <div class="database-quadrant database-quadrant--profile">
                    <div class="profile-manager" id="profile-manager"></div>
                </div>
                <div class="database-quadrant database-quadrant--details">
                    <div class="profile-details" id="profile-details">
                        <div class="profile-details__header">
                            <div class="profile-details__tabs">
                                <button class="profile-details__tab ${this.currentDetailsTab === 'stats' ? 'profile-details__tab--active' : ''}" 
                                        data-tab="stats" onclick="ApexViewRenderer.switchDetailsTab('stats')">Stats</button>
                                <button class="profile-details__tab ${this.currentDetailsTab === 'config' ? 'profile-details__tab--active' : ''}" 
                                        data-tab="config" onclick="ApexViewRenderer.switchDetailsTab('config')">Config</button>
                            </div>
                        </div>
                        <div class="profile-details__content">
                            <div class="profile-details__page ${this.currentDetailsTab === 'stats' ? 'profile-details__page--active' : ''}" id="profile-stats-page">
                                ${this.renderProfileStatsContent()}
                            </div>
                            <div class="profile-details__page ${this.currentDetailsTab === 'config' ? 'profile-details__page--active' : ''}" id="profile-config-page">
                                ${this.renderProfileConfigContent()}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        if (typeof ProfileManager !== 'undefined') ProfileManager.init();
        
        this.controlBody.innerHTML = `
            <div class="database-quadrant-grid">
                <div class="database-quadrant database-quadrant--instances" id="instance-browser-panel"></div>
                <div class="database-quadrant database-quadrant--data">
                    <div class="database-panel__header">
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentTable === 'core' ? 'active' : ''}" data-table="core">CORE</button>
                            <button class="db-tab ${this.currentTable === 'basic' ? 'active' : ''}" data-table="basic">BASIC</button>
                            <button class="db-tab ${this.currentTable === 'advanced' ? 'active' : ''}" data-table="advanced">ADV</button>
                            <button class="db-tab ${this.currentTable === 'fibonacci' ? 'active' : ''}" data-table="fibonacci">FIB</button>
                            <button class="db-tab ${this.currentTable === 'ath' ? 'active' : ''}" data-table="ath">ATH</button>
                        </div>
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentTimeframe === '15m' ? 'active' : ''}" data-tf="15m">15M</button>
                            <button class="db-tab ${this.currentTimeframe === '1h' ? 'active' : ''}" data-tf="1h">1H</button>
                        </div>
                    </div>
                    <div class="database-panel__content" id="data-table-content"><div class="database-loading">Loading...</div></div>
                </div>
            </div>
        `;
        
        const instancePanel = document.getElementById('instance-browser-panel');
        if (instancePanel && typeof ApexInstanceBrowser !== 'undefined') {
            ApexInstanceBrowser.init(instancePanel, symbolKey);
        }
        
        this.initPanelControls();
        this.loadDataTable();
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       PROFILE DETAILS (Q2)
       ═══════════════════════════════════════════════════════════════════════ */
    
    switchDetailsTab(tab) {
        this.currentDetailsTab = tab;
        document.querySelectorAll('.profile-details__tab').forEach(btn => {
            btn.classList.toggle('profile-details__tab--active', btn.dataset.tab === tab);
        });
        document.querySelectorAll('.profile-details__page').forEach(page => {
            page.classList.remove('profile-details__page--active');
        });
        const activePage = document.getElementById(`profile-${tab}-page`);
        if (activePage) activePage.classList.add('profile-details__page--active');
    },
    
    renderProfileStatsContent() {
        const profile = this.getSelectedLocalProfile();
        if (!profile) {
            return `<div class="profile-stats__empty"><div class="profile-stats__empty-icon">📊</div><div>Select a profile to view stats</div></div>`;
        }
        const stats = profile.stats || {};
        const northStar = this.calculateNorthStar(profile);
        return `
            <div class="profile-stats"><div class="profile-stats__grid">
                <div class="profile-stat-card"><div class="profile-stat-card__label">North Star</div><div class="profile-stat-card__value profile-stat-card__value--positive">${northStar.toFixed(2)}</div></div>
                <div class="profile-stat-card"><div class="profile-stat-card__label">Net Profit</div><div class="profile-stat-card__value ${stats.netProfit >= 0 ? 'profile-stat-card__value--positive' : 'profile-stat-card__value--negative'}">$${(stats.netProfit || 0).toLocaleString()}</div></div>
                <div class="profile-stat-card"><div class="profile-stat-card__label">Total Signals</div><div class="profile-stat-card__value">${stats.totalLots || 0}</div></div>
                <div class="profile-stat-card"><div class="profile-stat-card__label">Profit Factor</div><div class="profile-stat-card__value">${(stats.profitFactor || 0).toFixed(2)}</div></div>
                <div class="profile-stat-card"><div class="profile-stat-card__label">API Calls</div><div class="profile-stat-card__value">${stats.totalCalls || 0}</div></div>
                <div class="profile-stat-card"><div class="profile-stat-card__label">Avg Latency</div><div class="profile-stat-card__value">${stats.avgLatency || 0}ms</div></div>
            </div></div>
        `;
    },
    
    renderProfileConfigContent() {
        const profile = this.getSelectedLocalProfile();
        if (!profile) {
            return `<div class="profile-config__empty"><div class="profile-stats__empty-icon">⚙️</div><div>Select a profile to view config</div></div>`;
        }
        const configJson = JSON.stringify({
            id: profile.id, name: profile.name, provider: profile.provider, model: profile.model,
            config: profile.config || { maxTokens: 1500, temperature: 0.7, schedule: { tf15m: [1, 16, 31, 46], tf1mInterval: 2 } }
        }, null, 2);
        return `
            <div class="profile-config"><div class="profile-config__editor"><div class="json-editor">
                <textarea class="json-editor__textarea" id="profile-config-editor" spellcheck="false"
                          onclick="event.stopPropagation()" onkeydown="event.stopPropagation()" oninput="ApexViewRenderer.onConfigChange()">${configJson}</textarea>
                <div class="json-editor__actions">
                    <span class="json-editor__status" id="config-status"></span>
                    <button type="button" class="json-editor__btn json-editor__btn--secondary" onclick="event.stopPropagation(); ApexViewRenderer.resetConfig()">Reset</button>
                    <button type="button" class="json-editor__btn" onclick="event.stopPropagation(); ApexViewRenderer.saveConfig()">Save Config</button>
                </div>
            </div></div></div>
        `;
    },
    
    getSelectedLocalProfile() {
        if (typeof ProfileManager !== 'undefined' && ProfileManager.selectedProfileId) {
            return ProfileManager.profiles.find(p => p.id === ProfileManager.selectedProfileId);
        }
        return null;
    },
    
    calculateNorthStar(profile) {
        const stats = profile.stats || {};
        const netProfit = stats.netProfit || 0;
        const totalLots = stats.totalLots || 0;
        const profitFactor = stats.profitFactor || 0;
        if (totalLots === 0 || profitFactor === 0) return 0;
        return (netProfit / totalLots) * profitFactor;
    },
    
    updateProfileDetails() {
        const statsPage = document.getElementById('profile-stats-page');
        const configPage = document.getElementById('profile-config-page');
        if (statsPage) statsPage.innerHTML = this.renderProfileStatsContent();
        if (configPage) configPage.innerHTML = this.renderProfileConfigContent();
    },
    
    onConfigChange() {
        const textarea = document.getElementById('profile-config-editor');
        const status = document.getElementById('config-status');
        if (!textarea) return;
        try {
            JSON.parse(textarea.value);
            textarea.style.border = '1px solid rgba(74, 222, 170, 0.2)';
            if (status) { status.textContent = 'Valid JSON'; status.className = 'json-editor__status'; }
        } catch (e) {
            textarea.style.border = '1px solid #f87171';
            if (status) { status.textContent = 'Invalid JSON'; status.className = 'json-editor__status json-editor__status--error'; }
        }
    },
    
    saveConfig() {
        const textarea = document.getElementById('profile-config-editor');
        const status = document.getElementById('config-status');
        if (!textarea) return;
        try {
            const configData = JSON.parse(textarea.value);
            const profile = this.getSelectedLocalProfile();
            if (profile && typeof ProfileManager !== 'undefined') {
                ProfileManager.updateProfile(profile.id, { config: configData.config });
                if (status) { status.textContent = '✓ Saved!'; status.className = 'json-editor__status json-editor__status--saved'; setTimeout(() => status.textContent = '', 2000); }
            }
        } catch (e) {
            if (status) { status.textContent = 'Error: Invalid JSON'; status.className = 'json-editor__status json-editor__status--error'; }
        }
    },
    
    resetConfig() {
        const profile = this.getSelectedLocalProfile();
        if (!profile) return;
        const configJson = JSON.stringify({
            id: profile.id, name: profile.name, provider: profile.provider, model: profile.model,
            config: profile.config || { maxTokens: 1500, temperature: 0.7, schedule: { tf15m: [1, 16, 31, 46], tf1mInterval: 2 } }
        }, null, 2);
        const textarea = document.getElementById('profile-config-editor');
        if (textarea) { textarea.value = configJson; textarea.style.border = ''; }
        const status = document.getElementById('config-status');
        if (status) { status.textContent = 'Reset'; status.className = 'json-editor__status'; setTimeout(() => status.textContent = '', 1500); }
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       DATA TABLE (Q4)
       ═══════════════════════════════════════════════════════════════════════ */
    
    initPanelControls() {
        document.querySelectorAll('.db-tab[data-table]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.db-tab[data-table]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTable = tab.dataset.table;
                this.loadDataTable();
            });
        });
        document.querySelectorAll('.db-tab[data-tf]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.db-tab[data-tf]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTimeframe = tab.dataset.tf;
                this.loadDataTable();
            });
        });
    },
    
    async loadDataTable() {
        const container = document.getElementById('data-table-content');
        if (!container) return;
        container.innerHTML = '<div class="database-loading">Loading...</div>';
        const endpoints = { 'core': '/api/chart-data', 'basic': '/api/basic', 'advanced': '/api/advanced', 'fibonacci': '/api/fibonacci', 'ath': '/api/ath' };
        try {
            const response = await fetch(`${endpoints[this.currentTable]}?timeframe=${this.currentTimeframe}&limit=100&symbol=${this.activeSymbol}`);
            const result = await response.json();
            if (result.success && result.data?.length > 0) {
                this.renderDatabaseTableHTML(container, this.currentTable, result.data);
            } else {
                container.innerHTML = `<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Data</div></div>`;
            }
        } catch (e) {
            container.innerHTML = '<div class="database-error">Error loading data</div>';
        }
    },
    
    renderDatabaseTableHTML(container, tableName, data) {
        const cols = { 
            'core': ['timestamp', 'open', 'high', 'low', 'close', 'volume'], 
            'basic': ['timestamp', 'atr_14', 'ema_short', 'ema_medium', 'supertrend'], 
            'advanced': ['timestamp', 'rsi_14', 'cci_14', 'macd_line_12_26', 'bb_width_20'], 
            'fibonacci': ['timestamp', 'current_fib_zone', 'in_golden_zone', 'zone_multiplier'], 
            'ath': ['timestamp', 'current_ath', 'ath_distance_pct', 'ath_zone'] 
        };
        const columns = cols[tableName] || Object.keys(data[0]);
        let html = `<table class="database-table"><thead><tr>${columns.map(c => `<th>${this.formatColumnName(c)}</th>`).join('')}</tr></thead><tbody>`;
        data.forEach(row => {
            html += '<tr>' + columns.map(col => {
                let v = row[col];
                if (v == null) return '<td>--</td>';
                if (typeof v === 'number') v = col.includes('volume') ? Math.round(v).toLocaleString() : v.toFixed(4);
                return `<td>${v}</td>`;
            }).join('') + '</tr>';
        });
        container.innerHTML = html + '</tbody></table>';
    },
    
    formatColumnName(col) {
        return col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).replace(/Atr|Ema|Rsi|Cci|Macd|Obv|Ath|Bb|Fib/gi, m => m.toUpperCase());
    },

    /* ═══════════════════════════════════════════════════════════════════════
       TRADING VIEW - RELATIVITY TRADING + PROFILE CONTROLLER
       ═══════════════════════════════════════════════════════════════════════ */
    renderTradingView(tab) {
        this.restoreApexLayout();
        let tabSymbol = tab.dbKey || this.activeSymbol;
        if (tabSymbol.startsWith('tr_')) tabSymbol = tab.symbol || tab.dbSymbol || this.activeSymbol;
        if (tabSymbol && !tabSymbol.startsWith('tr_')) tabSymbol = tabSymbol.toUpperCase();
        else tabSymbol = this.activeSymbol;
        
        if (tabSymbol !== this.activeSymbol) {
            this.chartData = { '15m': null, '1h': null };
            this.priceRange = { min: null, max: null };
        }
        this.activeSymbol = tabSymbol;
        
        // Initialize trading profile from ProfileManager
        this.initTradingProfile();
        
        // VIEW PANEL - 2x2 Grid (15m Tactical + 1h Trend)
        this.viewPanel.innerHTML = `
            <div class="trading-view-grid-v2">
                <div class="trading-cell trading-cell--chart" id="chart-15m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">15m</span><span class="trading-cell__title">Tactical</span></div>
                    <div class="trading-cell__content" id="chart-15m"></div>
                </div>
                <div class="trading-cell trading-cell--matrix" id="matrix-15m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">15m</span><span class="trading-cell__title">Transition Matrix</span></div>
                    <div class="trading-cell__content" id="matrix-15m"></div>
                </div>
                <div class="trading-cell trading-cell--chart" id="chart-1h-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">1h</span><span class="trading-cell__title">Trend</span></div>
                    <div class="trading-cell__content" id="chart-1h"></div>
                </div>
                <div class="trading-cell trading-cell--matrix" id="matrix-1h-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">1h</span><span class="trading-cell__title">Transition Matrix</span></div>
                    <div class="trading-cell__content" id="matrix-1h"></div>
                </div>
            </div>
        `;
        
        const today = new Date();
        this.calendarDate = new Date(today);
        
        // CONTROL CENTER with Profile Controller Orb
        this.controlBody.innerHTML = `
            <div class="rtc-fullpanel">
                <div class="rtc-stats-row">
                    <div class="rtc-stat-group">
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-avg">0.00</div><div class="rtc-stat-label">AVERAGE</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-15m">0.00</div><div class="rtc-stat-label">15M SCORE</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-1h">0.00</div><div class="rtc-stat-label">1H SCORE</div></div>
                    </div>
                    
                    <!-- PROFILE CONTROLLER ORB -->
                    <div class="rtc-orb-widget">
                        <button class="rtc-orb-arrow" id="rtc-prev" title="Previous Profile (Pause & Switch)">‹</button>
                        <div class="rtc-orb rtc-orb--profile" id="rtc-profile-orb" onclick="ApexViewRenderer.toggleProfileDirectory()">
                            ${this.renderProfileOrb()}
                        </div>
                        <button class="rtc-orb-arrow" id="rtc-next" title="Next Profile (Pause & Switch)">›</button>
                    </div>
                    
                    <div class="rtc-stat-group">
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-signals">0</div><div class="rtc-stat-label">SIGNALS</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-pf">0.00</div><div class="rtc-stat-label">PROFIT FACTOR</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-net">$0</div><div class="rtc-stat-label">NET P/L</div></div>
                    </div>
                </div>
                
                <div class="rtc-mode-toggle">
                    <button class="rtc-mode" data-mode="inactive">INACTIVE</button>
                    <button class="rtc-mode" data-mode="active">ACTIVE</button>
                    <button class="rtc-mode" data-mode="replay">REPLAY</button>
                </div>
                
                <div class="rtc-main-area">
                    <div class="rtc-panel rtc-panel--left">
                        <div class="rtc-panel-title">LIVE TRADING</div>
                        <div class="rtc-panel-body" id="rtc-trading-body">
                            <div class="rtc-row"><span>Position</span><span class="rtc-val">FLAT</span></div>
                            <div class="rtc-row"><span>Entry</span><span class="rtc-val">—</span></div>
                            <div class="rtc-row"><span>P/L</span><span class="rtc-val">$0.00</span></div>
                        </div>
                    </div>
                    
                    <!-- Calendar / Profile Directory Swap Area -->
                    <div class="rtc-calendar-swap" id="rtc-calendar-swap">
                        ${this.showProfileDirectory ? this.renderTradingProfileDirectory() : this.renderCalendarWidget()}
                    </div>
                    
                    <div class="rtc-panel rtc-panel--right">
                        <div class="rtc-panel-title">ANALYTICS</div>
                        <div class="rtc-panel-body" id="rtc-analytics-body">
                            <div class="rtc-row"><span>Win Rate</span><span class="rtc-val" id="rtc-winrate">—%</span></div>
                            <div class="rtc-row"><span>Trades</span><span class="rtc-val" id="rtc-trades">0</span></div>
                            <div class="rtc-row"><span>Sharpe</span><span class="rtc-val" id="rtc-sharpe">—</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.initRelativityControls();
        this.initProfileControls();
        this.updateModeDisplay();
        if (!this.showProfileDirectory) this.renderCalendarGrid();
        this.initTradingComponents(tab);
        this.startLiveClock();
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       PROFILE CONTROLLER - Orb Widget for Trading View
       ═══════════════════════════════════════════════════════════════════════ */
    
    initTradingProfile() {
        // Get profiles from ProfileManager (sorted by North Star)
        if (typeof ProfileManager !== 'undefined' && ProfileManager.profiles.length > 0) {
            // Find active profile or use first
            const activeProfile = ProfileManager.profiles.find(p => p.status === 'active');
            if (activeProfile) {
                this.tradingProfileId = activeProfile.id;
                this.tradingProfileIndex = ProfileManager.profiles.findIndex(p => p.id === activeProfile.id);
            } else {
                this.tradingProfileId = ProfileManager.profiles[0].id;
                this.tradingProfileIndex = 0;
            }
        }
    },
    
    getTradingProfile() {
        if (typeof ProfileManager === 'undefined') return null;
        return ProfileManager.profiles.find(p => p.id === this.tradingProfileId);
    },
    
    getTradingProfileRank() {
        if (typeof ProfileManager === 'undefined') return 0;
        const index = ProfileManager.profiles.findIndex(p => p.id === this.tradingProfileId);
        return index >= 0 ? index + 1 : 0;
    },
    
    getRankBadgeClass(rank) {
        if (rank === 1) return 'rtc-rank--gold';
        if (rank === 2) return 'rtc-rank--silver';
        if (rank === 3) return 'rtc-rank--bronze';
        return 'rtc-rank--matte'; // rank 4+
    },
    
    renderProfileOrb() {
        const profile = this.getTradingProfile();
        const rank = this.getTradingProfileRank();
        const provider = profile ? (typeof ProfileManager !== 'undefined' ? ProfileManager.providers[profile.provider] : null) : null;
        
        // Profile image or placeholder
        let imageHtml;
        if (profile?.imagePath) {
            imageHtml = `<img class="rtc-orb-img" src="${profile.imagePath}" alt="${profile.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                         <div class="rtc-orb-placeholder" style="display:none;">${provider?.icon || '?'}</div>`;
        } else {
            imageHtml = `<div class="rtc-orb-placeholder">${provider?.icon || '?'}</div>`;
        }
        
        // Rank badge
        const rankBadge = rank > 0 
            ? `<div class="rtc-rank-badge ${this.getRankBadgeClass(rank)}">${rank}</div>` 
            : '';
        
        return `
            ${imageHtml}
            <div class="rtc-orb-time" id="rtc-time">--:--</div>
            ${rankBadge}
        `;
    },
    
    updateProfileOrb() {
        const orb = document.getElementById('rtc-profile-orb');
        if (orb) {
            orb.innerHTML = this.renderProfileOrb();
        }
    },
    
    initProfileControls() {
        // Arrow buttons: Pause & Switch Profile
        document.getElementById('rtc-prev')?.addEventListener('click', () => this.switchProfile(-1));
        document.getElementById('rtc-next')?.addEventListener('click', () => this.switchProfile(1));
    },
    
    switchProfile(direction) {
        if (typeof ProfileManager === 'undefined' || ProfileManager.profiles.length === 0) return;
        
        // 1. Pause execution if running
        if (this.isTraderRunning) {
            this.isTraderRunning = false;
            console.log('[APEX] Trader PAUSED for profile switch');
            if (typeof ApexSentiment !== 'undefined') {
                ApexSentiment.stopEngine();
            }
        }
        
        // 2. Calculate new index
        const totalProfiles = ProfileManager.profiles.length;
        this.tradingProfileIndex = (this.tradingProfileIndex + direction + totalProfiles) % totalProfiles;
        this.tradingProfileId = ProfileManager.profiles[this.tradingProfileIndex].id;
        
        // 3. Update UI
        this.updateProfileOrb();
        this.updateModeDisplay();
        
        console.log('[APEX] Switched to profile:', ProfileManager.profiles[this.tradingProfileIndex].name);
    },
    
    toggleProfileDirectory() {
        this.showProfileDirectory = !this.showProfileDirectory;
        const swapArea = document.getElementById('rtc-calendar-swap');
        if (swapArea) {
            swapArea.innerHTML = this.showProfileDirectory 
                ? this.renderTradingProfileDirectory() 
                : this.renderCalendarWidget();
            
            if (!this.showProfileDirectory) {
                this.renderCalendarGrid();
            }
        }
    },
    
    renderTradingProfileDirectory() {
        // Get profiles from ProfileManager
        const profiles = typeof ProfileManager !== 'undefined' ? ProfileManager.profiles : [];
        
        if (profiles.length === 0) {
            return `
                <div class="rtc-profile-directory">
                    <div class="rtc-profile-directory__header">
                        <span>Select Profile</span>
                        <button class="rtc-profile-directory__close" onclick="ApexViewRenderer.toggleProfileDirectory()">×</button>
                    </div>
                    <div class="rtc-profile-directory__empty">
                        <div>No profiles available</div>
                        <div class="rtc-profile-directory__hint">Create profiles in the Database view</div>
                    </div>
                </div>
            `;
        }
        
        const profileRows = profiles.map((profile, index) => {
            const rank = index + 1;
            const isActive = profile.id === this.tradingProfileId;
            const provider = typeof ProfileManager !== 'undefined' ? ProfileManager.providers[profile.provider] : null;
            const northStar = this.calculateNorthStar(profile);
            
            return `
                <div class="rtc-profile-row ${isActive ? 'rtc-profile-row--active' : ''}" 
                     onclick="ApexViewRenderer.selectTradingProfile('${profile.id}')">
                    <div class="rtc-profile-row__avatar">
                        ${profile.imagePath 
                            ? `<img src="${profile.imagePath}" alt="${profile.name}" />` 
                            : `<div class="rtc-profile-row__placeholder">${provider?.icon || '?'}</div>`
                        }
                        <div class="rtc-profile-row__rank ${this.getRankBadgeClass(rank)}">${rank}</div>
                    </div>
                    <div class="rtc-profile-row__info">
                        <div class="rtc-profile-row__name">${profile.name}</div>
                        <div class="rtc-profile-row__provider">${provider?.shortName || profile.provider}</div>
                    </div>
                    <div class="rtc-profile-row__score">${northStar.toFixed(2)}</div>
                </div>
            `;
        }).join('');
        
        return `
            <div class="rtc-profile-directory">
                <div class="rtc-profile-directory__header">
                    <span>Select Profile</span>
                    <button class="rtc-profile-directory__close" onclick="ApexViewRenderer.toggleProfileDirectory()">×</button>
                </div>
                <div class="rtc-profile-directory__list">
                    ${profileRows}
                </div>
            </div>
        `;
    },
    
    selectTradingProfile(profileId) {
        if (typeof ProfileManager === 'undefined') return;
        
        const index = ProfileManager.profiles.findIndex(p => p.id === profileId);
        if (index === -1) return;
        
        // Pause if running
        if (this.isTraderRunning) {
            this.isTraderRunning = false;
            console.log('[APEX] Trader PAUSED for profile selection');
            if (typeof ApexSentiment !== 'undefined') {
                ApexSentiment.stopEngine();
            }
        }
        
        // Update state
        this.tradingProfileId = profileId;
        this.tradingProfileIndex = index;
        
        // Update UI
        this.updateProfileOrb();
        this.updateModeDisplay();
        this.toggleProfileDirectory(); // Close directory
        
        console.log('[APEX] Selected profile:', ProfileManager.profiles[index].name);
    },
    
    renderCalendarWidget() {
        return `
            <div class="rtc-calendar">
                <div class="rtc-cal-inputs">
                    <div class="rtc-cal-field">
                        <span class="rtc-cal-label">Start</span>
                        <div class="rtc-cal-date" id="rtc-start-date"></div>
                    </div>
                    <div class="rtc-cal-field">
                        <span class="rtc-cal-label">Due</span>
                        <div class="rtc-cal-date" id="rtc-end-date"></div>
                    </div>
                </div>
                <div class="rtc-cal-inputs">
                    <div class="rtc-cal-time">🕐 <input type="text" value="${this.calendarStartTime}" id="rtc-start-time" /></div>
                    <div class="rtc-cal-time">🕐 <input type="text" value="${this.calendarEndTime}" id="rtc-end-time" /></div>
                </div>
                <div class="rtc-cal-nav">
                    <button class="rtc-cal-nav-btn" id="rtc-cal-prev">‹</button>
                    <span class="rtc-cal-month" id="rtc-cal-month">${this.getMonthYear()}</span>
                    <button class="rtc-cal-nav-btn" id="rtc-cal-next">›</button>
                </div>
                <div class="rtc-cal-days"><span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span></div>
                <div class="rtc-cal-grid" id="rtc-cal-grid"></div>
            </div>
        `;
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       MODE MANAGEMENT
       ═══════════════════════════════════════════════════════════════════════ */
    setMode(mode) {
        const prevMode = this.replayMode;
        this.replayMode = mode;
        
        if (mode === 'active' && prevMode === 'active') {
            this.isTraderRunning = !this.isTraderRunning;
            if (this.isTraderRunning) {
                console.log('[APEX] Trader STARTED');
                if (typeof ApexSentiment !== 'undefined') ApexSentiment.startEngine(this.activeSymbol, true);
            } else {
                console.log('[APEX] Trader STOPPED');
                if (typeof ApexSentiment !== 'undefined') ApexSentiment.stopEngine();
            }
        } else if (mode === 'replay' && prevMode === 'replay') {
            this.isReplayRunning = !this.isReplayRunning;
        } else {
            this.isTraderRunning = false;
            this.isReplayRunning = false;
        }
        
        this.updateModeDisplay();
    },
    
    updateModeDisplay() {
        const today = new Date();
        const startDateEl = document.getElementById('rtc-start-date');
        const endDateEl = document.getElementById('rtc-end-date');
        const startTimeEl = document.getElementById('rtc-start-time');
        const endTimeEl = document.getElementById('rtc-end-time');
        
        document.querySelectorAll('.rtc-mode').forEach(btn => {
            btn.classList.remove('rtc-mode--active', 'rtc-mode--running');
            if (btn.dataset.mode === this.replayMode) {
                btn.classList.add('rtc-mode--active');
                if ((this.replayMode === 'active' && this.isTraderRunning) || (this.replayMode === 'replay' && this.isReplayRunning)) {
                    btn.classList.add('rtc-mode--running');
                }
            }
        });
        
        switch (this.replayMode) {
            case 'inactive':
                if (startDateEl) startDateEl.innerHTML = `<span class="rtc-cal-muted">—</span>`;
                if (endDateEl) endDateEl.innerHTML = `<span class="rtc-cal-muted">—</span>`;
                if (startTimeEl) startTimeEl.disabled = true;
                if (endTimeEl) endTimeEl.disabled = true;
                this.calendarStartDate = null;
                this.calendarEndDate = null;
                break;
            case 'active':
                this.calendarStartDate = new Date(today);
                this.calendarEndDate = null;
                if (startDateEl) startDateEl.innerHTML = `📅 ${this.formatDate(today)} <span class="rtc-cal-live">LIVE</span>`;
                if (endDateEl) endDateEl.innerHTML = `<span class="rtc-cal-infinity">∞</span> Unlimited`;
                if (startTimeEl) { startTimeEl.value = this.formatTime(today); startTimeEl.disabled = true; }
                if (endTimeEl) { endTimeEl.value = '∞'; endTimeEl.disabled = true; }
                break;
            case 'replay':
                if (!this.calendarStartDate) {
                    this.calendarStartDate = new Date(today);
                    this.calendarStartDate.setDate(this.calendarStartDate.getDate() - 7);
                    this.calendarEndDate = new Date(today);
                }
                if (startDateEl) startDateEl.innerHTML = `📅 ${this.formatDate(this.calendarStartDate)}`;
                if (endDateEl) endDateEl.innerHTML = `📅 ${this.formatDate(this.calendarEndDate)}`;
                if (startTimeEl) startTimeEl.disabled = false;
                if (endTimeEl) endTimeEl.disabled = false;
                break;
        }
        
        this.renderCalendarGrid();
        this.updateAnalyticsForDateRange();
    },
    
    updateAnalyticsForDateRange() {
        if (!this.calendarStartDate || !this.calendarEndDate) {
            const winrateEl = document.getElementById('rtc-winrate');
            const tradesEl = document.getElementById('rtc-trades');
            const sharpeEl = document.getElementById('rtc-sharpe');
            if (winrateEl) winrateEl.textContent = '—%';
            if (tradesEl) tradesEl.textContent = '0';
            if (sharpeEl) sharpeEl.textContent = '—';
            return;
        }
        let totalScore = 0, dayCount = 0;
        for (let d = new Date(this.calendarStartDate); d <= this.calendarEndDate; d.setDate(d.getDate() + 1)) {
            const key = this.getDateKey(d);
            if (this.dayPerformance[key]) { totalScore += this.dayPerformance[key]; dayCount++; }
        }
        const avgScore = dayCount > 0 ? totalScore / dayCount : 0;
        document.getElementById('rtc-winrate')?.textContent && (document.getElementById('rtc-winrate').textContent = `${(avgScore * 100).toFixed(1)}%`);
        document.getElementById('rtc-trades')?.textContent && (document.getElementById('rtc-trades').textContent = Math.floor(dayCount * 8).toString());
        document.getElementById('rtc-sharpe')?.textContent && (document.getElementById('rtc-sharpe').textContent = (avgScore * 2.5).toFixed(2));
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       CALENDAR METHODS
       ═══════════════════════════════════════════════════════════════════════ */
    getMonthYear() {
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        return `${months[this.calendarDate.getMonth()]} ${this.calendarDate.getFullYear()}`;
    },
    
    formatDate(date) {
        if (!date) return 'Select';
        return `${date.getDate().toString().padStart(2, '0')}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getFullYear()}`;
    },
    
    formatTime(date) {
        return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
    },
    
    getPerformanceColor(score) {
        if (score === undefined || score === null) return null;
        if (score < 0.4) return `rgba(180, ${Math.floor(60 + score * 100)}, ${Math.floor(60 + score * 100)}, 0.3)`;
        if (score < 0.6) return `rgba(180, 160, 80, 0.3)`;
        if (score < 0.75) return `rgba(120, 175, 130, 0.3)`;
        return `rgba(100, ${Math.floor(140 + (score - 0.75) * 200)}, 120, 0.4)`;
    },
    
    renderCalendarGrid() {
        const grid = document.getElementById('rtc-cal-grid');
        if (!grid) return;
        
        const year = this.calendarDate.getFullYear();
        const month = this.calendarDate.getMonth();
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const daysInPrevMonth = new Date(year, month, 0).getDate();
        
        let html = '';
        for (let i = 0; i < firstDayOfMonth; i++) {
            html += `<div class="rtc-cal-day rtc-cal-day--other">${daysInPrevMonth - firstDayOfMonth + 1 + i}</div>`;
        }
        
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            const dateKey = this.getDateKey(date);
            const isStart = this.calendarStartDate && this.isSameDay(date, this.calendarStartDate);
            const isEnd = this.calendarEndDate && this.isSameDay(date, this.calendarEndDate);
            const isInRange = this.isInRange(date);
            const isToday = this.isSameDay(date, new Date());
            const isFuture = date > new Date();
            const perfScore = this.dayPerformance[dateKey];
            const perfColor = !isFuture ? this.getPerformanceColor(perfScore) : null;
            
            let cls = 'rtc-cal-day';
            if (isStart) cls += ' rtc-cal-day--start';
            if (isEnd) cls += ' rtc-cal-day--end';
            if (isInRange && !isStart && !isEnd) cls += ' rtc-cal-day--range';
            if (isToday) cls += ' rtc-cal-day--today';
            if (isFuture) cls += ' rtc-cal-day--future';
            if (perfColor && !isFuture) cls += ' rtc-cal-day--perf';
            
            const style = perfColor ? `style="background: ${perfColor}"` : '';
            const perfIndicator = perfScore !== undefined && !isFuture ? `<span class="rtc-cal-perf" title="North Star: ${(perfScore * 100).toFixed(0)}%"></span>` : '';
            html += `<div class="${cls}" data-date="${year}-${month + 1}-${day}" ${style}>${day}${perfIndicator}</div>`;
        }
        
        const totalCells = firstDayOfMonth + daysInMonth;
        const remaining = Math.ceil(totalCells / 7) * 7 - totalCells;
        for (let day = 1; day <= remaining; day++) {
            html += `<div class="rtc-cal-day rtc-cal-day--other">${day}</div>`;
        }
        
        grid.innerHTML = html;
        
        if (this.replayMode === 'replay') {
            grid.querySelectorAll('.rtc-cal-day:not(.rtc-cal-day--other):not(.rtc-cal-day--future)').forEach(cell => {
                cell.addEventListener('click', () => {
                    const [y, m, d] = cell.dataset.date.split('-').map(Number);
                    this.selectCalendarDate(new Date(y, m - 1, d));
                });
            });
        }
    },
    
    selectCalendarDate(date) {
        if (this.replayMode !== 'replay') return;
        if (!this.calendarStartDate || (this.calendarStartDate && this.calendarEndDate)) {
            this.calendarStartDate = date;
            this.calendarEndDate = null;
        } else {
            if (date < this.calendarStartDate) {
                this.calendarEndDate = this.calendarStartDate;
                this.calendarStartDate = date;
            } else {
                this.calendarEndDate = date;
            }
        }
        document.getElementById('rtc-start-date').innerHTML = '📅 ' + this.formatDate(this.calendarStartDate);
        document.getElementById('rtc-end-date').innerHTML = '📅 ' + this.formatDate(this.calendarEndDate);
        this.renderCalendarGrid();
        this.updateAnalyticsForDateRange();
    },
    
    isSameDay(d1, d2) {
        return d1.getDate() === d2.getDate() && d1.getMonth() === d2.getMonth() && d1.getFullYear() === d2.getFullYear();
    },
    
    isInRange(date) {
        if (!this.calendarStartDate || !this.calendarEndDate) return false;
        return date > this.calendarStartDate && date < this.calendarEndDate;
    },
    
    initRelativityControls() {
        document.querySelectorAll('.rtc-mode').forEach(btn => {
            btn.addEventListener('click', () => this.setMode(btn.dataset.mode));
        });
        
        document.getElementById('rtc-cal-prev')?.addEventListener('click', () => {
            this.calendarDate.setMonth(this.calendarDate.getMonth() - 1);
            document.getElementById('rtc-cal-month').textContent = this.getMonthYear();
            this.renderCalendarGrid();
        });
        
        document.getElementById('rtc-cal-next')?.addEventListener('click', () => {
            this.calendarDate.setMonth(this.calendarDate.getMonth() + 1);
            document.getElementById('rtc-cal-month').textContent = this.getMonthYear();
            this.renderCalendarGrid();
        });
    },
    
    initTradingComponents(tab) {
        this.cleanup();
        const symbolKey = tab.dbKey || this.activeSymbol;
        
        setTimeout(() => {
            this.loadChartData('15m', false, symbolKey);
            this.loadChartData('1h', false, symbolKey);
            this.loadMarkovData('15m');
            this.loadMarkovData('1h');
        }, 50);
        
        this.setupResizeHandler();
        this.refreshIntervals['15m'] = setInterval(() => this.loadChartData('15m', true, symbolKey), 60 * 1000);
        this.refreshIntervals['1h'] = setInterval(() => this.loadChartData('1h', true, symbolKey), 5 * 60 * 1000);
    },
    
    setupResizeHandler() {
        let resizeTimeout;
        const handleResize = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                ['15m', '1h'].forEach(tf => {
                    const container = document.getElementById(`chart-${tf}`);
                    if (container && this.charts[tf]) Plotly.Plots.resize(container);
                });
            }, 150);
        };
        window.addEventListener('resize', handleResize);
        this._resizeHandler = handleResize;
    },
    
    async loadChartData(timeframe, isRefresh = false, symbolKey = null) {
        const container = document.getElementById(`chart-${timeframe}`);
        if (!container) return;
        const symbol = symbolKey || this.activeSymbol;
        const userBarCount = typeof ApexIndicators !== 'undefined' ? ApexIndicators.getBarCount(timeframe) : 200;
        
        // Request extra bars for indicator lookback (EMA200 needs 200 bars to start)
        const fetchCount = userBarCount + 250;
        
        try {
            const response = await fetch(`/api/chart-data?timeframe=${timeframe}&limit=${fetchCount}&symbol=${symbol}`);
            const result = await response.json();
            if (result.success && result.data?.length > 0) {
                this.chartData[timeframe] = result.data;
                this.updatePriceRange(result.data);
                this.renderPlotlyChart(container, result.data, timeframe, result.symbol);
            } else {
                if (!this.chartData[timeframe]) {
                    this.chartData[timeframe] = this.generateDemoOHLCV(fetchCount, timeframe);
                    this.updatePriceRange(this.chartData[timeframe]);
                }
                this.renderPlotlyChart(container, this.chartData[timeframe], timeframe, symbol);
            }
        } catch (e) {
            if (!this.chartData[timeframe]) {
                this.chartData[timeframe] = this.generateDemoOHLCV(fetchCount, timeframe);
                this.updatePriceRange(this.chartData[timeframe]);
            }
            this.renderPlotlyChart(container, this.chartData[timeframe], timeframe, symbol);
        }
    },
    
    updatePriceRange(data) {
        const highs = data.map(d => parseFloat(d.high));
        const lows = data.map(d => parseFloat(d.low));
        const dataMin = Math.min(...lows);
        const dataMax = Math.max(...highs);
        if (this.priceRange.min === null || dataMin < this.priceRange.min) this.priceRange.min = dataMin;
        if (this.priceRange.max === null || dataMax > this.priceRange.max) this.priceRange.max = dataMax;
    },
    
    renderPlotlyChart(container, data, timeframe, symbolName) {
        const containerWidth = container.clientWidth || 600;
        const userBarCount = typeof ApexIndicators !== 'undefined' ? ApexIndicators.getBarCount(timeframe) : 100;
        
        // Use the user's requested bar count, but cap at available data
        const displayBarCount = Math.min(userBarCount, data.length);
        
        // Calculate indicators on FULL data first (for proper lookback)
        let indicatorTraces = [];
        if (typeof ApexIndicators !== 'undefined') {
            // Generate traces using ALL data and full indices
            const fullXIndices = data.map((d, i) => i);
            indicatorTraces = ApexIndicators.generateTraces(data, timeframe, fullXIndices);
        }
        
        // Now slice to display range (last N bars)
        const startIdx = Math.max(0, data.length - displayBarCount);
        const chartData = data.slice(startIdx);
        
        // Remap x-indices for display (0 to displayBarCount-1)
        const xIndices = chartData.map((d, i) => i);
        
        // Slice indicator traces to match display range
        indicatorTraces = indicatorTraces.map(trace => {
            if (Array.isArray(trace.x) && Array.isArray(trace.y)) {
                // For line traces, slice both x and y
                if (trace.x.length === data.length) {
                    return {
                        ...trace,
                        x: trace.x.slice(startIdx).map((_, i) => i),
                        y: trace.y.slice(startIdx)
                    };
                } else if (trace.x.length === 2) {
                    // Horizontal lines (fib, pivots) - remap to new range
                    return {
                        ...trace,
                        x: [0, displayBarCount - 1]
                    };
                }
            }
            return trace;
        });
        
        const highs = chartData.map(d => parseFloat(d.high));
        const lows = chartData.map(d => parseFloat(d.low));
        const dataMin = Math.min(...lows);
        const dataMax = Math.max(...highs);
        const padding = (dataMax - dataMin) * 0.05;
        
        const xLabels = chartData.map(d => new Date(d.timestamp || d.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }));
        const tickStep = Math.max(1, Math.floor(chartData.length / 8));
        const tickVals = [], tickText = [];
        for (let i = 0; i < chartData.length; i += tickStep) { tickVals.push(i); tickText.push(xLabels[i]); }
        
        const traces = [{
            type: 'candlestick', x: xIndices,
            open: chartData.map(d => parseFloat(d.open)), high: chartData.map(d => parseFloat(d.high)),
            low: chartData.map(d => parseFloat(d.low)), close: chartData.map(d => parseFloat(d.close)),
            name: symbolName,
            increasing: { line: { color: '#7EAE8B', width: 1 }, fillcolor: '#7EAE8B' },
            decreasing: { line: { color: '#4A6A8A', width: 1 }, fillcolor: '#4A6A8A' }
        }];
        
        // Add sliced indicator traces
        traces.push(...indicatorTraces);
        
        const layout = {
            autosize: true, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
            font: { color: '#9CA3AF', size: 10, family: 'Inter, sans-serif' },
            margin: { l: 0, r: 50, t: 0, b: 25, pad: 0 },
            xaxis: { type: 'linear', tickmode: 'array', tickvals: tickVals, ticktext: tickText, gridcolor: 'rgba(255,255,255,0.025)', rangeslider: { visible: false }, fixedrange: true, showgrid: true, zeroline: false, tickfont: { size: 9, color: '#6B7280' }, tickangle: 0, automargin: true },
            yaxis: { side: 'right', gridcolor: 'rgba(255,255,255,0.025)', range: [dataMin - padding, dataMax + padding], fixedrange: true, showgrid: true, zeroline: false, tickformat: '.0f', tickfont: { size: 9, color: '#6B7280' }, automargin: true },
            showlegend: false, dragmode: false, hovermode: 'x unified',
            hoverlabel: { bgcolor: 'rgba(20, 22, 26, 0.95)', bordercolor: 'rgba(255, 255, 255, 0.1)', font: { size: 10, color: '#E5E7EB' } }
        };
        
        Plotly.newPlot(container, traces, layout, { displayModeBar: false, responsive: true, scrollZoom: false, doubleClick: false, staticPlot: false });
        this.charts[timeframe] = container;
        
        if (typeof ApexIndicators !== 'undefined') {
            ApexIndicators.renderSettingsButton(container, timeframe);
            ApexIndicators.renderLegend(container, timeframe);
        }
    },
    
    async loadMarkovData(timeframe) {
        const container = document.getElementById(`matrix-${timeframe}`);
        if (!container) return;
        if (!this.matrices[timeframe + '_data']) this.matrices[timeframe + '_data'] = this.generateDemoMatrix();
        const matrix = this.matrices[timeframe + '_data'];
        const currentState = Math.floor(Math.random() * 5);
        if (typeof ApexMarkovMatrix !== 'undefined') {
            this.matrices[timeframe] = new ApexMarkovMatrix(container, { cellWidth: 38, cellHeight: 26, labelWidth: 28, showLegend: false, showLabels: true });
            this.matrices[timeframe].setData(matrix, currentState);
        }
    },
    
    startLiveClock() {
        if (this.clockInterval) clearInterval(this.clockInterval);
        this.updateLiveClock();
        this.clockInterval = setInterval(() => this.updateLiveClock(), 1000);
    },
    
    updateLiveClock() {
        const display = document.getElementById('rtc-time');
        if (!display) return;
        const now = new Date();
        display.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    },
    
    generateDemoOHLCV(count, timeframe) {
        const seed = timeframe === '1m' ? 12345 : 67890;
        let rng = seed;
        const seededRandom = () => { rng = (rng * 1103515245 + 12345) & 0x7fffffff; return rng / 0x7fffffff; };
        const data = [];
        let price = 2680;
        const now = Date.now();
        const interval = timeframe === '1m' ? 60000 : 900000;
        for (let i = count - 1; i >= 0; i--) {
            const open = price;
            const change = (seededRandom() - 0.5) * 3;
            const close = open + change;
            data.push({
                timestamp: new Date(now - i * interval).toISOString(),
                open: parseFloat(open.toFixed(2)), high: parseFloat((Math.max(open, close) + seededRandom() * 1.5).toFixed(2)),
                low: parseFloat((Math.min(open, close) - seededRandom() * 1.5).toFixed(2)), close: parseFloat(close.toFixed(2)),
                volume: Math.floor(1000 + seededRandom() * 4000)
            });
            price = close;
        }
        return data;
    },
    
    generateDemoMatrix() {
        const matrix = [];
        for (let i = 0; i < 5; i++) {
            const row = [];
            let sum = 0;
            for (let j = 0; j < 5; j++) { const prob = Math.random() * (Math.abs(i - j) === 0 ? 2 : 1); row.push(prob); sum += prob; }
            matrix.push(row.map(p => p / sum));
        }
        return matrix;
    },
    
    cleanup() {
        ['15m', '1h'].forEach(tf => {
            const container = document.getElementById(`chart-${tf}`);
            if (container) try { Plotly.purge(container); } catch (e) {}
        });
        this.charts = { '15m': null, '1h': null };
        Object.keys(this.matrices).forEach(key => { if (!key.endsWith('_data') && this.matrices[key]?.destroy) this.matrices[key].destroy(); });
        if (this.clockInterval) { clearInterval(this.clockInterval); this.clockInterval = null; }
        Object.keys(this.refreshIntervals).forEach(tf => { if (this.refreshIntervals[tf]) { clearInterval(this.refreshIntervals[tf]); this.refreshIntervals[tf] = null; } });
        if (this._resizeHandler) { window.removeEventListener('resize', this._resizeHandler); this._resizeHandler = null; }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Plotly === 'undefined') return;
    ApexViewRenderer.init();
});

window.ApexViewRenderer = ApexViewRenderer;
