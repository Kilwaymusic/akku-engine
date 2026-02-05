"""
Akku SDK v4.0 - Sculpt Operations Module

Pure procedural sculpting operations for high-quality character generation.
Implements subdivision, smoothing, and sculpt-like vertex manipulation.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class SubdivisionOps:
    """
    Subdivision surface operations for mesh refinement.
    """
    
    @staticmethod
    def apply_subdivision(
        obj: bpy.types.Object,
        levels: int = 2,
        render_levels: int = 2,
        apply_modifier: bool = True
    ) -> bpy.types.Object:
        """
        Apply Catmull-Clark subdivision to mesh.
        Uses depsgraph for headless/CLI compatibility.
        
        Args:
            obj: Target mesh object
            levels: Viewport subdivision levels (clamped 0-3)
            render_levels: Render subdivision levels
            apply_modifier: Whether to apply modifier permanently
            
        Returns:
            Modified object
        """
        levels = max(0, min(3, levels))
        render_levels = max(0, min(3, render_levels))
        
        if levels == 0:
            return obj
        
        mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
        mod.levels = levels
        mod.render_levels = render_levels
        mod.subdivision_type = 'CATMULL_CLARK'
        
        if apply_modifier:
            try:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(depsgraph)
                mesh_from_eval = bpy.data.meshes.new_from_object(obj_eval)
                
                obj.modifiers.remove(mod)
                
                old_mesh = obj.data
                obj.data = mesh_from_eval
                bpy.data.meshes.remove(old_mesh)
            except Exception as e:
                print(f"[Akku SDK] Subdivision apply failed: {e}, keeping modifier")
        
        return obj
    
    @staticmethod
    def add_edge_loops(
        obj: bpy.types.Object,
        edge_indices: List[int],
        cuts: int = 1,
        smoothness: float = 0.0
    ) -> bpy.types.Object:
        """
        Add edge loops to mesh for better deformation.
        Uses bmesh subdivide_edges operation.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        
        edges_to_cut = []
        for idx in edge_indices:
            if idx < len(bm.edges):
                edges_to_cut.append(bm.edges[idx])
        
        if edges_to_cut:
            bmesh.ops.subdivide_edges(
                bm,
                edges=edges_to_cut,
                cuts=cuts,
                smooth=smoothness,
                use_grid_fill=True
            )
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @staticmethod
    def add_loop_cuts_by_position(
        obj: bpy.types.Object,
        axis: str = 'Z',
        positions: List[float] = None,
        tolerance: float = 0.05
    ) -> bpy.types.Object:
        """
        Add loop cuts at specific positions along an axis.
        Useful for adding joint loops at elbows, knees, etc.
        """
        if positions is None:
            return obj
            
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}.get(axis.upper(), 2)
        
        for pos in positions:
            edges_at_pos = []
            for edge in bm.edges:
                mid = (edge.verts[0].co + edge.verts[1].co) / 2
                if abs(mid[axis_idx] - pos) < tolerance:
                    edges_at_pos.append(edge)
            
            if edges_at_pos:
                bmesh.ops.subdivide_edges(
                    bm,
                    edges=edges_at_pos,
                    cuts=1,
                    smooth=0.0
                )
                bm.edges.ensure_lookup_table()
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj


class SculptBrush(Enum):
    """Sculpt brush types"""
    GRAB = "grab"
    SMOOTH = "smooth"
    INFLATE = "inflate"
    PINCH = "pinch"
    FLATTEN = "flatten"
    CREASE = "crease"


@dataclass
class SculptStroke:
    """Configuration for a sculpt stroke"""
    brush: SculptBrush
    center: Vector
    radius: float
    strength: float = 0.5
    direction: Optional[Vector] = None
    falloff: str = "smooth"


class SculptOps:
    """
    Sculpting operations for vertex manipulation.
    Implements procedural sculpt-like deformations.
    """
    
    @staticmethod
    def _get_falloff(distance: float, radius: float, falloff_type: str = "smooth") -> float:
        """Calculate falloff value based on distance from center"""
        if distance >= radius:
            return 0.0
        
        t = distance / radius
        
        if falloff_type == "smooth":
            return 1.0 - (3 * t * t - 2 * t * t * t)
        elif falloff_type == "sphere":
            return math.sqrt(1.0 - t * t)
        elif falloff_type == "sharp":
            return 1.0 - t * t
        elif falloff_type == "linear":
            return 1.0 - t
        elif falloff_type == "constant":
            return 1.0
        else:
            return 1.0 - t
    
    @classmethod
    def grab(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        offset: Vector,
        strength: float = 1.0,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Grab brush - moves vertices within radius.
        
        Args:
            obj: Target mesh object
            center: Center point of brush
            radius: Brush radius
            offset: Direction and magnitude of movement
            strength: Brush strength (0-1)
            falloff: Falloff type
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        for vert in bm.verts:
            distance = (vert.co - center).length
            if distance < radius:
                factor = cls._get_falloff(distance, radius, falloff) * strength
                vert.co += offset * factor
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def smooth(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        iterations: int = 1,
        strength: float = 0.5,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Smooth brush - averages vertex positions with neighbors.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        for _ in range(iterations):
            new_positions = {}
            
            for vert in bm.verts:
                distance = (vert.co - center).length
                if distance < radius:
                    factor = cls._get_falloff(distance, radius, falloff) * strength
                    
                    if vert.link_edges:
                        neighbor_avg = Vector((0, 0, 0))
                        count = 0
                        for edge in vert.link_edges:
                            other = edge.other_vert(vert)
                            neighbor_avg += other.co
                            count += 1
                        
                        if count > 0:
                            neighbor_avg /= count
                            new_positions[vert.index] = vert.co.lerp(neighbor_avg, factor)
            
            for idx, pos in new_positions.items():
                bm.verts[idx].co = pos
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def inflate(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        strength: float = 0.1,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Inflate brush - pushes vertices along their normals.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.normal_update()
        
        for vert in bm.verts:
            distance = (vert.co - center).length
            if distance < radius:
                factor = cls._get_falloff(distance, radius, falloff) * strength
                vert.co += vert.normal * factor
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def pinch(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        strength: float = 0.5,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Pinch brush - pulls vertices toward center.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        for vert in bm.verts:
            distance = (vert.co - center).length
            if distance < radius and distance > 0:
                factor = cls._get_falloff(distance, radius, falloff) * strength
                direction = (center - vert.co).normalized()
                vert.co += direction * factor * distance
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def flatten(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        plane_normal: Vector = None,
        strength: float = 0.5,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Flatten brush - flattens vertices to a plane.
        """
        if plane_normal is None:
            plane_normal = Vector((0, 0, 1))
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        plane_normal = plane_normal.normalized()
        plane_d = center.dot(plane_normal)
        
        for vert in bm.verts:
            distance = (vert.co - center).length
            if distance < radius:
                factor = cls._get_falloff(distance, radius, falloff) * strength
                
                dist_to_plane = vert.co.dot(plane_normal) - plane_d
                vert.co -= plane_normal * dist_to_plane * factor
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def crease(
        cls,
        obj: bpy.types.Object,
        center: Vector,
        radius: float,
        direction: Vector,
        strength: float = 0.5,
        falloff: str = "smooth"
    ) -> bpy.types.Object:
        """
        Crease brush - creates sharp creases by pushing vertices along direction.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.normal_update()
        
        direction = direction.normalized()
        
        for vert in bm.verts:
            distance = (vert.co - center).length
            if distance < radius:
                factor = cls._get_falloff(distance, radius, falloff) * strength
                
                normal_component = vert.normal.dot(direction)
                push = direction * normal_component * factor
                vert.co += push
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj
    
    @classmethod
    def apply_stroke(
        cls,
        obj: bpy.types.Object,
        stroke: SculptStroke
    ) -> bpy.types.Object:
        """
        Apply a sculpt stroke to the mesh.
        """
        if stroke.brush == SculptBrush.GRAB:
            if stroke.direction:
                return cls.grab(obj, stroke.center, stroke.radius, 
                              stroke.direction, stroke.strength, stroke.falloff)
        elif stroke.brush == SculptBrush.SMOOTH:
            return cls.smooth(obj, stroke.center, stroke.radius,
                            iterations=2, strength=stroke.strength, falloff=stroke.falloff)
        elif stroke.brush == SculptBrush.INFLATE:
            return cls.inflate(obj, stroke.center, stroke.radius,
                             stroke.strength, stroke.falloff)
        elif stroke.brush == SculptBrush.PINCH:
            return cls.pinch(obj, stroke.center, stroke.radius,
                           stroke.strength, stroke.falloff)
        elif stroke.brush == SculptBrush.FLATTEN:
            return cls.flatten(obj, stroke.center, stroke.radius,
                             stroke.direction, stroke.strength, stroke.falloff)
        elif stroke.brush == SculptBrush.CREASE:
            if stroke.direction:
                return cls.crease(obj, stroke.center, stroke.radius,
                                stroke.direction, stroke.strength, stroke.falloff)
        
        return obj
    
    @classmethod
    def smooth_all(
        cls,
        obj: bpy.types.Object,
        iterations: int = 3,
        factor: float = 0.5
    ) -> bpy.types.Object:
        """
        Apply Laplacian smoothing to entire mesh.
        """
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        for _ in range(iterations):
            new_positions = {}
            
            for vert in bm.verts:
                if vert.link_edges:
                    neighbor_avg = Vector((0, 0, 0))
                    count = 0
                    for edge in vert.link_edges:
                        other = edge.other_vert(vert)
                        neighbor_avg += other.co
                        count += 1
                    
                    if count > 0:
                        neighbor_avg /= count
                        new_positions[vert.index] = vert.co.lerp(neighbor_avg, factor)
            
            for idx, pos in new_positions.items():
                bm.verts[idx].co = pos
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return obj


class AnatomyProportions:
    """
    Anatomical proportions system based on classical figure drawing.
    Uses head-height units for consistent scaling.
    """
    
    REALISTIC = {
        "head_count": 7.5,
        "shoulder_width": 2.0,
        "hip_width": 1.5,
        "arm_length": 3.0,
        "leg_length": 4.0,
        "torso_length": 2.5,
        "neck_length": 0.5,
        "hand_length": 0.75,
        "foot_length": 1.0,
        "head_width": 0.75,
        "chest_depth": 0.8,
        "waist_depth": 0.6,
        "hip_depth": 0.7,
    }
    
    STYLIZED = {
        "head_count": 6.0,
        "shoulder_width": 2.2,
        "hip_width": 1.3,
        "arm_length": 2.5,
        "leg_length": 3.5,
        "torso_length": 2.0,
        "neck_length": 0.4,
        "hand_length": 0.6,
        "foot_length": 0.9,
        "head_width": 0.9,
        "chest_depth": 0.9,
        "waist_depth": 0.5,
        "hip_depth": 0.6,
    }
    
    CHIBI = {
        "head_count": 2.5,
        "shoulder_width": 1.5,
        "hip_width": 1.0,
        "arm_length": 1.2,
        "leg_length": 1.0,
        "torso_length": 0.8,
        "neck_length": 0.1,
        "hand_length": 0.4,
        "foot_length": 0.5,
        "head_width": 1.2,
        "chest_depth": 1.0,
        "waist_depth": 0.8,
        "hip_depth": 0.8,
    }
    
    HEROIC = {
        "head_count": 8.5,
        "shoulder_width": 2.5,
        "hip_width": 1.4,
        "arm_length": 3.5,
        "leg_length": 4.5,
        "torso_length": 3.0,
        "neck_length": 0.6,
        "hand_length": 0.8,
        "foot_length": 1.1,
        "head_width": 0.7,
        "chest_depth": 1.0,
        "waist_depth": 0.6,
        "hip_depth": 0.65,
    }
    
    @classmethod
    def get_proportions(cls, style: str) -> Dict[str, float]:
        """Get proportions for a style"""
        styles = {
            "realistic": cls.REALISTIC,
            "stylized": cls.STYLIZED,
            "chibi": cls.CHIBI,
            "sd": cls.CHIBI,
            "heroic": cls.HEROIC,
            "mobile": cls.STYLIZED,
            "minifig": cls.CHIBI,
            "cartoon": cls.STYLIZED,
        }
        return styles.get(style.lower(), cls.STYLIZED)
    
    @classmethod
    def calculate_dimensions(
        cls,
        style: str,
        total_height: float = 2.0,
        gender: str = "male"
    ) -> Dict[str, float]:
        """
        Calculate actual dimensions from proportions.
        
        Returns dictionary with actual measurements for each body part.
        """
        props = cls.get_proportions(style)
        head_height = total_height / props["head_count"]
        
        gender_mod = 1.0 if gender == "male" else 0.92
        shoulder_mod = 1.0 if gender == "male" else 0.85
        hip_mod = 1.0 if gender == "male" else 1.15
        
        return {
            "head_height": head_height,
            "head_width": head_height * props["head_width"],
            "neck_length": head_height * props["neck_length"],
            "shoulder_width": head_height * props["shoulder_width"] * shoulder_mod,
            "chest_depth": head_height * props["chest_depth"] * gender_mod,
            "waist_depth": head_height * props["waist_depth"],
            "hip_width": head_height * props["hip_width"] * hip_mod,
            "hip_depth": head_height * props["hip_depth"],
            "torso_length": head_height * props["torso_length"],
            "arm_length": head_height * props["arm_length"],
            "upper_arm_length": head_height * props["arm_length"] * 0.45,
            "forearm_length": head_height * props["arm_length"] * 0.40,
            "hand_length": head_height * props["hand_length"],
            "leg_length": head_height * props["leg_length"],
            "thigh_length": head_height * props["leg_length"] * 0.48,
            "calf_length": head_height * props["leg_length"] * 0.42,
            "foot_length": head_height * props["foot_length"],
            "total_height": total_height,
        }


class TopologyBuilder:
    """
    Builds game-optimized topology for characters.
    Creates edge loops at joints and maintains quad topology.
    """
    
    @staticmethod
    def create_limb_segment(
        length: float,
        radius_start: float,
        radius_end: float,
        segments: int = 8,
        rings: int = 4,
        joint_loops: bool = True
    ) -> bpy.types.Object:
        """
        Create a limb segment with proper edge loops for deformation.
        """
        bm = bmesh.new()
        
        for ring_idx in range(rings + 1):
            t = ring_idx / rings
            z = t * length
            radius = radius_start + (radius_end - radius_start) * t
            
            for seg_idx in range(segments):
                angle = (seg_idx / segments) * 2 * math.pi
                x = math.cos(angle) * radius
                y = math.sin(angle) * radius
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        for ring_idx in range(rings):
            for seg_idx in range(segments):
                v1 = ring_idx * segments + seg_idx
                v2 = ring_idx * segments + (seg_idx + 1) % segments
                v3 = (ring_idx + 1) * segments + (seg_idx + 1) % segments
                v4 = (ring_idx + 1) * segments + seg_idx
                
                bm.faces.new([bm.verts[v1], bm.verts[v2], bm.verts[v3], bm.verts[v4]])
        
        mesh = bpy.data.meshes.new("Limb")
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new("Limb", mesh)
        bpy.context.collection.objects.link(obj)
        
        if joint_loops:
            SubdivisionOps.add_loop_cuts_by_position(
                obj, 
                axis='Z',
                positions=[length * 0.1, length * 0.9],
                tolerance=length * 0.05
            )
        
        return obj
    
    @staticmethod
    def create_torso(
        dimensions: Dict[str, float],
        segments: int = 12,
        rings: int = 6
    ) -> bpy.types.Object:
        """
        Create torso with anatomical shape and proper edge loops.
        """
        bm = bmesh.new()
        
        chest_w = dimensions.get("shoulder_width", 0.4) / 2
        waist_w = chest_w * 0.7
        hip_w = dimensions.get("hip_width", 0.35) / 2
        
        chest_d = dimensions.get("chest_depth", 0.25) / 2
        waist_d = dimensions.get("waist_depth", 0.2) / 2
        hip_d = dimensions.get("hip_depth", 0.22) / 2
        
        length = dimensions.get("torso_length", 0.6)
        
        shape_curve = [
            (0.0, hip_w, hip_d),
            (0.25, waist_w * 0.95, waist_d),
            (0.5, waist_w, waist_d),
            (0.75, chest_w * 0.9, chest_d * 0.9),
            (1.0, chest_w, chest_d),
        ]
        
        for ring_idx in range(rings + 1):
            t = ring_idx / rings
            z = t * length
            
            for i, (ct, cw, cd) in enumerate(shape_curve[:-1]):
                ct_next, cw_next, cd_next = shape_curve[i + 1]
                if ct <= t <= ct_next:
                    local_t = (t - ct) / (ct_next - ct)
                    width = cw + (cw_next - cw) * local_t
                    depth = cd + (cd_next - cd) * local_t
                    break
            else:
                width, depth = chest_w, chest_d
            
            for seg_idx in range(segments):
                angle = (seg_idx / segments) * 2 * math.pi
                x = math.cos(angle) * width
                y = math.sin(angle) * depth
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        for ring_idx in range(rings):
            for seg_idx in range(segments):
                v1 = ring_idx * segments + seg_idx
                v2 = ring_idx * segments + (seg_idx + 1) % segments
                v3 = (ring_idx + 1) * segments + (seg_idx + 1) % segments
                v4 = (ring_idx + 1) * segments + seg_idx
                
                bm.faces.new([bm.verts[v1], bm.verts[v2], bm.verts[v3], bm.verts[v4]])
        
        mesh = bpy.data.meshes.new("Torso")
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new("Torso", mesh)
        bpy.context.collection.objects.link(obj)
        
        return obj
    
    @staticmethod
    def create_head(
        dimensions: Dict[str, float],
        segments: int = 16,
        rings: int = 8
    ) -> bpy.types.Object:
        """
        Create head with basic skull shape.
        """
        head_height = dimensions.get("head_height", 0.25)
        head_width = dimensions.get("head_width", 0.18)
        
        bm = bmesh.new()
        
        head_profile = [
            (0.0, 0.3),
            (0.15, 0.7),
            (0.3, 0.95),
            (0.5, 1.0),
            (0.7, 0.95),
            (0.85, 0.75),
            (1.0, 0.4),
        ]
        
        for ring_idx in range(rings + 1):
            t = ring_idx / rings
            z = t * head_height
            
            radius_mult = 0.3
            for i, (pt, pr) in enumerate(head_profile[:-1]):
                pt_next, pr_next = head_profile[i + 1]
                if pt <= t <= pt_next:
                    local_t = (t - pt) / (pt_next - pt)
                    radius_mult = pr + (pr_next - pr) * local_t
                    break
            
            radius = head_width / 2 * radius_mult
            
            for seg_idx in range(segments):
                angle = (seg_idx / segments) * 2 * math.pi
                
                front_factor = 1.0 + 0.1 * math.cos(angle) if t > 0.4 else 1.0
                
                x = math.cos(angle) * radius * front_factor
                y = math.sin(angle) * radius
                bm.verts.new((x, y, z))
        
        bm.verts.ensure_lookup_table()
        
        for ring_idx in range(rings):
            for seg_idx in range(segments):
                v1 = ring_idx * segments + seg_idx
                v2 = ring_idx * segments + (seg_idx + 1) % segments
                v3 = (ring_idx + 1) * segments + (seg_idx + 1) % segments
                v4 = (ring_idx + 1) * segments + seg_idx
                
                bm.faces.new([bm.verts[v1], bm.verts[v2], bm.verts[v3], bm.verts[v4]])
        
        top_center = bm.verts.new((0, 0, head_height))
        bm.verts.ensure_lookup_table()
        
        top_ring_start = rings * segments
        for seg_idx in range(segments):
            v1 = top_ring_start + seg_idx
            v2 = top_ring_start + (seg_idx + 1) % segments
            bm.faces.new([bm.verts[v1], bm.verts[v2], top_center])
        
        mesh = bpy.data.meshes.new("Head")
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new("Head", mesh)
        bpy.context.collection.objects.link(obj)
        
        return obj


class CharacterAssembler:
    """
    Assembles complete character from body parts with proper topology.
    """
    
    @classmethod
    def assemble_humanoid(
        cls,
        style: str = "stylized",
        gender: str = "male",
        total_height: float = 2.0,
        apply_subdivision: bool = False,
        subdivision_level: int = 1
    ) -> Dict[str, bpy.types.Object]:
        """
        Assemble a complete humanoid character.
        
        Returns dictionary of body part objects.
        """
        dims = AnatomyProportions.calculate_dimensions(style, total_height, gender)
        
        parts = {}
        
        parts["head"] = TopologyBuilder.create_head(dims)
        head_z = dims["torso_length"] + dims["neck_length"]
        parts["head"].location.z = head_z
        
        parts["torso"] = TopologyBuilder.create_torso(dims)
        
        arm_radius = dims["shoulder_width"] * 0.08
        parts["upper_arm_l"] = TopologyBuilder.create_limb_segment(
            dims["upper_arm_length"], arm_radius, arm_radius * 0.8
        )
        parts["upper_arm_l"].location = (
            dims["shoulder_width"] / 2,
            0,
            dims["torso_length"] * 0.85
        )
        parts["upper_arm_l"].rotation_euler = (0, math.radians(90), 0)
        
        parts["upper_arm_r"] = TopologyBuilder.create_limb_segment(
            dims["upper_arm_length"], arm_radius, arm_radius * 0.8
        )
        parts["upper_arm_r"].location = (
            -dims["shoulder_width"] / 2,
            0,
            dims["torso_length"] * 0.85
        )
        parts["upper_arm_r"].rotation_euler = (0, math.radians(-90), 0)
        
        leg_radius = dims["hip_width"] * 0.15
        parts["thigh_l"] = TopologyBuilder.create_limb_segment(
            dims["thigh_length"], leg_radius, leg_radius * 0.7
        )
        parts["thigh_l"].location = (dims["hip_width"] / 4, 0, 0)
        parts["thigh_l"].rotation_euler = (math.radians(180), 0, 0)
        
        parts["thigh_r"] = TopologyBuilder.create_limb_segment(
            dims["thigh_length"], leg_radius, leg_radius * 0.7
        )
        parts["thigh_r"].location = (-dims["hip_width"] / 4, 0, 0)
        parts["thigh_r"].rotation_euler = (math.radians(180), 0, 0)
        
        if apply_subdivision:
            for name, obj in parts.items():
                SubdivisionOps.apply_subdivision(obj, levels=subdivision_level)
                SculptOps.smooth_all(obj, iterations=1, factor=0.3)
        
        return parts
