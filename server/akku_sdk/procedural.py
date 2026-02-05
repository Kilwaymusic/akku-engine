"""
Akku SDK Procedural - Procedural Humanoid Mesh Generator

Generates low-poly humanoid base meshes from scratch using bmesh primitives.
Replaces Mixamo FBX dependency with fully procedural generation.
"""

import bpy
import bmesh
import math
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
from mathutils import Vector, Matrix

from .core import AkkuLogger


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
        gender: str = "male"
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
