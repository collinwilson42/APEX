/* ═══════════════════════════════════════════════════════════════════════════
   TORRA TRADER BRIDGE v2.0 — Config-First Frontend Validation
   Seed 19: The Rewired Engine
   
   Pre-flight checks BEFORE hitting the backend:
   1. ProfileManager has an active profile with API key
   2. tradingConfig exists with sentiment_weights, thresholds, timeframe_weights
   3. Weights sum to ~1.0
   
   Only after pre-flight passes does the bridge POST to /api/trader/toggle.
   The backend runs its own validation gate (double-check), then spawns.
   
   API key flow: Profile Manager → this bridge → POST body → backend env var → trader subprocess
   The API key NEVER touches the database.
   ═══════════════════════════════════════════════════════════════════════════ */

const TorraTraderBridge = {

    // ═══════════════════════════════════════════════════════════════════
    // DEFAULT TRADING CONFIG (Seed 19: ATH replaces Volume)
    // ═══════════════════════════════════════════════════════════════════

    DEFAULT_TRADING_CONFIG: {
        sentiment_weights: {
            price_action: 0.30,
            key_levels:   0.15,
            momentum:     0.25,
            ath:          0.10,
            structure:    0.20
        },
        timeframe_weights: {
            "15m": 0.40,
            "1h":  0.60
        },
        thresholds: {
            buy:       0.55,
            sell:     -0.55,
            dead_zone: 0.25,
            gut_veto:  0.30
        },
        risk: {
            base_lots:             1.0,
            max_lots:              1.0,
            stop_loss_points:      80,
            take_profit_points:    200,
            max_signals_per_hour:  3,
            cooldown_seconds:      300,
            consecutive_loss_halt: 2,
            sentiment_exit:        true
        }
    },

    // Track running traders
    _runningTraders: {},
    _pollInterval: null,

    // ═══════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════

    init() {
        this._startStatusPolling();
        console.log('[TorraTraderBridge] v2.0 initialized — Config-First');
    },

    // ═══════════════════════════════════════════════════════════════════
    // PRE-FLIGHT VALIDATION (Seed 19: Config-First Gate)
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Run all pre-flight checks before allowing trader start.
     * Returns { valid: true } or { valid: false, errors: [...] }
     */
    preflight() {
        const errors = [];

        // 1. ProfileManager must exist and have an active profile
        if (typeof ProfileManager === 'undefined') {
            errors.push('Profile Manager not loaded');
            return { valid: false, errors };
        }

        const config = ProfileManager.getActiveConfig();
        if (!config) {
            errors.push('No active profile — select one in Profile Manager');
            return { valid: false, errors };
        }

        // 2. API key must be set
        if (!config.apiKey || !config.apiKey.trim()) {
            errors.push('No API key — enter one in Profile Manager → API Key field');
            return { valid: false, errors };
        }

        // 3. Trading config must exist with required sections
        const tc = config.tradingConfig || this.DEFAULT_TRADING_CONFIG;

        if (!tc.sentiment_weights) {
            errors.push('Trading config missing sentiment_weights');
        } else {
            const wSum = Object.values(tc.sentiment_weights).reduce((a, b) => a + b, 0);
            if (Math.abs(wSum - 1.0) > 0.05) {
                errors.push(`Weights sum to ${wSum.toFixed(3)}, should be ~1.0`);
            }
        }

        if (!tc.thresholds || tc.thresholds.buy === undefined) {
            errors.push('Trading config missing thresholds');
        }

        if (!tc.timeframe_weights) {
            errors.push('Trading config missing timeframe_weights');
        }

        return { valid: errors.length === 0, errors };
    },

    // ═══════════════════════════════════════════════════════════════════
    // CONFIG + CREDENTIALS
    // ═══════════════════════════════════════════════════════════════════

    getTradingConfig() {
        if (typeof ProfileManager !== 'undefined') {
            const activeConfig = ProfileManager.getActiveConfig();
            if (activeConfig?.tradingConfig) {
                return activeConfig.tradingConfig;
            }
        }
        return { ...this.DEFAULT_TRADING_CONFIG };
    },

    saveTradingConfig(config) {
        if (typeof ProfileManager !== 'undefined' && ProfileManager.activeProfileId) {
            ProfileManager.updateProfile(ProfileManager.activeProfileId, {
                trading_config: config
            });
        }
    },

    getActiveCredentials() {
        if (typeof ProfileManager === 'undefined') return null;
        const config = ProfileManager.getActiveConfig();
        if (!config || !config.apiKey) return null;

        return {
            api_key:    config.apiKey,
            provider:   config.provider || 'anthropic',
            model:      config.model || 'claude-sonnet-4-20250514',
            profile_id: config.id || ''
        };
    },

    // ═══════════════════════════════════════════════════════════════════
    // TRADER TOGGLE — Called on double-tap "Active"
    // ═══════════════════════════════════════════════════════════════════

    async toggleTrader(instanceId, symbol) {
        if (!instanceId) {
            this._showToast('No instance selected', 'error');
            return;
        }

        // If already running, just stop
        if (this._runningTraders[instanceId]?.state === 'running') {
            return this.stopTrader(instanceId);
        }

        return this.startTrader(instanceId, symbol);
    },

    async startTrader(instanceId, symbol) {
        // ── PRE-FLIGHT CHECK (Seed 19) ──
        const check = this.preflight();
        if (!check.valid) {
            // Show each error as a separate toast line
            const msg = check.errors.join('\n');
            this._showToast(`✗ Cannot start trader:\n${msg}`, 'error');
            console.error('[TorraTraderBridge] Pre-flight failed:', check.errors);
            return { success: false, errors: check.errors };
        }

        const creds = this.getActiveCredentials();
        const tradingConfig = this.getTradingConfig();

        this._showToast(`Starting trader for ${symbol || instanceId}...`, 'info');

        try {
            const response = await fetch('/api/trader/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instance_id:    instanceId,
                    api_key:        creds.api_key,
                    provider:       creds.provider,
                    model:          creds.model,
                    trading_config: tradingConfig,
                    symbol:         symbol || '',
                    profile_id:     creds.profile_id || ''
                })
            });

            const result = await response.json();

            if (result.success) {
                this._runningTraders[instanceId] = { state: 'running', ...result.trader };
                this._showToast(`✓ Trader started — waiting for next 15m tick`, 'success');
                this._updateStatusIndicator(instanceId, 'running');
                
                window.dispatchEvent(new CustomEvent('torra:trader:started', {
                    detail: { instanceId, symbol, trader: result.trader }
                }));
            } else {
                // Backend validation errors (double-check gate)
                const errMsg = result.validation_errors
                    ? result.validation_errors.join('\n')
                    : result.error;
                this._showToast(`✗ ${errMsg}`, 'error');
            }

            return result;

        } catch (e) {
            console.error('[TorraTraderBridge] Start failed:', e);
            this._showToast(`Connection error: ${e.message}`, 'error');
            return { success: false, error: e.message };
        }
    },

    async stopTrader(instanceId) {
        this._showToast('Stopping trader...', 'info');

        try {
            const response = await fetch('/api/trader/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instance_id: instanceId })
            });

            const result = await response.json();

            if (result.success) {
                delete this._runningTraders[instanceId];
                this._showToast('✓ Trader stopped', 'success');
                this._updateStatusIndicator(instanceId, 'stopped');
                
                window.dispatchEvent(new CustomEvent('torra:trader:stopped', {
                    detail: { instanceId }
                }));
            } else {
                this._showToast(`✗ ${result.error}`, 'error');
            }

            return result;

        } catch (e) {
            console.error('[TorraTraderBridge] Stop failed:', e);
            this._showToast(`Connection error: ${e.message}`, 'error');
            return { success: false, error: e.message };
        }
    },

    // ═══════════════════════════════════════════════════════════════════
    // STATUS POLLING
    // ═══════════════════════════════════════════════════════════════════

    _startStatusPolling() {
        this._pollInterval = setInterval(() => this._pollStatus(), 5000);
        this._pollStatus();
    },

    async _pollStatus() {
        try {
            const response = await fetch('/api/trader/status');
            const result = await response.json();

            if (result.traders) {
                this._runningTraders = result.traders;
                for (const [iid, trader] of Object.entries(result.traders)) {
                    this._updateStatusIndicator(iid, trader.state);
                }
            }
        } catch (e) {
            // Silent fail — status polling is informational
        }
    },

    // ═══════════════════════════════════════════════════════════════════
    // UI HELPERS
    // ═══════════════════════════════════════════════════════════════════

    _updateStatusIndicator(instanceId, state) {
        const dot = document.querySelector(
            `.pm-status-dot[data-instance="${instanceId}"], ` +
            `.trader-status-indicator[data-instance="${instanceId}"]`
        );
        if (dot) {
            dot.className = `trader-status-indicator trader-status-indicator--${state}`;
            dot.title = state === 'running' ? 'Trader Active' : 'Trader Inactive';
        }

        const card = document.querySelector(`.algo-card[data-id="${instanceId}"]`);
        if (card) {
            card.classList.toggle('algo-card--trader-active', state === 'running');
        }
    },

    _showToast(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }

        const existing = document.getElementById('torra-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.id = 'torra-toast';
        toast.className = `torra-toast torra-toast--${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            padding: 12px 24px; border-radius: 8px; z-index: 99999;
            font-family: 'SF Mono', monospace; font-size: 13px;
            color: #E0D5C1; backdrop-filter: blur(10px);
            white-space: pre-line; max-width: 500px; text-align: center;
            background: ${type === 'error' ? 'rgba(200,50,50,0.9)' : 
                         type === 'success' ? 'rgba(50,150,80,0.9)' : 
                         'rgba(10,37,64,0.9)'};
            border: 1px solid ${type === 'error' ? '#c83232' : 
                               type === 'success' ? '#32963c' : '#BB9847'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: toastSlideUp 0.3s ease-out;
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), type === 'error' ? 6000 : 4000);
    },

    // ═══════════════════════════════════════════════════════════════════
    // CONFIG EDITOR HELPERS
    // ═══════════════════════════════════════════════════════════════════

    exportConfig() {
        return JSON.stringify(this.getTradingConfig(), null, 2);
    },

    importConfig(jsonStr) {
        try {
            const config = JSON.parse(jsonStr);
            if (!config.sentiment_weights || !config.thresholds || !config.risk) {
                throw new Error('Missing required config sections');
            }
            this.saveTradingConfig(config);
            return { success: true };
        } catch (e) {
            return { success: false, error: e.message };
        }
    },

    isRunning(instanceId) {
        return this._runningTraders[instanceId]?.state === 'running';
    }
};


// ═══════════════════════════════════════════════════════════════════════════
// INSTANCE BROWSER INTEGRATION — Double-tap "Active" to toggle trader
// ═══════════════════════════════════════════════════════════════════════════

(function wireInstanceBrowserActivation() {
    
    window.addEventListener('torra:activate', (e) => {
        const { instanceId, symbol } = e.detail;
        TorraTraderBridge.toggleTrader(instanceId, symbol);
    });

    if (typeof ApexInstanceBrowser !== 'undefined') {
        const originalRenderCard = ApexInstanceBrowser.renderCard;
        
        ApexInstanceBrowser.renderCard = function(view, isFavorite, isArchived) {
            let html = originalRenderCard.call(this, view, isFavorite, isArchived);
            
            const isTraderRunning = TorraTraderBridge.isRunning(view.id);
            const traderIndicator = `<div class="trader-status-indicator trader-status-indicator--${isTraderRunning ? 'running' : 'stopped'}" 
                                          data-instance="${view.id}" 
                                          title="${isTraderRunning ? 'Trader Active (double-tap to stop)' : 'Double-tap to start trader'}"
                                          ondblclick="event.stopPropagation(); TorraTraderBridge.toggleTrader('${view.id}', '${view.symbol || ''}')">
                                          ${isTraderRunning ? '⚡' : '○'}
                                     </div>`;
            
            html = html.replace(/<\/div>\s*$/, traderIndicator + '</div>');
            return html;
        };
    }

})();


// ═══════════════════════════════════════════════════════════════════════════
// CSS for trader status indicators
// ═══════════════════════════════════════════════════════════════════════════

(function injectTraderCSS() {
    const style = document.createElement('style');
    style.textContent = `
        .trader-status-indicator {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
        }
        
        .trader-status-indicator--running {
            background: rgba(187, 152, 71, 0.2);
            border: 2px solid #BB9847;
            color: #BB9847;
            animation: traderPulse 2s infinite;
        }
        
        .trader-status-indicator--stopped {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: rgba(255, 255, 255, 0.3);
        }
        
        .trader-status-indicator--stopped:hover {
            border-color: #BB9847;
            color: #BB9847;
        }
        
        .algo-card--trader-active {
            border-left: 3px solid #BB9847 !important;
        }
        
        @keyframes traderPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(187, 152, 71, 0.4); }
            50% { box-shadow: 0 0 0 6px rgba(187, 152, 71, 0); }
        }
        
        @keyframes toastSlideUp {
            from { transform: translateX(-50%) translateY(20px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
})();


document.addEventListener('DOMContentLoaded', () => {
    TorraTraderBridge.init();
});

window.TorraTraderBridge = TorraTraderBridge;
