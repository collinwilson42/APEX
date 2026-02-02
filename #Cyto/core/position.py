"""
CYTO 4D Coordinate System - Position Calculator

Layers EXPAND outward:
  W=1: 0.618 ─ 1.000 ─ 1.618  (innermost, NOW)
  W=2: 1.618 ─ 2.000 ─ 2.618  (wraps around W=1)
  W=3: 2.618 ─ 3.000 ─ 3.618  (wraps around W=2)
  W=4: 3.618 ─ 4.000 ─ 4.618  (wraps around W=3)

Each layer's inner edge = previous layer's outer edge.
View zooms out dynamically as layers accumulate.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple


class LayerGeometry:
    """Calculate golden ratio ring positions for a W-layer.
    
    W=1 is innermost (current time), higher W expands outward.
    Each layer's inner edge = previous layer's outer edge.
    Layers stack outward like tree rings.
    """
    PHI = 1.618033988749895
    
    def __init__(self, w_layer: int = 1):
        self.w = max(1, w_layer)
        # W=1: 0.618-1.000-1.618
        # W=2: 1.618-2.000-2.618 (inner = W1's outer)
        # W=3: 2.618-3.000-3.618 (inner = W2's outer)
        # Pattern: inner = (w-1) + 0.618, mid = w, outer = w + 0.618
        self.mid = float(self.w)
        self.inner = (self.w - 1) + (self.PHI - 1)  # (w-1) + 0.618
        self.outer = self.w + (self.PHI - 1)        # w + 0.618
    
    @staticmethod
    def get_max_outer(max_w: int) -> float:
        """Get the outer radius of the largest layer for zoom calculation."""
        return max_w + (LayerGeometry.PHI - 1)  # max_w + 0.618
    
    @staticmethod
    def get_zoom_scale(max_w: int) -> float:
        """Calculate zoom scale to fit all layers in view.
        
        Returns scale factor where 1.0 = W=1 fills view.
        Higher values = zoomed out to show more layers.
        """
        # W=1 outer = 1.618, that's our baseline
        baseline_outer = LayerGeometry.PHI
        current_outer = LayerGeometry.get_max_outer(max_w)
        return current_outer / baseline_outer


class TimeMapper:
    """Map time to angular position on the torus.
    
    - North (0°/360°) = NOW
    - 9 sections, each 40° arc (360° / 9 = 40°)
    - Default 36-hour cycle (4 hours per section)
    - Time flows counter-clockwise (section 1 = past, section 9 = now)
    """
    
    def __init__(self, cycle_hours: int = 36):
        self.cycle_hours = cycle_hours
        self.hours_per_section = cycle_hours / 9
    
    def time_to_theta(self, dt: datetime, reference_now: datetime = None) -> float:
        """Convert datetime to angular position (degrees from north)."""
        if reference_now is None:
            reference_now = datetime.now()
        
        delta = reference_now - dt
        hours_ago = delta.total_seconds() / 3600
        
        # Wrap to cycle
        hours_in_cycle = hours_ago % self.cycle_hours
        
        # Convert to degrees (counter-clockwise from north)
        degrees = (hours_in_cycle / self.cycle_hours) * 360
        return degrees
    
    def theta_to_section(self, theta: float) -> int:
        """Convert theta to section number (1-9).
        
        Section 9 is at north (0°), sections count counter-clockwise.
        """
        # Normalize theta
        theta = theta % 360
        
        # Section 9 spans 340°-360° and 0°-20° (centered on north)
        if theta >= 340 or theta < 20:
            return 9
        
        # Other sections: each 40° starting from 20°
        section = int((theta - 20) / 40) + 1
        return min(max(section, 1), 8)
    
    def get_section_time_range(self, section: int, w_layer: int = 1) -> Tuple[datetime, datetime]:
        """Get the time range for a section on a given W-layer."""
        now = datetime.now()
        
        # Calculate hours ago for this section
        # Section 9 = now, Section 1 = oldest in cycle
        if section == 9:
            sections_ago = 0
        else:
            sections_ago = 9 - section
        
        # Add W-layer offset (each layer = one full cycle back)
        total_cycles_back = w_layer - 1
        hours_offset = total_cycles_back * self.cycle_hours
        
        start_hours = (sections_ago * self.hours_per_section) + hours_offset
        end_hours = start_hours + self.hours_per_section
        
        start_time = now - timedelta(hours=end_hours)
        end_time = now - timedelta(hours=start_hours)
        
        return start_time, end_time


@dataclass
class NodePosition:
    """4D position of a node on the torus."""
    theta: float      # Angular position (degrees, 0=north)
    radius: float     # Distance from center (golden ratio units)
    z: float = 0.0    # Vertical offset (for 3D view)
    w: int = 1        # W-layer (1=innermost/now, higher=older/outer)
    section: int = 9  # Convenience: which section this falls in


class NodePlacer:
    """Place sync and integration nodes at correct positions."""
    
    def __init__(self, w_layer: int = 1):
        self.layer = LayerGeometry(w_layer)
        self.time_mapper = TimeMapper()
    
    def place_sync_node(self, parent_theta: float, depth_in_tree: int = 0) -> NodePosition:
        """Place a sync node (grows from mid toward outer edge).
        
        Sync nodes extend from the 1.000 line toward 1.618 perimeter.
        """
        # Interpolate from mid to outer based on depth
        max_depth = 5
        t = min(depth_in_tree, max_depth) / max_depth
        radius = self.layer.mid + (self.layer.outer - self.layer.mid) * t * 0.8
        
        section = self.time_mapper.theta_to_section(parent_theta)
        
        return NodePosition(
            theta=parent_theta,
            radius=radius,
            w=self.layer.w,
            section=section
        )
    
    def place_integration_node(self, parent_theta: float, depth_in_tree: int = 0) -> NodePosition:
        """Place an integration node (grows from mid toward inner edge).
        
        Integration nodes extend from the 1.000 line toward 0.618 center.
        """
        # Interpolate from mid to inner based on depth
        max_depth = 5
        t = min(depth_in_tree, max_depth) / max_depth
        radius = self.layer.mid - (self.layer.mid - self.layer.inner) * t * 0.8
        
        section = self.time_mapper.theta_to_section(parent_theta)
        
        return NodePosition(
            theta=parent_theta,
            radius=radius,
            w=self.layer.w,
            section=section
        )
