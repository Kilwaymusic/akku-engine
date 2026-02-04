"""
Akku SDK v3.6 - Blender Entry Point
Uses modular akku_sdk package
"""

import bpy
import sys
import os
import json

# Add SDK path
sdk_path = os.path.dirname(os.path.abspath(__file__))
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from akku_sdk import (
    AkkuLogger, AkkuConfig,
    clear_scene, import_base_mesh, apply_body_type,
    apply_shader, equip_set, finalize, export_glb
)
from akku_sdk.kitbash import KitbashLibrary

# Color mappings
COLOR_MAP = {
    "red": (0.8, 0.1, 0.1), "blue": (0.1, 0.2, 0.8), "green": (0.1, 0.6, 0.1),
    "gold": (0.8, 0.6, 0.1), "silver": (0.7, 0.7, 0.75), "black": (0.1, 0.1, 0.1),
    "white": (0.9, 0.9, 0.9), "purple": (0.5, 0.1, 0.6), "orange": (0.9, 0.4, 0.1),
    "빨강": (0.8, 0.1, 0.1), "파랑": (0.1, 0.2, 0.8), "초록": (0.1, 0.6, 0.1),
    "금색": (0.8, 0.6, 0.1), "은색": (0.7, 0.7, 0.75), "검정": (0.1, 0.1, 0.1),
}

POLY_TARGETS = {"ultra_low": 300, "low": 800, "medium": 1500, "high": 3000}


def detect_color(prompt: str) -> tuple:
    prompt_lower = prompt.lower()
    for color_name, color_value in COLOR_MAP.items():
        if color_name in prompt_lower:
            return color_value
    return (0.5, 0.5, 0.5)


def detect_body_type(prompt: str, body_type_hint: str = "auto") -> str:
    if body_type_hint != "auto":
        return body_type_hint
    prompt_lower = prompt.lower()
    mappings = {
        "muscular": ["muscular", "강한", "근육", "buff", "strong"],
        "thin": ["thin", "마른", "slim", "skinny"],
        "heroic": ["hero", "영웅", "heroic"],
        "athletic": ["athletic", "운동"],
        "fat": ["fat", "뚱뚱"],
        "tall": ["tall", "키큰"],
        "chibi": ["chibi", "치비", "cute"],
    }
    for preset, keywords in mappings.items():
        if any(kw in prompt_lower for kw in keywords):
            return preset
    return "default"


def detect_equipment_style(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["knight", "기사", "armor", "갑옷", "warrior", "전사"]):
        return "heavy"
    if any(w in prompt_lower for w in ["mage", "마법사", "wizard", "magic"]):
        return "magic"
    if any(w in prompt_lower for w in ["scifi", "robot", "로봇", "cyber"]):
        return "scifi"
    return "heavy"


def generate_character(prompt: str, style: str, poly_level: str, output_path: str, gender: str = "male", body_type: str = "auto", use_remesh: bool = False):
    AkkuLogger.info(f"Starting generation: {prompt}")
    
    # Clear scene
    clear_scene()
    
    # Import base mesh
    result = import_base_mesh()
    if not result.get("success"):
        AkkuLogger.error(f"Failed to import base mesh: {result}")
        return False
    
    # Apply body type
    detected_body = detect_body_type(prompt, body_type)
    apply_body_type(preset=detected_body)
    
    # Detect color and style
    color = detect_color(prompt)
    equip_style = detect_equipment_style(prompt)
    
    # Apply shader to body
    apply_shader(color=color, style=style)
    
    # Equip armor set
    equip_set(style=equip_style, color=color, shader_style=style)
    
    # Finalize with target poly count
    target_tris = POLY_TARGETS.get(poly_level, 1500)
    finalize(platform="mobile", target_tris=target_tris)
    
    # Export GLB
    result = export_glb(filepath=output_path)
    
    AkkuLogger.info(f"Generation complete: {output_path}")
    return result.get("success", False)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    
    if len(args) < 4:
        print("Usage: blender --background --python akku-sdk-v3.py -- <prompt> <style> <poly_level> <output_path> [gender] [body_type] [use_remesh]")
        sys.exit(1)
    
    prompt = args[0]
    style = args[1]
    poly_level = args[2]
    output_path = args[3]
    gender = args[4] if len(args) > 4 else "male"
    body_type = args[5] if len(args) > 5 else "auto"
    use_remesh = args[6].lower() == "true" if len(args) > 6 else False
    
    success = generate_character(prompt, style, poly_level, output_path, gender, body_type, use_remesh)
    sys.exit(0 if success else 1)
