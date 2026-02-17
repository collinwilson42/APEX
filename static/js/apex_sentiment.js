/* ═══════════════════════════════════════════════════════════════════════════
   APEX SENTIMENT PANEL v4.0 — Seed 22: Three-Panel Rotation
   
   Displays REAL AI sentiment scores + Agent Debate results from the instance
   database.  When the TORRA trader is running, this module polls
   /api/instance/<id>/sentiments/latest and rotates three views:
   
     Phase 0: MATRIX    — Markov transition matrix (default view)
     Phase 1: SCORES    — 5 scored vectors + composite banner
     Phase 2: DEBATE    — Agent deliberation breakdown (Seed 22)
   
   Each phase shows for 5 seconds (15 s full cycle).

   Score Layout: 3 top / 2 bottom grid
   Signal Colors: Mint Green = BUY · Teal Blue = SELL
   ═══════════════════════════════════════════════════════════════════════════ */

var ApexSentiment = {
    // State
    isRunning: false,
    currentSymbol: 'XAUJ26',
    currentInstanceId: null,
    currentReadings: { '15m': null, '1h': null },

    // Rotation
    PHASE_NAMES: ['matrix', 'scores', 'debate'],
    PHASE_DURATION: 5000,  // 5 seconds per phase
    rotationPhase: { '15m': 0, '1h': 0 },
    rotationTimers: { '15m': null, '1h': null },

    // Polling
    pollInterval: null,
    pollRateMs: 5000,

    // DOM references
    containers: { '15m': null, '1h': null },

    // Category metadata
    categories: [
        { key: 'price_action', dbKey: 'price_action_score', label: 'Price Action', icon: '◆', abbr: 'PA' },
        { key: 'key_levels',   dbKey: 'key_levels_score',   label: 'Key Levels',   icon: '═', abbr: 'KL' },
        { key: 'momentum',     dbKey: 'momentum_score',     label: 'Momentum',     icon: '↗', abbr: 'MOM' },
        { key: 'ath',          dbKey: 'ath_score',           label: 'All Time High', icon: '▲', abbr: 'ATH' },
        { key: 'structure',    dbKey: 'structure_score',     label: 'Structure',    icon: '◫', abbr: 'STR' }
    ],

    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════

    init: function() {
        var self = this;
        window.addEventListener('torra:trader:started', function(e) {
            var d = e.detail;
            self.startEngine(d.symbol, d.instanceId);
        });
        window.addEventListener('torra:trader:stopped', function() {
            self.stopEngine();
        });
        console.log('[ApexSentiment] v4.0 initialized — 3-panel rotation ready');
    },

    // ═══════════════════════════════════════════════════════════════════════
    // ENGINE CONTROL
    // ═══════════════════════════════════════════════════════════════════════

    startEngine: function(symbol, instanceId) {
        this.isRunning = true;
        this.currentSymbol = symbol || 'XAUJ26';
        this.currentInstanceId = instanceId || this._resolveInstanceId();
        if (!this.currentInstanceId) {
            console.warn('[ApexSentiment] No instance ID — cannot poll DB');
            return;
        }
        console.log('[ApexSentiment] Engine STARTED — ' + this.currentInstanceId);
        this.startPolling();
        this.fetchLatest();
    },

    stopEngine: function() {
        if (!this.isRunning) return;
        this.isRunning = false;
        this.stopPolling();
        this._stopRotation('15m');
        this._stopRotation('1h');
        this._hideOverlay('15m');
        this._hideOverlay('1h');
        this._updateHeaderTitle('15m', 'matrix', null);
        this._updateHeaderTitle('1h', 'matrix', null);
        console.log('[ApexSentiment] Engine STOPPED');
    },

    _resolveInstanceId: function() {
        if (typeof ApexInstanceBrowser !== 'undefined' && ApexInstanceBrowser.currentInstanceId) {
            return ApexInstanceBrowser.currentInstanceId;
        }
        try {
            var saved = JSON.parse(localStorage.getItem('apex_selected_instance') || '{}');
            return saved.instanceId || null;
        } catch (e) { return null; }
    },

    // ═══════════════════════════════════════════════════════════════════════
    // DB POLLING
    // ═══════════════════════════════════════════════════════════════════════

    startPolling: function() {
        this.stopPolling();
        var self = this;
        this.pollInterval = setInterval(function() { self.fetchLatest(); }, this.pollRateMs);
    },

    stopPolling: function() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },

    fetchLatest: function() {
        if (!this.currentInstanceId) return;
        var self = this;
        fetch('/api/instance/' + this.currentInstanceId + '/sentiments/latest')
            .then(function(r) { return r.json(); })
            .then(function(result) {
                if (!result.success) return;
                ['15m', '1h'].forEach(function(tf) {
                    if (result[tf]) {
                        var prev = self.currentReadings[tf];
                        var nr = result[tf];
                        if (!prev || prev.id !== nr.id) {
                            self.currentReadings[tf] = nr;
                            self._onNewReading(tf, nr);
                        }
                    }
                });
            })
            .catch(function() {});
    },

    _onNewReading: function(tf, reading) {
        // Build/refresh both overlay panels, then start rotation if not running
        this._ensureOverlayDOM(tf);
        this._renderScoresPanel(tf, reading);
        this._renderDebatePanel(tf, reading);
        if (!this.rotationTimers[tf]) {
            this._startRotation(tf);
        }
    },

    // ═══════════════════════════════════════════════════════════════════════
    // THREE-PHASE ROTATION
    // ═══════════════════════════════════════════════════════════════════════

    _startRotation: function(tf) {
        this._stopRotation(tf);
        var self = this;
        // Start immediately at phase 0 (matrix)
        this.rotationPhase[tf] = 0;
        this._applyPhase(tf);
        this.rotationTimers[tf] = setInterval(function() {
            self.rotationPhase[tf] = (self.rotationPhase[tf] + 1) % 3;
            self._applyPhase(tf);
        }, this.PHASE_DURATION);
    },

    _stopRotation: function(tf) {
        if (this.rotationTimers[tf]) {
            clearInterval(this.rotationTimers[tf]);
            this.rotationTimers[tf] = null;
        }
    },

    _applyPhase: function(tf) {
        var phase = this.rotationPhase[tf];
        var phaseName = this.PHASE_NAMES[phase];
        var container = document.getElementById('matrix-' + tf);
        if (!container) return;

        var scoresEl = container.querySelector('.sentiment-overlay--scores');
        var debateEl = container.querySelector('.sentiment-overlay--debate');
        var reading = this.currentReadings[tf];

        if (phaseName === 'matrix') {
            // Show matrix, hide overlays
            if (scoresEl) scoresEl.classList.remove('sentiment-overlay--visible');
            if (debateEl) debateEl.classList.remove('sentiment-overlay--visible');
        } else if (phaseName === 'scores') {
            if (scoresEl) scoresEl.classList.add('sentiment-overlay--visible');
            if (debateEl) debateEl.classList.remove('sentiment-overlay--visible');
        } else if (phaseName === 'debate') {
            if (scoresEl) scoresEl.classList.remove('sentiment-overlay--visible');
            if (debateEl) debateEl.classList.add('sentiment-overlay--visible');
        }

        this._updateHeaderTitle(tf, phaseName, reading);
    },

    _hideOverlay: function(tf) {
        var container = document.getElementById('matrix-' + tf);
        if (!container) return;
        var els = container.querySelectorAll('.sentiment-overlay--scores, .sentiment-overlay--debate');
        for (var i = 0; i < els.length; i++) {
            els[i].classList.remove('sentiment-overlay--visible');
        }
    },

    // ═══════════════════════════════════════════════════════════════════════
    // DOM SCAFFOLDING
    // ═══════════════════════════════════════════════════════════════════════

    _ensureOverlayDOM: function(tf) {
        var container = document.getElementById('matrix-' + tf);
        if (!container) return;
        this.containers[tf] = container;

        if (!container.querySelector('.sentiment-overlay--scores')) {
            var el = document.createElement('div');
            el.className = 'sentiment-overlay sentiment-overlay--scores';
            container.appendChild(el);
        }
        if (!container.querySelector('.sentiment-overlay--debate')) {
            var el2 = document.createElement('div');
            el2.className = 'sentiment-overlay sentiment-overlay--debate';
            container.appendChild(el2);
        }
    },

    // ═══════════════════════════════════════════════════════════════════════
    // HEADER TITLE UPDATES
    // ═══════════════════════════════════════════════════════════════════════

    _updateHeaderTitle: function(tf, phaseName, reading) {
        var cell = document.getElementById('matrix-' + tf + '-container');
        if (!cell) return;
        var titleEl = cell.querySelector('.trading-cell__title');
        if (!titleEl) return;

        if (phaseName === 'matrix' || !reading) {
            titleEl.textContent = 'Transition Matrix';
            titleEl.classList.remove('trading-cell__title--sentiment');
            return;
        }

        var signal = reading.signal_direction || 'HOLD';
        var signalClass = signal === 'BUY' ? 'signal--buy' : signal === 'SELL' ? 'signal--sell' : 'signal--hold';

        if (phaseName === 'scores') {
            titleEl.innerHTML = '<span class="sentiment-title-label">SCORES</span> ' +
                tf.toUpperCase() + ' <span class="sentiment-signal ' + signalClass + '">' + signal + '</span>';
        } else if (phaseName === 'debate') {
            titleEl.innerHTML = '<span class="sentiment-title-label sentiment-title-label--debate">DEBATE</span> ' +
                tf.toUpperCase() + ' <span class="sentiment-signal ' + signalClass + '">' + signal + '</span>';
        }
        titleEl.classList.add('trading-cell__title--sentiment');
    },

    // ═══════════════════════════════════════════════════════════════════════
    // SCORES PANEL (Phase 1) — 3-top / 2-bottom layout
    // ═══════════════════════════════════════════════════════════════════════

    _renderScoresPanel: function(tf, reading) {
        var container = document.getElementById('matrix-' + tf);
        if (!container) return;
        var el = container.querySelector('.sentiment-overlay--scores');
        if (!el) return;

        var composite = reading.composite_score || 0;
        var consensus = reading.consensus_score != null ? reading.consensus_score : composite;
        var signal = reading.signal_direction || 'HOLD';
        var meets = reading.meets_threshold;
        var biasLabel = reading.matrix_bias_label || 'Neutral';

        var signalClass = signal === 'BUY' ? 'signal--buy' : signal === 'SELL' ? 'signal--sell' : 'signal--hold';
        var compositeClass = composite > 0.2 ? 'comp--bull' : composite < -0.2 ? 'comp--bear' : 'comp--neutral';
        var self = this;

        // Banner
        var html = '<div class="sentiment-panel">' +
            '<div class="sentiment-banner ' + compositeClass + '">' +
                '<div class="sentiment-banner__scores">' +
                    '<div class="sentiment-banner__composite">' +
                        '<span class="sentiment-banner__label">COMPOSITE</span>' +
                        '<span class="sentiment-banner__value">' + (composite >= 0 ? '+' : '') + composite.toFixed(3) + '</span>' +
                    '</div>' +
                    '<div class="sentiment-banner__consensus">' +
                        '<span class="sentiment-banner__label">CONSENSUS</span>' +
                        '<span class="sentiment-banner__value">' + (consensus >= 0 ? '+' : '') + consensus.toFixed(3) + '</span>' +
                    '</div>' +
                    '<div class="sentiment-banner__signal ' + signalClass + '">' +
                        '<span class="sentiment-banner__label">SIGNAL</span>' +
                        '<span class="sentiment-banner__value">' + signal + ' ' + (meets ? '✓' : '·') + '</span>' +
                    '</div>' +
                '</div>' +
                '<div class="sentiment-banner__bias">' + biasLabel + '</div>' +
            '</div>';

        // Score Grid — 3 top + 2 bottom
        html += '<div class="sentiment-score-grid">';
        this.categories.forEach(function(cat) {
            var score = parseFloat(reading[cat.dbKey] || 0);
            var scoreClass = score > 0.2 ? 'score--bull' : score < -0.2 ? 'score--bear' : 'score--neutral';
            var weight = 0;
            try {
                var ws = JSON.parse(reading.weights_snapshot || '{}');
                weight = (ws.sentiment_weights && ws.sentiment_weights[cat.key]) || 0;
            } catch (e) {}
            var contribution = score * weight;

            html += '<div class="sentiment-score-card ' + scoreClass + '">' +
                '<div class="score-card__header">' +
                    '<span class="score-card__icon">' + cat.icon + '</span>' +
                    '<span class="score-card__label">' + cat.abbr + '</span>' +
                    '<span class="score-card__weight">' + (weight * 100).toFixed(0) + '%</span>' +
                '</div>' +
                '<div class="score-card__value">' + (score >= 0 ? '+' : '') + score.toFixed(2) + '</div>' +
                '<div class="score-card__contrib">' + (contribution >= 0 ? '+' : '') + contribution.toFixed(3) + '</div>' +
            '</div>';
        });
        html += '</div>';

        // Footer
        var time = reading.timestamp ? new Date(reading.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) : '--:--';
        var procTime = reading.processing_time_ms ? reading.processing_time_ms + 'ms' : '';
        var sourceType = reading.source_type || '';
        var sourceLabel = (sourceType && sourceType !== 'API') ? '<span class="sentiment-footer__mock">' + sourceType + '</span>' : '';
        var model = reading.source_model ? reading.source_model.split('-').pop() : '';

        html += '<div class="sentiment-footer">' +
            '<span class="sentiment-footer__time">' + tf.toUpperCase() + ' · ' + time + '</span>' +
            sourceLabel +
            (model ? '<span class="sentiment-footer__model">' + model + '</span>' : '') +
            (procTime ? '<span class="sentiment-footer__proc">' + procTime + '</span>' : '') +
        '</div>';

        html += '</div>';
        el.innerHTML = html;
    },

    // ═══════════════════════════════════════════════════════════════════════
    // AGENT DEBATE PANEL (Phase 2) — Seed 22
    // ═══════════════════════════════════════════════════════════════════════

    _renderDebatePanel: function(tf, reading) {
        var container = document.getElementById('matrix-' + tf);
        if (!container) return;
        var el = container.querySelector('.sentiment-overlay--debate');
        if (!el) return;

        // Parse deliberation JSON
        var delib = null;
        try {
            if (reading.agent_deliberation) {
                delib = typeof reading.agent_deliberation === 'string'
                    ? JSON.parse(reading.agent_deliberation)
                    : reading.agent_deliberation;
            }
        } catch (e) { delib = null; }

        if (!delib) {
            el.innerHTML = '<div class="sentiment-panel">' +
                '<div class="debate-empty">' +
                    '<div class="debate-empty__icon">⚔</div>' +
                    '<div class="debate-empty__text">No agent debate data</div>' +
                    '<div class="debate-empty__sub">Enable agents in Profile Manager</div>' +
                '</div>' +
            '</div>';
            return;
        }

        var mode = delib.mode || '?';
        var agents = delib.active_agents || [];
        var timing = delib.timing || {};

        var html = '<div class="sentiment-panel">';

        // ── Header badge row ──
        html += '<div class="debate-header">';
        html += '<span class="debate-badge debate-badge--mode">' + mode.toUpperCase() + '</span>';
        html += '<span class="debate-badge debate-badge--agents">' + agents.length + ' agents</span>';
        if (timing.total_seconds) {
            html += '<span class="debate-badge debate-badge--time">' + timing.total_seconds.toFixed(1) + 's</span>';
        }
        html += '</div>';

        // ── Bull vs Bear ──
        var bull = delib.bull_result || {};
        var bear = delib.bear_result || {};

        html += '<div class="debate-versus">';

        // Bull side
        html += '<div class="debate-side debate-side--bull">';
        html += '<div class="debate-side__title">▲ BULL</div>';
        html += '<div class="debate-side__conf">' + (bull.confidence || '—') + '</div>';
        if (bull.strongest_vector) {
            html += '<div class="debate-side__detail">strongest: ' + bull.strongest_vector + '</div>';
        }
        var bullFlags = bull.flags || [];
        if (bullFlags.length > 0) {
            html += '<div class="debate-side__flags">' + bullFlags.slice(0, 2).join(', ') + '</div>';
        }
        html += '</div>';

        // Bear side
        html += '<div class="debate-side debate-side--bear">';
        html += '<div class="debate-side__title">▼ BEAR</div>';
        html += '<div class="debate-side__conf">' + (bear.confidence || '—') + '</div>';
        if (bear.weakest_vector) {
            html += '<div class="debate-side__detail">weakest: ' + bear.weakest_vector + '</div>';
        }
        var bearFlags = bear.flags || [];
        if (bearFlags.length > 0) {
            html += '<div class="debate-side__flags">' + bearFlags.slice(0, 2).join(', ') + '</div>';
        }
        html += '</div>';

        html += '</div>'; // end versus

        // ── Risk Gate ──
        var risk = delib.risk_result || {};
        if (risk.overall_risk_level) {
            var rl = risk.overall_risk_level;
            var riskCls = rl === 'low' ? 'risk--low' : rl === 'high' ? 'risk--high' : 'risk--med';
            html += '<div class="debate-risk ' + riskCls + '">';
            html += '<span class="debate-risk__label">⊚ RISK GATE</span>';
            html += '<span class="debate-risk__level">' + rl.toUpperCase() + '</span>';
            if (risk.veto) {
                html += '<span class="debate-risk__veto">VETO</span>';
            }
            // Multipliers
            var mults = risk.multipliers || {};
            var multKeys = Object.keys(mults);
            if (multKeys.length > 0) {
                html += '<div class="debate-risk__mults">';
                multKeys.forEach(function(k) {
                    var v = mults[k];
                    var mc = v >= 0.8 ? 'mult--ok' : v >= 0.5 ? 'mult--warn' : 'mult--bad';
                    html += '<span class="debate-mult ' + mc + '">' +
                        k.replace('_score', '').substring(0, 4) + ' ×' +
                        (typeof v === 'number' ? v.toFixed(2) : v) + '</span>';
                });
                html += '</div>';
            }
            html += '</div>';
        }

        // ── Final Adjustments ──
        var adj = delib.final_adjustments || {};
        var adjKeys = Object.keys(adj);
        if (adjKeys.length > 0) {
            html += '<div class="debate-adjustments">';
            html += '<div class="debate-adjustments__title">ADJUSTMENTS</div>';
            html += '<div class="debate-adjustments__row">';
            adjKeys.forEach(function(k) {
                var v = adj[k];
                var cls = v > 0.03 ? 'adj--pos' : v < -0.03 ? 'adj--neg' : 'adj--flat';
                html += '<span class="debate-adj ' + cls + '">' +
                    k.replace('_score', '').substring(0, 3).toUpperCase() + ' ' +
                    (v > 0 ? '+' : '') + (typeof v === 'number' ? v.toFixed(3) : v) + '</span>';
            });
            html += '</div></div>';
        }

        // ── Timing breakdown ──
        if (timing.phase1_analysts || timing.phase2_debate || timing.phase3_risk) {
            html += '<div class="debate-timing">';
            if (timing.phase1_analysts) html += '<span>analysts ' + timing.phase1_analysts.toFixed(1) + 's</span>';
            if (timing.phase2_debate) html += '<span>debate ' + timing.phase2_debate.toFixed(1) + 's</span>';
            if (timing.phase3_risk) html += '<span>risk ' + timing.phase3_risk.toFixed(1) + 's</span>';
            html += '</div>';
        }

        html += '</div>';
        el.innerHTML = html;
    },

    // ═══════════════════════════════════════════════════════════════════════
    // MANUAL TRIGGER (for testing from console)
    // ═══════════════════════════════════════════════════════════════════════

    triggerManual: function(instanceId, symbol) {
        this.currentInstanceId = instanceId || this._resolveInstanceId();
        this.currentSymbol = symbol || this.currentSymbol;
        this.isRunning = true;
        this.fetchLatest();
    }
};

document.addEventListener('DOMContentLoaded', function() {
    ApexSentiment.init();
});

window.ApexSentiment = ApexSentiment;
