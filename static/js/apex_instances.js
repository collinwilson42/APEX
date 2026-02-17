/* ═══════════════════════════════════════════════════════════════════════════
   APEX INSTANCE BROWSER V4.0 - The Sentient Ledger (Seed 18)
   
   Seed 10D: Dual-Timeframe Sentiments & Live Position Feed
   Seed 18:  ATH replaces Volume, DB-driven scoring, cell-tap drill-down
   
   Features:
   - POSITIONS tab: Unified, single table (no timeframe split)
   - SENTIMENTS tab: Dual-timeframe sub-tabs [15M | 1H]
   - Score columns: PA, KL, MOM, ATH, STR, COMP, BIAS
   - Cell-tap popover: click any score/header for weight breakdown
   - Live MT5 position sync indicator
   - Multiple instances can run simultaneously (per-instance config)
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexInstanceBrowser = {
    container: null,
    currentSymbol: null,
    currentSymbolId: null,
    currentInstanceId: null,
    currentTab: 'positions',
    currentSentimentTimeframe: '15m',
    isDropdownOpen: false,
    isLoading: false,
    syncStatus: null,
    
    dataCache: { 
        positions: null, 
        sentiments_15m: null,
        sentiments_1h: null, 
        transitions: null, 
        matrices: null 
    },
    
    TRADING_VIEWS_KEY: 'apex_trading_views',
    SELECTED_INSTANCE_KEY: 'apex_selected_instance',
    
    tabs: [
        { id: 'positions', label: 'Positions', icon: '◆', endpoint: '/api/instance/{id}/positions', hasSubTabs: false },
        { id: 'sentiments', label: 'Sentiments', icon: '◈', endpoint: '/api/instance/{id}/sentiments', hasSubTabs: true, subTabs: ['15M', '1H'] },
        { id: 'transitions', label: 'Transitions', icon: '⇄', endpoint: '/api/instance/{id}/transitions', hasSubTabs: false },
        { id: 'matrices', label: 'Matrices', icon: '▦', endpoint: '/api/instance/{id}/matrices', hasSubTabs: false }
    ],
    
    init(container, symbolId) {
        this.container = container;
        this.currentSymbolId = symbolId;
        this.currentSymbol = symbolId ? symbolId.toUpperCase() : null;
        this.restoreSelection();
        this.render();
        this.bindGlobalEvents();
        this.startSyncStatusPolling();
        console.log('[InstanceBrowser] V4.0 Initialized for symbol:', this.currentSymbol);
    },
    
    restoreSelection() {
        try {
            const saved = localStorage.getItem(this.SELECTED_INSTANCE_KEY);
            if (saved) {
                const { instanceId, name } = JSON.parse(saved);
                this.currentInstanceId = instanceId;
                console.log('[InstanceBrowser] Restored selection:', name);
            }
        } catch (e) { console.warn('[InstanceBrowser] Failed to restore selection:', e); }
    },
    
    saveSelection(instanceId, name, symbol) {
        try {
            localStorage.setItem(this.SELECTED_INSTANCE_KEY, JSON.stringify({ instanceId, name, symbol, timestamp: Date.now() }));
        } catch (e) { console.warn('[InstanceBrowser] Failed to save selection:', e); }
    },
    
    getSavedSelection() {
        try {
            const saved = localStorage.getItem(this.SELECTED_INSTANCE_KEY);
            return saved ? JSON.parse(saved) : null;
        } catch (e) { return null; }
    },
    
    startSyncStatusPolling() {
        setInterval(() => {
            if (this.currentInstanceId && this.currentTab === 'positions') {
                this.fetchSyncStatus();
            }
        }, 2000);
    },
    
    async fetchSyncStatus() {
        try {
            const response = await fetch(`/api/instance/${this.currentInstanceId}/sync/status`);
            const result = await response.json();
            if (result.success) { this.syncStatus = result.data; this.updateSyncIndicator(); }
        } catch (e) {}
    },
    
    updateSyncIndicator() {
        const indicator = document.getElementById('sync-indicator');
        if (!indicator) return;
        if (this.syncStatus?.running) {
            indicator.className = 'sync-indicator sync-indicator--active';
            indicator.innerHTML = `<span class="sync-indicator__dot"></span><span class="sync-indicator__label">LIVE</span><span class="sync-indicator__count">${this.syncStatus.position_count || 0}</span>`;
        } else {
            indicator.className = 'sync-indicator sync-indicator--offline';
            indicator.innerHTML = `<span class="sync-indicator__dot"></span><span class="sync-indicator__label">OFFLINE</span>`;
        }
    },
    
    async toggleSync() {
        if (!this.currentInstanceId) return;
        const action = this.syncStatus?.running ? 'stop' : 'start';
        const symbol = this.getSavedSelection()?.symbol || 'XAUJ26';
        try {
            const response = await fetch(`/api/instance/${this.currentInstanceId}/sync/${action}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol })
            });
            const result = await response.json();
            if (result.success) {
                await this.fetchSyncStatus();
                if (action === 'start') { this.dataCache.positions = null; this.loadTabContent(); }
            }
        } catch (e) { console.error('[InstanceBrowser] Sync toggle failed:', e); }
    },
    
    render() {
        const savedSelection = this.getSavedSelection();
        const headerLabel = savedSelection?.name || 'Select Algorithm';
        const headerStatus = savedSelection?.symbol ? this.formatSymbol(savedSelection.symbol) : '';
        const statusClass = savedSelection ? 'instance-selector__status instance-selector__status--active' : 'instance-selector__status';
        
        this.container.innerHTML = `
            <div class="instance-browser">
                <div class="instance-browser__header">
                    <button class="instance-hamburger" id="instance-hamburger">
                        <span class="hamburger-line"></span><span class="hamburger-line"></span><span class="hamburger-line"></span>
                    </button>
                    <div class="instance-selector" id="instance-selector">
                        <span class="instance-selector__label" id="instance-label">${headerLabel}</span>
                        <span class="${statusClass}" id="instance-status">${headerStatus}</span>
                    </div>
                    ${this.renderTimeframeTabs()}
                </div>
                <div class="instance-dropdown" id="instance-dropdown">
                    <div class="instance-dropdown__content" id="instance-dropdown-content"></div>
                </div>
                <div class="instance-tabs" id="instance-tabs">
                    ${this.tabs.map(tab => `
                        <button class="instance-tab ${tab.id === this.currentTab ? 'instance-tab--active' : ''}" data-tab="${tab.id}">
                            <span class="instance-tab__icon">${tab.icon}</span>
                            <span class="instance-tab__label">${tab.label}</span>
                        </button>
                    `).join('')}
                </div>
                ${this.renderSubTabs()}
                <div class="instance-content" id="instance-content">
                    <div class="instance-empty"><div class="instance-empty__icon">◎</div><div class="instance-empty__text">Select an algorithm</div></div>
                </div>
            </div>
        `;
        this.bindEvents();
        this.renderDropdownContent();
        if (this.currentInstanceId) this.loadTabContent();
    },
    
    renderTimeframeTabs() {
        return `
            <div class="instance-timeframe-tabs" id="timeframe-tabs">
                <button class="tf-tab ${this.currentSentimentTimeframe === '15m' ? 'tf-tab--active' : ''}" data-tf="15m" onclick="ApexInstanceBrowser.switchSentimentTimeframe('15m')">15M</button>
                <button class="tf-tab ${this.currentSentimentTimeframe === '1h' ? 'tf-tab--active' : ''}" data-tf="1h" onclick="ApexInstanceBrowser.switchSentimentTimeframe('1h')">1H</button>
            </div>
        `;
    },
    
    renderSubTabs() {
        const currentTabConfig = this.tabs.find(t => t.id === this.currentTab);
        if (!currentTabConfig?.hasSubTabs) return '';
        return `
            <div class="instance-subtabs" id="instance-subtabs">
                ${currentTabConfig.subTabs.map(st => {
                    const tf = st.toLowerCase();
                    const isActive = this.currentSentimentTimeframe === tf;
                    return `<button class="instance-subtab ${isActive ? 'instance-subtab--active' : ''}" data-subtab="${tf}" onclick="ApexInstanceBrowser.switchSentimentTimeframe('${tf}')">${st}</button>`;
                }).join('')}
            </div>
        `;
    },
    
    switchSentimentTimeframe(timeframe) {
        this.currentSentimentTimeframe = timeframe;
        document.querySelectorAll('.instance-subtab, .tf-tab').forEach(btn => {
            btn.classList.toggle('instance-subtab--active', btn.dataset.subtab === timeframe || btn.dataset.tf === timeframe);
            btn.classList.toggle('tf-tab--active', btn.dataset.tf === timeframe);
        });
        if (this.currentTab === 'sentiments') this.loadTabContent();
    },
    
    bindEvents() {
        const hamburger = document.getElementById('instance-hamburger');
        const selector = document.getElementById('instance-selector');
        const toggleDropdown = (e) => {
            e.stopPropagation();
            this.isDropdownOpen = !this.isDropdownOpen;
            document.getElementById('instance-dropdown')?.classList.toggle('instance-dropdown--open', this.isDropdownOpen);
            hamburger?.classList.toggle('instance-hamburger--open', this.isDropdownOpen);
            if (this.isDropdownOpen) this.renderDropdownContent();
        };
        hamburger?.addEventListener('click', toggleDropdown);
        selector?.addEventListener('click', toggleDropdown);
        document.getElementById('instance-tabs')?.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.instance-tab');
            if (tabBtn) this.switchTab(tabBtn.dataset.tab);
        });
    },
    
    bindGlobalEvents() {
        document.addEventListener('click', (e) => {
            const header = this.container?.querySelector('.instance-browser__header');
            const dropdown = document.getElementById('instance-dropdown');
            if (this.isDropdownOpen && !header?.contains(e.target) && !dropdown?.contains(e.target)) this.closeDropdown();
            const contextMenu = document.getElementById('algo-context-menu');
            if (contextMenu && !contextMenu.contains(e.target)) this.hideContextMenu();
        });
    },
    
    closeDropdown() {
        this.isDropdownOpen = false;
        document.getElementById('instance-dropdown')?.classList.remove('instance-dropdown--open');
        document.getElementById('instance-hamburger')?.classList.remove('instance-hamburger--open');
    },
    
    getSavedViews() { try { return JSON.parse(localStorage.getItem(this.TRADING_VIEWS_KEY) || '[]'); } catch (e) { return []; } },
    saveViews(views) { try { localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views)); } catch (e) {} },
    updateView(viewId, updates) {
        const views = this.getSavedViews();
        const idx = views.findIndex(v => v.id === viewId);
        if (idx >= 0) { views[idx] = { ...views[idx], ...updates }; this.saveViews(views); }
    },
    
    renderDropdownContent() {
        const content = document.getElementById('instance-dropdown-content');
        if (!content) return;
        const allViews = this.getSavedViews();
        const favorites = allViews.filter(v => v.favorite && !v.archived);
        const active = allViews.filter(v => !v.favorite && !v.archived);
        const archived = allViews.filter(v => v.archived);
        const sortByRecent = (a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0);
        favorites.sort(sortByRecent); active.sort(sortByRecent);
        archived.sort((a, b) => (b.archivedAt || 0) - (a.archivedAt || 0));
        let html = '';
        if (favorites.length > 0) { html += '<div class="algo-section-header algo-section-header--favorites">★ FAVORITES</div>'; favorites.forEach(v => { html += this.renderCard(v, true, false); }); }
        html += '<div class="algo-section-header">SAVED ALGORITHMS</div>';
        if (active.length === 0 && favorites.length === 0) { html += '<div class="algo-empty"><div class="algo-empty__text">No saved algorithms</div><div class="algo-empty__hint">Create one from the APEX menu</div></div>'; }
        else { active.forEach(v => { html += this.renderCard(v, false, false); }); if (active.length === 0) html += '<div class="algo-empty"><div class="algo-empty__hint">All in Favorites above</div></div>'; }
        if (archived.length > 0) { html += '<div class="algo-divider"></div><div class="algo-section-header algo-section-header--archived">ARCHIVED</div>'; archived.forEach(v => { html += this.renderCard(v, false, true); }); }
        content.innerHTML = html;
        this.bindCardEvents(content);
    },
    
    renderCard(view, isFavorite, isArchived) {
        const time = this.formatTimestamp(view.lastAccessed || view.createdAt);
        const symbol = this.formatSymbol(view.symbol);
        const selected = view.id === this.currentInstanceId;
        let cls = 'algo-card';
        if (selected) cls += ' algo-card--selected';
        if (isArchived) cls += ' algo-card--archived';
        return `<div class="${cls}" data-id="${view.id}" data-name="${this.escapeHtml(view.name)}" data-symbol="${view.symbol || ''}" data-favorite="${isFavorite}" data-archived="${isArchived}">
            <div class="algo-card__content"><div class="algo-card__name">${isFavorite ? '<span class="algo-card__star">★</span> ' : ''}${this.escapeHtml(view.name)}</div><div class="algo-card__symbol">${symbol}</div></div>
            <div class="algo-card__time">${time}</div></div>`;
    },
    
    bindCardEvents(container) {
        container.querySelectorAll('.algo-card').forEach(card => {
            card.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); if (card.dataset.archived !== 'true') this.selectInstance(card.dataset.id, card.dataset.name, card.dataset.symbol); });
            card.addEventListener('dblclick', (e) => { e.preventDefault(); e.stopPropagation(); if (card.dataset.archived !== 'true') { this.selectInstance(card.dataset.id, card.dataset.name, card.dataset.symbol); this.toggleTrading(card.dataset.id); } });
            card.addEventListener('contextmenu', (e) => { e.preventDefault(); e.stopPropagation(); this.showContextMenu(card.dataset.id, card.dataset.favorite === 'true', card.dataset.archived === 'true', e.clientX, e.clientY); });
        });
    },
    
    showContextMenu(instanceId, isFavorite, isArchived, x, y) {
        this.hideContextMenu();
        let items = isArchived ? `
            <button class="algo-context-item" data-action="restore" data-id="${instanceId}"><span class="algo-context-icon">↺</span> Restore</button>
            <div class="algo-context-divider"></div>
            <button class="algo-context-item algo-context-item--danger" data-action="delete" data-id="${instanceId}"><span class="algo-context-icon">✕</span> Delete Permanently</button>
        ` : `
            <button class="algo-context-item" data-action="favorite" data-id="${instanceId}"><span class="algo-context-icon">${isFavorite ? '☆' : '★'}</span> ${isFavorite ? 'Remove from Favorites' : 'Add to Favorites'}</button>
            <button class="algo-context-item" data-action="archive" data-id="${instanceId}"><span class="algo-context-icon">📦</span> Archive</button>
            <div class="algo-context-divider"></div>
            <button class="algo-context-item algo-context-item--danger" data-action="delete" data-id="${instanceId}"><span class="algo-context-icon">✕</span> Delete</button>
        `;
        const menu = document.createElement('div');
        menu.id = 'algo-context-menu'; menu.className = 'algo-context-menu'; menu.innerHTML = items;
        menu.style.cssText = `position: fixed; left: ${x}px; top: ${y}px; z-index: 10000;`;
        document.body.appendChild(menu);
        menu.querySelectorAll('.algo-context-item').forEach(item => {
            item.addEventListener('click', (e) => { e.stopPropagation(); this.handleContextAction(item.dataset.action, item.dataset.id); this.hideContextMenu(); });
        });
    },
    
    hideContextMenu() { document.getElementById('algo-context-menu')?.remove(); },
    
    handleContextAction(action, instanceId) {
        const views = this.getSavedViews();
        const view = views.find(v => v.id === instanceId);
        if (!view) return;
        switch (action) {
            case 'favorite': view.favorite = !view.favorite; this.saveViews(views); this.renderDropdownContent(); break;
            case 'archive': view.archived = true; view.archivedAt = Date.now(); view.favorite = false; this.saveViews(views); this.renderDropdownContent(); if (this.currentInstanceId === instanceId) this.clearSelection(); break;
            case 'restore': view.archived = false; view.archivedAt = null; this.saveViews(views); this.renderDropdownContent(); break;
            case 'delete': if (confirm(`Delete "${view.name}"?\n\nThis cannot be undone.`)) { this.saveViews(views.filter(v => v.id !== instanceId)); this.renderDropdownContent(); if (this.currentInstanceId === instanceId) this.clearSelection(); } break;
        }
    },
    
    clearSelection() {
        this.currentInstanceId = null;
        this.dataCache = { positions: null, sentiments_15m: null, sentiments_1h: null, transitions: null, matrices: null };
        this.syncStatus = null;
        try { localStorage.removeItem(this.SELECTED_INSTANCE_KEY); } catch (e) {}
        document.getElementById('instance-label').textContent = 'Select Algorithm';
        const status = document.getElementById('instance-status');
        status.textContent = ''; status.className = 'instance-selector__status';
        this.renderEmptyContent();
    },
    
    async selectInstance(instanceId, name, symbol) {
        this.currentInstanceId = instanceId;
        this.dataCache = { positions: null, sentiments_15m: null, sentiments_1h: null, transitions: null, matrices: null };
        this.saveSelection(instanceId, name, symbol);
        document.getElementById('instance-label').textContent = name;
        const status = document.getElementById('instance-status');
        status.textContent = symbol ? this.formatSymbol(symbol) : '';
        status.className = 'instance-selector__status instance-selector__status--active';
        this.updateView(instanceId, { lastAccessed: Date.now() });
        this.closeDropdown();
        this.container.querySelectorAll('.algo-card').forEach(card => { card.classList.toggle('algo-card--selected', card.dataset.id === instanceId); });
        this.showLoading();
        await this.initializeInstanceTables(instanceId, name, symbol);
        await this.loadTabContent();
        await this.fetchSyncStatus();
    },
    
    async initializeInstanceTables(instanceId, name, symbol) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        try {
            const response = await fetch(`/api/instance/${instanceId}/initialize`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol || 'UNKNOWN', name: name || 'Algorithm' }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            const result = await response.json();
            
            // Seed 20: If backend reused an existing instance, redirect to it
            if (result.success && result.reused && result.instance_id && result.instance_id !== instanceId) {
                console.log(`[InstanceBrowser] Reusing existing instance ${result.instance_id} (was ${instanceId})`);
                this.currentInstanceId = result.instance_id;
                this.saveSelection(result.instance_id, name, symbol);
            }
            
            return result.success;
        } catch (e) { clearTimeout(timeoutId); return false; }
    },
    
    switchTab(tabId) {
        this.currentTab = tabId;
        this.container.querySelectorAll('.instance-tab').forEach(tab => { tab.classList.toggle('instance-tab--active', tab.dataset.tab === tabId); });
        this.render();
    },
    
    showLoading() {
        const content = document.getElementById('instance-content');
        if (content) content.innerHTML = '<div class="instance-loading"><div class="instance-loading__spinner"></div><div class="instance-loading__text">Loading data...</div></div>';
    },
    
    async loadTabContent() {
        const content = document.getElementById('instance-content');
        if (!content || !this.currentInstanceId) { this.renderEmptyContent(); return; }
        const cacheKey = this.currentTab === 'sentiments' ? `sentiments_${this.currentSentimentTimeframe}` : this.currentTab;
        if (this.dataCache[cacheKey]) { this.renderTabData(this.currentTab, this.dataCache[cacheKey]); return; }
        this.showLoading();
        const tab = this.tabs.find(t => t.id === this.currentTab);
        let endpoint = tab.endpoint.replace('{id}', this.currentInstanceId);
        if (this.currentTab === 'sentiments') endpoint += `/${this.currentSentimentTimeframe}`;
        try {
            const response = await fetch(endpoint + '?limit=50');
            const result = await response.json();
            if (result.success && result.data) { this.dataCache[cacheKey] = result.data; this.renderTabData(this.currentTab, result.data); }
            else this.renderNoData(this.currentTab);
        } catch (e) { this.renderNoData(this.currentTab); }
    },
    
    renderTabData(tabId, data) {
        const content = document.getElementById('instance-content');
        if (!content) return;
        if (!data || data.length === 0) { this.renderNoData(tabId); return; }
        switch (tabId) {
            case 'positions': content.innerHTML = this.renderPositionsTable(data); break;
            case 'sentiments':
                this._sentimentDataCache = data;
                content.innerHTML = this.renderSentimentsTable(data);
                this.bindScoreTapEvents();
                break;
            case 'transitions': content.innerHTML = this.renderTransitionsTable(data); break;
            case 'matrices': content.innerHTML = this.renderMatricesTable(data); break;
            default: this.renderNoData(tabId);
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // TABLE RENDERERS
    // ═══════════════════════════════════════════════════════════════════════
    
    renderPositionsTable(data) {
        return `<div class="instance-table-wrap">
            <div class="instance-table__header">
                <div id="sync-indicator" class="sync-indicator sync-indicator--offline"><span class="sync-indicator__dot"></span><span class="sync-indicator__label">OFFLINE</span></div>
                <button class="sync-toggle-btn" onclick="ApexInstanceBrowser.toggleSync()">${this.syncStatus?.running ? 'Stop Sync' : 'Start Sync'}</button>
            </div>
            <table class="instance-table"><thead><tr>
                <th>Time</th><th>Symbol</th><th>Dir</th><th>Status</th><th>Entry</th><th>Current</th><th>Lots</th><th>SL</th><th>TP</th><th>P/L</th><th>Sync</th>
            </tr></thead><tbody>
                ${data.map(row => {
                    const pnl = row.mt5_profit ?? row.unrealized_pnl ?? row.realized_pnl ?? 0;
                    const pnlClass = pnl >= 0 ? 'cell--bull' : 'cell--bear';
                    const syncClass = row.sync_status === 'SYNCED' ? 'sync-badge--live' : row.sync_status === 'CLOSED_MT5' ? 'sync-badge--closed' : 'sync-badge--pending';
                    return `<tr class="${row.direction === 'LONG' ? 'row--bull' : row.direction === 'SHORT' ? 'row--bear' : ''}">
                        <td>${this.formatTime(row.entry_time || row.created_at)}</td>
                        <td>${row.symbol || '--'}</td>
                        <td class="${row.direction === 'LONG' ? 'cell--bull' : 'cell--bear'}">${row.direction || '--'}</td>
                        <td><span class="status-badge status-badge--${(row.status || 'pending').toLowerCase()}">${row.status || '--'}</span></td>
                        <td>${row.entry_price?.toFixed(2) || '--'}</td>
                        <td>${row.current_price?.toFixed(2) || '--'}</td>
                        <td>${row.lots?.toFixed(2) || '--'}</td>
                        <td>${row.stop_loss?.toFixed(2) || '--'}</td>
                        <td>${row.take_profit?.toFixed(2) || '--'}</td>
                        <td class="${pnlClass}">${pnl != null ? '$' + pnl.toFixed(2) : '--'}</td>
                        <td><span class="sync-badge ${syncClass}">${row.sync_status || 'PENDING'}</span></td>
                    </tr>`;
                }).join('')}
            </tbody></table>
            <div class="instance-table__count">${data.length} positions</div>
        </div>`;
    },
    
    renderSentimentsTable(data) {
        return `<div class="instance-table-wrap">
            <table class="instance-table instance-table--scores"><thead><tr>
                <th class="score-header" data-col="time">Time</th>
                <th class="score-header" data-col="price_action">PA</th>
                <th class="score-header" data-col="key_levels">KL</th>
                <th class="score-header" data-col="momentum">MOM</th>
                <th class="score-header" data-col="ath">ATH</th>
                <th class="score-header" data-col="structure">STR</th>
                <th class="score-header" data-col="composite">COMP</th>
                <th class="score-header" data-col="bias">BIAS</th>
            </tr></thead><tbody>
                ${data.map((row, idx) => {
                    const cons = row.consensus_score ?? row.composite_score ?? 0;
                    return `<tr data-row-idx="${idx}">
                        <td class="score-tap" data-col="time" data-idx="${idx}">${this.formatTime(row.timestamp)}</td>
                        <td class="score-tap" data-col="price_action" data-idx="${idx}">${this.renderScoreCell(row.price_action_score)}</td>
                        <td class="score-tap" data-col="key_levels" data-idx="${idx}">${this.renderScoreCell(row.key_levels_score)}</td>
                        <td class="score-tap" data-col="momentum" data-idx="${idx}">${this.renderScoreCell(row.momentum_score)}</td>
                        <td class="score-tap" data-col="ath" data-idx="${idx}">${this.renderScoreCell(row.ath_score)}</td>
                        <td class="score-tap" data-col="structure" data-idx="${idx}">${this.renderScoreCell(row.structure_score)}</td>
                        <td class="score-tap" data-col="composite" data-idx="${idx}">${this.renderScoreCell(cons, true)}</td>
                        <td class="score-tap" data-col="bias" data-idx="${idx}">${this.renderBiasBadge(row.matrix_bias, row.matrix_bias_label)}</td>
                    </tr>`;
                }).join('')}
            </tbody></table>
            <div class="instance-table__count">${data.length} readings (${this.currentSentimentTimeframe.toUpperCase()})</div>
        </div>`;
    },
    
    renderScoreCell(score, isComposite = false) {
        if (score == null || isNaN(score)) return '<span class="score-cell score-cell--neutral">--</span>';
        const value = parseFloat(score);
        let cls = 'score-cell';
        if (value > 0.3) cls += ' score-cell--bullish';
        else if (value < -0.3) cls += ' score-cell--bearish';
        else cls += ' score-cell--neutral';
        if (isComposite) cls += ' score-cell--composite';
        return `<span class="${cls}">${value.toFixed(2)}</span>`;
    },
    
    renderBiasBadge(bias, label) {
        const biasVal = parseInt(bias) || 0;
        let cls = 'bias-badge';
        if (biasVal >= 1) cls += ' bias-badge--bullish';
        else if (biasVal <= -1) cls += ' bias-badge--bearish';
        else cls += ' bias-badge--neutral';
        if (Math.abs(biasVal) >= 2) cls += ' bias-badge--strong';
        return `<span class="${cls}">${label || this.getBiasLabel(biasVal)}</span>`;
    },
    
    getBiasLabel(bias) {
        const labels = { '-2': 'Strong Bear', '-1': 'Bearish', '0': 'Neutral', '1': 'Bullish', '2': 'Strong Bull' };
        return labels[String(bias)] || 'Neutral';
    },
    
    renderTransitionsTable(data) {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>From</th><th></th><th>To</th><th>Trigger</th><th>Score</th>
        </tr></thead><tbody>
            ${data.map(row => {
                const fromCls = row.from_state > 0 ? 'cell--bull' : row.from_state < 0 ? 'cell--bear' : '';
                const toCls = row.to_state > 0 ? 'cell--bull' : row.to_state < 0 ? 'cell--bear' : '';
                return `<tr><td>${this.formatTime(row.timestamp)}</td><td>${row.timeframe || '--'}</td><td class="${fromCls}">${row.from_state_label || row.from_state}</td><td class="cell--arrow">→</td><td class="${toCls}">${row.to_state_label || row.to_state}</td><td>${row.trigger_source || '--'}</td><td>${row.composite_score?.toFixed(2) || '--'}</td></tr>`;
            }).join('')}
        </tbody></table><div class="instance-table__count">${data.length} transitions</div></div>`;
    },
    
    renderMatricesTable(data) {
        const stateLabels = ['Strong Bear', 'Bearish', 'Neutral', 'Bullish', 'Strong Bull'];
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>State</th><th>Stability</th><th>Bias</th><th>Trans</th>
        </tr></thead><tbody>
            ${data.map(row => {
                const cls = row.trend_bias > 0.1 ? 'cell--bull' : row.trend_bias < -0.1 ? 'cell--bear' : '';
                return `<tr><td>${this.formatTime(row.updated_at)}</td><td>${row.timeframe || '--'}</td><td class="${cls}">${stateLabels[(row.current_state || 0) + 2] || 'Unknown'}</td><td>${row.stability_score?.toFixed(2) || '--'}</td><td class="${cls}">${row.trend_bias?.toFixed(2) || '--'}</td><td>${row.total_transitions || 0}</td></tr>`;
            }).join('')}
        </tbody></table><div class="instance-table__count">${data.length} matrices</div></div>`;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EMPTY TABLE RENDERERS
    // ═══════════════════════════════════════════════════════════════════════
    
    renderNoData(tabId) {
        const content = document.getElementById('instance-content');
        if (!content) return;
        switch (tabId) {
            case 'positions': content.innerHTML = this.renderPositionsTableEmpty(); break;
            case 'sentiments': content.innerHTML = this.renderSentimentsTableEmpty(); break;
            case 'transitions': content.innerHTML = this.renderTransitionsTableEmpty(); break;
            case 'matrices': content.innerHTML = this.renderMatricesTableEmpty(); break;
            default: content.innerHTML = '<div class="instance-empty"><div class="instance-empty__icon">◎</div><div class="instance-empty__text">No data yet</div></div>';
        }
    },
    
    renderPositionsTableEmpty() {
        return `<div class="instance-table-wrap">
            <div class="instance-table__header"><div id="sync-indicator" class="sync-indicator sync-indicator--offline"><span class="sync-indicator__dot"></span><span class="sync-indicator__label">OFFLINE</span></div><button class="sync-toggle-btn" onclick="ApexInstanceBrowser.toggleSync()">Start Sync</button></div>
            <table class="instance-table"><thead><tr><th>Time</th><th>Symbol</th><th>Dir</th><th>Status</th><th>Entry</th><th>Current</th><th>Lots</th><th>SL</th><th>TP</th><th>P/L</th><th>Sync</th></tr></thead><tbody>
                <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
            </tbody></table><div class="instance-table__hint">No positions yet • Data will appear when trading is active</div></div>`;
    },
    
    renderSentimentsTableEmpty() {
        return `<div class="instance-table-wrap">
            <table class="instance-table instance-table--scores"><thead><tr><th>Time</th><th>PA</th><th>KL</th><th>MOM</th><th>ATH</th><th>STR</th><th>COMP</th><th>BIAS</th></tr></thead><tbody>
                <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
            </tbody></table><div class="instance-table__hint">No sentiment readings yet (${this.currentSentimentTimeframe.toUpperCase()}) • Data will appear when trading is active</div></div>`;
    },
    
    renderTransitionsTableEmpty() {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr><th>Time</th><th>TF</th><th>From</th><th></th><th>To</th><th>Trigger</th><th>Score</th></tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td class="cell--arrow">→</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No state transitions yet • Data will appear when trading is active</div></div>`;
    },
    
    renderMatricesTableEmpty() {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr><th>Time</th><th>TF</th><th>State</th><th>Stability</th><th>Bias</th><th>Trans</th></tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No Markov matrices yet • Data will appear when trading is active</div></div>`;
    },
    
    renderEmptyContent() {
        const content = document.getElementById('instance-content');
        if (content) content.innerHTML = '<div class="instance-empty"><div class="instance-empty__icon">◎</div><div class="instance-empty__text">Select an algorithm</div></div>';
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // SEED 18: CELL-TAP DRILL-DOWN POPOVER
    // ═══════════════════════════════════════════════════════════════════════
    
    _sentimentDataCache: [],
    
    bindScoreTapEvents() {
        const content = document.getElementById('instance-content');
        if (!content) return;
        content.addEventListener('click', (e) => {
            const cell = e.target.closest('.score-tap');
            const header = e.target.closest('.score-header');
            if (cell) { e.stopPropagation(); const idx = parseInt(cell.dataset.idx); const col = cell.dataset.col; const row = this._sentimentDataCache[idx]; if (row) this.showCellPopover(cell, col, row); }
            else if (header) { e.stopPropagation(); this.showHeaderPopover(header, header.dataset.col); }
        });
        document.addEventListener('click', () => this.hideCellPopover());
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') this.hideCellPopover(); });
    },
    
    showCellPopover(anchorEl, column, row) {
        this.hideCellPopover();
        const popover = document.createElement('div');
        popover.id = 'score-popover'; popover.className = 'score-popover';
        popover.innerHTML = this.buildPopoverContent(column, row);
        document.body.appendChild(popover);
        const rect = anchorEl.getBoundingClientRect();
        const popRect = popover.getBoundingClientRect();
        let left = rect.left + rect.width / 2 - popRect.width / 2;
        let top = rect.bottom + 6;
        if (left < 8) left = 8;
        if (left + popRect.width > window.innerWidth - 8) left = window.innerWidth - popRect.width - 8;
        if (top + popRect.height > window.innerHeight - 8) top = rect.top - popRect.height - 6;
        popover.style.left = `${left}px`; popover.style.top = `${top}px`;
        requestAnimationFrame(() => popover.classList.add('score-popover--visible'));
    },
    
    showHeaderPopover(anchorEl, column) {
        this.hideCellPopover();
        const popover = document.createElement('div');
        popover.id = 'score-popover'; popover.className = 'score-popover';
        popover.innerHTML = this.buildHeaderPopoverContent(column);
        document.body.appendChild(popover);
        const rect = anchorEl.getBoundingClientRect();
        let left = rect.left + rect.width / 2 - popover.getBoundingClientRect().width / 2;
        let top = rect.bottom + 6;
        if (left < 8) left = 8;
        popover.style.left = `${left}px`; popover.style.top = `${top}px`;
        requestAnimationFrame(() => popover.classList.add('score-popover--visible'));
    },
    
    hideCellPopover() {
        const existing = document.getElementById('score-popover');
        if (existing) { existing.classList.remove('score-popover--visible'); setTimeout(() => existing.remove(), 150); }
    },
    
    buildPopoverContent(column, row) {
        let ws = {}; try { ws = JSON.parse(row.weights_snapshot || '{}'); } catch(e) {}
        const sw = ws.sentiment_weights || {};
        const tw = ws.timeframe_weights || {};
        const th = ws.thresholds || {};
        const scoreMap = {
            price_action: { label: 'Price Action', score: row.price_action_score, weight: sw.price_action },
            key_levels:   { label: 'Key Levels',   score: row.key_levels_score,   weight: sw.key_levels },
            momentum:     { label: 'Momentum',     score: row.momentum_score,     weight: sw.momentum },
            ath:          { label: 'All Time High', score: row.ath_score,          weight: sw.ath },
            structure:    { label: 'Structure',     score: row.structure_score,    weight: sw.structure }
        };
        if (column === 'time') {
            return `<div class="pop-title">Meta</div>
                <div class="pop-row"><span class="pop-label">Model</span><span class="pop-value">${row.source_model || '—'}</span></div>
                <div class="pop-row"><span class="pop-label">Source</span><span class="pop-value">${row.source_type || '—'}</span></div>
                <div class="pop-row"><span class="pop-label">Latency</span><span class="pop-value">${row.processing_time_ms ? row.processing_time_ms + 'ms' : '—'}</span></div>
                <div class="pop-row"><span class="pop-label">Profile</span><span class="pop-value">${ws.profile_name || ws.profile_id || '—'}</span></div>
                <div class="pop-row"><span class="pop-label">Timeframe</span><span class="pop-value">${row.timeframe || '—'}</span></div>`;
        }
        if (column === 'composite') {
            let rows = Object.entries(scoreMap).map(([key, info]) => {
                const s = parseFloat(info.score || 0), w = parseFloat(info.weight || 0), contrib = s * w;
                const cls = contrib >= 0 ? 'pop-bull' : 'pop-bear';
                return `<div class="pop-row"><span class="pop-label">${info.label}</span><span class="pop-value">${s.toFixed(2)} × ${(w*100).toFixed(0)}% = <span class="${cls}">${contrib >= 0 ? '+' : ''}${contrib.toFixed(3)}</span></span></div>`;
            }).join('');
            return `<div class="pop-title">Composite Breakdown</div>${rows}<div class="pop-divider"></div><div class="pop-row pop-row--total"><span class="pop-label">Composite</span><span class="pop-value pop-value--lg">${(row.composite_score || 0).toFixed(3)}</span></div>`;
        }
        if (column === 'bias') {
            const ownTf = row.timeframe || '15m', partnerTf = ownTf === '15m' ? '1h' : '15m';
            const ownW = tw[ownTf] || 0.40, partnerW = tw[partnerTf] || 0.60;
            const comp = row.composite_score || 0, partner = row.partner_composite, cons = row.consensus_score || comp;
            const signal = row.signal_direction || 'HOLD', met = row.meets_threshold ? '✓ MET' : '· NOT MET';
            return `<div class="pop-title">Consensus & Signal</div>
                <div class="pop-row"><span class="pop-label">${ownTf} composite</span><span class="pop-value">${comp.toFixed(3)} × ${(ownW*100).toFixed(0)}%</span></div>
                <div class="pop-row"><span class="pop-label">${partnerTf} composite</span><span class="pop-value">${partner != null ? partner.toFixed(3) : '—'} × ${(partnerW*100).toFixed(0)}%</span></div>
                <div class="pop-divider"></div>
                <div class="pop-row pop-row--total"><span class="pop-label">Consensus</span><span class="pop-value pop-value--lg">${cons.toFixed(3)}</span></div>
                <div class="pop-divider"></div>
                <div class="pop-row"><span class="pop-label">Buy threshold</span><span class="pop-value">${(th.buy || 0.55).toFixed(2)}</span></div>
                <div class="pop-row"><span class="pop-label">Sell threshold</span><span class="pop-value">${(th.sell || -0.55).toFixed(2)}</span></div>
                <div class="pop-row"><span class="pop-label">Signal</span><span class="pop-value pop-value--signal">${signal} ${met}</span></div>`;
        }
        const info = scoreMap[column];
        if (!info) return '<div class="pop-title">—</div>';
        const s = parseFloat(info.score || 0), w = parseFloat(info.weight || 0), contrib = s * w;
        return `<div class="pop-title">${info.label}</div>
            <div class="pop-row"><span class="pop-label">Raw Score</span><span class="pop-value">${s.toFixed(3)}</span></div>
            <div class="pop-row"><span class="pop-label">Weight</span><span class="pop-value">${(w * 100).toFixed(0)}%</span></div>
            <div class="pop-divider"></div>
            <div class="pop-row pop-row--total"><span class="pop-label">Contribution</span><span class="pop-value ${contrib >= 0 ? 'pop-bull' : 'pop-bear'}">${contrib >= 0 ? '+' : ''}${contrib.toFixed(4)}</span></div>`;
    },
    
    buildHeaderPopoverContent(column) {
        const labels = { time: 'Timestamp', price_action: 'Price Action', key_levels: 'Key Levels', momentum: 'Momentum', ath: 'All Time High', structure: 'Structure', composite: 'Composite (Weighted)', bias: 'Consensus Bias' };
        const descriptions = {
            price_action: 'What is price doing right now? Candle patterns, direction, impulse vs correction.',
            key_levels: 'Where is price relative to support/resistance, EMAs, Bollinger bands?',
            momentum: 'Is the move accelerating or fading? RSI, MACD, candle size progression.',
            ath: 'Percentile rank of current price vs All Time High. Deterministic — no API cost.',
            structure: 'What regime or pattern is forming? Trend, range, breakout, distribution.',
            composite: "Weighted sum of all 5 scores using the active profile's sentiment weights.",
            bias: 'Cross-timeframe consensus blending 15m + 1h composites using timeframe weights.'
        };
        let weightInfo = '';
        if (['price_action','key_levels','momentum','ath','structure'].includes(column) && this._sentimentDataCache.length > 0) {
            try { const ws = JSON.parse(this._sentimentDataCache[0].weights_snapshot || '{}'); const w = (ws.sentiment_weights || {})[column]; if (w != null) weightInfo = `<div class="pop-row"><span class="pop-label">Current Weight</span><span class="pop-value">${(w * 100).toFixed(0)}%</span></div>`; } catch(e) {}
        }
        return `<div class="pop-title">${labels[column] || column}</div>${descriptions[column] ? `<div class="pop-desc">${descriptions[column]}</div>` : ''}${weightInfo}`;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════
    
    // ═══════════════════════════════════════════════════════════════════════
    // TRADER ACTIVATION (Seed 18/19: Wire to TorraTraderBridge)
    // ═══════════════════════════════════════════════════════════════════════
    
    toggleTrading(instanceId) {
        // Seed 20: Always use the resolved instance ID (may have been redirected by reuse)
        const resolvedId = this.currentInstanceId || instanceId;
        const saved = this.getSavedSelection();
        const symbol = saved?.symbol || '';
        
        // Dispatch event for TorraTraderBridge
        window.dispatchEvent(new CustomEvent('torra:activate', {
            detail: { instanceId: resolvedId, symbol }
        }));
        
        // Also start sentiment panel polling (reads from DB)
        if (typeof ApexSentiment !== 'undefined') {
            if (typeof TorraTraderBridge !== 'undefined' && TorraTraderBridge.isRunning(instanceId)) {
                ApexSentiment.stopEngine();
            } else {
                ApexSentiment.startEngine(symbol, instanceId);
            }
        }
    },
    
    formatSymbol(symbol) { if (!symbol) return '???'; return symbol.replace(/(\.sim)+$/gi, '') + '.SIM'; },
    formatTimestamp(ts) {
        if (!ts) return '';
        const d = new Date(ts), now = new Date(), diff = now - d;
        const mins = Math.floor(diff / 60000), hrs = Math.floor(diff / 3600000), days = Math.floor(diff / 86400000);
        if (mins < 1) return 'Now'; if (mins < 60) return `${mins}m ago`; if (hrs < 24) return `${hrs}h ago`;
        if (days === 1) return 'Yesterday'; if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },
    formatTime(ts) { if (!ts) return '--'; return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }); },
    escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
};

window.ApexInstanceBrowser = ApexInstanceBrowser;
