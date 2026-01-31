/* ═══════════════════════════════════════════════════════════════════════════
   DATABASE PANEL: US30Z25 (Dow Jones Futures)
   Hardcoded endpoint mapping to US30Z25_intelligence.db
   ═══════════════════════════════════════════════════════════════════════════ */

const DB_US30Z25 = {
    SYMBOL_ID: 'US30Z25',
    SYMBOL_NAME: 'Dow Jones Futures',
    SYMBOL_TICKER: 'US30Z25.sim',
    DB_PATH: 'US30Z25_intelligence.db',
    
    currentSource: 'profiles',
    currentTable: 'core',
    currentTimeframe: '15m',
    profiles: [],
    hyperspheres: [],
    
    endpoints: {
        profiles: '/api/profiles?symbol=US30Z25',
        hyperspheres: '/api/hyperspheres?symbol=US30Z25',
        core: '/api/chart-data?symbol=US30Z25',
        basic: '/api/basic?symbol=US30Z25',
        advanced: '/api/advanced?symbol=US30Z25',
        fibonacci: '/api/fibonacci?symbol=US30Z25',
        ath: '/api/ath?symbol=US30Z25',
        stats: '/api/symbols'
    },
    
    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) { console.error('[DB_US30Z25] Container not found:', containerId); return; }
        this.render();
        this.loadData();
    },
    
    render() {
        this.container.innerHTML = `
            <div class="database-split-panels" data-symbol="US30Z25">
                <div class="database-panel">
                    <div class="database-panel__header">
                        <div class="database-tab-group">
                            <button class="db-tab ${this.currentSource === 'profiles' ? 'active' : ''}" data-source="profiles">Profiles</button>
                            <button class="db-tab ${this.currentSource === 'hyperspheres' ? 'active' : ''}" data-source="hyperspheres">Hyperspheres</button>
                        </div>
                    </div>
                    <div class="database-panel__content" id="us30z25-left-panel"><div class="database-loading">Loading...</div></div>
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
                    <div class="database-panel__content" id="us30z25-right-panel"><div class="database-loading">Loading...</div></div>
                </div>
            </div>
        `;
        this.initControls();
    },
    
    initControls() {
        this.container.querySelectorAll('.db-tab[data-source]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-source]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active'); this.currentSource = tab.dataset.source; this.loadLeftPanel();
            });
        });
        this.container.querySelectorAll('.db-tab[data-table]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-table]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active'); this.currentTable = tab.dataset.table; this.loadRightPanel();
            });
        });
        this.container.querySelectorAll('.db-tab[data-tf]').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.db-tab[data-tf]').forEach(t => t.classList.remove('active'));
                tab.classList.add('active'); this.currentTimeframe = tab.dataset.tf; this.loadRightPanel();
            });
        });
    },
    
    async loadData() { await Promise.all([this.loadProfiles(), this.loadHyperspheres()]); this.loadLeftPanel(); this.loadRightPanel(); },
    async loadProfiles() { try { const r = await fetch(this.endpoints.profiles); const d = await r.json(); if (d.success) this.profiles = d.profiles || []; } catch (e) { this.profiles = []; } },
    async loadHyperspheres() { try { const r = await fetch(this.endpoints.hyperspheres); const d = await r.json(); if (d.success) this.hyperspheres = d.hyperspheres || []; } catch (e) { this.hyperspheres = []; } },
    
    loadLeftPanel() {
        const c = document.getElementById('us30z25-left-panel'); if (!c) return;
        c.innerHTML = this.currentSource === 'profiles' ? this.renderProfilesTable() : this.renderHyperspheresTable();
    },
    
    async loadRightPanel() {
        const c = document.getElementById('us30z25-right-panel'); if (!c) return;
        c.innerHTML = '<div class="database-loading">Loading...</div>';
        try {
            const r = await fetch(`${this.endpoints[this.currentTable]}&timeframe=${this.currentTimeframe}&limit=100`);
            const d = await r.json();
            if (d.success && d.data?.length > 0) c.innerHTML = this.renderDataTable(d.data);
            else c.innerHTML = '<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Data</div></div>';
        } catch (e) { c.innerHTML = '<div class="database-error">Error loading data</div>'; }
    },
    
    renderProfilesTable() {
        if (!this.profiles.length) return '<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Profiles</div></div>';
        let h = '<table class="database-table"><thead><tr><th>Name</th><th>North Star</th><th>PF</th><th>Win Rate</th><th>Signals</th><th>Rank</th></tr></thead><tbody>';
        this.profiles.forEach(p => { const m = p.metrics || {}; h += `<tr><td>${p.display_name || p.profile_id}</td><td class="cell-bull">${m.north_star?.toFixed(2) || '--'}</td><td>${m.profit_factor?.toFixed(2) || '--'}</td><td>${m.win_rate ? (m.win_rate*100).toFixed(1)+'%' : '--'}</td><td>${m.signals_generated || '--'}</td><td>#${m.rank || '--'}</td></tr>`; });
        return h + '</tbody></table>';
    },
    
    renderHyperspheresTable() {
        if (!this.hyperspheres.length) return '<div class="database-empty-state"><div class="database-empty-state__icon">◎</div><div class="database-empty-state__title">No Hyperspheres</div></div>';
        let h = '<table class="database-table"><thead><tr><th>Name</th><th>Type</th><th>States</th><th>Accuracy</th><th>Updated</th></tr></thead><tbody>';
        this.hyperspheres.forEach(hs => { const a = hs.accuracy ? (hs.accuracy*100).toFixed(1)+'%' : '--'; h += `<tr><td>${hs.name || 'Unnamed'}</td><td>${hs.classifier_type || 'MarkovChain'}</td><td>${hs.state_count || 5}</td><td class="${parseFloat(a)>60?'cell-bull':''}">${a}</td><td>${hs.last_trained ? new Date(hs.last_trained).toLocaleDateString() : '--'}</td></tr>`; });
        return h + '</tbody></table>';
    },
    
    renderDataTable(data) {
        const cols = { core: ['timestamp','open','high','low','close','volume'], basic: ['timestamp','atr_14','atr_50_avg','atr_ratio','ema_short','ema_medium','supertrend'], advanced: ['timestamp','rsi_14','cci_14','stoch_k_14','macd_line_12_26','bb_width_20','obv'], fibonacci: ['timestamp','current_fib_zone','in_golden_zone','zone_multiplier','fib_level_0382','fib_level_0618'], ath: ['timestamp','current_ath','current_close','ath_distance_pct','ath_zone'] }[this.currentTable] || Object.keys(data[0]);
        let h = '<table class="database-table"><thead><tr>' + cols.map(c => `<th>${c.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</th>`).join('') + '</tr></thead><tbody>';
        data.forEach(row => { h += '<tr>'; cols.forEach(col => { let v = row[col], cls = ''; if (v == null) v = '--'; else if (typeof v === 'number') v = col.includes('volume') || col.includes('obv') ? Math.round(v).toLocaleString() : col.includes('pct') || col.includes('ratio') ? v.toFixed(2)+'%' : v.toFixed(4); else if (col === 'supertrend') cls = v === 'BULL' ? 'cell-bull' : v === 'BEAR' ? 'cell-bear' : ''; else if (col === 'in_golden_zone') { v = v ? 'YES' : 'NO'; cls = v === 'YES' ? 'cell-bull' : ''; } else if (col === 'ath_zone') cls = v === 'NEAR_ATH' ? 'cell-bull' : v === 'FAR_FROM_ATH' ? 'cell-bear' : ''; h += `<td class="${cls}">${v}</td>`; }); h += '</tr>'; });
        return h + '</tbody></table>';
    }
};
window.DB_US30Z25 = DB_US30Z25;
