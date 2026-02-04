"""
Akku SDK Finalize - Game Engine Optimization Pipeline
Unity/Unreal-ready export with LOD, decimation, and mesh optimization
"""

import bpy
import bmesh
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .core import AkkuLogger, MeshStats


class PlatformTarget(Enum):
    MOBILE_LOW = "mobile_low"
    MOBILE = "mobile"
    MOBILE_HIGH = "mobile_high"
    PC_LOW = "pc_low"
    PC = "pc"
    PC_HIGH = "pc_high"


@dataclass
class PlatformProfile:
    max_tris: int
    max_materials: int
    max_texture_size: int
    lod_levels: int


PLATFORM_PROFILES: Dict[PlatformTarget, PlatformProfile] = {
    PlatformTarget.MOBILE_LOW: PlatformProfile(300, 1, 256, 2),
    PlatformTarget.MOBILE: PlatformProfile(800, 2, 512, 3),
    PlatformTarget.MOBILE_HIGH: PlatformProfile(1500, 3, 1024, 3),
    PlatformTarget.PC_LOW: PlatformProfile(3000, 4, 1024, 4),
    PlatformTarget.PC: PlatformProfile(8000, 6, 2048, 4),
    PlatformTarget.PC_HIGH: PlatformProfile(20000, 8, 4096, 4),
}


class MeshOptimizer:
    @staticmethod
    def remove_doubles(obj: bpy.types.Object, threshold: float = 0.0001) -> int:
        if not obj or obj.type != 'MESH':
            return 0
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        result = bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=threshold)
        removed = len(result.get('verts', [])) if result else 0
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return removed
    
    @staticmethod
    def dissolve_degenerate(obj: bpy.types.Object, threshold: float = 0.0001) -> int:
        if not obj or obj.type != 'MESH':
            return 0
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        initial = len(bm.faces)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=threshold)
        dissolved = initial - len(bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return dissolved
    
    @staticmethod
    def recalculate_normals(obj: bpy.types.Object) -> bool:
        if not obj or obj.type != 'MESH':
            return False
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return True
    
    @staticmethod
    def optimize_mesh(obj: bpy.types.Object) -> Dict:
        results = {"doubles_removed": 0, "degenerate_dissolved": 0, "normals_fixed": False}
        results["doubles_removed"] = MeshOptimizer.remove_doubles(obj)
        results["degenerate_dissolved"] = MeshOptimizer.dissolve_degenerate(obj)
        results["normals_fixed"] = MeshOptimizer.recalculate_normals(obj)
        AkkuLogger.info(f"Optimized mesh: {obj.name}", results)
        return results


class MaterialOptimizer:
    @staticmethod
    def merge_identical_materials(objects: List[bpy.types.Object]) -> int:
        material_map = {}
        merged = 0
        for obj in objects:
            if not obj.data or not hasattr(obj.data, 'materials'):
                continue
            for i, mat in enumerate(obj.data.materials):
                if not mat:
                    continue
                key = (mat.diffuse_color[:3] if hasattr(mat, 'diffuse_color') else (0.5, 0.5, 0.5))
                if key in material_map:
                    obj.data.materials[i] = material_map[key]
                    merged += 1
                else:
                    material_map[key] = mat
        return merged
    
    @staticmethod
    def consolidate_to_single(obj: bpy.types.Object, base_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)) -> bool:
        if not obj or obj.type != 'MESH':
            return False
        obj.data.materials.clear()
        mat = bpy.data.materials.new(name=f"{obj.name}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        obj.data.materials.append(mat)
        return True
    
    @staticmethod
    def reduce_to_limit(obj: bpy.types.Object, max_materials: int) -> int:
        if not obj or obj.type != 'MESH':
            return 0
        current = len(obj.data.materials)
        if current <= max_materials:
            return 0
        removed = current - max_materials
        while len(obj.data.materials) > max_materials:
            obj.data.materials.pop()
        return removed


class DecimateEngine:
    @staticmethod
    def get_triangle_count(obj: bpy.types.Object) -> int:
        if not obj or obj.type != 'MESH':
            return 0
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        mesh.calc_loop_triangles()
        count = len(mesh.loop_triangles)
        obj_eval.to_mesh_clear()
        return count
    
    @staticmethod
    def decimate_to_target(obj: bpy.types.Object, target_tris: int, min_ratio: float = 0.1) -> Tuple[int, int]:
        if not obj or obj.type != 'MESH':
            return 0, 0
        initial = DecimateEngine.get_triangle_count(obj)
        if initial <= target_tris:
            return initial, initial
        ratio = max(min_ratio, target_tris / initial)
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        try:
            bmesh.ops.dissolve_limit(bm, angle_limit=0.1, verts=bm.verts, edges=bm.edges)
        except:
            pass
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        new_mesh = bpy.data.meshes.new_from_object(obj_eval)
        obj.modifiers.remove(mod)
        old_mesh = obj.data
        obj.data = new_mesh
        bpy.data.meshes.remove(old_mesh)
        final = DecimateEngine.get_triangle_count(obj)
        AkkuLogger.info(f"Decimated {obj.name}: {initial} -> {final} tris")
        return initial, final


class MeshJoiner:
    @staticmethod
    def join_objects(objects: List[bpy.types.Object], name: str = "Joined_Mesh") -> Optional[bpy.types.Object]:
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        if not mesh_objects:
            return None
        if len(mesh_objects) == 1:
            return mesh_objects[0]
        combined_mesh = bpy.data.meshes.new(name=f"{name}_mesh")
        combined_obj = bpy.data.objects.new(name=name, object_data=combined_mesh)
        bpy.context.scene.collection.objects.link(combined_obj)
        bm = bmesh.new()
        for obj in mesh_objects:
            temp_mesh = obj.to_mesh()
            temp_bm = bmesh.new()
            temp_bm.from_mesh(temp_mesh)
            temp_bm.transform(obj.matrix_world)
            for vert in temp_bm.verts:
                bm.verts.new(vert.co)
            bm.verts.ensure_lookup_table()
            vert_offset = len(bm.verts) - len(temp_bm.verts)
            for face in temp_bm.faces:
                try:
                    new_verts = [bm.verts[v.index + vert_offset] for v in face.verts]
                    bm.faces.new(new_verts)
                except:
                    pass
            temp_bm.free()
            obj.to_mesh_clear()
        bm.to_mesh(combined_mesh)
        bm.free()
        combined_mesh.update()
        for obj in mesh_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        AkkuLogger.info(f"Joined {len(mesh_objects)} meshes into {name}")
        return combined_obj


class LODGenerator:
    LOD_RATIOS = [1.0, 0.5, 0.25, 0.125]
    
    @staticmethod
    def generate_lod_chain(obj: bpy.types.Object, num_levels: int = 4) -> List[bpy.types.Object]:
        if not obj or obj.type != 'MESH':
            return []
        lods = [obj]
        obj.name = f"{obj.name}_LOD0"
        base_tris = DecimateEngine.get_triangle_count(obj)
        for i in range(1, min(num_levels, len(LODGenerator.LOD_RATIOS))):
            lod_obj = obj.copy()
            lod_obj.data = obj.data.copy()
            lod_obj.name = f"{obj.name.replace('_LOD0', '')}_LOD{i}"
            bpy.context.scene.collection.objects.link(lod_obj)
            target = int(base_tris * LODGenerator.LOD_RATIOS[i])
            DecimateEngine.decimate_to_target(lod_obj, target)
            lods.append(lod_obj)
        AkkuLogger.info(f"Generated {len(lods)} LOD levels")
        return lods


class FinalizePipeline:
    @staticmethod
    def finalize_for_platform(objects: List[bpy.types.Object], platform: PlatformTarget = PlatformTarget.MOBILE) -> Dict:
        profile = PLATFORM_PROFILES[platform]
        results = {"platform": platform.value, "objects_processed": 0, "total_tris": 0}
        for obj in objects:
            if obj.type != 'MESH':
                continue
            MeshOptimizer.optimize_mesh(obj)
            DecimateEngine.decimate_to_target(obj, profile.max_tris)
            MaterialOptimizer.reduce_to_limit(obj, profile.max_materials)
            results["objects_processed"] += 1
        MaterialOptimizer.merge_identical_materials(objects)
        for obj in objects:
            if obj.type == 'MESH':
                results["total_tris"] += DecimateEngine.get_triangle_count(obj)
        AkkuLogger.info(f"Finalized for {platform.value}", results)
        results["success"] = True
        return results
    
    @staticmethod
    def quick_optimize(obj: bpy.types.Object, target_tris: int = 1500) -> Dict:
        results = {}
        results["optimization"] = MeshOptimizer.optimize_mesh(obj)
        initial, final = DecimateEngine.decimate_to_target(obj, target_tris)
        results["decimation"] = {"initial": initial, "final": final}
        return results
    
    @staticmethod
    def full_pipeline(objects: List[bpy.types.Object], platform: PlatformTarget = PlatformTarget.MOBILE, generate_lods: bool = False) -> Dict:
        results = FinalizePipeline.finalize_for_platform(objects, platform)
        if generate_lods:
            profile = PLATFORM_PROFILES[platform]
            for obj in objects:
                if obj.type == 'MESH':
                    LODGenerator.generate_lod_chain(obj, profile.lod_levels)
        return results
