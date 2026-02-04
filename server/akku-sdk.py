"""
Akku SDK - Low-Poly Character Modeling Toolkit for Blender
Advanced procedural character generation with style-based modifications
"""

import bpy
import bmesh
import math
import sys
import os
import json
import re
from mathutils import Vector, Color

# ========================================
# AKKU SDK CORE CONFIGURATION
# ========================================

AKKU_CONFIG = {
    "base_meshes": {
        "male": "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx",
        "female": "/home/composerkil/akku-engine/assets/base_meshes/X_Bot.fbx"
    },
    "output_dir": "/home/composerkil/akku-engine/outputs"
}

# Proportion type configurations
PROPORTION_TYPES = {
    "stylized": {"scale": 1.0, "head_scale": 1.0, "limb_scale": 1.0, "body_style": "balanced"},
    "chibi": {"scale": 0.7, "head_scale": 1.8, "limb_scale": 0.7, "body_style": "cute"},
    "sd": {"scale": 0.7, "head_scale": 1.6, "limb_scale": 0.8, "body_style": "deformed"},
    "mobile": {"scale": 0.8, "head_scale": 1.2, "limb_scale": 0.9, "body_style": "simple"},
    "minifig": {"scale": 0.6, "head_scale": 1.4, "limb_scale": 0.6, "body_style": "blocky"},
    "cartoon": {"scale": 0.9, "head_scale": 1.3, "limb_scale": 0.95, "body_style": "expressive"},
    "realistic": {"scale": 1.0, "head_scale": 1.0, "limb_scale": 1.0, "body_style": "anatomical"}
}

# Polygon level targets
POLY_LEVELS = {
    "ultra_low": {"target_ratio": 0.1, "decimate_ratio": 0.15, "max_tris": 300},
    "low": {"target_ratio": 0.25, "decimate_ratio": 0.3, "max_tris": 800},
    "medium": {"target_ratio": 0.5, "decimate_ratio": 0.5, "max_tris": 1500},
    "high": {"target_ratio": 0.8, "decimate_ratio": 0.75, "max_tris": 3000}
}

# Color mappings (Korean + English)
COLOR_MAP = {
    # Korean colors
    "빨강": (1.0, 0.1, 0.1), "빨간": (1.0, 0.1, 0.1), "레드": (1.0, 0.1, 0.1),
    "파랑": (0.1, 0.3, 1.0), "파란": (0.1, 0.3, 1.0), "블루": (0.1, 0.3, 1.0),
    "초록": (0.1, 0.8, 0.2), "녹색": (0.1, 0.8, 0.2), "그린": (0.1, 0.8, 0.2),
    "노랑": (1.0, 0.9, 0.1), "노란": (1.0, 0.9, 0.1), "옐로우": (1.0, 0.9, 0.1),
    "주황": (1.0, 0.5, 0.0), "오렌지": (1.0, 0.5, 0.0),
    "보라": (0.6, 0.2, 0.8), "퍼플": (0.6, 0.2, 0.8),
    "분홍": (1.0, 0.5, 0.7), "핑크": (1.0, 0.5, 0.7),
    "검정": (0.05, 0.05, 0.05), "검은": (0.05, 0.05, 0.05), "블랙": (0.05, 0.05, 0.05),
    "흰": (0.95, 0.95, 0.95), "하얀": (0.95, 0.95, 0.95), "화이트": (0.95, 0.95, 0.95),
    "회색": (0.5, 0.5, 0.5), "그레이": (0.5, 0.5, 0.5),
    "금색": (0.9, 0.7, 0.2), "골드": (0.9, 0.7, 0.2),
    "은색": (0.8, 0.8, 0.85), "실버": (0.8, 0.8, 0.85),
    "갈색": (0.4, 0.25, 0.1), "브라운": (0.4, 0.25, 0.1),
    "청록": (0.0, 0.8, 0.8), "시안": (0.0, 0.8, 0.8),
    "메탈릭": (0.6, 0.6, 0.7),
    # English colors
    "red": (1.0, 0.1, 0.1), "blue": (0.1, 0.3, 1.0), "green": (0.1, 0.8, 0.2),
    "yellow": (1.0, 0.9, 0.1), "orange": (1.0, 0.5, 0.0), "purple": (0.6, 0.2, 0.8),
    "pink": (1.0, 0.5, 0.7), "black": (0.05, 0.05, 0.05), "white": (0.95, 0.95, 0.95),
    "gray": (0.5, 0.5, 0.5), "grey": (0.5, 0.5, 0.5), "gold": (0.9, 0.7, 0.2),
    "silver": (0.8, 0.8, 0.85), "brown": (0.4, 0.25, 0.1), "cyan": (0.0, 0.8, 0.8),
    "metallic": (0.6, 0.6, 0.7)
}

# Character archetypes for style detection
ARCHETYPES = {
    "robot": {"metallic": 0.9, "roughness": 0.2, "solidify": 0.03, "bevel": True, "emission": 0.1},
    "로봇": {"metallic": 0.9, "roughness": 0.2, "solidify": 0.03, "bevel": True, "emission": 0.1},
    "전사": {"metallic": 0.7, "roughness": 0.3, "solidify": 0.02, "bevel": True, "emission": 0.0},
    "warrior": {"metallic": 0.7, "roughness": 0.3, "solidify": 0.02, "bevel": True, "emission": 0.0},
    "마법사": {"metallic": 0.1, "roughness": 0.6, "solidify": 0.01, "bevel": False, "emission": 0.3},
    "wizard": {"metallic": 0.1, "roughness": 0.6, "solidify": 0.01, "bevel": False, "emission": 0.3},
    "기사": {"metallic": 0.85, "roughness": 0.25, "solidify": 0.025, "bevel": True, "emission": 0.0},
    "knight": {"metallic": 0.85, "roughness": 0.25, "solidify": 0.025, "bevel": True, "emission": 0.0},
    "닌자": {"metallic": 0.2, "roughness": 0.8, "solidify": 0.005, "bevel": False, "emission": 0.0},
    "ninja": {"metallic": 0.2, "roughness": 0.8, "solidify": 0.005, "bevel": False, "emission": 0.0},
    "좀비": {"metallic": 0.0, "roughness": 0.9, "solidify": 0.0, "bevel": False, "emission": 0.0},
    "zombie": {"metallic": 0.0, "roughness": 0.9, "solidify": 0.0, "bevel": False, "emission": 0.0},
    "사이보그": {"metallic": 0.8, "roughness": 0.3, "solidify": 0.02, "bevel": True, "emission": 0.2},
    "cyborg": {"metallic": 0.8, "roughness": 0.3, "solidify": 0.02, "bevel": True, "emission": 0.2},
    "엘프": {"metallic": 0.1, "roughness": 0.5, "solidify": 0.0, "bevel": False, "emission": 0.05},
    "elf": {"metallic": 0.1, "roughness": 0.5, "solidify": 0.0, "bevel": False, "emission": 0.05},
    "드워프": {"metallic": 0.6, "roughness": 0.4, "solidify": 0.015, "bevel": True, "emission": 0.0},
    "dwarf": {"metallic": 0.6, "roughness": 0.4, "solidify": 0.015, "bevel": True, "emission": 0.0},
    "오크": {"metallic": 0.3, "roughness": 0.7, "solidify": 0.01, "bevel": False, "emission": 0.0},
    "orc": {"metallic": 0.3, "roughness": 0.7, "solidify": 0.01, "bevel": False, "emission": 0.0}
}

# ========================================
# UTILITY FUNCTIONS
# ========================================

def clear_scene():
    """Clear all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

def parse_prompt(prompt: str) -> dict:
    """Parse prompt to extract color, archetype, and style information"""
    prompt_lower = prompt.lower()
    
    result = {
        "color": (0.5, 0.5, 0.5),
        "archetype": None,
        "archetype_settings": {"metallic": 0.5, "roughness": 0.5, "solidify": 0.01, "bevel": False, "emission": 0.0},
        "is_metallic": False,
        "is_glowing": False
    }
    
    # Detect color
    for color_name, color_value in COLOR_MAP.items():
        if color_name in prompt_lower:
            result["color"] = color_value
            break
    
    # Detect archetype
    for archetype_name, archetype_settings in ARCHETYPES.items():
        if archetype_name in prompt_lower:
            result["archetype"] = archetype_name
            result["archetype_settings"] = archetype_settings
            break
    
    # Detect metallic keywords
    metallic_keywords = ["메탈", "metal", "metallic", "철", "강철", "steel", "chrome", "크롬", "아머", "armor", "armour"]
    for kw in metallic_keywords:
        if kw in prompt_lower:
            result["is_metallic"] = True
            result["archetype_settings"]["metallic"] = max(result["archetype_settings"]["metallic"], 0.8)
            break
    
    # Detect glowing keywords
    glow_keywords = ["빛나는", "glow", "glowing", "발광", "네온", "neon", "luminous"]
    for kw in glow_keywords:
        if kw in prompt_lower:
            result["is_glowing"] = True
            result["archetype_settings"]["emission"] = max(result["archetype_settings"]["emission"], 0.5)
            break
    
    return result

def detect_gender(prompt: str) -> str:
    """Detect gender from prompt"""
    prompt_lower = prompt.lower()
    female_keywords = ["여성", "여자", "female", "woman", "girl", "소녀", "공주", "princess", "queen", "여왕"]
    for kw in female_keywords:
        if kw in prompt_lower:
            return "female"
    return "male"

# ========================================
# MESH MODIFICATION TOOLS
# ========================================

class AkkuMeshTools:
    """Collection of mesh modification tools for low-poly character generation"""
    
    @staticmethod
    def apply_solidify(obj, thickness=0.02):
        """Add thickness/armor effect to mesh"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Akku_Solidify", type='SOLIDIFY')
        mod.thickness = thickness
        mod.offset = 1.0
        mod.use_rim = True
        mod.use_rim_only = False
        
    @staticmethod
    def apply_decimate(obj, ratio=0.5):
        """Reduce polygon count for low-poly style"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Akku_Decimate", type='DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        
    @staticmethod
    def apply_bevel(obj, width=0.01, segments=1):
        """Add edge beveling for mechanical/armored look"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Akku_Bevel", type='BEVEL')
        mod.width = width
        mod.segments = segments
        mod.affect = 'EDGES'
        
    @staticmethod
    def apply_remesh(obj, voxel_size=0.05):
        """Remesh for uniform polygon distribution"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Akku_Remesh", type='REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = voxel_size
        
    @staticmethod
    def apply_smooth(obj, factor=0.5, iterations=2):
        """Apply smoothing for organic shapes"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Akku_Smooth", type='SMOOTH')
        mod.factor = factor
        mod.iterations = iterations
        
    @staticmethod
    def apply_all_modifiers(obj):
        """Apply all modifiers to mesh"""
        if obj.type != 'MESH':
            return
        
        bpy.context.view_layer.objects.active = obj
        for mod in obj.modifiers[:]:
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                pass

# ========================================
# MATERIAL SYSTEM
# ========================================

class AkkuMaterialSystem:
    """Advanced material system for character generation"""
    
    @staticmethod
    def create_pbr_material(name: str, color: tuple, metallic=0.0, roughness=0.5, emission=0.0) -> bpy.types.Material:
        """Create a PBR material with specified properties"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Create nodes
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        # Set properties
        principled.inputs['Base Color'].default_value = (*color, 1.0)
        principled.inputs['Metallic'].default_value = metallic
        principled.inputs['Roughness'].default_value = roughness
        
        if emission > 0:
            principled.inputs['Emission Color'].default_value = (*color, 1.0)
            principled.inputs['Emission Strength'].default_value = emission * 2.0
        
        # Connect nodes
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        return mat
    
    @staticmethod
    def apply_material_to_mesh(obj, material):
        """Apply material to mesh object"""
        if obj.type != 'MESH':
            return
        
        # Clear existing materials
        obj.data.materials.clear()
        obj.data.materials.append(material)

# ========================================
# PROPORTION SYSTEM
# ========================================

class AkkuProportionSystem:
    """Handle character proportion modifications"""
    
    @staticmethod
    def apply_proportion(armature, proportion_type: str):
        """Apply proportion settings to armature"""
        if proportion_type not in PROPORTION_TYPES:
            proportion_type = "stylized"
        
        settings = PROPORTION_TYPES[proportion_type]
        
        # Apply overall scale to armature only
        armature.scale = (settings["scale"], settings["scale"], settings["scale"])
        
        # For non-uniform proportions, we'd need to modify bone scales
        # This requires entering pose mode and adjusting individual bones
        if settings["head_scale"] != 1.0 or settings["limb_scale"] != 1.0:
            AkkuProportionSystem._apply_bone_scaling(armature, settings)
    
    @staticmethod
    def _apply_bone_scaling(armature, settings):
        """Apply bone-level scaling for proportions"""
        if armature.type != 'ARMATURE':
            return
        
        bpy.context.view_layer.objects.active = armature
        
        try:
            bpy.ops.object.mode_set(mode='POSE')
            
            head_bones = ["Head", "head", "Neck", "neck", "mixamorig:Head", "mixamorig:Neck"]
            limb_bones = ["Arm", "arm", "Leg", "leg", "Hand", "hand", "Foot", "foot"]
            
            for bone in armature.pose.bones:
                bone_name = bone.name.lower()
                
                # Scale head
                if any(hb.lower() in bone_name for hb in head_bones):
                    bone.scale = (settings["head_scale"], settings["head_scale"], settings["head_scale"])
                
                # Scale limbs
                elif any(lb.lower() in bone_name for lb in limb_bones):
                    bone.scale = (settings["limb_scale"], settings["limb_scale"], settings["limb_scale"])
            
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            print(f"Warning: Could not apply bone scaling: {e}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

# ========================================
# MAIN GENERATION PIPELINE
# ========================================

class AkkuGenerator:
    """Main character generation pipeline"""
    
    def __init__(self):
        self.mesh_tools = AkkuMeshTools()
        self.material_system = AkkuMaterialSystem()
        self.proportion_system = AkkuProportionSystem()
    
    def generate(self, prompt: str, style: str, poly_level: str, output_path: str, gender: str = None):
        """Generate a character based on prompt and settings"""
        
        print(f"[Akku SDK] Starting generation...")
        print(f"  Prompt: {prompt}")
        print(f"  Style: {style}")
        print(f"  Poly Level: {poly_level}")
        
        # 1. Clear scene
        clear_scene()
        
        # 2. Detect gender and load base mesh
        if gender is None:
            gender = detect_gender(prompt)
        
        base_mesh_path = AKKU_CONFIG["base_meshes"].get(gender, AKKU_CONFIG["base_meshes"]["male"])
        
        if os.path.exists(base_mesh_path):
            print(f"[Akku SDK] Loading base mesh: {base_mesh_path}")
            bpy.ops.import_scene.fbx(filepath=base_mesh_path)
        else:
            print(f"[Akku SDK] WARNING: Base mesh not found, creating fallback")
            self._create_fallback_character()
            return self._export(output_path)
        
        # 3. Parse prompt for styling
        prompt_data = parse_prompt(prompt)
        archetype_settings = prompt_data["archetype_settings"]
        
        print(f"[Akku SDK] Detected color: {prompt_data['color']}")
        print(f"[Akku SDK] Detected archetype: {prompt_data['archetype']}")
        
        # 4. Find armature and meshes
        armature = None
        meshes = []
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                armature = obj
            elif obj.type == 'MESH':
                meshes.append(obj)
        
        # 5. Apply proportion to armature
        if armature:
            self.proportion_system.apply_proportion(armature, style)
        
        # 6. Apply mesh modifications based on archetype
        poly_settings = POLY_LEVELS.get(poly_level, POLY_LEVELS["medium"])
        
        for mesh in meshes:
            bpy.context.view_layer.objects.active = mesh
            
            # Apply solidify for armored/robotic look
            if archetype_settings["solidify"] > 0:
                self.mesh_tools.apply_solidify(mesh, archetype_settings["solidify"])
            
            # Apply bevel for mechanical edges
            if archetype_settings["bevel"]:
                self.mesh_tools.apply_bevel(mesh, width=0.005, segments=1)
            
            # Apply decimate for low-poly
            self.mesh_tools.apply_decimate(mesh, poly_settings["decimate_ratio"])
        
        # 7. Create and apply material
        material = self.material_system.create_pbr_material(
            name="Akku_Character_Material",
            color=prompt_data["color"],
            metallic=archetype_settings["metallic"],
            roughness=archetype_settings["roughness"],
            emission=archetype_settings["emission"]
        )
        
        for mesh in meshes:
            self.material_system.apply_material_to_mesh(mesh, material)
        
        # 8. Export
        return self._export(output_path)
    
    def _create_fallback_character(self):
        """Create a simple fallback character if base mesh is not available"""
        # Body
        bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 1.0))
        body = bpy.context.active_object
        body.name = "Fallback_Body"
        body.scale = (0.4, 0.25, 0.5)
        
        # Head
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, 1.6))
        head = bpy.context.active_object
        head.name = "Fallback_Head"
        
        # Arms
        for x_offset in [-0.35, 0.35]:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.5, location=(x_offset, 0, 1.0))
            arm = bpy.context.active_object
            arm.name = f"Fallback_Arm_{'L' if x_offset < 0 else 'R'}"
            arm.rotation_euler = (0, 1.57, 0)
        
        # Legs
        for x_offset in [-0.15, 0.15]:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.6, location=(x_offset, 0, 0.35))
            leg = bpy.context.active_object
            leg.name = f"Fallback_Leg_{'L' if x_offset < 0 else 'R'}"
    
    def _export(self, output_path: str) -> bool:
        """Export scene to GLB"""
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Export to GLB
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                export_format='GLB',
                use_selection=False,
                export_apply=True
            )
            
            print(f"[Akku SDK] Successfully exported to: {output_path}")
            return True
        except Exception as e:
            print(f"[Akku SDK] Export failed: {e}")
            return False

# ========================================
# CLI INTERFACE
# ========================================

def main():
    """Main entry point for CLI usage"""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    
    # Parse arguments
    prompt = "default character"
    style = "stylized"
    poly_level = "medium"
    output_path = "/home/composerkil/akku-engine/outputs/output.glb"
    gender = None
    
    i = 0
    while i < len(args):
        if args[i] == "--prompt" and i + 1 < len(args):
            prompt = args[i + 1]
            i += 2
        elif args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
        elif args[i] == "--poly-level" and i + 1 < len(args):
            poly_level = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        elif args[i] == "--gender" and i + 1 < len(args):
            gender = args[i + 1]
            i += 2
        else:
            i += 1
    
    # Generate character
    generator = AkkuGenerator()
    success = generator.generate(prompt, style, poly_level, output_path, gender)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
