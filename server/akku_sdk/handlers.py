"""
Akku SDK Handlers - FBX Import and GLB Export with Freeze Support

CRITICAL: Before GLB export, all modifiers and transforms must be FROZEN
to ensure proper export. This module handles that automatically.
"""

import bpy
import bmesh
import os
from typing import List

from .core import AkkuLogger


class FBXHandler:
    """FBX import handler"""
    
    @staticmethod
    def import_fbx(filepath: str) -> List[bpy.types.Object]:
        """Import FBX file and return new objects"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"FBX file not found: {filepath}")
        
        existing_objects = set(bpy.data.objects.keys())
        
        bpy.ops.import_scene.fbx(
            filepath=filepath,
            use_custom_normals=True,
            use_image_search=False,
            ignore_leaf_bones=True,
            automatic_bone_orientation=True,
            global_scale=1.0
        )
        
        new_objects = [obj for obj in bpy.data.objects if obj.name not in existing_objects]
        AkkuLogger.info(f"Imported FBX: {filepath}", {"new_objects": len(new_objects)})
        
        return new_objects


class MeshFreezer:
    """
    Mesh Freezer - Bakes all transformations into mesh data
    
    CRITICAL: This must be called before GLB export to ensure:
    1. All modifiers are applied
    2. All transforms are baked
    3. Mesh data is final and portable
    """
    
    @staticmethod
    def freeze_modifiers(obj: bpy.types.Object) -> bool:
        """Apply all modifiers to mesh data"""
        if obj.type != 'MESH':
            return False
        
        if not obj.modifiers:
            return True
        
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            mesh_eval = bpy.data.meshes.new_from_object(obj_eval)
            
            old_mesh = obj.data
            obj.data = mesh_eval
            
            if old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
            
            obj.modifiers.clear()
            
            AkkuLogger.info(f"Froze modifiers for {obj.name}")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to freeze modifiers for {obj.name}: {str(e)}")
            return False
    
    @staticmethod
    def freeze_transform(obj: bpy.types.Object) -> bool:
        """Bake object transforms into mesh vertices"""
        if obj.type != 'MESH':
            return False
        
        if (obj.location.length_squared == 0 and 
            obj.rotation_euler == (0, 0, 0) and 
            obj.scale == (1, 1, 1)):
            return True
        
        try:
            matrix = obj.matrix_world.copy()
            
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
            
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.location = (0, 0, 0)
            obj.rotation_euler = (0, 0, 0)
            obj.scale = (1, 1, 1)
            
            obj.data.update()
            
            AkkuLogger.info(f"Froze transform for {obj.name}")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to freeze transform for {obj.name}: {str(e)}")
            return False
    
    @classmethod
    def freeze_all_meshes(cls) -> int:
        """Freeze all mesh objects in scene - modifiers only for rigged meshes"""
        count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                cls.freeze_modifiers(obj)
                
                has_armature = any(mod.type == 'ARMATURE' for mod in obj.modifiers) or obj.parent and obj.parent.type == 'ARMATURE'
                if not has_armature:
                    cls.freeze_transform(obj)
                
                count += 1
        
        AkkuLogger.info(f"Froze {count} meshes (modifiers, transforms for non-rigged) for export")
        return count


class GLBHandler:
    """
    GLB export handler with automatic freeze
    
    Before export:
    1. Freeze all mesh modifiers
    2. Use export_apply=True for remaining transforms
    """
    
    @staticmethod
    def export_glb(filepath: str, freeze_before_export: bool = True) -> bool:
        """
        Export scene to GLB file.
        
        Args:
            filepath: Output path for GLB file
            freeze_before_export: If True, freeze all modifiers first (recommended)
            
        Returns:
            True if export successful
        """
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        
        if freeze_before_export:
            MeshFreezer.freeze_all_meshes()
        
        try:
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLB',
                use_selection=False,
                export_apply=True,
                export_animations=True,
                export_skins=True,
                export_morph=False,
                export_lights=False,
                export_cameras=False,
                export_materials='EXPORT',
                export_colors=True,
            )
        except Exception as e:
            AkkuLogger.error(f"GLB export error: {str(e)}")
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLB',
                use_selection=False,
                export_apply=True,
            )
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            AkkuLogger.info(f"Exported GLB", {"path": filepath, "size": file_size})
            return True
        
        AkkuLogger.error(f"GLB export failed - file not created: {filepath}")
        return False
