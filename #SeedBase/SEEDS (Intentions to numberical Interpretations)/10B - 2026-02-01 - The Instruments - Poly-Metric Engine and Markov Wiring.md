# Logic – Seed Log (Part B)

---

10B: 2026-02-01 – The Instruments: Poly-Metric Engine & Markov Wiring ^seed-logic-instruments

## Prompts & Execution
"There is a lot more content now in the json file... we need a part b for better results... AI will create sentiments for the six follow categories (Overall, Price Action, Key Levels, Momentum, Volume, Structure)... we also need an exit strategy."

## 1. Seed (Intent)
- **Objective:** Upgrade the core logic to calculate the **6 Distinct Sentiment Vectors** and wire the **Markov Matrix** parameters defined in the Maestro V2 Profile.
- **Specifics:**
    - **Poly-Metric Refactor:** Break `sentiment_engine.py` into 6 discrete calculation functions (e.g., `calc_price_action()`, `calc_volume_flow()`). The final score is the weighted sum of these parts.
    - **Markov Injection:** Connect the JSON `markov_matrix` parameters (History, Learning Rate) to the actual `wizaude_core_state_classifier.py` (or new Markov module).
    - **Complex Exits:** Implement the `check_dynamic_exits()` logic in the main loop to handle "Sentiment Flip" and "Regime Change" events.

## 2. Related (Context)
- [[Logic – Seed Log]] (Part A: The Conductor).
- `profiles/maestro_v2.json` (The Sheet Music).
- `Markov-State-Machine.md` (The Logic Source).

## 4. Foundation (Structure)
*Files to be modified:*
- `sentiment_engine.py`:
    - **CRITICAL:** Add distinct methods:
        - `_analyze_price_action(data)`
        - `_analyze_volume_flow(data)`
        - `_analyze_structure(data)`
        - `_analyze_key_levels(data)`
    - Update main `calculate()` to aggregate these using `profile['sentiment_engine']['vector_weights']`.
- `wizaude_core_state_classifier.py` (or new `markov_engine.py`):
    - Update `init` to accept `learning_rate` and `persistence` from JSON.
- `init2.py`:
    - In the trade management loop, add: `if trade_manager.should_exit(current_sentiment, current_regime): close_position()`.

## 8. Infinity (Patterns/Debt)
- **Pattern:** **Strategy Pattern.** Each of the 6 vectors is a mini-strategy. They don't know about each other; they just report their own score.
- **Anti-Pattern:** **Black Box Scoring.** Avoid a single "Magic Number" output. We need to know *why* the score is high (e.g., "Volume is 0.9, but Structure is 0.2").

## 5. Senses (UX/DX)
- **Transparency:** The logs should read: `Final Score: 0.72 | Breakdown: PA: 0.8, Vol: 0.6, Mom: 0.9`. You can see exactly which "Instrument" is playing the loudest.
- **Responsiveness:** If you change the JSON weight of "Volume" to 0.0, the Engine effectively "mutes" that instrument instantly.

## 7. Evolution (Real-Time Log)
*Claude: Log milestones here.*
- [ ] [Refactored `sentiment_engine.py` to support 6 vectors]
- [ ] [Wired JSON weights to vector aggregation math]
- [ ] [Connected Markov JSON params to State Machine logic]
- [ ] [Implemented "Sentiment Flip" exit trigger]

## Architecture Flow (The Poly-Metric Engine)
```mermaid
graph LR
    subgraph Inputs
        Data[Market Data]
        JSON[Profile Weights]
    end

    subgraph The_Instruments
        Data --> PA[Price Action Algo]
        Data --> Vol[Volume Flow Algo]
        Data --> Lvl[Key Levels Algo]
        Data --> Mom[Momentum Algo]
        Data --> Str[Structure Algo]
        Data --> Bias[Overall Bias Algo]
    end

    subgraph The_Mixer
        PA -->|x Weight| Sum((Weighted Sum))
        Vol -->|x Weight| Sum
        Lvl -->|x Weight| Sum
        Mom -->|x Weight| Sum
        Str -->|x Weight| Sum
        Bias -->|x Weight| Sum
        JSON --> Sum
    end

    Sum --> Final[Final Trade Signal]