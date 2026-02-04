"""
Akku SDK Handlers - FBX Import and GLB Export
"""

import bpy
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


class GLBHandler:
    """GLB export handler"""
    
    @staticmethod
    def export_glb(filepath: str) -> bool:
        """Export scene to GLB file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        bpy.ops.export_scene.gltf(
            filepath=filepath,
            export_format='GLB',
            use_selection=False,
            export_apply=True,
            export_animations=True,
            export_skins=True,
            export_morph=False,
            export_lights=False,
            export_cameras=False
        )
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            AkkuLogger.info(f"Exported GLB", {"path": filepath, "size": file_size})
            return True
        return False
