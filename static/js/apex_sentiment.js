/* ═══════════════════════════════════════════════════════════════════════════
   APEX SENTIMENT PANEL - Overlay Component for Transition Matrix
   
   Displays AI sentiment analysis with 5 narrative categories:
   1. Price Action - What is price doing?
   2. Key Levels - What's above and below?
   3. Momentum - Strengthening or weakening?
   4. Volume Story - What's participation saying?
   5. Structure - What pattern is forming?
   
   Activated by double-clicking ACTIVE button in control panel.
   Shows for 30 seconds then transitions back to matrix view.
   ═══════════════════════════════════════════════════════════════════════════ */

const ApexSentiment = {
    // State
    isRunning: false,
    isMockMode: true,
    currentSymbol: 'XAUJ26',
    currentReading: null,
    displayTimeout: null,
    
    // Scheduling
    scheduleInterval: null,
    lastRun15m: null,
    lastRun1m: null,
    
    // Config
    config: {
        displayDuration: 30000, // 30 seconds
        tf15mOffsets: [1, 16, 31, 46], // Minutes after hour for 15m analysis
        tf1mInterval: 1, // Run 1m analysis every N minutes
        replaySpeedMultiplier: 1
    },
    
    // DOM references
    containers: {
        '1m': null,
        '15m': null
    },
    
    // Category metadata
    categories: [
        { key: 'price_action', label: 'Price Action', icon: '◆' },
        { key: 'key_levels', label: 'Key Levels', icon: '═' },
        { key: 'momentum', label: 'Momentum', icon: '↗' },
        { key: 'volume_story', label: 'Volume', icon: '▊' },
        { key: 'structure', label: 'Structure', icon: '◫' }
    ],
    
    // ═══════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════
    
    init() {
        // Listen for replay speed changes
        window.addEventListener('apex-replay-speed', (e) => {
            this.config.replaySpeedMultiplier = e.detail.speed || 1;
        });
        
        console.log('[ApexSentiment] Initialized - waiting for activation');
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // ENGINE CONTROL
    // ═══════════════════════════════════════════════════════════════════════
    
    startEngine(symbol, mockMode = true) {
        if (this.isRunning) {
            console.log('[ApexSentiment] Already running');
            return;
        }
        
        this.isRunning = true;
        this.isMockMode = mockMode;
        this.currentSymbol = symbol || 'XAUJ26';
        
        console.log(`[ApexSentiment] Engine STARTED - Symbol: ${this.currentSymbol}, Mock: ${this.isMockMode}`);
        
        // Start the scheduler
        this.startScheduler();
        
        // Run immediately for both timeframes to show something
        this.runAnalysis('15m');
        setTimeout(() => this.runAnalysis('1m'), 500);
    },
    
    stopEngine() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        this.stopScheduler();
        
        // Hide any visible sentiment panels
        this.hideSentiment('1m');
        this.hideSentiment('15m');
        
        console.log('[ApexSentiment] Engine STOPPED');
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // SCHEDULER
    // ═══════════════════════════════════════════════════════════════════════
    
    startScheduler() {
        if (this.scheduleInterval) clearInterval(this.scheduleInterval);
        
        // Check every 5 seconds for schedule triggers
        this.scheduleInterval = setInterval(() => {
            this.checkSchedule();
        }, 5000);
        
        console.log('[ApexSentiment] Scheduler started');
    },
    
    stopScheduler() {
        if (this.scheduleInterval) {
            clearInterval(this.scheduleInterval);
            this.scheduleInterval = null;
        }
        
        if (this.displayTimeout) {
            clearTimeout(this.displayTimeout);
            this.displayTimeout = null;
        }
    },
    
    checkSchedule() {
        if (!this.isRunning) return;
        
        const now = new Date();
        const minute = now.getMinutes();
        const second = now.getSeconds();
        
        // Only trigger at the start of the minute (first 10 seconds)
        if (second > 10) return;
        
        // Check 15m schedule (X:01, X:16, X:31, X:46)
        if (this.config.tf15mOffsets.includes(minute)) {
            const key15m = `${now.getHours()}-${minute}`;
            if (this.lastRun15m !== key15m) {
                this.lastRun15m = key15m;
                console.log(`[ApexSentiment] 15m trigger at ${now.toLocaleTimeString()}`);
                this.runAnalysis('15m');
            }
        }
        
        // Check 1m schedule (every minute or every N minutes based on config)
        if (minute % this.config.tf1mInterval === 0) {
            const key1m = `${now.getHours()}-${minute}`;
            if (this.lastRun1m !== key1m) {
                this.lastRun1m = key1m;
                console.log(`[ApexSentiment] 1m trigger at ${now.toLocaleTimeString()}`);
                this.runAnalysis('1m');
            }
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // ANALYSIS
    // ═══════════════════════════════════════════════════════════════════════
    
    async runAnalysis(timeframe) {
        if (!this.isRunning) return;
        
        let reading;
        
        if (this.isMockMode) {
            reading = this.generateMockReading(timeframe);
        } else {
            // Call backend API
            try {
                const response = await fetch('/api/sentiment/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        symbol: this.currentSymbol, 
                        timeframe: timeframe 
                    })
                });
                
                const result = await response.json();
                if (result.success && result.data) {
                    reading = result.data;
                } else {
                    console.warn('[ApexSentiment] API returned no data, using mock');
                    reading = this.generateMockReading(timeframe);
                }
            } catch (e) {
                console.warn('[ApexSentiment] API call failed, using mock:', e);
                reading = this.generateMockReading(timeframe);
            }
        }
        
        // Display the sentiment
        this.showSentiment(timeframe, reading);
    },
    
    generateMockReading(timeframe) {
        const now = new Date();
        const price = (2780 + Math.random() * 20).toFixed(0);
        const ema21 = (parseFloat(price) - 10 - Math.random() * 5).toFixed(0);
        const ema50 = (parseFloat(price) - 20 - Math.random() * 10).toFixed(0);
        const bbUpper = (parseFloat(price) + 8 + Math.random() * 5).toFixed(0);
        const bbLower = (parseFloat(price) - 15 - Math.random() * 5).toFixed(0);
        
        // Randomly choose a market scenario
        const scenarios = [
            {
                price_action: `Price testing upper resistance around ${price}, showing hesitation with smaller bodied candles. Recent push was impulsive but now stalling at this level with potential for rejection.`,
                key_levels: `EMA 21 at ${ema21} providing dynamic support. Upper Bollinger band at ${bbUpper}. Key horizontal resistance at ${price}-${parseInt(price)+10} zone formed by previous swing highs.`,
                momentum: `Candles getting progressively smaller on the push up - classic momentum fade pattern. Watching for either volume confirmation or reversal signal.`,
                volume_story: `Volume declining on last 3-4 bars despite price holding highs. This divergence often precedes a pullback to test support.`,
                structure: `Potential distribution forming at resistance. If ${ema21} breaks, next support at ${bbLower}. Compression building for directional move.`,
                summary: `Bullish structure but momentum fading at resistance. Watch for volume spike above ${parseInt(price)+10} or rejection back to ${ema21}.`
            },
            {
                price_action: `Strong bullish candles breaking above ${ema21} with follow-through. Price accelerating away from the moving averages with clean higher highs and higher lows.`,
                key_levels: `Just cleared resistance at ${ema21}, now acting as support. Next resistance at ${bbUpper}. EMA 50 at ${ema50} well below providing backstop.`,
                momentum: `Candles expanding in size with each push higher - acceleration phase. Momentum indicators confirming with no divergences visible.`,
                volume_story: `Volume expanding on up moves, contracting on pullbacks. Classic accumulation pattern with strong participation on breakouts.`,
                structure: `Trending structure established. Higher timeframe bias bullish. Pullbacks to ${ema21} are buying opportunities until structure breaks.`,
                summary: `Strong uptrend in impulse phase. Buy dips to ${ema21}, target ${bbUpper}. Only concern is potential exhaustion if volume drops.`
            },
            {
                price_action: `Choppy price action with overlapping candles. Neither bulls nor bears in control. Price oscillating between ${bbLower} and ${ema21} without conviction.`,
                key_levels: `Range bound between ${bbLower} support and ${ema21} resistance. Multiple tests of both levels with no clean break. EMA 50 flat at ${ema50}.`,
                momentum: `Momentum indicators flatlining around neutral. No clear directional bias. Candles mixed with no consistent pattern.`,
                volume_story: `Volume below average and declining. Market waiting for catalyst. Neither buyers nor sellers stepping up with size.`,
                structure: `Consolidation/range structure. Expect expansion soon but direction unclear. Watch for volume spike to signal breakout direction.`,
                summary: `Range-bound chop - avoid trading middle. Wait for clean break of ${bbLower} or ${ema21} with volume confirmation before taking position.`
            },
            {
                price_action: `Bearish rejection candle forming at ${ema21} resistance. Previous attempt failed at same level. Price showing weakness with lower highs.`,
                key_levels: `Rejected at EMA 21 (${ema21}) for second time. Support at ${bbLower}, break targets ${parseInt(bbLower)-15}. Resistance overhead at ${bbUpper} increasingly distant.`,
                momentum: `Momentum rolling over from overbought. Each rally attempt weaker than prior. Distribution pattern forming on multiple timeframes.`,
                volume_story: `Volume spikes on down moves, dries up on rallies. Clear seller aggression pattern. Smart money appears to be distributing.`,
                structure: `Lower high structure forming. If ${bbLower} breaks, measured move targets ${parseInt(bbLower)-20}. Rallies are selling opportunities.`,
                summary: `Bearish setup forming. Short rallies to ${ema21} with stops above ${bbUpper}. Target ${bbLower} break for continuation.`
            }
        ];
        
        const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
        
        return {
            id: Date.now(),
            timestamp: now.toISOString(),
            symbol: this.currentSymbol,
            timeframe: timeframe,
            price_action: scenario.price_action,
            key_levels: scenario.key_levels,
            momentum: scenario.momentum,
            volume_story: scenario.volume_story,
            structure: scenario.structure,
            summary: scenario.summary,
            processing_time_ms: Math.floor(100 + Math.random() * 400)
        };
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // DISPLAY LOGIC
    // ═══════════════════════════════════════════════════════════════════════
    
    showSentiment(timeframe, reading) {
        const container = document.getElementById(`matrix-${timeframe}`);
        if (!container) {
            console.warn(`[ApexSentiment] Container matrix-${timeframe} not found`);
            return;
        }
        
        // Store reference
        this.containers[timeframe] = container;
        this.currentReading = reading;
        
        // Create sentiment overlay
        const overlay = this.createSentimentOverlay(reading, timeframe);
        
        // Find or create overlay container
        let overlayContainer = container.querySelector('.sentiment-overlay');
        if (!overlayContainer) {
            overlayContainer = document.createElement('div');
            overlayContainer.className = 'sentiment-overlay';
            container.appendChild(overlayContainer);
        }
        
        // Animate in
        overlayContainer.innerHTML = '';
        overlayContainer.appendChild(overlay);
        
        // Force reflow then add visible class for animation
        overlayContainer.offsetHeight;
        overlayContainer.classList.add('sentiment-overlay--visible');
        
        // Update header title
        this.updateHeaderTitle(timeframe, true, reading);
        
        // Set timeout to hide
        const duration = this.config.displayDuration / this.config.replaySpeedMultiplier;
        
        // Clear any existing timeout for this timeframe
        if (this[`displayTimeout_${timeframe}`]) {
            clearTimeout(this[`displayTimeout_${timeframe}`]);
        }
        
        this[`displayTimeout_${timeframe}`] = setTimeout(() => {
            this.hideSentiment(timeframe);
        }, duration);
        
        console.log(`[ApexSentiment] Showing ${timeframe} sentiment for ${duration/1000}s`);
    },
    
    hideSentiment(timeframe) {
        const container = this.containers[timeframe];
        if (!container) return;
        
        const overlayContainer = container.querySelector('.sentiment-overlay');
        if (overlayContainer) {
            overlayContainer.classList.remove('sentiment-overlay--visible');
            
            // Remove after animation
            setTimeout(() => {
                if (overlayContainer.parentNode) {
                    overlayContainer.remove();
                }
            }, 300);
        }
        
        // Restore header title
        this.updateHeaderTitle(timeframe, false);
    },
    
    updateHeaderTitle(timeframe, showSentiment, reading = null) {
        const cellContainer = document.getElementById(`matrix-${timeframe}-container`);
        if (!cellContainer) return;
        
        const titleEl = cellContainer.querySelector('.trading-cell__title');
        if (!titleEl) return;
        
        if (showSentiment && reading) {
            titleEl.innerHTML = `<span class="sentiment-title-label">SENTIMENT</span> ${timeframe.toUpperCase()}`;
            titleEl.classList.add('trading-cell__title--sentiment');
        } else {
            titleEl.textContent = 'Transition Matrix';
            titleEl.classList.remove('trading-cell__title--sentiment');
        }
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // COMPONENT RENDERING
    // ═══════════════════════════════════════════════════════════════════════
    
    createSentimentOverlay(reading, timeframe) {
        const wrapper = document.createElement('div');
        wrapper.className = 'sentiment-panel';
        
        // Summary at top
        if (reading.summary) {
            const summarySection = this.createSummarySection(reading);
            wrapper.appendChild(summarySection);
        }
        
        // Five narrative categories
        const categoriesSection = this.createCategoriesSection(reading);
        wrapper.appendChild(categoriesSection);
        
        // Timestamp footer
        const footer = this.createFooter(reading);
        wrapper.appendChild(footer);
        
        return wrapper;
    },
    
    createSummarySection(reading) {
        const section = document.createElement('div');
        section.className = 'sentiment-summary';
        
        section.innerHTML = `
            <div class="sentiment-summary__text">${reading.summary || 'No summary available'}</div>
        `;
        
        return section;
    },
    
    createCategoriesSection(reading) {
        const section = document.createElement('div');
        section.className = 'sentiment-categories';
        
        this.categories.forEach(cat => {
            const text = reading[cat.key] || '';
            if (text) {
                const card = this.createCategoryCard(cat, text);
                section.appendChild(card);
            }
        });
        
        return section;
    },
    
    createCategoryCard(category, text) {
        const card = document.createElement('div');
        card.className = 'sentiment-category';
        
        card.innerHTML = `
            <div class="sentiment-category__header">
                <span class="sentiment-category__icon">${category.icon}</span>
                <span class="sentiment-category__label">${category.label}</span>
            </div>
            <div class="sentiment-category__text">${text}</div>
        `;
        
        return card;
    },
    
    createFooter(reading) {
        const footer = document.createElement('div');
        footer.className = 'sentiment-footer';
        
        const time = reading.timestamp ? new Date(reading.timestamp).toLocaleTimeString() : '--:--';
        const procTime = reading.processing_time_ms ? `${reading.processing_time_ms}ms` : '';
        const modeLabel = this.isMockMode ? '<span class="sentiment-footer__mock">MOCK</span>' : '';
        
        footer.innerHTML = `
            <span class="sentiment-footer__time">${time}</span>
            ${modeLabel}
            ${procTime ? `<span class="sentiment-footer__proc">${procTime}</span>` : ''}
        `;
        
        return footer;
    },
    
    // ═══════════════════════════════════════════════════════════════════════
    // MANUAL TRIGGER (for testing)
    // ═══════════════════════════════════════════════════════════════════════
    
    async triggerAnalysis(symbol, timeframe) {
        this.currentSymbol = symbol || this.currentSymbol;
        await this.runAnalysis(timeframe);
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ApexSentiment.init();
});

// Export
window.ApexSentiment = ApexSentiment;
