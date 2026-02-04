"""
Akku SDK Mesh - Mesh Operations, Undo System, Boolean/Remesh
"""

import bpy
import bmesh
from typing import Dict, List, Optional, Tuple
from mathutils import Vector, Matrix

from .core import AkkuLogger, MeshStats


class MeshSnapshot:
    """Stores a snapshot of mesh data for undo operations"""
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Can only snapshot mesh objects")
        
        self.object_name = obj.name
        self.mesh_data = None
        self._capture(obj)
    
    def _capture(self, obj: bpy.types.Object):
        """Capture current mesh state"""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        self.vertices = [(v.co.x, v.co.y, v.co.z) for v in bm.verts]
        
        bm.verts.ensure_lookup_table()
        self.faces = [[v.index for v in f.verts] for f in bm.faces]
        
        self.materials = [slot.material.name if slot.material else None 
                         for slot in obj.material_slots]
        
        self.location = tuple(obj.location)
        self.rotation = tuple(obj.rotation_euler)
        self.scale = tuple(obj.scale)
        
        bm.free()
        AkkuLogger.debug(f"Captured snapshot of '{obj.name}'", {
            "vertices": len(self.vertices),
            "faces": len(self.faces)
        })
    
    def restore(self) -> bool:
        """Restore mesh to snapshot state"""
        obj = bpy.data.objects.get(self.object_name)
        if not obj or obj.type != 'MESH':
            AkkuLogger.error(f"Cannot restore: object '{self.object_name}' not found")
            return False
        
        try:
            bm = bmesh.new()
            
            for co in self.vertices:
                bm.verts.new(Vector(co))
            
            bm.verts.ensure_lookup_table()
            
            for face_indices in self.faces:
                try:
                    verts = [bm.verts[i] for i in face_indices]
                    bm.faces.new(verts)
                except:
                    pass
            
            obj.data.clear_geometry()
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.location = Vector(self.location)
            obj.rotation_euler = self.rotation
            obj.scale = Vector(self.scale)
            
            obj.data.update()
            
            AkkuLogger.info(f"Restored snapshot of '{self.object_name}'")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to restore snapshot: {str(e)}")
            return False


class UndoManager:
    """Manages undo states for mesh operations"""
    
    _snapshots: Dict[str, List[MeshSnapshot]] = {}
    _max_history = 10
    
    @classmethod
    def save_state(cls, obj: bpy.types.Object, label: str = ""):
        """Save current state for potential undo"""
        if obj.type != 'MESH':
            return
        
        obj_name = obj.name
        if obj_name not in cls._snapshots:
            cls._snapshots[obj_name] = []
        
        snapshot = MeshSnapshot(obj)
        cls._snapshots[obj_name].append(snapshot)
        
        if len(cls._snapshots[obj_name]) > cls._max_history:
            cls._snapshots[obj_name].pop(0)
        
        AkkuLogger.debug(f"Saved undo state for '{obj_name}'", {"label": label})
    
    @classmethod
    def undo(cls, obj_name: str) -> bool:
        """Undo to previous state"""
        if obj_name not in cls._snapshots or not cls._snapshots[obj_name]:
            AkkuLogger.warning(f"No undo history for '{obj_name}'")
            return False
        
        snapshot = cls._snapshots[obj_name].pop()
        return snapshot.restore()
    
    @classmethod
    def clear(cls, obj_name: str = None):
        """Clear undo history"""
        if obj_name:
            cls._snapshots.pop(obj_name, None)
        else:
            cls._snapshots.clear()


class MeshTools:
    """Low-level mesh manipulation tools - Context Independent"""
    
    @staticmethod
    def clear_scene():
        """Clear all objects from scene"""
        while bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[0], do_unlink=True)
        
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        
        for mat in list(bpy.data.materials):
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        
        for arm in list(bpy.data.armatures):
            if arm.users == 0:
                bpy.data.armatures.remove(arm)
        
        for action in list(bpy.data.actions):
            if action.users == 0:
                bpy.data.actions.remove(action)
        
        AkkuLogger.info("Scene cleared")
    
    @staticmethod
    def get_mesh_bounds(obj) -> Tuple[Vector, Vector, float]:
        """Get mesh bounding box and height"""
        if obj.type != 'MESH':
            return Vector((0, 0, 0)), Vector((0, 0, 0)), 0
        
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        min_co = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
        max_co = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
        height = max_co.z - min_co.z
        
        return min_co, max_co, height
    
    @staticmethod
    def normalize_scale(obj, target_height: float = 1.8):
        """Normalize object to target height using bmesh"""
        if obj.type != 'MESH':
            return 1.0
        
        UndoManager.save_state(obj, "before_normalize")
        
        _, _, current_height = MeshTools.get_mesh_bounds(obj)
        
        if current_height > 0:
            scale_factor = target_height / current_height
            
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            bmesh.ops.scale(
                bm,
                vec=Vector((scale_factor, scale_factor, scale_factor)),
                space=Matrix.Identity(4),
                verts=bm.verts
            )
            
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.scale = (1.0, 1.0, 1.0)
            obj.data.update()
            
            AkkuLogger.info(f"Normalized scale: {current_height:.2f}m -> {target_height:.2f}m", {
                "scale_factor": scale_factor
            })
            return scale_factor
        return 1.0
    
    @staticmethod
    def apply_modifier_via_depsgraph(obj, modifier_name: str):
        """Apply modifier using depsgraph - Context Independent"""
        if obj.type != 'MESH' or modifier_name not in obj.modifiers:
            return
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh_eval = obj_eval.to_mesh()
        
        bm = bmesh.new()
        bm.from_mesh(mesh_eval)
        obj.data.clear_geometry()
        bm.to_mesh(obj.data)
        bm.free()
        
        obj_eval.to_mesh_clear()
        obj.modifiers.remove(obj.modifiers[modifier_name])
        obj.data.update()
    
    @staticmethod
    def decimate_mesh(obj, ratio: float):
        """Decimate mesh with modifier + depsgraph"""
        if obj.type != 'MESH':
            return
        
        UndoManager.save_state(obj, "before_decimate")
        
        mod = obj.modifiers.new(name="AkkuDecimate", type='DECIMATE')
        mod.ratio = max(0.1, min(1.0, ratio))
        mod.use_collapse_triangulate = True
        
        MeshTools.apply_modifier_via_depsgraph(obj, "AkkuDecimate")
        AkkuLogger.info(f"Applied decimation", {"ratio": ratio})
    
    @staticmethod
    def triangulate_mesh(obj):
        """Triangulate mesh using bmesh"""
        if obj.type != 'MESH':
            return
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        AkkuLogger.info("Mesh triangulated")
    
    @staticmethod
    def get_triangle_count(obj) -> int:
        """Get triangle count for mesh"""
        if obj.type != 'MESH':
            return 0
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tri_count = len(bm.faces)
        bm.free()
        
        return tri_count


class BooleanRemeshTools:
    """Advanced mesh operations: Boolean Union, Voxel Remesh, Smoothing"""
    
    @staticmethod
    def boolean_union(target_obj: bpy.types.Object, source_obj: bpy.types.Object) -> bool:
        """Perform Boolean Union operation using modifier"""
        if target_obj.type != 'MESH' or source_obj.type != 'MESH':
            AkkuLogger.error("Boolean union requires mesh objects")
            return False
        
        UndoManager.save_state(target_obj, "before_boolean_union")
        
        try:
            mod = target_obj.modifiers.new(name="AkkuBoolean", type='BOOLEAN')
            mod.operation = 'UNION'
            mod.object = source_obj
            mod.solver = 'FAST'
            
            MeshTools.apply_modifier_via_depsgraph(target_obj, "AkkuBoolean")
            
            bpy.data.objects.remove(source_obj, do_unlink=True)
            
            AkkuLogger.info("Boolean union completed", {"target": target_obj.name})
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Boolean union failed: {str(e)}")
            UndoManager.undo(target_obj.name)
            return False
    
    @staticmethod
    def union_all_meshes() -> Optional[bpy.types.Object]:
        """Union all mesh objects in scene into a single mesh"""
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        if len(mesh_objects) == 0:
            AkkuLogger.warning("No mesh objects to union")
            return None
        
        if len(mesh_objects) == 1:
            AkkuLogger.info("Only one mesh object, no union needed")
            return mesh_objects[0]
        
        target = mesh_objects[0]
        UndoManager.save_state(target, "before_union_all")
        
        bm = bmesh.new()
        bm.from_mesh(target.data)
        
        for obj in mesh_objects[1:]:
            temp_bm = bmesh.new()
            temp_bm.from_mesh(obj.data)
            
            for v in temp_bm.verts:
                v.co = obj.matrix_world @ v.co
            
            temp_bm.to_mesh(target.data)
            bm.from_mesh(target.data)
            temp_bm.free()
            
            bpy.data.objects.remove(obj, do_unlink=True)
        
        bm.to_mesh(target.data)
        bm.free()
        target.data.update()
        
        AkkuLogger.info("Unified all meshes", {
            "result_name": target.name,
            "original_count": len(mesh_objects)
        })
        
        return target
    
    @staticmethod
    def voxel_remesh(obj: bpy.types.Object, voxel_size: float = 0.02) -> bool:
        """Apply Voxel Remesh to create organic geometry"""
        if obj.type != 'MESH':
            AkkuLogger.error("Voxel remesh requires mesh object")
            return False
        
        UndoManager.save_state(obj, "before_voxel_remesh")
        
        try:
            mod = obj.modifiers.new(name="AkkuRemesh", type='REMESH')
            mod.mode = 'VOXEL'
            mod.voxel_size = voxel_size
            mod.use_smooth_shade = False
            mod.adaptivity = 0.0
            
            MeshTools.apply_modifier_via_depsgraph(obj, "AkkuRemesh")
            
            from .tools import MeshAnalyzer
            stats = MeshAnalyzer.get_stats(obj)
            AkkuLogger.info("Voxel remesh completed", {
                "voxel_size": voxel_size,
                "new_vertex_count": stats.vertex_count,
                "new_face_count": stats.face_count
            })
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Voxel remesh failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @staticmethod
    def smooth_mesh(obj: bpy.types.Object, iterations: int = 2, factor: float = 0.5) -> bool:
        """Apply smoothing to mesh"""
        if obj.type != 'MESH':
            return False
        
        UndoManager.save_state(obj, "before_smooth")
        
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            for _ in range(iterations):
                bmesh.ops.smooth_vert(
                    bm,
                    verts=bm.verts,
                    factor=factor,
                    use_axis_x=True,
                    use_axis_y=True,
                    use_axis_z=True
                )
            
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
            
            AkkuLogger.info("Smoothing completed", {
                "iterations": iterations,
                "factor": factor
            })
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Smoothing failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @staticmethod
    def union_and_smooth(voxel_size: float = 0.02, smooth_iterations: int = 2) -> Optional[bpy.types.Object]:
        """Complete workflow: Union all parts -> Voxel Remesh -> Smooth"""
        AkkuLogger.info("Starting Union and Smooth workflow", {
            "voxel_size": voxel_size,
            "smooth_iterations": smooth_iterations
        })
        
        unified = BooleanRemeshTools.union_all_meshes()
        if not unified:
            return None
        
        from .tools import MeshAnalyzer
        MeshAnalyzer.log_stats(unified, "After Union")
        
        if not BooleanRemeshTools.voxel_remesh(unified, voxel_size):
            AkkuLogger.warning("Voxel remesh failed, continuing without")
        else:
            MeshAnalyzer.log_stats(unified, "After Voxel Remesh")
        
        if not BooleanRemeshTools.smooth_mesh(unified, smooth_iterations, 0.5):
            AkkuLogger.warning("Smoothing failed, continuing without")
        else:
            MeshAnalyzer.log_stats(unified, "After Smooth")
        
        AkkuLogger.info("Union and Smooth workflow completed")
        return unified
