# Profile – Seed Log A

---

7: 2026-01-31 – Profile Images & North Star Ranking (Deepened) ^seed-profile-ranking

## Prompts & Execution
"A: When creating a profile there should be an option for adding a circular profile image. The upload will take place in the front end and save to the img folder automatically. The profile directory in the left quadrent of the database page. will show a scroll list of all profiles with the profile image to the left and their rank for that specific symbol based on the north star metric which is (Net Profit * 0.25) * (Profit Factor * 0.75) [Correction: (Net Profit / Total Signals) * Profit Factor] So each profile picture will have a white number inside in order from 1 (at the top) - n (number of profiles created for that symbol) followed by the name of the profile and the API provider (Claude Sonnet / google gemini pro etc."

## 1. Seed (Intent)
- **Objective:** Implement Profile Image uploading and a Ranked Directory in the Database Page (Left Quadrant).
- **North Star Metric:** `(Net Profit / Total Signals) * Profit Factor`.
    - *Constraint:* If `Total Signals` is 0, Rank Score = 0.
- **Specifics:**
    - **Upload Handling:** Frontend sends file -> Backend sanitizes name -> Saves to `static/img/profiles/` -> Updates DB record.
    - **Directory UI:**
        - **Visual:** Circular Avatar (60px) with a "Rank Badge" (White text, absolute position bottom-right or center overlay).
        - **Meta:** Name + Provider (e.g., "Claude Sonnet") + Calculated Score (hidden or subtle).
        - **Sorting:** Auto-sorts descending by North Star Score.

## 2. Related (Context)
- `init2.py` (File handling for uploads).
- `instance_database.py` (Source of `net_profit`, `total_trades`, `profit_factor`).
- [[UI – Seed Log#^seed-ui-profile-grid]] (The Grid Layout this lives inside).

## 4. Foundation (Structure)
*Files to be modified:*
- `init2.py`:
    - Add `/api/profile/upload` (POST): Handles `multipart/form-data`.
    - Add `/api/profiles/ranked`: Returns profiles sorted by the North Star formula.
- `instance_database.py`:
    - Method `get_ranked_profiles(symbol)`: Performs the `(NP/Trades)*PF` calculation via SQL or Python.
- `static/js/profile_manager.js`:
    - `renderProfileList()`: Needs to handle the "Rank Badge" overlay injection.
    - `uploadProfileImage()`: Async fetch with visual progress feedback.
- `static/css/profile_manager.css`:
    - `.profile-avatar`: Circular, `object-fit: cover`.
    - `.rank-badge`: Absolute positioning, z-index 10, white text, semi-transparent background.

## 5. Senses (UX/DX)
- **Visual:** "Leaderboard" aesthetic. High ranks feel prestigious.
- **Feedback:** "Flash" effect on the list when re-sorting happens.
- **Safety:** Prevent uploading massive images (limit to 2MB).

## 7. Evolution (The Shift)
- **From:** A flat, unverified list of text configurations.
- **To:** A **Meritocratic Asset Board**. Profiles are judged by their efficiency per signal, not just raw profit.

## 8. Infinity (Patterns)
- **Pattern:** **Calculated Property Injection.** The backend calculates the rank; the frontend just displays it.

## Architecture Flow
```mermaid
graph LR
    User[Frontend: Upload] -->|POST /image| API[init2.py]
    API -->|Sanitize & Save| Disk[static/img/profiles/id_time.png]
    API -->|Update Path| DB[Instance DB]
    
    Stats[Stats Engine] -->|Fetch: NP, Trades, PF| Ranker[Ranking Logic]
    Ranker -->|Calc: (NP/Trades)*PF| Score[North Star Score]
    Score -->|Sort Descending| JSON[Ranked List JSON]
    JSON -->|Render| DOM[Left Quadrant: Leaderboard]