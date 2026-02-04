"""Blender entry script for Akku SDK v3.6"""
import sys
import os
import json

sdk_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(sdk_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from akku_sdk.tools import ToolRegistry

def main():
    if "--" not in sys.argv:
        print("Usage: blender --background --python run.py -- <prompt> <style> <poly> <output> [gender] [body_type_json]")
        return
    
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) < 4:
        print("Need: prompt, style, poly_level, output_path")
        return
    
    prompt, style, poly_level, output_path = args[0], args[1], args[2], args[3]
    gender = args[4] if len(args) > 4 else "male"
    body_type_json = args[5] if len(args) > 5 else '{"preset":"auto"}'
    
    try:
        body_params = json.loads(body_type_json)
    except:
        body_params = {"preset": "auto"}
    
    print(f"\n{'='*60}")
    print(f"[Akku SDK v3.6] Character Generation")
    print(f"Prompt: {prompt}, Style: {style}, Poly: {poly_level}")
    print(f"Body params: {body_params}")
    print(f"{'='*60}\n")
    
    # Correct FBX paths
    base_path = "/home/composerkil/akku-engine/assets/base_meshes"
    if gender == "female":
        fbx_path = f"{base_path}/X_Bot.fbx"
    else:
        fbx_path = f"{base_path}/Y_Bot.fbx"
    
    print(f"[DEBUG] Using FBX: {fbx_path}")
    print(f"[DEBUG] File exists: {os.path.exists(fbx_path)}")
    
    # Step 1: Clear scene
    ToolRegistry.execute("clear_scene", {})
    print("[Step 1] Clear scene: OK")
    
    # Step 2: Import base mesh
    result = ToolRegistry.execute("import_base_mesh", {"filepath": fbx_path, "mesh_type": "mixamo"})
    print(f"[Step 2] Import mesh: {result.get('status')} - {result.get('message', '')}")
    
    # Step 3: Apply body type
    custom_params = {
        "muscular": body_params.get("muscular", 0.0),
        "fat": body_params.get("fat", 0.0),
        "shoulder_width": body_params.get("shoulderWidth", 0.0),
        "height": body_params.get("height", 0.0)
    }
    result = ToolRegistry.execute("apply_body_type", {
        "preset": body_params.get("preset", "default"),
        "custom_params": custom_params
    })
    print(f"[Step 3] Body type: {result.get('status')}")
    
    # Step 4: Apply shader
    result = ToolRegistry.execute("apply_shader", {"style": style, "color": (0.5, 0.5, 0.8)})
    print(f"[Step 4] Shader: {result.get('status')}")
    
    # Step 5: Finalize
    platform_map = {"ultra_low": "mobile", "low": "mobile", "medium": "mobile", "high": "pc"}
    platform = platform_map.get(poly_level, "mobile")
    result = ToolRegistry.execute("finalize", {"platform": platform})
    print(f"[Step 5] Finalize: {result.get('status')}")
    
    # Step 6: Export GLB
    result = ToolRegistry.execute("export_glb", {"filepath": output_path})
    print(f"[Step 6] Export: {result.get('status')}")
    
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"\n[SUCCESS] Generated {output_path} ({size} bytes)")
    else:
        print(f"\n[FAILED] Output not created")

if __name__ == "__main__":
    main()
