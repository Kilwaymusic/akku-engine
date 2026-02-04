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
        "leg_length": 0.3
    },
    "stylized": {  # Stylized proportions (5-6 heads)
        "head_ratio": 0.18,
        "body_height": 1.6,
        "limb_thickness": 0.08,
        "head_scale": 1.0,
        "torso_width": 0.28,
        "leg_length": 0.5
    },
    "realistic": {  # 8-head proportions
        "head_ratio": 0.125,
        "body_height": 1.8,
        "limb_thickness": 0.06,
        "head_scale": 0.9,
        "torso_width": 0.25,
        "leg_length": 0.55
    },
    "chibi": {  # Chibi style (1.5-2 heads)
        "head_ratio": 0.5,
        "body_height": 0.8,
        "limb_thickness": 0.15,
        "head_scale": 1.8,
        "torso_width": 0.4,
        "leg_length": 0.2
    }
}

# Armor plate presets for kitbashing
ARMOR_PRESETS = {
    "shoulder_pad": {"type": "cube", "scale": (0.15, 0.12, 0.08), "bevel": 0.02},
    "chest_plate": {"type": "cube", "scale": (0.35, 0.08, 0.3), "bevel": 0.03},
    "knee_guard": {"type": "cube", "scale": (0.1, 0.08, 0.12), "bevel": 0.015},
    "gauntlet": {"type": "cylinder", "scale": (0.07, 0.07, 0.15), "bevel": 0.01},
    "helmet_visor": {"type": "cube", "scale": (0.2, 0.05, 0.1), "bevel": 0.02},
    "belt_buckle": {"type": "cube", "scale": (0.12, 0.04, 0.08), "bevel": 0.01},
    "boot_plate": {"type": "cube", "scale": (0.1, 0.15, 0.08), "bevel": 0.015}
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
        if self.running:
            print("MCP Server is already running")
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

            print(f"Akku MCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start MCP server: {str(e)}")
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
        print("MCP Server thread started")

        while self.running:
            try:
                try:
                    client, address = self.socket.accept()
                    print(f"MCP Client connected: {address}")
                    self._handle_client(client)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {str(e)}")
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
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

    def export_glb(self, filepath):
        bpy.ops.object.select_all(action='SELECT')
        
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                for mod in obj.modifiers:
                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    except:
                        pass

        bpy.ops.export_scene.gltf(
            filepath=filepath,
            export_format='GLB',
            use_selection=True,
            export_apply=True,
            export_materials='EXPORT'
        )

        return f"Exported to {filepath}"

    # ============================================================
    # AKKU SDK CATEGORY 1: BASE GENERATION
    # ============================================================

    def spawn_humanoid_base(self, proportion_type="stylized"):
        """
        Spawn a clean topology humanoid base with optimized UV and proportions.
        proportion_type: 'sd', 'stylized', 'realistic', 'chibi'
        """
        self.clear_scene()
        
        preset = BASE_PRESETS.get(proportion_type, BASE_PRESETS["stylized"])
        
        body_height = preset["body_height"]
        head_scale = preset["head_scale"]
        torso_width = preset["torso_width"]
        limb_thickness = preset["limb_thickness"]
        leg_length = preset["leg_length"]
        
        # Calculate positions based on body height
        head_pos = body_height * 0.9
        torso_pos = body_height * 0.6
        hip_pos = body_height * 0.4
        
        # Head - sphere for organic look
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.22 * head_scale,
            segments=16,
            ring_count=12,
            location=(0, 0, head_pos)
        )
        head = bpy.context.active_object
        head.name = "AkkuBase_Head"
        
        # Torso - rounded box style
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(0, 0, torso_pos)
        )
        torso = bpy.context.active_object
        torso.name = "AkkuBase_Torso"
        torso.scale = (torso_width, torso_width * 0.6, body_height * 0.25)
        bpy.ops.object.transform_apply(scale=True)
        
        # Add bevel to torso for rounded edges
        bevel = torso.modifiers.new(name="Bevel", type='BEVEL')
        bevel.width = 0.05
        bevel.segments = 3
        
        # Hips
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(0, 0, hip_pos)
        )
        hips = bpy.context.active_object
        hips.name = "AkkuBase_Hips"
        hips.scale = (torso_width * 0.9, torso_width * 0.5, body_height * 0.1)
        bpy.ops.object.transform_apply(scale=True)
        
        # Arms
        arm_positions = [
            (-torso_width - 0.05, 0, torso_pos + 0.05),
            (torso_width + 0.05, 0, torso_pos + 0.05)
        ]
        for i, pos in enumerate(arm_positions):
            side = "L" if i == 0 else "R"
            
            # Upper arm
            bpy.ops.mesh.primitive_cylinder_add(
                radius=limb_thickness,
                depth=body_height * 0.2,
                location=(pos[0] + (0.1 if i == 0 else -0.1), pos[1], pos[2] - 0.05),
                rotation=(0, 1.57, 0)
            )
            upper_arm = bpy.context.active_object
            upper_arm.name = f"AkkuBase_UpperArm_{side}"
            
            # Forearm
            bpy.ops.mesh.primitive_cylinder_add(
                radius=limb_thickness * 0.85,
                depth=body_height * 0.18,
                location=(pos[0] + (0.25 if i == 0 else -0.25), pos[1], pos[2] - 0.05),
                rotation=(0, 1.57, 0)
            )
            forearm = bpy.context.active_object
            forearm.name = f"AkkuBase_Forearm_{side}"
            
            # Hand
            bpy.ops.mesh.primitive_cube_add(
                size=limb_thickness * 2,
                location=(pos[0] + (0.4 if i == 0 else -0.4), pos[1], pos[2] - 0.05)
            )
            hand = bpy.context.active_object
            hand.name = f"AkkuBase_Hand_{side}"
            hand.scale = (1, 0.4, 1.2)
            bpy.ops.object.transform_apply(scale=True)

        # Legs
        leg_positions = [(-torso_width * 0.4, 0, hip_pos - 0.1), (torso_width * 0.4, 0, hip_pos - 0.1)]
        for i, pos in enumerate(leg_positions):
            side = "L" if i == 0 else "R"
            
            # Upper leg
            bpy.ops.mesh.primitive_cylinder_add(
                radius=limb_thickness * 1.3,
                depth=leg_length,
                location=(pos[0], pos[1], pos[2] - leg_length * 0.5)
            )
            upper_leg = bpy.context.active_object
            upper_leg.name = f"AkkuBase_UpperLeg_{side}"
            
            # Lower leg
            bpy.ops.mesh.primitive_cylinder_add(
                radius=limb_thickness * 1.1,
                depth=leg_length * 0.9,
                location=(pos[0], pos[1], pos[2] - leg_length * 1.3)
            )
            lower_leg = bpy.context.active_object
            lower_leg.name = f"AkkuBase_LowerLeg_{side}"
            
            # Foot
            bpy.ops.mesh.primitive_cube_add(
                size=limb_thickness * 2.5,
                location=(pos[0], pos[1] - 0.03, pos[2] - leg_length * 1.7)
            )
            foot = bpy.context.active_object
            foot.name = f"AkkuBase_Foot_{side}"
            foot.scale = (0.8, 1.5, 0.4)
            bpy.ops.object.transform_apply(scale=True)

        # Apply default gray material to all
        default_mat = bpy.data.materials.new(name="AkkuBase_Material")
        default_mat.use_nodes = True
        bsdf = default_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.5
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.name.startswith("AkkuBase_"):
                obj.data.materials.clear()
                obj.data.materials.append(default_mat)

        return {
            "message": f"Spawned {proportion_type} humanoid base",
            "proportion_type": proportion_type,
            "body_height": body_height,
            "objects": [obj.name for obj in bpy.context.scene.objects if obj.name.startswith("AkkuBase_")]
        }

    def deform_body(self, part, strength=0.5, deform_type="scale"):
        """
        Deform a specific body part using shape keys or scaling.
        part: 'head', 'torso', 'arms', 'legs', 'hands', 'feet', 'shoulders', 'hips'
        strength: -1.0 to 1.0 (negative = shrink, positive = enlarge)
        deform_type: 'scale', 'stretch_vertical', 'stretch_horizontal', 'bulge'
        """
        part_mapping = {
            "head": ["AkkuBase_Head"],
            "torso": ["AkkuBase_Torso"],
            "arms": ["AkkuBase_UpperArm_L", "AkkuBase_UpperArm_R", "AkkuBase_Forearm_L", "AkkuBase_Forearm_R"],
            "legs": ["AkkuBase_UpperLeg_L", "AkkuBase_UpperLeg_R", "AkkuBase_LowerLeg_L", "AkkuBase_LowerLeg_R"],
            "hands": ["AkkuBase_Hand_L", "AkkuBase_Hand_R"],
            "feet": ["AkkuBase_Foot_L", "AkkuBase_Foot_R"],
            "shoulders": ["AkkuBase_UpperArm_L", "AkkuBase_UpperArm_R"],
            "hips": ["AkkuBase_Hips"]
        }
        
        target_objects = part_mapping.get(part, [])
        if not target_objects:
            raise ValueError(f"Unknown body part: {part}")
        
        scale_factor = 1.0 + (strength * 0.5)  # Convert -1..1 to 0.5..1.5
        
        modified_objects = []
        for obj_name in target_objects:
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                continue
            
            bpy.context.view_layer.objects.active = obj
            
            if deform_type == "scale":
                obj.scale *= scale_factor
            elif deform_type == "stretch_vertical":
                obj.scale[2] *= scale_factor
            elif deform_type == "stretch_horizontal":
                obj.scale[0] *= scale_factor
                obj.scale[1] *= scale_factor
            elif deform_type == "bulge":
                # Add lattice modifier for bulge effect
                bpy.ops.object.add(type='LATTICE')
                lattice = bpy.context.active_object
                lattice.name = f"{obj_name}_Lattice"
                lattice.location = obj.location
                lattice.scale = obj.scale * 1.5
                
                # Modify lattice points for bulge
                lattice.data.points_u = 2
                lattice.data.points_v = 2
                lattice.data.points_w = 3
                
                # Add lattice modifier to object
                bpy.context.view_layer.objects.active = obj
                mod = obj.modifiers.new(name="Lattice", type='LATTICE')
                mod.object = lattice
            
            modified_objects.append(obj_name)
        
        bpy.ops.object.transform_apply(scale=True)
        
        return {
            "message": f"Deformed {part} with {deform_type}",
            "strength": strength,
            "modified_objects": modified_objects
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
            bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
        elif preset["type"] == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1, location=pos)
        
        armor = bpy.context.active_object
        armor.name = f"Armor_{location}_{style}"
        
        # Apply scale from preset and user scale
        base_scale = preset["scale"]
        armor.scale = (base_scale[0] * scale, base_scale[1] * scale, base_scale[2] * scale)
        bpy.ops.object.transform_apply(scale=True)
        
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
        target_obj: name of object to add details to
        detail_level: 'low', 'medium', 'high'
        """
        obj = bpy.data.objects.get(target_obj)
        if not obj:
            raise ValueError(f"Object not found: {target_obj}")
        
        if obj.type != 'MESH':
            raise ValueError(f"Object must be a mesh: {target_obj}")
        
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        detail_configs = {
            "low": {"cuts": 1, "inset": 0.01, "depth": 0.005},
            "medium": {"cuts": 2, "inset": 0.015, "depth": 0.008},
            "high": {"cuts": 3, "inset": 0.02, "depth": 0.01}
        }
        
        config = detail_configs.get(detail_level, detail_configs["medium"])
        
        # Enter edit mode to add panel lines
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Add loop cuts for panel detail
        try:
            for _ in range(config["cuts"]):
                bpy.ops.mesh.loopcut_slide(
                    MESH_OT_loopcut={"number_cuts": 1},
                    TRANSFORM_OT_edge_slide={"value": 0}
                )
        except:
            pass  # Loop cut may fail on some geometries
        
        # Inset faces for panel detail
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.mesh.inset(thickness=config["inset"], depth=config["depth"])
        except:
            pass
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Add edge split for sharp edges
        edge_split = obj.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
        edge_split.split_angle = 0.523599  # 30 degrees
        
        return {
            "message": f"Added {detail_level} sci-fi details to {target_obj}",
            "cuts": config["cuts"],
            "inset": config["inset"]
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
        Join all mesh objects and bind to an armature with automatic weights.
        Creates a game-ready rigged character.
        """
        # Collect all mesh objects
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        if not mesh_objects:
            raise ValueError("No mesh objects found in scene")
        
        # Apply all modifiers first
        for obj in mesh_objects:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            for mod in list(obj.modifiers):
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                except:
                    pass
        
        # Join all meshes
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        
        if len(mesh_objects) > 1:
            bpy.ops.object.join()
        
        final_mesh = bpy.context.active_object
        final_mesh.name = "AkkuCharacter"
        
        # Create armature
        bpy.ops.object.armature_add(enter_editmode=True)
        armature = bpy.context.active_object
        armature.name = "AkkuArmature"
        self.current_armature = armature
        
        # Get mesh bounds for bone positioning
        bbox = [final_mesh.matrix_world @ Vector(corner) for corner in final_mesh.bound_box]
        min_z = min(v.z for v in bbox)
        max_z = max(v.z for v in bbox)
        height = max_z - min_z
        
        # Remove default bone
        bpy.ops.armature.select_all(action='SELECT')
        bpy.ops.armature.delete()
        
        # Create bone structure
        arm_data = armature.data
        
        # Root bone
        root = arm_data.edit_bones.new("Root")
        root.head = (0, 0, min_z)
        root.tail = (0, 0, min_z + height * 0.1)
        
        # Spine
        spine = arm_data.edit_bones.new("Spine")
        spine.head = (0, 0, min_z + height * 0.4)
        spine.tail = (0, 0, min_z + height * 0.6)
        spine.parent = root
        
        # Head
        head = arm_data.edit_bones.new("Head")
        head.head = (0, 0, min_z + height * 0.8)
        head.tail = (0, 0, max_z)
        head.parent = spine
        
        # Arms
        for side, x_mult in [("L", -1), ("R", 1)]:
            upper_arm = arm_data.edit_bones.new(f"UpperArm_{side}")
            upper_arm.head = (x_mult * height * 0.15, 0, min_z + height * 0.65)
            upper_arm.tail = (x_mult * height * 0.25, 0, min_z + height * 0.55)
            upper_arm.parent = spine
            
            lower_arm = arm_data.edit_bones.new(f"LowerArm_{side}")
            lower_arm.head = upper_arm.tail
            lower_arm.tail = (x_mult * height * 0.35, 0, min_z + height * 0.45)
            lower_arm.parent = upper_arm
            
            hand = arm_data.edit_bones.new(f"Hand_{side}")
            hand.head = lower_arm.tail
            hand.tail = (x_mult * height * 0.4, 0, min_z + height * 0.4)
            hand.parent = lower_arm
        
        # Legs
        for side, x_mult in [("L", -1), ("R", 1)]:
            upper_leg = arm_data.edit_bones.new(f"UpperLeg_{side}")
            upper_leg.head = (x_mult * height * 0.08, 0, min_z + height * 0.35)
            upper_leg.tail = (x_mult * height * 0.08, 0, min_z + height * 0.2)
            upper_leg.parent = root
            
            lower_leg = arm_data.edit_bones.new(f"LowerLeg_{side}")
            lower_leg.head = upper_leg.tail
            lower_leg.tail = (x_mult * height * 0.08, 0, min_z + height * 0.05)
            lower_leg.parent = upper_leg
            
            foot = arm_data.edit_bones.new(f"Foot_{side}")
            foot.head = lower_leg.tail
            foot.tail = (x_mult * height * 0.08, -height * 0.08, min_z)
            foot.parent = lower_leg
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Parent mesh to armature with automatic weights
        bpy.ops.object.select_all(action='DESELECT')
        final_mesh.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        
        try:
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        except:
            # Fallback to basic parenting if auto weights fail
            bpy.ops.object.parent_set(type='ARMATURE')
        
        return {
            "message": "Character finalized and rigged",
            "mesh_name": final_mesh.name,
            "armature_name": armature.name,
            "bone_count": len(arm_data.bones),
            "bones": [bone.name for bone in arm_data.bones]
        }

    def test_animation(self, clip_name="idle"):
        """
        Apply a test animation clip to the character.
        clip_name: 'idle', 'walk', 'attack', 'jump'
        """
        if not self.current_armature:
            raise ValueError("No armature found. Run finalize_and_bind first.")
        
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
    server = BlenderMCPServer(host='localhost', port=port)
    server.start()
    
    print(f"MCP Server running on port {port}. Waiting for commands...")
    
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
    
    print(f"Starting Blender MCP with port {port}")
    run_headless_server(port)
