# UI – Seed Log

---

9: 2026-02-01 – UI Perfection: 4-Quadrant Grid & Top-Right JSON Editor Framework ^seed-ui-grid-json

## Prompts & Execution
"The top left quadrent is the profile manager and it should fit to the size of the left half of the panel and adapt to screen size. It should show the two screens. The ranks and the create a new profile. The top right quadrant is going to be the stats of each profile when selected in the left panel and the config which i believe the best format is to have a json editor screen... There should be two seperate pages on the right and left screen. The stats and config tabs at the top should change the page. Lets just focus on perfecting the ui in this seed. Also im not sure why the bottom left quadrent got moved to the top but that needs to go back down where it was."

## 1. Seed (Intent)
- **Objective:** Finalize the symmetrical 4-Quadrant Grid layout and implement the UI framework for the Top-Right "Profile Details" panel.
- **Specifics:**
    - **Grid Fix:** Restore the bottom-left quadrant to its correct position. Ensure the top two quadrants perfectly align width-wise with the bottom two. Responsiveness is key.
    - **Top-Left (Profile Manager):** Ensure it fills its quadrant and correctly toggles between "Ranks List" and "Create New" views (building on previous seeds).
    - **Top-Right (Profile Details - NEW):** Create a new panel that acts as the "Detail View" for the selected profile on the left.
    - **Tabs & JSON:** The Top-Right panel must have tabs for "Stats" and "Config". The "Config" tab must render a professional **JSON Editor** component (not a plain text area).

## 2. Related (Context)
- [[UI – Seed Log#^seed-ui-profile-grid]] (Previous attempt at grid layout).
- [[Profile - Seed Log A#^seed-profile-ranking]] (The left panel that triggers the right panel).

## 4. Foundation (Structure)
*Claude: You must integrate a JS-based JSON editor library (e.g., jsoneditor, ace, or monaco). Add the chosen library to this list.*
*Files to be modified/created:*
- `templates/apex.html`: The master grid structure. Needs fixing to restore bottom quadrants.
- `static/css/databases_database_panels.css`: Main grid layout rules.
- `static/js/profile_manager.js`: (Left Panel Logic) Needs to fire an event when a profile is selected.
- **NEW:** `static/js/profile_details.js`: (Right Panel Logic) Handles tab switching and initializing the JSON editor.
- **NEW:** `static/css/profile_details.css`: Styling for tabs and the editor container.
- **Constraint:** Need a JSON Editor library asset (e.g., `<script src="...jsoneditor.min.js">`).

## 8. Infinity (Patterns/Debt)
- **Pattern:** **Master-Detail View.** The Left Panel is the Master (list); the Right Panel is the Detail.
- **Pattern:** **Event-Driven Communication.** The left panel should *not* directly manipulate the right panel. It should emit a `profileSelected` event that the right panel listens for. This prevents spaghetti code.

## 7. Evolution (Real-Time Log)
*Claude: Log milestones here.*
- [ ] [Grid layout fixed (bottom quadrants restored)]
- [ ] [Top-Right panel structure created with Tabs]
- [ ] [JSON Editor library integrated and rendering]
- [ ] [Left-to-Right click communication established]

## 5. Senses (UX/DX)
- **Symmetry:** Top quadrants must visually align with bottom quadrants. No "stair-step" effect.
- **Responsiveness:** Panels fit to screen size.
- **Editor Feel:** The JSON editor must provide syntax highlighting and code folding, feeling like a professional tool.
- **Tab Switching:** Instant, no page reload.

## Architecture Flow
```mermaid
graph TD
    subgraph Global_Layout
        Grid[apex.html CSS Grid] --> TL[Top Left: Profile Manager]
        Grid --> TR[Top Right: Profile Details]
        Grid --> BL[Bottom Left: Restored Panel]
        Grid --> BR[Bottom Right: Existing Panel]
    end

    subgraph Interaction
        TL -->|User Clicks Profile| Event[Fire 'profileSelected' Event]
        Event -->|Listen| TR_Logic[profile_details.js]
        
        TR_Logic -->|Update| Tabs[Update Tab Content]
        
        subgraph Top_Right_Panel
            Tabs -->|Tab 1 Selected| StatsUI[Show Stats Div]
            Tabs -->|Tab 2 Selected| ConfigUI[Show JSON Editor Div]
            ConfigUI -->|Init| EditorLib[JSON Editor Component]
        end
    end