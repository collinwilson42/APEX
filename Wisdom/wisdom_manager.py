"""
Wisdom Manager - Work with markdown-based wisdom database

Usage:
    python wisdom_manager.py add quote "Your quote" --section 9 --source "Proverbs 1:7"
    python wisdom_manager.py add principle "Your principle" --section 9
    python wisdom_manager.py add interpretation "Your interpretation" --section 9
    python wisdom_manager.py list quotes --section 9
    python wisdom_manager.py list principles
    python wisdom_manager.py search "decision making"
    python wisdom_manager.py tree "principle_name"
"""

import os
import re
import argparse
from datetime import datetime
from pathlib import Path
import json

# Base wisdom directory
WISDOM_DIR = Path(r"C:\Users\colli\Downloads\#CodeBase\Wisdom")

SECTION_NAMES = {
    9: "Beginnings/Foundations",
    1: "Unity/Wholeness",
    2: "Choice/Decision",
    3: "Growth/Building",
    4: "Structure/Order",
    5: "Change/Adaptation",
    6: "Harvest/Results",
    7: "Mystery/Unknown",
    8: "Completion/Mastery",
}

def slugify(text):
    """Convert text to filename-safe slug."""
    # Remove special characters, replace spaces with underscores
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '_', text)
    return text[:50]  # Limit length

def create_quote(content, section, source="Unknown", domain="WISDOM", tags=None):
    """Create a new quote markdown file."""
    section_name = SECTION_NAMES.get(section, "Unknown")
    section_dir = WISDOM_DIR / "Quotes" / f"Section_{section}_{section_name.split('/')[0]}"
    section_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename from source
    slug = slugify(source)
    filename = f"{slug}.md"
    filepath = section_dir / filename
    
    # Check if file exists
    counter = 1
    while filepath.exists():
        filename = f"{slug}_{counter}.md"
        filepath = section_dir / filename
        counter += 1
    
    tags_list = tags if tags else ["wisdom"]
    tags_str = json.dumps(tags_list)
    
    content_md = f"""---
type: quote
section: {section}
section_name: {section_name}
source: {source}
domain: {domain}
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: {tags_str}
---

# Quote

"{content}"

## Context

*Add context about this quote here - what was happening, why it matters, historical background, etc.*

## Related Principles

*Link to principles derived from this quote:*
- [[principle_name.md]]

## Notes

*Add your personal notes and observations here.*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_md)
    
    print(f"✓ Quote created: {filepath.name}")
    print(f"  Location: {filepath}")
    return filepath

def create_principle(title, content, section, derived_from=None, tags=None):
    """Create a new principle markdown file."""
    section_name = SECTION_NAMES.get(section, "Unknown")
    principles_dir = WISDOM_DIR / "Principles"
    principles_dir.mkdir(parents=True, exist_ok=True)
    
    slug = slugify(title)
    filename = f"principle_{slug}.md"
    filepath = principles_dir / filename
    
    counter = 1
    while filepath.exists():
        filename = f"principle_{slug}_{counter}.md"
        filepath = principles_dir / filename
        counter += 1
    
    tags_list = tags if tags else ["wisdom"]
    tags_str = json.dumps(tags_list)
    
    derived_str = ""
    if derived_from:
        derived_str = f"\nderived_from:\n  - [[{derived_from}]]"
    
    content_md = f"""---
type: principle
section: {section}
section_name: {section_name}
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: {tags_str}{derived_str}
---

# Principle: {title}

{content}

## Core Insight

*Explain the core insight of this principle - what makes it universally true?*

## Universal Applications

- In learning: ...
- In relationships: ...
- In business: ...
- In life: ...

## Related Quotes

*Link to source quotes:*
- [[quote_file.md]]

## Related Principles

*Link to related principles:*
- [[other_principle.md]]

## Interpretations

*Link to specific interpretations:*
- [[interpretation_file.md]]
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_md)
    
    print(f"✓ Principle created: {filepath.name}")
    print(f"  Location: {filepath}")
    return filepath

def create_interpretation(title, content, section, context="General", derived_from=None, tags=None):
    """Create a new interpretation markdown file."""
    section_name = SECTION_NAMES.get(section, "Unknown")
    interp_dir = WISDOM_DIR / "Interpretations"
    interp_dir.mkdir(parents=True, exist_ok=True)
    
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = interp_dir / filename
    
    counter = 1
    while filepath.exists():
        filename = f"{slug}_{counter}.md"
        filepath = interp_dir / filename
        counter += 1
    
    tags_list = tags if tags else ["application"]
    tags_str = json.dumps(tags_list)
    
    derived_str = ""
    if derived_from:
        derived_str = f"\nderived_from:\n  - [[{derived_from}]]"
    
    content_md = f"""---
type: interpretation
section: {section}
section_name: {section_name}
date_added: {datetime.now().strftime('%Y-%m-%d')}
tags: {tags_str}
context: {context}{derived_str}
---

# Interpretation: {title}

## Principle Applied

*State which principle this interprets and how it applies*

{content}

## Specific Application

**Actionable steps:**
1. ...
2. ...
3. ...

## Real-World Example

*Describe a concrete example of applying this interpretation*

## Key Takeaway

*One-sentence summary of the practical wisdom*

## Related Interpretations

*Link to related interpretations:*
- [[other_interpretation.md]]

## Review Notes

*Add notes on how this has worked in practice, refinements needed, etc.*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_md)
    
    print(f"✓ Interpretation created: {filepath.name}")
    print(f"  Location: {filepath}")
    return filepath

def list_files(file_type, section=None):
    """List wisdom files of a given type."""
    if file_type == "quotes":
        if section:
            section_name = SECTION_NAMES.get(section, "Unknown")
            search_dir = WISDOM_DIR / "Quotes" / f"Section_{section}_{section_name.split('/')[0]}"
        else:
            search_dir = WISDOM_DIR / "Quotes"
    elif file_type == "principles":
        search_dir = WISDOM_DIR / "Principles"
    elif file_type == "interpretations":
        search_dir = WISDOM_DIR / "Interpretations"
    else:
        print(f"Unknown type: {file_type}")
        return
    
    if not search_dir.exists():
        print(f"No files found in {search_dir}")
        return
    
    files = list(search_dir.rglob("*.md"))
    files = [f for f in files if not f.name.startswith("_TEMPLATE")]
    
    if not files:
        print(f"No {file_type} found")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(files)} {file_type}")
    print(f"{'='*80}\n")
    
    for filepath in sorted(files):
        # Read frontmatter
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract title from first header
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else filepath.stem
        
        # Extract section from frontmatter
        section_match = re.search(r'^section:\s+(\d+)', content, re.MULTILINE)
        section_num = section_match.group(1) if section_match else "?"
        
        print(f"[Section {section_num}] {title}")
        print(f"    {filepath.relative_to(WISDOM_DIR)}")
        print()

def search_content(query):
    """Search across all wisdom files."""
    results = []
    
    for filepath in WISDOM_DIR.rglob("*.md"):
        if filepath.name.startswith("_TEMPLATE"):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if query.lower() in content.lower():
            # Extract title
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else filepath.stem
            
            # Extract section
            section_match = re.search(r'^section:\s+(\d+)', content, re.MULTILINE)
            section_num = section_match.group(1) if section_match else "?"
            
            # Find matching lines
            lines = content.split('\n')
            matches = [line for line in lines if query.lower() in line.lower()]
            
            results.append({
                'file': filepath,
                'title': title,
                'section': section_num,
                'matches': matches[:3]  # First 3 matches
            })
    
    if not results:
        print(f"No matches found for '{query}'")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(results)} matches for '{query}'")
    print(f"{'='*80}\n")
    
    for result in results:
        print(f"[Section {result['section']}] {result['title']}")
        print(f"    {result['file'].relative_to(WISDOM_DIR)}")
        for match in result['matches']:
            print(f"    ... {match.strip()[:80]} ...")
        print()

def show_stats():
    """Show database statistics."""
    stats = {
        'quotes': 0,
        'principles': 0,
        'interpretations': 0,
        'by_section': {i: 0 for i in range(1, 10)}
    }
    
    for filepath in WISDOM_DIR.rglob("*.md"):
        if filepath.name.startswith("_TEMPLATE"):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        type_match = re.search(r'^type:\s+(\w+)', content, re.MULTILINE)
        if type_match:
            file_type = type_match.group(1)
            if file_type in stats:
                stats[file_type] += 1
        
        section_match = re.search(r'^section:\s+(\d+)', content, re.MULTILINE)
        if section_match:
            section = int(section_match.group(1))
            if section in stats['by_section']:
                stats['by_section'][section] += 1
    
    print(f"\n{'='*80}")
    print("WISDOM DATABASE STATISTICS")
    print(f"{'='*80}\n")
    
    print("By Type:")
    print(f"  Quotes: {stats['quotes']}")
    print(f"  Principles: {stats['principles']}")
    print(f"  Interpretations: {stats['interpretations']}")
    print(f"  Total: {sum([stats['quotes'], stats['principles'], stats['interpretations']])}")
    
    print("\nBy Section:")
    for section, count in stats['by_section'].items():
        if count > 0:
            print(f"  Section {section} ({SECTION_NAMES[section]}): {count}")
    print()

def main():
    parser = argparse.ArgumentParser(
        description="Wisdom Manager - Markdown-based wisdom database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a quote
  python wisdom_manager.py add quote "Plans fail for lack of counsel" --section 2 --source "Proverbs 15:22"
  
  # Add a principle
  python wisdom_manager.py add principle "Seek diverse input" "Isolation in decisions leads to failure" --section 2
  
  # Add interpretation
  python wisdom_manager.py add interpretation "Trading strategy testing" "Test with multiple data sets" --section 2 --context "Trading"
  
  # List quotes in section 9
  python wisdom_manager.py list quotes --section 9
  
  # Search all files
  python wisdom_manager.py search "decision"
  
  # Show statistics
  python wisdom_manager.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add wisdom content')
    add_parser.add_argument('type', choices=['quote', 'principle', 'interpretation'], help='Content type')
    add_parser.add_argument('title', help='Title or content')
    add_parser.add_argument('content', nargs='?', help='Additional content (for principle/interpretation)')
    add_parser.add_argument('--section', type=int, required=True, choices=range(1, 10), help='Section 1-9')
    add_parser.add_argument('--source', default='Unknown', help='Source citation (for quotes)')
    add_parser.add_argument('--domain', default='WISDOM', help='Domain/category (for quotes)')
    add_parser.add_argument('--context', default='General', help='Application context (for interpretations)')
    add_parser.add_argument('--tags', nargs='+', help='Tags for the content')
    add_parser.add_argument('--from', dest='derived_from', help='Source file this is derived from')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List wisdom content')
    list_parser.add_argument('type', choices=['quotes', 'principles', 'interpretations'], help='Content type')
    list_parser.add_argument('--section', type=int, choices=range(1, 10), help='Filter by section')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search all content')
    search_parser.add_argument('query', help='Search query')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'add':
        if args.type == 'quote':
            create_quote(args.title, args.section, args.source, args.domain, args.tags)
        elif args.type == 'principle':
            if not args.content:
                print("Error: principle requires both title and content")
                return
            create_principle(args.title, args.content, args.section, args.derived_from, args.tags)
        elif args.type == 'interpretation':
            if not args.content:
                print("Error: interpretation requires both title and content")
                return
            create_interpretation(args.title, args.content, args.section, args.context, args.derived_from, args.tags)
    
    elif args.command == 'list':
        list_files(args.type, args.section)
    
    elif args.command == 'search':
        search_content(args.query)
    
    elif args.command == 'stats':
        show_stats()

if __name__ == '__main__':
    main()
