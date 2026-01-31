# Wisdom Database - Quick Start Guide

## Overview

Your wisdom database is now set up as simple markdown files organized by section. This makes it easy to:
- Read and edit in any text editor
- Search with Windows search or grep
- Backup and version control
- Use with Obsidian later
- Query with Claude via Filesystem MCP

## Structure

```
Wisdom/
├── Quotes/
│   ├── Section_1_Unity/
│   ├── Section_2_Choice/
│   ├── Section_3_Growth/
│   ├── Section_4_Structure/
│   ├── Section_5_Change/
│   ├── Section_6_Harvest/
│   ├── Section_7_Mystery/
│   ├── Section_8_Completion/
│   └── Section_9_Foundations/
├── Principles/
├── Interpretations/
└── wisdom_manager.py
```

## Quick Commands

### Add a Quote
```bash
python wisdom_manager.py add quote "Your quote text" --section 9 --source "Proverbs 1:7" --domain "SOLOMON"
```

### Add a Principle
```bash
python wisdom_manager.py add principle "Principle Title" "Principle explanation and content" --section 9 --tags wisdom humility
```

### Add an Interpretation
```bash
python wisdom_manager.py add interpretation "Application Title" "How this applies in practice" --section 9 --context "Trading" --tags trading risk-management
```

### List Content
```bash
# List all quotes
python wisdom_manager.py list quotes

# List quotes in specific section
python wisdom_manager.py list quotes --section 9

# List all principles
python wisdom_manager.py list principles

# List all interpretations
python wisdom_manager.py list interpretations
```

### Search Everything
```bash
python wisdom_manager.py search "decision making"
python wisdom_manager.py search "humility"
python wisdom_manager.py search "trading"
```

### Show Statistics
```bash
python wisdom_manager.py stats
```

## Section Guide

| Section | Theme | Use For |
|---------|-------|---------|
| 9 | Beginnings/Foundations | Starting points, core truths |
| 1 | Unity/Wholeness | Integration, harmony |
| 2 | Choice/Decision | Decisions, discernment |
| 3 | Growth/Building | Development, progress |
| 4 | Structure/Order | Systems, organization |
| 5 | Change/Adaptation | Transformation, timing |
| 6 | Harvest/Results | Outcomes, consequences |
| 7 | Mystery/Unknown | Paradoxes, deeper truths |
| 8 | Completion/Mastery | Peak wisdom, synthesis |

## Template Files

Each section has template files showing the structure:
- `_TEMPLATE_quote.md` - In each section folder
- `_TEMPLATE_principle.md` - In Principles folder
- `_TEMPLATE_interpretation.md` - In Interpretations folder

Copy these templates and fill them in, or use the `wisdom_manager.py` commands.

## Example Workflow

### 1. Add a quote from Proverbs
```bash
cd "C:\Users\colli\Downloads\#CodeBase\Wisdom"
python wisdom_manager.py add quote "Plans fail for lack of counsel, but with many advisers they succeed" --section 2 --source "Proverbs 15:22" --domain "SOLOMON" --tags decision counsel
```

### 2. Extract a principle
```bash
python wisdom_manager.py add principle "Seek Diverse Input" "Isolation in decision-making leads to failure; diverse input leads to success" --section 2 --tags decision-making counsel collaboration
```

### 3. Create an interpretation
```bash
python wisdom_manager.py add interpretation "Trading Strategy Validation" "Before launching a strategy, test with multiple data sets and get feedback from other traders. Never trade in isolation." --section 2 --context "Trading" --tags trading strategy validation
```

### 4. View your work
```bash
python wisdom_manager.py stats
python wisdom_manager.py list quotes --section 2
```

## Using with Claude Desktop

Once the Filesystem MCP is working properly, Claude can:
- Read your wisdom files
- Search across all content
- Help you create new entries
- Suggest connections between ideas
- Reference your wisdom in conversations

Just ask: "What do my wisdom notes say about decision making?"

## Using with Obsidian (Future)

When you're ready to use Obsidian:
1. Point Obsidian to the Wisdom folder as a vault
2. The `[[link]]` syntax will create clickable connections
3. Graph view will show relationships
4. All your content will work perfectly

## Tips

- **Start small**: Add 3-5 quotes per session
- **Link deliberately**: Use `[[filename]]` to connect related content
- **Review regularly**: Use search to revisit themes
- **Refine over time**: Update interpretations as you learn
- **Keep it practical**: Focus on wisdom you'll actually use

## Backup

Simply copy the Wisdom folder to:
- OneDrive / Google Drive
- USB drive
- Git repository
- Wherever you back up important files

It's just markdown files - easy to backup and portable!

## Next Steps

1. Add your first quote from Solomon
2. Extract a principle from it
3. Write one interpretation for your trading
4. Use `stats` to see your progress
5. Build steadily over time

Remember: This is a foundation you're building. Quality over quantity. Steady progress over perfection.
