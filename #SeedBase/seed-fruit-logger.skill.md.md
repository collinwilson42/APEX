
---
``name: seed-fruit-logger description: Keep work aligned with Seeds (current tasks) and Fruits (user feedback) stored in Obsidian. --- ## Purpose This skill keeps each session tightly aligned with: - **Seeds**: what we’re doing now. - **Fruits**: what happened and how it feels (user feedback). It should: - Read existing Seeds/Fruits at the start of a session. - Ask to create a Seed when the user starts a new focus. - Suggest Fruit updates when the user gives feedback. ## When to Use This Skill Use this skill whenever: - A new coding or UX task is started. - The user returns to the project after a break. - The user gives feedback on recent changes (good or bad). ## Behavior ### 1. At Session Start 1. Ask the user where the Seed/Fruit logs live, if not already known (e.g., in Obsidian, file names like `Instance Browser — Seed Log.md` and `Instance Browser — Fruit Log.md`). 2. Read the latest Seed for the relevant area (e.g., Instance Browser, Sentiment Engine, etc.). 3. If a Fruit exists for that Seed, read the latest Fruit entry as well. 4. Summarize in 1–3 bullets:    - Current Seed: what we’re doing now.   - Latest Fruit: what changed and any open issues. 5. Confirm with the user:    - “Is this still the current focus, or are we starting something new?” ### 2. When the User Sends a “Seed-Worthy” Prompt A prompt is “Seed-worthy” if it defines a new, non-trivial focus (e.g., fixing the dropdown behavior, redesigning a panel, adding a new data path). Steps: 1. Interpret the request in 1–3 bullets. 2. Say: **“Got it. Should I create the Seed?”** 3. If the user says yes:    - Draft a Seed entry in the agreed format, including:     - Timestamp     - One-sentence intent     - Up to the last 3 prompts that define this Seed     - Optional sections for Related, Foundation, Senses, Cycle, Infinity if they add clear value.   - Present the Seed entry so the user can paste it into their Seed Log.   - Use simple, readable labels like:      ```markdown     1: [time] — [intent] ^seed-[short-name]      Prompts:     - "prompt 1"     - "prompt 2"     - "prompt 3"      Related (2): ...     Foundation (4): ...     Senses (5): ...     Cycle (7): ...     Infinity (8): ...     ``` 4. If the user says no:    - Continue the conversation without creating a Seed, but still keep the context in mind. ### 3. While Working on a Seed While doing code or design work under an active Seed, this skill should help you: - Stay focused on the current Seed’s intent. - Refer back to:   - Foundation(files/components)  - Senses (UX notes) - Avoid drift into unrelated tasks without starting a new Seed. - Occasionally check with the user:   - “Are we still on Seed [name], or do you want to define a new one?” ### 4. When the User Gives Feedback (Fruit) Any time the user reacts with “this feels good/bad/slow/confusing” or reports outcomes: 1. Identify which Seed this feedback belongs to. 2. Ask:    - “Do you want me to add or update a Fruit entry for this Seed?” 3. If yes:    - If a Fruit already exists for that Seed:     - Append new feedback under that Fruit.   - If not:     - Draft a new Fruit entry. Fruit entries should have: ```markdown F: [date] — Seed: [short-name] ^fruit-[short-name] What changed: - ... What works: - ... What doesn’t: - ... Next ideas: - ... Links: - Seed: [[Seed Log#^seed-[short-name]]] - Files: [key files]``

4. Present the Fruit entry so the user can paste or update it in their Fruit Log.
    

## 5. Asking for Feedback Before Assuming

Before logging Fruit or making big decisions:

- If feedback is incomplete or vague, ask simple, direct questions like:
    
    - “What feels better now?”
        
    - “What still feels wrong or slow?”
        
    - “Is there anything about this change that surprised you?”
        

Only log Fruit after the user has given clear feedback, to keep the Fruit Log meaningful.

## Tone and Style

- Keep all Seed/Fruit suggestions **short, clear, and readable**.
    
- Avoid cryptic abbreviations; favor simple shorthand like:
    
    - `What changed / What works / What doesn’t / Next ideas / Links`.
        
- Aim to save the user time, not add overhead.
  
  ---