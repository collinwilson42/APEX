/* ═══════════════════════════════════════════════════════════════════════════
   APEX MARKOV V1 - Family D: Markov Matrix Visualization
   5x5 transition matrices, probability heatmaps, state flow diagrams
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Markov State Labels
 */
const MARKOV_STATES = [
    { id: 0, name: 'Strong Bull', short: 'SB', color: '#ADEBB3' },
    { id: 1, name: 'Bull', short: 'B', color: '#46B4AF' },
    { id: 2, name: 'Neutral', short: 'N', color: '#A4A9B3' },
    { id: 3, name: 'Bear', short: 'BR', color: '#3A5F8A' },
    { id: 4, name: 'Strong Bear', short: 'SBR', color: '#5A7EA8' }  // Steel blue - more visible
];

/**
 * APEX Markov Matrix Visualizer
 * Renders 5x5 transition probability matrices as heatmaps
 */
class ApexMarkovMatrix {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;
        
        this.options = {
            cellWidth: options.cellWidth || options.cellSize || 42,
            cellHeight: options.cellHeight || options.cellSize || 28,
            labelWidth: options.labelWidth || 40,
            showValues: options.showValues !== false,
            showLabels: options.showLabels !== false,
            animated: options.animated !== false,
            colorScale: options.colorScale || 'probability',
            compact: options.compact || false,
            ...options
        };
        
        this.matrix = null;
        this.currentState = null;
        
        this.setupDOM();
    }
    
    setupDOM() {
        this.container.innerHTML = '';
        this.container.classList.add('markov-matrix-container');
        
        // Create wrapper with centering
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'markov-matrix';
        this.wrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
        `;
        this.container.appendChild(this.wrapper);
    }
    
    /**
     * Set matrix data
     * @param {Array<Array<number>>} matrix - 5x5 transition probability matrix
     * @param {number} currentState - Current state index (0-4) for highlighting
     */
    setData(matrix, currentState = null) {
        this.matrix = matrix;
        this.currentState = currentState;
        this.render();
    }
    
    render() {
        if (!this.matrix) return;
        
        // Calculate responsive cell sizes based on container
        const containerWidth = this.container.clientWidth || 280;
        const containerHeight = this.container.clientHeight || 200;
        
        // Calculate optimal cell dimensions to fit container while staying centered
        const showLabels = this.options.showLabels;
        const gap = 2;
        const numCols = showLabels ? 6 : 5; // 5 data cols + optional label col
        const numRows = showLabels ? 6 : 5; // 5 data rows + optional header row
        const headerHeight = showLabels ? 20 : 0;
        const labelWidth = showLabels ? Math.min(this.options.labelWidth, 40) : 0;
        
        // Calculate available space for cells
        const availableWidth = containerWidth - labelWidth - (numCols * gap) - 20; // 20px padding
        const availableHeight = containerHeight - headerHeight - (numRows * gap) - 20;
        
        // Calculate cell size to fit, with max limits from options
        const maxCellWidth = this.options.cellWidth || 42;
        const maxCellHeight = this.options.cellHeight || 28;
        const cellWidth = Math.min(maxCellWidth, Math.floor(availableWidth / 5));
        const cellHeight = Math.min(maxCellHeight, Math.floor(availableHeight / 5));
        
        const { showValues } = this.options;
        
        this.wrapper.innerHTML = '';
        
        // Create grid with centering
        const grid = document.createElement('div');
        grid.className = 'markov-grid';
        grid.style.cssText = `
            display: grid;
            grid-template-columns: ${showLabels ? labelWidth + 'px' : ''} repeat(5, ${cellWidth}px);
            grid-template-rows: ${showLabels ? '20px' : ''} repeat(5, ${cellHeight}px);
            gap: ${gap}px;
            font-family: var(--font-mono, 'JetBrains Mono', monospace);
            margin: auto;
        `;
        
        // Column headers (To State)
        if (showLabels) {
            // Empty corner cell - no From/To text
            const corner = document.createElement('div');
            corner.className = 'markov-corner';
            corner.style.cssText = `
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 9px;
                color: var(--color-text-disabled, #5A5F6A);
            `;
            // Leave corner empty - cleaner look
            grid.appendChild(corner);
            
            // Column labels
            MARKOV_STATES.forEach(state => {
                const label = document.createElement('div');
                label.className = 'markov-col-label';
                label.style.cssText = `
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 10px;
                    font-weight: 600;
                    color: ${state.color};
                `;
                label.textContent = state.short;
                label.title = state.name;
                grid.appendChild(label);
            });
        }
        
        // Rows
        this.matrix.forEach((row, fromState) => {
            // Row label (From State)
            if (showLabels) {
                const label = document.createElement('div');
                label.className = 'markov-row-label';
                const stateInfo = MARKOV_STATES[fromState];
                label.style.cssText = `
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    padding-right: 8px;
                    font-size: 10px;
                    font-weight: 600;
                    color: ${stateInfo.color};
                    ${this.currentState === fromState ? 'background: rgba(255,255,255,0.05); border-radius: 4px;' : ''}
                `;
                label.textContent = stateInfo.short;
                label.title = stateInfo.name;
                grid.appendChild(label);
            }
            
            // Cells
            row.forEach((probability, toState) => {
                const cell = this.createCell(probability, fromState, toState, cellWidth, cellHeight);
                grid.appendChild(cell);
            });
        });
        
        this.wrapper.appendChild(grid);
        
        // Add legend
        if (this.options.showLegend !== false) {
            this.addLegend();
        }
    }
    
    createCell(probability, fromState, toState, cellWidth, cellHeight) {
        const { showValues, animated } = this.options;
        
        const cell = document.createElement('div');
        cell.className = 'markov-cell';
        
        // Calculate color intensity
        const intensity = this.calculateIntensity(probability);
        const bgColor = this.getColor(probability, fromState, toState);
        
        // Highlight current state row/column
        const isCurrentRow = this.currentState === fromState;
        const isCurrentCol = this.currentState === toState;
        const isDiagonal = fromState === toState;
        
        cell.style.cssText = `
            width: ${cellWidth}px;
            height: ${cellHeight}px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: ${bgColor};
            border-radius: 4px;
            font-size: 9px;
            font-weight: 500;
            color: ${intensity > 0.5 ? '#1C1E22' : '#F2F4F7'};
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            position: relative;
            ${isDiagonal ? 'border: 1px solid rgba(255,255,255,0.15);' : ''}
            ${isCurrentRow || isCurrentCol ? 'box-shadow: inset 0 0 0 1px rgba(173, 235, 179, 0.3);' : ''}
        `;
        
        if (showValues) {
            cell.textContent = (probability * 100).toFixed(0) + '%';
        }
        
        // Hover effect
        cell.addEventListener('mouseenter', () => {
            cell.style.transform = 'scale(1.1)';
            cell.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
            cell.style.zIndex = '10';
            this.showTooltip(cell, probability, fromState, toState);
        });
        
        cell.addEventListener('mouseleave', () => {
            cell.style.transform = 'scale(1)';
            cell.style.boxShadow = isCurrentRow || isCurrentCol 
                ? 'inset 0 0 0 2px rgba(173, 235, 179, 0.3)' 
                : 'none';
            cell.style.zIndex = '1';
            this.hideTooltip();
        });
        
        // Animation on load
        if (animated) {
            cell.style.opacity = '0';
            cell.style.transform = 'scale(0.8)';
            setTimeout(() => {
                cell.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                cell.style.opacity = '1';
                cell.style.transform = 'scale(1)';
            }, (fromState * 5 + toState) * 30);
        }
        
        return cell;
    }
    
    calculateIntensity(probability) {
        // Non-linear scaling to make differences more visible
        return Math.pow(probability, 0.7);
    }
    
    getColor(probability, fromState, toState) {
        const intensity = this.calculateIntensity(probability);
        
        if (this.options.colorScale === 'divergence') {
            // Divergence from expected (0.2 for 5 states)
            const expected = 0.2;
            const divergence = probability - expected;
            
            if (divergence > 0) {
                // Above expected - mint/teal
                const alpha = Math.min(1, divergence * 3);
                return `rgba(173, 235, 179, ${0.2 + alpha * 0.6})`;
            } else {
                // Below expected - steel blue
                const alpha = Math.min(1, Math.abs(divergence) * 3);
                return `rgba(58, 95, 138, ${0.2 + alpha * 0.4})`;
            }
        }
        
        // Default probability scale
        // Mix from dark base to state color based on probability
        const stateColor = MARKOV_STATES[toState].color;
        return this.mixColors('#1C1E22', stateColor, intensity);
    }
    
    mixColors(color1, color2, ratio) {
        const hex = (c) => parseInt(c.slice(1), 16);
        const r = (h) => (h >> 16) & 255;
        const g = (h) => (h >> 8) & 255;
        const b = (h) => h & 255;
        
        const h1 = hex(color1);
        const h2 = hex(color2);
        
        const mixR = Math.round(r(h1) + (r(h2) - r(h1)) * ratio);
        const mixG = Math.round(g(h1) + (g(h2) - g(h1)) * ratio);
        const mixB = Math.round(b(h1) + (b(h2) - b(h1)) * ratio);
        
        return `rgb(${mixR}, ${mixG}, ${mixB})`;
    }
    
    showTooltip(cell, probability, fromState, toState) {
        // Remove existing tooltip
        this.hideTooltip();
        
        const tooltip = document.createElement('div');
        tooltip.className = 'markov-tooltip';
        tooltip.style.cssText = `
            position: fixed;
            background: rgba(28, 30, 34, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            color: #F2F4F7;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
            max-width: 200px;
        `;
        
        const fromInfo = MARKOV_STATES[fromState];
        const toInfo = MARKOV_STATES[toState];
        
        tooltip.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="color: ${fromInfo.color}; font-weight: 600;">${fromInfo.name}</span>
                <span style="color: #6B7280;">→</span>
                <span style="color: ${toInfo.color}; font-weight: 600;">${toInfo.name}</span>
            </div>
            <div style="font-size: 20px; font-weight: 700; color: #ADEBB3;">
                ${(probability * 100).toFixed(1)}%
            </div>
            <div style="font-size: 10px; color: #6B7280; margin-top: 4px;">
                Transition Probability
            </div>
        `;
        
        document.body.appendChild(tooltip);
        
        // Position tooltip
        const rect = cell.getBoundingClientRect();
        tooltip.style.left = rect.right + 10 + 'px';
        tooltip.style.top = rect.top + 'px';
        
        // Adjust if off-screen
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.right > window.innerWidth) {
            tooltip.style.left = rect.left - tooltipRect.width - 10 + 'px';
        }
        
        this.tooltip = tooltip;
    }
    
    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.remove();
            this.tooltip = null;
        }
    }
    
    addLegend() {
        const legend = document.createElement('div');
        legend.className = 'markov-legend';
        legend.style.cssText = `
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-top: 12px;
            font-size: 10px;
            color: var(--color-text-secondary, #A4A9B3);
        `;
        
        // Probability scale
        const scale = document.createElement('div');
        scale.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        
        scale.innerHTML = `
            <span>0%</span>
            <div style="
                width: 100px;
                height: 8px;
                border-radius: 4px;
                background: linear-gradient(to right, 
                    #1C1E22 0%, 
                    #46B4AF 50%, 
                    #ADEBB3 100%
                );
            "></div>
            <span>100%</span>
        `;
        
        legend.appendChild(scale);
        this.wrapper.appendChild(legend);
    }
    
    /**
     * Animate transition from one state to another
     */
    animateTransition(fromState, toState) {
        const cells = this.wrapper.querySelectorAll('.markov-cell');
        const targetIndex = fromState * 5 + toState;
        
        cells.forEach((cell, i) => {
            if (i === targetIndex) {
                cell.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
                cell.style.transform = 'scale(1.2)';
                cell.style.boxShadow = '0 0 20px rgba(173, 235, 179, 0.5)';
                
                setTimeout(() => {
                    cell.style.transform = 'scale(1)';
                    cell.style.boxShadow = '';
                }, 500);
            }
        });
        
        this.currentState = toState;
    }
    
    destroy() {
        this.hideTooltip();
        this.container.innerHTML = '';
    }
}

/**
 * APEX Markov State Flow Diagram
 * Circular layout showing state transitions
 */
class ApexMarkovFlow {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;
        
        this.options = {
            radius: options.radius || 100,
            nodeRadius: options.nodeRadius || 24,
            showProbabilities: options.showProbabilities !== false,
            minArrowThreshold: options.minArrowThreshold || 0.05,
            ...options
        };
        
        this.matrix = null;
        this.currentState = null;
        this.svg = null;
        
        this.setupDOM();
    }
    
    setupDOM() {
        this.container.innerHTML = '';
        
        const size = (this.options.radius + this.options.nodeRadius) * 2 + 40;
        
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', size);
        this.svg.setAttribute('height', size);
        this.svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
        this.svg.style.cssText = 'display: block; margin: auto;';
        
        // Defs for arrow markers
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                    refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-text-disabled, #5A5F6A)" />
            </marker>
        `;
        this.svg.appendChild(defs);
        
        this.container.appendChild(this.svg);
    }
    
    setData(matrix, currentState = null) {
        this.matrix = matrix;
        this.currentState = currentState;
        this.render();
    }
    
    render() {
        if (!this.matrix || !this.svg) return;
        
        // Clear previous content (except defs)
        Array.from(this.svg.children).forEach(child => {
            if (child.tagName !== 'defs') child.remove();
        });
        
        const { radius, nodeRadius, minArrowThreshold } = this.options;
        const center = radius + nodeRadius + 20;
        
        // Calculate node positions (pentagon layout)
        const positions = MARKOV_STATES.map((_, i) => {
            const angle = (i / 5) * Math.PI * 2 - Math.PI / 2; // Start from top
            return {
                x: center + radius * Math.cos(angle),
                y: center + radius * Math.sin(angle)
            };
        });
        
        // Draw arrows first (so nodes appear on top)
        const arrowsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        this.matrix.forEach((row, fromState) => {
            row.forEach((prob, toState) => {
                if (fromState === toState || prob < minArrowThreshold) return;
                
                const from = positions[fromState];
                const to = positions[toState];
                
                // Calculate arrow path (curved)
                const dx = to.x - from.x;
                const dy = to.y - from.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                // Offset start/end to account for node radius
                const startOffset = nodeRadius / dist;
                const endOffset = (nodeRadius + 8) / dist; // Extra offset for arrowhead
                
                const startX = from.x + dx * startOffset;
                const startY = from.y + dy * startOffset;
                const endX = to.x - dx * endOffset;
                const endY = to.y - dy * endOffset;
                
                // Control point for curve
                const midX = (startX + endX) / 2;
                const midY = (startY + endY) / 2;
                const perpX = -dy / dist * 20;
                const perpY = dx / dist * 20;
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${startX} ${startY} Q ${midX + perpX} ${midY + perpY} ${endX} ${endY}`);
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke', MARKOV_STATES[toState].color);
                path.setAttribute('stroke-width', Math.max(1, prob * 4));
                path.setAttribute('stroke-opacity', 0.3 + prob * 0.5);
                path.setAttribute('marker-end', 'url(#arrowhead)');
                
                arrowsGroup.appendChild(path);
            });
        });
        
        this.svg.appendChild(arrowsGroup);
        
        // Draw nodes
        const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        MARKOV_STATES.forEach((state, i) => {
            const pos = positions[i];
            const isCurrent = this.currentState === i;
            
            // Node circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', pos.x);
            circle.setAttribute('cy', pos.y);
            circle.setAttribute('r', nodeRadius);
            circle.setAttribute('fill', isCurrent ? state.color : '#22252A');
            circle.setAttribute('stroke', state.color);
            circle.setAttribute('stroke-width', isCurrent ? 3 : 2);
            
            if (isCurrent) {
                circle.style.filter = `drop-shadow(0 0 8px ${state.color})`;
            }
            
            nodesGroup.appendChild(circle);
            
            // Node label
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', pos.x);
            text.setAttribute('y', pos.y);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'central');
            text.setAttribute('fill', isCurrent ? '#1C1E22' : state.color);
            text.setAttribute('font-size', '11');
            text.setAttribute('font-weight', '600');
            text.setAttribute('font-family', 'Inter, sans-serif');
            text.textContent = state.short;
            
            nodesGroup.appendChild(text);
        });
        
        this.svg.appendChild(nodesGroup);
    }
    
    setCurrentState(state) {
        this.currentState = state;
        this.render();
    }
    
    destroy() {
        this.container.innerHTML = '';
    }
}

// Export
window.ApexMarkovMatrix = ApexMarkovMatrix;
window.ApexMarkovFlow = ApexMarkovFlow;
window.MARKOV_STATES = MARKOV_STATES;
