"""
Quick populate script - creates all wisdom files directly
"""
from pathlib import Path
from datetime import datetime

WISDOM_DIR = Path(r"C:\Users\colli\Downloads\#CodeBase\Wisdom")

# All quotes data
quotes = [
    ("Section_9_Foundations", "proverbs_1_7", 9, "Proverbs 1:7", "The fear of the Lord is the beginning of knowledge, but fools despise wisdom and instruction."),
    ("Section_9_Foundations", "proverbs_3_5", 9, "Proverbs 3:5", "Trust in the Lord with all your heart and lean not on your own understanding."),
    
    ("Section_1_Unity", "proverbs_11_29", 1, "Proverbs 11:29", "A house divided against itself cannot stand."),
    ("Section_1_Unity", "ecclesiastes_4_9", 1, "Ecclesiastes 4:9-10", "Two are better than one, because they have a good return for their labor: If either of them falls down, one can help the other up."),
    ("Section_1_Unity", "ecclesiastes_4_12", 1, "Ecclesiastes 4:12", "A cord of three strands is not quickly broken."),
    
    ("Section_2_Choice", "proverbs_15_22", 2, "Proverbs 15:22", "Plans fail for lack of counsel, but with many advisers they succeed."),
    ("Section_2_Choice", "proverbs_12_15", 2, "Proverbs 12:15", "The way of fools seems right to them, but the wise listen to advice."),
    ("Section_2_Choice", "proverbs_13_10", 2, "Proverbs 13:10", "Where there is strife, there is pride, but wisdom is found in those who take advice."),
    ("Section_2_Choice", "proverbs_14_15", 2, "Proverbs 14:15", "The simple believe anything, but the prudent give thought to their steps."),
    
    ("Section_3_Growth", "proverbs_21_5", 3, "Proverbs 21:5", "Steady plodding brings prosperity; hasty speculation brings poverty."),
    ("Section_3_Growth", "proverbs_24_3", 3, "Proverbs 24:3-4", "By wisdom a house is built, and through understanding it is established; through knowledge its rooms are filled with rare and beautiful treasures."),
    ("Section_3_Growth", "proverbs_24_27", 3, "Proverbs 24:27", "Finish your outdoor work and get your fields ready; after that, build your house."),
    
    ("Section_4_Structure", "proverbs_10_14", 4, "Proverbs 10:14", "The wise store up knowledge, but the mouth of a fool invites ruin."),
    ("Section_4_Structure", "proverbs_16_3", 4, "Proverbs 16:3", "Commit to the Lord whatever you do, and he will establish your plans."),
    ("Section_4_Structure", "proverbs_16_9", 4, "Proverbs 16:9", "In their hearts humans plan their course, but the Lord establishes their steps."),
    ("Section_4_Structure", "proverbs_27_12", 4, "Proverbs 27:12", "The prudent see danger and take refuge, but the simple keep going and pay the penalty."),
    
    ("Section_5_Change", "ecclesiastes_3_1", 5, "Ecclesiastes 3:1", "There is a time for everything, and a season for every activity under the heavens."),
    ("Section_5_Change", "ecclesiastes_3_2", 5, "Ecclesiastes 3:2", "A time to be born and a time to die, a time to plant and a time to uproot."),
    ("Section_5_Change", "ecclesiastes_3_3", 5, "Ecclesiastes 3:3-4", "A time to tear down and a time to build, a time to weep and a time to laugh."),
    
    ("Section_6_Harvest", "proverbs_11_25", 6, "Proverbs 11:25", "A generous person will prosper; whoever refreshes others will be refreshed."),
    ("Section_6_Harvest", "proverbs_18_9", 6, "Proverbs 18:9", "One who is slack in his work is brother to one who destroys."),
    ("Section_6_Harvest", "proverbs_12_11", 6, "Proverbs 12:11", "Those who work their land will have abundant food, but those who chase fantasies have no sense."),
    ("Section_6_Harvest", "ecclesiastes_11_1", 6, "Ecclesiastes 11:1", "Cast your bread upon the waters, for after many days you will find it again."),
    
    ("Section_7_Mystery", "proverbs_25_2", 7, "Proverbs 25:2", "It is the glory of God to conceal a matter; to search out a matter is the glory of kings."),
    ("Section_7_Mystery", "ecclesiastes_8_16", 7, "Ecclesiastes 8:16-17", "When I applied my mind to know wisdom, I saw all that God has done. No one can comprehend what goes on under the sun."),
    
    ("Section_8_Completion", "ecclesiastes_12_13", 8, "Ecclesiastes 12:13", "Now all has been heard; here is the conclusion of the matter: Fear God and keep his commandments, for this is the duty of all mankind."),
    ("Section_8_Completion", "ecclesiastes_7_8", 8, "Ecclesiastes 7:8", "The end of a matter is better than its beginning, and patience is better than pride."),
    ("Section_8_Completion", "proverbs_27_17", 8, "Proverbs 27:17", "As iron sharpens iron, so one person sharpens another."),
]

print("Creating quote files...")
for section_dir, slug, section_num, source, content in quotes:
    filepath = WISDOM_DIR / "Quotes" / section_dir / f"{slug}.md"
    
    md_content = f"""---
type: quote
section: {section_num}
source: {source}
domain: SOLOMON
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: ["wisdom", "solomon"]
---

# Quote

"{content}"

## Context

*Add your notes about this quote's context and meaning*

## Related Principles

*Link principles derived from this quote*

## Notes

*Your personal observations*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ {slug}.md")

# Create principles
principles_data = [
    ("foundational_humility", 9, "Foundational Humility", "True wisdom requires respect and humility. Overconfidence blocks growth."),
    ("seek_diverse_counsel", 2, "Seek Diverse Counsel", "Isolation in decision-making leads to failure. Success comes through diverse perspectives."),
    ("steady_progress", 3, "Steady Progress Over Haste", "Sustainable success comes from consistent effort, not rushing or speculation."),
    ("proper_timing", 5, "Proper Timing and Seasons", "Everything has its appropriate time. Wisdom includes knowing when to act and when to wait."),
    ("work_produces_results", 6, "Work Produces Results", "Diligent work on real tasks produces results. Chasing fantasies leads nowhere."),
]

print("\nCreating principle files...")
for slug, section, title, content in principles_data:
    filepath = WISDOM_DIR / "Principles" / f"principle_{slug}.md"
    
    md_content = f"""---
type: principle
section: {section}
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: ["wisdom", "principle"]
---

# Principle: {title}

{content}

## Core Insight

*Explain what makes this universally true*

## Universal Applications

- **In learning:** ...
- **In relationships:** ...
- **In business:** ...
- **In trading:** ...

## Related Quotes

*Link source quotes*

## Interpretations

*Link specific applications*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ principle_{slug}.md")

# Create interpretations
interp_data = [
    ("trading_risk_management", 9, "Trading Risk Management", "Respect the market's power. Start with humility, not hubris."),
    ("strategy_validation", 2, "Strategy Validation", "Test with multiple data sets. Get feedback. Never trade in isolation."),
    ("incremental_systems", 3, "Building Systems Incrementally", "Start small. Validate live. Scale only after proving consistency."),
    ("market_timing", 5, "Market Timing and Patience", "Not every moment is right for trading. Wait for high-probability setups."),
    ("process_focus", 6, "Focus on Process", "Work on real edge: data, systems, risk management. Not quick-profit fantasies."),
]

print("\nCreating interpretation files...")
for slug, section, title, content in interp_data:
    filepath = WISDOM_DIR / "Interpretations" / f"{slug}.md"
    
    md_content = f"""---
type: interpretation
section: {section}
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: ["trading", "application"]
context: Trading
---

# Interpretation: {title}

## Principle Applied

{content}

## Specific Application

**In practice:**
1. ...
2. ...
3. ...

## Real-World Example

*Describe when you applied this*

## Key Takeaway

**{content}**

## Review Notes

*Track how this works in practice*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ {slug}.md")

print("\n" + "="*60)
print("✓ Created 25+ quotes across all sections")
print("✓ Created 5 principles")
print("✓ Created 5 interpretations")
print("="*60)
print("\nRun: python wisdom_manager.py stats")
