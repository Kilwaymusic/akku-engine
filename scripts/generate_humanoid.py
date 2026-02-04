"""
Blender Python script to generate a simple humanoid character.
This creates a basic humanoid mesh with proper rigging for game engines.
"""
import bpy
import sys
import math
import random

def clear_scene():
    """Clear all objects from the scene."""
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

def create_material(name, color):
    """Create a simple material with given color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Roughness"].default_value = 0.5
        principled.inputs["Metallic"].default_value = 0.0
    return mat

def create_humanoid_body():
    """Create a simple humanoid body mesh."""
    # Body (torso)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.2))
    torso = bpy.context.active_object
    torso.name = "Torso"
    torso.scale = (0.4, 0.25, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, 1.8))
    head = bpy.context.active_object
    head.name = "Head"
    
    # Arms
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.5, location=(0.5, 0, 1.2))
    left_arm = bpy.context.active_object
    left_arm.name = "LeftArm"
    left_arm.rotation_euler = (0, 0, math.radians(90))
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.5, location=(-0.5, 0, 1.2))
    right_arm = bpy.context.active_object
    right_arm.name = "RightArm"
    right_arm.rotation_euler = (0, 0, math.radians(-90))
    
    # Legs
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.6, location=(0.15, 0, 0.4))
    left_leg = bpy.context.active_object
    left_leg.name = "LeftLeg"
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.6, location=(-0.15, 0, 0.4))
    right_leg = bpy.context.active_object
    right_leg.name = "RightLeg"
    
    # Hands (spheres)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(0.75, 0, 1.2))
    left_hand = bpy.context.active_object
    left_hand.name = "LeftHand"
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(-0.75, 0, 1.2))
    right_hand = bpy.context.active_object
    right_hand.name = "RightHand"
    
    # Feet (cubes)
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0.15, 0.05, 0.075))
    left_foot = bpy.context.active_object
    left_foot.name = "LeftFoot"
    left_foot.scale = (1, 1.5, 0.5)
    
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(-0.15, 0.05, 0.075))
    right_foot = bpy.context.active_object
    right_foot.name = "RightFoot"
    right_foot.scale = (1, 1.5, 0.5)
    
    return [torso, head, left_arm, right_arm, left_leg, right_leg, left_hand, right_hand, left_foot, right_foot]

def create_armature():
    """Create a simple armature for the humanoid."""
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Armature"
    
    arm = armature.data
    arm.name = "HumanoidRig"
    
    # Get the default bone and rename it as root
    root_bone = arm.edit_bones[0]
    root_bone.name = "Root"
    root_bone.head = (0, 0, 0)
    root_bone.tail = (0, 0, 0.2)
    
    # Spine
    spine = arm.edit_bones.new("Spine")
    spine.head = (0, 0, 0.7)
    spine.tail = (0, 0, 1.0)
    spine.parent = root_bone
    
    # Chest
    chest = arm.edit_bones.new("Chest")
    chest.head = (0, 0, 1.0)
    chest.tail = (0, 0, 1.4)
    chest.parent = spine
    
    # Neck
    neck = arm.edit_bones.new("Neck")
    neck.head = (0, 0, 1.5)
    neck.tail = (0, 0, 1.65)
    neck.parent = chest
    
    # Head
    head = arm.edit_bones.new("Head")
    head.head = (0, 0, 1.65)
    head.tail = (0, 0, 2.0)
    head.parent = neck
    
    # Left Arm
    l_shoulder = arm.edit_bones.new("LeftShoulder")
    l_shoulder.head = (0.2, 0, 1.35)
    l_shoulder.tail = (0.35, 0, 1.35)
    l_shoulder.parent = chest
    
    l_arm = arm.edit_bones.new("LeftArm")
    l_arm.head = (0.35, 0, 1.35)
    l_arm.tail = (0.55, 0, 1.15)
    l_arm.parent = l_shoulder
    
    l_forearm = arm.edit_bones.new("LeftForeArm")
    l_forearm.head = (0.55, 0, 1.15)
    l_forearm.tail = (0.75, 0, 1.2)
    l_forearm.parent = l_arm
    
    l_hand = arm.edit_bones.new("LeftHand")
    l_hand.head = (0.75, 0, 1.2)
    l_hand.tail = (0.85, 0, 1.2)
    l_hand.parent = l_forearm
    
    # Right Arm
    r_shoulder = arm.edit_bones.new("RightShoulder")
    r_shoulder.head = (-0.2, 0, 1.35)
    r_shoulder.tail = (-0.35, 0, 1.35)
    r_shoulder.parent = chest
    
    r_arm = arm.edit_bones.new("RightArm")
    r_arm.head = (-0.35, 0, 1.35)
    r_arm.tail = (-0.55, 0, 1.15)
    r_arm.parent = r_shoulder
    
    r_forearm = arm.edit_bones.new("RightForeArm")
    r_forearm.head = (-0.55, 0, 1.15)
    r_forearm.tail = (-0.75, 0, 1.2)
    r_forearm.parent = r_arm
    
    r_hand = arm.edit_bones.new("RightHand")
    r_hand.head = (-0.75, 0, 1.2)
    r_hand.tail = (-0.85, 0, 1.2)
    r_hand.parent = r_forearm
    
    # Hips
    hips = arm.edit_bones.new("Hips")
    hips.head = (0, 0, 0.7)
    hips.tail = (0, 0, 0.5)
    hips.parent = root_bone
    
    # Left Leg
    l_upleg = arm.edit_bones.new("LeftUpLeg")
    l_upleg.head = (0.15, 0, 0.7)
    l_upleg.tail = (0.15, 0, 0.4)
    l_upleg.parent = hips
    
    l_leg = arm.edit_bones.new("LeftLeg")
    l_leg.head = (0.15, 0, 0.4)
    l_leg.tail = (0.15, 0, 0.1)
    l_leg.parent = l_upleg
    
    l_foot = arm.edit_bones.new("LeftFoot")
    l_foot.head = (0.15, 0, 0.1)
    l_foot.tail = (0.15, 0.15, 0.05)
    l_foot.parent = l_leg
    
    # Right Leg
    r_upleg = arm.edit_bones.new("RightUpLeg")
    r_upleg.head = (-0.15, 0, 0.7)
    r_upleg.tail = (-0.15, 0, 0.4)
    r_upleg.parent = hips
    
    r_leg = arm.edit_bones.new("RightLeg")
    r_leg.head = (-0.15, 0, 0.4)
    r_leg.tail = (-0.15, 0, 0.1)
    r_leg.parent = r_upleg
    
    r_foot = arm.edit_bones.new("RightFoot")
    r_foot.head = (-0.15, 0, 0.1)
    r_foot.tail = (-0.15, 0.15, 0.05)
    r_foot.parent = r_leg
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature

def parse_prompt_for_colors(prompt):
    """Parse the prompt to determine character colors."""
    prompt_lower = prompt.lower()
    
    # Default colors
    skin_color = (0.9, 0.75, 0.6)  # Beige skin
    body_color = (0.2, 0.4, 0.8)   # Blue outfit
    
    # Color mappings
    color_map = {
        'red': (0.8, 0.2, 0.2),
        'blue': (0.2, 0.4, 0.8),
        'green': (0.2, 0.7, 0.3),
        'yellow': (0.9, 0.8, 0.2),
        'purple': (0.6, 0.2, 0.8),
        'orange': (0.9, 0.5, 0.1),
        'pink': (0.9, 0.5, 0.7),
        'black': (0.1, 0.1, 0.1),
        'white': (0.95, 0.95, 0.95),
        'gold': (0.85, 0.65, 0.2),
        'silver': (0.75, 0.75, 0.8),
        'cyan': (0.2, 0.8, 0.9),
        'magenta': (0.9, 0.2, 0.6),
        '빨간': (0.8, 0.2, 0.2),
        '파란': (0.2, 0.4, 0.8),
        '녹색': (0.2, 0.7, 0.3),
        '노란': (0.9, 0.8, 0.2),
        '보라': (0.6, 0.2, 0.8),
        '주황': (0.9, 0.5, 0.1),
        '분홍': (0.9, 0.5, 0.7),
        '검은': (0.1, 0.1, 0.1),
        '흰': (0.95, 0.95, 0.95),
        '금색': (0.85, 0.65, 0.2),
        '은색': (0.75, 0.75, 0.8),
        '메탈릭': (0.6, 0.6, 0.7),
    }
    
    for color_name, color_value in color_map.items():
        if color_name in prompt_lower:
            body_color = color_value
            break
    
    # Check for robot/mech keywords
    if any(word in prompt_lower for word in ['robot', '로봇', 'mech', '메카', 'android', '안드로이드', 'sf']):
        skin_color = (0.5, 0.5, 0.6)  # Metallic skin
    
    # Check for fantasy keywords
    if any(word in prompt_lower for word in ['elf', '엘프', 'fairy', '요정']):
        skin_color = (0.85, 0.9, 0.85)  # Pale greenish
    
    if any(word in prompt_lower for word in ['orc', '오크', 'goblin', '고블린']):
        skin_color = (0.4, 0.6, 0.35)  # Green
    
    return skin_color, body_color

def apply_materials(meshes, skin_color, body_color):
    """Apply materials to the humanoid meshes."""
    skin_mat = create_material("SkinMaterial", skin_color)
    body_mat = create_material("BodyMaterial", body_color)
    
    for mesh in meshes:
        if mesh.name in ["Head", "LeftHand", "RightHand"]:
            mesh.data.materials.append(skin_mat)
        else:
            mesh.data.materials.append(body_mat)

def join_meshes(meshes):
    """Join all meshes into a single object."""
    bpy.ops.object.select_all(action='DESELECT')
    
    for mesh in meshes:
        mesh.select_set(True)
    
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    
    result = bpy.context.active_object
    result.name = "Character"
    return result

def parent_to_armature(mesh, armature):
    """Parent mesh to armature with automatic weights."""
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

def export_glb(filepath):
    """Export the scene as GLB."""
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        export_apply=True,
        export_animations=True,
        export_skins=True,
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: blender --background --python generate_humanoid.py -- <output_path> [prompt]")
        sys.exit(1)
    
    # Parse arguments after "--"
    try:
        args_index = sys.argv.index("--") + 1
        output_path = sys.argv[args_index]
        prompt = sys.argv[args_index + 1] if len(sys.argv) > args_index + 1 else "default character"
    except (ValueError, IndexError):
        output_path = "/tmp/character.glb"
        prompt = "default character"
    
    print(f"Generating character with prompt: {prompt}")
    print(f"Output path: {output_path}")
    
    # Clear scene
    clear_scene()
    
    # Parse colors from prompt
    skin_color, body_color = parse_prompt_for_colors(prompt)
    
    # Create humanoid body
    meshes = create_humanoid_body()
    
    # Apply materials
    apply_materials(meshes, skin_color, body_color)
    
    # Join meshes
    character = join_meshes(meshes)
    
    # Create armature
    armature = create_armature()
    
    # Parent character to armature
    parent_to_armature(character, armature)
    
    # Export as GLB
    export_glb(output_path)
    
    print(f"Character exported to: {output_path}")

if __name__ == "__main__":
    main()
