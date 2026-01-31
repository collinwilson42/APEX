/* ═══════════════════════════════════════════════════════════════════════════
   APEX CHARTS V1 - Family A: Candlestick & Visual Render Core
   5-State coloring, EMA lines, volume bars, Bollinger bands
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * APEX Chart Configuration
 */
const ChartConfig = {
    // Candle appearance
    candle: {
        width: 8,
        spacing: 2,
        wickWidth: 1,
        borderRadius: 1
    },
    
    // 5-State color palette
    colors: {
        strongBull: '#ADEBB3',  // Mint
        bull: '#46B4AF',        // Teal
        neutral: '#A4A9B3',     // Gray
        bear: '#3A5F8A',        // Steel Blue
        strongBear: '#0A2540', // Deep Navy
        wick: '#6B7280',
        grid: 'rgba(255, 255, 255, 0.04)',
        gridText: '#5A5F6A',
        crosshair: 'rgba(164, 169, 179, 0.5)',
        ema9: '#ADEBB3',
        ema21: '#46B4AF',
        ema50: '#A4A9B3',
        ema200: '#3A5F8A',
        bollingerUpper: 'rgba(70, 180, 175, 0.4)',
        bollingerLower: 'rgba(70, 180, 175, 0.4)',
        bollingerFill: 'rgba(70, 180, 175, 0.08)',
        volume: 'rgba(164, 169, 179, 0.3)'
    },
    
    // Layout
    layout: {
        padding: { top: 20, right: 60, bottom: 30, left: 10 },
        volumeHeight: 0.15, // 15% of chart height
        priceAxisWidth: 55
    }
};

/**
 * APEX Candlestick Chart
 * Canvas-based for performance with large datasets
 */
class ApexCandlestickChart {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
            
        this.options = { ...ChartConfig, ...options };
        this.data = [];
        this.visibleRange = { start: 0, end: 100 };
        this.crosshair = null;
        this.indicators = {
            ema9: true,
            ema21: true,
            ema50: false,
            ema200: false,
            bollinger: false,
            volume: true
        };
        
        this.canvas = null;
        this.ctx = null;
        this.overlayCanvas = null;
        this.overlayCtx = null;
        
        this.setupDOM();
        this.setupEventListeners();
    }
    
    setupDOM() {
        this.container.innerHTML = '';
        this.container.style.position = 'relative';
        
        // Main canvas for chart
        this.canvas = document.createElement('canvas');
        this.canvas.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%;';
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // Overlay canvas for crosshair and tooltips
        this.overlayCanvas = document.createElement('canvas');
        this.overlayCanvas.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;';
        this.container.appendChild(this.overlayCanvas);
        this.overlayCtx = this.overlayCanvas.getContext('2d');
        
        // Tooltip element
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'chart-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            display: none;
            background: rgba(28, 30, 34, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 11px;
            color: #F2F4F7;
            pointer-events: none;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        `;
        this.container.appendChild(this.tooltip);
        
        this.resize();
    }
    
    resize() {
        const rect = this.container.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        
        this.width = rect.width;
        this.height = rect.height;
        
        // Set canvas sizes with DPR for sharp rendering
        [this.canvas, this.overlayCanvas].forEach(canvas => {
            canvas.width = this.width * dpr;
            canvas.height = this.height * dpr;
            canvas.style.width = this.width + 'px';
            canvas.style.height = this.height + 'px';
            canvas.getContext('2d').scale(dpr, dpr);
        });
        
        this.render();
    }
    
    setupEventListeners() {
        // Resize observer
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.container);
        
        // Mouse events for crosshair
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.onMouseLeave());
        
        // Scroll to zoom
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Drag to pan
        let isDragging = false;
        let dragStart = 0;
        
        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            dragStart = e.clientX;
            this.canvas.style.cursor = 'grabbing';
        });
        
        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const delta = e.clientX - dragStart;
            this.pan(delta);
            dragStart = e.clientX;
        });
        
        window.addEventListener('mouseup', () => {
            isDragging = false;
            this.canvas.style.cursor = 'crosshair';
        });
    }
    
    /**
     * Set chart data
     * @param {Array} data - Array of OHLCV objects {time, open, high, low, close, volume}
     */
    setData(data) {
        this.data = data;
        this.calculateIndicators();
        
        // Set initial visible range to last 100 candles
        this.visibleRange.end = data.length;
        this.visibleRange.start = Math.max(0, data.length - 100);
        
        this.render();
    }
    
    calculateIndicators() {
        if (this.data.length === 0) return;
        
        // Calculate EMAs
        this.data.forEach((candle, i) => {
            candle.ema9 = this.calcEMA(i, 9);
            candle.ema21 = this.calcEMA(i, 21);
            candle.ema50 = this.calcEMA(i, 50);
            candle.ema200 = this.calcEMA(i, 200);
        });
        
        // Calculate Bollinger Bands (20, 2)
        const period = 20;
        const stdDev = 2;
        
        this.data.forEach((candle, i) => {
            if (i < period - 1) {
                candle.bbUpper = candle.bbMiddle = candle.bbLower = null;
                return;
            }
            
            const slice = this.data.slice(i - period + 1, i + 1);
            const sma = slice.reduce((sum, c) => sum + c.close, 0) / period;
            const variance = slice.reduce((sum, c) => sum + Math.pow(c.close - sma, 2), 0) / period;
            const std = Math.sqrt(variance);
            
            candle.bbMiddle = sma;
            candle.bbUpper = sma + stdDev * std;
            candle.bbLower = sma - stdDev * std;
        });
        
        // Calculate 5-state classification
        this.data.forEach((candle, i) => {
            candle.state = this.classifyCandle(candle, i);
        });
    }
    
    calcEMA(index, period) {
        if (index < period - 1) return null;
        
        const multiplier = 2 / (period + 1);
        
        if (index === period - 1) {
            // First EMA is SMA
            let sum = 0;
            for (let i = 0; i < period; i++) {
                sum += this.data[i].close;
            }
            return sum / period;
        }
        
        const prevEMA = this.data[index - 1][`ema${period}`];
        if (prevEMA === null) return null;
        
        return (this.data[index].close - prevEMA) * multiplier + prevEMA;
    }
    
    /**
     * Classify candle into 5-state system
     */
    classifyCandle(candle, index) {
        const bodySize = Math.abs(candle.close - candle.open);
        const range = candle.high - candle.low;
        const bodyRatio = range > 0 ? bodySize / range : 0;
        const isBullish = candle.close > candle.open;
        
        // Look at momentum (compare to previous candles)
        let momentum = 0;
        if (index >= 3) {
            const prevCandles = this.data.slice(index - 3, index);
            const avgClose = prevCandles.reduce((s, c) => s + c.close, 0) / 3;
            momentum = (candle.close - avgClose) / avgClose;
        }
        
        // Strong Bull: Large bullish body with strong momentum
        if (isBullish && bodyRatio > 0.6 && momentum > 0.005) {
            return 'strongBull';
        }
        
        // Strong Bear: Large bearish body with strong negative momentum
        if (!isBullish && bodyRatio > 0.6 && momentum < -0.005) {
            return 'strongBear';
        }
        
        // Bull: Bullish candle
        if (isBullish && bodyRatio > 0.3) {
            return 'bull';
        }
        
        // Bear: Bearish candle
        if (!isBullish && bodyRatio > 0.3) {
            return 'bear';
        }
        
        // Neutral: Doji or small body
        return 'neutral';
    }
    
    render() {
        if (!this.ctx || this.data.length === 0) return;
        
        const ctx = this.ctx;
        const { padding, volumeHeight, priceAxisWidth } = this.options.layout;
        
        // Clear
        ctx.clearRect(0, 0, this.width, this.height);
        
        // Calculate chart area
        const chartLeft = padding.left;
        const chartRight = this.width - padding.right - priceAxisWidth;
        const chartTop = padding.top;
        const chartBottom = this.height - padding.bottom;
        const chartWidth = chartRight - chartLeft;
        const chartHeight = chartBottom - chartTop;
        
        // Volume area (bottom portion)
        const volumeTop = chartBottom - chartHeight * volumeHeight;
        const priceBottom = volumeTop - 10; // Gap between price and volume
        const priceHeight = priceBottom - chartTop;
        
        // Get visible data
        const visibleData = this.data.slice(this.visibleRange.start, this.visibleRange.end);
        if (visibleData.length === 0) return;
        
        // Calculate scales
        const priceMin = Math.min(...visibleData.map(c => c.low));
        const priceMax = Math.max(...visibleData.map(c => c.high));
        const priceRange = priceMax - priceMin;
        const pricePadding = priceRange * 0.1;
        
        const volumeMax = Math.max(...visibleData.map(c => c.volume));
        
        const scaleY = (price) => {
            return chartTop + priceHeight - ((price - priceMin + pricePadding) / (priceRange + pricePadding * 2)) * priceHeight;
        };
        
        const scaleVolumeY = (vol) => {
            return chartBottom - (vol / volumeMax) * (chartHeight * volumeHeight);
        };
        
        // Calculate candle width
        const totalCandleWidth = chartWidth / visibleData.length;
        const candleWidth = Math.max(1, Math.min(this.options.candle.width, totalCandleWidth * 0.8));
        const candleSpacing = totalCandleWidth - candleWidth;
        
        // Draw grid
        this.drawGrid(ctx, chartLeft, chartTop, chartRight, priceBottom, priceMin, priceMax, pricePadding);
        
        // Draw Bollinger Bands
        if (this.indicators.bollinger) {
            this.drawBollingerBands(ctx, visibleData, chartLeft, totalCandleWidth, scaleY);
        }
        
        // Draw volume bars
        if (this.indicators.volume) {
            this.drawVolume(ctx, visibleData, chartLeft, totalCandleWidth, candleWidth, scaleVolumeY, chartBottom);
        }
        
        // Draw EMAs
        this.drawEMAs(ctx, visibleData, chartLeft, totalCandleWidth, scaleY);
        
        // Draw candles
        this.drawCandles(ctx, visibleData, chartLeft, totalCandleWidth, candleWidth, scaleY);
        
        // Draw price axis
        this.drawPriceAxis(ctx, chartRight + 5, chartTop, priceBottom, priceMin, priceMax, pricePadding);
    }
    
    drawGrid(ctx, left, top, right, bottom, priceMin, priceMax, padding) {
        const { colors } = this.options;
        
        ctx.strokeStyle = colors.grid;
        ctx.lineWidth = 1;
        
        // Horizontal lines (price levels)
        const priceRange = priceMax - priceMin + padding * 2;
        const numLines = 5;
        const step = priceRange / numLines;
        
        for (let i = 0; i <= numLines; i++) {
            const y = top + (bottom - top) * (i / numLines);
            ctx.beginPath();
            ctx.moveTo(left, y);
            ctx.lineTo(right, y);
            ctx.stroke();
        }
    }
    
    drawCandles(ctx, data, startX, totalWidth, candleWidth, scaleY) {
        const { colors, candle } = this.options;
        
        data.forEach((d, i) => {
            const x = startX + i * totalWidth + (totalWidth - candleWidth) / 2;
            const color = colors[d.state];
            
            const openY = scaleY(d.open);
            const closeY = scaleY(d.close);
            const highY = scaleY(d.high);
            const lowY = scaleY(d.low);
            
            const bodyTop = Math.min(openY, closeY);
            const bodyBottom = Math.max(openY, closeY);
            const bodyHeight = Math.max(1, bodyBottom - bodyTop);
            
            // Draw wick
            ctx.strokeStyle = colors.wick;
            ctx.lineWidth = candle.wickWidth;
            ctx.beginPath();
            ctx.moveTo(x + candleWidth / 2, highY);
            ctx.lineTo(x + candleWidth / 2, lowY);
            ctx.stroke();
            
            // Draw body
            ctx.fillStyle = color;
            ctx.beginPath();
            if (candle.borderRadius > 0) {
                this.roundRect(ctx, x, bodyTop, candleWidth, bodyHeight, candle.borderRadius);
            } else {
                ctx.rect(x, bodyTop, candleWidth, bodyHeight);
            }
            ctx.fill();
        });
    }
    
    drawVolume(ctx, data, startX, totalWidth, candleWidth, scaleY, bottom) {
        const { colors } = this.options;
        
        data.forEach((d, i) => {
            const x = startX + i * totalWidth + (totalWidth - candleWidth) / 2;
            const y = scaleY(d.volume);
            const height = bottom - y;
            
            ctx.fillStyle = d.close >= d.open 
                ? 'rgba(173, 235, 179, 0.3)' 
                : 'rgba(58, 95, 138, 0.3)';
            ctx.fillRect(x, y, candleWidth, height);
        });
    }
    
    drawEMAs(ctx, data, startX, totalWidth, scaleY) {
        const { colors } = this.options;
        const emas = [
            { key: 'ema9', color: colors.ema9, enabled: this.indicators.ema9 },
            { key: 'ema21', color: colors.ema21, enabled: this.indicators.ema21 },
            { key: 'ema50', color: colors.ema50, enabled: this.indicators.ema50 },
            { key: 'ema200', color: colors.ema200, enabled: this.indicators.ema200 }
        ];
        
        emas.forEach(ema => {
            if (!ema.enabled) return;
            
            ctx.strokeStyle = ema.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            
            let started = false;
            data.forEach((d, i) => {
                if (d[ema.key] === null) return;
                
                const x = startX + i * totalWidth + totalWidth / 2;
                const y = scaleY(d[ema.key]);
                
                if (!started) {
                    ctx.moveTo(x, y);
                    started = true;
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
        });
    }
    
    drawBollingerBands(ctx, data, startX, totalWidth, scaleY) {
        const { colors } = this.options;
        
        // Draw fill between bands
        ctx.fillStyle = colors.bollingerFill;
        ctx.beginPath();
        
        // Upper band (forward)
        let started = false;
        data.forEach((d, i) => {
            if (d.bbUpper === null) return;
            const x = startX + i * totalWidth + totalWidth / 2;
            const y = scaleY(d.bbUpper);
            if (!started) {
                ctx.moveTo(x, y);
                started = true;
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        // Lower band (backward)
        for (let i = data.length - 1; i >= 0; i--) {
            if (data[i].bbLower === null) continue;
            const x = startX + i * totalWidth + totalWidth / 2;
            const y = scaleY(data[i].bbLower);
            ctx.lineTo(x, y);
        }
        
        ctx.closePath();
        ctx.fill();
        
        // Draw band lines
        ['bbUpper', 'bbLower'].forEach(band => {
            ctx.strokeStyle = band === 'bbUpper' ? colors.bollingerUpper : colors.bollingerLower;
            ctx.lineWidth = 1;
            ctx.beginPath();
            
            started = false;
            data.forEach((d, i) => {
                if (d[band] === null) return;
                const x = startX + i * totalWidth + totalWidth / 2;
                const y = scaleY(d[band]);
                if (!started) {
                    ctx.moveTo(x, y);
                    started = true;
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
        });
    }
    
    drawPriceAxis(ctx, x, top, bottom, priceMin, priceMax, padding) {
        const { colors } = this.options;
        const numLabels = 5;
        const priceRange = priceMax - priceMin + padding * 2;
        
        ctx.fillStyle = colors.gridText;
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'left';
        
        for (let i = 0; i <= numLabels; i++) {
            const y = top + (bottom - top) * (i / numLabels);
            const price = priceMax + padding - (priceRange * (i / numLabels));
            ctx.fillText(this.formatPrice(price), x, y + 3);
        }
    }
    
    formatPrice(price) {
        if (price >= 1000) return price.toFixed(0);
        if (price >= 1) return price.toFixed(2);
        return price.toFixed(5);
    }
    
    roundRect(ctx, x, y, width, height, radius) {
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.crosshair = { x, y };
        this.renderOverlay();
        this.updateTooltip(x, y);
    }
    
    onMouseLeave() {
        this.crosshair = null;
        this.tooltip.style.display = 'none';
        this.overlayCtx.clearRect(0, 0, this.width, this.height);
    }
    
    renderOverlay() {
        if (!this.crosshair) return;
        
        const ctx = this.overlayCtx;
        const { padding, priceAxisWidth } = this.options.layout;
        
        ctx.clearRect(0, 0, this.width, this.height);
        
        // Draw crosshair
        ctx.strokeStyle = this.options.colors.crosshair;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        
        // Vertical line
        ctx.beginPath();
        ctx.moveTo(this.crosshair.x, padding.top);
        ctx.lineTo(this.crosshair.x, this.height - padding.bottom);
        ctx.stroke();
        
        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(padding.left, this.crosshair.y);
        ctx.lineTo(this.width - padding.right - priceAxisWidth, this.crosshair.y);
        ctx.stroke();
        
        ctx.setLineDash([]);
    }
    
    updateTooltip(mouseX, mouseY) {
        const { padding, priceAxisWidth } = this.options.layout;
        const chartLeft = padding.left;
        const chartRight = this.width - padding.right - priceAxisWidth;
        const chartWidth = chartRight - chartLeft;
        
        const visibleData = this.data.slice(this.visibleRange.start, this.visibleRange.end);
        if (visibleData.length === 0) return;
        
        const totalWidth = chartWidth / visibleData.length;
        const index = Math.floor((mouseX - chartLeft) / totalWidth);
        
        if (index < 0 || index >= visibleData.length) {
            this.tooltip.style.display = 'none';
            return;
        }
        
        const candle = visibleData[index];
        const stateLabel = {
            strongBull: 'Strong Bull',
            bull: 'Bull',
            neutral: 'Neutral',
            bear: 'Bear',
            strongBear: 'Strong Bear'
        };
        
        this.tooltip.innerHTML = `
            <div style="margin-bottom: 4px; color: #A4A9B3; font-size: 10px;">
                ${new Date(candle.time).toLocaleString()}
            </div>
            <div style="display: grid; grid-template-columns: auto auto; gap: 2px 12px;">
                <span style="color: #6B7280;">O</span><span>${this.formatPrice(candle.open)}</span>
                <span style="color: #6B7280;">H</span><span>${this.formatPrice(candle.high)}</span>
                <span style="color: #6B7280;">L</span><span>${this.formatPrice(candle.low)}</span>
                <span style="color: #6B7280;">C</span><span>${this.formatPrice(candle.close)}</span>
                <span style="color: #6B7280;">V</span><span>${(candle.volume / 1000).toFixed(1)}K</span>
            </div>
            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.1);">
                <span style="color: ${this.options.colors[candle.state]}; font-weight: 500;">
                    ${stateLabel[candle.state]}
                </span>
            </div>
        `;
        
        this.tooltip.style.display = 'block';
        this.tooltip.style.left = Math.min(mouseX + 15, this.width - 150) + 'px';
        this.tooltip.style.top = Math.max(mouseY - 80, 10) + 'px';
    }
    
    pan(deltaX) {
        const visibleCount = this.visibleRange.end - this.visibleRange.start;
        const candlesPerPixel = visibleCount / this.width;
        const candleDelta = Math.round(-deltaX * candlesPerPixel);
        
        let newStart = this.visibleRange.start + candleDelta;
        let newEnd = this.visibleRange.end + candleDelta;
        
        if (newStart < 0) {
            newStart = 0;
            newEnd = visibleCount;
        }
        if (newEnd > this.data.length) {
            newEnd = this.data.length;
            newStart = Math.max(0, newEnd - visibleCount);
        }
        
        this.visibleRange.start = newStart;
        this.visibleRange.end = newEnd;
        this.render();
    }
    
    onWheel(e) {
        e.preventDefault();
        
        const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
        const visibleCount = this.visibleRange.end - this.visibleRange.start;
        const newCount = Math.round(visibleCount * zoomFactor);
        
        // Limit zoom
        if (newCount < 20 || newCount > this.data.length) return;
        
        const delta = newCount - visibleCount;
        
        // Zoom towards mouse position
        const rect = this.canvas.getBoundingClientRect();
        const mouseRatio = (e.clientX - rect.left) / this.width;
        
        this.visibleRange.start = Math.max(0, this.visibleRange.start - Math.round(delta * mouseRatio));
        this.visibleRange.end = Math.min(this.data.length, this.visibleRange.start + newCount);
        
        if (this.visibleRange.end > this.data.length) {
            this.visibleRange.end = this.data.length;
            this.visibleRange.start = Math.max(0, this.visibleRange.end - newCount);
        }
        
        this.render();
    }
    
    setIndicators(indicators) {
        this.indicators = { ...this.indicators, ...indicators };
        this.render();
    }
    
    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        this.container.innerHTML = '';
    }
}

// Export
window.ApexCandlestickChart = ApexCandlestickChart;
window.ChartConfig = ChartConfig;
