"""
Add context to all wisdom quotes
"""
from pathlib import Path
import re

WISDOM_DIR = Path(r"C:\Users\colli\Downloads\#CodeBase\Wisdom")

# Context data for each quote
contexts = {
    "proverbs_1_7": {
        "context": "This opens the Book of Proverbs, setting the stage for all wisdom that follows. Solomon contrasts two paths: those who seek wisdom through humility, and fools who reject instruction. The word 'fool' here doesn't mean lacking intelligence, but rather someone who rejects wisdom due to pride or stubbornness.",
        "notes": "In trading: The 'fools' are those who refuse to learn from losses, ignore risk management, and think they're smarter than the market. True knowledge starts with acknowledging what you don't know."
    },
    "proverbs_3_5": {
        "context": "This verse counsels against over-reliance on your own analysis and judgment. While intelligence and planning are valuable, Solomon warns against trusting solely in your own understanding without considering broader perspectives or the possibility you're wrong.",
        "notes": "In trading: Trust your system, but don't trust your ego. Your analysis might be flawed. Your emotions might cloud judgment. Build systematic approaches that account for your own limitations."
    },
    "proverbs_9_10": {
        "context": "This verse establishes the foundational principle that true wisdom begins with proper respect, reverence, and humility. It's not about fear in the sense of terror, but about having appropriate awe and respect for forces greater than ourselves.",
        "notes": "This is the cornerstone quote for understanding the nature of wisdom. Without humility and recognition of our limitations, we cannot truly learn or grow."
    },
    "proverbs_11_29": {
        "context": "Solomon observes that internal conflict and division destroys from within. A house, family, business, or mind that is divided against itself cannot stand under pressure. Unity and coherence are necessary for strength.",
        "notes": "In trading: If your strategy conflicts with your risk management, or your emotions conflict with your plan, you'll fail. Internal coherence between strategy, execution, and psychology is essential."
    },
    "ecclesiastes_4_9": {
        "context": "The Preacher (traditionally Solomon) reflects on the value of partnership and community. Working together produces better returns than working alone. When one person struggles or falls, having support makes the critical difference.",
        "notes": "In trading: Share ideas with other traders. Get feedback on strategies. Have accountability partners. Isolation leads to blind spots and emotional decisions."
    },
    "ecclesiastes_4_12": {
        "context": "Continuing the theme of partnership, this verse uses the metaphor of rope construction. A single strand breaks easily, two strands are stronger, but three strands woven together create something remarkably durable.",
        "notes": "Multiple sources of validation create robust decisions. In trading: technical + fundamental + sentiment analysis creates stronger conviction than any single factor."
    },
    "proverbs_15_22": {
        "context": "Solomon directly addresses decision-making and planning. Plans made in isolation, without input from others, tend to fail. Success comes from gathering diverse counsel and perspectives before committing to action.",
        "notes": "Before launching a trading strategy: backtest it, forward test it, get peer review, test on different timeframes, validate assumptions. Plans fail when you skip these steps."
    },
    "proverbs_12_15": {
        "context": "This verse contrasts the fool who is certain of their own rightness with the wise person who actively seeks and listens to advice. The fool's confidence is their downfall; the wise person's humility is their strength.",
        "notes": "When you're certain you're right without checking with others, you're in danger. The best traders constantly seek feedback and alternative viewpoints."
    },
    "proverbs_13_10": {
        "context": "Solomon identifies pride as the root of strife and conflict. Where pride exists, people argue rather than collaborate. But those who can set aside ego and genuinely consider advice find wisdom.",
        "notes": "In trading: Pride makes you marry your positions, refuse to cut losses, and ignore warning signs. Humility lets you adapt, learn, and improve."
    },
    "proverbs_14_15": {
        "context": "The simple (naive) person believes whatever they hear without verification. The prudent person thinks carefully, considers consequences, and validates information before acting.",
        "notes": "Don't believe every 'hot tip' or market prediction. Do your own analysis. Verify data. Think through implications. Test before trusting."
    },
    "proverbs_21_5": {
        "context": "Solomon contrasts two approaches: steady, diligent work versus hasty speculation and shortcuts. The patient plodder builds wealth over time; the speculator rushes to poverty.",
        "notes": "Trading application: Build edge systematically. Test thoroughly. Scale gradually. Get rich slow. The traders who try to get rich quick usually go broke quick."
    },
    "proverbs_24_3": {
        "context": "Solomon uses the metaphor of house-building for life and wealth creation. Wisdom provides the foundation and framework. Understanding establishes it firmly. Knowledge fills it with valuable things.",
        "notes": "In trading: Wisdom = understanding market principles. Understanding = grasping your edge. Knowledge = mastering execution details. Build the foundation before adding complexity."
    },
    "proverbs_24_27": {
        "context": "Agricultural wisdom applied to life: prepare your fields and ensure income before building your house. Get the fundamentals working before expanding. Foundation before flourish.",
        "notes": "In trading: Prove your strategy works with small size before scaling up. Ensure consistent profitability before adding complexity or capital."
    },
    "proverbs_10_14": {
        "context": "The wise accumulate knowledge over time, building a reservoir of understanding. The fool speaks without knowledge and invites disaster through ignorant actions.",
        "notes": "Keep a trading journal. Document what works and why. Study your losses. Build a knowledge base. The fool repeats mistakes; the wise learn from them."
    },
    "proverbs_16_3": {
        "context": "When you commit your work to something greater than yourself—a higher purpose, a systematic approach, proven principles—your plans have a better foundation for success.",
        "notes": "Commit to the process, not the outcome. Trust your tested system rather than trying to predict each trade. Let go of control; follow the method."
    },
    "proverbs_16_9": {
        "context": "Humans make plans, but ultimate outcomes depend on factors beyond our control. This isn't fatalism—it's realism. Plan wisely, but hold plans loosely.",
        "notes": "You can plan your trade setup, but you can't control what the market does. Accept uncertainty. Manage risk. Adapt as conditions change."
    },
    "proverbs_27_12": {
        "context": "The prudent person sees danger coming and takes protective action. The simple (naive) person ignores warning signs and suffers consequences. Awareness and preemptive action are marks of wisdom.",
        "notes": "In trading: See danger = use stop losses. Take refuge = reduce position size, hedge, or exit. Don't ignore warning signals just because you want the trade to work."
    },
    "ecclesiastes_3_1": {
        "context": "The Preacher observes that time has natural rhythms and seasons. Everything has its appropriate time. Forcing action in the wrong season leads to failure.",
        "notes": "Not every market condition suits your strategy. Some seasons are for action, some for patience. Know which season you're in."
    },
    "ecclesiastes_3_2": {
        "context": "Life has beginnings and endings, planting seasons and harvest seasons. Trying to harvest when you should be planting, or plant when you should harvest, leads to failure.",
        "notes": "In trading: There's a time to plant capital (enter positions) and a time to harvest profits (exit). There's a time to build systems and a time to execute them."
    },
    "ecclesiastes_3_3": {
        "context": "Some circumstances require tearing down what isn't working before you can build something better. Some situations call for mourning; others for celebration. Wisdom is knowing which is appropriate now.",
        "notes": "Sometimes you need to tear down a losing strategy before building a new one. Sometimes you need to process a loss before moving forward. Honor the season."
    },
    "proverbs_11_25": {
        "context": "Generosity creates abundance. Those who help others prosper themselves. Those who refresh others find refreshment. This isn't just moral teaching—it's an observed pattern of success.",
        "notes": "In trading community: Share what works. Help others learn. The knowledge you give away strengthens your own understanding. Abundance mindset beats scarcity."
    },
    "proverbs_18_9": {
        "context": "Being lazy or half-hearted in your work makes you akin to someone who actively destroys. Slack work and destructive work end in the same place: ruin.",
        "notes": "Half-hearted trading—not following your rules, being sloppy with risk management—is as destructive as deliberately sabotaging your account."
    },
    "proverbs_12_11": {
        "context": "Those who work their actual land (do real work on real things) will have food. Those who chase fantasies (get-rich-quick schemes, unrealistic dreams) lack sense and substance.",
        "notes": "Work on your actual trading edge—backtesting, journaling, risk management. Don't chase the fantasy of easy profits or holy grail systems."
    },
    "ecclesiastes_11_1": {
        "context": "A mysterious proverb about investment and patience. Cast your bread (invest your resources) on waters (uncertain places). After time passes, you'll find returns. Trust the process over time.",
        "notes": "Invest in your development. Build systems. Be patient. Results come from consistent effort over time, not from one perfect trade."
    },
    "proverbs_25_2": {
        "context": "God conceals mysteries; it's glorious for humans to search them out and discover truth. Not everything is obvious. Some understanding requires effort, research, and investigation.",
        "notes": "Edge in trading isn't obvious. You have to dig for it. Research, test, investigate. The best opportunities are often hidden in data others ignore."
    },
    "ecclesiastes_8_16": {
        "context": "The Preacher observes that despite applying his mind to wisdom, he cannot comprehend everything. Some things remain mysterious. Complete understanding is impossible.",
        "notes": "You'll never understand the market completely. Accept mystery. Focus on what you can know and manage. Let go of needing to predict everything."
    },
    "ecclesiastes_12_13": {
        "context": "After exploring life's mysteries and paradoxes, the Preacher gives his final conclusion: respect what's greater than you and follow proven principles. This is the essential duty.",
        "notes": "After all the analysis, backtesting, and strategy development, the conclusion is simple: respect the market, follow your rules, manage your risk. That's the duty."
    },
    "ecclesiastes_7_8": {
        "context": "Finishing something is more important than starting it enthusiastically. Patience is more valuable than pride in the long run. Completion beats intention.",
        "notes": "In trading: Following through on your complete trading plan (entry, management, exit) is more important than finding the perfect entry. Patience beats ego."
    },
    "proverbs_27_17": {
        "context": "Just as iron sharpens iron through friction and interaction, people sharpen each other through dialogue, challenge, and collaboration. Growth requires interaction.",
        "notes": "Engage with other traders. Welcome critique of your strategies. Challenge and be challenged. Growth happens through friction, not isolation."
    }
}

def update_quote_context(filepath, slug):
    """Update a quote file with proper context."""
    if slug not in contexts:
        print(f"⚠ No context for {slug}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the context placeholder
    content = re.sub(
        r'\*Add your notes about this quote\'s context and meaning\*',
        contexts[slug]['context'],
        content
    )
    
    # Replace the notes placeholder
    content = re.sub(
        r'\*Your personal observations\*',
        contexts[slug]['notes'],
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated {slug}")

# Update all quote files
quotes_dir = WISDOM_DIR / "Quotes"
for section_dir in quotes_dir.iterdir():
    if section_dir.is_dir() and not section_dir.name.startswith('_'):
        for quote_file in section_dir.iterdir():
            if quote_file.suffix == '.md' and not quote_file.name.startswith('_TEMPLATE'):
                slug = quote_file.stem
                update_quote_context(quote_file, slug)

print("\n✓ All quotes updated with context!")
