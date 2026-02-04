"""
Akku SDK v3.7 - BMesh Direct Manipulation Tools
Low-level mesh editing primitives for procedural character generation
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
