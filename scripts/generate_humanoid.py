"""
Blender Python script to generate a 3D humanoid character.
Accepts JSON parameters from Gemini AI for customization.
"""
import bpy
import sys
import math
import json

def clear_scene():
    """Clear all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.armatures:
        if block.users == 0:
            bpy.data.armatures.remove(block)

def create_material(name, color, roughness=0.5, metallic=0.0):
    """Create a material with given color and properties."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metallic
    return mat

def create_humanoid_body(params):
    """Create a humanoid body mesh with given parameters."""
    head_scale = params.get("headScale", [1.0, 1.0, 1.0])
    torso_scale = params.get("torsoScale", [1.0, 1.0, 1.0])
    arm_length = params.get("armLength", 1.0)
    leg_length = params.get("legLength", 1.0)
    
    # Body (torso)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.2))
    torso = bpy.context.active_object
    torso.name = "Torso"
    torso.scale = (0.4 * torso_scale[0], 0.25 * torso_scale[1], 0.5 * torso_scale[2])
    bpy.ops.object.transform_apply(scale=True)
    
    # Head
    head_radius = 0.2 * max(head_scale)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=head_radius, location=(0, 0, 1.8))
    head = bpy.context.active_object
    head.name = "Head"
    head.scale = (head_scale[0], head_scale[1], head_scale[2])
    bpy.ops.object.transform_apply(scale=True)
    
    # Arms
    arm_depth = 0.5 * arm_length
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=arm_depth, location=(0.5 * arm_length, 0, 1.2))
    left_arm = bpy.context.active_object
    left_arm.name = "LeftArm"
    left_arm.rotation_euler = (0, 0, math.radians(90))
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=arm_depth, location=(-0.5 * arm_length, 0, 1.2))
    right_arm = bpy.context.active_object
    right_arm.name = "RightArm"
    right_arm.rotation_euler = (0, 0, math.radians(-90))
    
    # Legs
    leg_depth = 0.6 * leg_length
    leg_y = 0.4 * leg_length
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=leg_depth, location=(0.15, 0, leg_y))
    left_leg = bpy.context.active_object
    left_leg.name = "LeftLeg"
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=leg_depth, location=(-0.15, 0, leg_y))
    right_leg = bpy.context.active_object
    right_leg.name = "RightLeg"
    
    # Hands
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(0.75 * arm_length, 0, 1.2))
    left_hand = bpy.context.active_object
    left_hand.name = "LeftHand"
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(-0.75 * arm_length, 0, 1.2))
    right_hand = bpy.context.active_object
    right_hand.name = "RightHand"
    
    # Feet
    foot_y = 0.075 * leg_length
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0.15, 0.05, foot_y))
    left_foot = bpy.context.active_object
    left_foot.name = "LeftFoot"
    left_foot.scale = (1, 1.5, 0.5)
    
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(-0.15, 0.05, foot_y))
    right_foot = bpy.context.active_object
    right_foot.name = "RightFoot"
    right_foot.scale = (1, 1.5, 0.5)
    
    return [torso, head, left_arm, right_arm, left_leg, right_leg, left_hand, right_hand, left_foot, right_foot]

def create_armature(params):
    """Create a simple armature for the humanoid."""
    arm_length = params.get("armLength", 1.0)
    leg_length = params.get("legLength", 1.0)
    
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "Armature"
    
    arm = armature.data
    arm.name = "HumanoidRig"
    
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
    l_shoulder.tail = (0.35 * arm_length, 0, 1.35)
    l_shoulder.parent = chest
    
    l_arm = arm.edit_bones.new("LeftArm")
    l_arm.head = (0.35 * arm_length, 0, 1.35)
    l_arm.tail = (0.55 * arm_length, 0, 1.15)
    l_arm.parent = l_shoulder
    
    l_forearm = arm.edit_bones.new("LeftForeArm")
    l_forearm.head = (0.55 * arm_length, 0, 1.15)
    l_forearm.tail = (0.75 * arm_length, 0, 1.2)
    l_forearm.parent = l_arm
    
    l_hand = arm.edit_bones.new("LeftHand")
    l_hand.head = (0.75 * arm_length, 0, 1.2)
    l_hand.tail = (0.85 * arm_length, 0, 1.2)
    l_hand.parent = l_forearm
    
    # Right Arm
    r_shoulder = arm.edit_bones.new("RightShoulder")
    r_shoulder.head = (-0.2, 0, 1.35)
    r_shoulder.tail = (-0.35 * arm_length, 0, 1.35)
    r_shoulder.parent = chest
    
    r_arm = arm.edit_bones.new("RightArm")
    r_arm.head = (-0.35 * arm_length, 0, 1.35)
    r_arm.tail = (-0.55 * arm_length, 0, 1.15)
    r_arm.parent = r_shoulder
    
    r_forearm = arm.edit_bones.new("RightForeArm")
    r_forearm.head = (-0.55 * arm_length, 0, 1.15)
    r_forearm.tail = (-0.75 * arm_length, 0, 1.2)
    r_forearm.parent = r_arm
    
    r_hand = arm.edit_bones.new("RightHand")
    r_hand.head = (-0.75 * arm_length, 0, 1.2)
    r_hand.tail = (-0.85 * arm_length, 0, 1.2)
    r_hand.parent = r_forearm
    
    # Hips
    hips = arm.edit_bones.new("Hips")
    hips.head = (0, 0, 0.7)
    hips.tail = (0, 0, 0.5)
    hips.parent = root_bone
    
    # Left Leg
    l_upleg = arm.edit_bones.new("LeftUpLeg")
    l_upleg.head = (0.15, 0, 0.7 * leg_length)
    l_upleg.tail = (0.15, 0, 0.4 * leg_length)
    l_upleg.parent = hips
    
    l_leg = arm.edit_bones.new("LeftLeg")
    l_leg.head = (0.15, 0, 0.4 * leg_length)
    l_leg.tail = (0.15, 0, 0.1 * leg_length)
    l_leg.parent = l_upleg
    
    l_foot = arm.edit_bones.new("LeftFoot")
    l_foot.head = (0.15, 0, 0.1 * leg_length)
    l_foot.tail = (0.15, 0.15, 0.05 * leg_length)
    l_foot.parent = l_leg
    
    # Right Leg
    r_upleg = arm.edit_bones.new("RightUpLeg")
    r_upleg.head = (-0.15, 0, 0.7 * leg_length)
    r_upleg.tail = (-0.15, 0, 0.4 * leg_length)
    r_upleg.parent = hips
    
    r_leg = arm.edit_bones.new("RightLeg")
    r_leg.head = (-0.15, 0, 0.4 * leg_length)
    r_leg.tail = (-0.15, 0, 0.1 * leg_length)
    r_leg.parent = r_upleg
    
    r_foot = arm.edit_bones.new("RightFoot")
    r_foot.head = (-0.15, 0, 0.1 * leg_length)
    r_foot.tail = (-0.15, 0.15, 0.05 * leg_length)
    r_foot.parent = r_leg
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature

def apply_materials(meshes, params):
    """Apply materials to the humanoid meshes based on Gemini parameters."""
    skin_color = tuple(params.get("skinColor", [0.9, 0.75, 0.6]))
    body_color = tuple(params.get("bodyColor", [0.2, 0.4, 0.8]))
    roughness = params.get("roughness", 0.5)
    metallic = params.get("metallic", 0.0)
    
    skin_mat = create_material("SkinMaterial", skin_color, roughness, metallic)
    body_mat = create_material("BodyMaterial", body_color, roughness, metallic)
    
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
    # Parse arguments after "--"
    try:
        args_index = sys.argv.index("--") + 1
        output_path = sys.argv[args_index]
        params_json = sys.argv[args_index + 1] if len(sys.argv) > args_index + 1 else "{}"
    except (ValueError, IndexError):
        output_path = "/tmp/character.glb"
        params_json = "{}"
    
    # Parse JSON parameters from Gemini
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON parameters, using defaults")
        params = {}
    
    print(f"Generating character with parameters: {json.dumps(params, indent=2)}")
    print(f"Output path: {output_path}")
    
    # Clear scene
    clear_scene()
    
    # Create humanoid body with parameters
    meshes = create_humanoid_body(params)
    
    # Apply materials
    apply_materials(meshes, params)
    
    # Join meshes
    character = join_meshes(meshes)
    
    # Create armature
    armature = create_armature(params)
    
    # Parent character to armature
    parent_to_armature(character, armature)
    
    # Export as GLB
    export_glb(output_path)
    
    print(f"Character exported to: {output_path}")

if __name__ == "__main__":
    main()
