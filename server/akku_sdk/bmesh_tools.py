"""
Akku SDK v3.8 - BMesh Direct Manipulation Tools
Low-level mesh editing primitives for procedural character generation

Features:
- Bmesh Wrapper: Direct bmesh manipulation without bpy.ops
- Loop Cut: Edge flow-based face splitting for joint creation
- Rig-Aware Extrude: Weight inheritance from parent vertices
- Normal Recalculate: Automatic normal fixing after all operations
"""

import bpy
import bmesh
import mathutils
from mathutils import Vector, Matrix
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field


@dataclass
class ExtrudeResult:
    """Result of a smart extrude operation"""
    new_face_indices: List[int] = field(default_factory=list)
    new_vert_indices: List[int] = field(default_factory=list)
    new_edge_indices: List[int] = field(default_factory=list)
    assigned_vertex_group: Optional[str] = None


@dataclass
class LoopCutResult:
    """Result of a loop cut operation"""
    new_edge_indices: List[int] = field(default_factory=list)
    new_vert_indices: List[int] = field(default_factory=list)
    slide_factor: float = 0.0


@dataclass
class MirrorResult:
    """Result of mirror and weld operation"""
    original_vert_count: int = 0
    mirrored_vert_count: int = 0
    welded_vert_count: int = 0
    merged_center_verts: int = 0


class BmeshTools:
    """
    Core BMesh manipulation tools for procedural modeling.
    All operations work directly on bmesh data structures.
    """
    
    WELD_THRESHOLD = 0.0001  # Distance threshold for welding vertices
    
    def __init__(self, obj: Optional[bpy.types.Object] = None):
        """
        Initialize with optional existing object.
        If no object provided, operations will create new meshes.
        """
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
        self._vertex_group_cache: Dict[str, int] = {}
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        """Ensure bmesh is available and synced with object"""
        if self.bm is None:
            if self.obj is None:
                self.bm = bmesh.new()
            else:
                self.bm = bmesh.new()
                self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def _update_mesh(self):
        """Update object mesh from bmesh"""
        if self.obj is not None and self.bm is not None:
            self.bm.to_mesh(self.obj.data)
            self.obj.data.update()
    
    def _get_or_create_vertex_group(self, name: str) -> int:
        """Get vertex group index, creating if needed"""
        if self.obj is None:
            return -1
        
        if name in self._vertex_group_cache:
            return self._vertex_group_cache[name]
        
        if name in self.obj.vertex_groups:
            group = self.obj.vertex_groups[name]
        else:
            group = self.obj.vertex_groups.new(name=name)
        
        self._vertex_group_cache[name] = group.index
        return group.index
    
    def _assign_verts_to_group(self, vert_indices: List[int], group_name: str, weight: float = 1.0):
        """Assign vertices to a vertex group with specified weight"""
        if self.obj is None or not vert_indices:
            return
        
        if group_name not in self.obj.vertex_groups:
            self.obj.vertex_groups.new(name=group_name)
        
        group = self.obj.vertex_groups[group_name]
        group.add(vert_indices, weight, 'REPLACE')

    # =========================================================================
    # PRIMITIVE CREATION
    # =========================================================================
    
    def add_primitive_box(
        self,
        size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        name: str = "AkkuBox"
    ) -> bpy.types.Object:
        """
        Create a primitive box as the starting point for all modeling.
        
        Args:
            size: (width, depth, height) dimensions
            location: (x, y, z) world position
            name: Name for the new object
            
        Returns:
            The created mesh object
        """
        bm = bmesh.new()
        
        width, depth, height = size
        x, y, z = location
        
        hw = width / 2
        hd = depth / 2
        hh = height / 2
        
        verts = [
            bm.verts.new((x - hw, y - hd, z - hh)),  # 0: bottom-back-left
            bm.verts.new((x + hw, y - hd, z - hh)),  # 1: bottom-back-right
            bm.verts.new((x + hw, y + hd, z - hh)),  # 2: bottom-front-right
            bm.verts.new((x - hw, y + hd, z - hh)),  # 3: bottom-front-left
            bm.verts.new((x - hw, y - hd, z + hh)),  # 4: top-back-left
            bm.verts.new((x + hw, y - hd, z + hh)),  # 5: top-back-right
            bm.verts.new((x + hw, y + hd, z + hh)),  # 6: top-front-right
            bm.verts.new((x - hw, y + hd, z + hh)),  # 7: top-front-left
        ]
        
        bm.faces.new([verts[0], verts[1], verts[2], verts[3]])  # bottom
        bm.faces.new([verts[4], verts[7], verts[6], verts[5]])  # top
        bm.faces.new([verts[0], verts[4], verts[5], verts[1]])  # back
        bm.faces.new([verts[2], verts[6], verts[7], verts[3]])  # front
        bm.faces.new([verts[0], verts[3], verts[7], verts[4]])  # left
        bm.faces.new([verts[1], verts[5], verts[6], verts[2]])  # right
        
        bm.normal_update()
        
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        self.obj = obj
        self.bm = None
        self._vertex_group_cache.clear()
        
        return obj

    # =========================================================================
    # SMART EXTRUDE
    # =========================================================================
    
    def smart_extrude(
        self,
        face_index: int,
        length: float,
        vertex_group: Optional[str] = None,
        scale: Tuple[float, float] = (1.0, 1.0),
        inset: float = 0.0
    ) -> ExtrudeResult:
        """
        Extrude a face by specified length with automatic vertex group assignment.
        
        This is the core operation for building character limbs and body parts.
        Extruded vertices are automatically assigned to the specified rigging group.
        
        Args:
            face_index: Index of face to extrude
            length: Distance to extrude along face normal
            vertex_group: Name of vertex group for new vertices (for rigging)
            scale: (x, y) scale factors for extruded face
            inset: Optional inset before extrude (for tapered shapes)
            
        Returns:
            ExtrudeResult with indices of new geometry and assigned group
        """
        result = ExtrudeResult()
        
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        if face_index >= len(bm.faces):
            print(f"[BmeshTools] Face index {face_index} out of range")
            return result
        
        face = bm.faces[face_index]
        normal = face.normal.copy()
        original_face_verts = set(v for v in face.verts)
        
        if inset > 0:
            bmesh.ops.inset_individual(
                bm, 
                faces=[face], 
                thickness=inset, 
                depth=0,
                use_even_offset=True
            )
        
        extrude_result = bmesh.ops.extrude_face_region(bm, geom=[face])
        
        extruded_verts = [v for v in extrude_result['geom'] if isinstance(v, bmesh.types.BMVert)]
        extruded_edges = [e for e in extrude_result['geom'] if isinstance(e, bmesh.types.BMEdge)]
        
        translation = normal * length
        bmesh.ops.translate(bm, verts=extruded_verts, vec=translation)
        
        cap_face = None
        for f in bm.faces:
            if all(v in extruded_verts for v in f.verts):
                if f.normal.dot(normal) > 0.9:
                    cap_face = f
                    break
        
        if scale != (1.0, 1.0) and cap_face:
            cap_center = cap_face.calc_center_median()
            for vert in cap_face.verts:
                local_pos = vert.co - cap_center
                vert.co.x = cap_center.x + local_pos.x * scale[0]
                vert.co.y = cap_center.y + local_pos.y * scale[1]
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        result.new_vert_indices = [v.index for v in extruded_verts]
        result.new_edge_indices = [e.index for e in extruded_edges]
        
        if cap_face:
            result.new_face_indices = [cap_face.index]
        
        self._update_mesh()
        
        if vertex_group and self.obj and result.new_vert_indices:
            self._assign_verts_to_group(result.new_vert_indices, vertex_group)
            result.assigned_vertex_group = vertex_group
        
        return result

    # =========================================================================
    # LOOP CUT AND SLIDE
    # =========================================================================
    
    def loop_cut_and_slide(
        self,
        edge_index: int,
        count: int = 1,
        slide_factor: float = 0.0,
        smooth: float = 0.0
    ) -> LoopCutResult:
        """
        Add edge loops for smooth joint deformation.
        
        Loop cuts are essential for proper joint bending - they add
        geometry where the mesh needs to deform.
        
        Args:
            edge_index: Index of edge to cut through
            count: Number of cuts to make
            slide_factor: -1.0 to 1.0, position along perpendicular edges
            smooth: Smoothing factor for new geometry
            
        Returns:
            LoopCutResult with indices of new edges and vertices
        """
        result = LoopCutResult()
        result.slide_factor = slide_factor
        
        bm = self._ensure_bmesh()
        bm.edges.ensure_lookup_table()
        
        if edge_index >= len(bm.edges):
            print(f"[BmeshTools] Edge index {edge_index} out of range")
            return result
        
        loop_edge_indices = self.get_edge_loop(edge_index)
        if not loop_edge_indices:
            loop_edge_indices = [edge_index]
        
        bm.edges.ensure_lookup_table()
        loop_edges = [bm.edges[i] for i in loop_edge_indices if i < len(bm.edges)]
        
        original_verts = set(v.index for v in bm.verts)
        original_edges = set(e.index for e in bm.edges)
        
        subdivide_result = bmesh.ops.subdivide_edges(
            bm,
            edges=loop_edges,
            cuts=count,
            use_grid_fill=False,
            smooth=smooth
        )
        
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        new_verts = [v for v in bm.verts if v.index not in original_verts]
        
        if slide_factor != 0.0 and new_verts:
            for vert in new_verts:
                connected_edges = list(vert.link_edges)
                if len(connected_edges) >= 2:
                    edge1, edge2 = connected_edges[0], connected_edges[1]
                    
                    v1 = edge1.other_vert(vert)
                    v2 = edge2.other_vert(vert)
                    
                    if v1 and v2:
                        direction = (v1.co - v2.co).normalized()
                        max_dist = (v1.co - vert.co).length
                        vert.co += direction * slide_factor * max_dist * 0.5
        
        result.new_vert_indices = [v.index for v in new_verts]
        result.new_edge_indices = [
            e.index for e in bm.edges 
            if e.index not in original_edges
        ]
        
        self._update_mesh()
        
        return result
    
    def add_loop_cuts_at_joints(
        self,
        joint_positions: List[Tuple[float, float, float]],
        cut_count: int = 2
    ) -> List[LoopCutResult]:
        """
        Add loop cuts near specified joint positions for better deformation.
        
        Args:
            joint_positions: List of (x, y, z) positions where joints will be
            cut_count: Number of loops per joint
            
        Returns:
            List of LoopCutResult for each joint
        """
        results = []
        
        bm = self._ensure_bmesh()
        bm.edges.ensure_lookup_table()
        
        for joint_pos in joint_positions:
            joint_vec = Vector(joint_pos)
            
            closest_edge = None
            closest_dist = float('inf')
            
            for edge in bm.edges:
                edge_center = (edge.verts[0].co + edge.verts[1].co) / 2
                dist = (edge_center - joint_vec).length
                
                if dist < closest_dist:
                    closest_dist = dist
                    closest_edge = edge
            
            if closest_edge:
                result = self.loop_cut_and_slide(
                    edge_index=closest_edge.index,
                    count=cut_count
                )
                results.append(result)
        
        return results

    # =========================================================================
    # MIRROR AND WELD
    # =========================================================================
    
    def mirror_and_weld(
        self,
        axis: str = 'X',
        merge_threshold: float = 0.001,
        use_bisect: bool = True,
        flip_normals: bool = False
    ) -> MirrorResult:
        """
        Mirror geometry and weld center vertices.
        
        Model one half of a character, then use this to create the
        symmetrical other half with properly merged center vertices.
        
        Args:
            axis: 'X', 'Y', or 'Z' - axis to mirror across
            merge_threshold: Distance for welding center vertices
            use_bisect: Cut geometry at mirror plane first
            flip_normals: If True, flip normals on mirrored geometry (usually False)
            
        Returns:
            MirrorResult with vertex counts and merge statistics
        """
        result = MirrorResult()
        
        bm = self._ensure_bmesh()
        
        result.original_vert_count = len(bm.verts)
        
        axis_index = {'X': 0, 'Y': 1, 'Z': 2}.get(axis.upper(), 0)
        
        if use_bisect:
            plane_co = Vector((0, 0, 0))
            plane_no = Vector((0, 0, 0))
            plane_no[axis_index] = 1.0
            
            geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
            
            bmesh.ops.bisect_plane(
                bm,
                geom=geom,
                plane_co=plane_co,
                plane_no=plane_no,
                clear_outer=True,
                clear_inner=False
            )
            
            bm.verts.ensure_lookup_table()
        
        original_verts = list(bm.verts)
        original_faces = list(bm.faces)
        
        vert_map = {}
        
        for v in original_verts:
            new_co = v.co.copy()
            new_co[axis_index] = -new_co[axis_index]
            new_vert = bm.verts.new(new_co)
            vert_map[v] = new_vert
        
        for face in original_faces:
            try:
                new_verts = [vert_map[v] for v in face.verts]
                if flip_normals:
                    pass
                else:
                    new_verts = list(reversed(new_verts))
                bm.faces.new(new_verts)
            except ValueError:
                pass
        
        bm.verts.ensure_lookup_table()
        result.mirrored_vert_count = len(bm.verts)
        
        all_verts = list(bm.verts)
        bmesh.ops.remove_doubles(
            bm,
            verts=all_verts,
            dist=merge_threshold
        )
        
        for v in bm.verts:
            if abs(v.co[axis_index]) < merge_threshold:
                v.co[axis_index] = 0.0
        
        bm.verts.ensure_lookup_table()
        result.welded_vert_count = len(bm.verts)
        result.merged_center_verts = result.mirrored_vert_count - result.welded_vert_count
        
        bm.normal_update()
        self._update_mesh()
        
        return result

    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================
    
    def get_face_by_normal(
        self,
        direction: Tuple[float, float, float],
        threshold: float = 0.9
    ) -> Optional[int]:
        """
        Find face most aligned with given direction.
        
        Useful for finding the "top" face, "front" face, etc.
        
        Args:
            direction: Normalized direction vector
            threshold: Dot product threshold for match
            
        Returns:
            Face index or None if no match
        """
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        dir_vec = Vector(direction).normalized()
        best_face = None
        best_dot = -1
        
        for face in bm.faces:
            dot = face.normal.dot(dir_vec)
            if dot > best_dot and dot > threshold:
                best_dot = dot
                best_face = face
        
        return best_face.index if best_face else None
    
    def get_edge_loop(self, edge_index: int) -> List[int]:
        """
        Get all edges in the same loop as specified edge.
        
        Args:
            edge_index: Starting edge index
            
        Returns:
            List of edge indices in the loop
        """
        bm = self._ensure_bmesh()
        bm.edges.ensure_lookup_table()
        
        if edge_index >= len(bm.edges):
            return []
        
        start_edge = bm.edges[edge_index]
        loop_edges = [start_edge]
        visited = {start_edge}
        
        def get_connected_loop_edge(edge, vert):
            for linked_edge in vert.link_edges:
                if linked_edge not in visited:
                    if len(linked_edge.link_faces) == 2:
                        for face in linked_edge.link_faces:
                            face_edges = list(face.edges)
                            if edge in face_edges:
                                opposite_idx = (face_edges.index(edge) + 2) % 4
                                if len(face_edges) == 4 and face_edges[opposite_idx] == linked_edge:
                                    return linked_edge
            return None
        
        for vert in start_edge.verts:
            current_edge = start_edge
            current_vert = vert
            
            while True:
                for v in current_edge.verts:
                    if v != current_vert:
                        next_vert = v
                        break
                
                next_edge = get_connected_loop_edge(current_edge, next_vert)
                
                if next_edge is None or next_edge in visited:
                    break
                
                visited.add(next_edge)
                loop_edges.append(next_edge)
                current_edge = next_edge
                current_vert = next_vert
        
        return [e.index for e in loop_edges]
    
    def finish(self) -> Optional[bpy.types.Object]:
        """
        Finalize bmesh operations and return the object.
        
        Call this when done with all bmesh operations.
        """
        if self.bm is not None:
            self._update_mesh()
            self.bm.free()
            self.bm = None
        
        return self.obj
    
    def __del__(self):
        """Cleanup bmesh on deletion"""
        if self.bm is not None:
            try:
                self.bm.free()
            except:
                pass


# =========================================================================
# HIGH-LEVEL CHARACTER BUILDING
# =========================================================================

class CharacterBuilder:
    """
    High-level character construction using BmeshTools.
    Builds characters piece by piece with automatic rigging groups.
    """
    
    BONE_GROUPS = {
        'spine': ['spine', 'spine.001', 'spine.002', 'chest'],
        'head': ['neck', 'head'],
        'arm_l': ['shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L'],
        'arm_r': ['shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R'],
        'leg_l': ['thigh.L', 'shin.L', 'foot.L', 'toe.L'],
        'leg_r': ['thigh.R', 'shin.R', 'foot.R', 'toe.R'],
    }
    
    def __init__(self, name: str = "AkkuCharacter"):
        self.name = name
        self.tools = BmeshTools()
        self.parts: Dict[str, List[int]] = {}
    
    def build_torso(
        self,
        width: float = 0.4,
        depth: float = 0.25,
        height: float = 0.6
    ) -> bpy.types.Object:
        """Build the character torso as starting point"""
        obj = self.tools.add_primitive_box(
            size=(width, depth, height),
            location=(0, 0, height / 2 + 0.1),
            name=self.name
        )
        
        self.tools._assign_verts_to_group(list(range(8)), 'spine')
        
        return obj
    
    def extrude_limb(
        self,
        direction: Tuple[float, float, float],
        segments: List[Tuple[float, str]],
        base_scale: float = 1.0
    ) -> List[ExtrudeResult]:
        """
        Extrude a multi-segment limb from the closest face.
        
        Args:
            direction: Direction to find starting face
            segments: List of (length, vertex_group_name) tuples
            base_scale: Starting scale factor
            
        Returns:
            List of extrude results for each segment
        """
        results = []
        
        face_idx = self.tools.get_face_by_normal(direction)
        if face_idx is None:
            return results
        
        current_scale = base_scale
        
        for length, group_name in segments:
            current_scale *= 0.9
            
            result = self.tools.smart_extrude(
                face_index=face_idx,
                length=length,
                vertex_group=group_name,
                scale=(current_scale, current_scale)
            )
            results.append(result)
            
            if result.new_face_indices:
                face_idx = result.new_face_indices[-1]
        
        return results
    
    def add_joint_loops(self, joint_groups: List[str], cuts_per_joint: int = 2):
        """Add loop cuts at joint positions for better deformation"""
        pass
    
    def finalize(self, apply_mirror: bool = True) -> bpy.types.Object:
        """
        Finalize the character mesh.
        
        Args:
            apply_mirror: Apply mirror modifier for symmetry
            
        Returns:
            The finished character object
        """
        obj = self.tools.finish()
        
        if obj and apply_mirror:
            mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
            mirror_mod.use_axis[0] = True
            mirror_mod.use_clip = True
            mirror_mod.merge_threshold = 0.001
        
        return obj


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def add_primitive_box(
    size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    name: str = "AkkuBox"
) -> bpy.types.Object:
    """
    Create a primitive box - starting point for all modeling.
    
    Args:
        size: (width, depth, height) dimensions
        location: (x, y, z) world position
        name: Object name
        
    Returns:
        The created mesh object
    """
    tools = BmeshTools()
    return tools.add_primitive_box(size, location, name)


def smart_extrude(
    obj: bpy.types.Object,
    face_index: int,
    length: float,
    vertex_group: Optional[str] = None
) -> ExtrudeResult:
    """
    Extrude face with automatic vertex group assignment.
    
    Args:
        obj: Mesh object to modify
        face_index: Index of face to extrude
        length: Extrusion distance
        vertex_group: Name of vertex group for rigging
        
    Returns:
        ExtrudeResult with new geometry indices
    """
    tools = BmeshTools(obj)
    result = tools.smart_extrude(face_index, length, vertex_group)
    tools.finish()
    return result


def loop_cut_and_slide(
    obj: bpy.types.Object,
    edge_index: int,
    count: int = 1,
    slide_factor: float = 0.0
) -> LoopCutResult:
    """
    Add loop cuts for smooth joint deformation.
    
    Args:
        obj: Mesh object to modify
        edge_index: Index of edge to cut
        count: Number of cuts
        slide_factor: Position along edge (-1 to 1)
        
    Returns:
        LoopCutResult with new geometry indices
    """
    tools = BmeshTools(obj)
    result = tools.loop_cut_and_slide(edge_index, count, slide_factor)
    tools.finish()
    return result


def mirror_and_weld(
    obj: bpy.types.Object,
    axis: str = 'X',
    merge_threshold: float = 0.001
) -> MirrorResult:
    """
    Mirror geometry and weld center vertices.
    
    Args:
        obj: Mesh object to modify
        axis: Mirror axis ('X', 'Y', or 'Z')
        merge_threshold: Distance for welding
        
    Returns:
        MirrorResult with vertex statistics
    """
    tools = BmeshTools(obj)
    result = tools.mirror_and_weld(axis, merge_threshold)
    tools.finish()
    return result


# =============================================================================
# RIG-AWARE EXTRUDE - Weight Inheritance System
# =============================================================================

@dataclass
class RigAwareExtrudeResult:
    """Result of rig-aware extrude with weight inheritance"""
    new_vert_indices: List[int] = field(default_factory=list)
    new_face_indices: List[int] = field(default_factory=list)
    inherited_weights: Dict[str, List[Tuple[int, float]]] = field(default_factory=dict)
    source_bone: Optional[str] = None


class RigAwareExtruder:
    """
    Extrude with automatic weight inheritance from parent vertices.
    
    When extruding geometry, new vertices automatically inherit
    bone weights from their source vertices, maintaining rig integrity.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
        self._deform_layer = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        """Initialize bmesh with deform layer for weights"""
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
            self._deform_layer = self.bm.verts.layers.deform.verify()
        return self.bm
    
    def _get_vertex_weights(self, vert: bmesh.types.BMVert) -> Dict[int, float]:
        """Get all vertex group weights for a vertex"""
        if self._deform_layer is None:
            return {}
        return dict(vert[self._deform_layer])
    
    def _set_vertex_weights(self, vert: bmesh.types.BMVert, weights: Dict[int, float]):
        """Set vertex group weights for a vertex"""
        if self._deform_layer is None:
            return
        for group_idx, weight in weights.items():
            vert[self._deform_layer][group_idx] = weight
    
    def _average_weights(self, verts: List[bmesh.types.BMVert]) -> Dict[int, float]:
        """Calculate average weights from multiple vertices"""
        if not verts:
            return {}
        
        weight_sums: Dict[int, float] = {}
        weight_counts: Dict[int, int] = {}
        
        for vert in verts:
            weights = self._get_vertex_weights(vert)
            for group_idx, weight in weights.items():
                weight_sums[group_idx] = weight_sums.get(group_idx, 0.0) + weight
                weight_counts[group_idx] = weight_counts.get(group_idx, 0) + 1
        
        return {
            group_idx: weight_sums[group_idx] / weight_counts[group_idx]
            for group_idx in weight_sums
        }
    
    def extrude_with_weight_inheritance(
        self,
        face_index: int,
        length: float,
        scale: Tuple[float, float] = (1.0, 1.0),
        weight_falloff: float = 1.0
    ) -> RigAwareExtrudeResult:
        """
        Extrude face with automatic weight inheritance.
        
        New vertices inherit bone weights from source vertices,
        with optional falloff for gradual weight transition.
        
        Args:
            face_index: Index of face to extrude
            length: Extrusion distance along face normal
            scale: (x, y) scale factors for extruded face
            weight_falloff: 0.0-1.0, how much to preserve parent weights
            
        Returns:
            RigAwareExtrudeResult with new geometry and weight info
        """
        result = RigAwareExtrudeResult()
        
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        if face_index >= len(bm.faces):
            return result
        
        face = bm.faces[face_index]
        normal = face.normal.copy()
        
        source_verts = list(face.verts)
        source_weights = {v: self._get_vertex_weights(v) for v in source_verts}
        avg_weights = self._average_weights(source_verts)
        
        extrude_result = bmesh.ops.extrude_face_region(bm, geom=[face])
        
        new_verts = [v for v in extrude_result['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        translation = normal * length
        bmesh.ops.translate(bm, verts=new_verts, vec=translation)
        
        cap_face = None
        for f in bm.faces:
            if all(v in new_verts for v in f.verts):
                if f.normal.dot(normal) > 0.9:
                    cap_face = f
                    break
        
        if scale != (1.0, 1.0) and cap_face:
            cap_center = cap_face.calc_center_median()
            for vert in cap_face.verts:
                local_pos = vert.co - cap_center
                vert.co.x = cap_center.x + local_pos.x * scale[0]
                vert.co.y = cap_center.y + local_pos.y * scale[1]
        
        for new_vert in new_verts:
            closest_source = None
            min_dist = float('inf')
            
            for src_vert in source_verts:
                src_pos = src_vert.co + translation
                dist = (new_vert.co - src_pos).length
                if dist < min_dist:
                    min_dist = dist
                    closest_source = src_vert
            
            if closest_source and closest_source in source_weights:
                inherited = source_weights[closest_source]
            else:
                inherited = avg_weights
            
            scaled_weights = {
                group_idx: weight * weight_falloff
                for group_idx, weight in inherited.items()
            }
            self._set_vertex_weights(new_vert, scaled_weights)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        result.new_vert_indices = [v.index for v in new_verts]
        if cap_face:
            result.new_face_indices = [cap_face.index]
        
        for group_idx, weight in avg_weights.items():
            group_name = self._get_group_name(group_idx)
            if group_name:
                result.inherited_weights[group_name] = [
                    (v.index, weight * weight_falloff) for v in new_verts
                ]
                if result.source_bone is None:
                    result.source_bone = group_name
        
        self.bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def _get_group_name(self, group_index: int) -> Optional[str]:
        """Get vertex group name from index"""
        for group in self.obj.vertex_groups:
            if group.index == group_index:
                return group.name
        return None
    
    def finish(self):
        """Finalize and free bmesh"""
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# NORMAL RECALCULATOR - Automatic Normal Fixing
# =============================================================================

@dataclass
class NormalRecalcResult:
    """Result of normal recalculation"""
    faces_processed: int = 0
    faces_flipped: int = 0
    is_manifold: bool = True
    has_consistent_normals: bool = True


class NormalRecalculator:
    """
    Automatic normal recalculation and fixing.
    
    Ensures mesh normals are consistent and properly oriented
    after any mesh manipulation operations.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        """Initialize bmesh"""
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def recalculate_normals(self, inside: bool = False) -> NormalRecalcResult:
        """
        Recalculate all face normals to be consistent.
        
        Args:
            inside: If True, orient normals inward (for hollow objects)
            
        Returns:
            NormalRecalcResult with processing statistics
        """
        result = NormalRecalcResult()
        
        bm = self._ensure_bmesh()
        
        result.faces_processed = len(bm.faces)
        
        result.is_manifold = all(e.is_manifold for e in bm.edges)
        
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        
        if inside:
            for face in bm.faces:
                face.normal_flip()
                result.faces_flipped += 1
        
        bm.normal_update()
        
        if result.faces_processed > 0:
            first_face = bm.faces[0]
            for face in bm.faces[1:]:
                for edge in face.edges:
                    if edge in first_face.edges:
                        if face.normal.dot(first_face.normal) < 0:
                            result.has_consistent_normals = False
                            break
        
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def flip_normals(self, face_indices: Optional[List[int]] = None) -> int:
        """
        Flip normals of specified faces (or all faces).
        
        Args:
            face_indices: List of face indices to flip, or None for all
            
        Returns:
            Number of faces flipped
        """
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        if face_indices is None:
            faces_to_flip = list(bm.faces)
        else:
            faces_to_flip = [bm.faces[i] for i in face_indices if i < len(bm.faces)]
        
        for face in faces_to_flip:
            face.normal_flip()
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return len(faces_to_flip)
    
    def smooth_vertex_normals(self, angle_threshold: float = 30.0):
        """
        Apply smooth shading based on angle threshold.
        
        Args:
            angle_threshold: Edges sharper than this angle stay sharp (degrees)
        """
        import math
        
        bm = self._ensure_bmesh()
        
        threshold_rad = math.radians(angle_threshold)
        
        for edge in bm.edges:
            if len(edge.link_faces) == 2:
                angle = edge.calc_face_angle()
                edge.smooth = angle < threshold_rad
        
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
    
    def finish(self):
        """Finalize and free bmesh"""
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# EDGE LOOP CUTTER - Advanced Loop Cut System
# =============================================================================

@dataclass
class EdgeLoopResult:
    """Result of edge loop operation"""
    loop_edge_indices: List[int] = field(default_factory=list)
    loop_vert_indices: List[int] = field(default_factory=list)
    is_closed_loop: bool = False
    loop_length: float = 0.0


class EdgeLoopCutter:
    """
    Advanced edge loop cutting for joint creation.
    
    Follows edge flow to create proper loop cuts that
    enable smooth deformation at joints.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        """Initialize bmesh"""
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def find_edge_loop(self, edge_index: int) -> EdgeLoopResult:
        """
        Find all edges in a loop starting from given edge.
        
        Args:
            edge_index: Starting edge index
            
        Returns:
            EdgeLoopResult with loop information
        """
        result = EdgeLoopResult()
        
        bm = self._ensure_bmesh()
        bm.edges.ensure_lookup_table()
        
        if edge_index >= len(bm.edges):
            return result
        
        start_edge = bm.edges[edge_index]
        loop_edges = [start_edge]
        visited = {start_edge}
        
        def find_opposite_edge(edge: bmesh.types.BMEdge, face: bmesh.types.BMFace) -> Optional[bmesh.types.BMEdge]:
            """Find edge on opposite side of quad face"""
            if len(face.edges) != 4:
                return None
            
            face_edges = list(face.edges)
            idx = face_edges.index(edge)
            opposite_idx = (idx + 2) % 4
            return face_edges[opposite_idx]
        
        for direction in [0, 1]:
            current_edge = start_edge
            current_vert = start_edge.verts[direction]
            
            while True:
                other_vert = current_edge.other_vert(current_vert)
                if other_vert is None:
                    break
                
                next_edge = None
                for face in current_edge.link_faces:
                    if len(face.edges) == 4:
                        opposite = find_opposite_edge(current_edge, face)
                        if opposite and opposite not in visited:
                            next_edge = opposite
                            break
                
                if next_edge is None:
                    break
                
                visited.add(next_edge)
                
                if direction == 0:
                    loop_edges.append(next_edge)
                else:
                    loop_edges.insert(0, next_edge)
                
                shared_verts = set(current_edge.verts) & set(next_edge.verts)
                if not shared_verts:
                    for face in next_edge.link_faces:
                        if current_edge in face.edges:
                            shared_verts = set(next_edge.verts) - {other_vert}
                            break
                
                if shared_verts:
                    current_vert = list(shared_verts)[0]
                else:
                    break
                
                current_edge = next_edge
                
                if current_edge == start_edge:
                    result.is_closed_loop = True
                    break
        
        result.loop_edge_indices = [e.index for e in loop_edges]
        
        verts_in_loop = set()
        for edge in loop_edges:
            verts_in_loop.update(edge.verts)
        result.loop_vert_indices = [v.index for v in verts_in_loop]
        
        result.loop_length = sum(e.calc_length() for e in loop_edges)
        
        return result
    
    def cut_loop(
        self,
        edge_index: int,
        cuts: int = 1,
        slide: float = 0.0,
        inherit_weights: bool = True
    ) -> LoopCutResult:
        """
        Cut edge loop with optional weight inheritance.
        
        Args:
            edge_index: Starting edge in the loop
            cuts: Number of cuts to make
            slide: -1.0 to 1.0, position of cuts
            inherit_weights: If True, new verts inherit weights from neighbors
            
        Returns:
            LoopCutResult with new geometry
        """
        result = LoopCutResult()
        result.slide_factor = slide
        
        bm = self._ensure_bmesh()
        
        loop_info = self.find_edge_loop(edge_index)
        if not loop_info.loop_edge_indices:
            return result
        
        bm.edges.ensure_lookup_table()
        loop_edges = [bm.edges[i] for i in loop_info.loop_edge_indices if i < len(bm.edges)]
        
        original_verts = set(v.index for v in bm.verts)
        original_edges = set(e.index for e in bm.edges)
        
        deform_layer = bm.verts.layers.deform.verify()
        
        edge_weights = {}
        for edge in loop_edges:
            v1_weights = dict(edge.verts[0][deform_layer])
            v2_weights = dict(edge.verts[1][deform_layer])
            edge_weights[edge] = (v1_weights, v2_weights)
        
        subdivide_result = bmesh.ops.subdivide_edges(
            bm,
            edges=loop_edges,
            cuts=cuts,
            use_grid_fill=False,
        )
        
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        new_verts = [v for v in bm.verts if v.index not in original_verts]
        
        if slide != 0.0:
            for vert in new_verts:
                edges = list(vert.link_edges)
                if len(edges) >= 2:
                    v1 = edges[0].other_vert(vert)
                    v2 = edges[1].other_vert(vert)
                    
                    if v1 and v2:
                        direction = (v1.co - v2.co).normalized()
                        max_slide = (v1.co - vert.co).length
                        vert.co += direction * slide * max_slide * 0.5
        
        if inherit_weights:
            for vert in new_verts:
                neighbor_weights: Dict[int, List[float]] = {}
                
                for edge in vert.link_edges:
                    other = edge.other_vert(vert)
                    if other and other.index in original_verts:
                        weights = dict(other[deform_layer])
                        for group_idx, weight in weights.items():
                            if group_idx not in neighbor_weights:
                                neighbor_weights[group_idx] = []
                            neighbor_weights[group_idx].append(weight)
                
                for group_idx, weights in neighbor_weights.items():
                    avg_weight = sum(weights) / len(weights)
                    vert[deform_layer][group_idx] = avg_weight
        
        result.new_vert_indices = [v.index for v in new_verts]
        result.new_edge_indices = [e.index for e in bm.edges if e.index not in original_edges]
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def add_joint_loops(
        self,
        joint_position: Tuple[float, float, float],
        loops_before: int = 1,
        loops_after: int = 1,
        spacing: float = 0.1
    ) -> List[LoopCutResult]:
        """
        Add supporting loops around a joint position.
        
        Args:
            joint_position: (x, y, z) position of joint
            loops_before: Number of loops before joint
            loops_after: Number of loops after joint
            spacing: Distance between loops
            
        Returns:
            List of LoopCutResult for each added loop
        """
        results = []
        
        bm = self._ensure_bmesh()
        joint_vec = Vector(joint_position)
        
        closest_edge = None
        closest_dist = float('inf')
        
        bm.edges.ensure_lookup_table()
        for edge in bm.edges:
            mid = (edge.verts[0].co + edge.verts[1].co) / 2
            dist = (mid - joint_vec).length
            if dist < closest_dist:
                closest_dist = dist
                closest_edge = edge
        
        if closest_edge is None:
            return results
        
        for i in range(loops_before):
            slide = -(i + 1) * spacing / closest_dist if closest_dist > 0 else 0
            slide = max(-0.9, min(0.9, slide))
            result = self.cut_loop(closest_edge.index, cuts=1, slide=slide)
            results.append(result)
        
        for i in range(loops_after):
            slide = (i + 1) * spacing / closest_dist if closest_dist > 0 else 0
            slide = max(-0.9, min(0.9, slide))
            result = self.cut_loop(closest_edge.index, cuts=1, slide=slide)
            results.append(result)
        
        return results
    
    def finish(self):
        """Finalize and free bmesh"""
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# ATOMIC OPERATIONS WRAPPER - Unified Interface
# =============================================================================

class AtomicMeshOps:
    """
    Unified interface for all atomic mesh operations.
    
    This class wraps all low-level operations into a single interface
    that handles bmesh lifecycle, normal recalculation, and cleanup.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self._tools = BmeshTools(obj)
        self._rig_extruder: Optional[RigAwareExtruder] = None
        self._loop_cutter: Optional[EdgeLoopCutter] = None
        self._normal_calc: Optional[NormalRecalculator] = None
    
    def add_box(
        self,
        size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        name: str = "AkkuBox"
    ) -> bpy.types.Object:
        """Create a primitive box"""
        return self._tools.add_primitive_box(size, location, name)
    
    def extrude(
        self,
        face_index: int,
        length: float,
        vertex_group: Optional[str] = None,
        scale: Tuple[float, float] = (1.0, 1.0),
        inherit_weights: bool = False
    ):
        """
        Extrude face with optional weight inheritance.
        
        Args:
            face_index: Face to extrude
            length: Extrusion distance
            vertex_group: Vertex group for new verts
            scale: Scale factor for extruded face
            inherit_weights: If True, inherit weights from source
        """
        if inherit_weights:
            if self._rig_extruder is None:
                self._rig_extruder = RigAwareExtruder(self.obj)
            return self._rig_extruder.extrude_with_weight_inheritance(
                face_index, length, scale
            )
        else:
            return self._tools.smart_extrude(
                face_index, length, vertex_group, scale
            )
    
    def loop_cut(
        self,
        edge_index: int,
        cuts: int = 1,
        slide: float = 0.0,
        inherit_weights: bool = True
    ) -> LoopCutResult:
        """
        Add loop cuts following edge flow.
        
        Args:
            edge_index: Starting edge
            cuts: Number of cuts
            slide: Position of cuts (-1 to 1)
            inherit_weights: Inherit weights from neighbors
        """
        if self._loop_cutter is None:
            self._loop_cutter = EdgeLoopCutter(self.obj)
        return self._loop_cutter.cut_loop(edge_index, cuts, slide, inherit_weights)
    
    def mirror(
        self,
        axis: str = 'X',
        merge_threshold: float = 0.001
    ) -> MirrorResult:
        """Mirror and weld geometry"""
        return self._tools.mirror_and_weld(axis, merge_threshold)
    
    def recalculate_normals(self, inside: bool = False) -> NormalRecalcResult:
        """Recalculate all face normals"""
        if self._normal_calc is None:
            self._normal_calc = NormalRecalculator(self.obj)
        return self._normal_calc.recalculate_normals(inside)
    
    def finalize(self, recalc_normals: bool = True) -> bpy.types.Object:
        """
        Finalize all operations and clean up.
        
        Args:
            recalc_normals: If True, recalculate normals before finishing
            
        Returns:
            The modified object
        """
        if recalc_normals:
            self.recalculate_normals()
        
        self._tools.finish()
        
        if self._rig_extruder:
            self._rig_extruder.finish()
        if self._loop_cutter:
            self._loop_cutter.finish()
        if self._normal_calc:
            self._normal_calc.finish()
        
        return self.obj


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def rig_aware_extrude(
    obj: bpy.types.Object,
    face_index: int,
    length: float,
    weight_falloff: float = 1.0
) -> RigAwareExtrudeResult:
    """
    Extrude face with automatic weight inheritance.
    
    Args:
        obj: Mesh object
        face_index: Face to extrude
        length: Extrusion distance
        weight_falloff: Weight preservation factor (0-1)
    """
    extruder = RigAwareExtruder(obj)
    result = extruder.extrude_with_weight_inheritance(face_index, length, weight_falloff=weight_falloff)
    extruder.finish()
    return result


def recalculate_normals(obj: bpy.types.Object, inside: bool = False) -> NormalRecalcResult:
    """
    Recalculate and fix mesh normals.
    
    Args:
        obj: Mesh object
        inside: Orient normals inward if True
    """
    calc = NormalRecalculator(obj)
    result = calc.recalculate_normals(inside)
    calc.finish()
    return result


def cut_edge_loop(
    obj: bpy.types.Object,
    edge_index: int,
    cuts: int = 1,
    slide: float = 0.0,
    inherit_weights: bool = True
) -> LoopCutResult:
    """
    Cut edge loop following edge flow.
    
    Args:
        obj: Mesh object
        edge_index: Starting edge
        cuts: Number of cuts
        slide: Position (-1 to 1)
        inherit_weights: Inherit weights from neighbors
    """
    cutter = EdgeLoopCutter(obj)
    result = cutter.cut_loop(edge_index, cuts, slide, inherit_weights)
    cutter.finish()
    return result


# =============================================================================
# SYMMETRY MIRRORING - Real-time Mirror with Auto-Weld
# =============================================================================

@dataclass
class SymmetryResult:
    """Result of symmetry mirroring operation"""
    mirrored_vert_count: int = 0
    welded_vert_count: int = 0
    center_verts_merged: int = 0
    axis: str = 'X'


class SymmetryMirror:
    """
    Symmetry mirroring with automatic center vertex welding.
    
    Work on one half of the model, mirror to the other side,
    and automatically weld vertices at the center seam.
    """
    
    WELD_THRESHOLD = 0.0001
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def mirror_geometry(
        self,
        axis: str = 'X',
        merge_center: bool = True,
        merge_threshold: float = 0.001,
        flip_normals: bool = True,
        source_side: str = 'positive'
    ) -> SymmetryResult:
        """
        Mirror geometry across specified axis with center weld.
        
        Args:
            axis: 'X', 'Y', or 'Z' - mirror axis
            merge_center: If True, weld vertices at center (axis=0)
            merge_threshold: Distance for merging center vertices
            flip_normals: If True, flip normals on mirrored faces
            source_side: 'positive' or 'negative' - which side to keep and mirror
            
        Returns:
            SymmetryResult with operation statistics
        """
        result = SymmetryResult(axis=axis)
        
        bm = self._ensure_bmesh()
        
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}.get(axis.upper(), 0)
        
        original_verts = list(bm.verts)
        original_faces = list(bm.faces)
        
        if source_side.lower() == 'positive':
            source_verts = [v for v in original_verts if v.co[axis_idx] > self.WELD_THRESHOLD]
        else:
            source_verts = [v for v in original_verts if v.co[axis_idx] < -self.WELD_THRESHOLD]
        
        vert_map = {}
        for vert in source_verts:
            new_co = vert.co.copy()
            new_co[axis_idx] = -new_co[axis_idx]
            new_vert = bm.verts.new(new_co)
            vert_map[vert] = new_vert
            result.mirrored_vert_count += 1
        
        center_verts = [v for v in original_verts if abs(v.co[axis_idx]) <= self.WELD_THRESHOLD]
        for vert in center_verts:
            vert_map[vert] = vert
        
        for face in original_faces:
            if all(v in vert_map for v in face.verts):
                new_face_verts = [vert_map[v] for v in face.verts]
                
                if flip_normals:
                    new_face_verts = list(reversed(new_face_verts))
                
                try:
                    bm.faces.new(new_face_verts)
                except ValueError:
                    pass
        
        if merge_center:
            bm.verts.ensure_lookup_table()
            
            center_pairs = []
            for orig_vert, new_vert in vert_map.items():
                if orig_vert != new_vert:
                    if abs(orig_vert.co[axis_idx]) <= merge_threshold:
                        if abs(new_vert.co[axis_idx]) <= merge_threshold:
                            center_pairs.append((orig_vert, new_vert))
            
            for v1, v2 in center_pairs:
                if v1.is_valid and v2.is_valid:
                    try:
                        bmesh.ops.pointmerge(bm, verts=[v1, v2], merge_co=v1.co)
                        result.center_verts_merged += 1
                    except:
                        pass
            
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge_threshold)
        
        bm.verts.ensure_lookup_table()
        result.welded_vert_count = len(bm.verts)
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def delete_half(self, axis: str = 'X', keep_positive: bool = True):
        """
        Delete half of the mesh for symmetry editing.
        
        Args:
            axis: 'X', 'Y', or 'Z'
            keep_positive: Keep positive side if True, negative if False
        """
        bm = self._ensure_bmesh()
        
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}.get(axis.upper(), 0)
        
        verts_to_delete = []
        for vert in bm.verts:
            coord = vert.co[axis_idx]
            if keep_positive and coord < -self.WELD_THRESHOLD:
                verts_to_delete.append(vert)
            elif not keep_positive and coord > self.WELD_THRESHOLD:
                verts_to_delete.append(vert)
        
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
        
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
    
    def finish(self):
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# FACE NORMAL ORIENT - Force Outward-Facing Normals
# =============================================================================

@dataclass
class NormalOrientResult:
    """Result of normal orientation operation"""
    faces_processed: int = 0
    faces_flipped: int = 0
    is_watertight: bool = False


class FaceNormalOrient:
    """
    Force all face normals to point outward.
    
    Essential for proper shader rendering - inward-facing
    normals cause black rendering artifacts.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def orient_outward(self) -> NormalOrientResult:
        """
        Orient all face normals to point outward from mesh center.
        
        Uses mesh centroid to determine inside vs outside.
        
        Returns:
            NormalOrientResult with processing statistics
        """
        result = NormalOrientResult()
        
        bm = self._ensure_bmesh()
        
        centroid = Vector((0, 0, 0))
        for vert in bm.verts:
            centroid += vert.co
        if len(bm.verts) > 0:
            centroid /= len(bm.verts)
        
        result.faces_processed = len(bm.faces)
        
        for face in bm.faces:
            face_center = face.calc_center_median()
            outward_dir = (face_center - centroid).normalized()
            
            if face.normal.dot(outward_dir) < 0:
                face.normal_flip()
                result.faces_flipped += 1
        
        result.is_watertight = all(e.is_manifold for e in bm.edges)
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def make_consistent(self) -> NormalOrientResult:
        """
        Make all normals consistent using Blender's algorithm.
        
        Uses bmesh.ops.recalc_face_normals for proper topology-based
        normal calculation (better for complex shapes).
        """
        result = NormalOrientResult()
        
        bm = self._ensure_bmesh()
        result.faces_processed = len(bm.faces)
        
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return result
    
    def finish(self):
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# LOCAL VS GLOBAL TRANSFORM - Coordinate Space Control
# =============================================================================

class TransformSpace:
    """
    Transform vertices in local (face normal) or global (world XYZ) space.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def move_along_normal(
        self,
        face_index: int,
        distance: float,
        affect_connected: bool = False
    ) -> List[int]:
        """
        Move face vertices along face normal direction.
        
        Args:
            face_index: Face to use for normal direction
            distance: Distance to move (positive = outward)
            affect_connected: If True, also move adjacent vertices
            
        Returns:
            List of moved vertex indices
        """
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        if face_index >= len(bm.faces):
            return []
        
        face = bm.faces[face_index]
        normal = face.normal.copy()
        
        verts_to_move = set(face.verts)
        
        if affect_connected:
            for vert in list(verts_to_move):
                for edge in vert.link_edges:
                    verts_to_move.add(edge.other_vert(vert))
        
        translation = normal * distance
        for vert in verts_to_move:
            vert.co += translation
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return [v.index for v in verts_to_move]
    
    def move_global(
        self,
        vert_indices: List[int],
        translation: Tuple[float, float, float]
    ) -> int:
        """
        Move vertices in global world coordinates.
        
        Args:
            vert_indices: List of vertex indices to move
            translation: (x, y, z) movement in world space
            
        Returns:
            Number of vertices moved
        """
        bm = self._ensure_bmesh()
        bm.verts.ensure_lookup_table()
        
        trans_vec = Vector(translation)
        moved = 0
        
        for idx in vert_indices:
            if idx < len(bm.verts):
                bm.verts[idx].co += trans_vec
                moved += 1
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return moved
    
    def scale_from_face_center(
        self,
        face_index: int,
        scale: Tuple[float, float, float]
    ) -> List[int]:
        """
        Scale vertices relative to face center in local space.
        
        Args:
            face_index: Face to use as scale center
            scale: (x, y, z) scale factors in face-local space
            
        Returns:
            List of scaled vertex indices
        """
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        if face_index >= len(bm.faces):
            return []
        
        face = bm.faces[face_index]
        center = face.calc_center_median()
        
        normal = face.normal.normalized()
        tangent = (face.verts[1].co - face.verts[0].co).normalized()
        bitangent = normal.cross(tangent).normalized()
        
        for vert in face.verts:
            local_pos = vert.co - center
            
            n_comp = local_pos.dot(normal)
            t_comp = local_pos.dot(tangent)
            b_comp = local_pos.dot(bitangent)
            
            n_comp *= scale[2]
            t_comp *= scale[0]
            b_comp *= scale[1]
            
            vert.co = center + tangent * t_comp + bitangent * b_comp + normal * n_comp
        
        bm.normal_update()
        bm.to_mesh(self.obj.data)
        self.obj.data.update()
        
        return [v.index for v in face.verts]
    
    def finish(self):
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# SELECTION FILTER - Position-Based Face Selection
# =============================================================================

@dataclass
class SelectionResult:
    """Result of position-based selection"""
    face_indices: List[int] = field(default_factory=list)
    vert_indices: List[int] = field(default_factory=list)
    edge_indices: List[int] = field(default_factory=list)
    selection_type: str = ""


class SelectionFilter:
    """
    Position-based automatic selection for AI-friendly modeling.
    
    Select faces by semantic position (top, front, left, etc.)
    instead of requiring specific indices.
    """
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Object must be a mesh")
        self.obj = obj
        self.bm: Optional[bmesh.types.BMesh] = None
    
    def _ensure_bmesh(self) -> bmesh.types.BMesh:
        if self.bm is None:
            self.bm = bmesh.new()
            self.bm.from_mesh(self.obj.data)
        return self.bm
    
    def _get_bounds(self) -> Tuple[Vector, Vector]:
        """Get mesh bounding box min/max"""
        bm = self._ensure_bmesh()
        
        if not bm.verts:
            return Vector((0, 0, 0)), Vector((0, 0, 0))
        
        min_co = Vector(bm.verts[0].co)
        max_co = Vector(bm.verts[0].co)
        
        for vert in bm.verts:
            for i in range(3):
                min_co[i] = min(min_co[i], vert.co[i])
                max_co[i] = max(max_co[i], vert.co[i])
        
        return min_co, max_co
    
    def select_by_position(
        self,
        position: str,
        threshold: float = 0.1
    ) -> SelectionResult:
        """
        Select faces by semantic position.
        
        Args:
            position: 'top', 'bottom', 'front', 'back', 'left', 'right',
                     'center_x', 'center_y', 'center_z'
            threshold: Relative threshold (0-1) for selection range
            
        Returns:
            SelectionResult with selected geometry
        """
        result = SelectionResult(selection_type=position)
        
        bm = self._ensure_bmesh()
        min_co, max_co = self._get_bounds()
        size = max_co - min_co
        
        position_map = {
            'top': (2, 'max'),
            'bottom': (2, 'min'),
            'front': (1, 'max'),
            'back': (1, 'min'),
            'right': (0, 'max'),
            'left': (0, 'min'),
            'center_x': (0, 'center'),
            'center_y': (1, 'center'),
            'center_z': (2, 'center'),
        }
        
        pos_lower = position.lower()
        if pos_lower not in position_map:
            return result
        
        axis, direction = position_map[pos_lower]
        
        if direction == 'max':
            target_val = max_co[axis]
            range_min = target_val - size[axis] * threshold
            range_max = target_val + 0.001
        elif direction == 'min':
            target_val = min_co[axis]
            range_min = target_val - 0.001
            range_max = target_val + size[axis] * threshold
        else:
            center_val = (min_co[axis] + max_co[axis]) / 2
            half_range = size[axis] * threshold / 2
            range_min = center_val - half_range
            range_max = center_val + half_range
        
        selected_verts = set()
        for face in bm.faces:
            center = face.calc_center_median()
            if range_min <= center[axis] <= range_max:
                result.face_indices.append(face.index)
                selected_verts.update(v.index for v in face.verts)
        
        result.vert_indices = list(selected_verts)
        
        return result
    
    def select_by_normal(
        self,
        direction: str,
        angle_threshold: float = 45.0
    ) -> SelectionResult:
        """
        Select faces by normal direction.
        
        Args:
            direction: 'up', 'down', 'forward', 'backward', 'left', 'right'
            angle_threshold: Maximum angle deviation in degrees
            
        Returns:
            SelectionResult with selected geometry
        """
        import math
        
        result = SelectionResult(selection_type=f"normal_{direction}")
        
        bm = self._ensure_bmesh()
        
        direction_map = {
            'up': Vector((0, 0, 1)),
            'down': Vector((0, 0, -1)),
            'forward': Vector((0, 1, 0)),
            'backward': Vector((0, -1, 0)),
            'right': Vector((1, 0, 0)),
            'left': Vector((-1, 0, 0)),
        }
        
        dir_lower = direction.lower()
        if dir_lower not in direction_map:
            return result
        
        target_normal = direction_map[dir_lower]
        threshold_rad = math.radians(angle_threshold)
        
        selected_verts = set()
        for face in bm.faces:
            angle = face.normal.angle(target_normal)
            if angle <= threshold_rad:
                result.face_indices.append(face.index)
                selected_verts.update(v.index for v in face.verts)
        
        result.vert_indices = list(selected_verts)
        
        return result
    
    def select_extremes(
        self,
        axis: str = 'Z',
        select_max: bool = True,
        count: int = 1
    ) -> SelectionResult:
        """
        Select the most extreme faces along an axis.
        
        Args:
            axis: 'X', 'Y', or 'Z'
            select_max: If True, select highest; if False, select lowest
            count: Number of faces to select
            
        Returns:
            SelectionResult with selected geometry
        """
        result = SelectionResult(selection_type=f"extreme_{axis}_{('max' if select_max else 'min')}")
        
        bm = self._ensure_bmesh()
        
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}.get(axis.upper(), 2)
        
        face_positions = []
        for face in bm.faces:
            center = face.calc_center_median()
            face_positions.append((face.index, center[axis_idx]))
        
        face_positions.sort(key=lambda x: x[1], reverse=select_max)
        
        selected_verts = set()
        for i in range(min(count, len(face_positions))):
            face_idx = face_positions[i][0]
            result.face_indices.append(face_idx)
            
            bm.faces.ensure_lookup_table()
            face = bm.faces[face_idx]
            selected_verts.update(v.index for v in face.verts)
        
        result.vert_indices = list(selected_verts)
        
        return result
    
    def select_adjacent_to(
        self,
        face_indices: List[int],
        depth: int = 1
    ) -> SelectionResult:
        """
        Select faces adjacent to given faces.
        
        Args:
            face_indices: Starting face indices
            depth: How many layers of adjacency to include
            
        Returns:
            SelectionResult with selected geometry
        """
        result = SelectionResult(selection_type="adjacent")
        
        bm = self._ensure_bmesh()
        bm.faces.ensure_lookup_table()
        
        selected = set()
        current_layer = set()
        
        for idx in face_indices:
            if idx < len(bm.faces):
                selected.add(idx)
                current_layer.add(bm.faces[idx])
        
        for _ in range(depth):
            next_layer = set()
            for face in current_layer:
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face.index not in selected:
                            selected.add(linked_face.index)
                            next_layer.add(linked_face)
            current_layer = next_layer
        
        result.face_indices = list(selected)
        
        selected_verts = set()
        for idx in result.face_indices:
            face = bm.faces[idx]
            selected_verts.update(v.index for v in face.verts)
        result.vert_indices = list(selected_verts)
        
        return result
    
    def finish(self):
        if self.bm is not None:
            self.bm.free()
            self.bm = None


# =============================================================================
# CONVENIENCE FUNCTIONS FOR GEOMETRIC OPS
# =============================================================================

def symmetry_mirror(
    obj: bpy.types.Object,
    axis: str = 'X',
    merge_center: bool = True,
    merge_threshold: float = 0.001
) -> SymmetryResult:
    """
    Mirror mesh with automatic center welding.
    
    Args:
        obj: Mesh object
        axis: 'X', 'Y', or 'Z'
        merge_center: Weld center vertices
        merge_threshold: Distance for merging
    """
    mirror = SymmetryMirror(obj)
    result = mirror.mirror_geometry(axis, merge_center, merge_threshold)
    mirror.finish()
    return result


def orient_normals_outward(obj: bpy.types.Object) -> NormalOrientResult:
    """
    Force all face normals to point outward using topology-based algorithm.
    
    Uses bmesh.ops.recalc_face_normals for reliable results on all mesh types.
    
    Args:
        obj: Mesh object
    """
    orient = FaceNormalOrient(obj)
    result = orient.make_consistent()
    orient.finish()
    return result


def select_faces_by_position(
    obj: bpy.types.Object,
    position: str,
    threshold: float = 0.1
) -> SelectionResult:
    """
    Select faces by semantic position.
    
    Args:
        obj: Mesh object
        position: 'top', 'bottom', 'front', 'back', 'left', 'right'
        threshold: Selection range (0-1)
    """
    selector = SelectionFilter(obj)
    result = selector.select_by_position(position, threshold)
    selector.finish()
    return result


def move_along_face_normal(
    obj: bpy.types.Object,
    face_index: int,
    distance: float
) -> List[int]:
    """
    Move face vertices along local normal direction.
    
    Args:
        obj: Mesh object
        face_index: Face to move
        distance: Distance (positive = outward)
    """
    transform = TransformSpace(obj)
    result = transform.move_along_normal(face_index, distance)
    transform.finish()
    return result
