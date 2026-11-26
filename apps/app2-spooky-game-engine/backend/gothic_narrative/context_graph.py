"""
Context Graph - Story state management and relationship tracking.

Implements a graph-based context system for tracking story state,
character relationships, and narrative dependencies.

Task 4.5: Implement Context Graph
Validates: Requirements 4.1, 4.2
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class EdgeType(str, Enum):
    """Types of relationships in the context graph."""
    LEADS_TO = "leads_to"  # Scene progression
    REQUIRES = "requires"  # Prerequisite relationship
    CONFLICTS = "conflicts"  # Mutually exclusive
    IMPLIES = "implies"  # Narrative implication
    CHARACTER_KNOWS = "character_knows"  # Knowledge state
    CHARACTER_FEELS = "character_feels"  # Emotional state
    ITEM_LOCATION = "item_location"  # Item placement
    EVENT_TRIGGER = "event_trigger"  # Event activation
    BRANCH_SPLIT = "branch_split"  # Story branching
    BRANCH_MERGE = "branch_merge"  # Branch convergence


@dataclass
class GraphNode:
    """A node in the context graph."""

    id: str
    node_type: str  # "scene", "item", "character", "event", "flag"
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "nodeType": self.node_type,
            "properties": self.properties,
            "createdAt": self.created_at,
            "modifiedAt": self.modified_at,
        }


@dataclass
class GraphEdge:
    """An edge connecting two nodes in the context graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)  # Conditions for edge to be active

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "edgeType": self.edge_type.value,
            "weight": self.weight,
            "properties": self.properties,
            "conditions": self.conditions,
        }


@dataclass
class ContextSnapshot:
    """A snapshot of the context graph state."""

    timestamp: str
    active_nodes: list[str]
    active_edges: list[tuple[str, str]]
    flags: dict[str, bool]
    variables: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "activeNodes": self.active_nodes,
            "activeEdges": self.active_edges,
            "flags": self.flags,
            "variables": self.variables,
        }


class ContextGraph:
    """
    Graph-based context management for narrative state.

    Tracks:
    - Story progression and dependencies
    - Character knowledge and relationships
    - Item locations and ownership
    - Event triggers and conditions
    - Branch tracking and merging

    Task 4.5: Context Graph
    Validates: Requirements 4.1, 4.2

    Example:
        >>> graph = ContextGraph()
        >>> graph.add_scene("start", {"title": "The Gates"})
        >>> graph.add_transition("start", "foyer", condition={"visited": True})
        >>> graph.can_reach("start", "foyer")
        True
    """

    def __init__(
        self,
        *,
        max_history: int = 100,
    ) -> None:
        """
        Initialize the context graph.

        Args:
            max_history: Maximum snapshots to retain
        """
        self.max_history = max_history
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._flags: dict[str, bool] = {}
        self._variables: dict[str, Any] = {}
        self._history: list[ContextSnapshot] = []
        self._current_scene: str | None = None

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # =========================================================================
    # Node Management
    # =========================================================================

    def add_scene(
        self,
        scene_id: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Add a scene node to the graph.

        Args:
            scene_id: Unique scene identifier
            properties: Scene properties

        Returns:
            Created GraphNode
        """
        return self._add_node(scene_id, "scene", properties or {})

    def add_item(
        self,
        item_id: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Add an item node to the graph.

        Args:
            item_id: Unique item identifier
            properties: Item properties

        Returns:
            Created GraphNode
        """
        return self._add_node(item_id, "item", properties or {})

    def add_character(
        self,
        character_id: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Add a character node to the graph.

        Args:
            character_id: Unique character identifier
            properties: Character properties

        Returns:
            Created GraphNode
        """
        return self._add_node(character_id, "character", properties or {})

    def add_event(
        self,
        event_id: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        """
        Add an event node to the graph.

        Args:
            event_id: Unique event identifier
            properties: Event properties

        Returns:
            Created GraphNode
        """
        return self._add_node(event_id, "event", properties or {})

    def add_flag(
        self,
        flag_id: str,
        initial_value: bool = False,
    ) -> GraphNode:
        """
        Add a flag node to the graph.

        Args:
            flag_id: Unique flag identifier
            initial_value: Initial flag value

        Returns:
            Created GraphNode
        """
        self._flags[flag_id] = initial_value
        return self._add_node(flag_id, "flag", {"value": initial_value})

    def _add_node(
        self,
        node_id: str,
        node_type: str,
        properties: dict[str, Any],
    ) -> GraphNode:
        """Add a node to the graph."""
        node = GraphNode(
            id=node_id,
            node_type=node_type,
            properties=properties,
        )
        self._nodes[node_id] = node
        return node

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def update_node(self, node_id: str, properties: dict[str, Any]) -> bool:
        """
        Update a node's properties.

        Args:
            node_id: Node ID
            properties: Properties to update

        Returns:
            True if node was updated, False if not found
        """
        node = self._nodes.get(node_id)
        if node:
            node.properties.update(properties)
            node.modified_at = datetime.utcnow().isoformat()
            return True
        return False

    # =========================================================================
    # Edge Management
    # =========================================================================

    def add_transition(
        self,
        from_scene: str,
        to_scene: str,
        *,
        condition: dict[str, Any] | None = None,
        weight: float = 1.0,
    ) -> GraphEdge:
        """
        Add a scene transition edge.

        Args:
            from_scene: Source scene ID
            to_scene: Target scene ID
            condition: Conditions for transition
            weight: Edge weight

        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            source_id=from_scene,
            target_id=to_scene,
            edge_type=EdgeType.LEADS_TO,
            weight=weight,
            conditions=condition or {},
        )
        self._edges.append(edge)
        return edge

    def add_dependency(
        self,
        dependent: str,
        prerequisite: str,
        *,
        dependency_type: str = "requires",
    ) -> GraphEdge:
        """
        Add a dependency edge.

        Args:
            dependent: Dependent node ID
            prerequisite: Prerequisite node ID
            dependency_type: Type of dependency

        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            source_id=dependent,
            target_id=prerequisite,
            edge_type=EdgeType.REQUIRES,
            properties={"dependencyType": dependency_type},
        )
        self._edges.append(edge)
        return edge

    def add_knowledge(
        self,
        character_id: str,
        knowledge_id: str,
        *,
        knows: bool = True,
    ) -> GraphEdge:
        """
        Add a knowledge relationship.

        Args:
            character_id: Character node ID
            knowledge_id: Knowledge/event node ID
            knows: Whether character knows this

        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            source_id=character_id,
            target_id=knowledge_id,
            edge_type=EdgeType.CHARACTER_KNOWS,
            properties={"knows": knows},
        )
        self._edges.append(edge)
        return edge

    def add_item_location(
        self,
        item_id: str,
        location_id: str,
        *,
        owner: str | None = None,
    ) -> GraphEdge:
        """
        Add an item location relationship.

        Args:
            item_id: Item node ID
            location_id: Location/scene node ID
            owner: Optional character owner

        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            source_id=item_id,
            target_id=location_id,
            edge_type=EdgeType.ITEM_LOCATION,
            properties={"owner": owner},
        )
        self._edges.append(edge)
        return edge

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        """Get all edges originating from a node."""
        return [e for e in self._edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        """Get all edges pointing to a node."""
        return [e for e in self._edges if e.target_id == node_id]

    # =========================================================================
    # State Management
    # =========================================================================

    def set_flag(self, flag_id: str, value: bool) -> None:
        """
        Set a flag value.

        Args:
            flag_id: Flag identifier
            value: Flag value
        """
        self._flags[flag_id] = value
        if flag_id in self._nodes:
            self._nodes[flag_id].properties["value"] = value

    def get_flag(self, flag_id: str, default: bool = False) -> bool:
        """
        Get a flag value.

        Args:
            flag_id: Flag identifier
            default: Default value if not found

        Returns:
            Flag value
        """
        return self._flags.get(flag_id, default)

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a context variable.

        Args:
            key: Variable key
            value: Variable value
        """
        self._variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """
        Get a context variable.

        Args:
            key: Variable key
            default: Default value if not found

        Returns:
            Variable value
        """
        return self._variables.get(key, default)

    def set_current_scene(self, scene_id: str) -> None:
        """
        Set the current scene.

        Args:
            scene_id: Current scene ID
        """
        self._current_scene = scene_id
        self.set_flag(f"visited_{scene_id}", True)

    def get_current_scene(self) -> str | None:
        """Get the current scene ID."""
        return self._current_scene

    # =========================================================================
    # Graph Queries
    # =========================================================================

    def can_reach(
        self,
        from_scene: str,
        to_scene: str,
        *,
        check_conditions: bool = True,
    ) -> bool:
        """
        Check if a scene can be reached from another.

        Args:
            from_scene: Starting scene
            to_scene: Target scene
            check_conditions: Whether to check edge conditions

        Returns:
            True if reachable, False otherwise
        """
        if from_scene == to_scene:
            return True

        visited = set()
        stack = [from_scene]

        while stack:
            current = stack.pop()

            if current == to_scene:
                return True

            if current in visited:
                continue

            visited.add(current)

            for edge in self.get_edges_from(current):
                if edge.edge_type != EdgeType.LEADS_TO:
                    continue

                if check_conditions and edge.conditions:
                    if not self._check_conditions(edge.conditions):
                        continue

                stack.append(edge.target_id)

        return False

    def get_reachable_scenes(self, from_scene: str) -> list[str]:
        """
        Get all scenes reachable from a given scene.

        Args:
            from_scene: Starting scene

        Returns:
            List of reachable scene IDs
        """
        reachable = []
        visited = set()
        stack = [from_scene]

        while stack:
            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)

            for edge in self.get_edges_from(current):
                if edge.edge_type == EdgeType.LEADS_TO:
                    if self._check_conditions(edge.conditions):
                        reachable.append(edge.target_id)
                        stack.append(edge.target_id)

        return reachable

    def get_path(
        self,
        from_scene: str,
        to_scene: str,
    ) -> list[str] | None:
        """
        Find a path between two scenes.

        Args:
            from_scene: Starting scene
            to_scene: Target scene

        Returns:
            List of scene IDs forming the path, or None if no path
        """
        if from_scene == to_scene:
            return [from_scene]

        visited = {from_scene: None}
        stack = [from_scene]

        while stack:
            current = stack.pop()

            for edge in self.get_edges_from(current):
                if edge.edge_type != EdgeType.LEADS_TO:
                    continue

                if edge.target_id in visited:
                    continue

                visited[edge.target_id] = current

                if edge.target_id == to_scene:
                    # Reconstruct path
                    path = [to_scene]
                    node = to_scene
                    while visited[node] is not None:
                        node = visited[node]
                        path.append(node)
                    return list(reversed(path))

                stack.append(edge.target_id)

        return None

    def get_dependencies(self, node_id: str) -> list[str]:
        """
        Get all dependencies for a node.

        Args:
            node_id: Node to check

        Returns:
            List of dependency node IDs
        """
        dependencies = []
        for edge in self.get_edges_from(node_id):
            if edge.edge_type == EdgeType.REQUIRES:
                dependencies.append(edge.target_id)
                # Recursively get dependencies
                dependencies.extend(self.get_dependencies(edge.target_id))
        return list(set(dependencies))

    def are_dependencies_met(self, node_id: str) -> bool:
        """
        Check if all dependencies for a node are met.

        Args:
            node_id: Node to check

        Returns:
            True if all dependencies are met
        """
        dependencies = self.get_dependencies(node_id)
        for dep_id in dependencies:
            if not self.get_flag(f"completed_{dep_id}", False):
                return False
        return True

    def get_item_location(self, item_id: str) -> str | None:
        """
        Get the current location of an item.

        Args:
            item_id: Item ID

        Returns:
            Location/scene ID or None
        """
        for edge in self._edges:
            if edge.edge_type == EdgeType.ITEM_LOCATION and edge.source_id == item_id:
                return edge.target_id
        return None

    def move_item(self, item_id: str, new_location: str) -> bool:
        """
        Move an item to a new location.

        Args:
            item_id: Item ID
            new_location: New location/scene ID

        Returns:
            True if item was moved
        """
        # Remove existing location edges
        self._edges = [
            e for e in self._edges
            if not (e.edge_type == EdgeType.ITEM_LOCATION and e.source_id == item_id)
        ]

        # Add new location edge
        self.add_item_location(item_id, new_location)
        return True

    def _check_conditions(self, conditions: dict[str, Any]) -> bool:
        """
        Check if conditions are met.

        Args:
            conditions: Conditions to check

        Returns:
            True if all conditions are met
        """
        for key, value in conditions.items():
            if key.startswith("flag_"):
                flag_name = key[5:]
                if self.get_flag(flag_name) != value:
                    return False
            elif key == "visited":
                if not self.get_flag(f"visited_{value}", False):
                    return False
            elif key == "has_item":
                if not self.get_flag(f"has_{value}", False):
                    return False
            elif key == "stat_min":
                stat_name, min_value = value.split(">")
                if self.get_variable(f"stat_{stat_name}", 0) < int(min_value):
                    return False

        return True

    # =========================================================================
    # Serialization
    # =========================================================================

    def create_snapshot(self) -> ContextSnapshot:
        """Create a snapshot of the current state."""
        return ContextSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            active_nodes=list(self._nodes.keys()),
            active_edges=[(e.source_id, e.target_id) for e in self._edges],
            flags=self._flags.copy(),
            variables=self._variables.copy(),
        )

    def restore_snapshot(self, snapshot: ContextSnapshot) -> None:
        """
        Restore from a snapshot.

        Args:
            snapshot: Snapshot to restore
        """
        self._flags = snapshot.flags.copy()
        self._variables = snapshot.variables.copy()

    def save_snapshot(self) -> None:
        """Save current state to history."""
        snapshot = self.create_snapshot()
        self._history.append(snapshot)

        # Trim history if needed
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "flags": self._flags,
            "variables": self._variables,
            "currentScene": self._current_scene,
            "history": [s.to_dict() for s in self._history[-10:]],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextGraph":
        """Create from dictionary."""
        graph = cls()

        for nid, ndata in data.get("nodes", {}).items():
            node = GraphNode(
                id=nid,
                node_type=ndata["nodeType"],
                properties=ndata["properties"],
            )
            graph._nodes[nid] = node

        for edata in data.get("edges", []):
            edge = GraphEdge(
                source_id=edata["sourceId"],
                target_id=edata["targetId"],
                edge_type=EdgeType(edata["edgeType"]),
                weight=edata.get("weight", 1.0),
                properties=edata.get("properties", {}),
                conditions=edata.get("conditions", {}),
            )
            graph._edges.append(edge)

        graph._flags = data.get("flags", {})
        graph._variables = data.get("variables", {})
        graph._current_scene = data.get("currentScene")

        return graph

    def save_to_file(self, path: Path | str) -> None:
        """Save to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load_from_file(cls, path: Path | str) -> "ContextGraph":
        """Load from a JSON file."""
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)
