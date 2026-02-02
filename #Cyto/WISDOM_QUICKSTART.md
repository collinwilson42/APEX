# Wisdom Bridge - Quick Reference

## Setup
```bash
cd C:\Users\colli\Downloads\Cyto_v3\Cyto
pip install -r requirements.txt
```

## Commands

### Add a Quote (Inner Ring - 0.618)
```bash
python wisdom_bridge.py add quote "Your quote text here" --section 9 --source "Proverbs 1:7" --domain "SOLOMON"
```

### Add a Principle (Middle Ring - 1.000)
```bash
python wisdom_bridge.py add principle "Your principle statement" --section 9 --parent 5
```

### Add an Interpretation (Outer Ring - 1.618)
```bash
python wisdom_bridge.py add interpretation "Your interpretation and application" --section 9 --parent 12
```

### List All Nodes
```bash
python wisdom_bridge.py list
```

### List by Section
```bash
python wisdom_bridge.py list --section 9
```

### List by Type
```bash
python wisdom_bridge.py list --type quote
```

### Show Tree Structure
```bash
python wisdom_bridge.py tree 5
```

### Show Statistics
```bash
python wisdom_bridge.py stats
```

## Section Guide

| Section | Degrees | Theme | Use For |
|---------|---------|-------|---------|
| 9 | 340-20° | Beginnings/Foundations | Starting points, core truths |
| 1 | 20-60° | Unity/Wholeness | Integration, harmony |
| 2 | 60-100° | Duality/Choice | Decisions, discernment |
| 3 | 100-140° | Growth/Building | Development, progress |
| 4 | 140-180° | Structure/Order | Systems, organization |
| 5 | 180-220° | Change/Adaptation | Transformation, timing |
| 6 | 220-260° | Harvest/Results | Outcomes, consequences |
| 7 | 260-300° | Mystery/Unknown | Paradoxes, deeper truths |
| 8 | 300-340° | Completion/Mastery | Peak wisdom, synthesis |

## Example Workflow

### 1. Add a quote from Proverbs
```bash
python wisdom_bridge.py add quote "Plans fail for lack of counsel, but with many advisers they succeed" --section 2 --source "Proverbs 15:22" --domain "SOLOMON"
```
**Output:** `✓ Quote added: ID 1 at θ=80° (Section 2)`

### 2. Extract a principle from that quote
```bash
python wisdom_bridge.py add principle "Isolation in decision-making leads to failure; diverse input leads to success" --section 2 --parent 1
```
**Output:** `✓ Principle added: ID 2 at θ=80° (Section 2) (from quote 1)`

### 3. Add your interpretation
```bash
python wisdom_bridge.py add interpretation "Before launching a new trading strategy, test with multiple data sets and get feedback from other traders. Don't trade in isolation." --section 2 --parent 2
```
**Output:** `✓ Interpretation added: ID 3 at θ=80° (Section 2) (from principle 2)`

### 4. View the tree
```bash
python wisdom_bridge.py tree 1
```

## Tips

- **Start small**: Add 3-5 quotes per session
- **Link carefully**: Always link principles to their source quotes
- **Be specific**: Make interpretations actionable for your situation
- **Review regularly**: Use `list` and `tree` commands to review your foundation
- **Theta offsets**: Use `--offset` to spread nodes within a section (e.g., `--offset 5` or `--offset -10`)

## Visualization

To see your wisdom nodes in the CYTO interface:
```bash
python run.py
```
Then open http://localhost:5000

- Inner ring (0.618) = Quotes (blue)
- Middle ring (1.000) = Principles (gold)
- Outer ring (1.618) = Interpretations (green)
