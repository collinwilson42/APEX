/* ═══════════════════════════════════════════════════════════════════════════
   APEX TAB RENDERER V2.9 - Instance Management Update
   
   BC-044: INSTANCE_TYPE_TITLE_UPDATE
   BC-046: API_ERROR_GRACEFUL_FALLBACK
   BC-047: DATABASE_NOT_FOUND_MESSAGING
   BC-048: SYMBOL_UNAVAILABLE_VISUAL
   BC-049: CONSOLE_ERROR_REDUCTION
   BC-050: NETWORK_TIMEOUT_HANDLING
   BC-051: FAVORITES_ARCHIVED_SECTIONS
   BC-052: ALGORITHM_CONTEXT_MENU
   
   NEW:
   - Favorites section (★) at top of Algorithms
   - Archived section at bottom
   - Right-click context menu: Favorite, Archive, Delete
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexTabRenderer = {
    container: null,
    tabsContainer: null,
    logoButton: null,
    dropdown: null,
    currentType: 'database',
    isExpanded: false,
    symbolsCache: null,
    symbolsLoading: false,
    symbolsError: null,
    
    TRADING_VIEWS_KEY: 'apex_trading_views',
    DB_ACCESS_KEY: 'apex_db_access',
    
    FETCH_TIMEOUT: 10000,
    MAX_RETRIES: 2,

    dragState: {
        isDragging: false,
        draggedTabId: null,
        startIndex: 0
    },

    init() {
        this.container = document.getElementById('apex-tab-bar');
        if (!this.container) return;

        this.buildStructure();
        this.setupKeyboardShortcuts();
        this.setupGlobalClickHandler();
        this.preloadSymbols();

        ApexState.subscribe(state => this.render(state));
        this.render(ApexState.getState());
    },

    async fetchWithTimeout(url, options = {}, retries = 0) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.FETCH_TIMEOUT);
        
        try {
            const response = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                if (retries < this.MAX_RETRIES) {
                    console.warn(`[APEX] Request timeout, retrying (${retries + 1}/${this.MAX_RETRIES})...`);
                    return this.fetchWithTimeout(url, options, retries + 1);
                }
                throw new Error('Request timed out after multiple retries');
            }
            throw error;
        }
    },

    async preloadSymbols() {
        if (this.symbolsLoading) return;
        this.symbolsLoading = true;
        this.symbolsError = null;
        
        try {
            const response = await this.fetchWithTimeout('/api/symbols');
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            const result = await response.json();
            if (result.success) {
                this.symbolsCache = result.symbols || [];
                this.symbolsError = null;
            } else {
                throw new Error(result.error || 'Failed to load symbols');
            }
        } catch (e) {
            console.warn('[APEX] Symbol preload warning:', e.message);
            this.symbolsCache = [];
            this.symbolsError = e.message;
        } finally {
            this.symbolsLoading = false;
        }
    },

    buildStructure() {
        this.container.innerHTML = `
            <div class="tab-bar">
                <button class="tab-bar__logo" aria-label="New instance (Ctrl+T)" title="Create New Instance">
                    <img src="/static/img/apex_logo.png" alt="APEX" class="tab-bar__logo-img">
                </button>
                <div class="tab-bar__separator"></div>
                <div class="tab-bar__tabs"></div>
            </div>
        `;

        this.tabsContainer = this.container.querySelector('.tab-bar__tabs');
        this.logoButton = this.container.querySelector('.tab-bar__logo');
        this.createDropdown();

        this.logoButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
    },

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'new-tab-dropdown';
        this.dropdown.innerHTML = `
            <div class="new-tab-dropdown__types">
                <button class="dropdown-type dropdown-type--database dropdown-type--active" data-type="database">
                    <span class="dropdown-type__dot"></span>
                    Databases
                </button>
                <button class="dropdown-type dropdown-type--trading dropdown-type--algorithms" data-type="trading">
                    <span class="dropdown-type__dot"></span>
                    Algorithms
                </button>
                <button class="dropdown-type dropdown-type--metatron" data-type="metatron">
                    <span class="dropdown-type__dot"></span>
                    Metatron
                </button>
            </div>
            <div class="new-tab-dropdown__instances"></div>
            <div class="new-tab-dropdown__create" style="display:none;">
                <div class="create-panel">
                    <div class="create-panel__header">
                        <input type="text" class="create-panel__input" placeholder="Instance name..." id="create-instance-name">
                    </div>
                    <div class="create-panel__symbols"></div>
                </div>
            </div>
        `;
        document.body.appendChild(this.dropdown);

        this.dropdown.querySelectorAll('.dropdown-type').forEach(btn => {
            btn.addEventListener('click', () => this.switchType(btn.dataset.type));
        });
    },

    toggleDropdown() {
        const { ui } = ApexState.getState();
        if (ui.newTabDropdownVisible) {
            this.hideDropdown();
        } else {
            this.showDropdown();
        }
    },

    async showDropdown() {
        const btnRect = this.logoButton.getBoundingClientRect();
        this.dropdown.style.top = (btnRect.bottom + 4) + 'px';
        this.dropdown.style.left = btnRect.left + 'px';
        
        this.isExpanded = false;
        this.dropdown.classList.remove('new-tab-dropdown--expanded');
        this.dropdown.querySelector('.new-tab-dropdown__create').style.display = 'none';
        
        this.dropdown.classList.add('new-tab-dropdown--visible');
        ApexState.setState({ ui: { newTabDropdownVisible: true } });

        if (!this.symbolsCache || this.symbolsCache.length === 0 || this.symbolsError) {
            await this.preloadSymbols();
        }

        await this.renderInstances(this.currentType);
    },

    hideDropdown() {
        this.dropdown.classList.remove('new-tab-dropdown--visible', 'new-tab-dropdown--expanded');
        this.isExpanded = false;
        ApexState.setState({ ui: { newTabDropdownVisible: false } });
    },

    switchType(type) {
        this.currentType = type;
        this.isExpanded = false;
        this.dropdown.classList.remove('new-tab-dropdown--expanded');
        this.dropdown.querySelector('.new-tab-dropdown__create').style.display = 'none';
        
        this.dropdown.querySelectorAll('.dropdown-type').forEach(btn => {
            btn.classList.toggle('dropdown-type--active', btn.dataset.type === type);
        });
        this.renderInstances(type);
    },

    async renderInstances(type) {
        const instancesContainer = this.dropdown.querySelector('.new-tab-dropdown__instances');
        
        if (type === 'database') {
            this.renderDatabaseInstances(instancesContainer);
        } else if (type === 'trading') {
            this.renderTradingInstances(instancesContainer);
        } else if (type === 'metatron') {
            this.renderMetatronInstances(instancesContainer);
        }
    },

    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        
        if (diffMins < 1) return 'Current';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },

    renderDatabaseInstances(container) {
        const symbols = this.symbolsCache || [];
        const dbAccess = JSON.parse(localStorage.getItem(this.DB_ACCESS_KEY) || '{}');
        
        let html = '';
        
        if (this.symbolsLoading) {
            html = '<div class="dropdown-loading">Loading databases...</div>';
            container.innerHTML = html;
            return;
        }
        
        if (this.symbolsError) {
            html = `
                <div class="dropdown-error">
                    <div style="margin-bottom: 8px;">⚠️ ${this.escapeHtml(this.symbolsError)}</div>
                    <div style="font-size: 10px; color: var(--color-text-secondary);">
                        Check if the server is running at localhost:5000
                    </div>
                </div>
            `;
            container.innerHTML = html;
            return;
        }
        
        if (symbols.length === 0) {
            html = `
                <div class="dropdown-empty">
                    <div class="dropdown-empty__title">No databases found</div>
                    <div class="dropdown-empty__subtitle">Run init_databases.py to create symbol databases</div>
                </div>
            `;
            container.innerHTML = html;
            return;
        }

        const sorted = [...symbols].sort((a, b) => (dbAccess[a.id] || 0) - (dbAccess[b.id] || 0)).reverse();
        
        sorted.forEach(db => {
            const bars = (db.records_1m || 0) + (db.records_15m || 0);
            const time = dbAccess[db.id] ? this.formatTimestamp(dbAccess[db.id]) : '';
            const disabled = !db.available;
            
            html += `
                <button class="dropdown-instance ${disabled ? 'dropdown-instance--disabled' : ''}" 
                        data-action="open" data-type="database" data-id="${db.id}" 
                        data-name="${db.name}" data-symbol="${db.symbol}" ${disabled ? 'disabled' : ''}>
                    <div class="dropdown-instance__info">
                        <span class="dropdown-instance__name">${db.name}</span>
                        <span class="dropdown-instance__meta">
                            <span class="dropdown-instance__symbol">${db.symbol}</span>
                            ${db.available 
                                ? `<span>${bars.toLocaleString()} bars</span>` 
                                : '<span class="dropdown-instance__unavailable">Not Initialized</span>'}
                        </span>
                    </div>
                    ${time ? `<span class="dropdown-instance__time">${time}</span>` : ''}
                </button>
            `;
        });

        const analyticsTime = dbAccess['analytics'] ? this.formatTimestamp(dbAccess['analytics']) : '';
        html += `
            <div class="dropdown-divider"></div>
            <button class="dropdown-instance dropdown-instance--analytics" 
                    data-action="open" data-type="database" data-id="analytics" 
                    data-name="Unified Analytics" data-symbol="">
                <div class="dropdown-instance__info">
                    <span class="dropdown-instance__name">Unified Analytics</span>
                    <span class="dropdown-instance__meta"><span>Cross-Symbol Analysis</span></span>
                </div>
                ${analyticsTime ? `<span class="dropdown-instance__time">${analyticsTime}</span>` : ''}
            </button>
        `;

        container.innerHTML = html;
        this.bindInstanceClicks(container);
    },

    // BC-051, BC-052: Trading instances with favorites, archived, and context menu
    renderTradingInstances(container) {
        const allViews = this.getSavedTradingViews();
        
        // Split into favorites, active, and archived
        const favorites = allViews.filter(v => v.favorite && !v.archived);
        const active = allViews.filter(v => !v.favorite && !v.archived);
        const archived = allViews.filter(v => v.archived);
        
        // Sort each by lastAccessed DESC
        const sortByRecent = (a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0);
        favorites.sort(sortByRecent);
        active.sort(sortByRecent);
        archived.sort((a, b) => (b.archivedAt || b.lastAccessed || 0) - (a.archivedAt || a.lastAccessed || 0));
        
        let html = `
            <button class="dropdown-instance dropdown-instance--create" data-action="create" data-type="trading">
                <span class="dropdown-instance__name">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    New Algorithm Instance
                </span>
            </button>
        `;
        
        // Favorites section
        if (favorites.length > 0) {
            html += '<div class="dropdown-section-header dropdown-section-header--favorites">★ Favorites</div>';
            favorites.forEach(view => {
                html += this.renderAlgorithmCard(view, true, false);
            });
        }
        
        // Saved Algorithms section
        html += '<div class="dropdown-section-header">Saved Algorithms</div>';
        
        if (active.length === 0 && favorites.length === 0) {
            html += `
                <div class="dropdown-empty">
                    <div class="dropdown-empty__title">No saved algorithms</div>
                    <div class="dropdown-empty__subtitle">Create a new algorithm instance<br>to start trading</div>
                </div>
            `;
        } else if (active.length === 0) {
            html += `<div class="dropdown-empty"><div class="dropdown-empty__subtitle">All algorithms are in Favorites</div></div>`;
        } else {
            active.forEach(view => {
                html += this.renderAlgorithmCard(view, false, false);
            });
        }
        
        // Archived section
        if (archived.length > 0) {
            html += '<div class="dropdown-divider"></div>';
            html += '<div class="dropdown-section-header dropdown-section-header--archived">Archived</div>';
            archived.forEach(view => {
                html += this.renderAlgorithmCard(view, false, true);
            });
        }

        container.innerHTML = html;
        this.bindInstanceClicks(container);
        this.bindAlgorithmContextMenu(container);
    },
    
    renderAlgorithmCard(view, isFavorite, isArchived) {
        const time = this.formatTimestamp(view.lastAccessed);
        const symbolSim = view.symbol ? `${view.symbol}.sim` : '';
        
        let cardClass = 'dropdown-instance';
        if (isArchived) cardClass += ' dropdown-instance--archived';
        
        return `
            <button class="${cardClass}" 
                    data-action="${isArchived ? 'none' : 'open'}" 
                    data-type="trading"
                    data-id="${view.id}" 
                    data-name="${this.escapeHtml(view.name)}" 
                    data-symbol="${view.symbol || ''}"
                    data-favorite="${isFavorite}"
                    data-archived="${isArchived}">
                <div class="dropdown-instance__info">
                    <span class="dropdown-instance__name">
                        ${isFavorite ? '<span class="dropdown-instance__star">★</span> ' : ''}${this.escapeHtml(view.name)}
                    </span>
                    <span class="dropdown-instance__meta">
                        ${symbolSim ? `<span class="dropdown-instance__symbol">${symbolSim}</span>` : ''}
                    </span>
                </div>
                ${time ? `<span class="dropdown-instance__time">${time}</span>` : ''}
            </button>
        `;
    },
    
    bindAlgorithmContextMenu(container) {
        container.querySelectorAll('.dropdown-instance[data-type="trading"]:not([data-action="create"])').forEach(btn => {
            btn.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.showAlgorithmContextMenu(
                    btn.dataset.id,
                    btn.dataset.favorite === 'true',
                    btn.dataset.archived === 'true',
                    e.clientX,
                    e.clientY
                );
            });
        });
    },
    
    showAlgorithmContextMenu(viewId, isFavorite, isArchived, x, y) {
        this.hideAlgorithmContextMenu();
        
        const menu = document.createElement('div');
        menu.className = 'algo-dropdown-context-menu';
        menu.id = 'algo-dropdown-context-menu';
        
        let menuItems = '';
        
        if (isArchived) {
            menuItems = `
                <button class="algo-ctx-item" data-action="restore" data-id="${viewId}">
                    <span class="algo-ctx-icon">↺</span> Restore
                </button>
                <div class="algo-ctx-divider"></div>
                <button class="algo-ctx-item algo-ctx-item--danger" data-action="delete" data-id="${viewId}">
                    <span class="algo-ctx-icon">✕</span> Delete Permanently
                </button>
            `;
        } else {
            menuItems = `
                <button class="algo-ctx-item" data-action="favorite" data-id="${viewId}">
                    <span class="algo-ctx-icon">${isFavorite ? '☆' : '★'}</span> 
                    ${isFavorite ? 'Remove from Favorites' : 'Add to Favorites'}
                </button>
                <button class="algo-ctx-item" data-action="archive" data-id="${viewId}">
                    <span class="algo-ctx-icon">📦</span> Archive
                </button>
                <div class="algo-ctx-divider"></div>
                <button class="algo-ctx-item algo-ctx-item--danger" data-action="delete" data-id="${viewId}">
                    <span class="algo-ctx-icon">✕</span> Delete
                </button>
            `;
        }
        
        menu.innerHTML = menuItems;
        menu.style.cssText = `position: fixed; left: ${x}px; top: ${y}px; z-index: 10000;`;
        
        document.body.appendChild(menu);
        
        menu.querySelectorAll('.algo-ctx-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleAlgorithmContextAction(item.dataset.action, item.dataset.id);
                this.hideAlgorithmContextMenu();
            });
        });
        
        requestAnimationFrame(() => {
            const rect = menu.getBoundingClientRect();
            if (rect.right > window.innerWidth) menu.style.left = (x - rect.width) + 'px';
            if (rect.bottom > window.innerHeight) menu.style.top = (y - rect.height) + 'px';
        });
    },
    
    hideAlgorithmContextMenu() {
        document.getElementById('algo-dropdown-context-menu')?.remove();
    },
    
    handleAlgorithmContextAction(action, viewId) {
        const views = this.getSavedTradingViews();
        const view = views.find(v => v.id === viewId);
        if (!view) return;
        
        switch (action) {
            case 'favorite':
                view.favorite = !view.favorite;
                localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views));
                console.log(`[APEX] ${view.favorite ? 'Favorited' : 'Unfavorited'}:`, view.name);
                break;
                
            case 'archive':
                view.archived = true;
                view.archivedAt = Date.now();
                view.favorite = false;
                localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views));
                console.log('[APEX] Archived:', view.name);
                break;
                
            case 'restore':
                view.archived = false;
                view.archivedAt = null;
                localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views));
                console.log('[APEX] Restored:', view.name);
                break;
                
            case 'delete':
                if (confirm(`Delete "${view.name}"?\n\nThis action cannot be undone.`)) {
                    const updated = views.filter(v => v.id !== viewId);
                    localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(updated));
                    
                    const { tabs } = ApexState.getState();
                    const tabToClose = tabs.find(t => t.instanceId === viewId);
                    if (tabToClose) ApexTabs.close(tabToClose.id);
                    
                    console.log('[APEX] Deleted:', view.name);
                }
                break;
        }
        
        const instancesContainer = this.dropdown.querySelector('.new-tab-dropdown__instances');
        if (instancesContainer) this.renderTradingInstances(instancesContainer);
    },

    renderMetatronInstances(container) {
        let html = `
            <button class="dropdown-instance dropdown-instance--create dropdown-instance--metatron" data-action="open" data-type="metatron" data-id="radial-db" data-name="Radial Database">
                <span class="dropdown-instance__name">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <circle cx="12" cy="12" r="6"></circle>
                        <circle cx="12" cy="12" r="2"></circle>
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                    </svg>
                    Radial Database
                </span>
                <span class="dropdown-instance__meta">4D Time-Capsule</span>
            </button>
            <div class="dropdown-section-header">Architecture</div>
            <div class="dropdown-info-card">
                <div class="dropdown-info-card__row"><span>Ring System</span><span>Fibonacci 0.382 → 1.000</span></div>
                <div class="dropdown-info-card__row"><span>Coordinate</span><span>4D (X, Y, Z, W)</span></div>
                <div class="dropdown-info-card__row"><span>Sync Layer</span><span>Outer perimeter nodes</span></div>
                <div class="dropdown-info-card__row"><span>Integration</span><span>Code node pairs</span></div>
            </div>
        `;

        container.innerHTML = html;
        this.bindInstanceClicks(container);
    },

    expandCreatePanel() {
        this.isExpanded = true;
        this.dropdown.classList.add('new-tab-dropdown--expanded');
        
        const createPanel = this.dropdown.querySelector('.new-tab-dropdown__create');
        createPanel.style.display = 'block';
        
        const symbolsContainer = createPanel.querySelector('.create-panel__symbols');
        const symbols = this.symbolsCache || [];
        
        let html = '';
        
        if (symbols.length === 0) {
            html = '<div class="dropdown-empty"><div class="dropdown-empty__subtitle">No symbols available</div></div>';
        } else {
            symbols.forEach(sym => {
                const bars = (sym.records_1m || 0) + (sym.records_15m || 0);
                const disabled = !sym.available;
                
                html += `
                    <button class="symbol-select ${disabled ? 'symbol-select--disabled' : ''}" 
                            data-id="${sym.id}" data-symbol="${sym.symbol}" data-name="${sym.name}" ${disabled ? 'disabled' : ''}>
                        <span class="symbol-select__name">${sym.name}</span>
                        <span class="symbol-select__meta">${sym.symbol}</span>
                        ${sym.available 
                            ? `<span class="symbol-select__bars">${bars.toLocaleString()}</span>` 
                            : '<span class="symbol-select__unavailable">N/A</span>'}
                    </button>
                `;
            });
        }
        symbolsContainer.innerHTML = html;

        symbolsContainer.querySelectorAll('.symbol-select:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => this.createNewInstance(btn.dataset));
        });

        const input = createPanel.querySelector('#create-instance-name');
        input.value = '';
        setTimeout(() => input.focus(), 100);
    },

    createNewInstance(dataset) {
        const input = this.dropdown.querySelector('#create-instance-name');
        let name = input.value.trim() || `${dataset.name} Algorithm`;
        
        const viewId = 'tr_' + Date.now();
        this.saveTradingView({ id: viewId, name, symbol: dataset.symbol, symbolId: dataset.id });
        
        ApexTabs.create({
            title: name,
            instanceType: 'trading',
            instanceId: viewId,
            symbol: dataset.symbol,
            dbKey: dataset.id
        });
        
        this.hideDropdown();
    },

    getSavedTradingViews() {
        try { 
            return JSON.parse(localStorage.getItem(this.TRADING_VIEWS_KEY) || '[]'); 
        } catch (e) { 
            return []; 
        }
    },

    saveTradingView(view) {
        try {
            const views = this.getSavedTradingViews();
            const idx = views.findIndex(v => v.id === view.id);
            if (idx >= 0) views[idx] = { ...views[idx], ...view, lastAccessed: Date.now() };
            else views.push({ ...view, lastAccessed: Date.now(), createdAt: Date.now() });
            localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views));
        } catch (e) {
            console.warn('[APEX] Could not save trading view:', e.message);
        }
    },

    updateDatabaseAccess(dbId) {
        try {
            const access = JSON.parse(localStorage.getItem(this.DB_ACCESS_KEY) || '{}');
            access[dbId] = Date.now();
            localStorage.setItem(this.DB_ACCESS_KEY, JSON.stringify(access));
        } catch (e) {}
    },

    bindInstanceClicks(container) {
        container.querySelectorAll('.dropdown-instance:not([disabled]):not([data-action="none"])').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (e.target.closest('.dropdown-instance__delete')) return;
                this.handleInstanceClick(btn);
            });
        });
    },

    handleInstanceClick(btn) {
        const action = btn.dataset.action;
        const type = btn.dataset.type;

        if (action === 'create') {
            if (type === 'trading') this.expandCreatePanel();
            return;
        }
        
        if (action === 'open') {
            if (type === 'database') this.updateDatabaseAccess(btn.dataset.id);
            else {
                try {
                    const views = this.getSavedTradingViews();
                    const v = views.find(x => x.id === btn.dataset.id);
                    if (v) { 
                        v.lastAccessed = Date.now(); 
                        localStorage.setItem(this.TRADING_VIEWS_KEY, JSON.stringify(views)); 
                    }
                } catch (e) {}
            }
            
            ApexTabs.create({
                title: btn.dataset.name,
                instanceType: type,
                instanceId: btn.dataset.id,
                symbol: btn.dataset.symbol || null,
                dbKey: btn.dataset.id
            });
        }
        this.hideDropdown();
    },

    setupGlobalClickHandler() {
        document.addEventListener('click', (e) => {
            if (!this.dropdown.contains(e.target) && !this.logoButton.contains(e.target)) {
                this.hideDropdown();
            }
            this.hideContextMenu();
            this.hideAlgorithmContextMenu();
        });
    },

    render(state) {
        const { tabs, activeTabId } = state;
        this.tabsContainer.innerHTML = '';
        tabs.forEach((tab, index) => {
            const tabEl = this.createTabElement(tab, tab.id === activeTabId, index);
            this.tabsContainer.appendChild(tabEl);
        });
    },

    createTabElement(tab, isActive, index) {
        const el = document.createElement('div');
        
        let typeClass = 'tab--type-database';
        if (tab.instanceType === 'trading') typeClass = 'tab--type-trading';
        else if (tab.instanceType === 'metatron') typeClass = 'tab--type-metatron';
        
        el.className = `tab ${typeClass}${isActive ? ' tab--active' : ''}`;
        el.dataset.tabId = tab.id;
        el.dataset.index = index;
        el.draggable = true;

        el.innerHTML = `
            <div class="tab__favicon"></div>
            <span class="tab__title" title="${this.escapeHtml(tab.title)}">${this.escapeHtml(tab.title)}</span>
            <button class="tab__close" aria-label="Close tab">×</button>
        `;

        el.addEventListener('click', (e) => {
            if (!e.target.closest('.tab__close')) ApexTabs.activate(tab.id);
        });
        el.querySelector('.tab__close').addEventListener('click', (e) => {
            e.stopPropagation();
            ApexTabs.close(tab.id);
        });
        el.addEventListener('auxclick', (e) => { 
            if (e.button === 1) { e.preventDefault(); ApexTabs.close(tab.id); } 
        });
        el.addEventListener('contextmenu', (e) => { 
            e.preventDefault(); 
            this.showContextMenu(tab.id, e.clientX, e.clientY); 
        });

        el.addEventListener('dragstart', (e) => this.onDragStart(e, tab.id, index));
        el.addEventListener('dragend', () => this.onDragEnd());
        el.addEventListener('dragover', (e) => this.onDragOver(e, index));
        el.addEventListener('drop', (e) => this.onDrop(e, index));

        return el;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    onDragStart(e, tabId, index) {
        this.dragState = { isDragging: true, draggedTabId: tabId, startIndex: index };
        e.target.closest('.tab').classList.add('tab--dragging');
        e.dataTransfer.effectAllowed = 'move';
    },

    onDragEnd() {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab--dragging', 'tab--drag-over'));
        this.dragState = { isDragging: false, draggedTabId: null, startIndex: 0 };
    },

    onDragOver(e, index) {
        if (!this.dragState.isDragging) return;
        e.preventDefault();
        const tab = e.target.closest('.tab');
        if (tab && tab.dataset.tabId !== this.dragState.draggedTabId) {
            document.querySelectorAll('.tab--drag-over').forEach(t => t.classList.remove('tab--drag-over'));
            tab.classList.add('tab--drag-over');
        }
    },

    onDrop(e, toIndex) {
        e.preventDefault();
        if (!this.dragState.isDragging) return;
        if (this.dragState.startIndex !== toIndex) ApexTabs.reorder(this.dragState.startIndex, toIndex);
    },

    showContextMenu(tabId, x, y) {
        this.hideContextMenu();
        const menu = document.createElement('div');
        menu.className = 'tab-context-menu tab-context-menu--visible';
        menu.innerHTML = `
            <button class="context-menu__item" data-action="duplicate">Duplicate</button>
            <button class="context-menu__item" data-action="rename">Rename</button>
            <div class="context-menu__divider"></div>
            <button class="context-menu__item context-menu__item--danger" data-action="close">Close</button>
        `;
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (action) { 
                this.handleContextAction(action, tabId); 
                this.hideContextMenu(); 
            }
        });
        document.body.appendChild(menu);
    },

    hideContextMenu() {
        document.querySelectorAll('.tab-context-menu').forEach(m => m.remove());
    },

    handleContextAction(action, tabId) {
        const { tabs } = ApexState.getState();
        const tab = tabs.find(t => t.id === tabId);
        if (action === 'duplicate') ApexTabs.duplicate(tabId);
        else if (action === 'rename') {
            const newTitle = prompt('Enter new tab name:', tab?.title || '');
            if (newTitle) ApexTabs.update(tabId, { title: newTitle });
        }
        else if (action === 'close') ApexTabs.close(tabId);
    },

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 't') { 
                e.preventDefault(); 
                this.showDropdown(); 
            }
            if (e.ctrlKey && e.key === 'w') { 
                e.preventDefault(); 
                const a = ApexTabs.getActive(); 
                if (a) ApexTabs.close(a.id); 
            }
            if (e.key === 'Escape') { 
                this.hideDropdown(); 
                this.hideContextMenu();
                this.hideAlgorithmContextMenu();
            }
        });
    }
};

window.ApexTabRenderer = ApexTabRenderer;
