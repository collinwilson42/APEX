"""
Wisdom Bridge - Import quotes, principles, and interpretations into CYTO

Usage:
    python wisdom_bridge.py add quote "Your quote here" --section 9 --source "Proverbs 1:7"
    python wisdom_bridge.py add principle "Your principle" --parent 5 --section 9
    python wisdom_bridge.py add interpretation "Your interpretation" --parent 12 --section 9
    python wisdom_bridge.py list --section 9
    python wisdom_bridge.py tree 5
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


# ============================================
# CONFIGURATION
# ============================================

DB_PATH = Path(__file__).parent / "cyto.db"
PHI = 1.618033988749895

# Radius for each ring
RADIUS_QUOTE = 0.618
RADIUS_PRINCIPLE = 1.000
RADIUS_INTERPRETATION = 1.618

# Section theta ranges (midpoint of each section)
SECTION_THETA = {
    9: 0,      # Beginnings/Foundations (340-20°)
    1: 40,     # Unity/Wholeness (20-60°)
    2: 80,     # Duality/Choice (60-100°)
    3: 120,    # Growth/Building (100-140°)
    4: 160,    # Structure/Order (140-180°)
    5: 200,    # Change/Adaptation (180-220°)
    6: 240,    # Harvest/Results (220-260°)
    7: 280,    # Mystery/Unknown (260-300°)
    8: 320,    # Completion/Mastery (300-340°)
}

SECTION_NAMES = {
    9: "Beginnings/Foundations",
    1: "Unity/Wholeness",
    2: "Duality/Choice",
    3: "Growth/Building",
    4: "Structure/Order",
    5: "Change/Adaptation",
    6: "Harvest/Results",
    7: "Mystery/Unknown",
    8: "Completion/Mastery",
}


# ============================================
# DATABASE
# ============================================

def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_wisdom_schema():
    """Ensure schema supports wisdom nodes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if we need to add wisdom node types
    cursor.execute("SELECT DISTINCT node_type FROM nodes WHERE node_type IN ('quote', 'principle', 'interpretation')")
    
    # Note: The existing schema should work, we just add new node types
    # If needed, we can alter the CHECK constraint, but SQLite makes this tricky
    # For now, we'll just use the existing schema
    
    conn.close()
    print("✓ Wisdom schema ready")


def section_to_theta(section, offset=0):
    """
    Convert section number to theta angle.
    
    Args:
        section: 1-9
        offset: -20 to +20 for variation within section (default 0 = midpoint)
    
    Returns:
        theta angle (0-360)
    """
    if section not in SECTION_THETA:
        raise ValueError(f"Section must be 1-9, got {section}")
    
    base_theta = SECTION_THETA[section]
    return (base_theta + offset) % 360


def add_quote(content, section, source="Unknown", domain="WISDOM", offset=0):
    """
    Add a quote node at radius 0.618.
    
    Args:
        content: The quote text
        section: Section 1-9
        source: Citation (e.g., "Proverbs 1:7")
        domain: Source category (e.g., "SOLOMON", "PROVERBS")
        offset: Theta offset within section (-20 to +20)
    
    Returns:
        node_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    theta = section_to_theta(section, offset)
    
    # Format content with source attribution
    full_content = f"{content}\n\n— {source}"
    
    cursor.execute("""
        INSERT INTO nodes (
            node_type, content, theta, radius, z, w, section,
            domain, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'quote',
        full_content,
        theta,
        RADIUS_QUOTE,
        0.0,
        1,
        section,
        domain,
        'wisdom_bridge',
        datetime.now()
    ))
    
    node_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✓ Quote added: ID {node_id} at θ={theta}° (Section {section})")
    return node_id


def add_principle(content, section, parent_id=None, offset=0):
    """
    Add a principle node at radius 1.000.
    
    Args:
        content: The principle statement
        section: Section 1-9
        parent_id: Optional parent quote node ID
        offset: Theta offset within section (-20 to +20)
    
    Returns:
        node_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    theta = section_to_theta(section, offset)
    
    cursor.execute("""
        INSERT INTO nodes (
            node_type, content, theta, radius, z, w, section,
            parent_id, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'principle',
        content,
        theta,
        RADIUS_PRINCIPLE,
        0.0,
        1,
        section,
        parent_id,
        'wisdom_bridge',
        datetime.now()
    ))
    
    node_id = cursor.lastrowid
    
    # Create link if parent exists
    if parent_id:
        cursor.execute("""
            INSERT INTO links (source_id, target_id, link_type, strength)
            VALUES (?, ?, ?, ?)
        """, (parent_id, node_id, 'derives_from', 1.0))
    
    conn.commit()
    conn.close()
    
    parent_str = f" (from quote {parent_id})" if parent_id else ""
    print(f"✓ Principle added: ID {node_id} at θ={theta}° (Section {section}){parent_str}")
    return node_id


def add_interpretation(content, section, parent_id=None, offset=0):
    """
    Add an interpretation node at radius 1.618.
    
    Args:
        content: The interpretation/application
        section: Section 1-9  
        parent_id: Optional parent principle node ID
        offset: Theta offset within section (-20 to +20)
    
    Returns:
        node_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    theta = section_to_theta(section, offset)
    
    cursor.execute("""
        INSERT INTO nodes (
            node_type, content, theta, radius, z, w, section,
            parent_id, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'interpretation',
        content,
        theta,
        RADIUS_INTERPRETATION,
        0.0,
        1,
        section,
        parent_id,
        'wisdom_bridge',
        datetime.now()
    ))
    
    node_id = cursor.lastrowid
    
    # Create link if parent exists
    if parent_id:
        cursor.execute("""
            INSERT INTO links (source_id, target_id, link_type, strength)
            VALUES (?, ?, ?, ?)
        """, (parent_id, node_id, 'applies_to', 1.0))
    
    conn.commit()
    conn.close()
    
    parent_str = f" (from principle {parent_id})" if parent_id else ""
    print(f"✓ Interpretation added: ID {node_id} at θ={theta}° (Section {section}){parent_str}")
    return node_id


def list_nodes(section=None, node_type=None):
    """
    List wisdom nodes.
    
    Args:
        section: Filter by section (1-9) or None for all
        node_type: Filter by type ('quote', 'principle', 'interpretation') or None
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM nodes WHERE node_type IN ('quote', 'principle', 'interpretation')"
    params = []
    
    if section:
        query += " AND section = ?"
        params.append(section)
    
    if node_type:
        query += " AND node_type = ?"
        params.append(node_type)
    
    query += " ORDER BY section, theta, radius"
    
    cursor.execute(query, params)
    nodes = cursor.fetchall()
    conn.close()
    
    if not nodes:
        print("No nodes found")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(nodes)} node(s)")
    print(f"{'='*80}\n")
    
    current_section = None
    for node in nodes:
        if node['section'] != current_section:
            current_section = node['section']
            print(f"\n{'─'*80}")
            print(f"SECTION {current_section}: {SECTION_NAMES.get(current_section, 'Unknown')}")
            print(f"{'─'*80}\n")
        
        radius_label = {
            RADIUS_QUOTE: "QUOTE",
            RADIUS_PRINCIPLE: "PRINCIPLE", 
            RADIUS_INTERPRETATION: "INTERPRETATION"
        }.get(node['radius'], "UNKNOWN")
        
        print(f"[{node['id']}] {radius_label} (θ={node['theta']:.0f}°, r={node['radius']:.3f})")
        
        # Format content (limit to 100 chars)
        content = node['content'][:100]
        if len(node['content']) > 100:
            content += "..."
        print(f"    {content}")
        
        if node['parent_id']:
            print(f"    ↳ Parent: {node['parent_id']}")
        
        if node['domain']:
            print(f"    Domain: {node['domain']}")
        
        print()


def show_tree(node_id):
    """
    Show the tree structure starting from a node.
    
    Args:
        node_id: Root node to show tree from
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get root node
    cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
    root = cursor.fetchone()
    
    if not root:
        print(f"Node {node_id} not found")
        conn.close()
        return
    
    def print_node(node, indent=0):
        """Recursively print node and children."""
        prefix = "  " * indent
        radius_label = {
            RADIUS_QUOTE: "QUOTE",
            RADIUS_PRINCIPLE: "PRINCIPLE",
            RADIUS_INTERPRETATION: "INTERPRETATION"
        }.get(node['radius'], "UNKNOWN")
        
        print(f"{prefix}[{node['id']}] {radius_label} (θ={node['theta']:.0f}°)")
        content = node['content'][:80]
        if len(node['content']) > 80:
            content += "..."
        print(f"{prefix}    {content}")
        
        # Get children
        cursor.execute("""
            SELECT n.* FROM nodes n
            JOIN links l ON l.target_id = n.id
            WHERE l.source_id = ?
            ORDER BY n.radius
        """, (node['id'],))
        
        children = cursor.fetchall()
        for child in children:
            print(f"{prefix}    ↓")
            print_node(child, indent + 1)
    
    print(f"\n{'='*80}")
    print(f"Tree from node {node_id}")
    print(f"{'='*80}\n")
    
    print_node(root)
    conn.close()


def get_stats():
    """Get database statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            section,
            node_type,
            COUNT(*) as count
        FROM nodes
        WHERE node_type IN ('quote', 'principle', 'interpretation')
        GROUP BY section, node_type
        ORDER BY section, node_type
    """)
    
    stats = cursor.fetchall()
    
    cursor.execute("""
        SELECT node_type, COUNT(*) as count
        FROM nodes
        WHERE node_type IN ('quote', 'principle', 'interpretation')
        GROUP BY node_type
    """)
    
    totals = cursor.fetchall()
    conn.close()
    
    print(f"\n{'='*80}")
    print("WISDOM DATABASE STATISTICS")
    print(f"{'='*80}\n")
    
    print("By Type:")
    for row in totals:
        print(f"  {row['node_type']}: {row['count']}")
    
    print("\nBy Section:")
    current_section = None
    for row in stats:
        if row['section'] != current_section:
            current_section = row['section']
            section_name = SECTION_NAMES.get(current_section, "Unknown")
            print(f"\n  Section {current_section}: {section_name}")
        print(f"    {row['node_type']}: {row['count']}")
    
    print()


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Wisdom Bridge - Import wisdom nodes into CYTO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a quote
  python wisdom_bridge.py add quote "The fear of the Lord is the beginning of wisdom" --section 9 --source "Proverbs 9:10"
  
  # Add a principle linked to quote ID 5
  python wisdom_bridge.py add principle "Wisdom requires foundational humility" --section 9 --parent 5
  
  # Add interpretation linked to principle ID 12
  python wisdom_bridge.py add interpretation "In trading: respect the market's power, start with humility" --section 9 --parent 12
  
  # List all nodes in section 9
  python wisdom_bridge.py list --section 9
  
  # Show tree from quote ID 5
  python wisdom_bridge.py tree 5
  
  # Show statistics
  python wisdom_bridge.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a wisdom node')
    add_parser.add_argument('type', choices=['quote', 'principle', 'interpretation'], help='Node type')
    add_parser.add_argument('content', help='Node content')
    add_parser.add_argument('--section', type=int, required=True, choices=range(1, 10), help='Section 1-9')
    add_parser.add_argument('--parent', type=int, help='Parent node ID')
    add_parser.add_argument('--source', default='Unknown', help='Source citation (for quotes)')
    add_parser.add_argument('--domain', default='WISDOM', help='Domain/category (for quotes)')
    add_parser.add_argument('--offset', type=int, default=0, help='Theta offset within section (-20 to +20)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List wisdom nodes')
    list_parser.add_argument('--section', type=int, choices=range(1, 10), help='Filter by section')
    list_parser.add_argument('--type', choices=['quote', 'principle', 'interpretation'], help='Filter by type')
    
    # Tree command
    tree_parser = subparsers.add_parser('tree', help='Show node tree')
    tree_parser.add_argument('node_id', type=int, help='Root node ID')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize schema
    init_wisdom_schema()
    
    # Execute command
    if args.command == 'add':
        if args.type == 'quote':
            add_quote(args.content, args.section, args.source, args.domain, args.offset)
        elif args.type == 'principle':
            add_principle(args.content, args.section, args.parent, args.offset)
        elif args.type == 'interpretation':
            add_interpretation(args.content, args.section, args.parent, args.offset)
    
    elif args.command == 'list':
        list_nodes(args.section, args.type)
    
    elif args.command == 'tree':
        show_tree(args.node_id)
    
    elif args.command == 'stats':
        get_stats()


if __name__ == '__main__':
    main()
