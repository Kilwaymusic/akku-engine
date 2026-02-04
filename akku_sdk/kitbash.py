"""
Akku SDK Kitbash - Semantic Component Library for Equipment
"""

import bpy
import bmesh
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from mathutils import Vector, Euler

from .core import AkkuLogger
from .shader import StylizedShaderSystem
from .rigging import AutoWeightTransfer


@dataclass
class SocketInfo:
    bone_name: str
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0


@dataclass
class SemanticPart:
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
    BONE_SOCKETS = {
        "head": "mixamorig:Head", "neck": "mixamorig:Neck", "chest": "mixamorig:Spine2",
        "spine": "mixamorig:Spine1", "hips": "mixamorig:Hips",
        "left_shoulder": "mixamorig:LeftShoulder", "right_shoulder": "mixamorig:RightShoulder",
        "left_arm": "mixamorig:LeftArm", "right_arm": "mixamorig:RightArm",
        "left_forearm": "mixamorig:LeftForeArm", "right_forearm": "mixamorig:RightForeArm",
        "left_hand": "mixamorig:LeftHand", "right_hand": "mixamorig:RightHand",
        "left_leg": "mixamorig:LeftUpLeg", "right_leg": "mixamorig:RightUpLeg",
        "left_foot": "mixamorig:LeftFoot", "right_foot": "mixamorig:RightFoot",
    }
    CATEGORY_TAXONOMY = {
        "armor": ["helmet", "shoulder", "chest", "boots", "gauntlet"],
        "weapons": ["weapon", "shield"], "accessories": ["accessory"],
        "full_set": ["helmet", "shoulder", "chest", "boots", "gauntlet", "weapon", "shield"],
    }
    _parts: Dict[str, SemanticPart] = {}
    
    @classmethod
    def _init_library(cls):
        if cls._parts:
            return
        cls._parts["Knight_Helmet"] = SemanticPart(name="Knight_Helmet", category="helmet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, 0, 0.08), scale=0.12),
            mesh_data={"type": "uv_sphere", "segments": 8, "rings": 6}, tags=["knight", "heavy"])
        cls._parts["SciFi_Helmet"] = SemanticPart(name="SciFi_Helmet", category="helmet", style="scifi",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["head"], offset=(0, 0.02, 0.06), rotation=(15, 0, 0), scale=0.11),
            mesh_data={"type": "cube", "size": 1.0}, tags=["scifi", "tech"])
        cls._parts["Knight_Shoulder_L"] = SemanticPart(name="Knight_Shoulder_L", category="shoulder", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_shoulder"], offset=(0.08, 0, 0.02), rotation=(0, 0, -15), scale=0.08),
            mesh_data={"type": "uv_sphere", "segments": 6, "rings": 4}, tags=["knight", "left"])
        cls._parts["Knight_Shoulder_R"] = SemanticPart(name="Knight_Shoulder_R", category="shoulder", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_shoulder"], offset=(-0.08, 0, 0.02), rotation=(0, 0, 15), scale=0.08),
            mesh_data={"type": "uv_sphere", "segments": 6, "rings": 4}, tags=["knight", "right"])
        cls._parts["Knight_Chestplate"] = SemanticPart(name="Knight_Chestplate", category="chest", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["chest"], offset=(0, 0.08, 0), scale=0.15),
            mesh_data={"type": "cube", "size": 1.0}, tags=["knight", "plate"])
        cls._parts["Heavy_Boots_L"] = SemanticPart(name="Heavy_Boots_L", category="boots", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_foot"], offset=(0, 0, -0.02), scale=0.06),
            mesh_data={"type": "cube", "size": 1.0}, tags=["boots", "left"])
        cls._parts["Heavy_Boots_R"] = SemanticPart(name="Heavy_Boots_R", category="boots", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_foot"], offset=(0, 0, -0.02), scale=0.06),
            mesh_data={"type": "cube", "size": 1.0}, tags=["boots", "right"])
        cls._parts["Knight_Gauntlet_L"] = SemanticPart(name="Knight_Gauntlet_L", category="gauntlet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_forearm"], scale=0.04),
            mesh_data={"type": "cylinder", "vertices": 6, "radius": 0.6, "depth": 1.5}, tags=["gauntlet", "left"])
        cls._parts["Knight_Gauntlet_R"] = SemanticPart(name="Knight_Gauntlet_R", category="gauntlet", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_forearm"], scale=0.04),
            mesh_data={"type": "cylinder", "vertices": 6, "radius": 0.6, "depth": 1.5}, tags=["gauntlet", "right"])
        cls._parts["Knight_Sword"] = SemanticPart(name="Knight_Sword", category="weapon", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_hand"], offset=(0, 0.05, 0), rotation=(90, 0, 0), scale=0.08),
            mesh_data={"type": "cube", "size": 1.0}, tags=["sword", "weapon"])
        cls._parts["Knight_Shield"] = SemanticPart(name="Knight_Shield", category="shield", style="heavy",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["left_forearm"], offset=(0.05, 0.03, 0), rotation=(0, 90, 0), scale=0.1),
            mesh_data={"type": "cube", "size": 1.0}, tags=["shield", "defense"])
        cls._parts["Staff"] = SemanticPart(name="Staff", category="weapon", style="magic",
            socket=SocketInfo(bone_name=cls.BONE_SOCKETS["right_hand"], offset=(0, 0.08, 0), scale=0.03),
            mesh_data={"type": "cylinder", "vertices": 6, "radius": 0.15, "depth": 4.0}, tags=["staff", "magic"])
        AkkuLogger.info(f"Kitbash library initialized with {len(cls._parts)} parts")
    
    @classmethod
    def get_part(cls, name: str) -> Optional[SemanticPart]:
        cls._init_library()
        return cls._parts.get(name)
    
    @classmethod
    def query_parts(cls, category: str = None, style: str = None, tags: List[str] = None) -> List[SemanticPart]:
        cls._init_library()
        results = list(cls._parts.values())
        if category:
            if category in cls.CATEGORY_TAXONOMY:
                results = [p for p in results if p.category in cls.CATEGORY_TAXONOMY[category]]
            else:
                results = [p for p in results if p.category == category]
        if style:
            results = [p for p in results if p.style == style]
        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]
        return results
    
    @classmethod
    def get_equipment_set(cls, style: str) -> Dict[str, List[SemanticPart]]:
        cls._init_library()
        equipment = {}
        for cat in ["helmet", "shoulder", "chest", "boots", "gauntlet", "weapon", "shield"]:
            parts = cls.query_parts(category=cat, style=style)
            if parts:
                equipment[cat] = parts
        return equipment
    
    @classmethod
    def list_categories(cls) -> List[str]:
        cls._init_library()
        return list(set(p.category for p in cls._parts.values()))
    
    @classmethod
    def list_styles(cls) -> List[str]:
        cls._init_library()
        return list(set(p.style for p in cls._parts.values()))


class KitbashEquipper:
    @staticmethod
    def create_primitive_mesh(mesh_data: Dict, name: str) -> bpy.types.Object:
        mesh_type = mesh_data.get("type", "cube")
        mesh = bpy.data.meshes.new(name=f"{name}_mesh")
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        bpy.context.scene.collection.objects.link(obj)
        bm = bmesh.new()
        if mesh_type == "cube":
            bmesh.ops.create_cube(bm, size=mesh_data.get("size", 1.0) / 2)
        elif mesh_type == "uv_sphere":
            bmesh.ops.create_uvsphere(bm, u_segments=mesh_data.get("segments", 8), v_segments=mesh_data.get("rings", 6), radius=0.5)
        elif mesh_type == "cylinder":
            bmesh.ops.create_cone(bm, segments=mesh_data.get("vertices", 8), radius1=mesh_data.get("radius", 0.5), radius2=mesh_data.get("radius", 0.5), depth=mesh_data.get("depth", 1.0), cap_ends=True)
        elif mesh_type == "cone":
            bmesh.ops.create_cone(bm, segments=mesh_data.get("vertices", 8), radius1=mesh_data.get("radius1", 1.0), radius2=0, depth=mesh_data.get("depth", 1.0), cap_ends=True)
        else:
            bmesh.ops.create_cube(bm, size=0.5)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return obj
    
    @staticmethod
    def find_armature() -> Optional[bpy.types.Object]:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        return None
    
    @staticmethod
    def find_bone(armature, bone_name: str):
        if armature and armature.type == 'ARMATURE':
            return armature.pose.bones.get(bone_name)
        return None
    
    @staticmethod
    def equip_part(part: SemanticPart, color: Tuple[float, float, float] = (0.5, 0.5, 0.5), style_preset: str = "stylized", auto_rig: bool = True) -> Optional[bpy.types.Object]:
        armature = KitbashEquipper.find_armature()
        if not armature:
            return None
        bone = KitbashEquipper.find_bone(armature, part.socket.bone_name)
        if not bone:
            return None
        obj = KitbashEquipper.create_primitive_mesh(part.mesh_data, part.name)
        socket = part.socket
        bone_matrix = armature.matrix_world @ bone.matrix
        socket_rot = Euler((math.radians(socket.rotation[0]), math.radians(socket.rotation[1]), math.radians(socket.rotation[2])), 'XYZ')
        bone_rot = bone_matrix.to_euler()
        obj.location = bone_matrix.to_translation() + bone_matrix.to_3x3() @ Vector(socket.offset)
        obj.rotation_euler = Euler((bone_rot.x + socket_rot.x, bone_rot.y + socket_rot.y, bone_rot.z + socket_rot.z), 'XYZ')
        obj.scale = (socket.scale, socket.scale, socket.scale)
        obj.parent = armature
        obj.parent_type = 'BONE'
        obj.parent_bone = part.socket.bone_name
        StylizedShaderSystem.apply_stylized_shader(obj, color, style_preset)
        if auto_rig:
            result = AutoWeightTransfer.auto_rig_part(obj, apply_transfer=True)
        AkkuLogger.info(f"Equipped part: {part.name}", {"category": part.category, "bone": part.socket.bone_name})
        return obj
