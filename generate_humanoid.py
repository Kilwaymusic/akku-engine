import bpy
import sys
import os
import argparse

# SDK 임포트
sys.path.append("/home/composerkil/akku-engine")
from akku_sdk import (
    create_preset_material, assemble_robot_character,
    apply_armor_thickness, set_poly_level, export_glb,
    MATERIAL_PRESETS
)

# 색상-프리셋 매핑
COLOR_TO_PRESET = {
    "블루": "metal_blue", "파랑": "metal_blue", "blue": "metal_blue",
    "레드": "metal_red", "빨강": "metal_red", "red": "metal_red",
    "골드": "metal_gold", "금색": "metal_gold", "gold": "metal_gold",
    "실버": "metal_silver", "은색": "metal_silver", "silver": "metal_silver",
    "블랙": "metal_black", "검정": "metal_black", "black": "metal_black",
}

def find_preset(prompt):
    for keyword, preset in COLOR_TO_PRESET.items():
        if keyword in prompt.lower() or keyword in prompt:
            return preset
    return "metal_blue"

def detect_style(prompt):
    if any(k in prompt for k in ["전사", "warrior", "soldier"]):
        return "warrior"
    if any(k in prompt for k in ["로봇", "robot", "mech"]):
        return "robot"
    return "warrior"

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output.glb")
    parser.add_argument("--style", default="stylized")
    parser.add_argument("--poly", default="medium")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args(argv)

    # 씬 초기화
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # FBX 로드
    fbx_path = "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx"
    
    if os.path.exists(fbx_path):
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # 베이스 메시 찾기
        base_mesh = None
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                base_mesh = obj
                break
        
        # SDK 도구 사용
        char_style = detect_style(args.prompt)
        character = assemble_robot_character(base_mesh, style=char_style)
        
        if character:
            apply_armor_thickness(character, thickness=0.015)
            set_poly_level(character, args.poly)
            
            preset = find_preset(args.prompt)
            mat = create_preset_material(preset)
            character.data.materials.clear()
            character.data.materials.append(mat)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1))

    export_glb(args.output)

if __name__ == "__main__":
    main()
