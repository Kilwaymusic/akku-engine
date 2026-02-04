"""
Akku SDK Handlers - FBX and GLB file handlers
"""

import bpy
import os
from typing import Optional

from .core import AkkuLogger


class FBXHandler:
    @staticmethod
    def import_fbx(filepath: str) -> bool:
        if not os.path.exists(filepath):
            AkkuLogger.error(f"FBX file not found: {filepath}")
            return False
        try:
            bpy.ops.import_scene.fbx(filepath=filepath)
            AkkuLogger.info(f"Imported FBX: {filepath}")
            return True
        except Exception as e:
            AkkuLogger.error(f"FBX import failed: {e}")
            return False


class GLBHandler:
    @staticmethod
    def export_glb(filepath: str, selected_only: bool = False) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLB',
                use_selection=selected_only,
                export_animations=True,
                export_skins=True
            )
            AkkuLogger.info(f"Exported GLB: {filepath}")
            return True
        except Exception as e:
            AkkuLogger.error(f"GLB export failed: {e}")
            return False
    
    @staticmethod
    def import_glb(filepath: str) -> bool:
        if not os.path.exists(filepath):
            AkkuLogger.error(f"GLB file not found: {filepath}")
            return False
        try:
            bpy.ops.import_scene.gltf(filepath=filepath)
            AkkuLogger.info(f"Imported GLB: {filepath}")
            return True
        except Exception as e:
            AkkuLogger.error(f"GLB import failed: {e}")
            return False
