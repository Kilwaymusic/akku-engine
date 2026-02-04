"""
Blender MCP Addon for Akku Engine
Headless-compatible MCP server for procedural 3D character generation
"""

import bpy
import json
import threading
import socket
import traceback
import os

class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None

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
        client.settimeout(60.0)
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

            handlers = {
                "get_scene_info": self.get_scene_info,
                "execute_code": self.execute_code,
                "create_character": self.create_character,
                "apply_modifier": self.apply_modifier,
                "setup_material": self.setup_material,
                "export_glb": self.export_glb,
                "clear_scene": self.clear_scene,
                "get_object_info": self.get_object_info,
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
        }

    def execute_code(self, code):
        local_vars = {"bpy": bpy, "result": None}
        exec(code, {"bpy": bpy}, local_vars)
        return local_vars.get("result", "Code executed successfully")

    def clear_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        return "Scene cleared"

    def create_character(self, character_type="humanoid", params=None):
        if params is None:
            params = {}

        self.clear_scene()
        
        head_scale = params.get("headScale", 1.0)
        torso_scale = params.get("torsoScale", 1.0)
        arm_length = params.get("armLength", 1.0)
        leg_length = params.get("legLength", 1.0)
        
        skin_color = params.get("skinColor", [0.8, 0.6, 0.5])
        body_color = params.get("bodyColor", [0.2, 0.4, 0.8])

        head_radius = 0.25 * head_scale
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=head_radius,
            segments=32,
            ring_count=16,
            location=(0, 0, 1.7)
        )
        head = bpy.context.active_object
        head.name = "Head"
        
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.3 * torso_scale,
            depth=0.7 * torso_scale,
            location=(0, 0, 1.1)
        )
        torso = bpy.context.active_object
        torso.name = "Torso"
        
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.35 * torso_scale,
            location=(0, 0, 0.7)
        )
        hips = bpy.context.active_object
        hips.name = "Hips"

        arm_positions = [(-0.45, 0, 1.2), (0.45, 0, 1.2)]
        for i, pos in enumerate(arm_positions):
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.08,
                depth=0.5 * arm_length,
                location=pos,
                rotation=(0, 1.57, 0)
            )
            arm = bpy.context.active_object
            arm.name = f"Arm_{'L' if i == 0 else 'R'}"

        leg_positions = [(-0.15, 0, 0.35), (0.15, 0, 0.35)]
        for i, pos in enumerate(leg_positions):
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.1,
                depth=0.7 * leg_length,
                location=pos
            )
            leg = bpy.context.active_object
            leg.name = f"Leg_{'L' if i == 0 else 'R'}"

        skin_mat = bpy.data.materials.new(name="Skin")
        skin_mat.use_nodes = True
        skin_bsdf = skin_mat.node_tree.nodes.get("Principled BSDF")
        if skin_bsdf:
            skin_bsdf.inputs["Base Color"].default_value = (*skin_color, 1.0)
            skin_bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.5)
            skin_bsdf.inputs["Metallic"].default_value = params.get("metallic", 0.0)
        
        body_mat = bpy.data.materials.new(name="Body")
        body_mat.use_nodes = True
        body_bsdf = body_mat.node_tree.nodes.get("Principled BSDF")
        if body_bsdf:
            body_bsdf.inputs["Base Color"].default_value = (*body_color, 1.0)
            body_bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.5)
            body_bsdf.inputs["Metallic"].default_value = params.get("metallic", 0.0)

        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                obj.data.materials.clear()
                if obj.name in ["Head"]:
                    obj.data.materials.append(skin_mat)
                else:
                    obj.data.materials.append(body_mat)

        return {
            "message": f"Created {character_type} character",
            "objects": [obj.name for obj in bpy.context.scene.objects]
        }

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
            bsdf.inputs["IOR"].default_value = material_params.get("ior", 1.45)
            
            if material_params.get("emission"):
                emission_color = material_params.get("emission_color", color)
                emission_strength = material_params.get("emission_strength", 1.0)
                bsdf.inputs["Emission Color"].default_value = (*emission_color, 1.0)
                bsdf.inputs["Emission Strength"].default_value = emission_strength

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
    port = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 9876
    run_headless_server(port)
