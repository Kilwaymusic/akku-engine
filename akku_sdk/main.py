"""
Akku SDK Main - CLI Interface and Tool Registration
"""

import bpy
import sys
import json
import os
from typing import Dict, Any, Optional

from .core import AkkuLogger, AkkuConfig
from .tools import ToolRegistry, tool
from .mesh import MeshTools
from .shader import StylizedShaderSystem
from .body import BodyTypeSystem, BodyTypePresets
from .kitbash import KitbashLibrary, KitbashEquipper
from .rigging import AutoWeightTransfer
from .finalize import FinalizePipeline, DecimateEngine, PlatformTarget
from .handlers import FBXHandler, GLBHandler


@tool(name="clear_scene", category="scene")
def clear_scene(keep_camera: bool = True, keep_lights: bool = True) -> Dict:
    removed = 0
    for obj in list(bpy.data.objects):
        if keep_camera and obj.type == 'CAMERA':
            continue
        if keep_lights and obj.type == 'LIGHT':
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
        removed += 1
    return {"removed_objects": removed}


@tool(name="import_base_mesh", category="mesh")
def import_base_mesh(filepath: str = None, mesh_type: str = "mixamo") -> Dict:
    if not filepath:
        filepath = AkkuConfig.MIXAMO_FBX_PATH
    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}
    success = FBXHandler.import_fbx(filepath)
    return {"success": success, "filepath": filepath, "mesh_type": mesh_type}


@tool(name="apply_body_type", category="body")
def apply_body_type(preset: str = "default", custom_params: Dict = None) -> Dict:
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break
    if not armature:
        return {"success": False, "error": "No armature found"}
    if custom_params:
        from .body import BodyTypeParams
        params = BodyTypeParams(**custom_params)
    else:
        params = BodyTypePresets.get_preset(preset)
    success = BodyTypeSystem.apply_body_type(armature, params)
    return {"success": success, "preset": preset}


@tool(name="apply_shader", category="shader")
def apply_shader(color: tuple = (0.5, 0.5, 0.5), style: str = "stylized") -> Dict:
    applied = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            StylizedShaderSystem.apply_stylized_shader(obj, color, style)
            applied += 1
    return {"applied_to": applied, "color": color, "style": style}


@tool(name="equip_part", category="kitbash")
def equip_part(part_name: str, color: tuple = (0.5, 0.5, 0.5), style: str = "stylized") -> Dict:
    part = KitbashLibrary.get_part(part_name)
    if not part:
        available = [p.name for p in KitbashLibrary.query_parts()]
        return {"success": False, "error": f"Part not found: {part_name}", "available": available[:10]}
    obj = KitbashEquipper.equip_part(part, color, style)
    return {"success": obj is not None, "part": part_name, "equipped": obj.name if obj else None}


@tool(name="equip_set", category="kitbash")
def equip_set(style: str = "heavy", color: tuple = (0.5, 0.5, 0.5), shader_style: str = "stylized") -> Dict:
    equipment = KitbashLibrary.get_equipment_set(style)
    equipped = []
    for category, parts in equipment.items():
        for part in parts:
            obj = KitbashEquipper.equip_part(part, color, shader_style)
            if obj:
                equipped.append(part.name)
    return {"equipped": equipped, "count": len(equipped), "style": style}


@tool(name="finalize", category="export")
def finalize(platform: str = "mobile", target_tris: int = None) -> Dict:
    platform_enum = PlatformTarget.MOBILE
    for p in PlatformTarget:
        if p.value == platform:
            platform_enum = p
            break
    objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if target_tris:
        for obj in objects:
            DecimateEngine.decimate_to_target(obj, target_tris)
    results = FinalizePipeline.finalize_for_platform(objects, platform_enum)
    return results


@tool(name="export_glb", category="export")
def export_glb(filepath: str = "/tmp/output.glb") -> Dict:
    success = GLBHandler.export_glb(filepath)
    return {"success": success, "filepath": filepath}


@tool(name="auto_rig_all", category="rigging")
def auto_rig_all() -> Dict:
    rigged = 0
    failed = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'body' not in obj.name.lower():
            result = AutoWeightTransfer.auto_rig_part(obj)
            if result.success:
                rigged += 1
            else:
                failed += 1
    return {"rigged": rigged, "failed": failed}


@tool(name="list_parts", category="kitbash")
def list_parts(category: str = None, style: str = None) -> Dict:
    parts = KitbashLibrary.query_parts(category=category, style=style)
    return {"parts": [p.name for p in parts], "count": len(parts)}


def execute_plan(plan: Dict) -> Dict:
    results = {"steps": [], "success": True}
    for step in plan.get("steps", []):
        tool_name = step.get("tool")
        params = step.get("params", {})
        tool_func = ToolRegistry.get_tool(tool_name)
        if not tool_func:
            results["steps"].append({"tool": tool_name, "error": "Tool not found"})
            results["success"] = False
            continue
        try:
            result = tool_func(**params)
            results["steps"].append({"tool": tool_name, "result": result})
        except Exception as e:
            results["steps"].append({"tool": tool_name, "error": str(e)})
            results["success"] = False
    return results


def run_cli():
    if "--" not in sys.argv:
        print("Usage: blender --background --python run.py -- <command> [args]")
        return
    args = sys.argv[sys.argv.index("--") + 1:]
    if not args:
        print("Available tools:", list(ToolRegistry._tools.keys()))
        return
    command = args[0]
    if command == "list":
        for name, info in ToolRegistry._tools.items():
            print(f"  {name}: {info['category']}")
    elif command == "plan":
        if len(args) < 2:
            print("Usage: plan <json_file>")
            return
        with open(args[1], 'r') as f:
            plan = json.load(f)
        result = execute_plan(plan)
        print(json.dumps(result, indent=2))
    else:
        tool_func = ToolRegistry.get_tool(command)
        if tool_func:
            params = {}
            for arg in args[1:]:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    try:
                        params[k] = json.loads(v)
                    except:
                        params[k] = v
            result = tool_func(**params)
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown command: {command}")


if __name__ == "__main__":
    run_cli()
