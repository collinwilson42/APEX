---
name: seed-fruit-expert-anchor
description: Enforces the 1-2-4-8-7-5 Strategic Circuit. Defines the "Living Seed" and "Breadcrumb Theory" protocols for expert architecture.
---

## Directories

ROOT: C:\Users\colli\Downloads#CodeBase#SeedBase SEEDS: C:\Users\colli\Downloads#CodeBase#SeedBase\SEEDS (Intentions to numberical Interpretations) FRUITFUL FEEDBACK: C:\Users\colli\Downloads#CodeBase#SeedBase\Fruitful Feedback (READ ONLY)


## Purpose

This skill transforms "tasks" into **Expert Architecture**. It uses the **Breadcrumb Theory** to maintain high-fidelity context across sessions and enforces the **Living Seed** protocol.

### Core Protocols

**1. The Breadcrumb Theory (Compressed Value)**
   - The `SEEDS` and `FRUIT` folders are not trash; they are **Condensed Context**.
   - **Rule:** Before starting a new Seed, the AI *must* scan previous `SEEDS` and `FRUIT` logs to understand the project's "DNA" and trajectory.
   - **Why:** This prevents re-learning the same lessons. The history is the map.

**2. The Living Seed (Grow Before Coding)**
   - The Seed is not a static order; it is a dynamic map.
   - **Gemini (Architect):** Plants the initial Seed (Structure & Intent).
   - **Claude (Cultivator):** **MUST grow the Seed before coding.**
     - *Check:* Are files missing in Lens 4? Add them.
     - *Check:* Is the Logic in Lens 8 sound? Refine it.
   - **Rule:** Never generate code until the Seed Log is accurate.

**3. The 1-2-4-8-7-5 Circuit (Strategic Order)**
   - We do not follow linear numbers (1,2,3...). We follow the **Strategic Path**:
     - **Material:** 1 (Intent) -> 2 (Context) -> 4 (Structure).
     - **Logic:** 8 (Patterns/Debt).
     - **Time:** 7 (Real-Time Evolution).
     - **Experience:** 5 (Senses/UX).

---

## The 6 Developmental Anchors (The Circuit)

The Seed grows strictly along this path.

| # | Anchor | Definition | Action Required |
|---|---|---|---|
| **1** | **Seed (Intent)** | The Cycle Origin. | Define the singular goal. No ambiguity. |
| **2** | **Related** | Context & Connections. | What does this connect to? (Fruitful Feedback, Docs, Skills, Relative Seeds). |
| **4** | **Foundation** | **Critical:** Structure & Files. | **The Map.** List specific file paths & classes *before* coding. Claude *must* expand this if incomplete. |
| **8** | **Infinity** | Patterns & Logic. | Define the algorithms, data structures, and debt to avoid. |
| **7** | **Evolution** | **Starting Point(s)** | **Active History** | **Update in Real-Time.** Define where we are now in progress then log specific milestones achieved *during* the session (e.g., "Merged Database Class"). |
| **5** | **Senses** | UI/UX/DX & Feel. | Define the final skin: Visuals, latency, and error handling. | *before and after* the session

---

## Behavior

### 1. The "Automatic Pause" Protocol
**Trigger:** When a prompt implies new complexity.
1.  **STOP.** Do not write code immediately.
2.  **Scan Breadcrumbs:** Read the last `FRUIT` log to ensure alignment.
3.  **Assess:** Does a Seed exist?
4.  **Action:** If no, propose the Seed Log. If yes, load the existing Seed Log.

### 2. Planting (Gemini/User)
1.  Draft the **Seed Log** using the **1-2-4-8-7-5** sequence.
2.  **Lens 4 (Foundation):** List the known files.
3.  **Save:** The Seed Log is saved to `SEEDS (INTENTIONS)/` before coding begins.

### 3. Cultivating (Claude)
**CRITICAL STEP: Grow the Seed.**
*Before writing Python/JS:*
1.  **Review Lens 4:** "Are all necessary files listed? If I need to touch `style.css`, add it to the list."
2.  **Review Lens 8:** "Is there a pattern I should enforce?"
3.  **Execute:** Write the code.
4.  **Update Lens 7:** As tasks are finished, append them to the "Evolution" section of the Seed Log to track progress.

### 4. Harvest (Fruit)
1.  User provides feedback via **Fruit Log**.
2.  Compare Fruit against the Seed.
    * **Ripe:** Mark Seed as Complete.
    * **Bitter:** Update Lens 4 or 8 for the next cycle.

---

## Seed Log Format (Strict 1-2-4-8-7-5)

Save to: `SEEDS (INTENTIONS)/[Area] – Seed Log.md`

```markdown
# [Area] – Seed Log

---

[ID]: [YYYY-MM-DD] – [Intent/Name] ^seed-[short-name]

## Prompts & Execution
"[Insert exact User Prompt here]"

## 1. Seed (Intent)
- [The core objective]

## 2. Related (Context)
- [[Link to Previous Fruit Log]] (Breadcrumb)
- [External Docs/APIs]

## 4. Foundation (Structure)
*AI/Claude: List ACTUAL files involved. Add to this list as you discover dependencies.*
- `path/to/file.js`
- `path/to/style.css`

## 8. Infinity (Patterns/Debt)
- [Logic, Algorithms, Positive-Patterns]

## 7. Evolution (Real-Time Log)
*Claude: Log completed milestones here as you work.*
- [ ] [Pending: Draft Phase]
- [x] [Completed: Feature A merged]
- [x] [Completed: Bug B fixed]

## 5. Senses (UX/DX)
- [Visual style, latency expectations, error handling]

## Architecture Flow
```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]

---

## Fruit Log Format (Reference Only)

```markdown
# [Area] – Fruit Log

F: [YYYY-MM-DD] – Seed: [short-name] ^fruit-[short-name]

**Review:**
- [Direct feedback on the Seed's result]

**Adjustments:**
- [What needs to change in the next cycle]


**Adjustments:**
- **Shift Role:** Gemini and Claude are **Co-Architects**. Either can plant the Seed.
- **Protocol:** The "Automatic Pause" is now in effect. If a prompt implies new complexity, the AI *must* propose a Seed before coding.
- **Goal:** Empower the Cultivator with a map, but allow for creative deviation if the Seed evolves.
Status: The Skill File is updated. The "Pause & Plant Protocol" is active. The "Evolution" Begins.