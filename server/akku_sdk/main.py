"""
Akku SDK v4.0 - Main Entry Point with Registered Tools

This module provides the CLI interface and registered tools for character generation.
Import from akku_sdk package to use individual components.
Includes Hard-Surface Kitbash and Vertex Color support.
"""

import bpy
import bmesh
import sys
import os
import json
import traceback
from mathutils import Vector, Matrix

from .core import AkkuConfig, AkkuLogger
from .tools import ToolRegistry, tool, StyleAnalyzer, MeshAnalyzer
from .mesh import MeshTools, BooleanRemeshTools
from .shader import StylizedShaderSystem
from .body import BodyTypePresets, BodyTypeSystem
from .kitbash import KitbashLibrary, KitbashEquipper
from .rigging import AutoWeightTransfer
from .handlers import FBXHandler, GLBHandler, ScreenshotHandler
from .procedural import ProceduralHumanoid, StyleProportions, PolyLevelPresets


# ========================================
# REGISTERED TOOLS
# ========================================

@tool("load_base_mesh", "Load Mixamo FBX base mesh (legacy)")
def load_base_mesh(gender: str = "male"):
    """Load and normalize a Mixamo FBX base mesh (legacy mode)"""
    MeshTools.clear_scene()
    AkkuLogger.clear()
    
    mesh_path = AkkuConfig.BASE_MESHES.get(gender, AkkuConfig.BASE_MESHES["male"])
    new_objects = FBXHandler.import_fbx(mesh_path)
    
    mesh_objects = [obj for obj in new_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        raise RuntimeError("No mesh objects found in FBX file")
    
    for obj in mesh_objects:
        MeshTools.normalize_scale(obj, AkkuConfig.TARGET_HEIGHT)
        MeshAnalyzer.log_stats(obj, "After normalization")
    
    return {
        "mesh_count": len(mesh_objects),
        "mesh_names": [obj.name for obj in mesh_objects],
        "target_height": AkkuConfig.TARGET_HEIGHT,
        "mode": "legacy_fbx"
    }


@tool("generate_procedural_base", "Generate procedural humanoid base mesh from scratch")
def generate_procedural_base(
    style: str = "stylized",
    poly_level: str = "medium",
    gender: str = "male",
    create_rig: bool = True,
    hierarchical: bool = True,
    equipment: str = "default"
):
    """
    Generate a procedural humanoid base mesh from scratch.
    No external dependencies (Mixamo, FBX) required.
    
    Args:
        style: Character style (realistic, stylized, chibi, sd, mobile, minifig, cartoon)
        poly_level: Polygon complexity (ultra_low, low, medium, high)
        gender: Gender for proportion adjustments (male, female)
        create_rig: Whether to create basic armature rig
        hierarchical: Use hierarchical generation with separate body parts (default: True)
        equipment: Equipment type for vertex colors (armor, robe, default)
        
    Returns:
        Dict with mesh info and stats
    """
    MeshTools.clear_scene()
    AkkuLogger.clear()
    
    AkkuLogger.info("Generating procedural humanoid", {
        "style": style,
        "poly_level": poly_level,
        "gender": gender,
        "create_rig": create_rig,
        "hierarchical": hierarchical,
        "equipment": equipment
    })
    
    if hierarchical:
        root_obj = ProceduralHumanoid.generate_hierarchical(
            style=style,
            poly_level=poly_level,
            gender=gender,
            equipment=equipment
        )
        
        total_verts = 0
        total_faces = 0
        total_tris = 0
        mesh_names = []
        
        for child in root_obj.children:
            if child.type == 'MESH':
                mesh_names.append(child.name)
                total_verts += len(child.data.vertices)
                total_faces += len(child.data.polygons)
                total_tris += sum(1 for p in child.data.polygons if len(p.vertices) == 3) + \
                             sum(2 for p in child.data.polygons if len(p.vertices) == 4)
        
        return {
            "root_name": root_obj.name,
            "mesh_names": mesh_names,
            "parts_count": len(mesh_names),
            "vertex_count": total_verts,
            "face_count": total_faces,
            "triangle_count": total_tris,
            "style": style,
            "poly_level": poly_level,
            "gender": gender,
            "mode": "procedural_hierarchical"
        }
    else:
        # Use Extrude-First unified mesh approach for better quality
        mesh_obj = ProceduralHumanoid.generate_unified_mesh(
            style=style,
            poly_level=poly_level,
            gender=gender
        )
        
        rig_obj = None
        if create_rig:
            rig_obj = ProceduralHumanoid.create_basic_rig(mesh_obj)
        
        stats = MeshAnalyzer.get_stats(mesh_obj)
        
        return {
            "mesh_name": mesh_obj.name,
            "rig_name": rig_obj.name if rig_obj else None,
            "vertex_count": stats.vertex_count,
            "face_count": stats.face_count,
            "triangle_count": stats.triangle_count,
            "style": style,
            "poly_level": poly_level,
            "gender": gender,
            "mode": "procedural"
        }


@tool("apply_style", "Apply style-based transformations")
def apply_style(prompt: str, style: str = "stylized", poly_level: str = "medium", base_color: list = None):
    """Apply style transformations based on prompt analysis
    
    Args:
        prompt: Character description for style detection
        style: Style preset (stylized, chibi, etc.)
        poly_level: Polygon complexity level
        base_color: Optional RGB color [r, g, b] from Gemini analysis (0.0-1.0 range)
    """
    
    # Use provided color or detect from prompt
    if base_color and isinstance(base_color, (list, tuple)) and len(base_color) >= 3:
        base_color = tuple(base_color[:3])
        AkkuLogger.info("Using provided base color from Gemini", {"color": base_color})
    else:
        base_color = StyleAnalyzer.detect_color(prompt)
    archetype = StyleAnalyzer.detect_archetype(prompt)
    proportion_scale = StyleAnalyzer.get_proportion_scale(style)
    poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
    
    AkkuLogger.info("Style Analysis", {
        "color": base_color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "poly_level": poly_level
    })
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    PART_COLOR_VARIATIONS = {
        "Head": (1.1, 1.05, 1.0),
        "Neck": (0.95, 0.95, 0.95),
        "Torso": (1.0, 1.0, 1.0),
        "Arm_L_Upper": (0.9, 0.95, 1.0),
        "Arm_L_Lower": (0.85, 0.9, 0.95),
        "Arm_R_Upper": (0.9, 0.95, 1.0),
        "Arm_R_Lower": (0.85, 0.9, 0.95),
        "Hand_L": (1.15, 1.1, 1.05),
        "Hand_R": (1.15, 1.1, 1.05),
        "Leg_L_Upper": (0.85, 0.85, 0.9),
        "Leg_L_Lower": (0.8, 0.8, 0.85),
        "Leg_R_Upper": (0.85, 0.85, 0.9),
        "Leg_R_Lower": (0.8, 0.8, 0.85),
        "Foot_L": (0.7, 0.7, 0.75),
        "Foot_R": (0.7, 0.7, 0.75),
    }
    
    for obj in mesh_objects:
        variation = PART_COLOR_VARIATIONS.get(obj.name, (1.0, 1.0, 1.0))
        part_color = (
            min(1.0, base_color[0] * variation[0]),
            min(1.0, base_color[1] * variation[1]),
            min(1.0, base_color[2] * variation[2])
        )
        
        StylizedShaderSystem.apply_stylized_shader(obj, part_color, style)
        
        if proportion_scale != 1.0:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.scale(
                bm,
                vec=Vector((proportion_scale, proportion_scale, proportion_scale)),
                space=Matrix.Identity(4),
                verts=bm.verts
            )
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
        
        MeshTools.triangulate_mesh(obj)
    
    total_tris = sum(MeshTools.get_triangle_count(obj) for obj in mesh_objects)
    
    return {
        "color": base_color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "total_triangles": total_tris
    }


@tool("apply_body_type", "Apply body type deformation to character mesh")
def apply_body_type_tool(
    body_type: str = "default",
    muscular: float = None,
    fat: float = None,
    height: float = None,
    shoulder_width: float = None,
    hip_width: float = None,
    use_lattice: bool = False
):
    """Apply body type deformation to all mesh objects."""
    from dataclasses import asdict
    
    params = BodyTypePresets.get_preset(body_type)
    
    if muscular is not None:
        params.muscular = muscular
    if fat is not None:
        params.fat = fat
    if height is not None:
        params.height = height
    if shoulder_width is not None:
        params.shoulder_width = shoulder_width
    if hip_width is not None:
        params.hip_width = hip_width
    
    AkkuLogger.info("Applying body type", {
        "preset": body_type,
        "params": asdict(params)
    })
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    success_count = 0
    
    for obj in mesh_objects:
        if BodyTypeSystem.apply_body_type(obj, params, use_lattice):
            success_count += 1
    
    return {
        "success": success_count > 0,
        "body_type": body_type,
        "params": asdict(params),
        "meshes_modified": success_count
    }


@tool("union_and_smooth", "Apply Boolean Union + Voxel Remesh + Smooth workflow")
def union_and_smooth_tool(voxel_size: float = 0.02, smooth_iterations: int = 2):
    """Combine all meshes with organic smoothing for low-poly style"""
    
    result = BooleanRemeshTools.union_and_smooth(voxel_size, smooth_iterations)
    
    if result:
        stats = MeshAnalyzer.get_stats(result)
        return {
            "success": True,
            "result_object": result.name,
            "vertex_count": stats.vertex_count,
            "face_count": stats.face_count,
            "triangle_count": stats.triangle_count
        }
    else:
        return {"success": False, "message": "Union and smooth failed"}


@tool("apply_stylized_shader", "Apply Akku Stylized Shader with edge highlighting and cavity darkening")
def tool_apply_stylized_shader(params: dict):
    """Apply stylized shader to character mesh"""
    obj_name = params.get("object_name")
    color = tuple(params.get("color", (0.8, 0.2, 0.2)))
    style = params.get("style", "stylized")
    
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return {"status": "error", "message": f"Object not found: {obj_name}"}
    
    material = StylizedShaderSystem.apply_stylized_shader(obj, color, style)
    
    return {
        "status": "success",
        "material_name": material.name,
        "style": style,
        "color": color
    }


@tool("equip_item", "Equip semantic parts from Kitbash library to character")
def tool_equip_item(category: str = None, style: str = None, part_name: str = None, 
                    color: tuple = (0.6, 0.6, 0.6), shader_style: str = "stylized"):
    """Equip items from Kitbash library to character"""
    if isinstance(color, list):
        color = tuple(color)
    
    equipped = []
    
    if part_name:
        part = KitbashLibrary.get_part(part_name)
        if part:
            obj = KitbashEquipper.equip_part(part, color, shader_style)
            if obj:
                equipped.append(part.name)
    else:
        parts = KitbashLibrary.query_parts(category=category, style=style)
        for part in parts:
            obj = KitbashEquipper.equip_part(part, color, shader_style)
            if obj:
                equipped.append(part.name)
    
    return {
        "status": "success" if equipped else "no_parts_found",
        "equipped": equipped,
        "count": len(equipped)
    }


@tool("list_kitbash_parts", "List available parts in Kitbash library")
def tool_list_kitbash_parts(category: str = None, style: str = None):
    """List available semantic parts"""
    
    parts = KitbashLibrary.query_parts(category=category, style=style)
    
    return {
        "status": "success",
        "parts": [
            {
                "name": p.name,
                "category": p.category,
                "style": p.style,
                "tags": p.tags
            }
            for p in parts
        ],
        "categories": KitbashLibrary.list_categories(),
        "styles": KitbashLibrary.list_styles()
    }


@tool("auto_weight_transfer", "Transfer vertex weights from base mesh to all parts")
def tool_auto_weight_transfer(params: dict = None):
    """
    Auto-rig all equipment parts by transferring vertex weights from base mesh.
    
    Uses Data Transfer modifier to copy vertex groups from the base character
    mesh to attached equipment parts, enabling them to deform with animations.
    
    Args:
        params: Optional dict with:
            - apply_modifier: bool - Whether to apply the modifier (default: True)
            - cleanup_empty: bool - Remove vertex groups with no weights (default: True)
    
    Returns:
        Dict with success status and details for each rigged part
    """
    if params is None:
        params = {}
    
    apply_modifier = params.get("apply_modifier", True)
    cleanup_empty = params.get("cleanup_empty", True)
    
    results = AutoWeightTransfer.auto_rig_all_parts(
        exclude_base=True,
        apply_transfer=apply_modifier
    )
    
    if cleanup_empty:
        for result in results:
            if result.success:
                obj = bpy.data.objects.get(result.part_name)
                if obj:
                    AutoWeightTransfer.cleanup_zero_weights(obj)
    
    success_count = sum(1 for r in results if r.success)
    
    return {
        "status": "success" if success_count > 0 else "no_parts_rigged",
        "parts_rigged": success_count,
        "total_parts": len(results),
        "details": [
            {
                "part": r.part_name,
                "success": r.success,
                "source": r.source_mesh,
                "groups": r.vertex_groups_created,
                "message": r.message
            }
            for r in results
        ]
    }


@tool("export_glb", "Export scene as GLB file")
def export_glb(output_path: str):
    """Export scene to GLB format"""
    success = GLBHandler.export_glb(output_path)
    
    if success:
        file_size = os.path.getsize(output_path)
        return {
            "path": output_path,
            "size_bytes": file_size,
            "success": True,
            "log_report": AkkuLogger.get_json_report()
        }
    else:
        raise RuntimeError(f"GLB export failed: {output_path}")


# ========================================
# AUTONOMOUS AGENT TOOLS
# ========================================

@tool("capture_screenshot", "Capture viewport screenshot for Gemini VLM review")
def capture_screenshot(
    output_path: str,
    view: str = "front",
    resolution: int = 768,
    include_composite: bool = False
):
    """
    Capture viewport screenshot for autonomous agent self-verification.
    
    This tool renders the current scene from a specified camera angle,
    producing a PNG image that can be sent to Gemini VLM for analysis.
    
    Args:
        output_path: Output PNG file path (e.g., "/tmp/preview.png")
        view: Camera preset - "front", "side", "quarter", or "top"
        resolution: Image resolution in pixels (square, default: 768)
        include_composite: Create front+side 2-up composite for proportion analysis
        
    Returns:
        Dict with path, size_bytes, view, resolution, and scene_info
        
    Example:
        capture_screenshot(
            output_path="/tmp/character_preview.png",
            view="quarter",
            resolution=768,
            include_composite=True
        )
    """
    result = ScreenshotHandler.capture_screenshot(
        output_path=output_path,
        view=view,
        resolution=resolution,
        include_composite=include_composite
    )
    
    # Add scene info for Gemini context
    result["scene_info"] = ScreenshotHandler.get_scene_info()
    
    return result


@tool("get_scene_info", "Get current scene statistics for Gemini context")
def get_scene_info():
    """
    Get current scene statistics for Gemini VLM context.
    
    Returns mesh counts, vertex/face totals, and armature info.
    Use this to provide context to Gemini when analyzing screenshots.
    
    Returns:
        Dict with mesh_count, mesh_names, total_vertices, total_faces,
        armature_count, armature_names
    """
    return ScreenshotHandler.get_scene_info()


@tool("generate_character", "Complete character generation pipeline")
def generate_character(
    prompt: str,
    style: str = "stylized",
    poly_level: str = "medium",
    output_path: str = None,
    gender: str = "male",
    body_type: str = "auto",
    body_type_params: dict = None,
    use_remesh: bool = False,
    use_procedural: bool = True,
    equipment: str = "default",
    base_color: list = None
):
    """Generate a complete low-poly character from prompt.
    
    Args:
        prompt: Character description
        style: Character style (realistic, stylized, chibi, sd, mobile, minifig, cartoon)
        poly_level: Polygon complexity (ultra_low, low, medium, high)
        output_path: Output GLB file path
        gender: Gender (male, female)
        body_type: Body type preset or "auto" for prompt detection
        body_type_params: Detailed body type parameters
        use_remesh: Whether to apply voxel remesh
        use_procedural: Use procedural mesh generation (default: True, False = legacy Mixamo)
        equipment: Equipment type for vertex colors (armor, robe, default)
        base_color: RGB color [r, g, b] from Gemini analysis (0.0-1.0 range)
    """
    
    if equipment == "default":
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["armor", "knight", "warrior", "기사", "전사", "갑옷"]):
            equipment = "armor"
        elif any(kw in prompt_lower for kw in ["robe", "mage", "wizard", "마법사", "로브"]):
            equipment = "robe"
    
    print(f"\n{'='*60}")
    print(f"[Akku SDK v4.0] Character Generation")
    print(f"{'='*60}")
    print(f"Prompt: {prompt}")
    print(f"Style: {style}, Poly Level: {poly_level}")
    print(f"Gender: {gender}, Body Type: {body_type}")
    print(f"Equipment: {equipment}")
    print(f"Body Type Params: {body_type_params}")
    print(f"Use Remesh: {use_remesh}")
    print(f"{'='*60}\n")
    
    if use_procedural:
        load_result = ToolRegistry.execute("generate_procedural_base", {
            "style": style,
            "poly_level": poly_level,
            "gender": gender,
            "create_rig": True,
            "hierarchical": True,
            "equipment": equipment
        })
    else:
        load_result = ToolRegistry.execute("load_base_mesh", {"gender": gender})
    
    if load_result["status"] == "error":
        raise RuntimeError(f"Load failed: {load_result['message']}")
    
    body_type_result = None
    
    # Use detailed params if provided (from Gemini), otherwise fallback to preset/auto
    if body_type_params and any(k in body_type_params for k in ["muscular", "fat", "shoulderWidth", "height", "hipWidth"]):
        # Convert camelCase to snake_case for SDK
        AkkuLogger.info("Using detailed body type params from Gemini", body_type_params)
        body_type_result = ToolRegistry.execute("apply_body_type", {
            "body_type": body_type_params.get("preset", "default"),
            "muscular": body_type_params.get("muscular", 0.0),
            "fat": body_type_params.get("fat", 0.0),
            "height": body_type_params.get("height", 0.0),
            "shoulder_width": body_type_params.get("shoulderWidth", 0.0),
            "hip_width": body_type_params.get("hipWidth", 0.0)
        })
    elif body_type != "default":
        if body_type == "auto":
            detected_params = BodyTypePresets.detect_from_prompt(prompt)
            if detected_params != BodyTypePresets.PRESETS["default"]:
                from dataclasses import asdict
                body_type_result = ToolRegistry.execute("apply_body_type", {
                    "body_type": "default",
                    "muscular": detected_params.muscular,
                    "fat": detected_params.fat,
                    "height": detected_params.height,
                    "shoulder_width": detected_params.shoulder_width,
                    "hip_width": detected_params.hip_width
                })
        else:
            body_type_result = ToolRegistry.execute("apply_body_type", {
                "body_type": body_type
            })
    
    style_params = {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level
    }
    # Use Gemini-analyzed color if provided
    if base_color:
        style_params["base_color"] = base_color
        AkkuLogger.info("Using Gemini-analyzed base color", {"color": base_color})
    
    style_result = ToolRegistry.execute("apply_style", style_params)
    if style_result["status"] == "error":
        raise RuntimeError(f"Style failed: {style_result['message']}")
    
    style_info = style_result.get("result", {}) if style_result.get("status") == "success" else {}
    color = style_info.get("color", (0.6, 0.6, 0.6))
    
    ARCHETYPE_KEYWORDS = {
        "warrior": "heavy", "전사": "heavy",
        "knight": "heavy", "기사": "heavy",
        "mage": "magic", "마법사": "magic",
        "wizard": "magic",
        "rogue": "light", "닌자": "light",
        "assassin": "light", "ninja": "light",
        "robot": "scifi", "로봇": "scifi",
        "cyborg": "scifi", "사이보그": "scifi",
        "sci-fi": "scifi", "scifi": "scifi", "SF": "scifi",
    }
    
    equipment_style = "heavy"
    prompt_lower = prompt.lower()
    for keyword, eq_style in ARCHETYPE_KEYWORDS.items():
        if keyword.lower() in prompt_lower:
            equipment_style = eq_style
            break
    
    AkkuLogger.info(f"Equipping kitbash parts", {
        "equipment_style": equipment_style,
        "color": color
    })
    
    equip_result = ToolRegistry.execute("equip_item", {
        "category": "armor",
        "style": equipment_style,
        "color": list(color) if isinstance(color, tuple) else color,
        "shader_style": style
    })
    
    if equip_result.get("status") == "success" and equip_result.get("result", {}).get("count", 0) > 0:
        AkkuLogger.info(f"Equipped {equip_result['result']['count']} parts, running auto weight transfer")
        weight_result = ToolRegistry.execute("auto_weight_transfer", {})
        if weight_result.get("status") != "success":
            AkkuLogger.warning(f"Weight transfer had issues: {weight_result.get('message', 'unknown')}")
    elif equip_result.get("status") == "error":
        AkkuLogger.warning(f"Equip failed: {equip_result.get('message', 'unknown')}")
    else:
        AkkuLogger.info("No kitbash parts equipped (style not found or no matching parts)")
    
    remesh_result = None
    if use_remesh:
        poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
        remesh_result = ToolRegistry.execute("union_and_smooth", {
            "voxel_size": poly_settings.get("voxel_size", 0.02),
            "smooth_iterations": 2
        })
    
    if output_path is None:
        output_path = os.path.join(AkkuConfig.OUTPUT_DIR, "character.glb")
    
    export_result = ToolRegistry.execute("export_glb", {"output_path": output_path})
    if export_result["status"] == "error":
        raise RuntimeError(f"Export failed: {export_result['message']}")
    
    return {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level,
        "body_type": body_type,
        "output_path": output_path,
        "generation_mode": "procedural" if use_procedural else "legacy_fbx",
        "load_info": load_result["result"],
        "body_type_info": body_type_result["result"] if body_type_result else None,
        "style_info": style_result["result"],
        "remesh_info": remesh_result["result"] if remesh_result else None,
        "export_info": export_result["result"]
    }


# ========================================
# CLI INTERFACE
# ========================================

def main():
    """Main entry point for CLI execution"""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    
    if len(args) < 4:
        print("Usage: blender --background --python -m akku_sdk.main -- <prompt> <style> <poly_level> <output_path> [gender] [body_type] [use_remesh] [equipment] [gemini_params] [screenshot_path]")
        print("\nStyles: realistic, stylized, chibi, sd, mobile, minifig, cartoon")
        print("Poly Levels: ultra_low, low, medium, high")
        print("Body Types: default, muscular, thin, fat, tall, short, athletic, stocky, slim, heroic, chibi, giant")
        print("Equipment: default, armor, robe")
        print("\nEquipment determines Vertex Colors and Hard-Surface details")
        print("Gemini Params: JSON object from Replit Gemini analysis")
        print("Screenshot Path: Optional PNG path for autonomous agent verification")
        sys.exit(1)
    
    prompt = args[0]
    style = args[1]
    poly_level = args[2]
    output_path = args[3]
    gender = args[4] if len(args) > 4 else "male"
    body_type_raw = args[5] if len(args) > 5 else "auto"
    use_remesh = args[6].lower() == "true" if len(args) > 6 else False
    equipment = args[7] if len(args) > 7 else "default"
    gemini_params_raw = args[8] if len(args) > 8 else ""
    screenshot_path = args[9] if len(args) > 9 else ""
    
    # Parse Gemini params from Replit server
    gemini_params = None
    if gemini_params_raw and gemini_params_raw.startswith("{"):
        try:
            gemini_params = json.loads(gemini_params_raw)
            AkkuLogger.info("Received Gemini-analyzed parameters", {
                "archetype": gemini_params.get("archetype", "unknown"),
                "body_preset": gemini_params.get("bodyType", {}).get("preset", "unknown"),
                "armor_style": gemini_params.get("equipment", {}).get("armorStyle", "none")
            })
            
            # Override parameters with Gemini analysis
            if "style" in gemini_params:
                style = gemini_params["style"].get("proportionType", style)
                poly_level = gemini_params["style"].get("polyLevel", poly_level)
                gender = gemini_params["style"].get("gender", gender)
            
            if "equipment" in gemini_params:
                gemini_armor = gemini_params["equipment"].get("armorStyle", "none")
                if gemini_armor == "plate" or gemini_armor == "heavy":
                    equipment = "armor"
                elif gemini_armor == "cloth" or gemini_armor == "magic":
                    equipment = "robe"
            
            if "bodyType" in gemini_params:
                body_type_raw = json.dumps(gemini_params["bodyType"])
        except json.JSONDecodeError:
            AkkuLogger.info("Failed to parse Gemini params, using defaults")
            gemini_params = None
    
    # Extract color from Gemini params if available
    gemini_color = None
    if gemini_params and "shader" in gemini_params:
        gemini_color = gemini_params["shader"].get("baseColor")
        if gemini_color:
            AkkuLogger.info("Using Gemini-analyzed color", {"color": gemini_color})
    
    # Parse body type - can be JSON with detailed params or simple preset name
    body_type_params = None
    body_type = "auto"
    if body_type_raw.startswith("{"):
        try:
            body_type_params = json.loads(body_type_raw)
            body_type = body_type_params.get("preset", "auto")
            AkkuLogger.info("Parsed detailed body type params", body_type_params)
        except json.JSONDecodeError:
            body_type_params = {"preset": "auto"}
    else:
        body_type = body_type_raw
        body_type_params = {"preset": body_type_raw}
    
    try:
        generate_params = {
            "prompt": prompt,
            "style": style,
            "use_procedural": True,
            "poly_level": poly_level,
            "output_path": output_path,
            "gender": gender,
            "body_type": body_type,
            "body_type_params": body_type_params,
            "use_remesh": use_remesh,
            "equipment": equipment
        }
        
        # Add Gemini-analyzed color if available
        if gemini_color:
            generate_params["base_color"] = gemini_color
        
        result = ToolRegistry.execute("generate_character", generate_params)
        
        if result["status"] == "success":
            print(f"\n[Akku SDK] Generation completed successfully!")
            print(json.dumps(result["result"], indent=2, ensure_ascii=False, default=str))
            
            # Capture screenshot if path provided (for autonomous agent verification)
            if screenshot_path:
                try:
                    AkkuLogger.info("Capturing screenshot for autonomous verification", {
                        "path": screenshot_path
                    })
                    screenshot_result = ScreenshotHandler.capture_screenshot(
                        output_path=screenshot_path,
                        view="quarter",
                        resolution=768
                    )
                    print(f"\n[Akku SDK] Screenshot captured: {screenshot_path}")
                    print(json.dumps(screenshot_result, indent=2, ensure_ascii=False, default=str))
                    
                    # Also output scene info for Gemini context
                    scene_info = ScreenshotHandler.get_scene_info()
                    print(f"\n[Akku SDK] Scene info:")
                    print(json.dumps(scene_info, indent=2, ensure_ascii=False, default=str))
                except Exception as e:
                    print(f"\n[Akku SDK] Screenshot capture failed: {str(e)}")
        else:
            print(f"\n[Akku SDK] Generation failed: {result['message']}")
            if "error_report" in result:
                print(json.dumps(result["error_report"], indent=2, ensure_ascii=False))
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[Akku SDK] Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
