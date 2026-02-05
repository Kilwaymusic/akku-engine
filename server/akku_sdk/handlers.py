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
        
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                obj.hide_viewport = False
                obj.hide_render = True
                if hasattr(obj.data, 'display_type'):
                    obj.data.display_type = 'STICK'
        
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
                export_extras=False,
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


class ScreenshotHandler:
    """
    Viewport Screenshot Handler for Autonomous 3D Agent
    
    Renders viewport to PNG for Gemini VLM analysis.
    Supports headless Blender (background mode) using Workbench render settings.
    """
    
    @classmethod
    def get_scene_bounds(cls) -> dict:
        """Calculate bounding box of all mesh objects for auto-framing"""
        from mathutils import Vector
        
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        if not mesh_objects:
            return {"min": (0, 0, 0), "max": (1, 1, 2), "center": (0.5, 0.5, 1), "size": (1, 1, 2)}
        
        min_coord = Vector((float('inf'), float('inf'), float('inf')))
        max_coord = Vector((float('-inf'), float('-inf'), float('-inf')))
        
        for obj in mesh_objects:
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ Vector(corner)
                min_coord.x = min(min_coord.x, world_corner.x)
                min_coord.y = min(min_coord.y, world_corner.y)
                min_coord.z = min(min_coord.z, world_corner.z)
                max_coord.x = max(max_coord.x, world_corner.x)
                max_coord.y = max(max_coord.y, world_corner.y)
                max_coord.z = max(max_coord.z, world_corner.z)
        
        center = (min_coord + max_coord) / 2
        size = max_coord - min_coord
        
        return {
            "min": tuple(min_coord),
            "max": tuple(max_coord),
            "center": tuple(center),
            "size": tuple(size)
        }
    
    @classmethod
    def get_camera_position(cls, view: str, bounds: dict) -> tuple:
        """Calculate camera position based on scene bounds for auto-framing"""
        center = bounds["center"]
        size = bounds["size"]
        max_dim = max(size[0], size[1], size[2])
        distance = max_dim * 2.5  # Distance multiplier for good framing
        
        center_z = center[2]
        
        if view == "front":
            return (center[0], center[1] - distance, center_z), (1.5708, 0, 0)
        elif view == "side":
            return (center[0] + distance, center[1], center_z), (1.5708, 0, 1.5708)
        elif view == "quarter":
            d = distance * 0.707  # sqrt(2)/2
            return (center[0] + d, center[1] - d, center_z + max_dim * 0.3), (1.2, 0, 0.785)
        elif view == "top":
            return (center[0], center[1], center[2] + distance), (0, 0, 0)
        else:
            return (center[0], center[1] - distance, center_z), (1.5708, 0, 0)
    
    @classmethod
    def setup_preview_scene(cls, bounds: dict = None):
        """Setup camera, lighting, and background for clean screenshots (headless-safe)"""
        scene = bpy.context.scene
        
        if bounds is None:
            bounds = cls.get_scene_bounds()
        
        # Create or get preview camera
        cam_name = "AkkuPreviewCamera"
        if cam_name in bpy.data.objects:
            cam_obj = bpy.data.objects[cam_name]
        else:
            cam_data = bpy.data.cameras.new(cam_name)
            cam_data.lens = 50
            cam_data.clip_start = 0.1
            cam_data.clip_end = 100
            cam_obj = bpy.data.objects.new(cam_name, cam_data)
            bpy.context.collection.objects.link(cam_obj)
        
        # Create or get preview lights (3-point lighting for better visualization)
        lights = []
        light_configs = [
            ("AkkuKeyLight", 'SUN', 4.0, (2, -2, 4), (0.8, 0.2, 0.3)),
            ("AkkuFillLight", 'SUN', 1.5, (-3, -1, 2), (0.6, 0.1, -0.3)),
            ("AkkuRimLight", 'SUN', 2.0, (0, 3, 3), (0.4, 3.14, 0)),
        ]
        
        for name, light_type, energy, location, rotation in light_configs:
            if name in bpy.data.objects:
                light_obj = bpy.data.objects[name]
            else:
                light_data = bpy.data.lights.new(name, light_type)
                light_data.energy = energy
                light_obj = bpy.data.objects.new(name, light_data)
                light_obj.location = location
                light_obj.rotation_euler = rotation
                bpy.context.collection.objects.link(light_obj)
            lights.append(light_obj)
        
        # Setup render settings (headless-safe - use Eevee which works in background mode)
        scene.camera = cam_obj
        
        # Try Eevee first (best quality, headless-safe), fallback to Workbench
        try:
            scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Blender 4.x
        except:
            try:
                scene.render.engine = 'BLENDER_EEVEE'  # Blender 3.x
            except:
                scene.render.engine = 'BLENDER_WORKBENCH'
        
        # Eevee render settings (headless-safe, render-only, no viewport API)
        if 'EEVEE' in scene.render.engine:
            scene.eevee.taa_render_samples = 16  # Fast but smooth
            scene.eevee.use_soft_shadows = False
            scene.eevee.use_ssr = False
            scene.eevee.use_bloom = False
        
        # World background setup (headless-safe, no viewport settings)
        scene.render.film_transparent = False
        world = bpy.data.worlds.get("AkkuPreviewWorld")
        if not world:
            world = bpy.data.worlds.new("AkkuPreviewWorld")
        scene.world = world
        
        # Use nodes for proper background in Eevee
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()
        
        # Create Background node with gray color
        bg_node = nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0.18, 0.18, 0.2, 1.0)
        bg_node.inputs['Strength'].default_value = 1.0
        
        # Create Output node
        output_node = nodes.new('ShaderNodeOutputWorld')
        links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])
        
        AkkuLogger.info("Preview scene setup complete", {
            "engine": scene.render.engine,
            "camera": cam_obj.name,
            "lights": len(lights)
        })
        
        return cam_obj, lights, bounds
    
    @classmethod
    def capture_screenshot(
        cls,
        output_path: str,
        view: str = "front",
        resolution: int = 768,
        include_composite: bool = False
    ) -> dict:
        """
        Capture viewport screenshot for Gemini analysis (headless-safe).
        
        Args:
            output_path: Output PNG file path
            view: Camera preset (front, side, quarter, top)
            resolution: Image resolution in pixels (square)
            include_composite: If True, create 2-up front+side composite
            
        Returns:
            Dict with path, size, resolution, bounds info
        """
        scene = bpy.context.scene
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Get scene bounds and setup scene
        bounds = cls.get_scene_bounds()
        cam_obj, lights, bounds = cls.setup_preview_scene(bounds)
        
        # Calculate auto-framed camera position
        cam_location, cam_rotation = cls.get_camera_position(view, bounds)
        cam_obj.location = cam_location
        cam_obj.rotation_euler = cam_rotation
        
        # Set render resolution
        scene.render.resolution_x = resolution
        scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.compression = 15
        
        # Render to file
        scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        
        result = {
            "path": output_path,
            "view": view,
            "resolution": resolution,
            "exists": os.path.exists(output_path),
            "bounds": bounds,
        }
        
        if os.path.exists(output_path):
            result["size_bytes"] = os.path.getsize(output_path)
            AkkuLogger.info(f"Screenshot captured", result)
        else:
            AkkuLogger.error(f"Screenshot failed: {output_path}")
            result["error"] = "Render failed - file not created"
        
        if include_composite:
            result["composite"] = cls.capture_composite(output_path.replace(".png", "_composite.png"), resolution, bounds)
        
        return result
    
    @classmethod
    def capture_composite(cls, output_path: str, resolution: int = 768, bounds: dict = None) -> dict:
        """Capture front + side view composite for better proportion analysis"""
        import tempfile
        
        scene = bpy.context.scene
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        if bounds is None:
            bounds = cls.get_scene_bounds()
        
        cam_obj, lights, bounds = cls.setup_preview_scene(bounds)
        
        # Render front view with auto-framing
        front_location, front_rotation = cls.get_camera_position("front", bounds)
        cam_obj.location = front_location
        cam_obj.rotation_euler = front_rotation
        
        scene.render.resolution_x = resolution // 2
        scene.render.resolution_y = resolution
        
        front_path = tempfile.mktemp(suffix="_front.png")
        scene.render.filepath = front_path
        bpy.ops.render.render(write_still=True)
        
        # Render side view with auto-framing
        side_location, side_rotation = cls.get_camera_position("side", bounds)
        cam_obj.location = side_location
        cam_obj.rotation_euler = side_rotation
        
        side_path = tempfile.mktemp(suffix="_side.png")
        scene.render.filepath = side_path
        bpy.ops.render.render(write_still=True)
        
        # Composite using Blender's compositor
        try:
            front_img = bpy.data.images.load(front_path)
            side_img = bpy.data.images.load(side_path)
            
            # Create new image for composite
            composite_img = bpy.data.images.new("AkkuComposite", resolution, resolution)
            
            # Simple side-by-side copy (manual pixel manipulation)
            front_pixels = list(front_img.pixels)
            side_pixels = list(side_img.pixels)
            composite_pixels = [0.18] * (resolution * resolution * 4)  # Gray background
            
            half_width = resolution // 2
            for y in range(resolution):
                for x in range(half_width):
                    # Front view on left
                    src_idx = (y * half_width + x) * 4
                    dst_idx = (y * resolution + x) * 4
                    if src_idx + 3 < len(front_pixels):
                        composite_pixels[dst_idx:dst_idx+4] = front_pixels[src_idx:src_idx+4]
                    
                    # Side view on right
                    dst_idx = (y * resolution + x + half_width) * 4
                    if src_idx + 3 < len(side_pixels):
                        composite_pixels[dst_idx:dst_idx+4] = side_pixels[src_idx:src_idx+4]
            
            composite_img.pixels = composite_pixels
            composite_img.filepath_raw = output_path
            composite_img.file_format = 'PNG'
            composite_img.save()
            
            # Cleanup
            bpy.data.images.remove(front_img)
            bpy.data.images.remove(side_img)
            bpy.data.images.remove(composite_img)
            os.remove(front_path)
            os.remove(side_path)
            
            return {
                "path": output_path,
                "type": "front_side_composite",
                "exists": os.path.exists(output_path)
            }
        except Exception as e:
            AkkuLogger.error(f"Composite creation failed: {str(e)}")
            return {"path": output_path, "error": str(e)}
    
    @classmethod
    def get_scene_info(cls) -> dict:
        """Get current scene statistics for Gemini context (includes bounds for auto-framing)"""
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
        
        total_verts = 0
        total_faces = 0
        mesh_names = []
        
        for obj in mesh_objects:
            if obj.data:
                total_verts += len(obj.data.vertices)
                total_faces += len(obj.data.polygons)
                mesh_names.append(obj.name)
        
        # Include scene bounds for Gemini to understand character scale
        bounds = cls.get_scene_bounds()
        
        return {
            "mesh_count": len(mesh_objects),
            "mesh_names": mesh_names,
            "total_vertices": total_verts,
            "total_faces": total_faces,
            "armature_count": len(armatures),
            "armature_names": [a.name for a in armatures],
            "bounds": bounds
        }
