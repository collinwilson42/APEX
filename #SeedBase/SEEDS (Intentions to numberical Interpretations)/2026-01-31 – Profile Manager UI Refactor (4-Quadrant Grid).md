# UI – Seed Log

---

5: 2026-01-31 – Profile Manager UI Refactor (4-Quadrant Grid - Deepened) ^seed-ui-profile-grid

## Prompts & Execution
"This is what the profile manager looks like currently. The ui is great. I want it to be full size within that top half of the database page so that the rounded corners meet the rounded corners and i want to use the original backdrop color not the darker black. That way the color scheme on the top half of the database ui matches the bottom half. Also currently there is 3 panels we can merge profiles and create profile into one panel so that when new is clicked it switches to the second currently middle window then the new button changes to save. and a back button appears. The whole database ui should be divided into 4 equal quadrants consistent with how the bottom half is already set up. In the top section The text Intelligence Database can be removed."

## 1. Seed (Intent)
- **Objective:** Refactor the Database Page into a strict, symmetrical **2x2 Quadrant Grid** with unified state management.
- **Specifics:**
    - **Grid Architecture:** Enforce a 50/50 vertical split and 50/50 horizontal split.
    - **Quadrant 1 (Top Left):** The "Profile Manager" (Merged List & Create Views).
    - **Quadrant 2 (Top Right):** The "Instance Browser" (or placeholder for future symmetry).
    - **Styling:** Remove the `#intelligence-header` ("Intelligence Database") entirely. Remove any `background-color: #000` overrides to expose the app's native "Matte Gray" theme.
    - **Interaction:** The Profile Manager becomes a **Single-Pane App** within its quadrant. clicking "New" does not open a modal; it *slides* the content to the Form View.

## 2. Related (Context)
- [[Structure – Seed Log#^seed-structure-init2-migration]] (Targeting `init2.py`).
- `static/css/databases_database_panels.css` (The Bottom Half reference).

## 4. Foundation (Structure)
*Files to be modified:*
- `templates/apex.html`:
    - Remove `<div id="intelligence-header">`.
    - Refactor `.database-top-section` to use CSS Grid (`grid-template-columns: 1fr 1fr`).
- `static/css/profile_manager.css`:
    - Remove `.dark-overlay` or specific background colors.
    - Ensure `.profile-panel` has `height: 100%`, `border-radius: var(--std-radius)`.
- `static/js/profile_manager.js`:
    - Implement `toggleView('list' | 'create')`.
    - Logic: "New" button click -> Hide List Div -> Show Form Div -> Change Button Text to "Save".

## 5. Senses (UX/DX)
- **Visual:** **Symmetry.** The top corners must align perfectly with the bottom corners.
- **Color:** **Monolithic.** The top half should not look like a "plugin"; it must match the bottom half's color palette exactly.
- **Motion:** **Slide/Fade.** Switching from "List" to "Create" should be a smooth internal transition, not a jarring jump.

## 7. Evolution (The Shift)
- **From:** A "Three-Column Widget" floating in a dark header.
- **To:** A **Integrated Command Quadrant.** The UI evolves from "putting things on the screen" to "organizing functional domains" (Profiles Top Left, Instances Top Right).

## 8. Infinity (Patterns)
- **Pattern:** **The Quadrant Law.** The screen is divided into 4 equal functional areas.
- **Pattern:** **In-Place Navigation.** Don't open windows; change the state of the current window.

## Architecture Flow

```mermaid
graph TD
    subgraph Database_Page_Layout
        Row1[Top Row] -->|50% Width| Q1[Quad 1: Profile Manager]
        Row1 -->|50% Width| Q2[Quad 2: Instance/Future]
        Row2[Bottom Row] -->|50% Width| Q3[Quad 3: Data]
        Row2 -->|50% Width| Q4[Quad 4: Analytics]
    end

    subgraph Q1_Internal_State
        ViewList[List Mode]
        ViewForm[Create Mode]
        
        BtnNew[Button: New] -->|Click| ViewForm
        BtnBack[Button: Back] -->|Click| ViewList
        BtnSave[Button: Save] -->|Click| ViewList
    end