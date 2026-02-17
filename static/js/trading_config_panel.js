/* ═══════════════════════════════════════════════════════════════════════════
   TRADING CONFIG PANEL — Structured config editor for Torra Trader profiles
   
   Renders inside the Profile Manager form (right quadrant only).
   
   Usage:
     TradingConfigPanel.render('containerId', configObj)  → mount into DOM
     TradingConfigPanel.getConfig()                     → read current values
     TradingConfigPanel.setConfig(configObj)             → update panel
   ═══════════════════════════════════════════════════════════════════════════ */

const TradingConfigPanel = {

    _config: null,
    _container: null,

    // ═══════════════════════════════════════════════════════════════════
    // SECTION DEFINITIONS
    // ═══════════════════════════════════════════════════════════════════

    SECTIONS: [
        {
            id: 'sentiment_weights',
            title: 'Sentiment Weights',
            icon: '◎',
            type: 'weights',          // auto-normalizing sliders
            path: 'sentiment_weights',
            fields: [
                { key: 'price_action', label: 'Price Action', color: '#4ADEAA' },
                { key: 'key_levels',   label: 'Key Levels',   color: '#5BC0DE' },
                { key: 'momentum',     label: 'Momentum',     color: '#7EE8C7' },
                { key: 'ath',          label: 'ATH Distance', color: '#3B9B7A' },
                { key: 'structure',    label: 'Structure',    color: '#A78BFA' },
            ]
        },
        {
            id: 'timeframe_weights',
            title: 'Timeframe Weights',
            icon: '⏱',
            type: 'weights',
            path: 'timeframe_weights',
            fields: [
                { key: '15m', label: '15 Minute', color: '#4ADEAA' },
                { key: '1h',  label: '1 Hour',    color: '#5BC0DE' },
            ]
        },
        {
            id: 'thresholds',
            title: 'Entry Thresholds',
            icon: '⊘',
            type: 'thresholds',
            path: 'thresholds',
            fields: [
                { key: 'buy',       label: 'Buy Signal',   min: 0,    max: 1.0,  step: 0.05, unit: '' },
                { key: 'sell',      label: 'Sell Signal',   min: -1.0, max: 0,    step: 0.05, unit: '' },
                { key: 'dead_zone', label: 'Dead Zone',     min: 0,    max: 0.5,  step: 0.05, unit: '' },
                { key: 'gut_veto',  label: 'Gut Veto',      min: 0,    max: 1.0,  step: 0.05, unit: '' },
            ]
        },
        {
            id: 'risk',
            title: 'Risk & Exit Strategy',
            icon: '⛊',
            type: 'mixed',
            path: 'risk',
            fields: [
                { key: 'base_lots',             label: 'Base Lots',           type: 'stepper', min: 0.01, max: 100,  step: 0.01, unit: 'lots' },
                { key: 'max_lots',              label: 'Max Lots',            type: 'stepper', min: 0.01, max: 100,  step: 0.01, unit: 'lots' },
                { key: 'stop_loss_points',      label: 'Stop Loss',           type: 'stepper', min: 1,    max: 5000, step: 5,    unit: 'pts' },
                { key: 'take_profit_points',    label: 'Take Profit',         type: 'stepper', min: 1,    max: 5000, step: 5,    unit: 'pts' },
                { key: 'max_signals_per_hour',  label: 'Max Signals / Hour',  type: 'stepper', min: 1,    max: 60,   step: 1,    unit: '/hr' },
                { key: 'cooldown_seconds',      label: 'Cooldown',            type: 'stepper', min: 0,    max: 3600, step: 30,   unit: 'sec', wide: true },
                { key: 'consecutive_loss_halt', label: 'Loss Halt After',     type: 'stepper', min: 1,    max: 20,   step: 1,    unit: 'losses' },
                { key: 'sentiment_exit',        label: 'Sentiment Exit',      type: 'toggle' },
            ]
        },
        {
            id: 'agents',
            title: 'Agent Framework',
            icon: '⚔',
            type: 'agents',
            path: 'agents',
            fields: [
                { key: 'enabled',                   label: 'Enable Agents',       type: 'toggle' },
                { key: 'mode',                      label: 'Mode',                type: 'select', options: [
                    { value: 'budget',   label: 'Budget \u2014 4 agents' },
                    { value: 'standard', label: 'Standard \u2014 6 agents' },
                    { value: 'full',     label: 'Full \u2014 8 agents' },
                ]},
                { key: 'debate_rounds',             label: 'Debate Rounds',       type: 'stepper', min: 1,    max: 3,     step: 1,    unit: '' },
                { key: 'timeout_seconds',           label: 'Tick Timeout',        type: 'stepper', min: 5,    max: 60,    step: 1,    unit: 'sec' },
                { key: 'max_api_cost_per_hour',     label: 'Max Cost / Hour',     type: 'stepper', min: 0.50, max: 20.00, step: 0.50, unit: 'usd' },
                { key: 'max_researcher_shift',      label: 'Researcher Shift',    type: 'stepper', min: 0.05, max: 0.30,  step: 0.01, unit: '\u00b1' },
                { key: 'max_total_adjustment',      label: 'Max Adjustment',      type: 'stepper', min: 0.10, max: 0.50,  step: 0.01, unit: '\u00b1' },
                { key: 'include_markov_context',    label: 'Markov Memory',       type: 'toggle' },
                { key: 'include_sentiment_history', label: 'Sentiment History',   type: 'toggle' },
                { key: 'history_lookback',          label: 'History Lookback',    type: 'stepper', min: 3,    max: 50,    step: 1,    unit: 'ticks' },
                { key: '_screenshot_divider',        label: 'Screenshot Region',   type: 'divider' },
                { key: 'screenshot_x',               label: 'X (left)',            type: 'stepper', min: 0,    max: 3840,  step: 10,   unit: 'px' },
                { key: 'screenshot_y',               label: 'Y (top)',             type: 'stepper', min: 0,    max: 2160,  step: 10,   unit: 'px' },
                { key: 'screenshot_w',               label: 'Width',               type: 'stepper', min: 200,  max: 3840,  step: 10,   unit: 'px' },
                { key: 'screenshot_h',               label: 'Height',              type: 'stepper', min: 200,  max: 2160,  step: 10,   unit: 'px' },
            ]
        },
    ],

    // ═══════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════

    render(containerId, config) {
        const el = document.getElementById(containerId);
        if (!el) return;
        this._container = el;
        this._config = this._deepClone(config || this._getDefault());
        el.innerHTML = this._buildHTML();
        this._bindEvents();
        this._updateAllVisuals();
    },

    getConfig() {
        if (!this._config) return this._getDefault();
        return this._deepClone(this._config);
    },

    setConfig(config) {
        this._config = this._deepClone(config);
        if (this._container) {
            this._syncInputsFromConfig();
            this._updateAllVisuals();
        }
    },

    // ═══════════════════════════════════════════════════════════════════
    // HTML GENERATION
    // ═══════════════════════════════════════════════════════════════════

    _buildHTML() {
        return '<div class="tcp">' +
            '<div class="tcp-status-bar">' +
                '<span class="tcp-status-bar__label">Trading Configuration</span>' +
                '<span class="tcp-save-badge" id="tcp-save-badge">Saved \u2713</span>' +
            '</div>' +
            this.SECTIONS.map(s => this._buildSection(s)).join('') +
        '</div>';
    },

    _buildSection(section) {
        let bodyContent = '';

        if (section.type === 'weights') {
            bodyContent = this._buildWeightsSection(section);
        } else if (section.type === 'thresholds') {
            bodyContent = this._buildThresholdsSection(section);
        } else if (section.type === 'mixed') {
            bodyContent = this._buildMixedSection(section);
        } else if (section.type === 'agents') {
            bodyContent = this._buildAgentsSection(section);
        }

        return '<div class="tcp-section" id="tcp-' + section.id + '" data-section="' + section.id + '">' +
            '<div class="tcp-section__header" onclick="TradingConfigPanel._toggleSection(\'' + section.id + '\')">' +
                '<div class="tcp-section__title">' +
                    '<span class="tcp-section__icon">' + section.icon + '</span> ' +
                    section.title +
                '</div>' +
                '<span class="tcp-section__chevron">\u25bc</span>' +
            '</div>' +
            '<div class="tcp-section__body">' +
                bodyContent +
            '</div>' +
        '</div>';
    },

    // ── Weights Section (auto-normalizing sliders) ──────────────────

    _buildWeightsSection(section) {
        const values = this._config[section.path] || {};
        const fields = section.fields;

        // Distribution bar
        const barSegments = fields.map(function(f) {
            const val = values[f.key] || 0;
            return '<div class="tcp-weight-bar__segment tcp-weight-bar__segment--' + f.key + '" ' +
                'data-bar-key="' + f.key + '" data-bar-section="' + section.path + '" ' +
                'style="width: ' + (val * 100) + '%; background: ' + f.color + ';" ' +
                'title="' + f.label + ': ' + (val * 100).toFixed(0) + '%"></div>';
        }).join('');

        // Slider rows
        const rows = fields.map(function(f) {
            const val = values[f.key] || 0;
            return '<div class="tcp-row">' +
                '<div class="tcp-row__label">' +
                    '<span class="tcp-row__dot" style="background: ' + f.color + ';"></span> ' +
                    f.label +
                '</div>' +
                '<div class="tcp-slider-wrap">' +
                    '<input type="range" class="tcp-slider" ' +
                        'id="tcp-w-' + section.path + '-' + f.key + '" ' +
                        'data-section="' + section.path + '" data-key="' + f.key + '" ' +
                        'min="0" max="100" step="1" value="' + Math.round(val * 100) + '" ' +
                        'oninput="TradingConfigPanel._onWeightSlider(this)" ' +
                        'onclick="event.stopPropagation()" />' +
                    '<span class="tcp-slider__value" id="tcp-wv-' + section.path + '-' + f.key + '">' + (val * 100).toFixed(0) + '%</span>' +
                '</div>' +
            '</div>';
        }).join('');

        const total = fields.reduce(function(s, f) { return s + (values[f.key] || 0); }, 0);
        const isOk = Math.abs(total - 1.0) < 0.01;

        return '<div class="tcp-weight-bar" id="tcp-bar-' + section.path + '">' + barSegments + '</div>' +
            rows +
            '<div class="tcp-total-row">' +
                '<span class="tcp-total-row__label">Total</span>' +
                '<span class="tcp-total-row__value ' + (isOk ? 'tcp-total-row__value--ok' : 'tcp-total-row__value--warn') + '" ' +
                    'id="tcp-total-' + section.path + '">' + (total * 100).toFixed(0) + '%</span>' +
            '</div>';
    },

    // ── Thresholds Section ──────────────────────────────────────────

    _buildThresholdsSection(section) {
        const values = this._config[section.path] || {};

        const buy  = values.buy || 0.55;
        const sell = Math.abs(values.sell || -0.55);
        const dz   = values.dead_zone || 0.25;

        const bar = '<div class="tcp-threshold-bar" id="tcp-thresh-bar">' +
            '<div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--sell" style="width: ' + (sell * 50) + '%;"></div>' +
            '<div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--dead" style="left: ' + (50 - dz * 50) + '%; width: ' + (dz * 100) + '%;"></div>' +
            '<div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--buy" style="width: ' + (buy * 50) + '%;"></div>' +
            '<span class="tcp-threshold-bar__label tcp-threshold-bar__label--sell">SELL</span>' +
            '<span class="tcp-threshold-bar__label tcp-threshold-bar__label--dead">DEAD ZONE</span>' +
            '<span class="tcp-threshold-bar__label tcp-threshold-bar__label--buy">BUY</span>' +
        '</div>';

        var self = this;
        const rows = section.fields.map(function(f) {
            const val = values[f.key] || 0;
            return '<div class="tcp-row">' +
                '<div class="tcp-row__label">' + f.label + '</div>' +
                '<div class="tcp-row__control">' +
                    self._buildStepper('tcp-t-' + f.key, val, f.min, f.max, f.step, f.unit, false, section.path, f.key) +
                '</div>' +
            '</div>';
        }).join('');

        return bar + rows;
    },

    // ── Mixed Section (steppers + toggles) ──────────────────────────

    _buildMixedSection(section) {
        const values = this._config[section.path] || {};
        var self = this;

        return section.fields.map(function(f) {
            const val = values[f.key];

            if (f.type === 'toggle') {
                return '<div class="tcp-row">' +
                    '<div class="tcp-row__label">' + f.label + '</div>' +
                    '<div class="tcp-row__control">' +
                        self._buildToggle('tcp-r-' + f.key, val, section.path, f.key) +
                    '</div>' +
                '</div>';
            }

            return '<div class="tcp-row">' +
                '<div class="tcp-row__label">' + f.label + '</div>' +
                '<div class="tcp-row__control">' +
                    self._buildStepper('tcp-r-' + f.key, val, f.min, f.max, f.step, f.unit, f.wide, section.path, f.key) +
                '</div>' +
            '</div>';
        }).join('');
    },

    // ── Agents Section (Seed 22) ────────────────────────────────────

    _buildAgentsSection(section) {
        const values = this._config[section.path] || {};
        var self = this;

        // Mode descriptions for the info line
        const modeInfo = {
            budget:   'Technical + Bull/Bear + Risk Gate',
            standard: 'Tech + KeyLevels + Momentum + Bull/Bear + Risk',
            full:     'All 5 analysts + Bull/Bear + Risk Gate'
        };

        return section.fields.map(function(f) {
            const val = (values[f.key] !== undefined) ? values[f.key] : self._getAgentDefault(f.key);

            if (f.type === 'toggle') {
                return '<div class="tcp-row">' +
                    '<div class="tcp-row__label">' + f.label + '</div>' +
                    '<div class="tcp-row__control">' +
                        self._buildToggle('tcp-a-' + f.key, val, section.path, f.key) +
                    '</div>' +
                '</div>';
            }

            if (f.type === 'select') {
                var optionsHtml = f.options.map(function(opt) {
                    var selected = (val === opt.value) ? ' selected' : '';
                    return '<option value="' + opt.value + '"' + selected + '>' + opt.label + '</option>';
                }).join('');

                var currentMode = val || 'budget';
                var infoText = modeInfo[currentMode] || '';

                return '<div class="tcp-row">' +
                    '<div class="tcp-row__label">' + f.label + '</div>' +
                    '<div class="tcp-row__control">' +
                        '<select class="tcp-select" id="tcp-a-' + f.key + '" ' +
                            'data-section="' + section.path + '" data-key="' + f.key + '" ' +
                            'onclick="event.stopPropagation()" ' +
                            'onchange="TradingConfigPanel._onSelectChange(this)">' +
                            optionsHtml +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="tcp-row tcp-row--info" id="tcp-agent-mode-info">' +
                    '<div class="tcp-row__label tcp-row__label--sub">' + infoText + '</div>' +
                '</div>';
            }

            if (f.type === 'divider') {
                return '<div class="tcp-divider"><span class="tcp-divider__label">' + f.label + '</span></div>';
            }

            if (f.type === 'stepper') {
                return '<div class="tcp-row">' +
                    '<div class="tcp-row__label">' + f.label + '</div>' +
                    '<div class="tcp-row__control">' +
                        self._buildStepper('tcp-a-' + f.key, val, f.min, f.max, f.step, f.unit, f.wide, section.path, f.key) +
                    '</div>' +
                '</div>';
            }

            return '';
        }).join('');
    },

    _getAgentDefault(key) {
        var defaults = {
            enabled: true,
            mode: 'budget',
            debate_rounds: 1,
            timeout_seconds: 15,
            max_api_cost_per_hour: 2.00,
            max_researcher_shift: 0.15,
            max_total_adjustment: 0.30,
            include_markov_context: true,
            include_sentiment_history: true,
            history_lookback: 10,
            screenshot_x: 0,
            screenshot_y: 0,
            screenshot_w: 0,
            screenshot_h: 0
        };
        return defaults[key];
    },

    // ── Stepper Builder ─────────────────────────────────────────────

    _buildStepper(id, value, min, max, step, unit, wide, sectionPath, key) {
        var displayVal = (typeof value === 'number') ? value : 0;
        return '<div class="tcp-stepper' + (wide ? ' tcp-stepper--wide' : '') + '">' +
            '<button type="button" class="tcp-stepper__btn" ' +
                'onclick="event.stopPropagation(); TradingConfigPanel._stepValue(\'' + id + '\', ' + (-step) + ', ' + min + ', ' + max + ', \'' + sectionPath + '\', \'' + key + '\')">&#8722;</button>' +
            '<input type="number" class="tcp-stepper__input" id="' + id + '" ' +
                'value="' + displayVal + '" min="' + min + '" max="' + max + '" step="' + step + '" ' +
                'data-section="' + sectionPath + '" data-key="' + key + '" ' +
                'onclick="event.stopPropagation()" ' +
                'onkeydown="event.stopPropagation()" ' +
                'onchange="TradingConfigPanel._onStepperChange(this)" />' +
            '<button type="button" class="tcp-stepper__btn" ' +
                'onclick="event.stopPropagation(); TradingConfigPanel._stepValue(\'' + id + '\', ' + step + ', ' + min + ', ' + max + ', \'' + sectionPath + '\', \'' + key + '\')">+</button>' +
            (unit ? '<span class="tcp-stepper__unit">' + unit + '</span>' : '') +
        '</div>';
    },

    // ── Toggle Builder ──────────────────────────────────────────────

    _buildToggle(id, value, sectionPath, key) {
        return '<label class="tcp-toggle" onclick="event.stopPropagation()">' +
            '<input type="checkbox" id="' + id + '" ' + (value ? 'checked' : '') + ' ' +
                'data-section="' + sectionPath + '" data-key="' + key + '" ' +
                'onchange="TradingConfigPanel._onToggleChange(this)" />' +
            '<div class="tcp-toggle__track"></div>' +
            '<div class="tcp-toggle__thumb"></div>' +
        '</label>';
    },

    // ═══════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════

    _toggleSection(sectionId) {
        var el = document.getElementById('tcp-' + sectionId);
        if (el) el.classList.toggle('tcp-section--collapsed');
    },

    /** Weight slider changed — auto-normalize to 1.0 */
    _onWeightSlider(input) {
        var section = input.dataset.section;
        var key     = input.dataset.key;
        var rawVal  = parseInt(input.value) / 100;

        var sectionDef = this.SECTIONS.find(function(s) { return s.path === section; });
        if (!sectionDef) return;

        var fields = sectionDef.fields;
        var otherFields = fields.filter(function(f) { return f.key !== key; });

        var othersSum = 0;
        var self = this;
        otherFields.forEach(function(f) {
            othersSum += (self._config[section] && self._config[section][f.key]) || 0;
        });

        var newVal = Math.max(0, Math.min(1, rawVal));
        if (!this._config[section]) this._config[section] = {};
        this._config[section][key] = newVal;

        var remaining = 1.0 - newVal;
        if (othersSum > 0) {
            var scale = remaining / othersSum;
            otherFields.forEach(function(f) {
                self._config[section][f.key] = Math.max(0, (self._config[section][f.key] || 0) * scale);
            });
        } else if (otherFields.length > 0) {
            var each = remaining / otherFields.length;
            otherFields.forEach(function(f) {
                self._config[section][f.key] = each;
            });
        }

        var sum = 0;
        fields.forEach(function(f) {
            self._config[section][f.key] = Math.round(self._config[section][f.key] * 100) / 100;
            sum += self._config[section][f.key];
        });
        if (Math.abs(sum - 1.0) > 0.001) {
            var lastField = fields[fields.length - 1];
            self._config[section][lastField.key] += (1.0 - sum);
            self._config[section][lastField.key] = Math.round(self._config[section][lastField.key] * 100) / 100;
        }

        fields.forEach(function(f) {
            var slider = document.getElementById('tcp-w-' + section + '-' + f.key);
            var label  = document.getElementById('tcp-wv-' + section + '-' + f.key);
            var val = self._config[section][f.key] || 0;
            if (slider && f.key !== key) slider.value = Math.round(val * 100);
            if (label) label.textContent = (val * 100).toFixed(0) + '%';
        });

        this._updateWeightBar(section);
        this._updateWeightTotal(section);
        this._emitChange();
    },

    /** Stepper button click */
    _stepValue(id, delta, min, max, sectionPath, key) {
        var input = document.getElementById(id);
        if (!input) return;
        var val = parseFloat(input.value) || 0;
        val = Math.round((val + delta) * 1000) / 1000;
        val = Math.max(min, Math.min(max, val));
        input.value = val;
        this._writeToConfig(sectionPath, key, val);
        this._updateThresholdBar();
        this._emitChange();
    },

    /** Stepper manual input */
    _onStepperChange(input) {
        var section = input.dataset.section;
        var key     = input.dataset.key;
        var val = parseFloat(input.value) || 0;
        var min = parseFloat(input.min);
        var max = parseFloat(input.max);
        val = Math.max(min, Math.min(max, val));
        input.value = val;
        this._writeToConfig(section, key, val);
        this._updateThresholdBar();
        this._emitChange();
    },

    /** Toggle change */
    _onToggleChange(input) {
        var section = input.dataset.section;
        var key     = input.dataset.key;
        this._writeToConfig(section, key, input.checked);
        this._emitChange();
    },

    /** Select dropdown change (Seed 22: Agent mode) */
    _onSelectChange(select) {
        var section = select.dataset.section;
        var key     = select.dataset.key;
        this._writeToConfig(section, key, select.value);

        // Update mode info line
        if (key === 'mode') {
            var modeInfo = {
                budget:   'Technical + Bull/Bear + Risk Gate',
                standard: 'Tech + KeyLevels + Momentum + Bull/Bear + Risk',
                full:     'All 5 analysts + Bull/Bear + Risk Gate'
            };
            var infoEl = document.getElementById('tcp-agent-mode-info');
            if (infoEl) {
                var label = infoEl.querySelector('.tcp-row__label--sub');
                if (label) label.textContent = modeInfo[select.value] || '';
            }
        }

        this._emitChange();
    },

    // ═══════════════════════════════════════════════════════════════════
    // CONFIG MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════

    _writeToConfig(sectionPath, key, value) {
        if (!this._config[sectionPath]) this._config[sectionPath] = {};
        this._config[sectionPath][key] = value;
    },

    _emitChange() {
        window.dispatchEvent(new CustomEvent('tcp:change', {
            detail: { config: this.getConfig() }
        }));
    },

    _getDefault() {
        if (typeof TorraTraderBridge !== 'undefined') {
            return TorraTraderBridge.DEFAULT_TRADING_CONFIG;
        }
        return {
            sentiment_weights: { price_action: 0.30, key_levels: 0.15, momentum: 0.25, volume: 0.10, structure: 0.20 },
            timeframe_weights: { "15m": 0.40, "1h": 0.60 },
            thresholds: { buy: 0.55, sell: -0.55, dead_zone: 0.25, gut_veto: 0.30 },
            risk: { base_lots: 1.0, max_lots: 1.0, stop_loss_points: 80, take_profit_points: 200,
                    max_signals_per_hour: 3, cooldown_seconds: 300, consecutive_loss_halt: 2, sentiment_exit: true },
            agents: {
                enabled: true, mode: 'budget', debate_rounds: 1, timeout_seconds: 15,
                max_api_cost_per_hour: 2.00, max_researcher_shift: 0.15, max_total_adjustment: 0.30,
                include_markov_context: true, include_sentiment_history: true, history_lookback: 10,
                screenshot_x: 0, screenshot_y: 0, screenshot_w: 0, screenshot_h: 0
            }
        };
    },

    // ═══════════════════════════════════════════════════════════════════
    // VISUAL UPDATES
    // ═══════════════════════════════════════════════════════════════════

    _updateAllVisuals() {
        var self = this;
        this.SECTIONS.forEach(function(s) {
            if (s.type === 'weights') {
                self._updateWeightBar(s.path);
                self._updateWeightTotal(s.path);
            }
        });
        this._updateThresholdBar();
    },

    _updateWeightBar(sectionPath) {
        var barEl = document.getElementById('tcp-bar-' + sectionPath);
        if (!barEl) return;
        var section = this.SECTIONS.find(function(s) { return s.path === sectionPath; });
        if (!section) return;
        var self = this;

        section.fields.forEach(function(f) {
            var seg = barEl.querySelector('[data-bar-key="' + f.key + '"]');
            if (seg) {
                var val = (self._config[sectionPath] && self._config[sectionPath][f.key]) || 0;
                seg.style.width = (val * 100) + '%';
                seg.title = f.label + ': ' + (val * 100).toFixed(0) + '%';
            }
        });
    },

    _updateWeightTotal(sectionPath) {
        var section = this.SECTIONS.find(function(s) { return s.path === sectionPath; });
        if (!section) return;
        var totalEl = document.getElementById('tcp-total-' + sectionPath);
        if (!totalEl) return;
        var self = this;

        var sum = section.fields.reduce(function(s, f) {
            return s + ((self._config[sectionPath] && self._config[sectionPath][f.key]) || 0);
        }, 0);
        var isOk = Math.abs(sum - 1.0) < 0.02;
        totalEl.textContent = (sum * 100).toFixed(0) + '%';
        totalEl.className = 'tcp-total-row__value ' + (isOk ? 'tcp-total-row__value--ok' : 'tcp-total-row__value--warn');
    },

    _updateThresholdBar() {
        var bar = document.getElementById('tcp-thresh-bar');
        if (!bar) return;

        var th = this._config.thresholds || {};
        var buy  = th.buy || 0.55;
        var sell = Math.abs(th.sell || -0.55);
        var dz   = th.dead_zone || 0.25;

        var sellZone = bar.querySelector('.tcp-threshold-bar__zone--sell');
        var deadZone = bar.querySelector('.tcp-threshold-bar__zone--dead');
        var buyZone  = bar.querySelector('.tcp-threshold-bar__zone--buy');

        if (sellZone) sellZone.style.width = (sell * 50) + '%';
        if (deadZone) {
            deadZone.style.left  = (50 - dz * 50) + '%';
            deadZone.style.width = (dz * 100) + '%';
        }
        if (buyZone) buyZone.style.width = (buy * 50) + '%';
    },

    _syncInputsFromConfig() {
        var self = this;
        this.SECTIONS.forEach(function(section) {
            var vals = self._config[section.path] || {};
            section.fields.forEach(function(f) {
                if (section.type === 'weights') {
                    var slider = document.getElementById('tcp-w-' + section.path + '-' + f.key);
                    var label  = document.getElementById('tcp-wv-' + section.path + '-' + f.key);
                    var val = vals[f.key] || 0;
                    if (slider) slider.value = Math.round(val * 100);
                    if (label) label.textContent = (val * 100).toFixed(0) + '%';
                } else if (f.type === 'toggle') {
                    // Check all prefixes (tcp-r for risk, tcp-a for agents)
                    var toggle = document.getElementById('tcp-r-' + f.key) ||
                                 document.getElementById('tcp-a-' + f.key);
                    if (toggle) toggle.checked = !!vals[f.key];
                } else if (f.type === 'select') {
                    var select = document.getElementById('tcp-a-' + f.key);
                    if (select) select.value = vals[f.key] || '';
                } else {
                    var idPrefix = section.type === 'thresholds' ? 'tcp-t' : 
                                   section.type === 'agents' ? 'tcp-a' : 'tcp-r';
                    var input = document.getElementById(idPrefix + '-' + f.key);
                    if (input) input.value = vals[f.key] || 0;
                }
            });
        });
    },

    // ═══════════════════════════════════════════════════════════════════
    // BIND EVENTS
    // ═══════════════════════════════════════════════════════════════════

    _bindEvents() {
        if (this._container) {
            this._container.addEventListener('click', function(e) { e.stopPropagation(); });
        }
    },

    // ═══════════════════════════════════════════════════════════════════
    // UTILS
    // ═══════════════════════════════════════════════════════════════════

    _deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }
};

// Expose
window.TradingConfigPanel = TradingConfigPanel;
