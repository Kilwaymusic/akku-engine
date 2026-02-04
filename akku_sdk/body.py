"""
Akku SDK Body - Body Type System with Lattice/Vertex Deformation
"""

import bpy
import bmesh
from typing import Dict, Tuple, Optional
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
        "muscular": BodyTypeParams(muscular=0.8, shoulder_width=0.5, fat=-0.2),
        "thin": BodyTypeParams(muscular=-0.6, fat=-0.5, shoulder_width=-0.3),
        "fat": BodyTypeParams(fat=0.7, muscular=-0.2, hip_width=0.4),
        "tall": BodyTypeParams(height=0.5, leg_length=0.3, arm_length=0.2),
        "short": BodyTypeParams(height=-0.4, leg_length=-0.2),
        "athletic": BodyTypeParams(muscular=0.5, fat=-0.3, shoulder_width=0.3, leg_length=0.1),
        "stocky": BodyTypeParams(height=-0.2, muscular=0.4, shoulder_width=0.4, fat=0.2),
        "slim": BodyTypeParams(muscular=-0.3, fat=-0.4, shoulder_width=-0.2, hip_width=-0.2),
        "heroic": BodyTypeParams(muscular=0.6, height=0.3, shoulder_width=0.5, hip_width=-0.1),
        "chibi": BodyTypeParams(height=-0.5, head_size=0.8, leg_length=-0.4, arm_length=-0.3),
        "giant": BodyTypeParams(height=0.8, muscular=0.4, shoulder_width=0.3),
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


class BodyTypeSystem:
    """Body type deformation system using Lattice and vertex manipulation."""
    
    BODY_REGIONS = {
        "head": {"z_min": 1.5, "z_max": 1.85, "scale_axes": "XYZ"},
        "neck": {"z_min": 1.4, "z_max": 1.5, "scale_axes": "XY"},
        "shoulders": {"z_min": 1.25, "z_max": 1.4, "scale_axes": "X"},
        "chest": {"z_min": 1.0, "z_max": 1.25, "scale_axes": "XYZ"},
        "waist": {"z_min": 0.85, "z_max": 1.0, "scale_axes": "XY"},
        "hips": {"z_min": 0.7, "z_max": 0.85, "scale_axes": "XY"},
        "upper_legs": {"z_min": 0.4, "z_max": 0.7, "scale_axes": "XYZ"},
        "lower_legs": {"z_min": 0.0, "z_max": 0.4, "scale_axes": "XYZ"},
    }
    
    ARM_X_THRESHOLD = 0.15
    ARM_Z_RANGE = (0.9, 1.4)
    
    @classmethod
    def create_lattice_for_mesh(cls, obj: bpy.types.Object, resolution: Tuple[int, int, int] = (4, 4, 6)) -> bpy.types.Object:
        """Create a lattice object that encompasses the mesh."""
        if obj.type != 'MESH':
            return None
        
        min_co, max_co, _ = MeshTools.get_mesh_bounds(obj)
        
        padding = 0.05
        size = (
            (max_co.x - min_co.x) + padding * 2,
            (max_co.y - min_co.y) + padding * 2,
            (max_co.z - min_co.z) + padding * 2
        )
        center = (
            (min_co.x + max_co.x) / 2,
            (min_co.y + max_co.y) / 2,
            (min_co.z + max_co.z) / 2
        )
        
        lattice_data = bpy.data.lattices.new(name="AkkuBodyLattice")
        lattice_data.points_u = resolution[0]
        lattice_data.points_v = resolution[1]
        lattice_data.points_w = resolution[2]
        lattice_data.interpolation_type_u = 'KEY_BSPLINE'
        lattice_data.interpolation_type_v = 'KEY_BSPLINE'
        lattice_data.interpolation_type_w = 'KEY_BSPLINE'
        
        lattice_obj = bpy.data.objects.new("AkkuBodyLattice", lattice_data)
        bpy.context.collection.objects.link(lattice_obj)
        
        lattice_obj.location = Vector(center)
        lattice_obj.scale = Vector(size)
        
        mod = obj.modifiers.new(name="AkkuLattice", type='LATTICE')
        mod.object = lattice_obj
        
        AkkuLogger.info("Created lattice for body deformation", {
            "resolution": resolution,
            "size": size
        })
        
        return lattice_obj
    
    @classmethod
    def deform_lattice(cls, lattice_obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """Deform lattice points based on body type parameters."""
        if lattice_obj.type != 'LATTICE':
            return False
        
        lattice = lattice_obj.data
        points_u = lattice.points_u
        points_v = lattice.points_v
        points_w = lattice.points_w
        
        AkkuLogger.info("Deforming lattice", {
            "muscular": params.muscular,
            "fat": params.fat,
            "height": params.height
        })
        
        for i, point in enumerate(lattice.points):
            w_idx = i // (points_u * points_v)
            remaining = i % (points_u * points_v)
            v_idx = remaining // points_u
            u_idx = remaining % points_u
            
            u_norm = u_idx / max(1, points_u - 1)
            v_norm = v_idx / max(1, points_v - 1)
            w_norm = w_idx / max(1, points_w - 1)
            
            dx, dy, dz = 0.0, 0.0, 0.0
            
            if params.height != 0:
                dz = params.height * 0.4 * w_norm
            
            body_width_factor = params.muscular * 0.5 + params.fat * 0.4
            
            if 0.55 < w_norm < 0.8:
                shoulder_factor = params.shoulder_width * 0.5
                dx = (u_norm - 0.5) * (body_width_factor + shoulder_factor)
                dy = (v_norm - 0.5) * body_width_factor * 0.7
            
            elif 0.45 < w_norm <= 0.55:
                waist_factor = -params.muscular * 0.2 + params.fat * 0.3
                dx = (u_norm - 0.5) * waist_factor
                dy = (v_norm - 0.5) * waist_factor
            
            elif 0.35 < w_norm <= 0.45:
                hip_factor = params.hip_width * 0.3 + params.fat * 0.25
                dx = (u_norm - 0.5) * hip_factor
                dy = (v_norm - 0.5) * hip_factor
            
            elif w_norm <= 0.35:
                leg_scale = params.leg_length * 0.3
                dz = leg_scale * w_norm
                leg_width = (params.muscular * 0.2 + params.fat * 0.06) * (1 - w_norm)
                dx = (u_norm - 0.5) * leg_width
                dy = (v_norm - 0.5) * leg_width
            
            elif w_norm > 0.85:
                head_scale = params.head_size * 0.25
                dx = (u_norm - 0.5) * head_scale
                dy = (v_norm - 0.5) * head_scale
                dz += head_scale * 0.5
            
            point.co_deform.x += dx
            point.co_deform.y += dy
            point.co_deform.z += dz
        
        return True
    
    @classmethod
    def apply_body_type_direct(cls, obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """Apply body type deformation directly to mesh vertices."""
        if obj.type != 'MESH':
            return False
        
        UndoManager.save_state(obj, "before_body_type")
        
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            z_coords = [v.co.z for v in bm.verts]
            z_min, z_max = min(z_coords), max(z_coords)
            height = z_max - z_min
            
            if height <= 0:
                bm.free()
                return False
            
            AkkuLogger.info("Applying body type directly", {
                "mesh_height": height,
                "params": asdict(params)
            })
            
            for vert in bm.verts:
                z_norm = (vert.co.z - z_min) / height
                x_dist = abs(vert.co.x)
                
                dx, dy, dz = 0.0, 0.0, 0.0
                
                if params.height != 0:
                    dz = params.height * 0.4 * height * z_norm
                
                if z_norm > 0.85:
                    scale = 1.0 + params.head_size * 0.15
                    vert.co.x *= scale
                    vert.co.y *= scale
                    dz += params.head_size * 0.05 * height
                    
                elif 0.7 < z_norm <= 0.85:
                    shoulder_scale = 1.0 + params.shoulder_width * 0.52 + params.muscular * 0.08
                    vert.co.x *= shoulder_scale
                    vert.co.y *= 1.0 + params.muscular * 0.2 + params.fat * 0.06
                    
                elif 0.55 < z_norm <= 0.7:
                    chest_scale = 1.0 + params.muscular * 0.1 + params.fat * 0.25
                    vert.co.x *= chest_scale
                    vert.co.y *= chest_scale
                    
                elif 0.45 < z_norm <= 0.55:
                    waist_scale = 1.0 - params.muscular * 0.08 + params.fat * 0.32
                    vert.co.x *= waist_scale
                    vert.co.y *= waist_scale
                    
                elif 0.35 < z_norm <= 0.45:
                    hip_scale = 1.0 + params.hip_width * 0.1 + params.fat * 0.25
                    vert.co.x *= hip_scale
                    vert.co.y *= hip_scale
                    
                elif z_norm <= 0.35:
                    if params.leg_length != 0:
                        leg_factor = 1.0 + params.leg_length * 0.35
                        vert.co.z = z_min + (vert.co.z - z_min) * leg_factor
                    
                    leg_thickness = 1.0 + params.muscular * 0.06 + params.fat * 0.25
                    vert.co.x *= leg_thickness
                    vert.co.y *= leg_thickness
                
                if x_dist > 0.1 and 0.5 < z_norm < 0.8:
                    if params.arm_length != 0:
                        arm_extend = params.arm_length * 0.1 * height
                        if vert.co.x > 0:
                            vert.co.x += arm_extend * 0.3
                        else:
                            vert.co.x -= arm_extend * 0.3
                    
                    arm_scale = 1.0 + params.muscular * 0.5 + params.fat * 0.06
                    vert.co.y *= arm_scale
                
                vert.co.z += dz
            
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
            
            AkkuLogger.info("Body type deformation completed")
            
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Body type deformation failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @classmethod
    def apply_body_type(cls, obj: bpy.types.Object, params: BodyTypeParams, use_lattice: bool = False) -> bool:
        """Apply body type deformation to mesh."""
        if use_lattice:
            lattice = cls.create_lattice_for_mesh(obj, resolution=(4, 4, 8))
            if lattice:
                cls.deform_lattice(lattice, params)
                MeshTools.apply_modifier_via_depsgraph(obj, "AkkuLattice")
                bpy.data.objects.remove(lattice, do_unlink=True)
                return True
            return False
        else:
            return cls.apply_body_type_direct(obj, params)
