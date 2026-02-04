"""
Akku SDK Body - Direct Mesh Deformation with Export Freeze

CRITICAL: All body deformations must be BAKED into mesh data before export.
No modifiers, no lattices - direct vertex manipulation only.
"""

import bpy
import bmesh
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
from mathutils import Vector

from .core import AkkuLogger
from .mesh import MeshTools, UndoManager


@dataclass
class BodyTypeParams:
    """Body type parameters for character customization"""
    muscular: float = 0.0
    fat: float = 0.0
    height: float = 0.0
    shoulder_width: float = 0.0
    hip_width: float = 0.0
    leg_length: float = 0.0
    arm_length: float = 0.0
    head_size: float = 0.0


class BodyTypePresets:
    """Predefined body type configurations"""
    
    PRESETS: Dict[str, BodyTypeParams] = {
        "default": BodyTypeParams(),
        "muscular": BodyTypeParams(muscular=1.0, shoulder_width=0.8, fat=-0.2),
        "thin": BodyTypeParams(muscular=-0.6, fat=-0.5, shoulder_width=-0.4),
        "fat": BodyTypeParams(fat=1.0, muscular=-0.2, hip_width=0.6),
        "tall": BodyTypeParams(height=0.6, leg_length=0.4, arm_length=0.3),
        "short": BodyTypeParams(height=-0.5, leg_length=-0.3),
        "athletic": BodyTypeParams(muscular=0.7, fat=-0.4, shoulder_width=0.5, leg_length=0.2),
        "stocky": BodyTypeParams(height=-0.3, muscular=0.6, shoulder_width=0.5, fat=0.3),
        "slim": BodyTypeParams(muscular=-0.4, fat=-0.5, shoulder_width=-0.3, hip_width=-0.3),
        "heroic": BodyTypeParams(muscular=0.9, height=0.4, shoulder_width=0.7, hip_width=-0.2),
        "chibi": BodyTypeParams(height=-0.6, head_size=1.0, leg_length=-0.5, arm_length=-0.4),
        "giant": BodyTypeParams(height=1.0, muscular=0.6, shoulder_width=0.5),
    }
    
    KOREAN_ALIASES: Dict[str, str] = {
        "근육질": "muscular",
        "마른": "thin",
        "뚱뚱한": "fat",
        "키큰": "tall",
        "키작은": "short",
        "운동선수": "athletic",
        "땅딸막한": "stocky",
        "날씬한": "slim",
        "영웅": "heroic",
        "치비": "chibi",
        "거인": "giant",
    }
    
    @classmethod
    def get_preset(cls, name: str) -> BodyTypeParams:
        """Get body type preset by name (supports Korean)"""
        if name in cls.KOREAN_ALIASES:
            name = cls.KOREAN_ALIASES[name]
        return cls.PRESETS.get(name.lower(), cls.PRESETS["default"])
    
    @classmethod
    def detect_from_prompt(cls, prompt: str) -> BodyTypeParams:
        """Detect body type from prompt text"""
        prompt_lower = prompt.lower()
        
        for korean, english in cls.KOREAN_ALIASES.items():
            if korean in prompt_lower:
                AkkuLogger.info(f"Detected body type from prompt: {english}")
                return cls.get_preset(english)
        
        for preset_name in cls.PRESETS.keys():
            if preset_name in prompt_lower:
                AkkuLogger.info(f"Detected body type from prompt: {preset_name}")
                return cls.get_preset(preset_name)
        
        return cls.PRESETS["default"]


class DirectMeshDeformer:
    """
    Direct Mesh Deformation System
    
    CRITICAL DESIGN PRINCIPLE:
    All deformations are applied directly to mesh vertex data using bmesh.
    This ensures:
    1. Changes are permanently baked into the mesh
    2. No modifiers that might not export correctly
    3. Predictable results in any viewer/engine
    """
    
    BODY_ZONES = {
        "head": (0.85, 1.0),
        "neck": (0.78, 0.85),
        "shoulders": (0.70, 0.78),
        "chest": (0.55, 0.70),
        "waist": (0.45, 0.55),
        "hips": (0.35, 0.45),
        "upper_legs": (0.18, 0.35),
        "lower_legs": (0.0, 0.18),
    }
    
    ARM_X_THRESHOLD = 0.12
    
    @classmethod
    def deform_mesh(cls, obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """
        Apply body type deformation directly to mesh vertices.
        
        This method:
        1. Opens mesh in bmesh
        2. Applies all deformations to vertex positions
        3. Writes changes back to mesh data
        4. Mesh is now permanently deformed - no modifiers needed
        """
        if obj.type != 'MESH':
            AkkuLogger.warning(f"Cannot deform non-mesh object: {obj.name}")
            return False
        
        UndoManager.save_state(obj, "before_body_deform")
        
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            
            z_coords = [v.co.z for v in bm.verts]
            if not z_coords:
                bm.free()
                return False
            
            z_min, z_max = min(z_coords), max(z_coords)
            height = z_max - z_min
            
            if height <= 0.001:
                bm.free()
                AkkuLogger.warning("Mesh has zero height, skipping deformation")
                return False
            
            AkkuLogger.info("Applying direct mesh deformation", {
                "mesh": obj.name,
                "height": height,
                "params": asdict(params)
            })
            
            for vert in bm.verts:
                z_norm = (vert.co.z - z_min) / height
                x_abs = abs(vert.co.x)
                
                scale_x, scale_y, scale_z = 1.0, 1.0, 1.0
                offset_z = 0.0
                
                MIN_SCALE = 0.4
                MAX_SCALE = 2.0
                
                if params.height != 0:
                    offset_z = params.height * 0.25 * height * z_norm
                
                if z_norm > 0.85:
                    head_scale = 1.0 + params.head_size * 0.45
                    scale_x = head_scale
                    scale_y = head_scale
                    offset_z += params.head_size * 0.15 * height
                
                elif 0.70 < z_norm <= 0.85:
                    shoulder_scale = 1.0 + params.shoulder_width * 0.45 + params.muscular * 0.35
                    scale_x = shoulder_scale
                    scale_y = 1.0 + params.muscular * 0.30 + params.fat * 0.35
                
                elif 0.55 < z_norm <= 0.70:
                    chest_scale = 1.0 + params.muscular * 0.40 + params.fat * 0.45
                    scale_x = chest_scale
                    scale_y = chest_scale
                
                elif 0.45 < z_norm <= 0.55:
                    waist_scale = 1.0 - params.muscular * 0.20 + params.fat * 0.50
                    scale_x = waist_scale
                    scale_y = waist_scale
                
                elif 0.35 < z_norm <= 0.45:
                    hip_scale = 1.0 + params.hip_width * 0.40 + params.fat * 0.45
                    scale_x = hip_scale
                    scale_y = hip_scale
                
                elif z_norm <= 0.35:
                    if params.leg_length != 0:
                        leg_factor = 1.0 + params.leg_length * 0.40
                        new_z = z_min + (vert.co.z - z_min) * leg_factor
                        offset_z = new_z - vert.co.z
                    
                    leg_thickness = 1.0 + params.muscular * 0.28 + params.fat * 0.40
                    scale_x = leg_thickness
                    scale_y = leg_thickness
                
                if x_abs > cls.ARM_X_THRESHOLD and 0.50 < z_norm < 0.80:
                    if params.arm_length != 0:
                        arm_extend = params.arm_length * 0.30 * height
                        if vert.co.x > 0:
                            vert.co.x += arm_extend * 0.5
                        else:
                            vert.co.x -= arm_extend * 0.5
                    
                    arm_scale = 1.0 + params.muscular * 0.35 + params.fat * 0.28
                    scale_y = arm_scale
                
                scale_x = max(MIN_SCALE, min(MAX_SCALE, scale_x))
                scale_y = max(MIN_SCALE, min(MAX_SCALE, scale_y))
                
                vert.co.x *= scale_x
                vert.co.y *= scale_y
                vert.co.z += offset_z
            
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.data.update()
            
            AkkuLogger.info(f"Direct mesh deformation completed: {obj.name}")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Mesh deformation failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @classmethod
    def apply_all_modifiers(cls, obj: bpy.types.Object) -> bool:
        """
        Apply (freeze) all modifiers to mesh data.
        
        CRITICAL: This must be called before export to ensure
        all deformations are baked into the mesh.
        """
        if obj.type != 'MESH':
            return False
        
        if not obj.modifiers:
            return True
        
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            mesh_eval = bpy.data.meshes.new_from_object(obj_eval)
            
            old_mesh = obj.data
            obj.data = mesh_eval
            
            bpy.data.meshes.remove(old_mesh)
            
            obj.modifiers.clear()
            
            AkkuLogger.info(f"Applied all modifiers to {obj.name}")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to apply modifiers: {str(e)}")
            return False
    
    @classmethod
    def apply_transform(cls, obj: bpy.types.Object) -> bool:
        """
        Bake object transforms (location, rotation, scale) into mesh data.
        
        After this, object will have:
        - Location: (0, 0, 0)
        - Rotation: (0, 0, 0)
        - Scale: (1, 1, 1)
        
        But the mesh vertices will be transformed accordingly.
        """
        if obj.type != 'MESH':
            return False
        
        try:
            matrix = obj.matrix_world.copy()
            
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            for vert in bm.verts:
                vert.co = matrix @ vert.co
            
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.matrix_world = obj.matrix_world.identity()
            obj.location = (0, 0, 0)
            obj.rotation_euler = (0, 0, 0)
            obj.scale = (1, 1, 1)
            
            obj.data.update()
            
            AkkuLogger.info(f"Applied transform to {obj.name}")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to apply transform: {str(e)}")
            return False


class BodyTypeSystem:
    """
    Body Type System - Public API
    
    This is the main interface for body type deformation.
    All deformations are done via DirectMeshDeformer.
    """
    
    @classmethod
    def apply_body_type(
        cls,
        obj: bpy.types.Object,
        params: BodyTypeParams,
        use_lattice: bool = False
    ) -> bool:
        """
        Apply body type deformation to mesh.
        
        Args:
            obj: Mesh object to deform
            params: Body type parameters
            use_lattice: IGNORED - always uses direct mesh deformation
            
        Returns:
            True if successful
        """
        return DirectMeshDeformer.deform_mesh(obj, params)
    
    @classmethod
    def apply_body_type_direct(cls, obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """Alias for apply_body_type - backward compatibility"""
        return DirectMeshDeformer.deform_mesh(obj, params)
    
    @classmethod
    def freeze_for_export(cls, objects: List[bpy.types.Object]) -> int:
        """
        Prepare all objects for GLB export by freezing transforms and modifiers.
        
        Returns:
            Number of objects processed
        """
        count = 0
        for obj in objects:
            if obj.type == 'MESH':
                DirectMeshDeformer.apply_all_modifiers(obj)
                count += 1
        
        AkkuLogger.info(f"Frozen {count} objects for export")
        return count
