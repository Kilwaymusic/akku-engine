"""
Blender MCP Addon for Akku Engine - Low-poly SDK
Headless-compatible MCP server for procedural 3D character generation
Implements Akku Low-poly SDK with 4 tool categories
"""

import bpy
import json
import threading
import socket
import traceback
import os
import math
from mathutils import Vector, Matrix

# ============================================================
# HELPER FUNCTIONS FOR HEADLESS MODE
# ============================================================

def get_last_created_object():
    """Get the most recently created object in headless mode.
    Works around bpy.context.active_object issues in background mode."""
    # In Blender, newly created objects are added to bpy.data.objects
    # The last one in the collection is typically the most recently created
    if len(bpy.data.objects) > 0:
        return bpy.data.objects[-1]
    return None

def create_and_get_primitive(primitive_func, **kwargs):
    """Create a primitive and return the created object safely.
    Works in both interactive and headless modes."""
    # Store existing object names
    existing_names = set(obj.name for obj in bpy.data.objects)
    
    # Create the primitive
    primitive_func(**kwargs)
    
    # Find the new object
    for obj in bpy.data.objects:
        if obj.name not in existing_names:
            return obj
    
    # Fallback - get last object
    return get_last_created_object()

def apply_smooth_shading(obj):
    """Apply smooth shading to an object in headless mode."""
    if obj and obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def apply_transform(obj, location=False, rotation=False, scale=True):
    """Apply transforms to an object without context issues."""
    if obj and obj.type == 'MESH':
        # Store the transformation matrix
        matrix = obj.matrix_world.copy()
        
        if scale:
            # Apply scale to mesh data
            mesh = obj.data
            scale_matrix = Matrix.Diagonal(obj.scale).to_4x4()
            mesh.transform(scale_matrix)
            obj.scale = (1, 1, 1)
        
        if location:
            obj.location = (0, 0, 0)
        
        if rotation:
            obj.rotation_euler = (0, 0, 0)

# ============================================================
# AKKU SDK PRESET DATA
# ============================================================

# Base mesh presets with optimized topology
BASE_PRESETS = {
    "sd": {  # Super-deformed (2-3 heads tall)
        "head_ratio": 0.4,
        "body_height": 1.0,
        "limb_thickness": 0.12,
        "head_scale": 1.5,
        "torso_width": 0.35,
        "leg_length": 0.3,
        "sphere_segments": 12,
        "sphere_rings": 8,
        "cylinder_vertices": 8
    },
    "stylized": {  # Stylized proportions (5-6 heads)
        "head_ratio": 0.18,
        "body_height": 1.6,
        "limb_thickness": 0.08,
        "head_scale": 1.0,
        "torso_width": 0.28,
        "leg_length": 0.5,
        "sphere_segments": 16,
        "sphere_rings": 10,
        "cylinder_vertices": 12
    },
    "realistic": {  # 8-head proportions
        "head_ratio": 0.125,
        "body_height": 1.8,
        "limb_thickness": 0.06,
        "head_scale": 0.9,
        "torso_width": 0.25,
        "leg_length": 0.55,
        "sphere_segments": 20,
        "sphere_rings": 12,
        "cylinder_vertices": 16
    },
    "chibi": {  # Chibi style (1.5-2 heads)
        "head_ratio": 0.5,
        "body_height": 0.8,
        "limb_thickness": 0.15,
        "head_scale": 1.8,
        "torso_width": 0.4,
        "leg_length": 0.2,
        "sphere_segments": 10,
        "sphere_rings": 6,
        "cylinder_vertices": 6
    },
    "mobile": {  # Ultra-low-poly for mobile games (~300 tris)
        "head_ratio": 0.35,
        "body_height": 1.2,
        "limb_thickness": 0.1,
        "head_scale": 1.3,
        "torso_width": 0.3,
        "leg_length": 0.35,
        "sphere_segments": 8,
        "sphere_rings": 4,
        "cylinder_vertices": 6
    },
    "minifig": {  # LEGO-like minifigure proportions
        "head_ratio": 0.45,
        "body_height": 0.9,
        "limb_thickness": 0.09,
        "head_scale": 1.4,
        "torso_width": 0.32,
        "leg_length": 0.25,
        "sphere_segments": 8,
        "sphere_rings": 6,
        "cylinder_vertices": 6
    },
    "cartoon": {  # Cartoon style (4-5 heads, exaggerated features)
        "head_ratio": 0.25,
        "body_height": 1.4,
        "limb_thickness": 0.1,
        "head_scale": 1.2,
        "torso_width": 0.32,
        "leg_length": 0.4,
        "sphere_segments": 14,
        "sphere_rings": 8,
        "cylinder_vertices": 10
    }
}

# Polygon count targets for different quality levels
POLY_LEVELS = {
    "ultra_low": {"target_tris": 300, "decimate_ratio": 0.3},
    "low": {"target_tris": 800, "decimate_ratio": 0.5},
    "medium": {"target_tris": 1500, "decimate_ratio": 0.7},
    "high": {"target_tris": 3000, "decimate_ratio": 0.9}
}

# Armor plate presets for kitbashing
ARMOR_PRESETS = {
    "shoulder_pad": {"type": "cube", "scale": (0.15, 0.12, 0.08), "bevel": 0.02},
    "chest_plate": {"type": "cube", "scale": (0.35, 0.08, 0.3), "bevel": 0.03},
    "knee_guard": {"type": "cube", "scale": (0.1, 0.08, 0.12), "bevel": 0.015},
    "gauntlet": {"type": "cylinder", "scale": (0.07, 0.07, 0.15), "bevel": 0.01},
    "helmet": {"type": "sphere", "scale": (0.18, 0.18, 0.2), "bevel": 0.01},
    "helmet_visor": {"type": "cube", "scale": (0.2, 0.05, 0.1), "bevel": 0.02},
    "belt_buckle": {"type": "cube", "scale": (0.12, 0.04, 0.08), "bevel": 0.01},
    "boot_plate": {"type": "cube", "scale": (0.1, 0.15, 0.08), "bevel": 0.015},
    "back_plate": {"type": "cube", "scale": (0.3, 0.06, 0.28), "bevel": 0.02},
    "bracer": {"type": "cylinder", "scale": (0.06, 0.06, 0.12), "bevel": 0.008},
    "pauldron": {"type": "cube", "scale": (0.18, 0.14, 0.1), "bevel": 0.025}
}

# Armor location offsets relative to body
ARMOR_LOCATIONS = {
    "left_shoulder": (-0.4, 0, 1.35),
    "right_shoulder": (0.4, 0, 1.35),
    "chest": (0, -0.15, 1.15),
    "back": (0, 0.15, 1.15),
    "left_knee": (-0.15, 0, 0.35),
    "right_knee": (0.15, 0, 0.35),
    "left_gauntlet": (-0.55, 0, 1.0),
    "right_gauntlet": (0.55, 0, 1.0),
    "helmet": (0, -0.1, 1.8),
    "belt": (0, 0, 0.75),
    "left_boot": (-0.15, 0, 0.1),
    "right_boot": (0.15, 0, 0.1)
}

# PBR material presets
PBR_PRESETS = {
    "metal": {
        "metallic": 1.0,
        "roughness": 0.3,
        "specular": 0.8
    },
    "brushed_metal": {
        "metallic": 0.95,
        "roughness": 0.5,
        "specular": 0.7
    },
    "plastic": {
        "metallic": 0.0,
        "roughness": 0.4,
        "specular": 0.5
    },
    "rubber": {
        "metallic": 0.0,
        "roughness": 0.9,
        "specular": 0.1
    },
    "cloth": {
        "metallic": 0.0,
        "roughness": 0.8,
        "specular": 0.2
    },
    "leather": {
        "metallic": 0.0,
        "roughness": 0.6,
        "specular": 0.3
    },
    "skin": {
        "metallic": 0.0,
        "roughness": 0.5,
        "specular": 0.4,
        "subsurface": 0.3
    },
    "glow": {
        "metallic": 0.0,
        "roughness": 0.2,
        "emission_strength": 5.0
    },
    "chrome": {
        "metallic": 1.0,
        "roughness": 0.05,
        "specular": 1.0
    },
    "gold": {
        "metallic": 1.0,
        "roughness": 0.25,
        "specular": 0.9
    }
}

# Basic animation clips (bone rotations per frame)
ANIMATION_CLIPS = {
    "idle": {
        "duration": 60,
        "loop": True,
        "keyframes": {
            "spine": [(0, (0, 0, 0)), (30, (0.02, 0, 0)), (60, (0, 0, 0))],
        }
    },
    "walk": {
        "duration": 40,
        "loop": True,
        "keyframes": {
            "left_leg": [(0, (0.3, 0, 0)), (20, (-0.3, 0, 0)), (40, (0.3, 0, 0))],
            "right_leg": [(0, (-0.3, 0, 0)), (20, (0.3, 0, 0)), (40, (-0.3, 0, 0))],
            "left_arm": [(0, (-0.2, 0, 0)), (20, (0.2, 0, 0)), (40, (-0.2, 0, 0))],
            "right_arm": [(0, (0.2, 0, 0)), (20, (-0.2, 0, 0)), (40, (0.2, 0, 0))]
        }
    },
    "attack": {
        "duration": 30,
        "loop": False,
        "keyframes": {
            "right_arm": [(0, (0, 0, 0)), (10, (-1.5, 0, 0.5)), (20, (0.5, 0, -0.3)), (30, (0, 0, 0))],
            "spine": [(0, (0, 0, 0)), (10, (0, 0.2, 0)), (20, (0, -0.3, 0)), (30, (0, 0, 0))]
        }
    },
    "jump": {
        "duration": 40,
        "loop": False,
        "keyframes": {
            "left_leg": [(0, (0, 0, 0)), (10, (0.5, 0, 0)), (20, (-0.3, 0, 0)), (40, (0, 0, 0))],
            "right_leg": [(0, (0, 0, 0)), (10, (0.5, 0, 0)), (20, (-0.3, 0, 0)), (40, (0, 0, 0))],
            "left_arm": [(0, (0, 0, 0)), (10, (-0.8, 0, 0.5)), (20, (0.5, 0, -0.3)), (40, (0, 0, 0))],
            "right_arm": [(0, (0, 0, 0)), (10, (-0.8, 0, -0.5)), (20, (0.5, 0, 0.3)), (40, (0, 0, 0))]
        }
    }
}


class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
        self.current_armature = None  # Track armature for rigging

    def start(self):
        import sys
        
        if self.running:
            print("MCP Server is already running", flush=True)
            return

        self.running = True

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.settimeout(1.0)

            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()

            print(f"Akku MCP server started on {self.host}:{self.port}", flush=True)
            sys.stdout.flush()
        except Exception as e:
            print(f"Failed to start MCP server: {str(e)}", flush=True)
            self.stop()

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        print("MCP Server stopped")

    def _server_loop(self):
        print("MCP Server thread started", flush=True)

        while self.running:
            try:
                try:
                    client, address = self.socket.accept()
                    print(f"MCP Client connected: {address}", flush=True)
                    self._handle_client(client)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {str(e)}", flush=True)
            except Exception as e:
                print(f"Error in server loop: {str(e)}", flush=True)
                if not self.running:
                    break

    def _handle_client(self, client):
        client.settimeout(300.0)  # 5 minutes for long operations
        buffer = b''

        try:
            while self.running:
                data = client.recv(65536)
                if not data:
                    break

                buffer += data
                
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        command = json.loads(line.decode('utf-8'))
                        response = self.execute_command(command)
                        response_json = json.dumps(response) + '\n'
                        client.sendall(response_json.encode('utf-8'))
                    except json.JSONDecodeError:
                        error_response = {"status": "error", "message": "Invalid JSON"}
                        client.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
        except socket.timeout:
            print("Client timeout")
        except Exception as e:
            print(f"Error handling client: {str(e)}")
        finally:
            client.close()

    def execute_command(self, command):
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})

            # Original commands
            handlers = {
                "get_scene_info": self.get_scene_info,
                "execute_code": self.execute_code,
                "create_character": self.create_character,
                "apply_modifier": self.apply_modifier,
                "setup_material": self.setup_material,
                "export_glb": self.export_glb,
                "clear_scene": self.clear_scene,
                "get_object_info": self.get_object_info,
                
                # ============ AKKU SDK TOOLS ============
                # Category 1: Base Generation
                "spawn_humanoid_base": self.spawn_humanoid_base,
                "deform_body": self.deform_body,
                
                # Category 2: Hard-Surface Kitbashing
                "attach_armor_plate": self.attach_armor_plate,
                "add_scifi_detail": self.add_scifi_detail,
                
                # Category 3: Game-Ready PBR Shading
                "apply_akku_pbr": self.apply_akku_pbr,
                "set_material_property": self.set_material_property,
                
                # Category 4: Auto-Rig & Animation
                "finalize_and_bind": self.finalize_and_bind,
                "test_animation": self.test_animation,
            }

            handler = handlers.get(cmd_type)
            if handler:
                result = handler(**params)
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "message": f"Unknown command: {cmd_type}"}

        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    # ============================================================
    # ORIGINAL MCP COMMANDS (kept for compatibility)
    # ============================================================

    def get_scene_info(self):
        return {
            "name": bpy.context.scene.name,
            "object_count": len(bpy.context.scene.objects),
            "objects": [
                {
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.location),
                    "vertices": len(obj.data.vertices) if hasattr(obj.data, 'vertices') else 0
                }
                for obj in bpy.context.scene.objects
            ],
            "materials_count": len(bpy.data.materials),
            "has_armature": self.current_armature is not None
        }

    def execute_code(self, code):
        # Security: Only allow trusted code patterns
        forbidden = ['import os', 'import subprocess', 'open(', 'eval(', '__import__', 
                     'exec(', 'compile(', 'shutil', 'socket', 'requests', 'urllib']
        code_lower = code.lower()
        for pattern in forbidden:
            if pattern.lower() in code_lower:
                raise ValueError(f"Forbidden code pattern detected: {pattern}")
        
        local_vars = {"bpy": bpy, "result": None}
        exec(code, {"bpy": bpy}, local_vars)
        return local_vars.get("result", "Code executed successfully")

    def clear_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        self.current_armature = None
        return "Scene cleared"

    def create_character(self, character_type="humanoid", params=None):
        # Legacy function - redirects to new SDK
        return self.spawn_humanoid_base(proportion_type="stylized")

    def apply_modifier(self, object_name, modifier_type, params=None):
        if params is None:
            params = {}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")

        bpy.context.view_layer.objects.active = obj

        if modifier_type == "SUBSURF":
            mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            mod.levels = params.get("levels", 1)
            mod.render_levels = params.get("render_levels", 2)
        elif modifier_type == "SMOOTH":
            mod = obj.modifiers.new(name="Smooth", type='SMOOTH')
            mod.factor = params.get("factor", 0.5)
            mod.iterations = params.get("iterations", 2)
        elif modifier_type == "BEVEL":
            mod = obj.modifiers.new(name="Bevel", type='BEVEL')
            mod.width = params.get("width", 0.02)
            mod.segments = params.get("segments", 3)
        elif modifier_type == "SOLIDIFY":
            mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            mod.thickness = params.get("thickness", 0.01)

        return f"Applied {modifier_type} to {object_name}"

    def setup_material(self, object_name, material_params):
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")

        mat_name = material_params.get("name", f"{object_name}_Material")
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            color = material_params.get("color", [0.8, 0.8, 0.8])
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Metallic"].default_value = material_params.get("metallic", 0.0)
            bsdf.inputs["Roughness"].default_value = material_params.get("roughness", 0.5)

        obj.data.materials.clear()
        obj.data.materials.append(mat)

        return f"Applied material {mat_name} to {object_name}"

    def get_object_info(self, name):
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")

        info = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "modifiers": [mod.type for mod in obj.modifiers],
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        }

        if obj.type == 'MESH' and obj.data:
            info["mesh"] = {
                "vertices": len(obj.data.vertices),
                "edges": len(obj.data.edges),
                "polygons": len(obj.data.polygons),
            }

        return info

    def export_glb(self, filepath, optimize_for_game=True):
        """
        Export scene to GLB format optimized for game engines.
        - Applies all modifiers (headless-compatible)
        - Joins meshes for draw call optimization (when optimize_for_game=True)
        - Uses subprocess for glTF export to avoid headless context issues
        """
        import subprocess
        import os
        import shlex
        import shutil
        
        # Get all mesh objects from scene (headless-compatible)
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        # Apply all modifiers using evaluated depsgraph (headless-compatible)
        for obj in mesh_objects:
            if obj.modifiers:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                eval_obj = obj.evaluated_get(depsgraph)
                new_mesh = bpy.data.meshes.new_from_object(eval_obj)
                obj.data = new_mesh
                obj.modifiers.clear()
        
        # Count triangles before export
        total_tris = 0
        mesh_count = len(mesh_objects)
        for obj in mesh_objects:
            total_tris += sum(len(p.vertices) - 2 for p in obj.data.polygons)
        
        # Join meshes for game optimization (reduces draw calls)
        joined = False
        if optimize_for_game and mesh_count > 1:
            # Deselect all, then select only meshes
            for obj in bpy.context.scene.objects:
                obj.select_set(False)
            for obj in mesh_objects:
                obj.select_set(True)
            
            # Set first mesh as active and join
            if mesh_objects:
                bpy.context.view_layer.objects.active = mesh_objects[0]
                try:
                    bpy.ops.object.join()
                    mesh_objects[0].name = "AkkuCharacter"
                    joined = True
                except Exception as e:
                    print(f"Warning: Could not join meshes: {e}")
        
        # Save .blend file to temp location (escape path for safety)
        blend_path = filepath.replace('.glb', '_temp.blend')
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        
        # Create export script with properly escaped paths
        escaped_filepath = filepath.replace('\\', '\\\\').replace('"', '\\"')
        export_script = f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath="{escaped_filepath}",
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False,
    export_yup=True,
)
print("GLB_EXPORT_SUCCESS")
'''
        # Find blender executable (prefer shutil.which for portability)
        blender_path = shutil.which('blender') or 'blender'
        
        # Run export in subprocess with proper context
        try:
            result = subprocess.run(
                [blender_path, '-b', blend_path, '--python-expr', export_script],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Log output for debugging
            if result.stdout:
                print(f"Blender export stdout: {result.stdout[-500:]}")
            
            # Check for success marker in output
            export_success = "GLB_EXPORT_SUCCESS" in result.stdout
            
            if result.returncode != 0 or not export_success:
                error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
                raise RuntimeError(f"Export failed (code {result.returncode}): {error_msg}")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Export timed out after 120 seconds")
        except FileNotFoundError:
            raise RuntimeError(f"Blender executable not found at: {blender_path}")
        finally:
            # Clean up temp blend file
            for f in [blend_path, blend_path + '1']:
                try:
                    os.remove(f)
                except:
                    pass

        return {
            "message": f"Exported to {filepath}",
            "filepath": filepath,
            "mesh_count": 1 if joined else mesh_count,
            "triangle_count": total_tris,
            "optimized": optimize_for_game,
            "joined": joined
        }

    # ============================================================
    # AKKU SDK CATEGORY 1: BASE GENERATION
    # ============================================================

    def spawn_humanoid_base(self, proportion_type="stylized", poly_level="medium", gender="neutral"):
        """
        Load Mixamo Y Bot / X Bot as base mesh and apply proportion adjustments.
        proportion_type: 'sd', 'stylized', 'realistic', 'chibi', 'mobile', 'minifig', 'cartoon'
        poly_level: 'ultra_low', 'low', 'medium', 'high' - controls polygon density via decimation
        gender: 'neutral' (Y Bot), 'male' (X Bot), 'female' (Y Bot)
        """
        self.clear_scene()
        
        preset = BASE_PRESETS.get(proportion_type, BASE_PRESETS["stylized"])
        poly_config = POLY_LEVELS.get(poly_level, POLY_LEVELS["medium"])
        
        # Determine which FBX to load
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        if gender == "male":
            fbx_path = os.path.join(project_root, "assets", "base_meshes", "X_Bot.fbx")
        else:
            fbx_path = os.path.join(project_root, "assets", "base_meshes", "Y_Bot.fbx")
        
        # Fallback paths for different working directories
        if not os.path.exists(fbx_path):
            alt_paths = [
                f"/home/runner/workspace/assets/base_meshes/{'X_Bot' if gender == 'male' else 'Y_Bot'}.fbx",
                f"./assets/base_meshes/{'X_Bot' if gender == 'male' else 'Y_Bot'}.fbx"
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    fbx_path = alt
                    break
        
        if not os.path.exists(fbx_path):
            raise FileNotFoundError(f"Base mesh FBX not found: {fbx_path}")
        
        # Store existing objects before import
        existing_objects = set(obj.name for obj in bpy.data.objects)
        
        # Import FBX
        bpy.ops.import_scene.fbx(
            filepath=fbx_path,
            use_custom_normals=True,
            use_image_search=False,
            use_alpha_decals=False,
            ignore_leaf_bones=True,
            force_connect_children=False,
            automatic_bone_orientation=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_prepost_rot=True,
            axis_forward='-Z',
            axis_up='Y'
        )
        
        # Find imported objects (armature and meshes)
        imported_objects = []
        imported_armature = None
        imported_meshes = []
        main_surface_mesh = None
        
        for obj in bpy.data.objects:
            if obj.name not in existing_objects:
                imported_objects.append(obj)
                if obj.type == 'ARMATURE':
                    imported_armature = obj
                    self.current_armature = obj
                elif obj.type == 'MESH':
                    imported_meshes.append(obj)
        
        # Identify main surface mesh (largest vertex count is typically the body mesh)
        if imported_meshes:
            imported_meshes.sort(key=lambda m: len(m.data.vertices), reverse=True)
            main_surface_mesh = imported_meshes[0]
        
        # Rename imported objects with consistent Akku naming
        for obj in imported_objects:
            if obj.type == 'ARMATURE':
                obj.name = "AkkuBase_Armature"
            elif obj.type == 'MESH':
                if obj == main_surface_mesh:
                    # Main body mesh gets consistent name for material targeting
                    obj.name = "AkkuBase_Surface"
                else:
                    # Secondary meshes (joints, eyes, etc.) - prefix with AkkuBase_Aux_
                    original_name = obj.name.replace("Alpha_", "").replace("Beta_", "")
                    obj.name = f"AkkuBase_Aux_{original_name}"
        
        # Apply proportion scaling based on proportion_type
        body_height = preset["body_height"]
        
        # Scale the entire character uniformly first
        base_scale = body_height / 1.8  # Normalize to ~1.8m default height
        
        for obj in imported_objects:
            obj.scale = (base_scale, base_scale, base_scale)
        
        # Apply transforms to all objects so scaling is baked into mesh
        for obj in imported_objects:
            obj.select_set(True)
        if imported_objects:
            bpy.context.view_layer.objects.active = imported_objects[0]
            try:
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            except Exception as e:
                print(f"Warning: Could not apply transforms: {e}")
        
        # NOTE: Non-uniform scaling breaks armature deformation
        # For proportion_type variations, we only adjust uniform scale
        # Stylized proportions are achieved through the FBX model choice
        # Chibi/SD effects would require custom FBX models with different proportions
        
        # Apply decimation for poly_level - ONLY to main surface mesh
        decimate_ratio = poly_config.get("decimate_ratio", 1.0)
        
        if decimate_ratio < 1.0 and main_surface_mesh:
            # Add decimate modifier only to main surface mesh
            decimate = main_surface_mesh.modifiers.new(name="Decimate", type='DECIMATE')
            decimate.decimate_type = 'COLLAPSE'
            decimate.ratio = decimate_ratio
            decimate.use_collapse_triangulate = True
            
            # Apply modifier using depsgraph (headless compatible)
            try:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                eval_obj = main_surface_mesh.evaluated_get(depsgraph)
                new_mesh = bpy.data.meshes.new_from_object(eval_obj)
                main_surface_mesh.data = new_mesh
                main_surface_mesh.modifiers.clear()
            except Exception as e:
                print(f"Warning: Could not apply decimate: {e}")
        
        # Apply default material
        default_mat = bpy.data.materials.new(name="AkkuBase_Material")
        default_mat.use_nodes = True
        bsdf = default_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.5
        
        # Count total triangles and apply material only to main surface
        total_tris = 0
        if main_surface_mesh:
            main_surface_mesh.data.materials.clear()
            main_surface_mesh.data.materials.append(default_mat)
            total_tris = sum(len(p.vertices) - 2 for p in main_surface_mesh.data.polygons)
        
        # Build list of final object names
        final_objects = [obj.name for obj in imported_objects if obj and obj.name]
        
        return {
            "message": f"Loaded Mixamo {'X Bot' if gender == 'male' else 'Y Bot'} as {proportion_type} base ({poly_level} poly)",
            "proportion_type": proportion_type,
            "poly_level": poly_level,
            "gender": gender,
            "body_height": body_height,
            "triangle_count": total_tris,
            "has_armature": imported_armature is not None,
            "main_mesh": "AkkuBase_Surface" if main_surface_mesh else None,
            "objects": final_objects
        }

    def deform_body(self, part, strength=0.5, deform_type="scale"):
        """
        Deform a specific body part via armature bone scaling (for Mixamo mesh).
        part: 'head', 'torso', 'arms', 'legs', 'hands', 'feet', 'shoulders', 'hips', 'body'
        strength: -1.0 to 1.0 (negative = shrink, positive = enlarge)
        deform_type: 'scale', 'stretch_vertical', 'stretch_horizontal'
        """
        # Mixamo bone name patterns for each body part
        bone_patterns = {
            "head": ["Head", "head"],
            "torso": ["Spine", "spine"],
            "arms": ["Arm", "arm", "ForeArm", "forearm"],
            "legs": ["UpLeg", "upleg", "Leg", "leg"],
            "hands": ["Hand", "hand"],
            "feet": ["Foot", "foot", "Toe", "toe"],
            "shoulders": ["Shoulder", "shoulder"],
            "hips": ["Hips", "hips"],
            "body": []  # Special case: scale entire mesh
        }
        
        patterns = bone_patterns.get(part)
        if patterns is None:
            raise ValueError(f"Unknown body part: {part}")
        
        scale_factor = 1.0 + (strength * 0.5)  # Convert -1..1 to 0.5..1.5
        
        # Special case: scale entire body mesh
        if part == "body":
            surface = bpy.data.objects.get("AkkuBase_Surface")
            if surface:
                if deform_type == "scale":
                    surface.scale *= scale_factor
                elif deform_type == "stretch_vertical":
                    surface.scale[2] *= scale_factor
                elif deform_type == "stretch_horizontal":
                    surface.scale[0] *= scale_factor
                    surface.scale[1] *= scale_factor
                apply_transform(surface, scale=True)
                return {"message": f"Scaled entire body by {scale_factor}", "part": part}
        
        # For specific body parts, try to scale bones in armature
        armature = bpy.data.objects.get("AkkuBase_Armature")
        modified_bones = []
        
        if armature and armature.type == 'ARMATURE':
            for bone in armature.data.bones:
                for pattern in patterns:
                    if pattern.lower() in bone.name.lower():
                        pose_bone = armature.pose.bones.get(bone.name)
                        if pose_bone:
                            if deform_type == "scale":
                                pose_bone.scale = (scale_factor, scale_factor, scale_factor)
                            elif deform_type == "stretch_vertical":
                                pose_bone.scale = (1.0, scale_factor, 1.0)
                            elif deform_type == "stretch_horizontal":
                                pose_bone.scale = (scale_factor, 1.0, scale_factor)
                            modified_bones.append(bone.name)
                        break
        
        if not modified_bones:
            return {
                "message": f"No bones found for part '{part}'",
                "part": part,
                "modified_bones": []
            }
        
        return {
            "message": f"Deformed {part} with {deform_type}",
            "strength": strength,
            "deform_type": deform_type,
            "modified_bones": modified_bones
        }

    # ============================================================
    # AKKU SDK CATEGORY 2: HARD-SURFACE KITBASHING
    # ============================================================

    def attach_armor_plate(self, location, style="shoulder_pad", scale=1.0):
        """
        Attach armor plate at specified location.
        location: 'left_shoulder', 'right_shoulder', 'chest', 'back', etc.
        style: 'shoulder_pad', 'chest_plate', 'knee_guard', 'gauntlet', etc.
        scale: size multiplier
        """
        if location not in ARMOR_LOCATIONS:
            raise ValueError(f"Unknown location: {location}. Available: {list(ARMOR_LOCATIONS.keys())}")
        
        if style not in ARMOR_PRESETS:
            raise ValueError(f"Unknown style: {style}. Available: {list(ARMOR_PRESETS.keys())}")
        
        preset = ARMOR_PRESETS[style]
        pos = ARMOR_LOCATIONS[location]
        
        # Create armor piece based on type
        if preset["type"] == "cube":
            armor = create_and_get_primitive(bpy.ops.mesh.primitive_cube_add, size=1, location=pos)
        elif preset["type"] == "cylinder":
            armor = create_and_get_primitive(bpy.ops.mesh.primitive_cylinder_add, radius=0.5, depth=1, location=pos)
        elif preset["type"] == "sphere":
            armor = create_and_get_primitive(bpy.ops.mesh.primitive_uv_sphere_add, segments=12, ring_count=8, radius=1, location=pos)
        else:
            armor = create_and_get_primitive(bpy.ops.mesh.primitive_cube_add, size=1, location=pos)
        
        armor.name = f"Armor_{location}_{style}"
        
        # Apply scale from preset and user scale
        base_scale = preset["scale"]
        armor.scale = (base_scale[0] * scale, base_scale[1] * scale, base_scale[2] * scale)
        apply_transform(armor, scale=True)
        
        # Add bevel for hard-surface look
        bevel = armor.modifiers.new(name="Bevel", type='BEVEL')
        bevel.width = preset["bevel"] * scale
        bevel.segments = 2
        
        # Add solidify for thickness
        solidify = armor.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify.thickness = 0.01 * scale
        
        # Apply default metal material
        metal_mat = bpy.data.materials.new(name=f"{armor.name}_Material")
        metal_mat.use_nodes = True
        bsdf = metal_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.4, 0.4, 0.45, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.9
            bsdf.inputs["Roughness"].default_value = 0.35
        
        armor.data.materials.clear()
        armor.data.materials.append(metal_mat)
        
        return {
            "message": f"Attached {style} at {location}",
            "object_name": armor.name,
            "location": pos,
            "scale": scale
        }

    def add_scifi_detail(self, target_obj, detail_level="medium"):
        """
        Add procedural sci-fi panel lines and details to an object.
        Uses modifiers instead of edit mode for headless compatibility.
        target_obj: name of object to add details to
        detail_level: 'low', 'medium', 'high'
        """
        obj = bpy.data.objects.get(target_obj)
        if not obj:
            raise ValueError(f"Object not found: {target_obj}")
        
        if obj.type != 'MESH':
            raise ValueError(f"Object must be a mesh: {target_obj}")
        
        detail_configs = {
            "low": {"subdivide": 1, "bevel_width": 0.008, "bevel_segments": 1},
            "medium": {"subdivide": 2, "bevel_width": 0.012, "bevel_segments": 2},
            "high": {"subdivide": 2, "bevel_width": 0.015, "bevel_segments": 3}
        }
        
        config = detail_configs.get(detail_level, detail_configs["medium"])
        
        # Add subdivision for more geometry (simple mode for low-poly look)
        if config["subdivide"] > 0:
            subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            subdiv.subdivision_type = 'SIMPLE'
            subdiv.levels = config["subdivide"]
            subdiv.render_levels = config["subdivide"]
        
        # Add bevel for edge highlighting
        bevel = obj.modifiers.new(name="SciFiBevel", type='BEVEL')
        bevel.width = config["bevel_width"]
        bevel.segments = config["bevel_segments"]
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = 0.523599  # 30 degrees
        
        # Add edge split for sharp edges
        edge_split = obj.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
        edge_split.split_angle = 0.523599  # 30 degrees
        
        return {
            "message": f"Added {detail_level} sci-fi details to {target_obj}",
            "detail_level": detail_level,
            "modifiers_added": ["Subdivision", "SciFiBevel", "EdgeSplit"]
        }

    # ============================================================
    # AKKU SDK CATEGORY 3: GAME-READY PBR SHADING
    # ============================================================

    def apply_akku_pbr(self, object_name, preset_name="metal", base_color=None):
        """
        Apply a PBR material preset to an object.
        object_name: target object
        preset_name: 'metal', 'plastic', 'cloth', 'leather', 'skin', 'glow', 'chrome', 'gold'
        base_color: [r, g, b] override (0-1 range)
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")
        
        if preset_name not in PBR_PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PBR_PRESETS.keys())}")
        
        preset = PBR_PRESETS[preset_name]
        
        # Create material
        mat_name = f"{object_name}_{preset_name}_PBR"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            # Set base color
            if base_color:
                bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
            else:
                # Default colors per preset
                default_colors = {
                    "metal": (0.5, 0.5, 0.55),
                    "brushed_metal": (0.6, 0.6, 0.62),
                    "plastic": (0.8, 0.2, 0.2),
                    "rubber": (0.1, 0.1, 0.1),
                    "cloth": (0.3, 0.4, 0.6),
                    "leather": (0.35, 0.2, 0.1),
                    "skin": (0.85, 0.65, 0.5),
                    "glow": (0.0, 0.8, 1.0),
                    "chrome": (0.9, 0.9, 0.95),
                    "gold": (1.0, 0.8, 0.3)
                }
                color = default_colors.get(preset_name, (0.5, 0.5, 0.5))
                bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            
            # Apply preset values
            bsdf.inputs["Metallic"].default_value = preset.get("metallic", 0.0)
            bsdf.inputs["Roughness"].default_value = preset.get("roughness", 0.5)
            bsdf.inputs["Specular IOR Level"].default_value = preset.get("specular", 0.5)
            
            # Subsurface for skin
            if "subsurface" in preset:
                bsdf.inputs["Subsurface Weight"].default_value = preset["subsurface"]
            
            # Emission for glow
            if "emission_strength" in preset:
                bsdf.inputs["Emission Strength"].default_value = preset["emission_strength"]
                if base_color:
                    bsdf.inputs["Emission Color"].default_value = (*base_color, 1.0)
                else:
                    bsdf.inputs["Emission Color"].default_value = (0.0, 0.8, 1.0, 1.0)
        
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        
        return {
            "message": f"Applied {preset_name} PBR to {object_name}",
            "material_name": mat_name,
            "metallic": preset.get("metallic", 0.0),
            "roughness": preset.get("roughness", 0.5)
        }

    def set_material_property(self, object_name, metallic=None, roughness=None, emission=None):
        """
        Fine-tune material properties on an object.
        object_name: target object
        metallic: 0.0 - 1.0
        roughness: 0.0 - 1.0
        emission: emission strength (0 = off)
        """
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise ValueError(f"Object not found: {object_name}")
        
        if not obj.material_slots or not obj.material_slots[0].material:
            raise ValueError(f"Object has no material: {object_name}")
        
        mat = obj.material_slots[0].material
        if not mat.use_nodes:
            raise ValueError(f"Material does not use nodes: {mat.name}")
        
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            raise ValueError(f"Material has no Principled BSDF: {mat.name}")
        
        changes = []
        
        if metallic is not None:
            bsdf.inputs["Metallic"].default_value = max(0.0, min(1.0, metallic))
            changes.append(f"metallic={metallic}")
        
        if roughness is not None:
            bsdf.inputs["Roughness"].default_value = max(0.0, min(1.0, roughness))
            changes.append(f"roughness={roughness}")
        
        if emission is not None:
            bsdf.inputs["Emission Strength"].default_value = max(0.0, emission)
            changes.append(f"emission={emission}")
        
        return {
            "message": f"Updated material on {object_name}",
            "changes": changes
        }

    # ============================================================
    # AKKU SDK CATEGORY 4: AUTO-RIG & ANIMATION
    # ============================================================

    def finalize_and_bind(self):
        """
        Finalize all mesh objects for export.
        Creates a game-ready character (simplified for headless mode).
        Note: Full rigging is deferred as it requires interactive context.
        """
        # Collect all mesh objects
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        if not mesh_objects:
            raise ValueError("No mesh objects found in scene")
        
        # Apply modifiers using bmesh (headless compatible)
        for obj in mesh_objects:
            for mod in list(obj.modifiers):
                try:
                    # For simple modifiers, try to apply via depsgraph
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    obj_eval = obj.evaluated_get(depsgraph)
                    mesh_from_eval = bpy.data.meshes.new_from_object(obj_eval)
                    obj.data = mesh_from_eval
                    obj.modifiers.clear()
                except:
                    pass  # Skip if can't apply
        
        # Refresh mesh objects list after modifier application
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        # Rename first mesh as main character
        if mesh_objects:
            mesh_objects[0].name = "AkkuCharacter"
        
        # Calculate total triangle count
        total_tris = sum(len(obj.data.polygons) * 2 for obj in mesh_objects if obj.data)
        
        # Note: Rigging is skipped in headless mode for stability
        # The exported GLB will have the mesh ready for rigging in external tools
        
        return {
            "message": "Character finalized (mesh-only, no rig)",
            "mesh_count": len(mesh_objects),
            "main_mesh": mesh_objects[0].name if mesh_objects else None,
            "total_triangles": total_tris,
            "note": "Rigging deferred for headless compatibility"
        }

    def test_animation(self, clip_name="idle"):
        """
        Apply a test animation clip to the character.
        clip_name: 'idle', 'walk', 'attack', 'jump'
        Note: Skipped in headless mode since rigging is deferred.
        """
        if not self.current_armature:
            return {
                "message": "Animation skipped (no armature)",
                "clip_name": clip_name,
                "note": "Rigging is deferred in headless mode. Animation can be added post-export."
            }
        
        if clip_name not in ANIMATION_CLIPS:
            raise ValueError(f"Unknown clip: {clip_name}. Available: {list(ANIMATION_CLIPS.keys())}")
        
        clip = ANIMATION_CLIPS[clip_name]
        armature = self.current_armature
        
        # Create action
        action_name = f"Akku_{clip_name}"
        action = bpy.data.actions.new(name=action_name)
        
        if armature.animation_data is None:
            armature.animation_data_create()
        armature.animation_data.action = action
        
        # Set animation properties
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = clip["duration"]
        
        # Apply keyframes
        bpy.ops.object.mode_set(mode='POSE')
        
        bone_name_mapping = {
            "spine": "Spine",
            "left_leg": "UpperLeg_L",
            "right_leg": "UpperLeg_R",
            "left_arm": "UpperArm_L",
            "right_arm": "UpperArm_R"
        }
        
        for bone_key, keyframes in clip["keyframes"].items():
            bone_name = bone_name_mapping.get(bone_key)
            if not bone_name:
                continue
            
            pose_bone = armature.pose.bones.get(bone_name)
            if not pose_bone:
                continue
            
            for frame, rotation in keyframes:
                bpy.context.scene.frame_set(frame)
                pose_bone.rotation_mode = 'XYZ'
                pose_bone.rotation_euler = rotation
                pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return {
            "message": f"Applied {clip_name} animation",
            "action_name": action_name,
            "duration": clip["duration"],
            "loop": clip["loop"]
        }


def run_headless_server(port=9876):
    import sys
    
    print(f"Initializing Akku MCP server...", flush=True)
    server = BlenderMCPServer(host='localhost', port=port)
    server.start()
    
    print(f"MCP server started on port {port}. Waiting for commands...", flush=True)
    sys.stdout.flush()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    import sys
    port = 9876
    try:
        if "--" in sys.argv:
            idx = sys.argv.index("--")
            if len(sys.argv) > idx + 1:
                port = int(sys.argv[idx + 1])
    except (ValueError, IndexError):
        pass
    
    print(f"Starting Blender MCP with port {port}", flush=True)
    sys.stdout.flush()
    run_headless_server(port)
