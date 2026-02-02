***

### **Seed B: Dashboard Integration & Widget Control**
*Save to: `SEEDS (INTENTIONS)/Profile - Seed Log B.md`*

```markdown
# Profile – Seed Log B

---

8: 2026-01-31 – Smart Clock & Control Widget (Deepened) ^seed-profile-clock-widget

## Prompts & Execution
"B: Looking at the image i send theres a profile image with the time at the top of the calendar the time every 2 minutes the clock should have a transition animation into the rank number of the current profile. So it might show #2 instead of the time that will last for 20 seconds then transition back to the time. The arrows to the side should pause the program if its active and switch the profile to the next profile in order of rank and show the number immediately for 20 seconds then transition back to the time. When the profile image itself is clicked on it should change the calendar area to the same panel (profile directory) as on the top left quadrant of the database. There shouldn't be an option to add a profile from the algorithm page instead this is where the profile is activated for the instance. The profile image will change when i new profile is selected and the program can be reactivated with the new profile configurations."

## 1. Seed (Intent)
- **Objective:** Transform the Dashboard Clock/Calendar into a **State-Aware Controller**.
- **The Loop (Passive):**
    - **State 1 (Time):** Shows Standard Clock (Duration: 100s).
    - **State 2 (Rank):** Transitions to show "Rank #X" (Duration: 20s).
    - **Animation:** Smooth fade-out/fade-in or flip transition.
- **The Control (Active):**
    - **Arrows (< >):**
        1. **Command:** PAUSE execution immediately (Backend Signal).
        2. **Action:** Switch to Prev/Next Profile in the Rank List.
        3. **Display:** Force "Rank State" immediately (show new Rank #).
    - **Profile Click:**
        1. **Action:** Swap the entire Calendar Panel DOM with the **Profile Directory Panel** (from Seed A).
        2. **Context:** Allows deep selection without leaving the dashboard header.

## 2. Related (Context)
- [[Profile - Seed Log A#^seed-profile-ranking]] (Dependency: Requires the ranked list to know "Next/Prev").
- `static/js/apex_calendar.js` (Target for the loop logic).
- `init2.py` (Needs a `/api/control/pause` and `/api/control/switch_profile` endpoint).

## 4. Foundation (Structure)
*Files to be modified:*
- `static/js/apex_calendar.js`:
    - Logic: `setInterval` loop managing a `viewState` ('TIME' vs 'RANK').
    - Event: `onArrowClick` -> `stopExecution()` -> `switchProfile(next_index)`.
- `init2.py`:
    - `/api/control/pause`: Sets global `EXECUTION_STATE = 'PAUSED'`.
    - `/api/active_profile`: POST endpoint to hot-swap the active profile ID.
- `templates/apex.html`:
    - Update `#calendar-widget` container to support the "Flip Card" CSS structure or overlay divs.

## 5. Senses (UX/DX)
- **Motion:** The Time->Rank transition should feel like a "System Heartbeat."
- **Control:** Arrow clicks must feel **mechanical** and instant. No loading spinners. Click -> Snap to new Rank.
- **Clarity:** When "Paused" by an arrow click, the UI should visually indicate a "Halted" state (maybe dim the chart or show a Pause icon).

## 7. Evolution (The Shift)
- **From:** A passive clock that tells time.
- **To:** A **Command Center**. The user manages the *identity* of the algorithm (Who is driving?) directly from the time display.

## 8. Infinity (Patterns)
- **Pattern:** **Widget-as-Controller.** The status display *is* the button.
- **Pattern:** **Hot-Swapping.** Changing the brain (Profile) without reloading the page.

## Architecture Flow
```mermaid
graph TD
    subgraph Frontend_Loop
        Time[State: Time] -->|100s| Trans1[Fade Out]
        Trans1 -->|Fade In| Rank[State: Rank #]
        Rank -->|20s| Trans2[Fade Out]
        Trans2 -->|Fade In| Time
    end
    
    subgraph User_Intervention
        Arrow[Click Arrow] -->|Interrupt| Loop[Reset Loop Timer]
        Arrow -->|API Call| Pause[Backend: PAUSE]
        Arrow -->|Calc| Next[Get Next Rank Index]
        Next -->|API Call| Switch[Backend: Set Active Profile]
        Switch -->|Update UI| ShowRank[Force Show Rank #]
    end
    
    subgraph Widget_Swap
        ImgClick[Click Avatar] -->|DOM Swap| HideCal[Hide Calendar]
        HideCal -->|Show| Dir[Show Profile Directory]
    end