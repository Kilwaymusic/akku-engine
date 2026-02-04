"""
Akku SDK Kitbash - Direct Bone Parenting System

CRITICAL DESIGN PRINCIPLES:
1. All accessories are parented to bones IMMEDIATELY upon creation
2. Mesh is created in LOCAL bone space (not world space)
3. No floating parts - everything follows armature

This uses BONE_RELATIVE parenting with vertex data in bone-local coordinates.
"""

import bpy
import bmesh
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from mathutils import Vector, Euler, Matrix

from .core import AkkuLogger
from .shader import StyleToGLBConverter


@dataclass
class SocketInfo:
    """Attachment socket definition for semantic parts"""
    bone_name: str
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0


@dataclass
class SemanticPart:
    """Semantic part definition with attachment data"""
    name: str
    category: str
    style: str
    socket: SocketInfo
    mesh_type: str = "primitive"
    mesh_data: Dict = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.mesh_data is None:
            self.mesh_data = {}
        if self.tags is None:
            self.tags = []


class KitbashLibrary:
    """Kitbash 2.0 - Semantic Component Library"""
    
    BONE_SOCKETS = {
        "head": "mixamorig:Head",
        "neck": "mixamorig:Neck",
        "chest": "mixamorig:Spine2",
        "spine": "mixamorig:Spine1",
        "hips": "mixamorig:Hips",
        "left_shoulder": "mixamorig:LeftShoulder",
        "right_shoulder": "mixamorig:RightShoulder",
        "left_arm": "mixamorig:LeftArm",
        "right_arm": "mixamorig:RightArm",
        "left_forearm": "mixamorig:LeftForeArm",
        "right_forearm": "mixamorig:RightForeArm",
        "left_hand": "mixamorig:LeftHand",
        "right_hand": "mixamorig:RightHand",
        "left_leg": "mixamorig:LeftUpLeg",
        "right_leg": "mixamorig:RightUpLeg",
        "left_foot": "mixamorig:LeftFoot",
        "right_foot": "mixamorig:RightFoot",
    }
    
    CATEGORY_TAXONOMY = {
        "armor": ["helmet", "shoulder", "chest", "boots", "gauntlet"],
        "weapons": ["weapon", "shield"],
        "accessories": ["accessory"],
        "full_set": ["helmet", "shoulder", "chest", "boots", "gauntlet", "weapon", "shield"],
    }
    
    _parts: Dict[str, SemanticPart] = {}
    
    @classmethod
    def _init_library(cls):
        """Initialize the parts library with default parts"""
        if cls._parts:
            return
        
        cls._parts["Knight_Helmet"] = SemanticPart(
            name="Knight_Helmet", category="helmet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, 0, 0.12), rotation=(0, 0, 0), scale=0.18),
            mesh_type="primitive", mesh_data={"type": "uv_sphere", "segments": 16, "rings": 12},
            tags=["knight", "medieval", "armor", "heavy"]
        )
        
        cls._parts["SciFi_Helmet"] = SemanticPart(
            name="SciFi_Helmet", category="helmet", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, 0.02, 0.10), rotation=(15, 0, 0), scale=0.16),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["scifi", "futuristic", "tech", "visor"]
        )
        
        cls._parts["Light_Hood"] = SemanticPart(
            name="Light_Hood", category="helmet", style="light",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, -0.02, 0.08), rotation=(-10, 0, 0), scale=0.18),
            mesh_type="primitive", mesh_data={"type": "cone", "vertices": 16, "radius1": 1.0, "depth": 0.8},
            tags=["rogue", "assassin", "light", "cloth"]
        )
        
        cls._parts["Magic_Hood"] = SemanticPart(
            name="Magic_Hood", category="helmet", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, -0.02, 0.10), rotation=(-15, 0, 0), scale=0.20),
            mesh_type="primitive", mesh_data={"type": "cone", "vertices": 16, "radius1": 1.2, "depth": 1.0},
            tags=["mage", "wizard", "magic", "cloth"]
        )
        
        cls._parts["Knight_Shoulder_L"] = SemanticPart(
            name="Knight_Shoulder_L", category="shoulder", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_shoulder"], offset=(0.10, 0, 0.04), rotation=(0, 0, -15), scale=0.12),
            mesh_type="primitive", mesh_data={"type": "uv_sphere", "segments": 12, "rings": 8},
            tags=["knight", "pauldron", "armor", "left"]
        )
        
        cls._parts["Knight_Shoulder_R"] = SemanticPart(
            name="Knight_Shoulder_R", category="shoulder", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_shoulder"], offset=(-0.10, 0, 0.04), rotation=(0, 0, 15), scale=0.12),
            mesh_type="primitive", mesh_data={"type": "uv_sphere", "segments": 12, "rings": 8},
            tags=["knight", "pauldron", "armor", "right"]
        )
        
        cls._parts["SciFi_Shoulder_L"] = SemanticPart(
            name="SciFi_Shoulder_L", category="shoulder", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_shoulder"], offset=(0.12, 0, 0.05), rotation=(0, 45, -20), scale=0.10),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["scifi", "tech", "angular", "left"]
        )
        
        cls._parts["SciFi_Shoulder_R"] = SemanticPart(
            name="SciFi_Shoulder_R", category="shoulder", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_shoulder"], offset=(-0.12, 0, 0.05), rotation=(0, -45, 20), scale=0.10),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["scifi", "tech", "angular", "right"]
        )
        
        cls._parts["Knight_Chestplate"] = SemanticPart(
            name="Knight_Chestplate", category="chest", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["chest"], offset=(0, 0.10, 0), rotation=(0, 0, 0), scale=0.20),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["knight", "plate", "torso", "heavy"]
        )
        
        cls._parts["SciFi_Chestplate"] = SemanticPart(
            name="SciFi_Chestplate", category="chest", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["chest"], offset=(0, 0.09, 0.02), rotation=(5, 0, 0), scale=0.18),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["scifi", "tech", "armor", "angular"]
        )
        
        cls._parts["Magic_Robe"] = SemanticPart(
            name="Magic_Robe", category="chest", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["chest"], offset=(0, 0.08, 0), rotation=(0, 0, 0), scale=0.22),
            mesh_type="primitive", mesh_data={"type": "cone", "vertices": 16, "radius1": 1.0, "depth": 1.5},
            tags=["mage", "wizard", "robe", "magic"]
        )
        
        cls._parts["Heavy_Boots_L"] = SemanticPart(
            name="Heavy_Boots_L", category="boots", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_foot"], offset=(0, 0, -0.03), rotation=(0, 0, 0), scale=0.08),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["knight", "boots", "heavy", "left"]
        )
        
        cls._parts["Heavy_Boots_R"] = SemanticPart(
            name="Heavy_Boots_R", category="boots", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_foot"], offset=(0, 0, -0.03), rotation=(0, 0, 0), scale=0.08),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["knight", "boots", "heavy", "right"]
        )
        
        cls._parts["SciFi_Boots_L"] = SemanticPart(
            name="SciFi_Boots_L", category="boots", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_foot"], offset=(0, 0.02, -0.02), rotation=(10, 0, 0), scale=0.07),
            mesh_type="primitive", mesh_data={"type": "cylinder", "vertices": 12, "radius": 0.5, "depth": 1.2},
            tags=["scifi", "boots", "tech", "left"]
        )
        
        cls._parts["SciFi_Boots_R"] = SemanticPart(
            name="SciFi_Boots_R", category="boots", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_foot"], offset=(0, 0.02, -0.02), rotation=(10, 0, 0), scale=0.07),
            mesh_type="primitive", mesh_data={"type": "cylinder", "vertices": 12, "radius": 0.5, "depth": 1.2},
            tags=["scifi", "boots", "tech", "right"]
        )
        
        cls._parts["Magic_Boots_L"] = SemanticPart(
            name="Magic_Boots_L", category="boots", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_foot"], offset=(0, 0, -0.02), rotation=(0, 0, 0), scale=0.06),
            mesh_type="primitive", mesh_data={"type": "cone", "vertices": 12, "radius1": 0.8, "depth": 1.0},
            tags=["mage", "boots", "cloth", "left"]
        )
        
        cls._parts["Magic_Boots_R"] = SemanticPart(
            name="Magic_Boots_R", category="boots", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_foot"], offset=(0, 0, -0.02), rotation=(0, 0, 0), scale=0.06),
            mesh_type="primitive", mesh_data={"type": "cone", "vertices": 12, "radius1": 0.8, "depth": 1.0},
            tags=["mage", "boots", "cloth", "right"]
        )
        
        cls._parts["Knight_Gauntlet_L"] = SemanticPart(
            name="Knight_Gauntlet_L", category="gauntlet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_forearm"], offset=(0, 0, 0), rotation=(0, 0, 0), scale=0.06),
            mesh_type="primitive", mesh_data={"type": "cylinder", "vertices": 12, "radius": 0.6, "depth": 1.5},
            tags=["knight", "gauntlet", "arm", "left"]
        )
        
        cls._parts["Knight_Gauntlet_R"] = SemanticPart(
            name="Knight_Gauntlet_R", category="gauntlet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_forearm"], offset=(0, 0, 0), rotation=(0, 0, 0), scale=0.06),
            mesh_type="primitive", mesh_data={"type": "cylinder", "vertices": 12, "radius": 0.6, "depth": 1.5},
            tags=["knight", "gauntlet", "arm", "right"]
        )
        
        cls._parts["Knight_Sword"] = SemanticPart(
            name="Knight_Sword", category="weapon", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_hand"], offset=(0, 0.08, 0), rotation=(90, 0, 0), scale=0.12),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["sword", "weapon", "melee", "knight"]
        )
        
        cls._parts["SciFi_Blaster"] = SemanticPart(
            name="SciFi_Blaster", category="weapon", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_hand"], offset=(0.02, 0.06, 0), rotation=(90, 0, 0), scale=0.08),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["gun", "blaster", "ranged", "scifi"]
        )
        
        cls._parts["Staff"] = SemanticPart(
            name="Staff", category="weapon", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_hand"], offset=(0, 0.12, 0), rotation=(0, 0, 0), scale=0.05),
            mesh_type="primitive", mesh_data={"type": "cylinder", "vertices": 12, "radius": 0.15, "depth": 4.0},
            tags=["staff", "magic", "wizard", "mage"]
        )
        
        cls._parts["Magic_Shoulder_L"] = SemanticPart(
            name="Magic_Shoulder_L", category="shoulder", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_shoulder"], offset=(0.08, 0, 0.03), rotation=(0, 0, -10), scale=0.08),
            mesh_type="primitive", mesh_data={"type": "uv_sphere", "segments": 12, "rings": 8},
            tags=["mage", "shoulder", "cloth", "left"]
        )
        
        cls._parts["Magic_Shoulder_R"] = SemanticPart(
            name="Magic_Shoulder_R", category="shoulder", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_shoulder"], offset=(-0.08, 0, 0.03), rotation=(0, 0, 10), scale=0.08),
            mesh_type="primitive", mesh_data={"type": "uv_sphere", "segments": 12, "rings": 8},
            tags=["mage", "shoulder", "cloth", "right"]
        )
        
        cls._parts["Knight_Shield"] = SemanticPart(
            name="Knight_Shield", category="shield", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_forearm"], offset=(0.06, 0.04, 0), rotation=(0, 90, 0), scale=0.14),
            mesh_type="primitive", mesh_data={"type": "cube", "size": 1.0},
            tags=["shield", "defense", "knight", "left"]
        )
        
        AkkuLogger.info(f"Kitbash library initialized with {len(cls._parts)} parts")
    
    @classmethod
    def get_part(cls, name: str) -> Optional[SemanticPart]:
        """Get a specific part by name"""
        cls._init_library()
        return cls._parts.get(name)
    
    @classmethod
    def query_parts(
        cls,
        category: str = None,
        style: str = None,
        tags: List[str] = None
    ) -> List[SemanticPart]:
        """Query parts by category, style, and/or tags"""
        cls._init_library()
        
        results = list(cls._parts.values())
        
        if category:
            if category in cls.CATEGORY_TAXONOMY:
                sub_categories = cls.CATEGORY_TAXONOMY[category]
                results = [p for p in results if p.category in sub_categories]
            else:
                results = [p for p in results if p.category == category]
        
        if style:
            results = [p for p in results if p.style == style]
        
        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]
        
        return results
    
    @classmethod
    def get_equipment_set(cls, style: str) -> Dict[str, List[SemanticPart]]:
        """Get a full equipment set for a style"""
        cls._init_library()
        
        categories = ["helmet", "shoulder", "chest", "boots", "gauntlet", "weapon", "shield"]
        equipment = {}
        
        for cat in categories:
            parts = cls.query_parts(category=cat, style=style)
            if parts:
                equipment[cat] = parts
        
        return equipment
    
    @classmethod
    def list_categories(cls) -> List[str]:
        """List all available categories"""
        cls._init_library()
        return list(set(p.category for p in cls._parts.values()))
    
    @classmethod
    def list_styles(cls) -> List[str]:
        """List all available styles"""
        cls._init_library()
        return list(set(p.style for p in cls._parts.values()))


class DirectBoneParenting:
    """
    Direct Bone Parenting System
    
    CRITICAL: This class ensures accessories are NEVER floating.
    
    Approach:
    1. Create mesh at origin (0,0,0)
    2. Immediately set parent to armature with BONE parent type
    3. Apply socket offset/rotation as parent_inverse
    4. Mesh data stays in local bone space
    """
    
    @staticmethod
    def find_armature() -> Optional[bpy.types.Object]:
        """Find the character armature in the scene"""
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        return None
    
    @staticmethod
    def find_bone(armature, bone_name: str):
        """Find a bone in the armature (from pose bones)"""
        if armature and armature.type == 'ARMATURE':
            return armature.pose.bones.get(bone_name)
        return None
    
    @staticmethod
    def create_primitive_at_origin(mesh_data: Dict, name: str) -> bpy.types.Object:
        """Create a primitive mesh centered at origin"""
        mesh_type = mesh_data.get("type", "cube")
        
        mesh = bpy.data.meshes.new(name=f"{name}_mesh")
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        bpy.context.scene.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        if mesh_type == "cube":
            size = mesh_data.get("size", 1.0) / 2
            bmesh.ops.create_cube(bm, size=size)
        elif mesh_type == "uv_sphere":
            segments = mesh_data.get("segments", 8)
            rings = mesh_data.get("rings", 6)
            bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=0.5)
        elif mesh_type == "cylinder":
            verts = mesh_data.get("vertices", 8)
            radius = mesh_data.get("radius", 0.5)
            depth = mesh_data.get("depth", 1.0)
            bmesh.ops.create_cone(bm, segments=verts, radius1=radius, radius2=radius, depth=depth, cap_ends=True)
        elif mesh_type == "cone":
            verts = mesh_data.get("vertices", 8)
            radius1 = mesh_data.get("radius1", 1.0)
            depth = mesh_data.get("depth", 1.0)
            bmesh.ops.create_cone(bm, segments=verts, radius1=radius1, radius2=0, depth=depth, cap_ends=True)
        else:
            bmesh.ops.create_cube(bm, size=0.5)
        
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        return obj
    
    @staticmethod
    def parent_to_bone(
        obj: bpy.types.Object,
        armature: bpy.types.Object,
        bone_name: str,
        offset: Tuple[float, float, float] = (0, 0, 0),
        rotation: Tuple[float, float, float] = (0, 0, 0),
        scale: float = 1.0
    ) -> bool:
        """
        Parent object to bone with local offset.
        
        CRITICAL: This is the key function that prevents floating parts.
        
        The object's location/rotation/scale are set in BONE-LOCAL space.
        When the bone moves (animation), the object moves with it.
        """
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            AkkuLogger.warning(f"Bone not found: {bone_name}")
            return False
        
        obj.parent = armature
        obj.parent_type = 'BONE'
        obj.parent_bone = bone_name
        
        obj.location = Vector(offset)
        
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = Euler((
            math.radians(rotation[0]),
            math.radians(rotation[1]),
            math.radians(rotation[2])
        ), 'XYZ')
        
        obj.scale = (scale, scale, scale)
        
        AkkuLogger.info(f"Parented {obj.name} to bone {bone_name}", {
            "offset": offset,
            "rotation": rotation,
            "scale": scale
        })
        
        return True
    
    @staticmethod
    def add_armature_modifier(obj: bpy.types.Object, armature: bpy.types.Object) -> bool:
        """
        Add armature modifier for skinned deformation.
        
        Use this if the part needs to deform with the character
        (e.g., clothing that stretches).
        
        For rigid parts (weapons, armor plates), bone parenting alone is sufficient.
        """
        if obj.type != 'MESH':
            return False
        
        mod = obj.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = armature
        mod.use_vertex_groups = True
        
        return True


class KitbashEquipper:
    """
    Equips semantic parts to character meshes.
    
    Uses DirectBoneParenting for proper bone attachment.
    """
    
    @staticmethod
    def create_primitive_mesh(mesh_data: Dict, name: str) -> bpy.types.Object:
        """Create a primitive mesh - delegates to DirectBoneParenting"""
        return DirectBoneParenting.create_primitive_at_origin(mesh_data, name)
    
    @staticmethod
    def find_armature() -> Optional[bpy.types.Object]:
        """Find the character armature in the scene"""
        return DirectBoneParenting.find_armature()
    
    @staticmethod
    def find_bone(armature, bone_name: str):
        """Find a bone in the armature"""
        return DirectBoneParenting.find_bone(armature, bone_name)
    
    @staticmethod
    def equip_part(
        part: SemanticPart,
        color: Tuple[float, float, float] = (0.5, 0.5, 0.5),
        style_preset: str = "stylized",
        auto_rig: bool = False
    ) -> Optional[bpy.types.Object]:
        """
        Equip a semantic part to the character.
        
        CRITICAL CHANGES from old implementation:
        1. Mesh is created at origin (not at world bone position)
        2. Immediately parented to bone with BONE parent type
        3. Offset/rotation are in bone-local space
        4. Part will NEVER float - it follows the bone
        
        Args:
            part: SemanticPart definition with socket info
            color: RGB color tuple for the part material
            style_preset: Style preset for shader system
            auto_rig: If True, add armature modifier for deformation
            
        Returns:
            The created mesh object, or None on failure
        """
        armature = DirectBoneParenting.find_armature()
        if not armature:
            AkkuLogger.warning("No armature found in scene")
            return None
        
        bone = DirectBoneParenting.find_bone(armature, part.socket.bone_name)
        if not bone:
            AkkuLogger.warning(f"Bone not found: {part.socket.bone_name}")
            return None
        
        obj = DirectBoneParenting.create_primitive_at_origin(part.mesh_data, part.name)
        
        socket = part.socket
        success = DirectBoneParenting.parent_to_bone(
            obj=obj,
            armature=armature,
            bone_name=socket.bone_name,
            offset=socket.offset,
            rotation=socket.rotation,
            scale=socket.scale
        )
        
        if not success:
            bpy.data.objects.remove(obj, do_unlink=True)
            return None
        
        StyleToGLBConverter.apply_style_as_glb(obj, color, style_preset)
        
        if auto_rig:
            DirectBoneParenting.add_armature_modifier(obj, armature)
        
        AkkuLogger.info(f"Equipped part: {part.name}", {
            "category": part.category,
            "style": part.style,
            "bone": part.socket.bone_name,
            "parenting": "BONE"
        })
        
        return obj
