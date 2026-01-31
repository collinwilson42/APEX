// ============================================================================
// API COMPLEX - UNIFIED DECISION ENGINE JAVASCRIPT V1.0
// Module management, configuration, and screenshot integration
// ============================================================================

// API Complex State
const apiComplexState = {
    modules: {
        1: { active: true, name: 'API #1 - FREQUENCY', config: {} },
        2: { active: false, name: null, config: {} },
        3: { active: false, name: null, config: {} },
        4: { active: false, name: null, config: {} }
    },
    currentConfigModule: null,
    decisionEngine: {
        direction: 'NEUTRAL',
        confidence: 0
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[API COMPLEX] Initializing...');
    
    initAPIComplex();
    initModuleSliders();
    
    console.log('[API COMPLEX] Ready');
});

function initAPIComplex() {
    // Module 1 sliders
    const freq1Slider = document.getElementById('frequency1Slider');
    const rr1Slider = document.getElementById('riskReward1Slider');
    
    if (freq1Slider) {
        freq1Slider.addEventListener('input', function() {
            document.getElementById('frequency1Display').textContent = this.value;
            document.getElementById('frequency1Value').textContent = this.value;
            updateDecisionEngine();
        });
    }
    
    if (rr1Slider) {
        rr1Slider.addEventListener('input', function() {
            document.getElementById('riskReward1Display').textContent = this.value;
            updateDecisionEngine();
        });
    }
    
    // Execute button
    const executeBtn = document.getElementById('apiExecuteBtn');
    if (executeBtn) {
        executeBtn.addEventListener('click', executeDecision);
    }
}

function initModuleSliders() {
    // Initialize all active module sliders
    document.querySelectorAll('.module-slider').forEach(slider => {
        slider.addEventListener('input', function() {
            const displayId = this.id.replace('Slider', 'Display');
            const valueId = this.id.replace('Slider', 'Value');
            
            document.getElementById(displayId).textContent = this.value;
            if (document.getElementById(valueId)) {
                document.getElementById(valueId).textContent = this.value;
            }
            
            updateDecisionEngine();
        });
    });
}

// ============================================================================
// MODULE MANAGEMENT
// ============================================================================

function addAPIModule(moduleNum) {
    console.log(`[API COMPLEX] Adding module ${moduleNum}`);
    
    apiComplexState.currentConfigModule = moduleNum;
    
    // Open configuration modal
    document.getElementById('apiConfigTitle').textContent = `CONFIGURE API MODULE #${moduleNum}`;
    document.getElementById('apiConfigName').value = '';
    document.getElementById('apiConfigScreenshot').checked = true;
    document.getElementById('apiConfigFrequency').value = '15min';
    
    document.getElementById('apiModuleConfigModal').style.display = 'flex';
}

function closeAPIConfigModal() {
    document.getElementById('apiModuleConfigModal').style.display = 'none';
    apiComplexState.currentConfigModule = null;
}

function saveAPIModuleConfig() {
    const moduleNum = apiComplexState.currentConfigModule;
    if (!moduleNum) return;
    
    const moduleName = document.getElementById('apiConfigName').value || `API #${moduleNum}`;
    const useScreenshot = document.getElementById('apiConfigScreenshot').checked;
    const frequency = document.getElementById('apiConfigFrequency').value;
    
    // Save configuration
    apiComplexState.modules[moduleNum] = {
        active: true,
        name: moduleName,
        config: {
            useScreenshot: useScreenshot,
            frequency: frequency
        }
    };
    
    // Activate the module in UI
    activateModule(moduleNum, moduleName);
    
    // Update status
    updateAPIStatus();
    
    // Close modal
    closeAPIConfigModal();
    
    console.log(`[API COMPLEX] Module ${moduleNum} activated:`, apiComplexState.modules[moduleNum]);
}

function activateModule(moduleNum, moduleName) {
    const moduleDiv = document.getElementById(`apiModule${moduleNum}`);
    if (!moduleDiv) return;
    
    // Remove placeholder class, add active
    moduleDiv.classList.remove('placeholder');
    moduleDiv.classList.add('active');
    
    // Replace content with active module template
    moduleDiv.innerHTML = `
        <div class="module-header">
            <div class="module-title-row">
                <h4 class="module-title">${moduleName}</h4>
                <button class="module-config-btn" onclick="configureModule(${moduleNum})" title="Configure">⚙</button>
            </div>
            <span class="module-value" id="frequency${moduleNum}Value">50</span>
        </div>
        <div class="module-body">
            <div class="slider-row">
                <label class="slider-label">Frequency</label>
                <input type="range" class="module-slider" id="frequency${moduleNum}Slider" min="0" max="100" value="50">
                <span class="slider-value" id="frequency${moduleNum}Display">50</span>
            </div>
            <div class="slider-row">
                <label class="slider-label">Risk/Reward</label>
                <input type="range" class="module-slider" id="riskReward${moduleNum}Slider" min="0" max="100" value="50">
                <span class="slider-value" id="riskReward${moduleNum}Display">50</span>
            </div>
            <div class="module-status">
                <div class="status-dot active"></div>
                <span class="status-text">ACTIVE</span>
            </div>
        </div>
    `;
    
    // Re-initialize sliders for this module
    initModuleSliders();
}

function configureModule(moduleNum) {
    console.log(`[API COMPLEX] Configuring module ${moduleNum}`);
    
    apiComplexState.currentConfigModule = moduleNum;
    const module = apiComplexState.modules[moduleNum];
    
    // Pre-fill modal with existing config
    document.getElementById('apiConfigTitle').textContent = `CONFIGURE ${module.name}`;
    document.getElementById('apiConfigName').value = module.name || '';
    document.getElementById('apiConfigScreenshot').checked = module.config.useScreenshot !== false;
    document.getElementById('apiConfigFrequency').value = module.config.frequency || '15min';
    
    document.getElementById('apiModuleConfigModal').style.display = 'flex';
}

function updateAPIStatus() {
    const activeCount = Object.values(apiComplexState.modules).filter(m => m.active).length;
    document.getElementById('apiStatus').textContent = `${activeCount} ACTIVE`;
}

// ============================================================================
// DECISION ENGINE
// ============================================================================

function updateDecisionEngine() {
    // Collect values from all active modules
    const activeModules = Object.entries(apiComplexState.modules)
        .filter(([num, mod]) => mod.active);
    
    if (activeModules.length === 0) {
        apiComplexState.decisionEngine.direction = 'NEUTRAL';
        apiComplexState.decisionEngine.confidence = 0;
    } else {
        // Calculate weighted average
        let totalFreq = 0;
        let totalRR = 0;
        
        activeModules.forEach(([num]) => {
            const freqSlider = document.getElementById(`frequency${num}Slider`);
            const rrSlider = document.getElementById(`riskReward${num}Slider`);
            
            if (freqSlider) totalFreq += parseInt(freqSlider.value);
            if (rrSlider) totalRR += parseInt(rrSlider.value);
        });
        
        const avgFreq = totalFreq / activeModules.length;
        const avgRR = totalRR / activeModules.length;
        
        // Determine direction
        if (avgFreq > 60) {
            apiComplexState.decisionEngine.direction = 'BULLISH';
        } else if (avgFreq < 40) {
            apiComplexState.decisionEngine.direction = 'BEARISH';
        } else {
            apiComplexState.decisionEngine.direction = 'NEUTRAL';
        }
        
        // Calculate confidence (0-100)
        apiComplexState.decisionEngine.confidence = Math.round((avgFreq + avgRR) / 2);
    }
    
    // Update UI
    updateDecisionUI();
}

function updateDecisionUI() {
    const { direction, confidence } = apiComplexState.decisionEngine;
    
    document.getElementById('apiDecisionValue').textContent = direction;
    document.getElementById('apiConfidenceText').textContent = `${confidence}%`;
    document.getElementById('apiConfidenceFill').style.width = `${confidence}%`;
    
    // Color based on direction
    const valueEl = document.getElementById('apiDecisionValue');
    if (direction === 'BULLISH') {
        valueEl.style.color = '#5cb85c';
    } else if (direction === 'BEARISH') {
        valueEl.style.color = '#ef4444';
    } else {
        valueEl.style.color = '#F2F3F4';
    }
}

async function executeDecision() {
    console.log('[API COMPLEX] Executing decision...', apiComplexState.decisionEngine);
    
    const btn = document.getElementById('apiExecuteBtn');
    btn.disabled = true;
    btn.innerHTML = '<span>EXECUTING...</span>';
    
    try {
        // Gather all active module configurations
        const activeModules = Object.entries(apiComplexState.modules)
            .filter(([num, mod]) => mod.active)
            .map(([num, mod]) => ({
                module: num,
                name: mod.name,
                frequency: parseInt(document.getElementById(`frequency${num}Slider`)?.value || 50),
                riskReward: parseInt(document.getElementById(`riskReward${num}Slider`)?.value || 50),
                useScreenshot: mod.config.useScreenshot
            }));
        
        // Call API to execute
        const response = await fetch('/api/complex/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                decision: apiComplexState.decisionEngine,
                modules: activeModules
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('[API COMPLEX] Execution successful:', data);
            showNotification('Decision executed successfully', 'success');
        } else {
            throw new Error(data.error || 'Execution failed');
        }
        
    } catch (error) {
        console.error('[API COMPLEX] Execution error:', error);
        showNotification(`Execution failed: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>EXECUTE</span>';
    }
}

// ============================================================================
// SCREENSHOT INTEGRATION
// ============================================================================

async function analyzeScreenshot(moduleNum) {
    console.log(`[API COMPLEX] Analyzing screenshot for module ${moduleNum}`);
    
    try {
        const response = await fetch('/api/vision/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                module: moduleNum,
                config: apiComplexState.modules[moduleNum].config
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`[API COMPLEX] Vision analysis complete for module ${moduleNum}:`, data.analysis);
            return data.analysis;
        } else {
            throw new Error(data.error || 'Vision analysis failed');
        }
        
    } catch (error) {
        console.error(`[API COMPLEX] Vision analysis error for module ${moduleNum}:`, error);
        return null;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // TODO: Add visual notification system
}

// ============================================================================
// END OF API COMPLEX JAVASCRIPT
// ============================================================================
