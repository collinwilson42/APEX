# Wisdom Framework Skill
## Foundation for Organizing Philosophical Principles in CYTO

### Purpose
A structured system for organizing quotes, principles, and interpretations using the golden ratio ring structure (0.618, 1.000, 1.618) to build a foundation of practical wisdom for decision-making.

---

## Core Structure

### Three-Ring System

**Inner Ring (0.618) - SOURCE QUOTES**
- Original text passages from source materials
- Direct quotations with attribution
- Primary evidence and source material
- Node type: `quote`
- Radius: `0.618`

**Middle Ring (1.000) - PRINCIPLES** 
- Core principles extracted from quotes
- Distilled wisdom statements
- Universal patterns and truths
- Node type: `principle`
- Radius: `1.000`

**Outer Ring (1.618) - INTERPRETATIONS**
- Personal reflections and applications
- How principles apply to specific situations
- Context-specific guidance
- Node type: `interpretation`
- Radius: `1.618`

---

## Theta Mapping (Semantic Sections)

### Section 9 (340-20°): Beginnings/Foundations
**Keywords:** foundation, start, first, beginning, origin, root
**Theme:** Where wisdom starts, foundational truths
**Example:** "The fear of the Lord is the beginning of wisdom"

### Section 1 (20-60°): Unity/Wholeness
**Keywords:** unity, wholeness, integration, harmony, peace, together
**Theme:** Principles about bringing things together
**Example:** "A house divided cannot stand"

### Section 2 (60-100°): Duality/Choice
**Keywords:** choice, decide, path, two, either, or, crossroads
**Theme:** Decision points, discernment, choosing wisely
**Example:** "Choose this day whom you will serve"

### Section 3 (100-140°): Growth/Building
**Keywords:** grow, build, plant, develop, progress, increase
**Theme:** Development over time, steady progression
**Example:** "Steady plodding brings prosperity"

### Section 4 (140-180°): Structure/Order
**Keywords:** order, system, plan, organize, structure, law
**Theme:** Systems, organization, proper arrangement
**Example:** "By wisdom a house is built"

### Section 5 (180-220°): Change/Adaptation
**Keywords:** change, adapt, season, time, transform, new
**Theme:** Transformation, timing, flexibility
**Example:** "There is a time for everything under heaven"

### Section 6 (220-260°): Harvest/Results
**Keywords:** harvest, result, consequence, fruit, reward, outcome
**Theme:** Outcomes of actions, reaping what you sow
**Example:** "As you sow, so shall you reap"

### Section 7 (260-300°): Mystery/Unknown
**Keywords:** mystery, unknown, hidden, paradox, wonder, deep
**Theme:** Paradoxes, deeper truths, accepting uncertainty
**Example:** "The secret things belong to the Lord"

### Section 8 (300-340°): Completion/Mastery
**Keywords:** complete, master, fulfill, accomplish, end, perfect
**Theme:** Peak wisdom, synthesis, bringing things full circle
**Example:** "I have finished the race, I have kept the faith"

---

## Node Relationships

### Linking Pattern
```
Quote (0.618) ← links to → Principle (1.000) ← links to → Interpretation (1.618)
```

### Example Tree:
```
QUOTE (0.618, θ=30°, Section 9):
"The fear of the Lord is the beginning of wisdom" - Proverbs 9:10

    ↓ spawns

PRINCIPLE (1.000, θ=30°, Section 9):
Wisdom requires foundational respect and humility

    ↓ spawns

INTERPRETATION (1.618, θ=30°, Section 9):
In trading: Don't let overconfidence override risk management. 
Respect the market's power. Start with humility, not hubris.
```

---

## Usage Guidelines

### When Adding Quotes
1. Read the source material
2. Identify key passages that resonate
3. Determine which section (1-9) the wisdom belongs to
4. Calculate theta within that section (manually or by feel)
5. Store as `quote` node at radius 0.618

### When Extracting Principles
1. Distill the quote to its core truth
2. Write in your own words (not copied)
3. Make it universal and timeless
4. Store as `principle` node at radius 1.000
5. Link back to source quote(s)

### When Creating Interpretations
1. Consider current life/business context
2. How does this principle apply specifically?
3. What actions or attitudes does it suggest?
4. Store as `interpretation` node at radius 1.618
5. Link back to principle

---

## Section Selection Guide

**Ask yourself:**
- What is the PRIMARY theme of this wisdom?
- What phase of a cycle does it address?
- Where would I look for this when I need it?

**Tips:**
- Beginnings → Section 9
- Endings/Completion → Section 8
- Choices/Decisions → Section 2
- Building/Progress → Section 3
- Change/Timing → Section 5

---

## Data Schema

### Quote Node
```python
{
    'node_type': 'quote',
    'content': 'Full quote text',
    'radius': 0.618,
    'theta': <calculated_theta>,
    'section': <1-9>,
    'z': 0.0,
    'w': 1,
    'domain': 'SOLOMON',  # or 'PROVERBS', 'ECCLESIASTES', etc.
    'source': 'manual'
}
```

### Principle Node
```python
{
    'node_type': 'principle',
    'content': 'Distilled principle statement',
    'radius': 1.000,
    'theta': <same_as_quote>,
    'section': <1-9>,
    'z': 0.0,
    'w': 1,
    'parent_id': <quote_node_id>,
    'source': 'manual'
}
```

### Interpretation Node
```python
{
    'node_type': 'interpretation',
    'content': 'Personal application and context',
    'radius': 1.618,
    'theta': <same_as_principle>,
    'section': <1-9>,
    'z': 0.0,
    'w': 1,
    'parent_id': <principle_node_id>,
    'source': 'manual'
}
```

---

## Benefits of This Structure

### 1. Steady Foundation
- Build wisdom gradually over time
- Each addition strengthens the whole
- No rush, just consistent progress

### 2. Clear Relationships
- Always see the source of a principle
- Trace interpretations back to original wisdom
- Understand context and derivation

### 3. Multiple Perspectives
- Same principle can have many interpretations
- Adapt wisdom to different contexts
- Build on existing foundation

### 4. Visual Organization
- Spatial arrangement helps memory
- Related concepts cluster naturally
- Easy to navigate and explore

### 5. Living System
- Update interpretations as you learn
- Add new principles as you discover them
- System grows with you

---

## Best Practices

### Solomonic Principles Applied to This Framework

**Steady Plodding**
- Add 1-3 nodes per session
- Don't rush to fill the database
- Quality over quantity

**Wisdom Through Counsel**
- Review entries periodically
- Refine interpretations based on experience
- Let the framework teach you

**Building on Solid Ground**
- Start with foundational texts
- Ensure quotes are accurate
- Verify your understanding before adding principles

**Balance and Rest**
- Don't force connections
- Let patterns emerge naturally
- Take breaks between sessions

---

## Getting Started

### Initial Setup
1. Choose a source text (e.g., Proverbs 1-9)
2. Read slowly and thoughtfully
3. Mark 3-5 passages that stand out
4. Start with Section 9 (Foundations)

### First Entries
1. Add your first quote (0.618)
2. Extract one principle (1.000)
3. Write one interpretation (1.618)
4. Link them together

### Build Gradually
- Week 1: 5-10 quotes
- Week 2: Extract principles
- Week 3: Add interpretations
- Week 4: Review and refine

---

## Example Workflow

```
1. Read Proverbs 15:22
   "Plans fail for lack of counsel, but with many advisers they succeed"

2. Identify Section: 2 (Choice/Decision) 
   θ = 80° (middle of section 2)

3. Create Quote Node (0.618, 80°)

4. Extract Principle (1.000, 80°):
   "Isolation in decision-making leads to failure; diverse input leads to success"

5. Create Interpretation (1.618, 80°):
   "Before launching a new trading strategy, test with multiple data sets and 
    get feedback from other traders. Don't trade in isolation."

6. Link: Quote → Principle → Interpretation
```

---

## Maintenance

### Weekly Review
- Browse through sections
- Update interpretations based on new experience
- Add connections between related principles

### Monthly Reflection
- Which sections need more depth?
- Which principles have proven most valuable?
- What new sources should you explore?

### Continuous Improvement
- Refine section boundaries if needed
- Adjust theta positions for better clustering
- Add cross-references between sections

---

## Remember

This framework is:
- **Practical** - For making better decisions
- **Personal** - Reflects your understanding
- **Progressive** - Grows with you over time
- **Grounded** - Based on tested wisdom
- **Balanced** - Respects both source and application

The goal is not to create a perfect system, but a **useful foundation** that supports your growth and decision-making.
