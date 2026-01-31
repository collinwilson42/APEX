/**
 * MT5 Meta Agent V5 Dashboard
 * Multi-API Complex with Zone-Based Adaptive Execution
 */

// ==================== State Management ====================
const state = {
    isRunning: false,
    cycleCount: 0,
    mainValue: 50,
    baseInterval: 180,
    threshold: 10,
    currentZone: null,
    currentInterval: null,
    lowestIntervalThisCycle: null, // Track lowest interval during countdown
    countdownTimer: null,
    countdownSeconds: null,
    apis: [
        {
            id: 'claude-1',
            name: 'Claude Sonnet 4',
            value: 50,
            weight: 1.0,
            enabled: true,
            profile: 'default'
        }
    ],
    nextApiId: 2
};

// ==================== Zone Calculation ====================
/**
 * Calculate zone and interval based on position (0-100 scale)
 * Zone 0-5: baseInterval ÷ 10
 * Zone 5-10: baseInterval ÷ 9
 * ...
 * Zone 45-50: baseInterval ÷ 1 (base interval)
 * Symmetric for buy side (50-100)
 */
function calculateZoneAndInterval(value, baseInterval) {
    // Convert to distance from 50 (center)
    const distanceFromCenter = Math.abs(value - 50);
    
    // If exactly at 50, show NEUTRAL
    if (distanceFromCenter === 0) {
        return {
            zone: 'NEUTRAL',
            interval: null,
            divisor: 1
        };
    }
    
    // Determine zone (0-50 scale, where 0 is center and 50 is extreme)
    const zone = Math.floor(distanceFromCenter / 5);
    
    // Calculate divisor (10 for zone 0-5, down to 1 for zone 45-50)
    const divisor = 10 - zone;
    
    // Calculate interval (rounded to nearest second)
    const interval = Math.round(baseInterval / divisor);
    
    // Determine zone label
    const zoneStart = zone * 5;
    const zoneEnd = (zone + 1) * 5;
    const direction = value < 50 ? 'SELL' : value > 50 ? 'BUY' : 'NEUTRAL';
    const zoneLabel = `${zoneStart}-${zoneEnd} ${direction}`;
    
    return {
        zone: zoneLabel,
        interval: interval,
        divisor: divisor
    };
}

// ==================== Weighted Average Calculation ====================
function calculateWeightedAverage() {
    const enabledApis = state.apis.filter(api => api.enabled);
    
    if (enabledApis.length === 0) {
        return 50; // Default to center if no APIs enabled
    }
    
    let weightedSum = 0;
    let totalWeight = 0;
    
    enabledApis.forEach(api => {
        weightedSum += api.value * api.weight;
        totalWeight += api.weight;
    });
    
    return totalWeight > 0 ? weightedSum / totalWeight : 50;
}

// ==================== UI Update Functions ====================
function updateMainSlider() {
    const mainBar = document.getElementById('mainBar');
    const mainValue = document.getElementById('mainValue');
    
    state.mainValue = calculateWeightedAverage();
    
    // Update value display
    mainValue.textContent = state.mainValue.toFixed(1);
    
    // Update bar fill
    const percentage = Math.abs(state.mainValue - 50);
    const direction = state.mainValue >= 50 ? 'buy' : 'sell';
    
    mainBar.style.width = `${percentage}%`;
    mainBar.setAttribute('data-direction', direction);
    
    // Update zone and interval
    const zoneInfo = calculateZoneAndInterval(state.mainValue, state.baseInterval);
    state.currentZone = zoneInfo.zone;
    state.currentInterval = zoneInfo.interval;
    
    document.getElementById('currentZone').textContent = zoneInfo.zone;
    document.getElementById('currentInterval').textContent = zoneInfo.interval !== null ? zoneInfo.interval : '--';
}

function updateThresholdGates() {
    const gateSell = document.getElementById('thresholdGateSell');
    const gateBuy = document.getElementById('thresholdGateBuy');
    
    const sellPosition = ((50 - state.threshold) / 100) * 100; // Convert to percentage
    const buyPosition = ((50 + state.threshold) / 100) * 100;
    
    gateSell.style.left = `${sellPosition}%`;
    gateBuy.style.left = `${buyPosition}%`;
}

function updateApiSlider(apiId, value) {
    const api = state.apis.find(a => a.id === apiId);
    if (!api) return;
    
    api.value = value;
    
    const apiBar = document.querySelector(`[data-api-id="${apiId}"] .bar-fill`);
    const apiValue = document.getElementById(`apiValue-${apiId}`);
    
    if (apiBar && apiValue) {
        apiValue.textContent = value.toFixed(1);
        
        const percentage = Math.abs(value - 50);
        const direction = value >= 50 ? 'buy' : 'sell';
        
        apiBar.style.width = `${percentage}%`;
        apiBar.setAttribute('data-direction', direction);
    }
    
    // Recalculate main slider
    updateMainSlider();
}

// ==================== Countdown Timer ====================
function startCountdown() {
    if (state.countdownTimer) {
        clearInterval(state.countdownTimer);
    }
    
    state.countdownSeconds = state.currentInterval;
    state.lowestIntervalThisCycle = state.currentInterval; // Track lowest interval
    
    state.countdownTimer = setInterval(() => {
        if (state.countdownSeconds <= 0) {
            executeDecision();
            // Reset countdown with current zone's interval
            const zoneInfo = calculateZoneAndInterval(state.mainValue, state.baseInterval);
            state.currentInterval = zoneInfo.interval;
            state.countdownSeconds = state.currentInterval;
            state.lowestIntervalThisCycle = state.currentInterval;
        } else {
            state.countdownSeconds--;
        }
        
        updateCountdownDisplay();
        
        // Check if zone changed during countdown
        const newZoneInfo = calculateZoneAndInterval(state.mainValue, state.baseInterval);
        
        // If we encounter a lower interval, lock it in for this cycle
        if (newZoneInfo.interval < state.lowestIntervalThisCycle) {
            state.lowestIntervalThisCycle = newZoneInfo.interval;
            // Adjust countdown if current countdown is longer than new lowest
            if (state.countdownSeconds > state.lowestIntervalThisCycle) {
                state.countdownSeconds = state.lowestIntervalThisCycle;
            }
        }
        
        // Update display with current zone info (even if not using its interval)
        state.currentZone = newZoneInfo.zone;
        state.currentInterval = state.lowestIntervalThisCycle; // Display the locked-in interval
        document.getElementById('currentZone').textContent = newZoneInfo.zone;
        document.getElementById('currentInterval').textContent = state.lowestIntervalThisCycle;
    }, 1000);
}

function stopCountdown() {
    if (state.countdownTimer) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
    }
    document.getElementById('executionCountdown').textContent = '--';
}

function updateCountdownDisplay() {
    const countdownEl = document.getElementById('executionCountdown');
    const seconds = state.countdownSeconds;
    
    if (seconds !== null) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        countdownEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// ==================== Decision Execution ====================
function executeDecision() {
    state.cycleCount++;
    document.getElementById('cycleCount').textContent = state.cycleCount;
    
    const action = determineAction(state.mainValue, state.threshold);
    
    console.log(`[Cycle ${state.cycleCount}] Position: ${state.mainValue.toFixed(1)}, Action: ${action}, Zone: ${state.currentZone}`);
    
    // Update execution history table
    addExecutionToHistory({
        time: new Date().toLocaleTimeString(),
        action: action,
        position: state.mainValue.toFixed(1),
        zone: state.currentZone,
        interval: state.currentInterval,
        apisActive: state.apis.filter(a => a.enabled).length
    });
    
    // TODO: Send to backend via SocketIO
    // socket.emit('execute_decision', { action, position: state.mainValue });
}

function determineAction(value, threshold) {
    const sellGate = 50 - threshold;
    const buyGate = 50 + threshold;
    
    if (value < sellGate) {
        return 'SELL';
    } else if (value > buyGate) {
        return 'BUY';
    } else {
        return 'HOLD';
    }
}

function addExecutionToHistory(execution) {
    const tbody = document.getElementById('decisionsTableBody');
    
    // Remove "no data" row if present
    if (tbody.querySelector('.no-data')) {
        tbody.innerHTML = '';
    }
    
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${execution.time}</td>
        <td class="action-${execution.action.toLowerCase()}">${execution.action}</td>
        <td>${execution.position}</td>
        <td>${execution.zone}</td>
        <td>${execution.interval}s</td>
        <td>${execution.apisActive}</td>
        <td class="executed-${execution.action !== 'HOLD' ? 'yes' : 'no'}">${execution.action !== 'HOLD' ? 'Yes' : 'No'}</td>
    `;
    
    // Add to top
    tbody.insertBefore(row, tbody.firstChild);
    
    // Keep only last 20 rows
    while (tbody.children.length > 20) {
        tbody.removeChild(tbody.lastChild);
    }
}

// ==================== API Management ====================
function addNewApi(name, profile) {
    const apiId = `api-${state.nextApiId++}`;
    
    const newApi = {
        id: apiId,
        name: name,
        value: 50,
        weight: 1.0,
        enabled: true,
        profile: profile
    };
    
    state.apis.push(newApi);
    renderApiSlider(newApi);
    updateMainSlider();
}

function removeApi(apiId) {
    const index = state.apis.findIndex(a => a.id === apiId);
    if (index > -1) {
        state.apis.splice(index, 1);
        document.querySelector(`[data-api-id="${apiId}"]`).remove();
        updateMainSlider();
    }
}

function renderApiSlider(api) {
    const container = document.getElementById('apiSlidersList');
    
    const row = document.createElement('div');
    row.className = 'api-slider-row';
    row.setAttribute('data-api-id', api.id);
    
    row.innerHTML = `
        <div class="api-slider-left">
            <div class="api-name-row">
                <input type="text" class="api-name-input" value="${api.name}">
                <button class="btn-remove-api" title="Remove API">×</button>
            </div>
            <div class="conf-bar-label">
                <span class="api-label">CONFIDENCE</span>
                <span class="api-value" id="apiValue-${api.id}">50</span>
            </div>
            <div class="bidirectional-bar api-bar">
                <div class="bar-track">
                    <div class="bar-center-line"></div>
                    <div class="bar-fill bar-api" data-value="50"></div>
                </div>
            </div>
        </div>
        <div class="api-slider-right">
            <div class="api-config">
                <div class="config-item">
                    <label>Profile</label>
                    <select class="profile-select">
                        <option value="default" ${api.profile === 'default' ? 'selected' : ''}>Default Analysis</option>
                    </select>
                </div>
                <div class="config-item">
                    <label>Weight</label>
                    <input type="number" class="weight-input" value="${api.weight}" step="0.1" min="0">
                </div>
                <div class="config-item">
                    <label>Status</label>
                    <div class="toggle-switch">
                        <input type="checkbox" id="toggle-${api.id}" ${api.enabled ? 'checked' : ''}>
                        <label for="toggle-${api.id}" class="toggle-label"></label>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(row);
    
    // Attach event listeners
    row.querySelector('.btn-remove-api').addEventListener('click', () => removeApi(api.id));
    
    row.querySelector('.weight-input').addEventListener('change', (e) => {
        const api = state.apis.find(a => a.id === api.id);
        if (api) {
            api.weight = parseFloat(e.target.value);
            updateMainSlider();
        }
    });
    
    row.querySelector(`#toggle-${api.id}`).addEventListener('change', (e) => {
        const api = state.apis.find(a => a.id === api.id);
        if (api) {
            api.enabled = e.target.checked;
            updateMainSlider();
        }
    });
}

// ==================== Event Listeners ====================
document.addEventListener('DOMContentLoaded', () => {
    // Menu toggle
    document.getElementById('menuToggle').addEventListener('click', () => {
        const menu = document.getElementById('dropdownMenu');
        menu.classList.toggle('show');
    });
    
    // Start/Stop agent
    document.getElementById('toggleAgent').addEventListener('click', () => {
        state.isRunning = !state.isRunning;
        
        const btn = document.getElementById('toggleAgent');
        const status = document.getElementById('agentStatus');
        
        if (state.isRunning) {
            btn.textContent = 'STOP AGENT';
            btn.classList.add('btn-secondary');
            btn.classList.remove('btn-primary');
            status.classList.add('running');
            startCountdown();
        } else {
            btn.textContent = 'START AGENT';
            btn.classList.add('btn-primary');
            btn.classList.remove('btn-secondary');
            status.classList.remove('running');
            stopCountdown();
        }
    });
    
    // Settings changes
    document.getElementById('settingBaseInterval').addEventListener('change', (e) => {
        state.baseInterval = parseInt(e.target.value);
        updateMainSlider();
    });
    
    document.getElementById('settingThreshold').addEventListener('change', (e) => {
        state.threshold = parseInt(e.target.value);
        updateThresholdGates();
    });
    
    // Add new API button
    document.getElementById('addApiSection').addEventListener('click', () => {
        document.getElementById('profileModal').classList.add('show');
    });
    
    // Modal controls
    document.querySelector('.modal-close').addEventListener('click', () => {
        document.getElementById('profileModal').classList.remove('show');
    });
    
    document.getElementById('cancelNewApi').addEventListener('click', () => {
        document.getElementById('profileModal').classList.remove('show');
    });
    
    document.getElementById('confirmNewApi').addEventListener('click', () => {
        const name = document.getElementById('newApiName').value;
        const profile = document.getElementById('newApiProfile').value;
        
        if (name && profile && profile !== '') {
            addNewApi(name, profile);
            document.getElementById('profileModal').classList.remove('show');
            document.getElementById('newApiName').value = '';
            document.getElementById('newApiProfile').value = '';
        } else {
            alert('Please enter an API name and select a profile');
        }
    });
    
    // Initialize UI
    updateMainSlider();
    updateThresholdGates();
    
    // Simulate API value changes for demo (remove in production)
    if (false) { // Set to true for demo mode
        setInterval(() => {
            const randomApi = state.apis[Math.floor(Math.random() * state.apis.length)];
            if (randomApi && randomApi.enabled) {
                const newValue = Math.max(0, Math.min(100, randomApi.value + (Math.random() - 0.5) * 10));
                updateApiSlider(randomApi.id, newValue);
            }
        }, 3000);
    }
});

// ==================== SocketIO (for future implementation) ====================
/*
const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
    document.getElementById('connectionStatus').textContent = 'CONNECTED';
    document.getElementById('connectionStatus').classList.remove('conn-disconnected');
    document.getElementById('connectionStatus').classList.add('conn-connected');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    document.getElementById('connectionStatus').textContent = 'DISCONNECTED';
    document.getElementById('connectionStatus').classList.remove('conn-connected');
    document.getElementById('connectionStatus').classList.add('conn-disconnected');
});

socket.on('api_update', (data) => {
    updateApiSlider(data.api_id, data.value);
});

socket.on('stats_update', (stats) => {
    document.getElementById('statDecisions').textContent = stats.total_decisions;
    document.getElementById('statSuccess').textContent = stats.successful_trades;
    document.getElementById('statFailed').textContent = stats.failed_trades;
    document.getElementById('statAvgConf').textContent = stats.avg_confidence;
});
*/
