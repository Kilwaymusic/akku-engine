"""
Akku SDK v4.0 Procedural - Procedural Humanoid Mesh Generator

Generates low-poly humanoid base meshes from scratch using bmesh primitives.
Includes Hard-Surface Kitbash and Vertex Color support.
"""

import bpy
import bmesh
import math
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
from mathutils import Vector, Matrix

from .core import AkkuLogger
from .atomic_ops import (
    AtomicOps,
    VertexColorOps,
    ColorPalette,
    HardSurfaceKitbash,
    CharacterPainter,
)
from .sculpt_ops import (
    SubdivisionOps,
    SculptOps,
    AnatomyProportions,
)


@dataclass
class ProportionPreset:
    """Character proportion settings"""
    total_height: float = 1.8
    head_ratio: float = 0.125
    torso_ratio: float = 0.30
    leg_ratio: float = 0.50
    arm_length_ratio: float = 0.38
    shoulder_width_ratio: float = 0.25
    hip_width_ratio: float = 0.15
    head_scale: float = 1.0
    limb_thickness: float = 0.04
    torso_thickness: float = 0.12
    base_color: Tuple[float, float, float] = (0.6, 0.6, 0.65)  # Default gray-blue


class StyleProportions:
    """Proportion presets for different character styles"""
    
    PRESETS: Dict[str, ProportionPreset] = {
        "realistic": ProportionPreset(
            total_height=1.8,
            head_ratio=0.125,
            torso_ratio=0.30,
            leg_ratio=0.50,
            arm_length_ratio=0.38,
            shoulder_width_ratio=0.25,
            hip_width_ratio=0.15,
            head_scale=1.0,
            limb_thickness=0.04,
            torso_thickness=0.12
        ),
        "stylized": ProportionPreset(
            total_height=1.6,
            head_ratio=0.16,
            torso_ratio=0.28,
            leg_ratio=0.45,
            arm_length_ratio=0.35,
            shoulder_width_ratio=0.28,
            hip_width_ratio=0.14,
            head_scale=1.2,
            limb_thickness=0.045,
            torso_thickness=0.13
        ),
        "chibi": ProportionPreset(
            total_height=0.8,
            head_ratio=0.40,
            torso_ratio=0.25,
            leg_ratio=0.28,
            arm_length_ratio=0.22,
            shoulder_width_ratio=0.30,
            hip_width_ratio=0.20,
            head_scale=2.0,
            limb_thickness=0.06,
            torso_thickness=0.15
        ),
        "sd": ProportionPreset(
            total_height=1.0,
            head_ratio=0.32,
            torso_ratio=0.26,
            leg_ratio=0.35,
            arm_length_ratio=0.28,
            shoulder_width_ratio=0.28,
            hip_width_ratio=0.18,
            head_scale=1.6,
            limb_thickness=0.055,
            torso_thickness=0.14
        ),
        "mobile": ProportionPreset(
            total_height=1.2,
            head_ratio=0.22,
            torso_ratio=0.28,
            leg_ratio=0.40,
            arm_length_ratio=0.30,
            shoulder_width_ratio=0.26,
            hip_width_ratio=0.16,
            head_scale=1.3,
            limb_thickness=0.05,
            torso_thickness=0.13
        ),
        "minifig": ProportionPreset(
            total_height=0.6,
            head_ratio=0.35,
            torso_ratio=0.30,
            leg_ratio=0.30,
            arm_length_ratio=0.25,
            shoulder_width_ratio=0.35,
            hip_width_ratio=0.25,
            head_scale=1.5,
            limb_thickness=0.08,
            torso_thickness=0.18
        ),
        "cartoon": ProportionPreset(
            total_height=1.4,
            head_ratio=0.20,
            torso_ratio=0.28,
            leg_ratio=0.42,
            arm_length_ratio=0.32,
            shoulder_width_ratio=0.30,
            hip_width_ratio=0.16,
            head_scale=1.4,
            limb_thickness=0.05,
            torso_thickness=0.14
        ),
    }
    
    @classmethod
    def get_preset(cls, style: str) -> ProportionPreset:
        """Get proportion preset by style name"""
        return cls.PRESETS.get(style.lower(), cls.PRESETS["stylized"])


@dataclass
class PolyLevelSettings:
    """Polygon complexity settings"""
    head_segments: int = 8
    torso_segments: int = 6
    limb_segments: int = 4
    use_subdivision: bool = False
    subdivision_level: int = 0
    target_tris: int = 1500


class PolyLevelPresets:
    """Polygon level configurations"""
    
    PRESETS: Dict[str, PolyLevelSettings] = {
        "ultra_low": PolyLevelSettings(
            head_segments=4,
            torso_segments=4,
            limb_segments=3,
            use_subdivision=False,
            subdivision_level=0,
            target_tris=300
        ),
        "low": PolyLevelSettings(
            head_segments=10,
            torso_segments=8,
            limb_segments=6,
            use_subdivision=False,
            subdivision_level=0,
            target_tris=1200
        ),
        "medium": PolyLevelSettings(
            head_segments=16,
            torso_segments=12,
            limb_segments=8,
            use_subdivision=False,
            subdivision_level=0,
            target_tris=2500
        ),
        "high": PolyLevelSettings(
            head_segments=24,
            torso_segments=16,
            limb_segments=12,
            use_subdivision=True,
            subdivision_level=1,
            target_tris=5000
        ),
    }
    
    @classmethod
    def get_preset(cls, poly_level: str) -> PolyLevelSettings:
        """Get poly level settings"""
        return cls.PRESETS.get(poly_level.lower(), cls.PRESETS["medium"])


class ProceduralHumanoid:
    """
    Procedural Humanoid Mesh Generator
    
    Creates low-poly humanoid characters from scratch using bmesh primitives.
    No external dependencies (Mixamo, FBX) required.
    """
    
    @classmethod
    def create_box_limb(
        cls,
        bm: bmesh.types.BMesh,
        start_pos: Vector,
        end_pos: Vector,
        width: float,
        depth: float,
        segments: int = 4
    ) -> List[bmesh.types.BMVert]:
        """Create a box-shaped limb segment"""
        direction = (end_pos - start_pos).normalized()
        length = (end_pos - start_pos).length
        
        up = Vector((0, 0, 1))
        if abs(direction.dot(up)) > 0.99:
            up = Vector((0, 1, 0))
        
        side = direction.cross(up).normalized()
        forward = side.cross(direction).normalized()
        
        verts = []
        half_w = width / 2
        half_d = depth / 2
        
        for i in range(segments + 1):
            t = i / segments
            pos = start_pos.lerp(end_pos, t)
            
            taper = 1.0 - (t * 0.3)
            
            corners = [
                pos + side * half_w * taper + forward * half_d * taper,
                pos - side * half_w * taper + forward * half_d * taper,
                pos - side * half_w * taper - forward * half_d * taper,
                pos + side * half_w * taper - forward * half_d * taper,
            ]
            
            for corner in corners:
                verts.append(bm.verts.new(corner))
        
        bm.verts.ensure_lookup_table()
        
        for i in range(segments):
            base = i * 4
            for j in range(4):
                v1 = verts[base + j]
                v2 = verts[base + (j + 1) % 4]
                v3 = verts[base + 4 + (j + 1) % 4]
                v4 = verts[base + 4 + j]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    pass
        
        top_verts = verts[-4:]
        try:
            bm.faces.new(top_verts)
        except ValueError:
            pass
        
        bottom_verts = verts[:4]
        try:
            bm.faces.new(bottom_verts[::-1])
        except ValueError:
            pass
        
        return verts
    
    @classmethod
    def create_cylinder_limb(
        cls,
        bm: bmesh.types.BMesh,
        start_pos: Vector,
        end_pos: Vector,
        radius: float,
        segments: int = 6,
        height_segments: int = 4
    ) -> List[bmesh.types.BMVert]:
        """Create a cylindrical limb segment"""
        direction = (end_pos - start_pos).normalized()
        length = (end_pos - start_pos).length
        
        up = Vector((0, 0, 1))
        if abs(direction.dot(up)) > 0.99:
            up = Vector((0, 1, 0))
        
        side = direction.cross(up).normalized()
        forward = side.cross(direction).normalized()
        
        verts = []
        
        for h in range(height_segments + 1):
            t = h / height_segments
            pos = start_pos.lerp(end_pos, t)
            
            taper = 1.0 - (t * 0.25)
            
            for s in range(segments):
                angle = (s / segments) * 2 * math.pi
                offset = (side * math.cos(angle) + forward * math.sin(angle)) * radius * taper
                verts.append(bm.verts.new(pos + offset))
        
        bm.verts.ensure_lookup_table()
        
        for h in range(height_segments):
            for s in range(segments):
                v1 = verts[h * segments + s]
                v2 = verts[h * segments + (s + 1) % segments]
                v3 = verts[(h + 1) * segments + (s + 1) % segments]
                v4 = verts[(h + 1) * segments + s]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    pass
        
        center_top = bm.verts.new(end_pos)
        for s in range(segments):
            v1 = verts[height_segments * segments + s]
            v2 = verts[height_segments * segments + (s + 1) % segments]
            try:
                bm.faces.new([v1, v2, center_top])
            except ValueError:
                pass
        
        center_bottom = bm.verts.new(start_pos)
        for s in range(segments):
            v1 = verts[(s + 1) % segments]
            v2 = verts[s]
            try:
                bm.faces.new([v1, v2, center_bottom])
            except ValueError:
                pass
        
        return verts
    
    @classmethod
    def create_sphere_head(
        cls,
        bm: bmesh.types.BMesh,
        center: Vector,
        radius: float,
        segments: int = 8,
        rings: int = 6
    ) -> List[bmesh.types.BMVert]:
        """Create a spherical head shape"""
        verts = []
        
        top = bm.verts.new(center + Vector((0, 0, radius)))
        verts.append(top)
        
        for ring in range(1, rings):
            phi = (ring / rings) * math.pi
            z = radius * math.cos(phi)
            ring_radius = radius * math.sin(phi)
            
            for seg in range(segments):
                theta = (seg / segments) * 2 * math.pi
                x = ring_radius * math.cos(theta)
                y = ring_radius * math.sin(theta)
                verts.append(bm.verts.new(center + Vector((x, y, z))))
        
        bottom = bm.verts.new(center + Vector((0, 0, -radius)))
        verts.append(bottom)
        
        bm.verts.ensure_lookup_table()
        
        for seg in range(segments):
            v1 = verts[0]
            v2 = verts[1 + seg]
            v3 = verts[1 + (seg + 1) % segments]
            try:
                bm.faces.new([v1, v3, v2])
            except ValueError:
                pass
        
        for ring in range(rings - 2):
            for seg in range(segments):
                base = 1 + ring * segments
                v1 = verts[base + seg]
                v2 = verts[base + (seg + 1) % segments]
                v3 = verts[base + segments + (seg + 1) % segments]
                v4 = verts[base + segments + seg]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    pass
        
        bottom_ring_start = 1 + (rings - 2) * segments
        for seg in range(segments):
            v1 = verts[bottom_ring_start + seg]
            v2 = verts[bottom_ring_start + (seg + 1) % segments]
            v3 = verts[-1]
            try:
                bm.faces.new([v1, v2, v3])
            except ValueError:
                pass
        
        return verts
    
    @classmethod
    def create_torso(
        cls,
        bm: bmesh.types.BMesh,
        base_pos: Vector,
        height: float,
        shoulder_width: float,
        hip_width: float,
        depth: float,
        segments: int = 6
    ) -> Dict[str, Vector]:
        """Create torso and return joint positions"""
        verts = []
        
        for i in range(segments + 1):
            t = i / segments
            y = base_pos.z + height * t
            
            width = hip_width + (shoulder_width - hip_width) * t
            
            half_w = width / 2
            half_d = depth / 2
            
            chest_bulge = math.sin(t * math.pi) * 0.02
            back_curve = -math.sin(t * math.pi) * 0.01
            
            corners = [
                Vector((half_w, depth / 2 + chest_bulge, y)),
                Vector((-half_w, depth / 2 + chest_bulge, y)),
                Vector((-half_w, -depth / 2 + back_curve, y)),
                Vector((half_w, -depth / 2 + back_curve, y)),
            ]
            
            for corner in corners:
                verts.append(bm.verts.new(corner))
        
        bm.verts.ensure_lookup_table()
        
        for i in range(segments):
            base = i * 4
            for j in range(4):
                v1 = verts[base + j]
                v2 = verts[base + (j + 1) % 4]
                v3 = verts[base + 4 + (j + 1) % 4]
                v4 = verts[base + 4 + j]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    pass
        
        top_verts = verts[-4:]
        try:
            bm.faces.new(top_verts)
        except ValueError:
            pass
        
        bottom_verts = verts[:4]
        try:
            bm.faces.new(bottom_verts[::-1])
        except ValueError:
            pass
        
        return {
            "hip_center": base_pos.copy(),
            "hip_left": Vector((-hip_width / 2, 0, base_pos.z)),
            "hip_right": Vector((hip_width / 2, 0, base_pos.z)),
            "shoulder_center": Vector((0, 0, base_pos.z + height)),
            "shoulder_left": Vector((-shoulder_width / 2, 0, base_pos.z + height)),
            "shoulder_right": Vector((shoulder_width / 2, 0, base_pos.z + height)),
            "spine_mid": Vector((0, 0, base_pos.z + height * 0.5)),
        }
    
    @classmethod
    def generate_unified_mesh(
        cls,
        style: str = "stylized",
        poly_level: str = "medium",
        gender: str = "male",
        base_color: Tuple[float, float, float] = None
    ) -> bpy.types.Object:
        """
        Generate a unified humanoid mesh using Extrude-First approach.
        
        Instead of creating separate primitives, starts with a torso box
        and extrudes all limbs from it, creating a single connected mesh.
        
        Args:
            style: Character style preset
            poly_level: Polygon complexity
            gender: Gender for proportion adjustments
            base_color: RGB color tuple (0.0-1.0) for character material
            
        Returns:
            Generated mesh object (single connected mesh)
        """
        props = StyleProportions.get_preset(style)
        poly_settings = PolyLevelPresets.get_preset(poly_level)
        
        # Apply base color if provided
        if base_color and isinstance(base_color, (list, tuple)) and len(base_color) >= 3:
            props.base_color = tuple(base_color[:3])
        
        if gender == "female":
            props.shoulder_width_ratio *= 0.9
            props.hip_width_ratio *= 1.1
            props.torso_thickness *= 0.9
        
        total_height = props.total_height
        head_ratio = props.head_ratio
        torso_ratio = props.torso_ratio
        leg_ratio = props.leg_ratio
        arm_ratio = props.arm_length_ratio
        shoulder_width = total_height * props.shoulder_width_ratio
        hip_width = total_height * props.hip_width_ratio
        limb_thickness = props.limb_thickness * total_height
        torso_depth = props.torso_thickness * total_height
        
        # Calculate heights
        leg_height = total_height * leg_ratio
        torso_height = total_height * torso_ratio
        head_height = total_height * head_ratio
        arm_length = total_height * arm_ratio
        
        AkkuLogger.info("Generating unified mesh humanoid (Extrude-First)", {
            "style": style,
            "poly_level": poly_level,
            "gender": gender,
            "total_height": total_height,
            "method": "extrude-first"
        })
        
        mesh = bpy.data.meshes.new("UnifiedHumanoid")
        obj = bpy.data.objects.new("Character", mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        # === PHASE 1: Create base torso with waist definition ===
        torso_base_z = leg_height
        waist_z = leg_height + torso_height * 0.35  # Waist at 35% of torso
        chest_z = leg_height + torso_height * 0.7   # Chest at 70% of torso
        torso_top_z = leg_height + torso_height
        
        hw = shoulder_width / 2 * 0.85  # half width at shoulders (reduced from 1.0)
        hd = torso_depth / 2     # half depth
        hip_hw = hip_width / 2 * 0.9  # Slightly narrower hips
        waist_hw = min(hip_hw, hw) * 0.8  # Waist is 80% of narrower width (less extreme)
        chest_hw = hw * 0.92  # Chest narrower than shoulders
        
        # Torso with 4 levels: hips, waist, chest, shoulders
        v_hip = [
            bm.verts.new(Vector((-hip_hw, -hd * 0.85, torso_base_z))),
            bm.verts.new(Vector((hip_hw, -hd * 0.85, torso_base_z))),
            bm.verts.new(Vector((hip_hw, hd * 0.85, torso_base_z))),
            bm.verts.new(Vector((-hip_hw, hd * 0.85, torso_base_z))),
        ]
        v_waist = [
            bm.verts.new(Vector((-waist_hw, -hd * 0.75, waist_z))),
            bm.verts.new(Vector((waist_hw, -hd * 0.75, waist_z))),
            bm.verts.new(Vector((waist_hw, hd * 0.75, waist_z))),
            bm.verts.new(Vector((-waist_hw, hd * 0.75, waist_z))),
        ]
        v_chest = [
            bm.verts.new(Vector((-chest_hw, -hd * 0.82, chest_z))),
            bm.verts.new(Vector((chest_hw, -hd * 0.82, chest_z))),
            bm.verts.new(Vector((chest_hw, hd * 0.82, chest_z))),
            bm.verts.new(Vector((-chest_hw, hd * 0.82, chest_z))),
        ]
        v_top = [
            bm.verts.new(Vector((-hw, -hd * 0.78, torso_top_z))),
            bm.verts.new(Vector((hw, -hd * 0.78, torso_top_z))),
            bm.verts.new(Vector((hw, hd * 0.78, torso_top_z))),
            bm.verts.new(Vector((-hw, hd * 0.78, torso_top_z))),
        ]
        
        # Alias for backwards compatibility
        v_bot = v_hip
        
        bm.verts.ensure_lookup_table()
        
        # Create faces - connect all 4 levels
        # Vertex layout: 0=front-left, 1=front-right, 2=back-right, 3=back-left
        # Face winding: CCW from outside = outward normal
        
        # Bottom face (hip) - normal pointing down (-Z)
        f_bottom = bm.faces.new([v_hip[0], v_hip[3], v_hip[2], v_hip[1]])
        
        # Helper function to create ring faces between two levels with consistent winding
        def create_ring_faces(lower, upper):
            """Create 4 quad faces connecting two vertex rings with outward normals"""
            faces = []
            # Front face (normal -Y): CCW from front = lower[0], upper[0], upper[1], lower[1]
            faces.append(bm.faces.new([lower[0], upper[0], upper[1], lower[1]]))
            # Right face (normal +X): CCW from right = lower[1], upper[1], upper[2], lower[2]
            faces.append(bm.faces.new([lower[1], upper[1], upper[2], lower[2]]))
            # Back face (normal +Y): CCW from back = lower[2], upper[2], upper[3], lower[3]
            faces.append(bm.faces.new([lower[2], upper[2], upper[3], lower[3]]))
            # Left face (normal -X): CCW from left = lower[3], upper[3], upper[0], lower[0]
            faces.append(bm.faces.new([lower[3], upper[3], upper[0], lower[0]]))
            return faces
        
        # Hip to waist
        create_ring_faces(v_hip, v_waist)
        
        # Waist to chest
        create_ring_faces(v_waist, v_chest)
        
        # Chest to shoulders - keep references for arm extrusion
        shoulder_faces = create_ring_faces(v_chest, v_top)
        f_right = shoulder_faces[1]  # Right face (normal +X)
        f_left = shoulder_faces[3]   # Left face (normal -X)
        
        # Top face (shoulders) - normal pointing up (+Z)
        f_top = bm.faces.new([v_top[0], v_top[1], v_top[2], v_top[3]])
        
        bm.faces.ensure_lookup_table()
        
        # === PHASE 2: Extrude neck and head from top face ===
        neck_height = head_height * 0.25
        head_size = head_height * props.head_scale * 0.75
        
        # Extrude neck
        neck_result = bmesh.ops.extrude_face_region(bm, geom=[f_top])
        neck_verts = [v for v in neck_result['geom'] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=neck_verts, vec=Vector((0, 0, neck_height)))
        
        # Scale neck inward (thinner neck)
        neck_center = sum((v.co for v in neck_verts), Vector()) / len(neck_verts)
        for v in neck_verts:
            direction = v.co - neck_center
            direction.x *= 0.35
            direction.y *= 0.35
            v.co = neck_center + direction
        
        bm.faces.ensure_lookup_table()
        
        # Find the new top face after neck extrusion
        neck_top_face = None
        for f in bm.faces:
            if f.is_valid and all(v in neck_verts for v in f.verts):
                center = f.calc_center_median()
                if center.z > torso_top_z + neck_height * 0.5:
                    neck_top_face = f
                    break
        
        # Extrude head from neck (better proportions)
        if neck_top_face:
            head_result = bmesh.ops.extrude_face_region(bm, geom=[neck_top_face])
            head_verts = [v for v in head_result['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=head_verts, vec=Vector((0, 0, head_size)))
            
            # Scale head for proper shape
            head_center = sum((v.co for v in head_verts), Vector()) / len(head_verts)
            head_scale_x = props.head_scale * 1.6  # Wider
            head_scale_y = props.head_scale * 1.4  # Slightly less deep
            for v in head_verts:
                direction = v.co - head_center
                direction.x *= head_scale_x
                direction.y *= head_scale_y
                v.co = head_center + direction
            
            # Move front vertices forward for face protrusion (chin/nose area)
            for v in head_verts:
                if v.co.y < head_center.y:  # Front vertices
                    v.co.y -= head_size * 0.15  # Slight forward protrusion
        
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # === PHASE 3: Extrude arms from side faces ===
        upper_arm_len = arm_length * 0.5
        lower_arm_len = arm_length * 0.4
        hand_len = arm_length * 0.1
        arm_thick = limb_thickness * 0.8  # Slightly thicker arms
        
        # Re-find side faces at shoulder level (faces may have been invalidated)
        # Look for faces with X-facing normals at the shoulder Z level
        shoulder_z = torso_top_z - torso_height * 0.1  # Just below shoulder top
        new_f_left = None
        new_f_right = None
        
        for f in bm.faces:
            if not f.is_valid:
                continue
            center = f.calc_center_median()
            # Check if face is at shoulder level
            if abs(center.z - shoulder_z) < torso_height * 0.3:
                normal = f.normal
                # Left face has normal pointing -X
                if normal.x < -0.5 and new_f_left is None:
                    new_f_left = f
                # Right face has normal pointing +X  
                elif normal.x > 0.5 and new_f_right is None:
                    new_f_right = f
        
        for side_face, direction, side in [(new_f_left, Vector((-1, 0, 0)), "left"), 
                                            (new_f_right, Vector((1, 0, 0)), "right")]:
            if side_face is None or not side_face.is_valid:
                continue
                
            direction = direction.normalized()
            
            # Extrude shoulder (small bump)
            shoulder_result = bmesh.ops.extrude_face_region(bm, geom=[side_face])
            shoulder_verts = [v for v in shoulder_result['geom'] if isinstance(v, bmesh.types.BMVert)]
            
            # Move shoulder outward (smaller distance)
            bmesh.ops.translate(bm, verts=shoulder_verts, vec=direction * (shoulder_width * 0.08))
            
            # Scale shoulder for arm attachment
            shoulder_center = sum((v.co for v in shoulder_verts), Vector()) / len(shoulder_verts)
            for v in shoulder_verts:
                diff = v.co - shoulder_center
                diff *= 0.45  # Moderate shoulder size
                v.co = shoulder_center + diff
            
            bm.faces.ensure_lookup_table()
            
            # Find shoulder end face (facing outward)
            shoulder_end_face = None
            for f in bm.faces:
                if f.is_valid and all(v in shoulder_verts for v in f.verts):
                    normal = f.normal
                    if (side == "left" and normal.x < -0.3) or (side == "right" and normal.x > 0.3):
                        shoulder_end_face = f
                        break
            
            if not shoulder_end_face:
                continue
            
            # Extrude upper arm (more downward angle)
            upper_result = bmesh.ops.extrude_face_region(bm, geom=[shoulder_end_face])
            upper_verts = [v for v in upper_result['geom'] if isinstance(v, bmesh.types.BMVert)]
            # More downward angle: X outward, Z down significantly
            arm_dir = Vector((-1 if side == "left" else 1, 0.05, -0.6)).normalized()
            bmesh.ops.translate(bm, verts=upper_verts, vec=arm_dir * upper_arm_len)
            
            # Taper upper arm
            upper_center = sum((v.co for v in upper_verts), Vector()) / len(upper_verts)
            for v in upper_verts:
                diff = v.co - upper_center
                diff *= 0.75  # Moderate taper
                v.co = upper_center + diff
            
            bm.faces.ensure_lookup_table()
            
            # Find upper arm end face
            upper_end_face = None
            for f in bm.faces:
                if f.is_valid and all(v in upper_verts for v in f.verts):
                    upper_end_face = f
                    break
            
            if not upper_end_face:
                continue
            
            # Extrude lower arm (continues downward)
            lower_result = bmesh.ops.extrude_face_region(bm, geom=[upper_end_face])
            lower_verts = [v for v in lower_result['geom'] if isinstance(v, bmesh.types.BMVert)]
            # Slightly forward and down
            lower_dir = Vector((-1 if side == "left" else 1, 0.1, -0.5)).normalized()
            bmesh.ops.translate(bm, verts=lower_verts, vec=lower_dir * lower_arm_len)
            
            # Taper lower arm (thinner at wrist)
            lower_center = sum((v.co for v in lower_verts), Vector()) / len(lower_verts)
            for v in lower_verts:
                diff = v.co - lower_center
                diff *= 0.65  # Moderate taper at wrist
                v.co = lower_center + diff
            
            bm.faces.ensure_lookup_table()
            
            # Find lower arm end face and extrude hand
            lower_end_face = None
            for f in bm.faces:
                if f.is_valid and all(v in lower_verts for v in f.verts):
                    lower_end_face = f
                    break
            
            if lower_end_face:
                hand_result = bmesh.ops.extrude_face_region(bm, geom=[lower_end_face])
                hand_verts = [v for v in hand_result['geom'] if isinstance(v, bmesh.types.BMVert)]
                # Hand goes slightly forward
                hand_dir = Vector((-1 if side == "left" else 1, 0.3, -0.2)).normalized()
                bmesh.ops.translate(bm, verts=hand_verts, vec=hand_dir * hand_len)
        
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # === PHASE 4: Extrude legs from bottom face (TRUE EXTRUDE-FIRST) ===
        # CRITICAL: Must extrude from torso bottom face, not create separate faces
        upper_leg_len = leg_height * 0.5
        lower_leg_len = leg_height * 0.4
        foot_len = leg_height * 0.1
        
        # Split the bottom face into left and right halves for legs
        if f_bottom.is_valid:
            bottom_verts = list(f_bottom.verts)
            
            # Delete the original bottom face - we'll split it into two leg faces
            bm.faces.remove(f_bottom)
            bm.verts.ensure_lookup_table()
            
            # Sort vertices by X and Y to identify corners
            # bottom_verts should be: 4 corners at (+-hip_hw, +-hd, torso_base_z)
            left_verts = sorted([v for v in bottom_verts if v.co.x < 0], key=lambda v: v.co.y)
            right_verts = sorted([v for v in bottom_verts if v.co.x >= 0], key=lambda v: v.co.y)
            
            # Add center vertices to create crotch/pelvis area
            center_front = bm.verts.new(Vector((0, -hd, torso_base_z)))
            center_back = bm.verts.new(Vector((0, hd, torso_base_z)))
            
            bm.verts.ensure_lookup_table()
            
            # Create left and right leg base faces (sharing center vertices)
            leg_faces = []
            try:
                # Left leg face: left_front, center_front, center_back, left_back
                left_leg_face = bm.faces.new([left_verts[0], center_front, center_back, left_verts[1]])
                leg_faces.append(("left", left_leg_face))
            except ValueError:
                pass
            
            try:
                # Right leg face: center_front, right_front, right_back, center_back
                right_leg_face = bm.faces.new([center_front, right_verts[0], right_verts[1], center_back])
                leg_faces.append(("right", right_leg_face))
            except ValueError:
                pass
            
            bm.faces.ensure_lookup_table()
            
            # Extrude each leg face
            for side, leg_face in leg_faces:
                if not leg_face or not leg_face.is_valid:
                    continue
                
                # Extrude upper leg downward
                upper_leg_result = bmesh.ops.extrude_face_region(bm, geom=[leg_face])
                upper_leg_verts = [v for v in upper_leg_result['geom'] if isinstance(v, bmesh.types.BMVert)]
                bmesh.ops.translate(bm, verts=upper_leg_verts, vec=Vector((0, 0, -upper_leg_len)))
                
                # Scale down for leg taper
                leg_center = sum((v.co for v in upper_leg_verts), Vector()) / len(upper_leg_verts)
                for v in upper_leg_verts:
                    diff = v.co - leg_center
                    diff.x *= 0.7
                    diff.y *= 0.7
                    v.co = leg_center + diff
                
                bm.faces.ensure_lookup_table()
                
                # Find upper leg end face (the one with downward normal)
                upper_leg_end = None
                for f in bm.faces:
                    if f.is_valid and all(v in upper_leg_verts for v in f.verts):
                        if f.normal.z < -0.5:
                            upper_leg_end = f
                            break
                
                if not upper_leg_end:
                    continue
                
                # Extrude lower leg
                lower_leg_result = bmesh.ops.extrude_face_region(bm, geom=[upper_leg_end])
                lower_leg_verts = [v for v in lower_leg_result['geom'] if isinstance(v, bmesh.types.BMVert)]
                bmesh.ops.translate(bm, verts=lower_leg_verts, vec=Vector((0, 0, -lower_leg_len)))
                
                # Taper lower leg
                lower_leg_center = sum((v.co for v in lower_leg_verts), Vector()) / len(lower_leg_verts)
                for v in lower_leg_verts:
                    diff = v.co - lower_leg_center
                    diff.x *= 0.8
                    diff.y *= 0.8
                    v.co = lower_leg_center + diff
                
                bm.faces.ensure_lookup_table()
                
                # Find lower leg end face
                lower_leg_end = None
                for f in bm.faces:
                    if f.is_valid and all(v in lower_leg_verts for v in f.verts):
                        if f.normal.z < -0.5:
                            lower_leg_end = f
                            break
                
                if not lower_leg_end:
                    continue
                
                # Extrude foot
                foot_result = bmesh.ops.extrude_face_region(bm, geom=[lower_leg_end])
                foot_verts = [v for v in foot_result['geom'] if isinstance(v, bmesh.types.BMVert)]
                # Foot goes forward and slightly down
                bmesh.ops.translate(bm, verts=foot_verts, vec=Vector((0, foot_len * 0.8, -foot_len * 0.3)))
                
                # Scale foot to be flatter and longer
                foot_center = sum((v.co for v in foot_verts), Vector()) / len(foot_verts)
                for v in foot_verts:
                    diff = v.co - foot_center
                    diff.x *= 1.2  # Wider
                    diff.y *= 1.5  # Longer
                    diff.z *= 0.5  # Flatter
                    v.co = foot_center + diff
        
        # === PHASE 5: Clean up mesh ===
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        # === PHASE 6: Apply material/shader ===
        cls._apply_stylized_material(obj, props)
        
        from .tools import MeshAnalyzer
        stats = MeshAnalyzer.get_stats(obj)
        AkkuLogger.info("Unified mesh humanoid generated", {
            "vertices": stats.vertex_count,
            "faces": stats.face_count,
            "triangles": stats.triangle_count,
            "style": style,
            "method": "extrude-first"
        })
        
        return obj
    
    @classmethod
    def _apply_stylized_material(cls, obj: bpy.types.Object, props: ProportionPreset) -> None:
        """Apply stylized low-poly shader to the character.
        
        Creates a material with:
        - Base color from props.base_color
        - Slight metallic for stylized look
        - Edge highlighting via Fresnel
        - Flat shading for faceted low-poly appearance
        """
        # Get color from props or use default
        base_color = props.base_color if hasattr(props, 'base_color') else (0.6, 0.6, 0.65)
        
        # Create material
        mat_name = f"AkkuStylized_{obj.name}"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        # Clear default nodes
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # Create shader nodes
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        
        # Set base color (convert tuple to RGBA)
        if len(base_color) == 3:
            bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
        else:
            bsdf.inputs['Base Color'].default_value = base_color
        
        # Stylized shader settings
        bsdf.inputs['Metallic'].default_value = 0.1  # Slight metallic
        bsdf.inputs['Roughness'].default_value = 0.7  # Slightly rough for matte look
        bsdf.inputs['Specular IOR Level'].default_value = 0.3  # Reduced specular
        
        # Connect to output
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        # Apply material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        
        # Enable flat shading for faceted low-poly look
        for poly in obj.data.polygons:
            poly.use_smooth = False
        
        AkkuLogger.info("Applied stylized material", {
            "material": mat_name,
            "base_color": base_color
        })
    
    @classmethod
    def generate(
        cls,
        style: str = "stylized",
        poly_level: str = "medium",
        gender: str = "male"
    ) -> bpy.types.Object:
        """
        Generate a complete procedural humanoid mesh.
        
        Args:
            style: Character style (realistic, stylized, chibi, sd, mobile, minifig, cartoon)
            poly_level: Polygon complexity (ultra_low, low, medium, high)
            gender: Gender for minor proportion adjustments (male, female)
            
        Returns:
            Generated mesh object
        """
        props = StyleProportions.get_preset(style)
        poly_settings = PolyLevelPresets.get_preset(poly_level)
        
        if gender == "female":
            props.shoulder_width_ratio *= 0.9
            props.hip_width_ratio *= 1.1
            props.torso_thickness *= 0.9
        
        total_height = props.total_height
        head_height = total_height * props.head_ratio
        torso_height = total_height * props.torso_ratio
        leg_height = total_height * props.leg_ratio
        arm_length = total_height * props.arm_length_ratio
        shoulder_width = total_height * props.shoulder_width_ratio
        hip_width = total_height * props.hip_width_ratio
        limb_thickness = props.limb_thickness
        torso_depth = props.torso_thickness
        
        AkkuLogger.info("Generating procedural humanoid", {
            "style": style,
            "poly_level": poly_level,
            "gender": gender,
            "total_height": total_height,
            "head_height": head_height,
            "torso_height": torso_height,
            "leg_height": leg_height
        })
        
        mesh = bpy.data.meshes.new("ProceduralHumanoid")
        obj = bpy.data.objects.new("Character", mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        leg_base = Vector((0, 0, 0))
        torso_base = Vector((0, 0, leg_height))
        shoulder_pos = Vector((0, 0, leg_height + torso_height))
        head_base = shoulder_pos + Vector((0, 0, head_height * 0.1))
        head_center = head_base + Vector((0, 0, head_height * 0.5))
        
        joints = cls.create_torso(
            bm,
            torso_base,
            torso_height,
            shoulder_width,
            hip_width,
            torso_depth,
            segments=poly_settings.torso_segments
        )
        
        head_radius = head_height * props.head_scale * 0.5
        cls.create_sphere_head(
            bm,
            head_center,
            head_radius,
            segments=poly_settings.head_segments,
            rings=max(4, poly_settings.head_segments // 2)
        )
        
        upper_leg_length = leg_height * 0.5
        lower_leg_length = leg_height * 0.5
        
        left_hip = joints["hip_left"]
        right_hip = joints["hip_right"]
        
        left_knee = left_hip - Vector((0, 0, upper_leg_length))
        right_knee = right_hip - Vector((0, 0, upper_leg_length))
        
        left_ankle = left_knee - Vector((0, 0, lower_leg_length * 0.9))
        right_ankle = right_knee - Vector((0, 0, lower_leg_length * 0.9))
        
        cls.create_cylinder_limb(
            bm, left_hip, left_knee, limb_thickness * 1.2,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        cls.create_cylinder_limb(
            bm, left_knee, left_ankle, limb_thickness,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        
        cls.create_cylinder_limb(
            bm, right_hip, right_knee, limb_thickness * 1.2,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        cls.create_cylinder_limb(
            bm, right_knee, right_ankle, limb_thickness,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        
        foot_length = limb_thickness * 3
        foot_width = limb_thickness * 1.5
        foot_height = limb_thickness * 0.8
        
        for ankle in [left_ankle, right_ankle]:
            foot_center = ankle + Vector((0, foot_length * 0.3, -foot_height / 2))
            cls.create_box_limb(
                bm,
                foot_center - Vector((0, 0, foot_height / 2)),
                foot_center + Vector((0, 0, foot_height / 2)),
                foot_width,
                foot_length,
                segments=2
            )
        
        upper_arm_length = arm_length * 0.5
        lower_arm_length = arm_length * 0.5
        
        left_shoulder = joints["shoulder_left"]
        right_shoulder = joints["shoulder_right"]
        
        left_elbow = left_shoulder - Vector((upper_arm_length * 0.8, 0, upper_arm_length * 0.2))
        right_elbow = right_shoulder + Vector((upper_arm_length * 0.8, 0, -upper_arm_length * 0.2))
        
        left_wrist = left_elbow - Vector((lower_arm_length * 0.8, 0, lower_arm_length * 0.2))
        right_wrist = right_elbow + Vector((lower_arm_length * 0.8, 0, -lower_arm_length * 0.2))
        
        cls.create_cylinder_limb(
            bm, left_shoulder, left_elbow, limb_thickness,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        cls.create_cylinder_limb(
            bm, left_elbow, left_wrist, limb_thickness * 0.9,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        
        cls.create_cylinder_limb(
            bm, right_shoulder, right_elbow, limb_thickness,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        cls.create_cylinder_limb(
            bm, right_elbow, right_wrist, limb_thickness * 0.9,
            segments=poly_settings.limb_segments,
            height_segments=3
        )
        
        hand_size = limb_thickness * 1.5
        for wrist in [left_wrist, right_wrist]:
            hand_end = wrist + (wrist - (left_elbow if wrist == left_wrist else right_elbow)).normalized() * hand_size
            cls.create_box_limb(
                bm, wrist, hand_end, hand_size, hand_size * 0.6, segments=2
            )
        
        neck_base = shoulder_pos
        neck_top = head_base
        cls.create_cylinder_limb(
            bm, neck_base, neck_top, limb_thickness * 0.8,
            segments=max(4, poly_settings.limb_segments - 1),
            height_segments=2
        )
        
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        bm.to_mesh(mesh)
        bm.free()
        
        mesh.update()
        
        from .tools import MeshAnalyzer
        stats = MeshAnalyzer.get_stats(obj)
        AkkuLogger.info("Procedural humanoid generated", {
            "vertices": stats.vertex_count,
            "faces": stats.face_count,
            "triangles": stats.triangle_count,
            "style": style,
            "poly_level": poly_level
        })
        
        return obj
    
    @classmethod
    def create_basic_rig(cls, obj: bpy.types.Object) -> bpy.types.Object:
        """Create a basic armature rig for the humanoid"""
        props = StyleProportions.get_preset("stylized")
        total_height = props.total_height
        
        arm = bpy.data.armatures.new("HumanoidRig")
        rig = bpy.data.objects.new("Armature", arm)
        bpy.context.collection.objects.link(rig)
        
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        
        leg_height = total_height * props.leg_ratio
        torso_height = total_height * props.torso_ratio
        head_height = total_height * props.head_ratio
        
        root = arm.edit_bones.new("Root")
        root.head = Vector((0, 0, 0))
        root.tail = Vector((0, 0, 0.1))
        
        hips = arm.edit_bones.new("Hips")
        hips.head = Vector((0, 0, leg_height))
        hips.tail = Vector((0, 0, leg_height + torso_height * 0.3))
        hips.parent = root
        
        spine = arm.edit_bones.new("Spine")
        spine.head = hips.tail.copy()
        spine.tail = Vector((0, 0, leg_height + torso_height * 0.6))
        spine.parent = hips
        
        chest = arm.edit_bones.new("Chest")
        chest.head = spine.tail.copy()
        chest.tail = Vector((0, 0, leg_height + torso_height))
        chest.parent = spine
        
        neck = arm.edit_bones.new("Neck")
        neck.head = chest.tail.copy()
        neck.tail = Vector((0, 0, leg_height + torso_height + head_height * 0.2))
        neck.parent = chest
        
        head = arm.edit_bones.new("Head")
        head.head = neck.tail.copy()
        head.tail = Vector((0, 0, total_height))
        head.parent = neck
        
        hip_width = total_height * props.hip_width_ratio
        shoulder_width = total_height * props.shoulder_width_ratio
        arm_length = total_height * props.arm_length_ratio
        
        for side, sign in [("L", -1), ("R", 1)]:
            upper_leg = arm.edit_bones.new(f"UpperLeg.{side}")
            upper_leg.head = Vector((sign * hip_width / 2, 0, leg_height))
            upper_leg.tail = Vector((sign * hip_width / 2, 0, leg_height * 0.5))
            upper_leg.parent = hips
            
            lower_leg = arm.edit_bones.new(f"LowerLeg.{side}")
            lower_leg.head = upper_leg.tail.copy()
            lower_leg.tail = Vector((sign * hip_width / 2, 0, 0.05))
            lower_leg.parent = upper_leg
            
            foot = arm.edit_bones.new(f"Foot.{side}")
            foot.head = lower_leg.tail.copy()
            foot.tail = Vector((sign * hip_width / 2, 0.1, 0))
            foot.parent = lower_leg
            
            shoulder = arm.edit_bones.new(f"Shoulder.{side}")
            shoulder.head = Vector((0, 0, leg_height + torso_height))
            shoulder.tail = Vector((sign * shoulder_width / 2, 0, leg_height + torso_height))
            shoulder.parent = chest
            
            upper_arm = arm.edit_bones.new(f"UpperArm.{side}")
            upper_arm.head = shoulder.tail.copy()
            upper_arm.tail = Vector((sign * (shoulder_width / 2 + arm_length * 0.5), 0, leg_height + torso_height - arm_length * 0.1))
            upper_arm.parent = shoulder
            
            lower_arm = arm.edit_bones.new(f"LowerArm.{side}")
            lower_arm.head = upper_arm.tail.copy()
            lower_arm.tail = Vector((sign * (shoulder_width / 2 + arm_length), 0, leg_height + torso_height - arm_length * 0.2))
            lower_arm.parent = upper_arm
            
            hand = arm.edit_bones.new(f"Hand.{side}")
            hand.head = lower_arm.tail.copy()
            hand.tail = Vector((sign * (shoulder_width / 2 + arm_length + 0.1), 0, leg_height + torso_height - arm_length * 0.25))
            hand.parent = lower_arm
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        obj.parent = rig
        modifier = obj.modifiers.new(name="Armature", type='ARMATURE')
        modifier.object = rig
        
        AkkuLogger.info("Basic rig created", {"bone_count": len(arm.bones)})
        
        return rig
    
    @classmethod
    def generate_hierarchical(
        cls,
        style: str = "stylized",
        poly_level: str = "medium",
        gender: str = "male",
        equipment: str = "default"
    ) -> bpy.types.Object:
        """
        Generate a humanoid with separate body parts in a hierarchy.
        
        Creates separate mesh objects for each body part:
        - Root (Empty)
          - Head
          - Torso
          - Arm_L (Upper + Lower + Hand)
          - Arm_R (Upper + Lower + Hand)
          - Leg_L (Upper + Lower + Foot)
          - Leg_R (Upper + Lower + Foot)
        
        Args:
            style: Character style preset
            poly_level: Polygon complexity
            gender: Gender for proportions
            equipment: Equipment type (armor, robe, default)
            
        Returns:
            Root empty object with all parts as children
        """
        props = StyleProportions.get_preset(style)
        poly_settings = PolyLevelPresets.get_preset(poly_level)
        
        if gender == "female":
            props.shoulder_width_ratio *= 0.9
            props.hip_width_ratio *= 1.1
            props.torso_thickness *= 0.9
        
        total_height = props.total_height
        head_height = total_height * props.head_ratio
        torso_height = total_height * props.torso_ratio
        leg_height = total_height * props.leg_ratio
        arm_length = total_height * props.arm_length_ratio
        shoulder_width = total_height * props.shoulder_width_ratio
        hip_width = total_height * props.hip_width_ratio
        limb_thickness = props.limb_thickness
        torso_depth = props.torso_thickness
        
        AkkuLogger.info("Generating hierarchical humanoid", {
            "style": style,
            "poly_level": poly_level,
            "gender": gender
        })
        
        root = bpy.data.objects.new("Character_Root", None)
        root.empty_display_type = 'ARROWS'
        root.empty_display_size = 0.2
        bpy.context.collection.objects.link(root)
        
        leg_base = Vector((0, 0, 0))
        torso_base = Vector((0, 0, leg_height))
        shoulder_pos = Vector((0, 0, leg_height + torso_height))
        head_base = shoulder_pos + Vector((0, 0, head_height * 0.1))
        head_center = head_base + Vector((0, 0, head_height * 0.5))
        
        torso_obj = cls._create_detailed_torso(
            "Torso",
            torso_base,
            torso_height,
            shoulder_width,
            hip_width,
            torso_depth,
            poly_settings
        )
        torso_obj.parent = root
        
        head_radius = head_height * props.head_scale * 0.5
        head_obj = cls._create_detailed_head(
            "Head",
            head_center,
            head_radius,
            poly_settings
        )
        head_obj.parent = root
        
        neck_obj = cls._create_limb_part(
            "Neck",
            shoulder_pos,
            head_base,
            limb_thickness * 0.8,
            poly_settings
        )
        neck_obj.parent = root
        
        upper_leg_length = leg_height * 0.5
        lower_leg_length = leg_height * 0.5
        
        left_hip = Vector((-hip_width / 2, 0, leg_height))
        right_hip = Vector((hip_width / 2, 0, leg_height))
        
        left_knee = left_hip - Vector((0, 0, upper_leg_length))
        right_knee = right_hip - Vector((0, 0, upper_leg_length))
        
        left_ankle = left_knee - Vector((0, 0, lower_leg_length * 0.9))
        right_ankle = right_knee - Vector((0, 0, lower_leg_length * 0.9))
        
        leg_l_upper = cls._create_limb_part("Leg_L_Upper", left_hip, left_knee, limb_thickness * 1.3, poly_settings)
        leg_l_lower = cls._create_limb_part("Leg_L_Lower", left_knee, left_ankle, limb_thickness * 1.1, poly_settings)
        leg_l_upper.parent = root
        leg_l_lower.parent = root
        
        leg_r_upper = cls._create_limb_part("Leg_R_Upper", right_hip, right_knee, limb_thickness * 1.3, poly_settings)
        leg_r_lower = cls._create_limb_part("Leg_R_Lower", right_knee, right_ankle, limb_thickness * 1.1, poly_settings)
        leg_r_upper.parent = root
        leg_r_lower.parent = root
        
        foot_length = limb_thickness * 3.5
        foot_width = limb_thickness * 2
        foot_height = limb_thickness * 0.9
        
        foot_l = cls._create_foot("Foot_L", left_ankle, foot_length, foot_width, foot_height, -1)
        foot_r = cls._create_foot("Foot_R", right_ankle, foot_length, foot_width, foot_height, 1)
        foot_l.parent = root
        foot_r.parent = root
        
        upper_arm_length = arm_length * 0.5
        lower_arm_length = arm_length * 0.5
        
        left_shoulder = shoulder_pos + Vector((-shoulder_width / 2, 0, 0))
        right_shoulder = shoulder_pos + Vector((shoulder_width / 2, 0, 0))
        
        left_elbow = left_shoulder - Vector((upper_arm_length * 0.85, 0, upper_arm_length * 0.15))
        right_elbow = right_shoulder + Vector((upper_arm_length * 0.85, 0, -upper_arm_length * 0.15))
        
        left_wrist = left_elbow - Vector((lower_arm_length * 0.85, 0, lower_arm_length * 0.15))
        right_wrist = right_elbow + Vector((lower_arm_length * 0.85, 0, -lower_arm_length * 0.15))
        
        arm_l_upper = cls._create_limb_part("Arm_L_Upper", left_shoulder, left_elbow, limb_thickness * 1.1, poly_settings)
        arm_l_lower = cls._create_limb_part("Arm_L_Lower", left_elbow, left_wrist, limb_thickness * 0.95, poly_settings)
        arm_l_upper.parent = root
        arm_l_lower.parent = root
        
        arm_r_upper = cls._create_limb_part("Arm_R_Upper", right_shoulder, right_elbow, limb_thickness * 1.1, poly_settings)
        arm_r_lower = cls._create_limb_part("Arm_R_Lower", right_elbow, right_wrist, limb_thickness * 0.95, poly_settings)
        arm_r_upper.parent = root
        arm_r_lower.parent = root
        
        hand_size = limb_thickness * 1.8
        hand_l = cls._create_hand("Hand_L", left_wrist, left_elbow, hand_size)
        hand_r = cls._create_hand("Hand_R", right_wrist, right_elbow, hand_size)
        hand_l.parent = root
        hand_r.parent = root
        
        if poly_settings.use_subdivision:
            AkkuLogger.info("Applying subdivision and smoothing", {
                "level": poly_settings.subdivision_level
            })
            for child in root.children:
                if child.type == 'MESH':
                    SubdivisionOps.apply_subdivision(
                        child, 
                        levels=poly_settings.subdivision_level,
                        render_levels=poly_settings.subdivision_level,
                        apply_modifier=True
                    )
                    SculptOps.smooth_all(child, iterations=2, factor=0.3)
        
        cls._apply_vertex_colors(root, style, equipment)
        
        total_verts = 0
        total_faces = 0
        for child in root.children:
            if child.type == 'MESH':
                total_verts += len(child.data.vertices)
                total_faces += len(child.data.polygons)
        
        AkkuLogger.info("Hierarchical humanoid generated", {
            "parts_count": len(root.children),
            "total_vertices": total_verts,
            "total_faces": total_faces,
            "style": style,
            "poly_level": poly_level
        })
        
        return root
    
    @classmethod
    def _apply_vertex_colors(
        cls,
        root: bpy.types.Object,
        style: str,
        equipment: Optional[str] = None
    ):
        """Apply vertex colors to all mesh parts based on style and equipment"""
        
        skin_color = ColorPalette.SKIN_LIGHT
        if "dark" in style.lower():
            skin_color = ColorPalette.SKIN_DARK
        elif "tan" in style.lower() or "medium" in style.lower():
            skin_color = ColorPalette.SKIN_MEDIUM
        
        equipment = equipment or "default"
        equipment_lower = equipment.lower()
        
        for child in root.children:
            if child.type != 'MESH':
                continue
            
            name_lower = child.name.lower()
            bm = AtomicOps.get_bmesh(child)
            
            if 'head' in name_lower:
                VertexColorOps.paint_all(bm, skin_color)
            elif 'hand' in name_lower:
                VertexColorOps.paint_all(bm, skin_color)
            elif 'torso' in name_lower:
                if 'armor' in equipment_lower or 'knight' in equipment_lower:
                    VertexColorOps.paint_all(bm, ColorPalette.CLOTH_BLACK)
                    AtomicOps.apply_bmesh(bm, child)
                    HardSurfaceKitbash.add_chest_armor(child, ColorPalette.ARMOR_BLUE)
                    continue
                elif 'robe' in equipment_lower or 'mage' in equipment_lower:
                    VertexColorOps.paint_all(bm, ColorPalette.ROBE_GREEN)
                else:
                    VertexColorOps.paint_all(bm, ColorPalette.CLOTH_WHITE)
            elif 'arm' in name_lower:
                if 'armor' in equipment_lower or 'knight' in equipment_lower:
                    VertexColorOps.paint_all(bm, ColorPalette.ARMOR_BLUE)
                elif 'robe' in equipment_lower or 'mage' in equipment_lower:
                    VertexColorOps.paint_gradient_vertical(
                        bm, ColorPalette.ROBE_GREEN, skin_color
                    )
                else:
                    VertexColorOps.paint_all(bm, ColorPalette.CLOTH_WHITE)
            elif 'leg' in name_lower:
                if 'armor' in equipment_lower or 'knight' in equipment_lower:
                    VertexColorOps.paint_all(bm, ColorPalette.ARMOR_DARK)
                elif 'robe' in equipment_lower or 'mage' in equipment_lower:
                    VertexColorOps.paint_all(bm, ColorPalette.ROBE_GREEN)
                else:
                    VertexColorOps.paint_all(bm, ColorPalette.LEATHER_BROWN)
            elif 'foot' in name_lower or 'feet' in name_lower:
                VertexColorOps.paint_all(bm, ColorPalette.LEATHER_BROWN)
            else:
                VertexColorOps.paint_all(bm, ColorPalette.CLOTH_WHITE)
            
            AtomicOps.apply_bmesh(bm, child)
    
    @classmethod
    def _create_detailed_torso(
        cls,
        name: str,
        base_pos: Vector,
        height: float,
        shoulder_width: float,
        hip_width: float,
        depth: float,
        poly_settings
    ) -> bpy.types.Object:
        """Create a detailed torso mesh with chest and waist definition"""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        segments = max(8, poly_settings.torso_segments + 2)
        height_divisions = max(6, poly_settings.torso_segments // 2)
        
        verts = []
        for h in range(height_divisions + 1):
            t = h / height_divisions
            y_pos = base_pos.z + height * t
            
            if t < 0.2:
                width = hip_width * (0.9 + t * 0.5)
                d = depth * 0.85
            elif t < 0.5:
                waist_t = (t - 0.2) / 0.3
                width = hip_width * (1.0 - waist_t * 0.15)
                d = depth * (0.85 + waist_t * 0.1)
            elif t < 0.8:
                chest_t = (t - 0.5) / 0.3
                width = hip_width * (0.85 + chest_t * 0.35) * (shoulder_width / hip_width)
                d = depth * (0.95 + chest_t * 0.15)
            else:
                shoulder_t = (t - 0.8) / 0.2
                width = shoulder_width * (1.0 - shoulder_t * 0.05)
                d = depth * (1.1 - shoulder_t * 0.1)
            
            row = []
            for s in range(segments):
                angle = (s / segments) * 2 * math.pi
                x = math.cos(angle) * width / 2
                z = math.sin(angle) * d / 2
                v = bm.verts.new(Vector((x, z, y_pos)))
                row.append(v)
            verts.append(row)
        
        bm.verts.ensure_lookup_table()
        
        for h in range(height_divisions):
            for s in range(segments):
                v1 = verts[h][s]
                v2 = verts[h][(s + 1) % segments]
                v3 = verts[h + 1][(s + 1) % segments]
                v4 = verts[h + 1][s]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except:
                    pass
        
        bottom_center = bm.verts.new(Vector((0, 0, base_pos.z)))
        bm.verts.ensure_lookup_table()
        for s in range(segments):
            try:
                bm.faces.new([bottom_center, verts[0][(s + 1) % segments], verts[0][s]])
            except:
                pass
        
        top_center = bm.verts.new(Vector((0, 0, base_pos.z + height)))
        bm.verts.ensure_lookup_table()
        for s in range(segments):
            try:
                bm.faces.new([top_center, verts[-1][s], verts[-1][(s + 1) % segments]])
            except:
                pass
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
    
    @classmethod
    def _create_detailed_head(
        cls,
        name: str,
        center: Vector,
        radius: float,
        poly_settings
    ) -> bpy.types.Object:
        """Create a detailed head with slight oval shape"""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        segments = max(12, poly_settings.head_segments + 4)
        rings = max(8, segments // 2)
        
        verts = []
        
        bottom = bm.verts.new(center - Vector((0, 0, radius * 0.9)))
        verts.append([bottom])
        
        for r in range(1, rings):
            t = r / rings
            phi = t * math.pi
            
            y_scale = 1.0 - 0.1 * math.sin(phi)
            z_scale = 1.0 + 0.05 * (1 - abs(t - 0.5) * 2)
            
            row = []
            for s in range(segments):
                theta = (s / segments) * 2 * math.pi
                x = radius * math.sin(phi) * math.cos(theta) * y_scale
                y = radius * math.sin(phi) * math.sin(theta) * y_scale
                z = radius * math.cos(phi) * z_scale
                v = bm.verts.new(center + Vector((x, y, z)))
                row.append(v)
            verts.append(row)
        
        top = bm.verts.new(center + Vector((0, 0, radius)))
        verts.append([top])
        
        bm.verts.ensure_lookup_table()
        
        for s in range(segments):
            try:
                bm.faces.new([verts[0][0], verts[1][s], verts[1][(s + 1) % segments]])
            except:
                pass
        
        for r in range(1, rings - 1):
            for s in range(segments):
                v1 = verts[r][s]
                v2 = verts[r][(s + 1) % segments]
                v3 = verts[r + 1][(s + 1) % segments]
                v4 = verts[r + 1][s]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except:
                    pass
        
        for s in range(segments):
            try:
                bm.faces.new([verts[-1][0], verts[-2][(s + 1) % segments], verts[-2][s]])
            except:
                pass
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
    
    @classmethod
    def _create_limb_part(
        cls,
        name: str,
        start: Vector,
        end: Vector,
        radius: float,
        poly_settings
    ) -> bpy.types.Object:
        """Create a limb segment with muscle bulge and natural taper"""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        segments = max(8, poly_settings.limb_segments)
        height_segments = max(6, poly_settings.limb_segments)
        
        direction = (end - start).normalized()
        length = (end - start).length
        
        if abs(direction.z) < 0.99:
            side = direction.cross(Vector((0, 0, 1))).normalized()
        else:
            side = direction.cross(Vector((1, 0, 0))).normalized()
        forward = direction.cross(side).normalized()
        
        verts = []
        for h in range(height_segments + 1):
            t = h / height_segments
            pos = start.lerp(end, t)
            
            muscle_bulge = math.sin(t * math.pi) * 0.25
            end_taper_start = 1.0 - (abs(t - 0.5) * 0.15)
            end_taper_end = 1.0 - (t * 0.1 if t > 0.7 else 0)
            scale = (1.0 + muscle_bulge) * end_taper_start * end_taper_end
            
            row = []
            for s in range(segments):
                angle = (s / segments) * 2 * math.pi
                front_back_scale = 1.0 + 0.1 * abs(math.sin(angle))
                r = radius * scale * front_back_scale
                offset = (side * math.cos(angle) + forward * math.sin(angle)) * r
                v = bm.verts.new(pos + offset)
                row.append(v)
            verts.append(row)
        
        bm.verts.ensure_lookup_table()
        
        for h in range(height_segments):
            for s in range(segments):
                v1 = verts[h][s]
                v2 = verts[h][(s + 1) % segments]
                v3 = verts[h + 1][(s + 1) % segments]
                v4 = verts[h + 1][s]
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except:
                    pass
        
        start_center = bm.verts.new(start)
        bm.verts.ensure_lookup_table()
        for s in range(segments):
            try:
                bm.faces.new([start_center, verts[0][(s + 1) % segments], verts[0][s]])
            except:
                pass
        
        end_center = bm.verts.new(end)
        bm.verts.ensure_lookup_table()
        for s in range(segments):
            try:
                bm.faces.new([end_center, verts[-1][s], verts[-1][(s + 1) % segments]])
            except:
                pass
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
    
    @classmethod
    def _create_foot(
        cls,
        name: str,
        ankle: Vector,
        length: float,
        width: float,
        height: float,
        side: int
    ) -> bpy.types.Object:
        """Create a detailed foot mesh with rounded shape"""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        foot_center = ankle + Vector((0, length * 0.35, -height / 2))
        
        segments_w = 4
        segments_l = 6
        segments_h = 3
        
        verts = []
        
        for h in range(segments_h + 1):
            ht = h / segments_h
            z = foot_center.z - height/2 + height * ht
            
            h_scale = 1.0 - abs(ht - 0.3) * 0.3
            
            row = []
            for li in range(segments_l + 1):
                lt = li / segments_l
                y = foot_center.y - length/2 + length * lt
                
                toe_taper = 1.0 - lt * 0.3 if lt > 0.5 else 1.0
                heel_round = 1.0 - (1-lt) * 0.2 if lt < 0.3 else 1.0
                
                for wi in range(segments_w + 1):
                    wt = wi / segments_w
                    x = foot_center.x - width/2 * toe_taper * heel_round * h_scale + width * toe_taper * heel_round * h_scale * wt
                    
                    v = bm.verts.new(Vector((x, y, z)))
                    row.append(v)
            verts.append(row)
        
        bm.verts.ensure_lookup_table()
        
        stride = segments_w + 1
        for h in range(segments_h):
            for li in range(segments_l):
                for wi in range(segments_w):
                    idx = li * stride + wi
                    v1 = verts[h][idx]
                    v2 = verts[h][idx + 1]
                    v3 = verts[h + 1][idx + 1]
                    v4 = verts[h + 1][idx]
                    try:
                        bm.faces.new([v1, v2, v3, v4])
                    except:
                        pass
        
        for li in range(segments_l):
            for wi in range(segments_w):
                idx = li * stride + wi
                try:
                    bm.faces.new([verts[0][idx], verts[0][idx + stride], verts[0][idx + stride + 1], verts[0][idx + 1]])
                except:
                    pass
                try:
                    bm.faces.new([verts[-1][idx], verts[-1][idx + 1], verts[-1][idx + stride + 1], verts[-1][idx + stride]])
                except:
                    pass
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
    
    @classmethod
    def _create_hand(
        cls,
        name: str,
        wrist: Vector,
        elbow: Vector,
        size: float
    ) -> bpy.types.Object:
        """Create a detailed hand mesh with rounded palm shape"""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        direction = (wrist - elbow).normalized()
        hand_end = wrist + direction * size
        
        hw = size * 0.5
        hh = size * 0.2
        
        if abs(direction.z) < 0.99:
            side_vec = direction.cross(Vector((0, 0, 1))).normalized()
        else:
            side_vec = direction.cross(Vector((1, 0, 0))).normalized()
        up = direction.cross(side_vec).normalized()
        
        segments_along = 5
        segments_across = 4
        segments_thick = 2
        
        verts = []
        for ti in range(segments_thick + 1):
            tt = ti / segments_thick
            thickness_offset = up * (hh * (tt - 0.5) * 2)
            
            palm_bulge = math.sin(tt * math.pi) * 0.15
            
            layer = []
            for ai in range(segments_along + 1):
                at = ai / segments_along
                pos_along = wrist.lerp(hand_end, at)
                
                finger_taper = 1.0 - at * 0.4
                
                for wi in range(segments_across + 1):
                    wt = wi / segments_across
                    side_offset = side_vec * (hw * finger_taper * (wt - 0.5) * 2)
                    
                    knuckle_bump = math.sin(wt * math.pi) * 0.05 * (1.0 + palm_bulge) if at > 0.6 else 0
                    
                    pos = pos_along + thickness_offset * (1.0 + palm_bulge) + side_offset + up * knuckle_bump
                    v = bm.verts.new(pos)
                    layer.append(v)
            verts.append(layer)
        
        bm.verts.ensure_lookup_table()
        
        stride = segments_across + 1
        for ti in range(segments_thick):
            for ai in range(segments_along):
                for wi in range(segments_across):
                    idx = ai * stride + wi
                    try:
                        bm.faces.new([
                            verts[ti][idx], verts[ti][idx + 1],
                            verts[ti + 1][idx + 1], verts[ti + 1][idx]
                        ])
                    except:
                        pass
        
        for ti in range(segments_thick):
            for ai in range(segments_along):
                idx = ai * stride
                try:
                    bm.faces.new([
                        verts[ti][idx], verts[ti + 1][idx],
                        verts[ti + 1][idx + stride], verts[ti][idx + stride]
                    ])
                except:
                    pass
                idx = ai * stride + segments_across
                try:
                    bm.faces.new([
                        verts[ti][idx], verts[ti][idx + stride],
                        verts[ti + 1][idx + stride], verts[ti + 1][idx]
                    ])
                except:
                    pass
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
