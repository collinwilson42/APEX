{
type: uploaded file
fileName: SKILL.md
fullContent:
---
name: seed-fruit-expert-anchor
description: Enforces expert-level preparation using 1-2-4-5-7-8 anchors before coding.
---

## Directories

ROOT: C:\Users\colli\Downloads\#CodeBase\#SeedBase 
SEEDS: C:\Users\colli\Downloads\#CodeBase\#SeedBase\SEEDS (Intentions to numberical Interpretations)
FRUITFUL FEEDBACK: C:\Users\colli\Downloads\#CodeBase\#SeedBase\Fruitful Feedback (READ ONLY)


## Purpose

This skill transforms "tasks" into **Expert Architecture**. It prevents "coding in the dark" by forcing a pause to establish **Developmental Anchors** (The 8 Lenses) before code generation begins.

**Core Rules:**
1.  **No Action Without Anchors:** Do not generate code until the Seed is established with the 8 Lenses.
2.  **Breadcrumbs (Lens 4):** You must explicitly identify and list related files (Foundation) before modifying them.
3.  **Visual Architecture:** Every Seed requires a Mermaid flowchart to map the logic *before* execution.
4.  **Feedback Loop:** Constantly cross-reference the User's "Fruit" (Feedback) to ensure the Seed is ripening correctly.

---

## The 8 Developmental Anchors (Lenses)

These are not tags. They are steps in the engineering process.

| # | Anchor | Definition | Action Required |
|---|---|---|---|
| **1** | **Seed (Intent)** | The singular focus. | Define the specific goal clearly. |
| **2** | **Related** | Context & Connections. | List APIs, documentation, or other systems involved. |
| **4** | **Foundation** | **Critical:** Structure & Files. | List specific file paths/classes existing *now*. This creates the breadcrumb trail. |
| **5** | **Senses** | UX/DX & Feel. | Define how it should feel (fast, smooth, matte) or behave (error handling). |
| **7** | **Cycle** | Phase/Status. | Where are we? (Drafting, Refactoring, Polishing). |
| **8** | **Infinity** | Patterns & Debt. | Identify repeated patterns to enforce or tech debt to avoid. |

---

## Behavior

### 1. Session Start: Alignment
1.  Scan `SEEDS` for the latest active focus.
2.  Scan `FRUIT` for the latest user feedback.
3.  **Synthesize:** "We are currently growing [Seed Name]. The last fruit indicated [Feedback Summary]. Should we continue this or plant a new Seed?"

### 2. Planting a Seed (The Preparation Phase)
When the user defines a new focus:
1.  **Pause.** Do not write code yet.
2.  Draft the **Seed Log** using the Anchors.
3.  **Crucial Step:** Fill out **Lens 4 (Foundation)** by finding the actual file names in the codebase.
4.  **Crucial Step:** Generate a **Mermaid Flowchart** representing the architectural flow of this Seed.
5.  Present the Seed Log for user confirmation.

### 3. Cultivating (The Coding Phase)
1.  Execute changes based *only* on the Anchors defined.
2.  If the scope drifts, ask: "This drifts from Anchor 1 (Intent). Should we update the Seed or log this for later?"
3.  Reference Lens 4 (Foundation) files by name to ensure continuity.

### 4. Harvest (Reviewing Fruit)
**The User creates the Fruit.** The AI reviews it.
1.  When the user provides feedback/fruit:
    * Analyze it against the current Seed.
    * If positive: "Fruit is ripe. Shall we close this Seed?"
    * If negative/constructive: "Fruit is bitter. Which Anchor failed? Was Lens 4 (Foundation) missing a file? Did we miss Lens 5 (Senses)?"
    * Update the Seed's "Tasks" or "Notes" based on this Fruit.

---

## Seed Log Format (Strict)

Save to: `SEEDS (INTENTIONS)/[Area] – Seed Log.md`

```markdown
# [Area] – Seed Log

---

[ID]: [YYYY-MM-DD] – [Intent/Name] ^seed-[short-name]

## 1. Seed (Intent)
- [The core objective]

## 2. Related (Context)
- [[Links to other notes]]
- [External Docs/APIs]

## 4. Foundation (Structure)
*AI: List the actual files/classes involved before coding.*
- `path/to/file.js`
- `path/to/style.css`
- **Pattern:** [e.g., Neumorphism, Singleton, Factory]

## 5. Senses (UX/DX)
- [Visual style, latency expectations, error feedback]

## 7. Cycle (Phase)
- [e.g., Refactoring / Implementation]

## 8. Infinity (Patterns/Debt)
- [What to avoid, what to repeat]

## Architecture Flow
```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]
Prompts & Execution
"User Prompt 1"

"User Prompt 2"

Tasks Completed
[ ] Task 1

[ ] Task 2


---

## Fruit Log Format (Reference Only)

*User creates this. AI reads this.*

```markdown
# [Area] – Fruit Log

F: [YYYY-MM-DD] – Seed: [short-name] ^fruit-[short-name]

**Review:**
- [Direct feedback on the Seed's result]

**Adjustments:**
- [What needs to change in the next cycle]
}


***

### 2. Fruitful Feedback (Critique of Previous Logs)

Here is a Fruit entry I have drafted for you. It critiques the two logs you provided (`Instance Browser` and `Phase 3`). It points out that while the work got done, the *Architecture* (Lenses) and *Flow* were missing, which risks "spaghetti code" in the long run.

**You should save this to:** `C:\Users\colli\Downloads\#CodeBase\#SeedBase\FRUIT (FEEDBACK)\Process – Fruit Log.md`

```markdown
# Process – Fruit Log

---

F: 2026-01-31 – Seed: Retroactive-Review ^fruit-process-review

**Context:**
Reviewing `Instance Browser – Seed Log` and `Phase 3 – Seed Log` against the new **Expert Anchor** protocols.

**What Changed:**
We are shifting from "Task Logging" to "Seed Architecting."

**Critique of Previous Seeds:**
The previous logs (Jan 30) were effective checklists (Tasks Completed ✅), but they lacked **Developmental Anchors**.
1.  **Missing Lens 4 (Foundation):** The logs listed "Files Modified" *after* the fact. The new process requires listing them *before* starting. This acts as a breadcrumb trail for the AI to understand the current state before mutating it.
2.  **Missing Flowchart:** There was no visual map of how the Database Schema updates (`instance_database.py`) flowed into the JS frontend (`apex_instances.js`).
3.  **Missing Lens 8 (Infinity):** We did not explicitly state the technical debt risks or reusable patterns (like the "Matte Black" theme) upfront.

**Corrected Example (How "Instance Browser" should have started):**

> **1. Seed:** Unify Left Panel UI with Right Panel & Update Schema.
> **4. Foundation:**
>    - `static/css/apex_instances.css` (Target for Matte Black)
>    - `templates/includes/database_panel_left.html` (Structure)
>    - `instance_database.py` (Schema source)
> **5. Senses:**
>    - Left panel must feel "matte" and "flat" (Neumorphic recessed), not glossy/blue.
>    - Bias labels must read as text ("Strong Bear"), not numbers, for immediate cognitive recognition.
> **Architecture Flow:**
> ```mermaid
> graph LR
>    DB[(SQLite)] -->|Raw Sentiment| API[Flask Endpoint]
>    API -->|Inject Matrix Label| JSON[Response]
>    JSON -->|getBiasLabel()| JS[Frontend Table]
>    JS -->|Apply CSS| UI[Matte Black DOM]
> ```

**Next Steps:**
- All future Seeds must strictly follow the `1-2-4-5-7-8` format.
- AI must generate the Mermaid flowchart *before* writing code.
- "Files Modified" goes at the end, but "Foundation" (Files Read) goes at the start.