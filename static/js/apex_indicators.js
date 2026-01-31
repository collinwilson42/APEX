/* ═══════════════════════════════════════════════════════════════════════════
   APEX CHART INDICATORS - Overlay System with Settings Panel
   
   Features:
   - Settings gear icon per chart
   - Indicator toggle with color pickers
   - Bar count selector (custom dropdown)
   - Live legend overlay on chart
   - Calculations for EMA, BB, VWAP, Fib zones
   - localStorage persistence for all settings
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexIndicators = {
    // Storage key for localStorage
    STORAGE_KEY: 'apex_chart_settings',
    
    // Default indicator configurations
    defaults: {
        ema9:      { enabled: false, color: '#4A9E9A', weight: 0.45, tf: '1m',   label: 'EMA 9' },
        ema21:     { enabled: true,  color: '#5B8A8A', weight: 0.65, tf: 'both', label: 'EMA 21' },
        ema50:     { enabled: true,  color: '#7AB5B0', weight: 0.75, tf: '15m',  label: 'EMA 50' },
        ema200:    { enabled: true,  color: '#6B7280', weight: 0.90, tf: '15m',  label: 'EMA 200' },
        vwap:      { enabled: false, color: '#8B7EC8', weight: 0.85, tf: 'both', label: 'VWAP' },
        bbands:    { enabled: true,  color: '#4A7A9E', weight: 0.70, tf: 'both', label: 'Bollinger Bands', fill: 'rgba(74, 122, 158, 0.06)' },
        keltner:   { enabled: false, color: '#5A6A9E', weight: 0.55, tf: '15m',  label: 'Keltner Channels' },
        fibGolden: { enabled: true,  color: '#7EAE8B', weight: 0.95, tf: '15m',  label: 'Golden Zone', fill: 'rgba(126, 174, 139, 0.08)' },
        fibLevels: { enabled: false, color: '#5B8A8A', weight: 0.60, tf: '15m',  label: 'Fib Levels' },
        pivots:    { enabled: false, color: '#A89060', weight: 0.80, tf: '15m',  label: 'Pivot Points' },
        athZone:   { enabled: false, color: '#7EAE8B', weight: 0.85, tf: '15m',  label: 'ATH Zone', fill: 'rgba(126, 174, 139, 0.06)' },
    },
    
    // Bar count options
    barOptions: [50, 100, 200, 500],
    
    // Per-chart settings storage
    chartSettings: {
        '1m':  { bars: 100, indicators: {} },
        '15m': { bars: 100, indicators: {} }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION & PERSISTENCE
    // ═══════════════════════════════════════════════════════════════════════
    
    init() {
        const saved = this.loadSettings();
        
        if (saved) {
            this.chartSettings = saved;
            console.log('[ApexIndicators] Loaded from localStorage - 1m bars:', this.chartSettings['1m'].bars, '15m bars:', this.chartSettings['15m'].bars);
        } else {
            ['1m', '15m'].forEach(tf => {
                this.chartSettings[tf].indicators = JSON.parse(JSON.stringify(this.defaults));
                Object.keys(this.chartSettings[tf].indicators).forEach(key => {
                    const ind = this.chartSettings[tf].indicators[key];
                    if (ind.tf !== 'both' && ind.tf !== tf) {
                        ind.enabled = false;
                    }
                });
            });
            this.saveSettings();
            console.log('[ApexIndicators] Initialized with defaults');
        }
    },
    
    loadSettings() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (data) {
                const parsed = JSON.parse(data);
                if (parsed['1m'] && parsed['15m'] && 
                    typeof parsed['1m'].bars === 'number' && parsed['1m'].indicators &&
                    typeof parsed['15m'].bars === 'number' && parsed['15m'].indicators) {
                    return parsed;
                }
            }
        } catch (e) {
            console.warn('[ApexIndicators] Failed to load settings:', e);
        }
        return null;
    },
    
    saveSettings() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.chartSettings));
        } catch (e) {
            console.warn('[ApexIndicators] Failed to save settings:', e);
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // INDICATOR CALCULATIONS
    // ═══════════════════════════════════════════════════════════════════════
    
    calculateEMA(data, period) {
        const k = 2 / (period + 1);
        const ema = [];
        let prevEma = null;
        
        for (let i = 0; i < data.length; i++) {
            const close = parseFloat(data[i].close);
            if (i < period - 1) {
                ema.push(null);
            } else if (prevEma === null) {
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    sum += parseFloat(data[i - j].close);
                }
                prevEma = sum / period;
                ema.push(prevEma);
            } else {
                prevEma = close * k + prevEma * (1 - k);
                ema.push(prevEma);
            }
        }
        return ema;
    },
    
    calculateSMA(data, period) {
        const sma = [];
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                sma.push(null);
            } else {
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    sum += parseFloat(data[i - j].close);
                }
                sma.push(sum / period);
            }
        }
        return sma;
    },
    
    calculateBollingerBands(data, period = 20, stdDev = 2) {
        const sma = this.calculateSMA(data, period);
        const upper = [];
        const lower = [];
        
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                upper.push(null);
                lower.push(null);
            } else {
                let sumSq = 0;
                for (let j = 0; j < period; j++) {
                    const diff = parseFloat(data[i - j].close) - sma[i];
                    sumSq += diff * diff;
                }
                const std = Math.sqrt(sumSq / period);
                upper.push(sma[i] + stdDev * std);
                lower.push(sma[i] - stdDev * std);
            }
        }
        return { upper, middle: sma, lower };
    },
    
    calculateVWAP(data) {
        const vwap = [];
        let cumVolPrice = 0;
        let cumVol = 0;
        let currentDay = null;
        
        for (let i = 0; i < data.length; i++) {
            const d = data[i];
            const date = new Date(d.timestamp || d.time);
            const day = date.toDateString();
            
            if (day !== currentDay) {
                cumVolPrice = 0;
                cumVol = 0;
                currentDay = day;
            }
            
            const typicalPrice = (parseFloat(d.high) + parseFloat(d.low) + parseFloat(d.close)) / 3;
            const volume = parseFloat(d.volume) || 1;
            
            cumVolPrice += typicalPrice * volume;
            cumVol += volume;
            
            vwap.push(cumVol > 0 ? cumVolPrice / cumVol : null);
        }
        return vwap;
    },
    
    calculateKeltnerChannels(data, period = 20, atrMult = 1.5) {
        const ema = this.calculateEMA(data, period);
        const atr = this.calculateATR(data, period);
        
        const upper = [];
        const lower = [];
        
        for (let i = 0; i < data.length; i++) {
            if (ema[i] === null || atr[i] === null) {
                upper.push(null);
                lower.push(null);
            } else {
                upper.push(ema[i] + atrMult * atr[i]);
                lower.push(ema[i] - atrMult * atr[i]);
            }
        }
        return { upper, middle: ema, lower };
    },
    
    calculateATR(data, period = 14) {
        const tr = [];
        const atr = [];
        
        for (let i = 0; i < data.length; i++) {
            const high = parseFloat(data[i].high);
            const low = parseFloat(data[i].low);
            const prevClose = i > 0 ? parseFloat(data[i - 1].close) : parseFloat(data[i].close);
            
            const trValue = Math.max(
                high - low,
                Math.abs(high - prevClose),
                Math.abs(low - prevClose)
            );
            tr.push(trValue);
            
            if (i < period - 1) {
                atr.push(null);
            } else if (i === period - 1) {
                let sum = 0;
                for (let j = 0; j < period; j++) sum += tr[j];
                atr.push(sum / period);
            } else {
                atr.push((atr[i - 1] * (period - 1) + trValue) / period);
            }
        }
        return atr;
    },
    
    calculatePivotPoints(data) {
        if (data.length < 2) return null;
        
        const lastBar = data[data.length - 1];
        const lastDate = new Date(lastBar.timestamp || lastBar.time).toDateString();
        
        let prevDayHigh = -Infinity, prevDayLow = Infinity, prevDayClose = 0;
        let foundPrevDay = false;
        
        for (let i = data.length - 1; i >= 0; i--) {
            const barDate = new Date(data[i].timestamp || data[i].time).toDateString();
            if (barDate !== lastDate) {
                if (!foundPrevDay) foundPrevDay = true;
                if (foundPrevDay) {
                    const h = parseFloat(data[i].high);
                    const l = parseFloat(data[i].low);
                    if (h > prevDayHigh) prevDayHigh = h;
                    if (l < prevDayLow) prevDayLow = l;
                    prevDayClose = parseFloat(data[i].close);
                }
            } else if (foundPrevDay) {
                break;
            }
        }
        
        if (!foundPrevDay) return null;
        
        const pivot = (prevDayHigh + prevDayLow + prevDayClose) / 3;
        return {
            pivot,
            r1: 2 * pivot - prevDayLow,
            r2: pivot + (prevDayHigh - prevDayLow),
            s1: 2 * pivot - prevDayHigh,
            s2: pivot - (prevDayHigh - prevDayLow)
        };
    },
    
    calculateFibLevels(data) {
        const highs = data.map(d => parseFloat(d.high));
        const lows = data.map(d => parseFloat(d.low));
        
        const swingHigh = Math.max(...highs);
        const swingLow = Math.min(...lows);
        const range = swingHigh - swingLow;
        
        return {
            level0: swingLow,
            level236: swingLow + range * 0.236,
            level382: swingLow + range * 0.382,
            level500: swingLow + range * 0.5,
            level618: swingLow + range * 0.618,
            level786: swingLow + range * 0.786,
            level1000: swingHigh,
            goldenLow: swingLow + range * 0.618,
            goldenHigh: swingLow + range * 0.786
        };
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // GENERATE PLOTLY TRACES
    // ═══════════════════════════════════════════════════════════════════════
    
    generateTraces(data, timeframe, xLabels = null) {
        const settings = this.chartSettings[timeframe];
        const indicators = settings.indicators;
        const traces = [];
        
        const x = xLabels || data.map(d => new Date(d.timestamp || d.time));
        
        if (indicators.ema9?.enabled) {
            traces.push({ type: 'scatter', mode: 'lines', x, y: this.calculateEMA(data, 9),
                name: 'EMA 9', line: { color: indicators.ema9.color, width: 1 }, hoverinfo: 'skip' });
        }
        
        if (indicators.ema21?.enabled) {
            traces.push({ type: 'scatter', mode: 'lines', x, y: this.calculateEMA(data, 21),
                name: 'EMA 21', line: { color: indicators.ema21.color, width: 1.5 }, hoverinfo: 'skip' });
        }
        
        if (indicators.ema50?.enabled) {
            traces.push({ type: 'scatter', mode: 'lines', x, y: this.calculateEMA(data, 50),
                name: 'EMA 50', line: { color: indicators.ema50.color, width: 1.5 }, hoverinfo: 'skip' });
        }
        
        if (indicators.ema200?.enabled) {
            traces.push({ type: 'scatter', mode: 'lines', x, y: this.calculateEMA(data, 200),
                name: 'EMA 200', line: { color: indicators.ema200.color, width: 2 }, hoverinfo: 'skip' });
        }
        
        if (indicators.vwap?.enabled) {
            traces.push({ type: 'scatter', mode: 'lines', x, y: this.calculateVWAP(data),
                name: 'VWAP', line: { color: indicators.vwap.color, width: 1.5, dash: 'dot' }, hoverinfo: 'skip' });
        }
        
        if (indicators.bbands?.enabled) {
            const bb = this.calculateBollingerBands(data, 20, 2);
            traces.push({ type: 'scatter', mode: 'lines', x, y: bb.upper,
                name: 'BB Upper', line: { color: indicators.bbands.color, width: 1 }, hoverinfo: 'skip' });
            traces.push({ type: 'scatter', mode: 'lines', x, y: bb.lower,
                name: 'BB Lower', line: { color: indicators.bbands.color, width: 1 },
                fill: 'tonexty', fillcolor: indicators.bbands.fill, hoverinfo: 'skip' });
            traces.push({ type: 'scatter', mode: 'lines', x, y: bb.middle,
                name: 'BB Mid', line: { color: indicators.bbands.color, width: 1, dash: 'dot' }, hoverinfo: 'skip' });
        }
        
        if (indicators.keltner?.enabled) {
            const kc = this.calculateKeltnerChannels(data, 20, 1.5);
            traces.push({ type: 'scatter', mode: 'lines', x, y: kc.upper,
                name: 'KC Upper', line: { color: indicators.keltner.color, width: 1, dash: 'dash' }, hoverinfo: 'skip' });
            traces.push({ type: 'scatter', mode: 'lines', x, y: kc.lower,
                name: 'KC Lower', line: { color: indicators.keltner.color, width: 1, dash: 'dash' }, hoverinfo: 'skip' });
        }
        
        if (indicators.fibGolden?.enabled) {
            const fib = this.calculateFibLevels(data);
            traces.push({ type: 'scatter', mode: 'lines', x: [x[0], x[x.length - 1]], y: [fib.goldenHigh, fib.goldenHigh],
                name: 'Golden Zone', line: { color: indicators.fibGolden.color, width: 1 }, hoverinfo: 'skip' });
            traces.push({ type: 'scatter', mode: 'lines', x: [x[0], x[x.length - 1]], y: [fib.goldenLow, fib.goldenLow],
                name: 'Golden Zone', line: { color: indicators.fibGolden.color, width: 1 },
                fill: 'tonexty', fillcolor: indicators.fibGolden.fill, showlegend: false, hoverinfo: 'skip' });
        }
        
        if (indicators.fibLevels?.enabled) {
            const fib = this.calculateFibLevels(data);
            [{ y: fib.level236, label: '23.6%' }, { y: fib.level382, label: '38.2%' },
             { y: fib.level500, label: '50%' }, { y: fib.level618, label: '61.8%' },
             { y: fib.level786, label: '78.6%' }].forEach(level => {
                traces.push({ type: 'scatter', mode: 'lines', x: [x[0], x[x.length - 1]], y: [level.y, level.y],
                    name: `Fib ${level.label}`, line: { color: indicators.fibLevels.color, width: 1, dash: 'dot' },
                    hoverinfo: 'skip', showlegend: false });
            });
        }
        
        if (indicators.pivots?.enabled) {
            const pivots = this.calculatePivotPoints(data);
            if (pivots) {
                [{ y: pivots.r2, dash: 'dot' }, { y: pivots.r1, dash: 'dash' },
                 { y: pivots.pivot, dash: 'solid' }, { y: pivots.s1, dash: 'dash' },
                 { y: pivots.s2, dash: 'dot' }].forEach(p => {
                    traces.push({ type: 'scatter', mode: 'lines', x: [x[0], x[x.length - 1]], y: [p.y, p.y],
                        line: { color: indicators.pivots.color, width: 1, dash: p.dash },
                        hoverinfo: 'skip', showlegend: false });
                });
            }
        }
        
        return traces;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // SETTINGS PANEL UI
    // ═══════════════════════════════════════════════════════════════════════
    
    renderSettingsButton(container, timeframe) {
        const cell = container.closest('.trading-cell');
        if (!cell || cell.querySelector('.chart-settings-btn')) return;
        
        const btn = document.createElement('button');
        btn.className = 'chart-settings-btn';
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>`;
        btn.title = 'Chart Settings';
        
        const self = this;
        btn.onclick = function(e) {
            e.stopPropagation();
            self.toggleSettingsPanel(container, timeframe);
        };
        
        const header = cell.querySelector('.trading-cell__header');
        if (header) {
            header.style.position = 'relative';
            btn.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%)';
            header.appendChild(btn);
        }
    },
    
    toggleSettingsPanel(container, timeframe) {
        const cell = container.closest('.trading-cell');
        const existingPanel = cell.querySelector('.chart-settings-panel');
        
        if (existingPanel) {
            existingPanel.remove();
            return;
        }
        
        document.querySelectorAll('.chart-settings-panel').forEach(p => p.remove());
        
        const panel = document.createElement('div');
        panel.className = 'chart-settings-panel';
        panel.innerHTML = this.renderSettingsPanelHTML(timeframe);
        
        cell.appendChild(panel);
        this.bindSettingsEvents(panel, timeframe);
    },
    
    renderSettingsPanelHTML(timeframe) {
        const settings = this.chartSettings[timeframe];
        const indicators = settings.indicators;
        
        let indicatorRows = '';
        Object.entries(indicators).forEach(([key, ind]) => {
            const tfBadge = ind.tf === 'both' ? '' : `<span class="ind-tf-badge ind-tf-badge--${ind.tf}">${ind.tf}</span>`;
            indicatorRows += `
                <div class="ind-row" data-key="${key}">
                    <label class="ind-toggle">
                        <input type="checkbox" ${ind.enabled ? 'checked' : ''} data-ind="${key}" />
                        <span class="ind-label">${ind.label}</span>
                        ${tfBadge}
                    </label>
                    <div class="ind-controls">
                        <span class="ind-weight">${ind.weight.toFixed(2)}</span>
                        <input type="color" value="${ind.color}" data-ind="${key}" class="ind-color" />
                    </div>
                </div>
            `;
        });
        
        // Custom dropdown for bars
        const barsOptions = this.barOptions.map(val => 
            `<div class="custom-dropdown__option ${settings.bars === val ? 'custom-dropdown__option--selected' : ''}" data-value="${val}">${val}</div>`
        ).join('');
        
        return `
            <div class="settings-panel-header">
                <span>Chart Settings (${timeframe})</span>
                <button class="settings-close">&times;</button>
            </div>
            <div class="settings-panel-body">
                <div class="settings-section">
                    <label class="settings-label">Bars</label>
                    <div class="custom-dropdown" data-tf="${timeframe}">
                        <div class="custom-dropdown__selected">
                            <span class="custom-dropdown__value">${settings.bars}</span>
                            <span class="custom-dropdown__arrow">▾</span>
                        </div>
                        <div class="custom-dropdown__options">
                            ${barsOptions}
                        </div>
                    </div>
                </div>
                <div class="settings-section">
                    <label class="settings-label">Indicators</label>
                    <div class="ind-list">
                        ${indicatorRows}
                    </div>
                </div>
            </div>
        `;
    },
    
    bindSettingsEvents(panel, timeframe) {
        const self = this;
        
        // Close button
        panel.querySelector('.settings-close').onclick = function() { panel.remove(); };
        
        // Custom dropdown for bars
        const dropdown = panel.querySelector('.custom-dropdown');
        const selected = dropdown.querySelector('.custom-dropdown__selected');
        const options = dropdown.querySelector('.custom-dropdown__options');
        
        selected.onclick = function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('custom-dropdown--open');
        };
        
        options.querySelectorAll('.custom-dropdown__option').forEach(function(opt) {
            opt.onclick = function(e) {
                e.stopPropagation();
                const newValue = parseInt(opt.dataset.value);
                
                console.log('[ApexIndicators] Bar count changing from', self.chartSettings[timeframe].bars, 'to', newValue, 'for', timeframe);
                
                // Update settings object FIRST
                self.chartSettings[timeframe].bars = newValue;
                
                // Save to localStorage
                self.saveSettings();
                
                // Update UI
                dropdown.querySelector('.custom-dropdown__value').textContent = newValue;
                options.querySelectorAll('.custom-dropdown__option').forEach(function(o) {
                    o.classList.toggle('custom-dropdown__option--selected', parseInt(o.dataset.value) === newValue);
                });
                dropdown.classList.remove('custom-dropdown--open');
                
                // Trigger refresh
                console.log('[ApexIndicators] Triggering refresh for', timeframe, 'with bars:', self.getBarCount(timeframe));
                self.triggerRefresh(timeframe);
            };
        });
        
        // Prevent panel from closing on interaction
        panel.onclick = function(e) { e.stopPropagation(); };
        panel.onmousedown = function(e) { e.stopPropagation(); };
        
        // Indicator toggles
        panel.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
            cb.onchange = function(e) {
                const key = e.target.dataset.ind;
                self.chartSettings[timeframe].indicators[key].enabled = e.target.checked;
                self.saveSettings();
                self.triggerRefresh(timeframe);
            };
        });
        
        // Color pickers
        panel.querySelectorAll('.ind-color').forEach(function(input) {
            input.onchange = function(e) {
                const key = e.target.dataset.ind;
                self.chartSettings[timeframe].indicators[key].color = e.target.value;
                self.saveSettings();
                self.triggerRefresh(timeframe);
            };
        });
    },
    
    triggerRefresh(timeframe) {
        console.log('[ApexIndicators] Dispatching apex-chart-refresh for', timeframe);
        window.dispatchEvent(new CustomEvent('apex-chart-refresh', { detail: { timeframe } }));
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // LEGEND OVERLAY
    // ═══════════════════════════════════════════════════════════════════════
    
    renderLegend(container, timeframe) {
        const cell = container.closest('.trading-cell');
        const existing = cell?.querySelector('.chart-legend');
        if (existing) existing.remove();
        
        const settings = this.chartSettings[timeframe];
        const activeIndicators = Object.entries(settings.indicators).filter(([_, ind]) => ind.enabled);
        
        if (activeIndicators.length === 0) return;
        
        const legend = document.createElement('div');
        legend.className = 'chart-legend';
        
        activeIndicators.forEach(([key, ind]) => {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = `<span class="legend-color" style="background:${ind.color}"></span><span class="legend-label">${ind.label}</span>`;
            legend.appendChild(item);
        });
        
        cell?.querySelector('.trading-cell__content')?.appendChild(legend);
    },
    
    getBarCount(timeframe) {
        const bars = this.chartSettings[timeframe]?.bars;
        console.log('[ApexIndicators] getBarCount for', timeframe, '=', bars);
        return bars || 100;
    }
};

// Initialize on load
ApexIndicators.init();
window.ApexIndicators = ApexIndicators;
