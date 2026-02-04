"""
Akku SDK Shader - Material and Stylized Shader System
"""

import bpy
from typing import Tuple
from dataclasses import dataclass

from .core import AkkuLogger


class MaterialSystem:
    """PBR Material creation system"""
    
    @staticmethod
    def create_material(
        name: str,
        color: Tuple[float, float, float],
        metallic: float = 0.0,
        roughness: float = 0.5,
        emission: float = 0.0
    ) -> bpy.types.Material:
        """Create a PBR material"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        principled.inputs['Base Color'].default_value = (*color, 1.0)
        principled.inputs['Metallic'].default_value = metallic
        principled.inputs['Roughness'].default_value = roughness
        
        if emission > 0:
            for emission_input in ['Emission', 'Emission Color']:
                try:
                    principled.inputs[emission_input].default_value = (*color, 1.0)
                    break
                except KeyError:
                    continue
            
            try:
                principled.inputs['Emission Strength'].default_value = emission * 2.0
            except KeyError:
                pass
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        return mat
    
    @staticmethod
    def apply_material(obj, material: bpy.types.Material):
        """Apply material to object"""
        if obj.type != 'MESH':
            return
        
        obj.data.materials.clear()
        obj.data.materials.append(material)


@dataclass
class StylizedShaderParams:
    """Parameters for stylized low-poly shader"""
    base_color: Tuple[float, float, float] = (0.8, 0.2, 0.2)
    edge_brightness: float = 0.3
    cavity_darkness: float = 0.4
    ao_distance: float = 0.5
    metallic: float = 0.0
    roughness: float = 0.6
    emission_strength: float = 0.0
    use_fresnel: bool = True
    fresnel_strength: float = 0.2


class StylizedShaderSystem:
    """
    Akku Stylized Shader System
    
    Creates procedural materials optimized for low-poly characters:
    - Edge highlighting using Geometry (Pointiness) node
    - Cavity darkening using Ambient Occlusion
    - Optional fresnel rim lighting
    """
    
    @staticmethod
    def create_stylized_material(
        name: str,
        params: StylizedShaderParams = None
    ) -> bpy.types.Material:
        """Create Akku_Stylized_Shader material"""
        if params is None:
            params = StylizedShaderParams()
        
        mat_name = f"Akku_Stylized_{name}"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (800, 0)
        
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (500, 0)
        principled.inputs['Metallic'].default_value = params.metallic
        principled.inputs['Roughness'].default_value = params.roughness
        
        if params.emission_strength > 0:
            for emission_input in ['Emission', 'Emission Color']:
                try:
                    principled.inputs[emission_input].default_value = (*params.base_color, 1.0)
                    break
                except KeyError:
                    continue
            try:
                principled.inputs['Emission Strength'].default_value = params.emission_strength
            except KeyError:
                pass
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        base_color_node = nodes.new('ShaderNodeRGB')
        base_color_node.location = (-600, 200)
        base_color_node.outputs[0].default_value = (*params.base_color, 1.0)
        base_color_node.label = "Base Color"
        
        geometry = nodes.new('ShaderNodeNewGeometry')
        geometry.location = (-600, -100)
        
        edge_ramp = nodes.new('ShaderNodeValToRGB')
        edge_ramp.location = (-400, -100)
        edge_ramp.label = "Edge Ramp"
        edge_ramp.color_ramp.elements[0].position = 0.4
        edge_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        edge_ramp.color_ramp.elements[1].position = 0.6
        edge_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        links.new(geometry.outputs['Pointiness'], edge_ramp.inputs['Fac'])
        
        edge_color = nodes.new('ShaderNodeRGB')
        edge_color.location = (-400, 50)
        bright_factor = 1.0 + params.edge_brightness
        edge_color.outputs[0].default_value = (
            min(1.0, params.base_color[0] * bright_factor),
            min(1.0, params.base_color[1] * bright_factor),
            min(1.0, params.base_color[2] * bright_factor),
            1.0
        )
        edge_color.label = "Edge Highlight"
        
        edge_mix = nodes.new('ShaderNodeMixRGB')
        edge_mix.location = (-200, 100)
        edge_mix.blend_type = 'MIX'
        edge_mix.label = "Edge Mix"
        
        links.new(edge_ramp.outputs['Color'], edge_mix.inputs['Fac'])
        links.new(base_color_node.outputs[0], edge_mix.inputs['Color1'])
        links.new(edge_color.outputs[0], edge_mix.inputs['Color2'])
        
        ao = nodes.new('ShaderNodeAmbientOcclusion')
        ao.location = (-600, -350)
        ao.inputs['Distance'].default_value = params.ao_distance
        ao.samples = 16
        
        ao_ramp = nodes.new('ShaderNodeValToRGB')
        ao_ramp.location = (-400, -350)
        ao_ramp.label = "Cavity Ramp"
        ao_ramp.color_ramp.elements[0].position = 0.0
        ao_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ao_ramp.color_ramp.elements[1].position = 0.8
        ao_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        links.new(ao.outputs['AO'], ao_ramp.inputs['Fac'])
        
        cavity_color = nodes.new('ShaderNodeRGB')
        cavity_color.location = (-400, -200)
        dark_factor = 1.0 - params.cavity_darkness
        cavity_color.outputs[0].default_value = (
            params.base_color[0] * dark_factor,
            params.base_color[1] * dark_factor,
            params.base_color[2] * dark_factor,
            1.0
        )
        cavity_color.label = "Cavity Dark"
        
        cavity_mix = nodes.new('ShaderNodeMixRGB')
        cavity_mix.location = (0, 0)
        cavity_mix.blend_type = 'MIX'
        cavity_mix.label = "Cavity Mix"
        
        links.new(ao_ramp.outputs['Color'], cavity_mix.inputs['Fac'])
        links.new(cavity_color.outputs[0], cavity_mix.inputs['Color1'])
        links.new(edge_mix.outputs['Color'], cavity_mix.inputs['Color2'])
        
        if params.use_fresnel and params.fresnel_strength > 0:
            fresnel = nodes.new('ShaderNodeFresnel')
            fresnel.location = (-200, -200)
            fresnel.inputs['IOR'].default_value = 1.45
            
            rim_color = nodes.new('ShaderNodeRGB')
            rim_color.location = (0, -350)
            rim_color.outputs[0].default_value = (
                min(1.0, params.base_color[0] + 0.2),
                min(1.0, params.base_color[1] + 0.2),
                min(1.0, params.base_color[2] + 0.2),
                1.0
            )
            rim_color.label = "Rim Color"
            
            rim_multiply = nodes.new('ShaderNodeMixRGB')
            rim_multiply.location = (100, -280)
            rim_multiply.blend_type = 'MULTIPLY'
            rim_multiply.inputs['Fac'].default_value = 1.0
            rim_multiply.label = "Rim Multiply"
            
            links.new(fresnel.outputs['Fac'], rim_multiply.inputs['Color1'])
            links.new(rim_color.outputs[0], rim_multiply.inputs['Color2'])
            
            final_mix = nodes.new('ShaderNodeMixRGB')
            final_mix.location = (250, 0)
            final_mix.blend_type = 'ADD'
            final_mix.inputs['Fac'].default_value = params.fresnel_strength
            final_mix.label = "Fresnel Mix"
            
            links.new(cavity_mix.outputs['Color'], final_mix.inputs['Color1'])
            links.new(rim_multiply.outputs['Color'], final_mix.inputs['Color2'])
            
            links.new(final_mix.outputs['Color'], principled.inputs['Base Color'])
        else:
            links.new(cavity_mix.outputs['Color'], principled.inputs['Base Color'])
        
        AkkuLogger.info(f"Created stylized material: {mat_name}", {
            "edge_brightness": params.edge_brightness,
            "cavity_darkness": params.cavity_darkness,
            "use_fresnel": params.use_fresnel
        })
        
        return mat
    
    @staticmethod
    def apply_stylized_shader(
        obj,
        color: Tuple[float, float, float],
        style: str = "stylized"
    ) -> bpy.types.Material:
        """Apply stylized shader to object based on style preset"""
        style_presets = {
            "stylized": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.3,
                cavity_darkness=0.35,
                fresnel_strength=0.15
            ),
            "chibi": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.4,
                cavity_darkness=0.2,
                ao_distance=0.3,
                fresnel_strength=0.25,
                roughness=0.7
            ),
            "sd": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.35,
                cavity_darkness=0.25,
                fresnel_strength=0.2
            ),
            "heroic": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.45,
                cavity_darkness=0.4,
                ao_distance=0.6,
                fresnel_strength=0.2,
                roughness=0.5
            ),
            "cartoon": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.5,
                cavity_darkness=0.15,
                ao_distance=0.3,
                use_fresnel=False,
                roughness=0.8
            ),
            "realistic": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.15,
                cavity_darkness=0.25,
                ao_distance=0.4,
                fresnel_strength=0.1,
                roughness=0.55
            ),
            "mobile": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.2,
                cavity_darkness=0.2,
                use_fresnel=False,
                roughness=0.7
            ),
            "minifig": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.35,
                cavity_darkness=0.3,
                ao_distance=0.25,
                fresnel_strength=0.1,
                roughness=0.65
            )
        }
        
        params = style_presets.get(style, style_presets["stylized"])
        params.base_color = color
        
        mat = StylizedShaderSystem.create_stylized_material(obj.name, params)
        
        if obj.type == 'MESH':
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            AkkuLogger.info(f"Applied stylized shader to {obj.name}", {"style": style})
        
        return mat
