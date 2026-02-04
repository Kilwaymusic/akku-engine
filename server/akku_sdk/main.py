"""
Akku SDK v3.5 - Main Entry Point with Registered Tools

This module provides the CLI interface and registered tools for character generation.
Import from akku_sdk package to use individual components.
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
from .handlers import FBXHandler, GLBHandler


# ========================================
# REGISTERED TOOLS
# ========================================

@tool("load_base_mesh", "Load Mixamo FBX base mesh")
def load_base_mesh(gender: str = "male"):
    """Load and normalize a Mixamo FBX base mesh"""
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
        "target_height": AkkuConfig.TARGET_HEIGHT
    }


@tool("apply_style", "Apply style-based transformations")
def apply_style(prompt: str, style: str = "stylized", poly_level: str = "medium"):
    """Apply style transformations based on prompt analysis"""
    
    color = StyleAnalyzer.detect_color(prompt)
    archetype = StyleAnalyzer.detect_archetype(prompt)
    proportion_scale = StyleAnalyzer.get_proportion_scale(style)
    poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
    
    AkkuLogger.info("Style Analysis", {
        "color": color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "poly_level": poly_level
    })
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    for obj in mesh_objects:
        StylizedShaderSystem.apply_stylized_shader(obj, color, style)
        
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
        
        MeshTools.decimate_mesh(obj, poly_settings["decimate_ratio"])
        MeshTools.triangulate_mesh(obj)
    
    total_tris = sum(MeshTools.get_triangle_count(obj) for obj in mesh_objects)
    
    return {
        "color": color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "decimate_ratio": poly_settings["decimate_ratio"],
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


@tool("generate_character", "Complete character generation pipeline")
def generate_character(
    prompt: str,
    style: str = "stylized",
    poly_level: str = "medium",
    output_path: str = None,
    gender: str = "male",
    body_type: str = "auto",
    body_type_params: dict = None,
    use_remesh: bool = False
):
    """Generate a complete low-poly character from prompt."""
    
    print(f"\n{'='*60}")
    print(f"[Akku SDK v3.6] Character Generation")
    print(f"{'='*60}")
    print(f"Prompt: {prompt}")
    print(f"Style: {style}, Poly Level: {poly_level}")
    print(f"Gender: {gender}, Body Type: {body_type}")
    print(f"Body Type Params: {body_type_params}")
    print(f"Use Remesh: {use_remesh}")
    print(f"{'='*60}\n")
    
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
    
    style_result = ToolRegistry.execute("apply_style", {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level
    })
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
        print("Usage: blender --background --python -m akku_sdk.main -- <prompt> <style> <poly_level> <output_path> [gender] [body_type] [use_remesh]")
        print("\nBody Types: default, muscular, thin, fat, tall, short, athletic, stocky, slim, heroic, chibi, giant")
        print("Korean: 근육질, 마른, 뚱뚱한, 키큰, 키작은, 운동선수, 땅딸막한, 날씬한, 영웅, 치비, 거인")
        sys.exit(1)
    
    prompt = args[0]
    style = args[1]
    poly_level = args[2]
    output_path = args[3]
    gender = args[4] if len(args) > 4 else "male"
    body_type_raw = args[5] if len(args) > 5 else "auto"
    use_remesh = args[6].lower() == "true" if len(args) > 6 else False
    
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
        result = ToolRegistry.execute("generate_character", {
            "prompt": prompt,
            "style": style,
            "poly_level": poly_level,
            "output_path": output_path,
            "gender": gender,
            "body_type": body_type,
            "body_type_params": body_type_params,
            "use_remesh": use_remesh
        })
        
        if result["status"] == "success":
            print(f"\n[Akku SDK] Generation completed successfully!")
            print(json.dumps(result["result"], indent=2, ensure_ascii=False, default=str))
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
