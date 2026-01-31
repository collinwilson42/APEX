/* ═══════════════════════════════════════════════════════════════════════════
   DATABASE PANEL: XAUJ26 (Gold Futures - April 2026)
   Hardcoded endpoint mapping to XAUJ26_intelligence.db
   ═══════════════════════════════════════════════════════════════════════════ */

const DB_XAUJ26 = {
    // Database Configuration
    SYMBOL_ID: 'XAUJ26',
    SYMBOL_NAME: 'Gold Futures',
    SYMBOL_TICKER: 'XAUJ26.sim',
    DB_PATH: 'XAUJ26_intelligence.db',
    
    // Panel State
    currentSource: 'profiles',
    currentTable: 'core',
    currentTimeframe: '15m',
    profiles: [],
    hyperspheres: [],
    
    // API Endpoints (hardcoded to this symbol)
    endpoints: {
        profiles: '/api/profiles?symbol=XAUJ26',
        hyperspheres: '/api/hyperspheres?symbol=XAUJ26',
        core: '/api/chart-data?symbol=XAUJ26',
        basic: '/api/basic?symbol=XAUJ26',
        advanced: '/api/advanced?symbol=XAUJ26',
        fibonacci: '/api/fibonacci?symbol=XAUJ26',
        ath: '/api/ath?symbol=XAUJ26',
        stats: '/api/symbols'
    },
    
    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[DB_XAUJ26] Container not found:', containerId);
            return;
        }
        this.render();
        this.loadData();
    },
    
    render() {
        this.container.innerHTML = `
            <div class="database-split-panels" data-symbol="XAUJ26">
                <!-- LEFT PANEL: Profiles / Hyperspheres -->
                <div class="database-panel">
                    <div class="database-panel__header">
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentSource === 'profiles' ? 'active' : ''}" data-source="profiles">Profiles</button>
                            <button class="db-tab ${this.currentSource === 'hyperspheres' ? 'active' : ''}" data-source="hyperspheres">Hyperspheres</button>
                        </div>
                    </div>
                    <div class="database-panel__content" id="xauj26-left-panel">
                        <div class="database-loading">Loading...</div>
                    </div>
                </div>
                
                <!-- RIGHT PANEL: Indicators + Timeframe -->
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
                    <div class="database-panel__content" id="xauj26-right-panel">
                        <div class="database-loading">Loading...</div>
                    </div>
                </div>
            </div>
        `;
        
        this.initControls();
    },
    
    initControls() {
        this.container.querySelectorAll('.db-tab[data-source]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-source]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentSource = tab.dataset.source;
                this.loadLeftPanel();
            });
        });
        
        this.container.querySelectorAll('.db-tab[data-table]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-table]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTable = tab.dataset.table;
                this.loadRightPanel();
            });
        });
        
        this.container.querySelectorAll('.db-tab[data-tf]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-tf]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTimeframe = tab.dataset.tf;
                this.loadRightPanel();
            });
        });
    },
    
    async loadData() {
        await Promise.all([
            this.loadProfiles(),
            this.loadHyperspheres()
        ]);
        this.loadLeftPanel();
        this.loadRightPanel();
    },
    
    async loadProfiles() {
        try {
            const response = await fetch(this.endpoints.profiles);
            const result = await response.json();
            if (result.success) {
                this.profiles = result.profiles || [];
            }
        } catch (e) {
            console.warn('[DB_XAUJ26] Failed to load profiles:', e.message);
            this.profiles = [];
        }
    },
    
    async loadHyperspheres() {
        try {
            const response = await fetch(this.endpoints.hyperspheres);
            const result = await response.json();
            if (result.success) {
                this.hyperspheres = result.hyperspheres || [];
            }
        } catch (e) {
            console.warn('[DB_XAUJ26] Failed to load hyperspheres:', e.message);
            this.hyperspheres = [];
        }
    },
    
    loadLeftPanel() {
        const container = document.getElementById('xauj26-left-panel');
        if (!container) return;
        
        if (this.currentSource === 'profiles') {
            container.innerHTML = this.renderProfilesTable();
        } else {
            container.innerHTML = this.renderHyperspheresTable();
        }
    },
    
    async loadRightPanel() {
        const container = document.getElementById('xauj26-right-panel');
        if (!container) return;
        
        container.innerHTML = '<div class="database-loading">Loading...</div>';
        
        const endpoint = this.endpoints[this.currentTable];
        const url = `${endpoint}&timeframe=${this.currentTimeframe}&limit=100`;
        
        try {
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success && result.data && result.data.length > 0) {
                container.innerHTML = this.renderDataTable(result.data);
            } else {
                container.innerHTML = `
                    <div class="database-empty-state">
                        <div class="database-empty-state__icon">◎</div>
                        <div class="database-empty-state__title">No Data</div>
                        <div class="database-empty-state__subtitle">Run fillall.py to populate ${this.SYMBOL_ID}</div>
                    </div>
                `;
            }
        } catch (e) {
            console.warn('[DB_XAUJ26] Right panel error:', e.message);
            container.innerHTML = '<div class="database-error">Error loading data</div>';
        }
    },
    
    renderProfilesTable() {
        if (this.profiles.length === 0) {
            return `
                <div class="database-empty-state">
                    <div class="database-empty-state__icon">◎</div>
                    <div class="database-empty-state__title">No Profiles</div>
                    <div class="database-empty-state__subtitle">Create a profile for ${this.SYMBOL_NAME}</div>
                </div>
            `;
        }
        
        let html = `<table class="database-table"><thead><tr>
            <th>Name</th><th>North Star</th><th>Profit Factor</th><th>Win Rate</th><th>Signals</th><th>Rank</th>
        </tr></thead><tbody>`;
        
        this.profiles.forEach(p => {
            const m = p.metrics || {};
            html += `<tr>
                <td>${p.display_name || p.profile_id}</td>
                <td class="cell-bull">${m.north_star?.toFixed(2) || '--'}</td>
                <td>${m.profit_factor?.toFixed(2) || '--'}</td>
                <td>${m.win_rate ? (m.win_rate * 100).toFixed(1) + '%' : '--'}</td>
                <td>${m.signals_generated || '--'}</td>
                <td>#${m.rank || '--'}</td>
            </tr>`;
        });
        
        return html + '</tbody></table>';
    },
    
    renderHyperspheresTable() {
        if (this.hyperspheres.length === 0) {
            return `
                <div class="database-empty-state">
                    <div class="database-empty-state__icon">◎</div>
                    <div class="database-empty-state__title">No Hyperspheres</div>
                    <div class="database-empty-state__subtitle">Configure hyperspheres for ${this.SYMBOL_NAME}</div>
                </div>
            `;
        }
        
        let html = `<table class="database-table"><thead><tr>
            <th>Name</th><th>Type</th><th>States</th><th>Accuracy</th><th>Last Updated</th>
        </tr></thead><tbody>`;
        
        this.hyperspheres.forEach(hs => {
            const acc = hs.accuracy ? (hs.accuracy * 100).toFixed(1) + '%' : '--';
            const updated = hs.last_trained ? new Date(hs.last_trained).toLocaleDateString() : '--';
            html += `<tr>
                <td>${hs.name || 'Unnamed'}</td>
                <td>${hs.classifier_type || 'MarkovChain'}</td>
                <td>${hs.state_count || 5}</td>
                <td class="${parseFloat(acc) > 60 ? 'cell-bull' : ''}">${acc}</td>
                <td>${updated}</td>
            </tr>`;
        });
        
        return html + '</tbody></table>';
    },
    
    renderDataTable(data) {
        const columns = this.getColumnsForTable(this.currentTable, data[0]);
        
        let html = `<table class="database-table"><thead><tr>
            ${columns.map(c => `<th>${this.formatColumnName(c)}</th>`).join('')}
        </tr></thead><tbody>`;
        
        data.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                let val = row[col];
                let cls = '';
                
                if (val === null || val === undefined) {
                    val = '--';
                } else if (typeof val === 'number') {
                    if (col.includes('volume') || col.includes('obv')) {
                        val = Math.round(val).toLocaleString();
                    } else if (col.includes('pct') || col.includes('ratio')) {
                        val = val.toFixed(2) + '%';
                    } else {
                        val = val.toFixed(4);
                    }
                } else if (col === 'supertrend') {
                    cls = val === 'BULL' ? 'cell-bull' : val === 'BEAR' ? 'cell-bear' : '';
                } else if (col === 'in_golden_zone') {
                    val = val ? 'YES' : 'NO';
                    cls = val === 'YES' ? 'cell-bull' : '';
                } else if (col === 'ath_zone') {
                    cls = val === 'NEAR_ATH' ? 'cell-bull' : val === 'FAR_FROM_ATH' ? 'cell-bear' : '';
                }
                
                html += `<td class="${cls}">${val}</td>`;
            });
            html += '</tr>';
        });
        
        return html + '</tbody></table>';
    },
    
    getColumnsForTable(tableName, sampleRow) {
        const columnMap = {
            'core': ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
            'basic': ['timestamp', 'atr_14', 'atr_50_avg', 'atr_ratio', 'ema_short', 'ema_medium', 'supertrend'],
            'advanced': ['timestamp', 'rsi_14', 'cci_14', 'stoch_k_14', 'macd_line_12_26', 'bb_width_20', 'obv'],
            'fibonacci': ['timestamp', 'current_fib_zone', 'in_golden_zone', 'zone_multiplier', 'fib_level_0382', 'fib_level_0618'],
            'ath': ['timestamp', 'current_ath', 'current_close', 'ath_distance_pct', 'ath_zone']
        };
        return columnMap[tableName] || Object.keys(sampleRow);
    },
    
    formatColumnName(col) {
        return col
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace('Atr', 'ATR').replace('Ema', 'EMA').replace('Rsi', 'RSI')
            .replace('Cci', 'CCI').replace('Macd', 'MACD').replace('Obv', 'OBV')
            .replace('Ath', 'ATH').replace('Bb', 'BB').replace('Fib', 'Fib');
    }
};

window.DB_XAUJ26 = DB_XAUJ26;
