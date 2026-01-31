/* ═══════════════════════════════════════════════════════════════════════════
   APEX INSTANCE BROWSER V2.4 - Full Schema Tables
   
   Bottom-left panel in Database view showing saved algorithms.
   - Shows ALL algorithms (mirrors APEX dropdown)
   - Favorites (★) at top, Saved in middle, Archived at bottom
   - Right-click context menu for favorite/archive/delete
   - PHASE 2: Loads data from 4 linked database tables with FULL SCHEMA
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexInstanceBrowser = {
    container: null,
    currentSymbol: null,
    currentSymbolId: null,
    currentInstanceId: null,
    currentTab: 'positions',
    isDropdownOpen: false,
    isLoading: false,
    
    dataCache: { positions: null, sentiments: null, transitions: null, matrices: null },
    
    TRADING_VIEWS_KEY: 'apex_trading_views',
    SELECTED_INSTANCE_KEY: 'apex_selected_instance',
    
    tabs: [
        { id: 'positions', label: 'Positions', icon: '◆', endpoint: '/api/instance/{id}/positions' },
        { id: 'sentiments', label: 'Sentiments', icon: '◈', endpoint: '/api/instance/{id}/sentiments' },
        { id: 'transitions', label: 'Transitions', icon: '⇄', endpoint: '/api/instance/{id}/transitions' },
        { id: 'matrices', label: 'Matrices', icon: '▦', endpoint: '/api/instance/{id}/matrices' }
    ],
    
    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════
    
    init(container, symbolId) {
        this.container = container;
        this.currentSymbolId = symbolId;
        this.currentSymbol = symbolId ? symbolId.toUpperCase() : null;
        this.restoreSelection();
        this.render();
        this.bindGlobalEvents();
        console.log('[InstanceBrowser] Initialized for symbol:', this.currentSymbol);
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
    
    render() {
        const savedSelection = this.getSavedSelection();
        const headerLabel = savedSelection?.name || 'Select Algorithm';
        const headerStatus = savedSelection?.symbol ? this.formatSymbol(savedSelection.symbol) : '';
        const statusClass = savedSelection ? 'instance-selector__status instance-selector__status--active' : 'instance-selector__status';
        
        this.container.innerHTML = `
            <div class="instance-browser">
                <div class="instance-browser__header">
                    <button class="instance-hamburger" id="instance-hamburger">
                        <span class="hamburger-line"></span>
                        <span class="hamburger-line"></span>
                        <span class="hamburger-line"></span>
                    </button>
                    <div class="instance-selector" id="instance-selector">
                        <span class="instance-selector__label" id="instance-label">${headerLabel}</span>
                        <span class="${statusClass}" id="instance-status">${headerStatus}</span>
                    </div>
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
                <div class="instance-content" id="instance-content">
                    <div class="instance-empty">
                        <div class="instance-empty__icon">◎</div>
                        <div class="instance-empty__text">Select an algorithm</div>
                    </div>
                </div>
            </div>
        `;
        this.bindEvents();
        this.renderDropdownContent();
        if (this.currentInstanceId) this.loadTabContent();
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
    
    // ═══════════════════════════════════════════════════════════════════════
    // DATA MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════
    
    getSavedViews() {
        try { return JSON.parse(localStorage.getItem(this.TRADING_VIEWS_KEY) || '[]'); }
        catch (e) { return []; }
    },
    
    saveViews(views) {
        try { localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views)); }
        catch (e) { console.warn('[InstanceBrowser] Save failed:', e); }
    },
    
    updateView(viewId, updates) {
        const views = this.getSavedViews();
        const idx = views.findIndex(v => v.id === viewId);
        if (idx >= 0) { views[idx] = { ...views[idx], ...updates }; this.saveViews(views); }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // DROPDOWN CONTENT
    // ═══════════════════════════════════════════════════════════════════════
    
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
        if (favorites.length > 0) {
            html += '<div class="algo-section-header algo-section-header--favorites">★ FAVORITES</div>';
            favorites.forEach(v => { html += this.renderCard(v, true, false); });
        }
        html += '<div class="algo-section-header">SAVED ALGORITHMS</div>';
        if (active.length === 0 && favorites.length === 0) {
            html += '<div class="algo-empty"><div class="algo-empty__text">No saved algorithms</div><div class="algo-empty__hint">Create one from the APEX menu</div></div>';
        } else {
            active.forEach(v => { html += this.renderCard(v, false, false); });
            if (active.length === 0) html += '<div class="algo-empty"><div class="algo-empty__hint">All in Favorites above</div></div>';
        }
        if (archived.length > 0) {
            html += '<div class="algo-divider"></div><div class="algo-section-header algo-section-header--archived">ARCHIVED</div>';
            archived.forEach(v => { html += this.renderCard(v, false, true); });
        }
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
            <div class="algo-card__content">
                <div class="algo-card__name">${isFavorite ? '<span class="algo-card__star">★</span> ' : ''}${this.escapeHtml(view.name)}</div>
                <div class="algo-card__symbol">${symbol}</div>
            </div>
            <div class="algo-card__time">${time}</div>
        </div>`;
    },
    
    bindCardEvents(container) {
        container.querySelectorAll('.algo-card').forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault(); e.stopPropagation();
                if (card.dataset.archived !== 'true') this.selectInstance(card.dataset.id, card.dataset.name, card.dataset.symbol);
            });
            card.addEventListener('contextmenu', (e) => {
                e.preventDefault(); e.stopPropagation();
                this.showContextMenu(card.dataset.id, card.dataset.favorite === 'true', card.dataset.archived === 'true', e.clientX, e.clientY);
            });
        });
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // CONTEXT MENU
    // ═══════════════════════════════════════════════════════════════════════
    
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
        this.dataCache = { positions: null, sentiments: null, transitions: null, matrices: null };
        try { localStorage.removeItem(this.SELECTED_INSTANCE_KEY); } catch (e) {}
        document.getElementById('instance-label').textContent = 'Select Algorithm';
        const status = document.getElementById('instance-status');
        status.textContent = ''; status.className = 'instance-selector__status';
        this.renderEmptyContent();
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // INSTANCE SELECTION
    // ═══════════════════════════════════════════════════════════════════════
    
    async selectInstance(instanceId, name, symbol) {
        console.log('[InstanceBrowser] selectInstance:', { instanceId, name, symbol });
        this.currentInstanceId = instanceId;
        this.dataCache = { positions: null, sentiments: null, transitions: null, matrices: null };
        this.saveSelection(instanceId, name, symbol);
        document.getElementById('instance-label').textContent = name;
        const status = document.getElementById('instance-status');
        status.textContent = symbol ? this.formatSymbol(symbol) : '';
        status.className = 'instance-selector__status instance-selector__status--active';
        this.updateView(instanceId, { lastAccessed: Date.now() });
        this.closeDropdown();
        this.container.querySelectorAll('.algo-card').forEach(card => {
            card.classList.toggle('algo-card--selected', card.dataset.id === instanceId);
        });
        this.showLoading();
        await this.initializeInstanceTables(instanceId, name, symbol);
        await this.loadTabContent();
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
            if (result.success) { console.log('[InstanceBrowser] Tables ready'); return true; }
            return false;
        } catch (e) { clearTimeout(timeoutId); return false; }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // TAB CONTENT
    // ═══════════════════════════════════════════════════════════════════════
    
    switchTab(tabId) {
        this.currentTab = tabId;
        this.container.querySelectorAll('.instance-tab').forEach(tab => {
            tab.classList.toggle('instance-tab--active', tab.dataset.tab === tabId);
        });
        this.loadTabContent();
    },
    
    showLoading() {
        const content = document.getElementById('instance-content');
        if (content) content.innerHTML = '<div class="instance-loading"><div class="instance-loading__spinner"></div><div class="instance-loading__text">Loading data...</div></div>';
    },
    
    async loadTabContent() {
        const content = document.getElementById('instance-content');
        if (!content || !this.currentInstanceId) { this.renderEmptyContent(); return; }
        if (this.dataCache[this.currentTab]) { this.renderTabData(this.currentTab, this.dataCache[this.currentTab]); return; }
        this.showLoading();
        const tab = this.tabs.find(t => t.id === this.currentTab);
        const endpoint = tab.endpoint.replace('{id}', this.currentInstanceId);
        try {
            const response = await fetch(endpoint + '?limit=50&timeframe=15m');
            const result = await response.json();
            if (result.success && result.data) { this.dataCache[this.currentTab] = result.data; this.renderTabData(this.currentTab, result.data); }
            else this.renderNoData(this.currentTab);
        } catch (e) { this.renderNoData(this.currentTab); }
    },
    
    renderTabData(tabId, data) {
        const content = document.getElementById('instance-content');
        if (!content) return;
        if (!data || data.length === 0) { this.renderNoData(tabId); return; }
        switch (tabId) {
            case 'positions': content.innerHTML = this.renderPositionsTable(data); break;
            case 'sentiments': content.innerHTML = this.renderSentimentsTable(data); break;
            case 'transitions': content.innerHTML = this.renderTransitionsTable(data); break;
            case 'matrices': content.innerHTML = this.renderMatricesTable(data); break;
            default: this.renderNoData(tabId);
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // TABLE RENDERERS - FULL SCHEMA
    // ═══════════════════════════════════════════════════════════════════════
    
    renderPositionsTable(data) {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>Symbol</th><th>Dir</th><th>Status</th><th>Entry</th><th>Exit</th><th>Lots</th><th>SL</th><th>TP</th><th>P/L</th><th>Signal</th>
        </tr></thead><tbody>
            ${data.map(row => `<tr class="${row.direction === 'LONG' ? 'row--bull' : row.direction === 'SHORT' ? 'row--bear' : ''}">
                <td>${this.formatTime(row.entry_time || row.created_at)}</td>
                <td>${row.symbol || '--'}</td>
                <td class="${row.direction === 'LONG' ? 'cell--bull' : 'cell--bear'}">${row.direction || '--'}</td>
                <td><span class="status-badge status-badge--${(row.status || 'pending').toLowerCase()}">${row.status || '--'}</span></td>
                <td>${row.entry_price?.toFixed(2) || '--'}</td>
                <td>${row.exit_price?.toFixed(2) || '--'}</td>
                <td>${row.lots?.toFixed(2) || '--'}</td>
                <td>${row.stop_loss?.toFixed(2) || '--'}</td>
                <td>${row.take_profit?.toFixed(2) || '--'}</td>
                <td class="${(row.realized_pnl || 0) >= 0 ? 'cell--bull' : 'cell--bear'}">${row.realized_pnl != null ? '$' + row.realized_pnl.toFixed(2) : '--'}</td>
                <td>${row.signal_source || '--'}</td>
            </tr>`).join('')}
        </tbody></table><div class="instance-table__count">${data.length} positions</div></div>`;
    },
    
    renderSentimentsTable(data) {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>Bias</th><th>Composite</th><th>Trend</th><th>Momentum</th><th>Volatility</th><th>Volume</th><th>Signal</th><th>Conf</th>
        </tr></thead><tbody>
            ${data.map(row => {
                const score = row.composite_score || 0;
                const cls = score > 0.2 ? 'cell--bull' : score < -0.2 ? 'cell--bear' : '';
                // Use matrix_bias_label from DB, fallback to calculated
                const biasLabel = row.matrix_bias_label || this.getBiasLabel(row.matrix_bias);
                return `<tr>
                    <td>${this.formatTime(row.timestamp)}</td>
                    <td>${row.timeframe || '--'}</td>
                    <td class="${cls}">${biasLabel}</td>
                    <td class="${cls}">${score.toFixed(3)}</td>
                    <td>${row.trend_score?.toFixed(2) || row.price_action_score?.toFixed(2) || '--'}</td>
                    <td>${row.momentum_score?.toFixed(2) || '--'}</td>
                    <td>${row.volatility_score?.toFixed(2) || row.volume_score?.toFixed(2) || '--'}</td>
                    <td>${row.volume_score?.toFixed(2) || row.structure_score?.toFixed(2) || '--'}</td>
                    <td class="${row.signal === 'BUY' ? 'cell--bull' : row.signal === 'SELL' ? 'cell--bear' : ''}">${row.signal || '--'}</td>
                    <td>${row.confidence?.toFixed(2) || (row.processing_time_ms ? row.processing_time_ms + 'ms' : '--')}</td>
                </tr>`;
            }).join('')}
        </tbody></table><div class="instance-table__count">${data.length} readings</div></div>`;
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
                return `<tr>
                    <td>${this.formatTime(row.timestamp)}</td>
                    <td>${row.timeframe || '--'}</td>
                    <td class="${fromCls}">${row.from_state_label || row.from_state}</td>
                    <td class="cell--arrow">→</td>
                    <td class="${toCls}">${row.to_state_label || row.to_state}</td>
                    <td>${row.trigger_source || '--'}</td>
                    <td>${row.composite_score?.toFixed(2) || '--'}</td>
                </tr>`;
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
                const stateLabel = stateLabels[(row.current_state || 0) + 2] || 'Unknown';
                return `<tr>
                    <td>${this.formatTime(row.timestamp)}</td>
                    <td>${row.timeframe || '--'}</td>
                    <td class="${cls}">${stateLabel}</td>
                    <td>${row.stability_score?.toFixed(2) || '--'}</td>
                    <td class="${cls}">${row.trend_bias?.toFixed(2) || '--'}</td>
                    <td>${row.total_transitions || 0}</td>
                </tr>`;
            }).join('')}
        </tbody></table><div class="instance-table__count">${data.length} matrices</div></div>`;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // EMPTY TABLE RENDERERS - FULL SCHEMA
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
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>Symbol</th><th>Dir</th><th>Status</th><th>Entry</th><th>Exit</th><th>Lots</th><th>SL</th><th>TP</th><th>P/L</th><th>Signal</th>
        </tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No positions yet • Data will appear when trading is active</div></div>`;
    },
    
    renderSentimentsTableEmpty() {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>Bias</th><th>Composite</th><th>Trend</th><th>Momentum</th><th>Volatility</th><th>Volume</th><th>Signal</th><th>Conf</th>
        </tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No sentiment readings yet • Data will appear when trading is active</div></div>`;
    },
    
    renderTransitionsTableEmpty() {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>From</th><th></th><th>To</th><th>Trigger</th><th>Score</th>
        </tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td class="cell--arrow">→</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No state transitions yet • Data will appear when trading is active</div></div>`;
    },
    
    renderMatricesTableEmpty() {
        return `<div class="instance-table-wrap"><table class="instance-table"><thead><tr>
            <th>Time</th><th>TF</th><th>State</th><th>Stability</th><th>Bias</th><th>Trans</th>
        </tr></thead><tbody>
            <tr class="instance-table__row--placeholder"><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>
        </tbody></table><div class="instance-table__hint">No Markov matrices yet • Data will appear when trading is active</div></div>`;
    },
    
    renderEmptyContent() {
        const content = document.getElementById('instance-content');
        if (content) content.innerHTML = '<div class="instance-empty"><div class="instance-empty__icon">◎</div><div class="instance-empty__text">Select an algorithm</div></div>';
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════
    
    formatSymbol(symbol) {
        if (!symbol) return '???';
        return symbol.replace(/(\.sim)+$/gi, '') + '.sim';
    },
    
    formatTimestamp(ts) {
        if (!ts) return '';
        const d = new Date(ts), now = new Date(), diff = now - d;
        const mins = Math.floor(diff / 60000), hrs = Math.floor(diff / 3600000), days = Math.floor(diff / 86400000);
        if (mins < 1) return 'Now';
        if (mins < 60) return `${mins}m ago`;
        if (hrs < 24) return `${hrs}h ago`;
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },
    
    formatTime(ts) {
        if (!ts) return '--';
        return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    },
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.ApexInstanceBrowser = ApexInstanceBrowser;
