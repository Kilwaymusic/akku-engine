"""
Akku SDK - Low-Poly Character Modeling Tools for Blender
"""
import bpy
import bmesh
import math

# ============================================
# 1. BODY PART GENERATORS (프로시저럴 파츠)
# ============================================

def create_robot_head(size=0.3, style="angular"):
    """로봇 헬멧/머리 생성"""
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, 1.7))
    head = bpy.context.active_object
    head.name = "Robot_Head"
    
    if style == "angular":
        # 각진 로봇 헬멧
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.transform.resize(value=(1.0, 0.8, 1.2))
        bpy.ops.object.mode_set(mode='OBJECT')
    
    return head

def create_shoulder_armor(side="left", size=0.15):
    """어깨 장갑 생성"""
    x = -0.35 if side == "left" else 0.35
    bpy.ops.mesh.primitive_cube_add(size=size, location=(x, 0, 1.4))
    armor = bpy.context.active_object
    armor.name = f"Shoulder_{side.capitalize()}"
    
    # 각진 형태로 변형
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.resize(value=(1.5, 1.2, 0.8))
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armor

def create_chest_plate(width=0.4, height=0.5, depth=0.15):
    """가슴 장갑 플레이트"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.1, 1.2))
    plate = bpy.context.active_object
    plate.name = "Chest_Plate"
    plate.scale = (width, depth, height)
    return plate

def create_visor(width=0.25, height=0.08):
    """로봇 바이저/눈"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.15, 1.72))
    visor = bpy.context.active_object
    visor.name = "Visor"
    visor.scale = (width, 0.02, height)
    return visor

# ============================================
# 2. STYLE MODIFIERS (스타일 변형기)
# ============================================

def apply_lowpoly_style(obj, target_faces=500):
    """로우폴리 스타일 적용"""
    decimate = obj.modifiers.new(name="LowPoly", type='DECIMATE')
    decimate.decimate_type = 'COLLAPSE'
    decimate.ratio = min(1.0, target_faces / max(len(obj.data.polygons), 1))
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="LowPoly")

def apply_armor_thickness(obj, thickness=0.02):
    """아머 두께 적용"""
    solidify = obj.modifiers.new(name="Armor", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = 1.0
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Armor")

def apply_bevel_edges(obj, width=0.01, segments=1):
    """엣지 베벨 (각진 느낌 완화)"""
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = width
    bevel.segments = segments
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Bevel")

def apply_chibi_proportions(armature):
    """치비 비율 적용 (머리 크게, 몸 작게)"""
    for bone in armature.pose.bones:
        if "head" in bone.name.lower():
            bone.scale = (1.5, 1.5, 1.5)
        elif "spine" in bone.name.lower():
            bone.scale = (0.8, 0.8, 0.7)
        elif "leg" in bone.name.lower():
            bone.scale = (0.6, 0.6, 0.6)

# ============================================
# 3. MATERIAL PRESETS (재질 프리셋)
# ============================================

MATERIAL_PRESETS = {
    "metal_blue": {"color": (0.1, 0.3, 1.0, 1.0), "metallic": 0.9, "roughness": 0.2},
    "metal_red": {"color": (1.0, 0.1, 0.1, 1.0), "metallic": 0.9, "roughness": 0.2},
    "metal_gold": {"color": (1.0, 0.8, 0.2, 1.0), "metallic": 1.0, "roughness": 0.1},
    "metal_silver": {"color": (0.85, 0.85, 0.9, 1.0), "metallic": 1.0, "roughness": 0.15},
    "metal_black": {"color": (0.05, 0.05, 0.08, 1.0), "metallic": 0.8, "roughness": 0.3},
    "plastic_white": {"color": (0.95, 0.95, 0.95, 1.0), "metallic": 0.0, "roughness": 0.4},
    "glow_cyan": {"color": (0.0, 1.0, 1.0, 1.0), "metallic": 0.0, "roughness": 0.0, "emission": 2.0},
    "glow_orange": {"color": (1.0, 0.5, 0.0, 1.0), "metallic": 0.0, "roughness": 0.0, "emission": 2.0},
}

def create_preset_material(preset_name):
    """프리셋 재질 생성"""
    if preset_name not in MATERIAL_PRESETS:
        preset_name = "metal_blue"
    
    preset = MATERIAL_PRESETS[preset_name]
    mat = bpy.data.materials.new(name=preset_name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    
    if bsdf:
        bsdf.inputs["Base Color"].default_value = preset["color"]
        bsdf.inputs["Metallic"].default_value = preset.get("metallic", 0.0)
        bsdf.inputs["Roughness"].default_value = preset.get("roughness", 0.5)
        if "emission" in preset:
            bsdf.inputs["Emission Strength"].default_value = preset["emission"]
            bsdf.inputs["Emission Color"].default_value = preset["color"]
    
    return mat

# ============================================
# 4. CHARACTER ASSEMBLER (캐릭터 조립기)
# ============================================

def assemble_robot_character(base_mesh, style="warrior"):
    """로봇 캐릭터 조립"""
    parts = []
    
    if style in ["warrior", "soldier", "전사"]:
        parts.append(create_shoulder_armor("left"))
        parts.append(create_shoulder_armor("right"))
        parts.append(create_chest_plate())
    
    if style in ["robot", "mech", "로봇"]:
        parts.append(create_robot_head())
        parts.append(create_visor())
    
    # 모든 파츠 합치기
    if parts:
        bpy.ops.object.select_all(action='DESELECT')
        for part in parts:
            part.select_set(True)
        if base_mesh:
            base_mesh.select_set(True)
            bpy.context.view_layer.objects.active = base_mesh
        bpy.ops.object.join()
    
    return bpy.context.active_object

# ============================================
# 5. POLY LEVEL MANAGER (폴리곤 레벨 관리)
# ============================================

POLY_TARGETS = {
    "ultra_low": 300,
    "low": 800,
    "medium": 1500,
    "high": 3000,
}

def set_poly_level(obj, level="medium"):
    """폴리곤 레벨 설정"""
    target = POLY_TARGETS.get(level, 1500)
    current = len(obj.data.polygons)
    
    if current > target:
        ratio = target / current
        decimate = obj.modifiers.new(name="PolyLevel", type='DECIMATE')
        decimate.ratio = ratio
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="PolyLevel")
    
    print(f"Poly level: {level}, Target: {target}, Final: {len(obj.data.polygons)}")

# ============================================
# 6. EXPORT UTILITIES (내보내기 유틸)
# ============================================

def export_glb(filepath, apply_modifiers=True):
    """GLB 내보내기"""
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        export_apply=apply_modifiers
    )
    print(f"Exported: {filepath}")
