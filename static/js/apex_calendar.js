/* ═══════════════════════════════════════════════════════════════════════════
   APEX CALENDAR WIDGET - Date Range Picker for Replay & Bot Scheduling
   
   Features:
   - Start/Due date selection
   - Time inputs for precise scheduling
   - Date range highlighting
   - Dark neumorphic theme
   ═══════════════════════════════════════════════════════════════════════════ */

class ApexCalendar {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        this.options = {
            onRangeSelect: options.onRangeSelect || (() => {}),
            onDateClick: options.onDateClick || (() => {}),
            startDate: options.startDate || null,
            endDate: options.endDate || null,
            startTime: options.startTime || '00:00:00',
            endTime: options.endTime || '18:45:00',
            ...options
        };
        
        this.currentDate = new Date();
        this.viewDate = new Date();
        this.startDate = this.options.startDate ? new Date(this.options.startDate) : null;
        this.endDate = this.options.endDate ? new Date(this.options.endDate) : null;
        this.startTime = this.options.startTime;
        this.endTime = this.options.endTime;
        this.selecting = 'start'; // 'start' or 'end'
        
        this.render();
        this.bindEvents();
    }
    
    render() {
        this.container.innerHTML = '';
        this.container.classList.add('apex-calendar');
        
        // Date/Time Inputs Row
        const inputsRow = document.createElement('div');
        inputsRow.className = 'calendar-inputs';
        inputsRow.innerHTML = `
            <div class="calendar-input-group">
                <label class="calendar-input-label">Start</label>
                <div class="calendar-input-field" id="start-date-display">
                    <span class="calendar-icon">📅</span>
                    <span class="calendar-date-text">${this.formatDateDisplay(this.startDate)}</span>
                </div>
            </div>
            <div class="calendar-input-group">
                <label class="calendar-input-label">Due</label>
                <div class="calendar-input-field" id="end-date-display">
                    <span class="calendar-icon">📅</span>
                    <span class="calendar-date-text">${this.formatDateDisplay(this.endDate)}</span>
                </div>
            </div>
        `;
        this.container.appendChild(inputsRow);
        
        // Time Inputs Row
        const timeRow = document.createElement('div');
        timeRow.className = 'calendar-time-row';
        timeRow.innerHTML = `
            <div class="calendar-time-input">
                <span class="calendar-icon">🕐</span>
                <input type="text" class="time-input" id="start-time" value="${this.startTime}" placeholder="00:00:00" />
            </div>
            <div class="calendar-time-input">
                <span class="calendar-icon">🕐</span>
                <input type="text" class="time-input" id="end-time" value="${this.endTime}" placeholder="00:00:00" />
            </div>
        `;
        this.container.appendChild(timeRow);
        
        // Month Navigation
        const nav = document.createElement('div');
        nav.className = 'calendar-nav';
        nav.innerHTML = `
            <button class="calendar-nav-btn" id="prev-month">‹</button>
            <span class="calendar-month-label">${this.getMonthYearLabel()}</span>
            <button class="calendar-nav-btn" id="next-month">›</button>
        `;
        this.container.appendChild(nav);
        
        // Day Headers
        const dayHeaders = document.createElement('div');
        dayHeaders.className = 'calendar-day-headers';
        ['S', 'M', 'T', 'W', 'T', 'F', 'S'].forEach(day => {
            const header = document.createElement('div');
            header.className = 'calendar-day-header';
            header.textContent = day;
            dayHeaders.appendChild(header);
        });
        this.container.appendChild(dayHeaders);
        
        // Calendar Grid
        const grid = document.createElement('div');
        grid.className = 'calendar-grid';
        grid.id = 'calendar-grid';
        this.container.appendChild(grid);
        
        this.renderDays();
    }
    
    renderDays() {
        const grid = this.container.querySelector('#calendar-grid');
        grid.innerHTML = '';
        
        const year = this.viewDate.getFullYear();
        const month = this.viewDate.getMonth();
        
        // First day of month
        const firstDay = new Date(year, month, 1);
        const startDay = firstDay.getDay();
        
        // Days in month
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        // Days from previous month
        const prevMonthDays = new Date(year, month, 0).getDate();
        
        // Total cells (6 weeks * 7 days)
        const totalCells = 42;
        
        for (let i = 0; i < totalCells; i++) {
            const cell = document.createElement('div');
            cell.className = 'calendar-day';
            
            let dayNum;
            let cellDate;
            let isOtherMonth = false;
            
            if (i < startDay) {
                // Previous month
                dayNum = prevMonthDays - startDay + i + 1;
                cellDate = new Date(year, month - 1, dayNum);
                isOtherMonth = true;
            } else if (i >= startDay + daysInMonth) {
                // Next month
                dayNum = i - startDay - daysInMonth + 1;
                cellDate = new Date(year, month + 1, dayNum);
                isOtherMonth = true;
            } else {
                // Current month
                dayNum = i - startDay + 1;
                cellDate = new Date(year, month, dayNum);
            }
            
            cell.textContent = dayNum;
            cell.dataset.date = cellDate.toISOString().split('T')[0];
            
            // Apply classes
            if (isOtherMonth) {
                cell.classList.add('calendar-day--other');
            }
            
            if (this.isToday(cellDate)) {
                cell.classList.add('calendar-day--today');
            }
            
            if (this.isSelected(cellDate, 'start')) {
                cell.classList.add('calendar-day--start');
            }
            
            if (this.isSelected(cellDate, 'end')) {
                cell.classList.add('calendar-day--end');
            }
            
            if (this.isInRange(cellDate)) {
                cell.classList.add('calendar-day--in-range');
            }
            
            grid.appendChild(cell);
        }
    }
    
    bindEvents() {
        // Navigation
        this.container.querySelector('#prev-month').addEventListener('click', () => {
            this.viewDate.setMonth(this.viewDate.getMonth() - 1);
            this.updateView();
        });
        
        this.container.querySelector('#next-month').addEventListener('click', () => {
            this.viewDate.setMonth(this.viewDate.getMonth() + 1);
            this.updateView();
        });
        
        // Date selection
        this.container.querySelector('#calendar-grid').addEventListener('click', (e) => {
            if (e.target.classList.contains('calendar-day') && !e.target.classList.contains('calendar-day--other')) {
                this.selectDate(new Date(e.target.dataset.date));
            }
        });
        
        // Date display clicks (toggle selection mode)
        this.container.querySelector('#start-date-display').addEventListener('click', () => {
            this.selecting = 'start';
            this.updateSelectionIndicator();
        });
        
        this.container.querySelector('#end-date-display').addEventListener('click', () => {
            this.selecting = 'end';
            this.updateSelectionIndicator();
        });
        
        // Time inputs
        this.container.querySelector('#start-time').addEventListener('change', (e) => {
            this.startTime = e.target.value;
            this.notifyChange();
        });
        
        this.container.querySelector('#end-time').addEventListener('change', (e) => {
            this.endTime = e.target.value;
            this.notifyChange();
        });
    }
    
    selectDate(date) {
        if (this.selecting === 'start') {
            this.startDate = date;
            // If end date is before start, clear it
            if (this.endDate && this.endDate < date) {
                this.endDate = null;
            }
            this.selecting = 'end';
        } else {
            // Ensure end is after start
            if (this.startDate && date < this.startDate) {
                this.endDate = this.startDate;
                this.startDate = date;
            } else {
                this.endDate = date;
            }
            this.selecting = 'start';
        }
        
        this.updateView();
        this.notifyChange();
    }
    
    updateView() {
        // Update month label
        this.container.querySelector('.calendar-month-label').textContent = this.getMonthYearLabel();
        
        // Update date displays
        this.container.querySelector('#start-date-display .calendar-date-text').textContent = 
            this.formatDateDisplay(this.startDate);
        this.container.querySelector('#end-date-display .calendar-date-text').textContent = 
            this.formatDateDisplay(this.endDate);
        
        // Re-render days
        this.renderDays();
        this.updateSelectionIndicator();
    }
    
    updateSelectionIndicator() {
        const startDisplay = this.container.querySelector('#start-date-display');
        const endDisplay = this.container.querySelector('#end-date-display');
        
        startDisplay.classList.toggle('calendar-input-field--active', this.selecting === 'start');
        endDisplay.classList.toggle('calendar-input-field--active', this.selecting === 'end');
    }
    
    notifyChange() {
        this.options.onRangeSelect({
            startDate: this.startDate,
            endDate: this.endDate,
            startTime: this.startTime,
            endTime: this.endTime
        });
    }
    
    // Utility methods
    getMonthYearLabel() {
        const months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return `${months[this.viewDate.getMonth()]} ${this.viewDate.getFullYear()}`;
    }
    
    formatDateDisplay(date) {
        if (!date) return 'Select date';
        const d = date.getDate().toString().padStart(2, '0');
        const m = (date.getMonth() + 1).toString().padStart(2, '0');
        const y = date.getFullYear();
        return `${d}-${m}-${y}`;
    }
    
    isToday(date) {
        const today = new Date();
        return date.getDate() === today.getDate() &&
               date.getMonth() === today.getMonth() &&
               date.getFullYear() === today.getFullYear();
    }
    
    isSelected(date, type) {
        const compareDate = type === 'start' ? this.startDate : this.endDate;
        if (!compareDate) return false;
        return date.getDate() === compareDate.getDate() &&
               date.getMonth() === compareDate.getMonth() &&
               date.getFullYear() === compareDate.getFullYear();
    }
    
    isInRange(date) {
        if (!this.startDate || !this.endDate) return false;
        return date > this.startDate && date < this.endDate;
    }
    
    // Public methods
    setRange(startDate, endDate, startTime, endTime) {
        this.startDate = startDate ? new Date(startDate) : null;
        this.endDate = endDate ? new Date(endDate) : null;
        if (startTime) this.startTime = startTime;
        if (endTime) this.endTime = endTime;
        this.updateView();
    }
    
    getRange() {
        return {
            startDate: this.startDate,
            endDate: this.endDate,
            startTime: this.startTime,
            endTime: this.endTime
        };
    }
    
    destroy() {
        this.container.innerHTML = '';
        this.container.classList.remove('apex-calendar');
    }
}

// Export
window.ApexCalendar = ApexCalendar;
