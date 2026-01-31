/* ═══════════════════════════════════════════════════════════════════════════
   APEX VIEWS V3.3 - Relativity Trading Control Panel
   
   Features:
   - Active/Replay mode with glowing animation
   - Calendar with performance coloring
   - Mode-specific date/time display
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexViewRenderer = {
    viewPanel: null,
    controlBody: null,
    charts: { '1m': null, '15m': null },
    chartData: { '1m': null, '15m': null },
    matrices: { '1m': null, '15m': null },
    calendar: null,
    replayTime: 0,
    clockInterval: null,
    refreshIntervals: { '1m': null, '15m': null },
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
    
    // Mock performance data for calendar (will be replaced with real data)
    dayPerformance: {},
    
    profiles: [],
    currentSource: 'profiles',
    currentTable: 'core',
    currentTimeframe: '15m',
    hyperspheres: [],
    
    init() {
        this.viewPanel = document.getElementById('view-panel-content');
        this.controlBody = document.getElementById('control-center-body');
        this.loadSymbols();
        this.generateMockPerformanceData();
        ApexState.subscribe(state => this.onStateChange(state));
        this.onStateChange(ApexState.getState());
        
        window.addEventListener('apex-chart-refresh', (e) => {
            const tf = e.detail.timeframe;
            if (this.chartData[tf]) {
                const container = document.getElementById(`chart-${tf}`);
                if (container) {
                    this.renderPlotlyChart(container, this.chartData[tf], tf, this.activeSymbol);
                }
            }
        });
    },
    
    generateMockPerformanceData() {
        // Generate mock North Star scores for past 60 days
        const today = new Date();
        for (let i = 0; i < 60; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const key = this.getDateKey(date);
            // Random score between 0.2 and 0.95
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
        this.viewPanel.innerHTML = `<iframe src="/metatron" style="width: 100%; height: 100%; border: none; background: #0a0b0d;" title="Metatron"></iframe>`;
        this.controlBody.innerHTML = `<div class="metatron-control-info"><div class="metatron-control-info__header"><span style="color: #C084FC;">◉</span> METATRON RADIAL DATABASE</div></div>`;
    },
    
    renderEmptyState() {
        this.viewPanel.innerHTML = `<div class="view-panel__placeholder"><div class="view-panel__placeholder-icon">◎</div><div class="view-panel__placeholder-text">Select a symbol database to view</div></div>`;
        this.controlBody.innerHTML = `<div class="control-center__placeholder">Click the APEX logo to open a database or trading view</div>`;
        this.cleanup();
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       DATABASE VIEW
       ═══════════════════════════════════════════════════════════════════════ */
    async renderDatabaseView(tab) {
        this.cleanup();
        const symbolKey = tab.dbKey || tab.instanceId || this.activeSymbol;
        this.activeSymbol = symbolKey;
        
        const symbolConfig = this.availableSymbols.find(s => s.id === symbolKey) || {};
        const symbolName = symbolConfig.name || symbolKey;
        const symbolTicker = symbolConfig.symbol || symbolKey;
        
        await Promise.all([this.loadProfiles(symbolKey), this.loadHyperspheres(symbolKey)]);
        
        this.viewPanel.innerHTML = `
            <div class="intelligence-view">
                <div class="intelligence-header">
                    <div class="intelligence-header__row"><span class="intelligence-header__dot"></span><span class="intelligence-header__label">INTELLIGENCE DATABASE</span></div>
                    <div class="intelligence-header__symbol">${symbolName} - ${symbolTicker}</div>
                </div>
                <!-- Profile Manager replaces the old analytics grid -->
                <div class="profile-manager" id="profile-manager">
                    <!-- Rendered by ProfileManager.init() -->
                </div>
            </div>
        `;
        
        // Initialize Profile Manager
        if (typeof ProfileManager !== 'undefined') {
            ProfileManager.init();
        }
        
        this.controlBody.innerHTML = `
            <div class="database-split-panels">
                <div class="database-panel" id="instance-browser-panel">
                    <!-- Instance Browser loads here -->
                </div>
                <div class="database-panel">
                    <div class="database-panel__header">
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentTable === 'core' ? 'active' : ''}" data-table="core">CORE</button>
                            <button class="db-tab ${this.currentTable === 'basic' ? 'active' : ''}" data-table="basic">BASIC</button>
                            <button class="db-tab ${this.currentTable === 'advanced' ? 'active' : ''}" data-table="advanced">ADV</button>
                            <button class="db-tab ${this.currentTable === 'fibonacci' ? 'active' : ''}" data-table="fibonacci">FIB</button>
                            <button class="db-tab ${this.currentTable === 'ath' ? 'active' : ''}" data-table="ath">ATH</button>
                        </div>
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentTimeframe === '1m' ? 'active' : ''}" data-tf="1m">1M</button>
                            <button class="db-tab ${this.currentTimeframe === '15m' ? 'active' : ''}" data-tf="15m">15M</button>
                        </div>
                    </div>
                    <div class="database-panel__content" id="right-panel-content"><div class="database-loading">Loading...</div></div>
                </div>
            </div>
        `;
        
        // Initialize Instance Browser in left panel
        const instancePanel = document.getElementById('instance-browser-panel');
        if (instancePanel && typeof ApexInstanceBrowser !== 'undefined') {
            ApexInstanceBrowser.init(instancePanel, symbolKey);
        }
        
        this.initPanelControls();
        this.loadRightPanel();
    },
    
    initPanelControls() {
        
        document.querySelectorAll('.db-tab[data-table]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.db-tab[data-table]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTable = tab.dataset.table;
                this.loadRightPanel();
            });
        });
        
        document.querySelectorAll('.db-tab[data-tf]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.db-tab[data-tf]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTimeframe = tab.dataset.tf;
                this.loadRightPanel();
            });
        });
    },
    
    async loadBothPanels() {
        await Promise.all([this.loadLeftPanel(), this.loadRightPanel()]);
    },
    
    async loadLeftPanel() {
        const container = document.getElementById('left-panel-content');
        if (!container) return;
        container.innerHTML = this.currentSource === 'profiles' ? this.renderProfilesTable() : this.renderHyperspheresTable();
    },
    
    async loadRightPanel() {
        const container = document.getElementById('right-panel-content');
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
    
    async loadDatabaseStats(symbolKey) {
        try {
            const response = await fetch(`/api/symbols`);
            const result = await response.json();
            if (result.success) {
                const symbol = result.symbols.find(s => s.id === symbolKey);
                if (symbol) {
                    const el1m = document.getElementById('db-stat-1m');
                    const el15m = document.getElementById('db-stat-15m');
                    if (el1m) el1m.textContent = (symbol.records_1m || 0).toLocaleString();
                    if (el15m) el15m.textContent = (symbol.records_15m || 0).toLocaleString();
                }
            }
        } catch (e) {}
    },
    
    renderProfilesTable() {
        if (this.profiles.length === 0) {
            return `<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Profiles</div></div>`;
        }
        let html = `<table class="database-table"><thead><tr><th>Name</th><th>North Star</th><th>PF</th><th>Win Rate</th></tr></thead><tbody>`;
        this.profiles.forEach(p => {
            const m = p.metrics || {};
            html += `<tr><td>${p.display_name || p.profile_id}</td><td class="cell-bull">${m.north_star?.toFixed(2) || '--'}</td><td>${m.profit_factor?.toFixed(2) || '--'}</td><td>${m.win_rate ? (m.win_rate * 100).toFixed(1) + '%' : '--'}</td></tr>`;
        });
        return html + '</tbody></table>';
    },
    
    renderHyperspheresTable() {
        if (this.hyperspheres.length === 0) {
            return `<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Hyperspheres</div></div>`;
        }
        let html = `<table class="database-table"><thead><tr><th>Name</th><th>Type</th><th>States</th><th>Accuracy</th></tr></thead><tbody>`;
        this.hyperspheres.forEach(h => {
            html += `<tr><td>${h.name || 'Unnamed'}</td><td>${h.classifier_type || 'MarkovChain'}</td><td>${h.state_count || 5}</td><td>${h.accuracy ? (h.accuracy * 100).toFixed(1) + '%' : '--'}</td></tr>`;
        });
        return html + '</tbody></table>';
    },
    
    renderDatabaseTableHTML(container, tableName, data) {
        const cols = { 'core': ['timestamp', 'open', 'high', 'low', 'close', 'volume'], 'basic': ['timestamp', 'atr_14', 'ema_short', 'ema_medium', 'supertrend'], 'advanced': ['timestamp', 'rsi_14', 'cci_14', 'macd_line_12_26', 'bb_width_20'], 'fibonacci': ['timestamp', 'current_fib_zone', 'in_golden_zone', 'zone_multiplier'], 'ath': ['timestamp', 'current_ath', 'ath_distance_pct', 'ath_zone'] };
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
       TRADING VIEW - RELATIVITY TRADING
       ═══════════════════════════════════════════════════════════════════════ */
    renderTradingView(tab) {
        let tabSymbol = tab.dbKey || this.activeSymbol;
        
        if (tabSymbol.startsWith('tr_')) {
            tabSymbol = tab.symbol || tab.dbSymbol || this.activeSymbol;
        }
        
        if (tabSymbol && !tabSymbol.startsWith('tr_')) {
            tabSymbol = tabSymbol.toUpperCase();
        } else {
            tabSymbol = this.activeSymbol;
        }
        
        if (tabSymbol !== this.activeSymbol) {
            this.chartData = { '1m': null, '15m': null };
            this.priceRange = { min: null, max: null };
        }
        this.activeSymbol = tabSymbol;
        
        // VIEW PANEL - 2x2 Grid
        this.viewPanel.innerHTML = `
            <div class="trading-view-grid-v2">
                <div class="trading-cell trading-cell--chart" id="chart-1m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">1m</span><span class="trading-cell__title">Price Action</span></div>
                    <div class="trading-cell__content" id="chart-1m"></div>
                </div>
                <div class="trading-cell trading-cell--matrix" id="matrix-1m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">1m</span><span class="trading-cell__title">Transition Matrix</span></div>
                    <div class="trading-cell__content" id="matrix-1m"></div>
                </div>
                <div class="trading-cell trading-cell--chart" id="chart-15m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">15m</span><span class="trading-cell__title">Price Action</span></div>
                    <div class="trading-cell__content" id="chart-15m"></div>
                </div>
                <div class="trading-cell trading-cell--matrix" id="matrix-15m-container">
                    <div class="trading-cell__header"><span class="trading-cell__timeframe">15m</span><span class="trading-cell__title">Transition Matrix</span></div>
                    <div class="trading-cell__content" id="matrix-15m"></div>
                </div>
            </div>
        `;
        
        // Initialize calendar for replay mode
        const today = new Date();
        this.calendarDate = new Date(today);
        
        // CONTROL CENTER
        this.controlBody.innerHTML = `
            <div class="rtc-fullpanel">
                <!-- Top Stats Row -->
                <div class="rtc-stats-row">
                    <div class="rtc-stat-group">
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-avg">0.00</div><div class="rtc-stat-label">AVERAGE</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-15m">0.00</div><div class="rtc-stat-label">15M SCORE</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-1m">0.00</div><div class="rtc-stat-label">1M SCORE</div></div>
                    </div>
                    
                    <div class="rtc-orb-widget">
                        <button class="rtc-orb-arrow" id="rtc-prev">‹</button>
                        <div class="rtc-orb">
                            <img src="/static/img/avatars-000149516274-q1cu9n-t500x500.jpg" class="rtc-orb-img" />
                            <div class="rtc-orb-time" id="rtc-time">--:--</div>
                        </div>
                        <button class="rtc-orb-arrow" id="rtc-next">›</button>
                    </div>
                    
                    <div class="rtc-stat-group">
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-signals">0</div><div class="rtc-stat-label">SIGNALS</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-pf">0.00</div><div class="rtc-stat-label">PROFIT FACTOR</div></div>
                        <div class="rtc-stat-card"><div class="rtc-stat-value" id="rtc-net">$0</div><div class="rtc-stat-label">NET P/L</div></div>
                    </div>
                </div>
                
                <!-- Mode Toggle -->
                <div class="rtc-mode-toggle">
                    <button class="rtc-mode" data-mode="inactive">INACTIVE</button>
                    <button class="rtc-mode" data-mode="active">ACTIVE</button>
                    <button class="rtc-mode" data-mode="replay">REPLAY</button>
                </div>
                
                <!-- Bottom: Panels + Calendar -->
                <div class="rtc-main-area">
                    <!-- Live Trading Panel -->
                    <div class="rtc-panel rtc-panel--left">
                        <div class="rtc-panel-title">LIVE TRADING</div>
                        <div class="rtc-panel-body" id="rtc-trading-body">
                            <div class="rtc-row"><span>Position</span><span class="rtc-val">FLAT</span></div>
                            <div class="rtc-row"><span>Entry</span><span class="rtc-val">—</span></div>
                            <div class="rtc-row"><span>P/L</span><span class="rtc-val">$0.00</span></div>
                        </div>
                    </div>
                    
                    <!-- Calendar -->
                    <div class="rtc-calendar">
                        <!-- Date/Time Display -->
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
                        
                        <!-- Month Nav -->
                        <div class="rtc-cal-nav">
                            <button class="rtc-cal-nav-btn" id="rtc-cal-prev">‹</button>
                            <span class="rtc-cal-month" id="rtc-cal-month">${this.getMonthYear()}</span>
                            <button class="rtc-cal-nav-btn" id="rtc-cal-next">›</button>
                        </div>
                        
                        <!-- Day Headers -->
                        <div class="rtc-cal-days">
                            <span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span>
                        </div>
                        
                        <!-- Calendar Grid -->
                        <div class="rtc-cal-grid" id="rtc-cal-grid"></div>
                    </div>
                    
                    <!-- Analytics Panel -->
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
        this.updateModeDisplay();
        this.renderCalendarGrid();
        this.initTradingComponents(tab);
        this.startLiveClock();
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       MODE MANAGEMENT
       ═══════════════════════════════════════════════════════════════════════ */
    setMode(mode) {
        const prevMode = this.replayMode;
        this.replayMode = mode;
        
        // Handle double-click activation
        if (mode === 'active' && prevMode === 'active') {
            this.isTraderRunning = !this.isTraderRunning;
            if (this.isTraderRunning) {
                console.log('[APEX] Trader STARTED - Sentiment Engine ACTIVE');
                // Start sentiment engine in mock mode
                if (typeof ApexSentiment !== 'undefined') {
                    ApexSentiment.startEngine(this.activeSymbol, true); // true = mock mode
                }
            } else {
                console.log('[APEX] Trader STOPPED');
                // Stop sentiment engine
                if (typeof ApexSentiment !== 'undefined') {
                    ApexSentiment.stopEngine();
                }
            }
        } else if (mode === 'replay' && prevMode === 'replay') {
            this.isReplayRunning = !this.isReplayRunning;
            if (this.isReplayRunning) {
                console.log('[APEX] Replay STARTED');
            } else {
                console.log('[APEX] Replay PAUSED');
            }
        } else {
            // Mode changed, reset running states
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
        
        // Update mode button states
        document.querySelectorAll('.rtc-mode').forEach(btn => {
            btn.classList.remove('rtc-mode--active', 'rtc-mode--running');
            if (btn.dataset.mode === this.replayMode) {
                btn.classList.add('rtc-mode--active');
                
                // Add running glow if active and running
                if ((this.replayMode === 'active' && this.isTraderRunning) ||
                    (this.replayMode === 'replay' && this.isReplayRunning)) {
                    btn.classList.add('rtc-mode--running');
                }
            }
        });
        
        // Update date/time display based on mode
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
                // Active mode: Start = Today, Due = ∞ (Unlimited)
                this.calendarStartDate = new Date(today);
                this.calendarEndDate = null;
                if (startDateEl) startDateEl.innerHTML = `📅 ${this.formatDate(today)} <span class="rtc-cal-live">LIVE</span>`;
                if (endDateEl) endDateEl.innerHTML = `<span class="rtc-cal-infinity">∞</span> Unlimited`;
                if (startTimeEl) {
                    startTimeEl.value = this.formatTime(today);
                    startTimeEl.disabled = true;
                }
                if (endTimeEl) {
                    endTimeEl.value = '∞';
                    endTimeEl.disabled = true;
                }
                break;
                
            case 'replay':
                // Replay mode: Allow date range selection
                if (!this.calendarStartDate) {
                    // Default to last 7 days
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
        // Calculate analytics for selected date range
        if (!this.calendarStartDate || !this.calendarEndDate) {
            document.getElementById('rtc-winrate')?.textContent && (document.getElementById('rtc-winrate').textContent = '—%');
            document.getElementById('rtc-trades')?.textContent && (document.getElementById('rtc-trades').textContent = '0');
            document.getElementById('rtc-sharpe')?.textContent && (document.getElementById('rtc-sharpe').textContent = '—');
            return;
        }
        
        // Mock analytics calculation based on date range
        let totalScore = 0;
        let dayCount = 0;
        const start = this.calendarStartDate;
        const end = this.calendarEndDate;
        
        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            const key = this.getDateKey(d);
            if (this.dayPerformance[key]) {
                totalScore += this.dayPerformance[key];
                dayCount++;
            }
        }
        
        const avgScore = dayCount > 0 ? totalScore / dayCount : 0;
        const winRate = (avgScore * 100).toFixed(1);
        const trades = Math.floor(dayCount * 8); // ~8 trades per day
        const sharpe = (avgScore * 2.5).toFixed(2);
        
        const winrateEl = document.getElementById('rtc-winrate');
        const tradesEl = document.getElementById('rtc-trades');
        const sharpeEl = document.getElementById('rtc-sharpe');
        
        if (winrateEl) winrateEl.textContent = `${winRate}%`;
        if (tradesEl) tradesEl.textContent = trades.toString();
        if (sharpeEl) sharpeEl.textContent = sharpe;
    },
    
    /* ═══════════════════════════════════════════════════════════════════════
       CALENDAR METHODS
       ═══════════════════════════════════════════════════════════════════════ */
    getMonthYear() {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return `${months[this.calendarDate.getMonth()]} ${this.calendarDate.getFullYear()}`;
    },
    
    formatDate(date) {
        if (!date) return 'Select';
        const d = date.getDate().toString().padStart(2, '0');
        const m = (date.getMonth() + 1).toString().padStart(2, '0');
        const y = date.getFullYear();
        return `${d}-${m}-${y}`;
    },
    
    formatTime(date) {
        const h = date.getHours().toString().padStart(2, '0');
        const m = date.getMinutes().toString().padStart(2, '0');
        const s = date.getSeconds().toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    },
    
    getPerformanceColor(score) {
        if (score === undefined || score === null) return null;
        
        // Score 0-1, map to color gradient
        // Low (red) -> Medium (yellow) -> High (green)
        if (score < 0.4) {
            // Red range
            const intensity = Math.floor(60 + score * 100);
            return `rgba(180, ${intensity}, ${intensity}, 0.3)`;
        } else if (score < 0.6) {
            // Yellow range
            return `rgba(180, 160, 80, 0.3)`;
        } else if (score < 0.75) {
            // Light green
            return `rgba(120, 175, 130, 0.3)`;
        } else {
            // Strong green
            const intensity = Math.floor(140 + (score - 0.75) * 200);
            return `rgba(100, ${intensity}, 120, 0.4)`;
        }
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
        
        // Previous month days
        for (let i = 0; i < firstDayOfMonth; i++) {
            const day = daysInPrevMonth - firstDayOfMonth + 1 + i;
            html += `<div class="rtc-cal-day rtc-cal-day--other">${day}</div>`;
        }
        
        // Current month days with performance coloring
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            const dateKey = this.getDateKey(date);
            const isStart = this.calendarStartDate && this.isSameDay(date, this.calendarStartDate);
            const isEnd = this.calendarEndDate && this.isSameDay(date, this.calendarEndDate);
            const isInRange = this.isInRange(date);
            const isToday = this.isSameDay(date, new Date());
            const isFuture = date > new Date();
            
            // Get performance color
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
            const perfIndicator = perfScore !== undefined && !isFuture 
                ? `<span class="rtc-cal-perf" title="North Star: ${(perfScore * 100).toFixed(0)}%"></span>` 
                : '';
            
            html += `<div class="${cls}" data-date="${year}-${month + 1}-${day}" ${style}>${day}${perfIndicator}</div>`;
        }
        
        // Next month days
        const totalCells = firstDayOfMonth + daysInMonth;
        const cellsNeeded = Math.ceil(totalCells / 7) * 7;
        const remaining = cellsNeeded - totalCells;
        for (let day = 1; day <= remaining; day++) {
            html += `<div class="rtc-cal-day rtc-cal-day--other">${day}</div>`;
        }
        
        grid.innerHTML = html;
        
        // Bind click events (only in replay mode)
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
        return d1.getDate() === d2.getDate() && 
               d1.getMonth() === d2.getMonth() && 
               d1.getFullYear() === d2.getFullYear();
    },
    
    isInRange(date) {
        if (!this.calendarStartDate || !this.calendarEndDate) return false;
        return date > this.calendarStartDate && date < this.calendarEndDate;
    },
    
    initRelativityControls() {
        // Mode toggle with double-click detection
        document.querySelectorAll('.rtc-mode').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setMode(btn.dataset.mode);
            });
        });
        
        // Time arrows
        document.getElementById('rtc-prev')?.addEventListener('click', () => this.stepTime(-1));
        document.getElementById('rtc-next')?.addEventListener('click', () => this.stepTime(1));
        
        // Calendar nav
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
    
    stepTime(direction) {
        if (this.replayMode === 'replay') {
            this.replayTime += direction * 60000;
        }
    },
    
    initTradingComponents(tab) {
        this.cleanup();
        const symbolKey = tab.dbKey || this.activeSymbol;
        
        setTimeout(() => {
            this.loadChartData('1m', false, symbolKey);
            this.loadChartData('15m', false, symbolKey);
            this.loadMarkovData('1m');
            this.loadMarkovData('15m');
        }, 50);
        
        this.setupResizeHandler();
        
        this.refreshIntervals['1m'] = setInterval(() => this.loadChartData('1m', true, symbolKey), 60 * 1000);
        this.refreshIntervals['15m'] = setInterval(() => this.loadChartData('15m', true, symbolKey), 5 * 60 * 1000);
    },
    
    setupResizeHandler() {
        let resizeTimeout;
        const handleResize = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                ['1m', '15m'].forEach(tf => {
                    const container = document.getElementById(`chart-${tf}`);
                    if (container && this.charts[tf]) {
                        Plotly.Plots.resize(container);
                    }
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
        
        try {
            const response = await fetch(`/api/chart-data?timeframe=${timeframe}&limit=200&symbol=${symbol}`);
            const result = await response.json();
            
            if (result.success && result.data?.length > 0) {
                this.chartData[timeframe] = result.data;
                this.updatePriceRange(result.data);
                this.renderPlotlyChart(container, result.data, timeframe, result.symbol);
            } else {
                if (!this.chartData[timeframe]) {
                    this.chartData[timeframe] = this.generateDemoOHLCV(200, timeframe);
                    this.updatePriceRange(this.chartData[timeframe]);
                }
                this.renderPlotlyChart(container, this.chartData[timeframe], timeframe, symbol);
            }
        } catch (e) {
            if (!this.chartData[timeframe]) {
                this.chartData[timeframe] = this.generateDemoOHLCV(200, timeframe);
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
        // Calculate optimal bar count based on container width
        const containerWidth = container.clientWidth || 600;
        const minCandleWidth = 8; // Minimum pixels per candle for clarity
        const maxBars = Math.floor(containerWidth / minCandleWidth);
        
        // Get user-selected bar count but cap at what fits well
        const userBarCount = typeof ApexIndicators !== 'undefined' 
            ? ApexIndicators.getBarCount(timeframe) 
            : 100;
        const barCount = Math.min(userBarCount, maxBars, data.length);
        
        const chartData = data.slice(-barCount);
        
        const highs = chartData.map(d => parseFloat(d.high));
        const lows = chartData.map(d => parseFloat(d.low));
        const dataMin = Math.min(...lows);
        const dataMax = Math.max(...highs);
        const padding = (dataMax - dataMin) * 0.05;
        const yMin = dataMin - padding;
        const yMax = dataMax + padding;
        
        // Use numeric indices for x-axis to eliminate gaps
        // This prevents the scatter plot appearance from time gaps
        const xIndices = chartData.map((d, i) => i);
        const xLabels = chartData.map((d, i) => {
            const date = new Date(d.timestamp || d.time);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
        });
        
        // Create tick values - show label every N bars
        const tickStep = Math.max(1, Math.floor(chartData.length / 8));
        const tickVals = [];
        const tickText = [];
        for (let i = 0; i < chartData.length; i += tickStep) {
            tickVals.push(i);
            tickText.push(xLabels[i]);
        }
        
        const traces = [{
            type: 'candlestick',
            x: xIndices,  // Use numeric indices
            open: chartData.map(d => parseFloat(d.open)),
            high: chartData.map(d => parseFloat(d.high)),
            low: chartData.map(d => parseFloat(d.low)),
            close: chartData.map(d => parseFloat(d.close)),
            name: symbolName,
            increasing: { 
                line: { color: '#7EAE8B', width: 1 }, 
                fillcolor: '#7EAE8B' 
            },
            decreasing: { 
                line: { color: '#4A6A8A', width: 1 }, 
                fillcolor: '#4A6A8A' 
            }
            // Don't set whiskerwidth - let Plotly use default which shows proper wicks
        }];
        
        if (typeof ApexIndicators !== 'undefined') {
            const indicatorTraces = ApexIndicators.generateTraces(chartData, timeframe, xIndices);
            traces.push(...indicatorTraces);
        }
        
        const layout = {
            autosize: true,
            paper_bgcolor: 'transparent', 
            plot_bgcolor: 'transparent',
            font: { color: '#9CA3AF', size: 10, family: 'Inter, sans-serif' },
            margin: { l: 0, r: 50, t: 0, b: 25, pad: 0 },
            xaxis: { 
                type: 'linear',  // Linear axis with custom tick labels
                tickmode: 'array',
                tickvals: tickVals,
                ticktext: tickText,
                gridcolor: 'rgba(255,255,255,0.025)', 
                rangeslider: { visible: false }, 
                fixedrange: true,
                showgrid: true,
                zeroline: false,
                tickfont: { size: 9, color: '#6B7280' },
                tickangle: 0,
                automargin: true
            },
            yaxis: { 
                side: 'right', 
                gridcolor: 'rgba(255,255,255,0.025)', 
                range: [yMin, yMax], 
                fixedrange: true,
                showgrid: true,
                zeroline: false,
                tickformat: '.0f',
                tickfont: { size: 9, color: '#6B7280' },
                automargin: true
            },
            showlegend: false, 
            dragmode: false,
            hovermode: 'x unified',
            hoverlabel: {
                bgcolor: 'rgba(20, 22, 26, 0.95)',
                bordercolor: 'rgba(255, 255, 255, 0.1)',
                font: { size: 10, color: '#E5E7EB' }
            }
        };
        
        const config = { 
            displayModeBar: false, 
            responsive: true, 
            scrollZoom: false, 
            doubleClick: false,
            staticPlot: false
        };
        
        Plotly.newPlot(container, traces, layout, config);
        this.charts[timeframe] = container;
        
        if (typeof ApexIndicators !== 'undefined') {
            ApexIndicators.renderSettingsButton(container, timeframe);
            ApexIndicators.renderLegend(container, timeframe);
        }
    },
    
    async loadMarkovData(timeframe) {
        const container = document.getElementById(`matrix-${timeframe}`);
        if (!container) return;
        
        if (!this.matrices[timeframe + '_data']) {
            this.matrices[timeframe + '_data'] = this.generateDemoMatrix();
        }
        
        const matrix = this.matrices[timeframe + '_data'];
        const currentState = Math.floor(Math.random() * 5);
        
        if (typeof ApexMarkovMatrix !== 'undefined') {
            this.matrices[timeframe] = new ApexMarkovMatrix(container, {
                cellWidth: 38, cellHeight: 26, labelWidth: 28,
                showLegend: false, showLabels: true
            });
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
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        display.textContent = `${hours}:${minutes}`;
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
            const high = Math.max(open, close) + seededRandom() * 1.5;
            const low = Math.min(open, close) - seededRandom() * 1.5;
            
            data.push({
                timestamp: new Date(now - i * interval).toISOString(),
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2)),
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
            for (let j = 0; j < 5; j++) {
                const prob = Math.random() * (Math.abs(i - j) === 0 ? 2 : 1);
                row.push(prob);
                sum += prob;
            }
            matrix.push(row.map(p => p / sum));
        }
        return matrix;
    },
    
    cleanup() {
        ['1m', '15m'].forEach(tf => {
            const container = document.getElementById(`chart-${tf}`);
            if (container) try { Plotly.purge(container); } catch (e) {}
        });
        this.charts = { '1m': null, '15m': null };
        
        Object.keys(this.matrices).forEach(key => {
            if (!key.endsWith('_data') && this.matrices[key]?.destroy) this.matrices[key].destroy();
        });
        
        if (this.clockInterval) { clearInterval(this.clockInterval); this.clockInterval = null; }
        Object.keys(this.refreshIntervals).forEach(tf => {
            if (this.refreshIntervals[tf]) { clearInterval(this.refreshIntervals[tf]); this.refreshIntervals[tf] = null; }
        });
        
        if (this._resizeHandler) {
            window.removeEventListener('resize', this._resizeHandler);
            this._resizeHandler = null;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Plotly === 'undefined') return;
    ApexViewRenderer.init();
});

window.ApexViewRenderer = ApexViewRenderer;
