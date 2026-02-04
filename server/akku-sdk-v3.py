"""
Akku SDK v3.0 - MCP-Style Low-Poly Character Generation Toolkit
Follows standard MCP architecture with tool registry pattern
"""

import bpy
import bmesh
import math
import sys
import os
import json
import re
from mathutils import Vector, Matrix
from typing import Dict, Any, Callable, Optional, Tuple, List
from functools import wraps

# ========================================
# CONFIGURATION
# ========================================

class AkkuConfig:
    BASE_MESHES = {
        "male": "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx",
        "female": "/home/composerkil/akku-engine/assets/base_meshes/X_Bot.fbx"
    }
    OUTPUT_DIR = "/home/composerkil/akku-engine/outputs"
    
    # Mixamo FBX files are in centimeters, Blender uses meters
    FBX_UNIT_SCALE = 0.01  # Convert cm to meters
    
    # Target character height in meters
    TARGET_HEIGHT = 1.8  # Standard human height


# ========================================
# TOOL REGISTRY (MCP-Style Pattern)
# ========================================

class ToolRegistry:
    """MCP-style tool registry for dynamic tool registration and execution"""
    
    _tools: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, description: str = ""):
        """Decorator to register a tool function"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                print(f"[Akku SDK] Executing tool: {name}")
                return func(*args, **kwargs)
            
            cls._tools[name] = {
                "function": wrapper,
                "description": description,
                "name": name
            }
            return wrapper
        return decorator
    
    @classmethod
    def execute(cls, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a registered tool by name"""
        if tool_name not in cls._tools:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}
        
        try:
            result = cls._tools[tool_name]["function"](**(params or {}))
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @classmethod
    def list_tools(cls) -> List[Dict[str, str]]:
        """List all registered tools"""
        return [{"name": t["name"], "description": t["description"]} for t in cls._tools.values()]


# Shortcut decorator
tool = ToolRegistry.register


# ========================================
# COLOR & STYLE DETECTION
# ========================================

class StyleAnalyzer:
    """Analyzes prompts to extract style, colors, and archetypes"""
    
    COLORS = {
        # Korean
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
        # English
        "red": (1.0, 0.1, 0.1), "blue": (0.1, 0.3, 1.0), "green": (0.1, 0.8, 0.2),
        "yellow": (1.0, 0.9, 0.1), "orange": (1.0, 0.5, 0.0), "purple": (0.6, 0.2, 0.8),
        "pink": (1.0, 0.5, 0.7), "black": (0.05, 0.05, 0.05), "white": (0.95, 0.95, 0.95),
        "gray": (0.5, 0.5, 0.5), "grey": (0.5, 0.5, 0.5), "gold": (0.9, 0.7, 0.2),
        "silver": (0.8, 0.8, 0.85), "brown": (0.4, 0.25, 0.1), "cyan": (0.0, 0.8, 0.8),
        "metallic": (0.6, 0.6, 0.7)
    }
    
    ARCHETYPES = {
        "robot": {"metallic": 0.9, "roughness": 0.2, "emission": 0.1},
        "로봇": {"metallic": 0.9, "roughness": 0.2, "emission": 0.1},
        "warrior": {"metallic": 0.7, "roughness": 0.3, "emission": 0.0},
        "전사": {"metallic": 0.7, "roughness": 0.3, "emission": 0.0},
        "wizard": {"metallic": 0.1, "roughness": 0.6, "emission": 0.3},
        "마법사": {"metallic": 0.1, "roughness": 0.6, "emission": 0.3},
        "knight": {"metallic": 0.85, "roughness": 0.25, "emission": 0.0},
        "기사": {"metallic": 0.85, "roughness": 0.25, "emission": 0.0},
        "ninja": {"metallic": 0.2, "roughness": 0.8, "emission": 0.0},
        "닌자": {"metallic": 0.2, "roughness": 0.8, "emission": 0.0},
        "zombie": {"metallic": 0.0, "roughness": 0.9, "emission": 0.0},
        "좀비": {"metallic": 0.0, "roughness": 0.9, "emission": 0.0},
        "cyborg": {"metallic": 0.8, "roughness": 0.3, "emission": 0.2},
        "사이보그": {"metallic": 0.8, "roughness": 0.3, "emission": 0.2},
        "elf": {"metallic": 0.1, "roughness": 0.5, "emission": 0.05},
        "엘프": {"metallic": 0.1, "roughness": 0.5, "emission": 0.05},
    }
    
    PROPORTION_TYPES = {
        "stylized": {"scale": 1.0, "description": "Standard balanced proportions"},
        "chibi": {"scale": 0.6, "description": "Cute, big-head style"},
        "sd": {"scale": 0.65, "description": "Super-deformed style"},
        "mobile": {"scale": 0.8, "description": "Mobile-optimized"},
        "minifig": {"scale": 0.5, "description": "Block figure style"},
        "cartoon": {"scale": 0.85, "description": "Cartoon proportions"},
        "realistic": {"scale": 1.0, "description": "Realistic human proportions"}
    }
    
    POLY_LEVELS = {
        "ultra_low": {"decimate_ratio": 0.15, "max_tris": 300},
        "low": {"decimate_ratio": 0.3, "max_tris": 800},
        "medium": {"decimate_ratio": 0.5, "max_tris": 1500},
        "high": {"decimate_ratio": 0.75, "max_tris": 3000}
    }
    
    @classmethod
    def detect_color(cls, prompt: str) -> Tuple[float, float, float]:
        """Extract primary color from prompt"""
        prompt_lower = prompt.lower()
        for keyword, color in cls.COLORS.items():
            if keyword in prompt_lower:
                return color
        return (0.5, 0.5, 0.6)  # Default gray
    
    @classmethod
    def detect_archetype(cls, prompt: str) -> Dict[str, float]:
        """Detect character archetype from prompt"""
        prompt_lower = prompt.lower()
        for keyword, props in cls.ARCHETYPES.items():
            if keyword in prompt_lower:
                return props
        return {"metallic": 0.3, "roughness": 0.5, "emission": 0.0}
    
    @classmethod
    def get_proportion_scale(cls, style: str) -> float:
        """Get scale factor for proportion type"""
        return cls.PROPORTION_TYPES.get(style, cls.PROPORTION_TYPES["stylized"])["scale"]
    
    @classmethod
    def get_poly_settings(cls, level: str) -> Dict[str, Any]:
        """Get polygon reduction settings"""
        return cls.POLY_LEVELS.get(level, cls.POLY_LEVELS["medium"])


# ========================================
# MESH OPERATIONS
# ========================================

class MeshTools:
    """Low-level mesh manipulation tools"""
    
    @staticmethod
    def clear_scene():
        """Clear all objects from scene"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        # Clear orphan data
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)
        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)
        for block in bpy.data.armatures:
            if block.users == 0:
                bpy.data.armatures.remove(block)
    
    @staticmethod
    def get_mesh_bounds(obj) -> Tuple[Vector, Vector, float]:
        """Get mesh bounding box and height"""
        if obj.type != 'MESH':
            return Vector((0, 0, 0)), Vector((0, 0, 0)), 0
        
        # Get world-space bounds
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        min_co = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
        max_co = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
        height = max_co.z - min_co.z
        
        return min_co, max_co, height
    
    @staticmethod
    def normalize_scale(obj, target_height: float = 1.8):
        """Normalize object to target height in meters"""
        _, _, current_height = MeshTools.get_mesh_bounds(obj)
        
        if current_height > 0:
            scale_factor = target_height / current_height
            obj.scale *= scale_factor
            
            # Apply the scale
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            print(f"[Akku SDK] Normalized scale: {current_height:.2f}m -> {target_height:.2f}m (factor: {scale_factor:.4f})")
            return scale_factor
        return 1.0
    
    @staticmethod
    def apply_decimate(obj, ratio: float):
        """Apply decimate modifier to reduce polygon count"""
        if obj.type != 'MESH':
            return
        
        # Add decimate modifier
        mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = max(0.1, min(1.0, ratio))
        mod.use_collapse_triangulate = True
        
        # Apply modifier
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        
        print(f"[Akku SDK] Applied decimate with ratio {ratio:.2f}")
    
    @staticmethod
    def triangulate_mesh(obj):
        """Ensure mesh is triangulated for game export"""
        if obj.type != 'MESH':
            return
        
        mod = obj.modifiers.new(name="Triangulate", type='TRIANGULATE')
        mod.quad_method = 'BEAUTY'
        mod.ngon_method = 'BEAUTY'
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    
    @staticmethod
    def get_triangle_count(obj) -> int:
        """Get triangle count for mesh"""
        if obj.type != 'MESH':
            return 0
        
        # Ensure we're counting triangulated faces
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        tri_count = len(bm.faces)
        bm.free()
        
        return tri_count


# ========================================
# MATERIAL SYSTEM
# ========================================

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
        
        # Handle emission (Blender 3.4 uses 'Emission', newer versions use 'Emission Color')
        if emission > 0:
            try:
                principled.inputs['Emission'].default_value = (*color, 1.0)
            except KeyError:
                try:
                    principled.inputs['Emission Color'].default_value = (*color, 1.0)
                except KeyError:
                    pass
            
            try:
                principled.inputs['Emission Strength'].default_value = emission * 2.0
            except KeyError:
                pass
        
        # Connect nodes
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        return mat
    
    @staticmethod
    def apply_material(obj, material: bpy.types.Material):
        """Apply material to object"""
        if obj.type != 'MESH':
            return
        
        # Clear existing materials
        obj.data.materials.clear()
        obj.data.materials.append(material)


# ========================================
# REGISTERED TOOLS
# ========================================

@tool("load_base_mesh", "Load Mixamo FBX base mesh")
def load_base_mesh(gender: str = "male") -> Dict[str, Any]:
    """Load and normalize a Mixamo FBX base mesh"""
    
    # Clear scene first
    MeshTools.clear_scene()
    
    # Get mesh path
    mesh_path = AkkuConfig.BASE_MESHES.get(gender, AkkuConfig.BASE_MESHES["male"])
    
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Base mesh not found: {mesh_path}")
    
    # Import FBX
    bpy.ops.import_scene.fbx(
        filepath=mesh_path,
        use_custom_normals=True,
        use_image_search=False,
        ignore_leaf_bones=True,
        automatic_bone_orientation=True
    )
    
    print(f"[Akku SDK] Loaded base mesh: {mesh_path}")
    
    # Find the mesh object(s)
    mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        raise RuntimeError("No mesh objects found in FBX file")
    
    # Normalize scale for each mesh
    for obj in mesh_objects:
        # FBX from Mixamo is often in cm, normalize to target height
        MeshTools.normalize_scale(obj, AkkuConfig.TARGET_HEIGHT)
    
    return {
        "mesh_count": len(mesh_objects),
        "mesh_names": [obj.name for obj in mesh_objects],
        "target_height": AkkuConfig.TARGET_HEIGHT
    }


@tool("apply_style", "Apply style-based transformations")
def apply_style(prompt: str, style: str = "stylized", poly_level: str = "medium") -> Dict[str, Any]:
    """Apply style transformations based on prompt analysis"""
    
    # Analyze prompt
    color = StyleAnalyzer.detect_color(prompt)
    archetype = StyleAnalyzer.detect_archetype(prompt)
    proportion_scale = StyleAnalyzer.get_proportion_scale(style)
    poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
    
    print(f"[Akku SDK] Style Analysis:")
    print(f"  Color: {color}")
    print(f"  Archetype: {archetype}")
    print(f"  Proportion Scale: {proportion_scale}")
    print(f"  Poly Level: {poly_level}")
    
    # Create material
    material = MaterialSystem.create_material(
        name="AkkuCharacterMat",
        color=color,
        metallic=archetype.get("metallic", 0.3),
        roughness=archetype.get("roughness", 0.5),
        emission=archetype.get("emission", 0.0)
    )
    
    # Apply to all mesh objects
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    for obj in mesh_objects:
        # Apply material
        MaterialSystem.apply_material(obj, material)
        
        # Apply proportion scale
        if proportion_scale != 1.0:
            obj.scale *= proportion_scale
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Apply polygon reduction
        MeshTools.apply_decimate(obj, poly_settings["decimate_ratio"])
        
        # Triangulate for game export
        MeshTools.triangulate_mesh(obj)
    
    # Count final triangles
    total_tris = sum(MeshTools.get_triangle_count(obj) for obj in mesh_objects)
    
    return {
        "color": color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "decimate_ratio": poly_settings["decimate_ratio"],
        "total_triangles": total_tris
    }


@tool("export_glb", "Export scene as GLB file")
def export_glb(output_path: str) -> Dict[str, Any]:
    """Export scene to GLB format"""
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=False,
        export_apply=True,
        export_animations=True,
        export_skins=True,
        export_morph=False,
        export_lights=False,
        export_cameras=False
    )
    
    # Verify export
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"[Akku SDK] Exported GLB: {output_path} ({file_size} bytes)")
        return {
            "path": output_path,
            "size_bytes": file_size,
            "success": True
        }
    else:
        raise RuntimeError(f"GLB export failed: {output_path}")


@tool("generate_character", "Complete character generation pipeline")
def generate_character(
    prompt: str,
    style: str = "stylized",
    poly_level: str = "medium",
    output_path: str = None,
    gender: str = "male"
) -> Dict[str, Any]:
    """Generate a complete low-poly character from prompt"""
    
    print(f"\n{'='*50}")
    print(f"[Akku SDK v3.0] Character Generation")
    print(f"{'='*50}")
    print(f"Prompt: {prompt}")
    print(f"Style: {style}")
    print(f"Poly Level: {poly_level}")
    print(f"Gender: {gender}")
    print(f"{'='*50}\n")
    
    # Step 1: Load base mesh
    load_result = ToolRegistry.execute("load_base_mesh", {"gender": gender})
    if load_result["status"] == "error":
        raise RuntimeError(f"Failed to load base mesh: {load_result['message']}")
    
    # Step 2: Apply style
    style_result = ToolRegistry.execute("apply_style", {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level
    })
    if style_result["status"] == "error":
        raise RuntimeError(f"Failed to apply style: {style_result['message']}")
    
    # Step 3: Export
    if output_path is None:
        output_path = os.path.join(AkkuConfig.OUTPUT_DIR, "character.glb")
    
    export_result = ToolRegistry.execute("export_glb", {"output_path": output_path})
    if export_result["status"] == "error":
        raise RuntimeError(f"Failed to export: {export_result['message']}")
    
    return {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level,
        "output_path": output_path,
        "load_info": load_result["result"],
        "style_info": style_result["result"],
        "export_info": export_result["result"]
    }


# ========================================
# CLI INTERFACE
# ========================================

def main():
    """Main entry point for CLI execution"""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    
    if len(args) < 4:
        print("Usage: blender --background --python akku-sdk-v3.py -- <prompt> <style> <poly_level> <output_path> [gender]")
        sys.exit(1)
    
    prompt = args[0]
    style = args[1]
    poly_level = args[2]
    output_path = args[3]
    gender = args[4] if len(args) > 4 else "male"
    
    try:
        result = ToolRegistry.execute("generate_character", {
            "prompt": prompt,
            "style": style,
            "poly_level": poly_level,
            "output_path": output_path,
            "gender": gender
        })
        
        if result["status"] == "success":
            print(f"\n[Akku SDK] Generation completed successfully!")
            print(json.dumps(result["result"], indent=2, ensure_ascii=False))
        else:
            print(f"\n[Akku SDK] Generation failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[Akku SDK] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
