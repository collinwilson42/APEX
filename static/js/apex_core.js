/* ═══════════════════════════════════════════════════════════════════════════
   APEX CORE V2 - State Manager, Layout Controller & Instance System
   Connected to init.py database, session persistence
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Instance Types
 */
const INSTANCE_TYPES = {
    DATABASE: {
        id: 'database',
        name: 'Intelligence Database',
        shortName: 'Database',
        color: '#46B4AF',  // Teal
        defaultTitle: 'Intelligence DB'
    },
    TRADING: {
        id: 'trading',
        name: 'Relativity Trading',
        shortName: 'Trading',
        color: '#ADEBB3',  // Mint
        defaultTitle: 'Trading View'
    }
};

/**
 * APEX State Manager
 */
const ApexState = {
    state: {
        tabs: [],
        activeTabId: null,
        instances: {},  // Cached instance data
        layout: {
            viewPanelRatio: 0.5
        },
        ui: {
            newTabDropdownVisible: false,
            newTabDropdownPosition: { x: 0, y: 0 },
            selectedInstanceType: 'database',
            contextMenuVisible: false,
            contextMenuPosition: { x: 0, y: 0 },
            contextMenuTabId: null
        }
    },

    listeners: [],

    subscribe(callback) {
        this.listeners.push(callback);
        return () => {
            this.listeners = this.listeners.filter(l => l !== callback);
        };
    },

    setState(partial) {
        this.state = this.deepMerge(this.state, partial);
        this.listeners.forEach(cb => cb(this.state));
        this.persist();
    },

    getState() {
        return this.state;
    },

    deepMerge(target, source) {
        const result = { ...target };
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.deepMerge(target[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        return result;
    },

    persist() {
        try {
            const toSave = {
                tabs: this.state.tabs,
                activeTabId: this.state.activeTabId,
                layout: this.state.layout
            };
            localStorage.setItem('apex_state_v2', JSON.stringify(toSave));
        } catch (e) {
            console.warn('Failed to persist state:', e);
        }
    },

    restore() {
        try {
            const saved = localStorage.getItem('apex_state_v2');
            if (saved) {
                const parsed = JSON.parse(saved);
                this.state = this.deepMerge(this.state, parsed);
                return true;
            }
        } catch (e) {
            console.warn('Failed to restore state:', e);
        }
        return false;
    }
};


/**
 * APEX Layout Controller
 */
const ApexLayout = {
    elements: {},

    init() {
        this.elements = {
            app: document.getElementById('apex-app'),
            tabBar: document.getElementById('apex-tab-bar'),
            main: document.getElementById('apex-main'),
            viewPanel: document.getElementById('apex-view-panel'),
            divider: document.getElementById('apex-divider'),
            controlCenter: document.getElementById('apex-control-center')
        };

        this.setupDividerDrag();
        this.applyLayout();

        ApexState.subscribe(state => {
            this.applyLayout();
            this.updateControlCenterHeader(state);
        });
    },

    applyLayout() {
        const { viewPanelRatio } = ApexState.getState().layout;
        const controlCenterRatio = 1 - viewPanelRatio;

        if (this.elements.viewPanel) {
            this.elements.viewPanel.style.flex = viewPanelRatio;
        }
        if (this.elements.controlCenter) {
            this.elements.controlCenter.style.flex = controlCenterRatio;
        }
    },

    setupDividerDrag() {
        const divider = this.elements.divider;
        if (!divider) return;

        let startY = 0;
        let startRatio = 0;

        const onMouseDown = (e) => {
            e.preventDefault();
            startY = e.clientY;
            startRatio = ApexState.getState().layout.viewPanelRatio;
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
        };

        const onMouseMove = (e) => {
            const mainRect = this.elements.main.getBoundingClientRect();
            const deltaY = e.clientY - startY;
            const deltaRatio = deltaY / mainRect.height;
            
            let newRatio = startRatio + deltaRatio;
            newRatio = Math.max(0.25, Math.min(0.75, newRatio));

            ApexState.setState({ layout: { viewPanelRatio: newRatio } });
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        divider.addEventListener('mousedown', onMouseDown);
    },

    updateControlCenterHeader(state) {
        const activeTab = state.tabs.find(t => t.id === state.activeTabId);
        const headerContent = document.querySelector('.control-center__header-content');
        
        if (!headerContent) return;

        if (!activeTab) {
            headerContent.innerHTML = `
                <div class="no-instance">
                    <div class="no-instance__title">No Instance Selected</div>
                    <div class="no-instance__subtitle">Create or select a tab to begin</div>
                </div>
            `;
            return;
        }

        const typeInfo = activeTab.instanceType === 'trading' ? INSTANCE_TYPES.TRADING : INSTANCE_TYPES.DATABASE;
        const typeClass = activeTab.instanceType === 'trading' ? 'trading' : 'database';

        headerContent.innerHTML = `
            <div class="control-center__instance-type control-center__instance-type--${typeClass}">
                ${typeInfo.name}
            </div>
            <div class="control-center__instance-name">${activeTab.title}</div>
            ${activeTab.symbol ? `<div class="control-center__instance-symbol">${activeTab.symbol}</div>` : ''}
        `;
    }
};


/**
 * APEX Tab Manager
 */
const ApexTabs = {
    generateId() {
        return 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    create(options = {}) {
        const id = this.generateId();
        const instanceType = options.instanceType || 'database';
        const typeInfo = instanceType === 'trading' ? INSTANCE_TYPES.TRADING : INSTANCE_TYPES.DATABASE;
        
        const tab = {
            id,
            title: options.title || typeInfo.defaultTitle,
            instanceType,
            instanceId: options.instanceId || null,
            symbol: options.symbol || null,
            dbKey: options.dbKey || options.instanceId || null,  // CRITICAL: Store dbKey for symbol routing
            isLoading: false,
            createdAt: Date.now(),
            lastAccessed: Date.now()
        };

        const { tabs } = ApexState.getState();
        ApexState.setState({
            tabs: [...tabs, tab],
            activeTabId: id
        });

        return tab;
    },

    close(tabId) {
        const { tabs, activeTabId } = ApexState.getState();
        const tabIndex = tabs.findIndex(t => t.id === tabId);
        
        if (tabIndex === -1) return;

        const newTabs = tabs.filter(t => t.id !== tabId);
        let newActiveId = activeTabId;

        if (activeTabId === tabId && newTabs.length > 0) {
            const newIndex = Math.min(tabIndex, newTabs.length - 1);
            newActiveId = newTabs[newIndex].id;
        } else if (newTabs.length === 0) {
            newActiveId = null;
        }

        ApexState.setState({
            tabs: newTabs,
            activeTabId: newActiveId
        });
    },

    activate(tabId) {
        const { tabs } = ApexState.getState();
        const updatedTabs = tabs.map(t => 
            t.id === tabId ? { ...t, lastAccessed: Date.now() } : t
        );
        ApexState.setState({ 
            tabs: updatedTabs,
            activeTabId: tabId 
        });
    },

    update(tabId, updates) {
        const { tabs } = ApexState.getState();
        const newTabs = tabs.map(t => 
            t.id === tabId ? { ...t, ...updates } : t
        );
        ApexState.setState({ tabs: newTabs });
    },

    reorder(fromIndex, toIndex) {
        const { tabs } = ApexState.getState();
        const newTabs = [...tabs];
        const [moved] = newTabs.splice(fromIndex, 1);
        newTabs.splice(toIndex, 0, moved);
        ApexState.setState({ tabs: newTabs });
    },

    getActive() {
        const { tabs, activeTabId } = ApexState.getState();
        return tabs.find(t => t.id === activeTabId) || null;
    },

    closeOthers(keepTabId) {
        const { tabs } = ApexState.getState();
        const newTabs = tabs.filter(t => t.id === keepTabId);
        ApexState.setState({
            tabs: newTabs,
            activeTabId: keepTabId
        });
    },

    closeToRight(tabId) {
        const { tabs, activeTabId } = ApexState.getState();
        const tabIndex = tabs.findIndex(t => t.id === tabId);
        const newTabs = tabs.slice(0, tabIndex + 1);
        
        let newActiveId = activeTabId;
        if (!newTabs.find(t => t.id === activeTabId)) {
            newActiveId = newTabs[newTabs.length - 1]?.id || null;
        }
        
        ApexState.setState({
            tabs: newTabs,
            activeTabId: newActiveId
        });
    },

    duplicate(tabId) {
        const { tabs } = ApexState.getState();
        const sourceTab = tabs.find(t => t.id === tabId);
        if (!sourceTab) return;

        this.create({
            title: sourceTab.title + ' (Copy)',
            instanceType: sourceTab.instanceType,
            symbol: sourceTab.symbol
        });
    }
};


/**
 * Instance Data Fetcher
 * Communicates with Flask API
 */
const ApexAPI = {
    baseUrl: '',

    async getStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/api/status`);
            return await response.json();
        } catch (e) {
            console.error('API Status Error:', e);
            return null;
        }
    },

    async getInstances(type) {
        try {
            const response = await fetch(`${this.baseUrl}/api/apex/instances?type=${type}`);
            const data = await response.json();
            if (data.success) {
                return data.instances.map(inst => ({
                    id: inst.id,
                    name: inst.name,
                    symbol: inst.symbol,
                    signalsToday: inst.signals_today,
                    trend: inst.trend,
                    pf: inst.pf,
                    np: inst.np,
                    regime: inst.regime,
                    confidence: inst.confidence
                }));
            }
            return [];
        } catch (e) {
            console.error('Failed to fetch instances:', e);
            return [];
        }
    }
};


/**
 * Initialize APEX
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  APEX v2 - Adaptive Platform for Evolving eXecution');
    console.log('═══════════════════════════════════════════════════════════════');

    // Restore state
    const hasState = ApexState.restore();
    
    // Initialize layout
    ApexLayout.init();

    // Initialize tab renderer
    if (window.ApexTabRenderer) {
        ApexTabRenderer.init();
    }

    // If no tabs exist, don't create welcome - wait for user to select
    const { tabs } = ApexState.getState();
    if (tabs.length > 0) {
        // Ensure there's an active tab
        const { activeTabId } = ApexState.getState();
        if (!activeTabId || !tabs.find(t => t.id === activeTabId)) {
            ApexState.setState({ activeTabId: tabs[0].id });
        }
    }

    // Update control center header
    ApexLayout.updateControlCenterHeader(ApexState.getState());

    console.log(`  Restored ${tabs.length} tab(s)`);
    console.log('═══════════════════════════════════════════════════════════════');
});


// Expose to window
window.ApexState = ApexState;
window.ApexLayout = ApexLayout;
window.ApexTabs = ApexTabs;
window.ApexAPI = ApexAPI;
window.INSTANCE_TYPES = INSTANCE_TYPES;
