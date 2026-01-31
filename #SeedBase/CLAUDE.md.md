
---

`CLAUDE.md` (clear shorthand version)

`# Project: Trading Workspace (Instance Browser & Algorithms) Goal: - Reliable, understandable code for a trading workspace UI - Fast, predictable behavior for live trading - Cool mintâ€“tealâ€“magenta theme with subtle neumorphic depth The user keeps project memory in Obsidian notes (with [[links]] and ^anchors). ## 1. How to Interpret the User - Start by restating the request in **1â€“3 short bullets**. - Keep their intent intact; donâ€™t oversimplify important details. - Ask when something is unclear or risky to guess. ## 2. Logging: Seeds and Fruits We use **two types of logs** in Obsidian: - **Seed Log** = what weâ€™re about to do. - **Fruit Log** = what happened and how it feels (feedback). Only log **important** things that the user is likely to care about later. ### 2.1 Seeds A Seed is: - The **current task**, in one short sentence. - The **prompts that created it** (up to 3). - Any key context (related notes, key files, UX notes). **Behavior when the user sends a new main request:** 1. Interpret it in 1â€“3 bullets. 2. Say: **â€œGot it. Should I create the seed?â€** 3. If the user says yes, create/suggest a Seed entry. **Seed format example:** ```markdown # Instance Browser â€” Seed Log 1: 2026-01-30 14:10 â€” Fix Instance Browser dropdown selection and layout ^seed-IB-dropdown Prompts: - "Phase 3 Preview: Live Data Population..." - "Ok one bug we need to work out..." - "It should just refresh the panel and the correct algo should be selected..." Related (2): - Linked to live data phase: [[APEX_PROGRESS#^phase-3]] Foundation (4): - Files: IB.jsx, IB_dropdown.jsx, IB_state.ts, IB_tabs.jsx - Pattern: update state â†’ refresh panel only Senses (5): - Full-page refresh feels bad - Selected algo not clearly visible in search bar Cycle (7): - Current stage: wiring core behavior before micro-UX Infinity (8): - None yet (add later when patterns repeat)`

Keep text simple and readable. Only include sections that matter for this seed.

## 2.2 Fruits

A Fruit is:

- A summary ofÂ **what changed**Â for a Seed.
    
- TheÂ **userâ€™s feedback**Â (what works, what doesnâ€™t).
    
- Next questions or followâ€‘ups.
    

Fruits are created or updatedÂ **only when the user gives feedback**.

**Behavior:**

- When the user reacts (â€œthis feels good/bad/slow/confusingâ€), ask:
    
    - â€œDo you want me to add/update fruit for this seed?â€
        
- If yes, propose a Fruit entry or update.
    

**Fruit format example:**

text

`# Instance Browser â€” Fruit Log F: 2026-01-30 â€” Seed: IB-dropdown ^fruit-IB-dropdown What changed: - Dropdown now fills the panel and scrolls inside. - Selecting an algorithm:   - Updates selected state  - Refreshes only the lower panel  - Highlights the selected row  - Shows the algo name in the search bar - Symbol text cleaned from "XAUJ26.sim.sim" to "XAUJ26.sim". What works: - No full-page flash; interaction feels smoother. - Selected algo is obvious. What doesnâ€™t (yet): - Heavy data swaps still feel a bit slow. - No loading indicator when switching large datasets. Next ideas: - Add a small loading indicator for the data panel. - Consider virtualization or pagination for very large tables. Links: - Seed: [[Instance Browser â€” Seed Log#^seed-IB-dropdown]] - Files: IB.jsx, IB_dropdown.jsx, IB_state.ts, IB_tabs.jsx`

Fruits can be updated over time (add new â€œwhat works/doesnâ€™tâ€ sections as the user tests more).

## 3. 1â€“2â€“4â€“5â€“7â€“8 Lenses (Plain Language)

Use these asÂ **light tags**, not heavy theory:

- **1 â€“ Seed**: the one thing weâ€™re doing now.
    
- **2 â€“ Related**: what this touches (other notes, systems, APIs).
    
- **4 â€“ Foundation**: key files, components, or patterns involved.
    
- **5 â€“ Senses**: how it feels to use/build/debug.
    
- **7 â€“ Cycle**: where we are in the current phase/loop.
    
- **8 â€“ Infinity**: repeated patterns, links between notes, technical debt loops.
    

Use them in headings or inline labels, like:

text

`1: ... Related (2): ... Foundation (4): ... Senses (5): ... Cycle (7): ... Infinity (8): ...`

## 4. Memory & Continuity

- DoÂ **not**Â rely on old chat threads for project memory.
    
- For context, prefer:
    
    - Seed Log & Fruit Log entries.
        
    - Linked notes in Obsidian.
        
    - Code files referenced in the Foundation sections.
        

If something feels important for later:

- Suggest adding a short line to the Seed or Fruit logs.
    
- Keep it simple and to the point.
    

## 5. Front-End Theme: Mintâ€“Tealâ€“Magenta

When touching UI (HTML/CSS/JSX/React):

- **Base colors:**
    
    - Dark / mid grey or blueâ€‘grey backgrounds.
        
- **Primary accents:**
    
    - Mint green: confirmations, positive/ready states.
        
    - Teal blue: primary actions, active items, selection.
        
    - Magenta: emphasis, warnings, or rare highlights.
        
- **Neumorphism:**
    
    - Use soft shadows and highlights to give cards, dropdowns, and buttons slight depth.
        
    - Keep contrast high enough for readability.
        
    - Avoid heavy, flashy effects; favor subtle, confident UI.
        

Behavior expectations (Instance Browser example):

- Dropdown uses full panel height and scrolls inside.
    
- Selecting an algorithm:
    
    - Does not reload the page.
        
    - Refreshes only the data panel.
        
    - Highlights the chosen row and updates the search bar text.
        
- Symbol formatting is clean (e.g.,Â `XAUJ26.sim`).
    

## 6. Code Workflow & Feedback

AtÂ **session start**:

1. Read the latest Seed and relevant Fruit (if they exist).
    
2. Summarize current state in 1â€“3 bullets.
    
3. If the userâ€™s new request is a shift, ask:
    
    - â€œGot it. Should I create the seed?â€
        

WhileÂ **coding**:

- Keep work focused on the current Seed.
    
- Identify key files (Foundation) before big changes.
    
- Explain:
    
    - What youâ€™re changing.
        
    - How to test it.
        
    - Any tradeâ€‘offs.
        

ForÂ **feedback**:

- Ask for feedback before assuming something is fine:
    
    - â€œTry the new dropdown behavior; what feels good, what still feels off?â€
        
- When the user answers, propose a Fruit entry or update.
    

AtÂ **session end**:

- Recap what changed in a way that can drop straight into the Fruit Log.
    
- Suggest the next possible Seed if itâ€™s obvious.
  
  ---