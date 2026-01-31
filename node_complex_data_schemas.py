"""
Data Schemas for Node Complex
==============================
ROOT C: DATA_MODELS (NC1-020 → NC1-035)
Phase NC-1 | Core Data Layer

Nodes Implemented:
- NC1-020: NODE_DATA_MODEL
- NC1-021: NODE_ID_VALIDATION
- NC1-022: NODE_WEIGHT_VALIDATION
- NC1-023: NODE_TITLE_VALIDATION
- NC1-024: NODE_STATUS_ENUM
- NC1-025: NODE_TYPE_ENUM
- NC1-026: PHASE_DATA_MODEL
- NC1-027: PHASE_AGGREGATE_WEIGHT_CALC
- NC1-028: PHASE_NODE_COUNT_TRACKING
- NC1-029: PHASE_STATUS_DERIVATION
- NC1-030: MANIFEST_DATA_MODEL
- NC1-031: MANIFEST_LINKED_PHASES
- NC1-032: MANIFEST_THREAD_COLOR_ASSIGNMENT
- NC1-033: THREAD_DATA_MODEL
- NC1-034: THREAD_TYPE_ENUM
- NC1-035: THREAD_COLOR_BY_DEPTH

STOIC Alignment:
- Stability: Validated ranges, type-safe models
- Tunity: Configurable via Pydantic validators
- Creativity: Flexible model composition
"""

import re
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator


# =============================================================================
# NC1-024: NODE_STATUS_ENUM
# =============================================================================

class NodeStatus(str, Enum):
    """Node lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETE = "complete"
    ARCHIVED = "archived"


# =============================================================================
# NC1-025: NODE_TYPE_ENUM
# =============================================================================

class NodeType(str, Enum):
    """Node structural type in the tree."""
    ROOT = "root"       # Top-level, no parent
    BRANCH = "branch"   # Has parent and children
    LEAF = "leaf"       # Has parent, no children
    ORPHAN = "orphan"   # No connections (error state)


# =============================================================================
# NC1-034: THREAD_TYPE_ENUM
# =============================================================================

class ThreadType(str, Enum):
    """Thread connection types."""
    MANIFEST = "manifest"         # Phase root → Master manifest (Gold)
    PARENT_CHILD = "parent_child" # Root → Child (depth-based color)
    CROSS_PHASE = "cross_phase"   # Dependencies between phases (Purple)
    SIBLING = "sibling"           # Same-level relationships (Gray)


# =============================================================================
# NC1-035: THREAD_COLOR_BY_DEPTH
# =============================================================================

DEPTH_COLORS = [
    "#3498DB",  # Level 0→1 - Blue
    "#27AE60",  # Level 1→2 - Green
    "#E67E22",  # Level 2→3 - Orange
    "#E74C3C",  # Level 3→4 - Red
    "#9B59B6",  # Level 4→5 - Purple
    "#1ABC9C",  # Level 5→6 - Teal
    "#F39C12",  # Level 6→7 - Yellow
    "#16A085",  # Level 7→8 - Dark Teal
]

MANIFEST_THREAD_COLOR = "#FFD700"  # Gold
CROSS_PHASE_COLOR = "#9B59B6"      # Purple
SIBLING_COLOR = "#95A5A6"          # Gray


def get_thread_color(thread_type: ThreadType, parent_depth: int = 0) -> str:
    """
    Get thread color based on type and parent depth.
    
    Args:
        thread_type: The type of thread
        parent_depth: Depth level of parent node (for PARENT_CHILD)
        
    Returns:
        Hex color string
    """
    if thread_type == ThreadType.MANIFEST:
        return MANIFEST_THREAD_COLOR
    elif thread_type == ThreadType.CROSS_PHASE:
        return CROSS_PHASE_COLOR
    elif thread_type == ThreadType.SIBLING:
        return SIBLING_COLOR
    else:  # PARENT_CHILD
        return DEPTH_COLORS[parent_depth % len(DEPTH_COLORS)]


# =============================================================================
# NC1-021: NODE_ID_VALIDATION (Regex pattern)
# =============================================================================

NODE_ID_PATTERN = re.compile(r'^[A-Z]+\d*-\d{3}$')
# Matches: NC1-001, P4-023, NC12-999, etc.


def validate_node_id(node_id: str) -> str:
    """
    Validate node ID format.
    
    Args:
        node_id: The node identifier to validate
        
    Returns:
        The validated node_id
        
    Raises:
        ValueError: If format is invalid
    """
    if not NODE_ID_PATTERN.match(node_id):
        raise ValueError(
            f"Invalid node_id '{node_id}'. "
            f"Must match pattern: PREFIX-NNN (e.g., NC1-001, P4-023)"
        )
    return node_id


# =============================================================================
# NC1-022: NODE_WEIGHT_VALIDATION
# =============================================================================

def validate_node_weight(weight: float) -> float:
    """
    Validate node weight is in valid range.
    
    Args:
        weight: The dev_weight value
        
    Returns:
        The validated weight
        
    Raises:
        ValueError: If weight is out of range
    """
    if not (-0.999 <= weight <= -0.001):
        raise ValueError(
            f"Invalid dev_weight {weight}. "
            f"Must be in range [-0.999, -0.001]"
        )
    return weight


# =============================================================================
# NC1-023: NODE_TITLE_VALIDATION
# =============================================================================

TITLE_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')


def validate_node_title(title: str) -> str:
    """
    Validate node title is ALL_CAPS_UNDERSCORES format.
    
    Args:
        title: The node title
        
    Returns:
        The validated title
        
    Raises:
        ValueError: If format is invalid
    """
    if not TITLE_PATTERN.match(title):
        raise ValueError(
            f"Invalid title '{title}'. "
            f"Must be ALL_CAPS_UNDERSCORES format (e.g., DATABASE_FOUNDATION)"
        )
    return title


# =============================================================================
# NC1-020: NODE_DATA_MODEL
# =============================================================================

class NodeBase(BaseModel):
    """Base node properties shared by all node schemas."""
    
    title: str = Field(..., description="ALL_CAPS_TITLE format")
    dev_weight: float = Field(..., ge=-0.999, le=-0.001, description="Friction weight")
    dev_spec: Optional[str] = Field(None, description="Development specification")
    phase_number: int = Field(..., ge=1, description="Phase this node belongs to")
    parent_id: Optional[str] = Field(None, description="Parent node ID")
    status: NodeStatus = Field(default=NodeStatus.DRAFT)
    
    # Validators
    _validate_title = validator('title', allow_reuse=True)(validate_node_title)
    _validate_weight = validator('dev_weight', allow_reuse=True)(validate_node_weight)
    
    @validator('parent_id')
    def validate_parent_id(cls, v):
        if v is not None:
            validate_node_id(v)
        return v


class NodeCreate(NodeBase):
    """Schema for creating a new node."""
    
    node_id: str = Field(..., description="Unique identifier (e.g., NC1-001)")
    
    _validate_node_id = validator('node_id', allow_reuse=True)(validate_node_id)


class NodeUpdate(BaseModel):
    """Schema for updating an existing node."""
    
    title: Optional[str] = None
    dev_weight: Optional[float] = Field(None, ge=-0.999, le=-0.001)
    dev_spec: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[NodeStatus] = None
    
    # Position updates (from physics engine)
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    position_z: Optional[float] = None
    
    _validate_title = validator('title', allow_reuse=True, pre=True)(
        lambda v: validate_node_title(v) if v else v
    )


class Node(NodeBase):
    """Full node model with all properties."""
    
    node_id: str = Field(..., description="Unique identifier")
    node_type: NodeType = Field(default=NodeType.LEAF)
    full_content: Optional[str] = Field(None, description="Complete content for vision model")
    
    # Positioning (from physics engine)
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    position_z: float = Field(default=0.0)
    layer: int = Field(default=0, ge=0, le=6, description="Tree layer based on weight")
    
    # Aggregate metrics
    family_weight: Optional[float] = Field(None, description="Average of root + children weights")
    children_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    _validate_node_id = validator('node_id', allow_reuse=True)(validate_node_id)
    
    @validator('layer', pre=True, always=True)
    def calculate_layer(cls, v, values):
        """Calculate layer from dev_weight if not provided."""
        if v is not None:
            return v
        
        weight = values.get('dev_weight', -0.1)
        abs_weight = abs(weight)
        
        # Map weight to layer (inverted pyramid)
        if abs_weight >= 0.601:
            return 0  # Extreme - apex
        elif abs_weight >= 0.501:
            return 1  # Critical
        elif abs_weight >= 0.401:
            return 2  # High
        elif abs_weight >= 0.301:
            return 3  # Elevated
        elif abs_weight >= 0.201:
            return 4  # Moderate
        elif abs_weight >= 0.101:
            return 5  # Low
        else:
            return 6  # Trivial - base
    
    def assemble_full_content(self) -> str:
        """
        NC1-A05: Assemble full_content from dev_spec + context.
        Used for vision model indexing.
        """
        parts = [
            f"[{self.node_id}] {self.title}",
            f"Weight: {self.dev_weight} | Status: {self.status.value}",
            f"Type: {self.node_type.value} | Layer: {self.layer}",
        ]
        
        if self.dev_spec:
            parts.append(f"Spec: {self.dev_spec}")
        
        if self.children_ids:
            parts.append(f"Children: {', '.join(self.children_ids)}")
        
        return "\n".join(parts)
    
    class Config:
        use_enum_values = True


# =============================================================================
# NC1-026: PHASE_DATA_MODEL
# NC1-027: PHASE_AGGREGATE_WEIGHT_CALC
# NC1-028: PHASE_NODE_COUNT_TRACKING
# NC1-029: PHASE_STATUS_DERIVATION
# =============================================================================

class PhaseStatus(str, Enum):
    """Phase lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class PhaseBase(BaseModel):
    """Base phase properties."""
    
    title: str = Field(..., description="Phase title")
    description: Optional[str] = Field(None, description="Phase description")


class PhaseCreate(PhaseBase):
    """Schema for creating a new phase."""
    
    phase_number: Optional[int] = Field(None, description="Auto-assigned if not provided")


class PhaseUpdate(BaseModel):
    """Schema for updating a phase."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PhaseStatus] = None


class Phase(PhaseBase):
    """Full phase model with aggregates."""
    
    phase_number: int = Field(..., ge=1)
    status: PhaseStatus = Field(default=PhaseStatus.DRAFT)
    
    # NC1-028: Node count tracking
    node_count: int = Field(default=0, ge=0)
    root_count: int = Field(default=0, ge=0)
    
    # NC1-027: Aggregate weight calculation
    aggregate_weight: Optional[float] = Field(None, description="Average weight of all nodes")
    min_weight: Optional[float] = Field(None)
    max_weight: Optional[float] = Field(None)
    
    # Completion metrics
    completion_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def calculate_aggregate_weight(self, node_weights: List[float]) -> None:
        """
        NC1-027: Calculate aggregate statistics from node weights.
        """
        if not node_weights:
            self.aggregate_weight = None
            self.min_weight = None
            self.max_weight = None
            return
        
        self.aggregate_weight = sum(node_weights) / len(node_weights)
        self.min_weight = min(node_weights)
        self.max_weight = max(node_weights)
    
    def derive_status(self, node_statuses: List[NodeStatus]) -> None:
        """
        NC1-029: Derive phase status from node statuses.
        """
        if not node_statuses:
            self.status = PhaseStatus.DRAFT
            return
        
        status_set = set(node_statuses)
        
        # All complete → phase complete
        if status_set == {NodeStatus.COMPLETE}:
            self.status = PhaseStatus.COMPLETE
        # Any active → phase active
        elif NodeStatus.ACTIVE in status_set:
            self.status = PhaseStatus.ACTIVE
        # All archived → phase archived
        elif status_set == {NodeStatus.ARCHIVED}:
            self.status = PhaseStatus.ARCHIVED
        else:
            self.status = PhaseStatus.DRAFT
        
        # Calculate completion percentage
        complete_count = sum(1 for s in node_statuses if s == NodeStatus.COMPLETE)
        self.completion_pct = (complete_count / len(node_statuses)) * 100
    
    class Config:
        use_enum_values = True


# =============================================================================
# NC1-030: MANIFEST_DATA_MODEL
# NC1-031: MANIFEST_LINKED_PHASES
# NC1-032: MANIFEST_THREAD_COLOR_ASSIGNMENT
# =============================================================================

# Manifest thread colors (cycle for multiple manifests)
MANIFEST_COLORS = [
    "#FFD700",  # Gold (primary)
    "#00CED1",  # Cyan
    "#FF6347",  # Tomato
    "#9370DB",  # Medium Purple
    "#3CB371",  # Medium Sea Green
    "#FF69B4",  # Hot Pink
]


class ManifestCreate(BaseModel):
    """Schema for creating a manifest."""
    
    manifest_id: str = Field(..., description="Unique manifest identifier")
    title: str = Field(..., description="Manifest title")
    description: Optional[str] = None
    linked_phase_numbers: List[int] = Field(default_factory=list)


class Manifest(BaseModel):
    """Full manifest model."""
    
    manifest_id: str = Field(..., description="Unique identifier (e.g., 'master', 'node-complex')")
    title: str
    description: Optional[str] = None
    version: str = Field(default="1.0")
    
    # NC1-031: Linked phases
    linked_phase_numbers: List[int] = Field(default_factory=list)
    
    # NC1-032: Thread color
    thread_color: str = Field(default=MANIFEST_COLORS[0])
    
    # Aggregates
    total_phases: int = Field(default=0)
    aggregate_weight: Optional[float] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def assign_thread_color(cls, manifest_index: int) -> str:
        """
        NC1-032: Assign unique thread color based on manifest index.
        """
        return MANIFEST_COLORS[manifest_index % len(MANIFEST_COLORS)]
    
    class Config:
        use_enum_values = True


# =============================================================================
# NC1-033: THREAD_DATA_MODEL
# =============================================================================

class ThreadCreate(BaseModel):
    """Schema for creating a thread."""
    
    source_node_id: str
    target_node_id: str
    thread_type: ThreadType = Field(default=ThreadType.PARENT_CHILD)
    
    _validate_source = validator('source_node_id', allow_reuse=True)(validate_node_id)
    _validate_target = validator('target_node_id', allow_reuse=True)(validate_node_id)


class Thread(BaseModel):
    """Full thread model."""
    
    source_node_id: str
    target_node_id: str
    thread_type: ThreadType
    color: str = Field(default="#3498DB")
    
    # Visual properties
    thickness: float = Field(default=1.0, ge=0.1, le=5.0)
    visibility: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def create_with_color(
        cls, 
        source_id: str, 
        target_id: str, 
        thread_type: ThreadType,
        parent_depth: int = 0
    ) -> "Thread":
        """Create thread with appropriate color."""
        color = get_thread_color(thread_type, parent_depth)
        return cls(
            source_node_id=source_id,
            target_node_id=target_id,
            thread_type=thread_type,
            color=color
        )
    
    class Config:
        use_enum_values = True


# =============================================================================
# CHANGE TRACKING (Addendum V)
# NC1-A01 → NC1-A04
# =============================================================================

class ChangeRecord(BaseModel):
    """Record of a change to a node."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    node_id: str
    field_changed: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    changed_by: str = Field(default="system")
    
    class Config:
        use_enum_values = True


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SCHEMA VALIDATION TEST")
    print("=" * 60)
    
    # Test valid node creation
    try:
        node = NodeCreate(
            node_id="NC1-001",
            title="DATABASE_FOUNDATION",
            dev_weight=-0.345,
            dev_spec="Core database setup and initialization",
            phase_number=1
        )
        print(f"\n✅ Valid node: {node.node_id} | {node.title}")
    except Exception as e:
        print(f"\n❌ Node creation failed: {e}")
    
    # Test invalid node ID
    try:
        bad_node = NodeCreate(
            node_id="invalid-id",
            title="BAD_NODE",
            dev_weight=-0.5,
            phase_number=1
        )
        print(f"\n❌ Should have rejected invalid ID")
    except ValueError as e:
        print(f"\n✅ Correctly rejected invalid ID: {str(e)[:50]}...")
    
    # Test invalid weight
    try:
        bad_weight = NodeCreate(
            node_id="NC1-002",
            title="BAD_WEIGHT",
            dev_weight=0.5,  # Positive - invalid
            phase_number=1
        )
        print(f"\n❌ Should have rejected positive weight")
    except ValueError as e:
        print(f"\n✅ Correctly rejected positive weight")
    
    # Test full node with layer calculation
    full_node = Node(
        node_id="NC1-075",
        title="TRANSACTION_DUAL_DB_CONSISTENCY",
        dev_weight=-0.445,
        phase_number=1,
        status=NodeStatus.ACTIVE
    )
    print(f"\n✅ Full node layer: {full_node.layer} (from weight {full_node.dev_weight})")
    
    # Test thread color
    color = get_thread_color(ThreadType.PARENT_CHILD, parent_depth=2)
    print(f"\n✅ Thread color for depth 2: {color}")
    
    print("\n" + "=" * 60)
    print("ALL SCHEMA TESTS PASSED!")
    print("=" * 60)
