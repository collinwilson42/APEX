/* ═══════════════════════════════════════════════════════════════════════════
   TRADING CONFIG PANEL — TradingView-Style Neomorphic Input Panel
   
   Renders structured inputs for the trading_config JSON blob:
   - Sentiment Weights (auto-normalizing sliders + distribution bar)
   - Timeframe Weights (dual slider + bar)
   - Entry Thresholds (steppers + visual zone bar)
   - Risk & Exit Strategy (steppers + toggles)
   
   API:
     TradingConfigPanel.render(containerId, configObj)  → draw panel
     TradingConfigPanel.getConfig()                     → read current values
     TradingConfigPanel.setConfig(configObj)             → update panel
   
   Emits 'tcp:change' CustomEvent on every input change.
   ═══════════════════════════════════════════════════════════════════════════ */

const TradingConfigPanel = {

    _container: null,
    _config: null,

    // ═══════════════════════════════════════════════════════════════════
    // SCHEMA — drives the UI generation
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
                { key: 'volume',       label: 'Volume',       color: '#3B9B7A' },
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
    ],

    // ═══════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Render the config panel into a container element.
     * @param {string} containerId  DOM id to render into
     * @param {object} config       trading_config JSON object
     */
    render(containerId, config) {
        const el = document.getElementById(containerId);
        if (!el) return;
        this._container = el;
        this._config = this._deepClone(config || this._getDefault());
        el.innerHTML = this._buildHTML();
        this._bindEvents();
        this._updateAllVisuals();
    },

    /** Read the current config from the panel inputs */
    getConfig() {
        if (!this._config) return this._getDefault();
        return this._deepClone(this._config);
    },

    /** Programmatically update the panel */
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
        return `<div class="tcp">${this.SECTIONS.map(s => this._buildSection(s)).join('')}</div>`;
    },

    _buildSection(section) {
        let bodyContent = '';

        if (section.type === 'weights') {
            bodyContent = this._buildWeightsSection(section);
        } else if (section.type === 'thresholds') {
            bodyContent = this._buildThresholdsSection(section);
        } else if (section.type === 'mixed') {
            bodyContent = this._buildMixedSection(section);
        }

        return `
            <div class="tcp-section" id="tcp-${section.id}" data-section="${section.id}">
                <div class="tcp-section__header" onclick="TradingConfigPanel._toggleSection('${section.id}')">
                    <div class="tcp-section__title">
                        <span class="tcp-section__icon">${section.icon}</span>
                        ${section.title}
                    </div>
                    <span class="tcp-section__chevron">▼</span>
                </div>
                <div class="tcp-section__body">
                    ${bodyContent}
                </div>
            </div>
        `;
    },

    // ── Weights Section (auto-normalizing sliders) ──────────────────

    _buildWeightsSection(section) {
        const values = this._config[section.path] || {};
        const fields = section.fields;

        // Distribution bar
        const barSegments = fields.map(f => {
            const val = values[f.key] || 0;
            return `<div class="tcp-weight-bar__segment tcp-weight-bar__segment--${f.key}" 
                         data-bar-key="${f.key}" data-bar-section="${section.path}"
                         style="width: ${val * 100}%; background: ${f.color};" 
                         title="${f.label}: ${(val * 100).toFixed(0)}%"></div>`;
        }).join('');

        // Slider rows
        const rows = fields.map(f => {
            const val = values[f.key] || 0;
            return `
                <div class="tcp-row">
                    <div class="tcp-row__label">
                        <span class="tcp-row__dot" style="background: ${f.color};"></span>
                        ${f.label}
                    </div>
                    <div class="tcp-slider-wrap">
                        <input type="range" class="tcp-slider" 
                               id="tcp-w-${section.path}-${f.key}"
                               data-section="${section.path}" data-key="${f.key}"
                               min="0" max="100" step="1" value="${Math.round(val * 100)}"
                               oninput="TradingConfigPanel._onWeightSlider(this)"
                               onclick="event.stopPropagation()" />
                        <span class="tcp-slider__value" id="tcp-wv-${section.path}-${f.key}">${(val * 100).toFixed(0)}%</span>
                    </div>
                </div>
            `;
        }).join('');

        // Total row
        const total = fields.reduce((s, f) => s + (values[f.key] || 0), 0);
        const isOk = Math.abs(total - 1.0) < 0.01;

        return `
            <div class="tcp-weight-bar" id="tcp-bar-${section.path}">${barSegments}</div>
            ${rows}
            <div class="tcp-total-row">
                <span class="tcp-total-row__label">Total</span>
                <span class="tcp-total-row__value ${isOk ? 'tcp-total-row__value--ok' : 'tcp-total-row__value--warn'}" 
                      id="tcp-total-${section.path}">${(total * 100).toFixed(0)}%</span>
            </div>
        `;
    },

    // ── Thresholds Section ──────────────────────────────────────────

    _buildThresholdsSection(section) {
        const values = this._config[section.path] || {};

        // Visual threshold bar
        const buy  = values.buy || 0.55;
        const sell = Math.abs(values.sell || -0.55);
        const dz   = values.dead_zone || 0.25;

        const bar = `
            <div class="tcp-threshold-bar" id="tcp-thresh-bar">
                <div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--sell"
                     style="width: ${sell * 50}%;"></div>
                <div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--dead"
                     style="left: ${50 - dz * 50}%; width: ${dz * 100}%;"></div>
                <div class="tcp-threshold-bar__zone tcp-threshold-bar__zone--buy"
                     style="width: ${buy * 50}%;"></div>
                <span class="tcp-threshold-bar__label tcp-threshold-bar__label--sell">SELL</span>
                <span class="tcp-threshold-bar__label tcp-threshold-bar__label--dead">DEAD ZONE</span>
                <span class="tcp-threshold-bar__label tcp-threshold-bar__label--buy">BUY</span>
            </div>
        `;

        const rows = section.fields.map(f => {
            const val = values[f.key] || 0;
            return `
                <div class="tcp-row">
                    <div class="tcp-row__label">${f.label}</div>
                    <div class="tcp-row__control">
                        ${this._buildStepper(`tcp-t-${f.key}`, val, f.min, f.max, f.step, f.unit, false, section.path, f.key)}
                    </div>
                </div>
            `;
        }).join('');

        return bar + rows;
    },

    // ── Mixed Section (steppers + toggles) ──────────────────────────

    _buildMixedSection(section) {
        const values = this._config[section.path] || {};

        return section.fields.map(f => {
            const val = values[f.key];

            if (f.type === 'toggle') {
                return `
                    <div class="tcp-row">
                        <div class="tcp-row__label">${f.label}</div>
                        <div class="tcp-row__control">
                            ${this._buildToggle(`tcp-r-${f.key}`, val, section.path, f.key)}
                        </div>
                    </div>
                `;
            }

            return `
                <div class="tcp-row">
                    <div class="tcp-row__label">${f.label}</div>
                    <div class="tcp-row__control">
                        ${this._buildStepper(`tcp-r-${f.key}`, val, f.min, f.max, f.step, f.unit, f.wide, section.path, f.key)}
                    </div>
                </div>
            `;
        }).join('');
    },

    // ── Stepper Builder ─────────────────────────────────────────────

    _buildStepper(id, value, min, max, step, unit, wide, sectionPath, key) {
        const displayVal = typeof value === 'number' ? value : 0;
        return `
            <div class="tcp-stepper ${wide ? 'tcp-stepper--wide' : ''}">
                <button type="button" class="tcp-stepper__btn" 
                        onclick="event.stopPropagation(); TradingConfigPanel._stepValue('${id}', ${-step}, ${min}, ${max}, '${sectionPath}', '${key}')">−</button>
                <input type="number" class="tcp-stepper__input" id="${id}"
                       value="${displayVal}" min="${min}" max="${max}" step="${step}"
                       data-section="${sectionPath}" data-key="${key}"
                       onclick="event.stopPropagation()"
                       onkeydown="event.stopPropagation()"
                       onchange="TradingConfigPanel._onStepperChange(this)" />
                <button type="button" class="tcp-stepper__btn" 
                        onclick="event.stopPropagation(); TradingConfigPanel._stepValue('${id}', ${step}, ${min}, ${max}, '${sectionPath}', '${key}')">+</button>
                ${unit ? `<span class="tcp-stepper__unit">${unit}</span>` : ''}
            </div>
        `;
    },

    // ── Toggle Builder ──────────────────────────────────────────────

    _buildToggle(id, value, sectionPath, key) {
        return `
            <label class="tcp-toggle" onclick="event.stopPropagation()">
                <input type="checkbox" id="${id}" ${value ? 'checked' : ''}
                       data-section="${sectionPath}" data-key="${key}"
                       onchange="TradingConfigPanel._onToggleChange(this)" />
                <div class="tcp-toggle__track"></div>
                <div class="tcp-toggle__thumb"></div>
            </label>
        `;
    },

    // ═══════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════

    _toggleSection(sectionId) {
        const el = document.getElementById(`tcp-${sectionId}`);
        if (el) el.classList.toggle('tcp-section--collapsed');
    },

    /** Weight slider changed — auto-normalize to 1.0 */
    _onWeightSlider(input) {
        const section = input.dataset.section;
        const key     = input.dataset.key;
        const rawVal  = parseInt(input.value) / 100;

        // Get the section schema
        const sectionDef = this.SECTIONS.find(s => s.path === section);
        if (!sectionDef) return;

        const fields = sectionDef.fields;
        const otherFields = fields.filter(f => f.key !== key);

        // Current sum of others
        let othersSum = 0;
        otherFields.forEach(f => {
            othersSum += (this._config[section]?.[f.key] || 0);
        });

        // Clamp: the slider value can't exceed what's left if others are at 0,
        // but it CAN be set freely — we'll scale others down proportionally.
        let newVal = Math.max(0, Math.min(1, rawVal));

        // Update config
        if (!this._config[section]) this._config[section] = {};
        this._config[section][key] = newVal;

        // Scale others proportionally so total = 1.0
        const remaining = 1.0 - newVal;
        if (othersSum > 0) {
            const scale = remaining / othersSum;
            otherFields.forEach(f => {
                this._config[section][f.key] = Math.max(0, (this._config[section][f.key] || 0) * scale);
            });
        } else if (otherFields.length > 0) {
            // All others are 0 — distribute remaining equally
            const each = remaining / otherFields.length;
            otherFields.forEach(f => {
                this._config[section][f.key] = each;
            });
        }

        // Round to avoid floating point drift
        let sum = 0;
        fields.forEach(f => {
            this._config[section][f.key] = Math.round(this._config[section][f.key] * 100) / 100;
            sum += this._config[section][f.key];
        });
        // Fix rounding error on last field
        if (Math.abs(sum - 1.0) > 0.001) {
            const lastField = fields[fields.length - 1];
            this._config[section][lastField.key] += (1.0 - sum);
            this._config[section][lastField.key] = Math.round(this._config[section][lastField.key] * 100) / 100;
        }

        // Sync all slider positions and labels
        fields.forEach(f => {
            const slider = document.getElementById(`tcp-w-${section}-${f.key}`);
            const label  = document.getElementById(`tcp-wv-${section}-${f.key}`);
            const val = this._config[section][f.key] || 0;
            if (slider && f.key !== key) slider.value = Math.round(val * 100);
            if (label) label.textContent = `${(val * 100).toFixed(0)}%`;
        });

        this._updateWeightBar(section);
        this._updateWeightTotal(section);
        this._emitChange();
    },

    /** Stepper button click */
    _stepValue(id, delta, min, max, sectionPath, key) {
        const input = document.getElementById(id);
        if (!input) return;
        let val = parseFloat(input.value) || 0;
        val = Math.round((val + delta) * 1000) / 1000; // avoid float drift
        val = Math.max(min, Math.min(max, val));
        input.value = val;
        this._writeToConfig(sectionPath, key, val);
        this._updateThresholdBar();
        this._emitChange();
    },

    /** Stepper manual input */
    _onStepperChange(input) {
        const section = input.dataset.section;
        const key     = input.dataset.key;
        let val = parseFloat(input.value) || 0;
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);
        val = Math.max(min, Math.min(max, val));
        input.value = val;
        this._writeToConfig(section, key, val);
        this._updateThresholdBar();
        this._emitChange();
    },

    /** Toggle change */
    _onToggleChange(input) {
        const section = input.dataset.section;
        const key     = input.dataset.key;
        this._writeToConfig(section, key, input.checked);
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
                    max_signals_per_hour: 3, cooldown_seconds: 300, consecutive_loss_halt: 2, sentiment_exit: true }
        };
    },

    // ═══════════════════════════════════════════════════════════════════
    // VISUAL UPDATES
    // ═══════════════════════════════════════════════════════════════════

    _updateAllVisuals() {
        this.SECTIONS.forEach(s => {
            if (s.type === 'weights') {
                this._updateWeightBar(s.path);
                this._updateWeightTotal(s.path);
            }
        });
        this._updateThresholdBar();
    },

    _updateWeightBar(sectionPath) {
        const barEl = document.getElementById(`tcp-bar-${sectionPath}`);
        if (!barEl) return;
        const section = this.SECTIONS.find(s => s.path === sectionPath);
        if (!section) return;

        section.fields.forEach(f => {
            const seg = barEl.querySelector(`[data-bar-key="${f.key}"]`);
            if (seg) {
                const val = this._config[sectionPath]?.[f.key] || 0;
                seg.style.width = `${val * 100}%`;
                seg.title = `${f.label}: ${(val * 100).toFixed(0)}%`;
            }
        });
    },

    _updateWeightTotal(sectionPath) {
        const section = this.SECTIONS.find(s => s.path === sectionPath);
        if (!section) return;
        const totalEl = document.getElementById(`tcp-total-${sectionPath}`);
        if (!totalEl) return;

        const sum = section.fields.reduce((s, f) => s + (this._config[sectionPath]?.[f.key] || 0), 0);
        const isOk = Math.abs(sum - 1.0) < 0.02;
        totalEl.textContent = `${(sum * 100).toFixed(0)}%`;
        totalEl.className = `tcp-total-row__value ${isOk ? 'tcp-total-row__value--ok' : 'tcp-total-row__value--warn'}`;
    },

    _updateThresholdBar() {
        const bar = document.getElementById('tcp-thresh-bar');
        if (!bar) return;

        const th = this._config.thresholds || {};
        const buy  = th.buy || 0.55;
        const sell = Math.abs(th.sell || -0.55);
        const dz   = th.dead_zone || 0.25;

        const sellZone = bar.querySelector('.tcp-threshold-bar__zone--sell');
        const deadZone = bar.querySelector('.tcp-threshold-bar__zone--dead');
        const buyZone  = bar.querySelector('.tcp-threshold-bar__zone--buy');

        if (sellZone) sellZone.style.width = `${sell * 50}%`;
        if (deadZone) {
            deadZone.style.left  = `${50 - dz * 50}%`;
            deadZone.style.width = `${dz * 100}%`;
        }
        if (buyZone) buyZone.style.width = `${buy * 50}%`;
    },

    _syncInputsFromConfig() {
        this.SECTIONS.forEach(section => {
            const vals = this._config[section.path] || {};
            section.fields.forEach(f => {
                if (section.type === 'weights') {
                    const slider = document.getElementById(`tcp-w-${section.path}-${f.key}`);
                    const label  = document.getElementById(`tcp-wv-${section.path}-${f.key}`);
                    const val = vals[f.key] || 0;
                    if (slider) slider.value = Math.round(val * 100);
                    if (label) label.textContent = `${(val * 100).toFixed(0)}%`;
                } else if (f.type === 'toggle') {
                    const toggle = document.getElementById(`tcp-r-${f.key}`);
                    if (toggle) toggle.checked = !!vals[f.key];
                } else {
                    const idPrefix = section.type === 'thresholds' ? 'tcp-t' : 'tcp-r';
                    const input = document.getElementById(`${idPrefix}-${f.key}`);
                    if (input) input.value = vals[f.key] || 0;
                }
            });
        });
    },

    // ═══════════════════════════════════════════════════════════════════
    // BIND EVENTS
    // ═══════════════════════════════════════════════════════════════════

    _bindEvents() {
        // Stop click propagation on the whole panel to prevent
        // the profile form from intercepting events
        if (this._container) {
            this._container.addEventListener('click', e => e.stopPropagation());
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
