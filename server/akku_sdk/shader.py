"""
Akku SDK Shader - GLB Standard Material System (Direct Data Manipulation)

CRITICAL: GLB only exports Principled BSDF with limited inputs:
- Base Color, Metallic, Roughness, Emission, Alpha
- Complex nodes (Pointiness, AO, Fresnel) DO NOT EXPORT

This module uses ONLY GLB-compatible materials.
"""

import bpy
from typing import Tuple, Optional
from dataclasses import dataclass

from .core import AkkuLogger


@dataclass
class GLBMaterialParams:
    """GLB-compatible material parameters"""
    base_color: Tuple[float, float, float] = (0.8, 0.2, 0.2)
    metallic: float = 0.0
    roughness: float = 0.5
    emission_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    emission_strength: float = 0.0
    alpha: float = 1.0


class GLBMaterialSystem:
    """
    GLB Standard Material System
    
    Creates ONLY Principled BSDF materials that export correctly to GLB.
    No complex shader nodes that would be lost on export.
    """
    
    @staticmethod
    def create_glb_material(
        name: str,
        params: GLBMaterialParams = None
    ) -> bpy.types.Material:
        """
        Create a GLB-compatible Principled BSDF material.
        
        This material will export correctly and display properly in:
        - Three.js / Babylon.js
        - Unity
        - Unreal Engine
        - Any glTF 2.0 viewer
        """
        if params is None:
            params = GLBMaterialParams()
        
        mat_name = f"Akku_GLB_{name}"
        
        if mat_name in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[mat_name])
        
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        principled.inputs['Base Color'].default_value = (*params.base_color, 1.0)
        principled.inputs['Metallic'].default_value = params.metallic
        principled.inputs['Roughness'].default_value = params.roughness
        principled.inputs['Alpha'].default_value = params.alpha
        
        if params.emission_strength > 0:
            try:
                principled.inputs['Emission Color'].default_value = (*params.emission_color, 1.0)
                principled.inputs['Emission Strength'].default_value = params.emission_strength
            except (KeyError, TypeError):
                try:
                    principled.inputs['Emission'].default_value = (*params.emission_color, 1.0)
                except (KeyError, TypeError):
                    pass
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        if params.alpha < 1.0:
            mat.blend_method = 'BLEND'
            mat.shadow_method = 'CLIP'
        
        AkkuLogger.info(f"Created GLB material: {mat_name}", {
            "base_color": params.base_color,
            "metallic": params.metallic,
            "roughness": params.roughness
        })
        
        return mat
    
    @staticmethod
    def apply_glb_material(obj, material: bpy.types.Material):
        """Apply GLB material to object"""
        if obj.type != 'MESH':
            return
        
        obj.data.materials.clear()
        obj.data.materials.append(material)


class StyleToGLBConverter:
    """
    Convert style presets to GLB-compatible material parameters.
    
    Since we can't use complex shading, we adjust base color, metallic,
    and roughness to approximate the visual style.
    """
    
    STYLE_PARAMS = {
        "stylized": GLBMaterialParams(
            metallic=0.0,
            roughness=0.7,
        ),
        "chibi": GLBMaterialParams(
            metallic=0.0,
            roughness=0.8,
        ),
        "sd": GLBMaterialParams(
            metallic=0.0,
            roughness=0.75,
        ),
        "heroic": GLBMaterialParams(
            metallic=0.3,
            roughness=0.5,
        ),
        "cartoon": GLBMaterialParams(
            metallic=0.0,
            roughness=0.9,
        ),
        "realistic": GLBMaterialParams(
            metallic=0.1,
            roughness=0.55,
        ),
        "mobile": GLBMaterialParams(
            metallic=0.0,
            roughness=0.8,
        ),
        "minifig": GLBMaterialParams(
            metallic=0.2,
            roughness=0.65,
        ),
        "scifi": GLBMaterialParams(
            metallic=0.7,
            roughness=0.3,
        ),
        "knight": GLBMaterialParams(
            metallic=0.8,
            roughness=0.35,
        ),
        "magic": GLBMaterialParams(
            metallic=0.1,
            roughness=0.6,
            emission_strength=0.3,
        ),
    }
    
    @classmethod
    def get_params_for_style(
        cls,
        style: str,
        base_color: Tuple[float, float, float]
    ) -> GLBMaterialParams:
        """Get GLB material params for a style, with custom base color"""
        template = cls.STYLE_PARAMS.get(style, cls.STYLE_PARAMS["stylized"])
        
        return GLBMaterialParams(
            base_color=base_color,
            metallic=template.metallic,
            roughness=template.roughness,
            emission_color=base_color if template.emission_strength > 0 else (0, 0, 0),
            emission_strength=template.emission_strength,
            alpha=template.alpha,
        )
    
    @classmethod
    def apply_style_as_glb(
        cls,
        obj,
        color: Tuple[float, float, float],
        style: str = "stylized"
    ) -> bpy.types.Material:
        """Apply a style as a GLB-compatible material"""
        params = cls.get_params_for_style(style, color)
        mat = GLBMaterialSystem.create_glb_material(obj.name, params)
        GLBMaterialSystem.apply_glb_material(obj, mat)
        
        AkkuLogger.info(f"Applied GLB material to {obj.name}", {
            "style": style,
            "metallic": params.metallic,
            "roughness": params.roughness
        })
        
        return mat


class StylizedShaderSystem:
    """
    DEPRECATED: Complex shader system.
    Now redirects to GLB-compatible materials.
    
    Kept for backward compatibility.
    """
    
    @staticmethod
    def apply_stylized_shader(
        obj,
        color: Tuple[float, float, float],
        style: str = "stylized"
    ) -> bpy.types.Material:
        """Apply GLB-compatible material (replaces complex shader)"""
        return StyleToGLBConverter.apply_style_as_glb(obj, color, style)
    
    @staticmethod
    def create_stylized_material(name: str, params=None) -> bpy.types.Material:
        """Create GLB-compatible material (replaces complex shader)"""
        if params is None:
            glb_params = GLBMaterialParams()
        else:
            glb_params = GLBMaterialParams(
                base_color=getattr(params, 'base_color', (0.8, 0.2, 0.2)),
                metallic=getattr(params, 'metallic', 0.0),
                roughness=getattr(params, 'roughness', 0.5),
            )
        return GLBMaterialSystem.create_glb_material(name, glb_params)


class MaterialSystem:
    """Simple PBR Material system - redirects to GLB system"""
    
    @staticmethod
    def create_material(
        name: str,
        color: Tuple[float, float, float],
        metallic: float = 0.0,
        roughness: float = 0.5,
        emission: float = 0.0
    ) -> bpy.types.Material:
        """Create a GLB-compatible PBR material"""
        params = GLBMaterialParams(
            base_color=color,
            metallic=metallic,
            roughness=roughness,
            emission_color=color if emission > 0 else (0, 0, 0),
            emission_strength=emission,
        )
        return GLBMaterialSystem.create_glb_material(name, params)
    
    @staticmethod
    def apply_material(obj, material: bpy.types.Material):
        """Apply material to object"""
        GLBMaterialSystem.apply_glb_material(obj, material)
