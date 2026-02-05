"""
Akku Engine - GCP Worker Flask Server v4.0
Modular SDK with Hard-Surface Kitbash and Vertex Color support
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import uuid
import os
import traceback
import json
import time
from datetime import datetime

app = Flask(__name__)

# Configuration
BASE_DIR = "/home/composerkil/akku-engine"
SDK_ENTRY_SCRIPT = os.path.join(BASE_DIR, "server/akku_sdk", "run.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
BLENDER_PATH = "blender"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "5.1.0",
        "sdk": "server/akku_sdk (Extrude-First)",
        "architecture": "mcp-style"
    })


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available SDK tools with JSON schemas for LLM consumption"""
    tools = [
        {
            "name": "generate_procedural_base",
            "description": "Create procedural humanoid mesh using Extrude-First methodology (single connected mesh)",
            "params": {
                "style": {"type": "string", "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"], "default": "stylized"},
                "poly_level": {"type": "string", "enum": ["ultra_low", "low", "medium", "high"], "default": "medium"},
                "gender": {"type": "string", "enum": ["male", "female", "neutral"], "default": "male"},
                "equipment": {"type": "string", "enum": ["default", "armor", "robe"], "default": "default"},
                "hierarchical": {"type": "boolean", "default": False, "description": "DEPRECATED: Use false for Extrude-First unified mesh"}
            }
        },
        {
            "name": "apply_body_type",
            "description": "Apply body type deformation to character mesh",
            "params": {
                "body_type": {"type": "string", "enum": ["default", "muscular", "thin", "fat", "tall", "athletic", "heroic", "chibi"], "default": "default"},
                "muscular": {"type": "number", "min": 0, "max": 1, "description": "Muscle definition override"},
                "fat": {"type": "number", "min": 0, "max": 1, "description": "Body fat override"},
                "height": {"type": "number", "min": 0.7, "max": 1.3, "description": "Height multiplier"},
                "shoulder_width": {"type": "number", "min": 0.7, "max": 1.5, "description": "Shoulder width multiplier"}
            }
        },
        {
            "name": "apply_style",
            "description": "Apply style transformations based on prompt",
            "params": {
                "prompt": {"type": "string", "description": "Character description"},
                "style": {"type": "string", "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"]},
                "poly_level": {"type": "string", "enum": ["ultra_low", "low", "medium", "high"]}
            }
        },
        {
            "name": "equip_item",
            "description": "Attach equipment from Kitbash library",
            "params": {
                "category": {"type": "string", "enum": ["helmet", "shoulder", "chest", "gauntlet", "boots", "weapon", "shield"]},
                "style": {"type": "string", "enum": ["knight", "scifi", "mage", "rogue"]},
                "color": {"type": "array", "items": "number", "description": "RGB color [0-1, 0-1, 0-1]"}
            }
        },
        {
            "name": "capture_screenshot",
            "description": "Capture viewport screenshot for Gemini VLM review (headless-safe)",
            "params": {
                "output_path": {"type": "string", "description": "Output PNG file path"},
                "view": {"type": "string", "enum": ["front", "side", "quarter", "top"], "default": "front"},
                "resolution": {"type": "integer", "min": 256, "max": 2048, "default": 768},
                "include_composite": {"type": "boolean", "default": False, "description": "Create front+side 2-up composite"}
            }
        },
        {
            "name": "get_scene_info",
            "description": "Get current scene statistics for Gemini context",
            "params": {}
        },
        {
            "name": "export_glb",
            "description": "Export scene as GLB file for game engines",
            "params": {
                "output_path": {"type": "string", "description": "Output GLB file path"}
            }
        },
        {
            "name": "generate_character",
            "description": "Complete character generation pipeline (all steps combined)",
            "params": {
                "prompt": {"type": "string", "description": "Character description"},
                "style": {"type": "string", "enum": ["realistic", "stylized", "chibi", "sd", "mobile", "minifig", "cartoon"]},
                "poly_level": {"type": "string", "enum": ["ultra_low", "low", "medium", "high"]},
                "output_path": {"type": "string"},
                "gender": {"type": "string", "enum": ["male", "female", "neutral"]},
                "body_type": {"type": "string"},
                "equipment": {"type": "string", "enum": ["default", "armor", "robe"]}
            }
        }
    ]
    return jsonify({
        "version": "5.1.0",
        "description": "Akku SDK v5.0 - Extrude-First unified mesh 3D character generation",
        "tools": tools
    })


@app.route('/generate', methods=['POST'])
def generate():
    """Generate a 3D character based on prompt"""
    try:
        data = request.get_json()
        
        prompt = data.get('prompt', 'default character')
        style = data.get('style', 'stylized')
        poly_level = data.get('polyLevel', 'medium')
        job_id = data.get('jobId', str(uuid.uuid4()))
        gender = data.get('gender', 'male')
        body_type_raw = data.get('bodyType', 'auto')
        use_remesh = data.get('useRemesh', False)
        equipment = data.get('equipment', 'default')
        gemini_params_raw = data.get('geminiParams', None)
        capture_screenshot = data.get('captureScreenshot', False)
        session_id = data.get('sessionId', '')
        iteration = data.get('iteration', 1)
        
        # Parse Gemini params from Replit server
        gemini_params = None
        if gemini_params_raw:
            try:
                gemini_params = json.loads(gemini_params_raw) if isinstance(gemini_params_raw, str) else gemini_params_raw
                print(f"[Gemini] Received analyzed params: archetype={gemini_params.get('archetype', 'unknown')}")
                
                # Override style/polyLevel from Gemini analysis if available
                if gemini_params.get('style'):
                    gemini_style = gemini_params['style']
                    if gemini_style.get('proportionType'):
                        style = gemini_style['proportionType']
                        print(f"[Gemini] Using analyzed style: {style}")
                    if gemini_style.get('polyLevel'):
                        poly_level = gemini_style['polyLevel']
                        print(f"[Gemini] Using analyzed polyLevel: {poly_level}")
                    if gemini_style.get('gender'):
                        gender = gemini_style['gender']
                        print(f"[Gemini] Using analyzed gender: {gender}")
                
                # Override equipment from Gemini analysis if available
                if gemini_params.get('equipment'):
                    armor_style = gemini_params['equipment'].get('armorStyle', 'none')
                    equipment_map = {
                        'plate': 'armor', 'heavy': 'armor', 'scifi': 'armor',
                        'cloth': 'robe', 'magic': 'robe', 'light': 'robe', 'leather': 'robe',
                        'none': 'default'
                    }
                    equipment = equipment_map.get(armor_style, 'default')
                    print(f"[Gemini] Using analyzed equipment: {equipment} (from armorStyle: {armor_style})")
                    
            except (json.JSONDecodeError, TypeError):
                print(f"[Gemini] Failed to parse geminiParams")
                gemini_params = None
        
        # Parse bodyType - prefer gemini_params.bodyType over request bodyType
        body_type_params = None
        
        # First priority: Use Gemini analyzed bodyType if available
        if gemini_params and gemini_params.get('bodyType'):
            body_type_params = gemini_params.get('bodyType')
            print(f"[Gemini] Using analyzed bodyType: {body_type_params}")
        # Fallback: Parse from request body
        elif isinstance(body_type_raw, str):
            try:
                body_type_params = json.loads(body_type_raw)
            except (json.JSONDecodeError, TypeError):
                body_type_params = {"preset": body_type_raw}
        elif isinstance(body_type_raw, dict):
            body_type_params = body_type_raw
        else:
            body_type_params = {"preset": "auto"}
        
        # Output path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{job_id}_{timestamp}.glb"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"\n{'='*60}")
        print(f"[Akku Worker v4.0] Starting generation")
        print(f"{'='*60}")
        print(f"  Job ID: {job_id}")
        print(f"  Prompt: {prompt}")
        print(f"  Style: {style}")
        print(f"  Poly Level: {poly_level}")
        print(f"  Gender: {gender}")
        print(f"  Equipment: {equipment}")
        print(f"  Body Type Params: {json.dumps(body_type_params)}")
        print(f"  Use Remesh: {use_remesh}")
        print(f"  Gemini Params: {'Yes' if gemini_params else 'No'}")
        if gemini_params:
            print(f"    Archetype: {gemini_params.get('archetype', 'unknown')}")
            print(f"    Body Preset: {gemini_params.get('bodyType', {}).get('preset', 'unknown')}")
            print(f"    Armor Style: {gemini_params.get('equipment', {}).get('armorStyle', 'none')}")
            print(f"    Shader Color: {gemini_params.get('shader', {}).get('baseColor', [0.5, 0.5, 0.5])}")
        print(f"  Output: {output_path}")
        print(f"  Capture Screenshot: {capture_screenshot}")
        print(f"  Session ID: {session_id}")
        print(f"  Iteration: {iteration}")
        print(f"{'='*60}\n")
        
        # Build screenshot path if requested
        screenshot_path = ""
        if capture_screenshot and session_id:
            screenshot_dir = f"/tmp/akku/{session_id}"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = f"{screenshot_dir}/iter{iteration}.png"
        
        # Build Blender command for modular SDK
        # Use safe entry script with arguments passed via command line
        # Pass body type params as JSON string for detailed control
        body_type_json = json.dumps(body_type_params)
        gemini_json = json.dumps(gemini_params) if gemini_params else ""
        cmd = [
            BLENDER_PATH,
            "--background",
            "--python", SDK_ENTRY_SCRIPT,
            "--",
            prompt,
            style,
            poly_level,
            output_path,
            gender,
            body_type_json,
            "true" if use_remesh else "false",
            equipment,
            gemini_json,  # Pass Gemini params to SDK
            screenshot_path  # 10th arg: screenshot path for autonomous agent
        ]
        
        # Run Blender
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"[Akku Worker] Blender output:\n{result.stdout}")
        if result.stderr:
            print(f"[Akku Worker] Blender stderr:\n{result.stderr}")
        
        # Check if file was created
        if not os.path.exists(output_path):
            error_msg = result.stderr or result.stdout or "Unknown error"
            return jsonify({"error": f"GLB not created: {error_msg}"}), 500
        
        # Verify file size
        file_size = os.path.getsize(output_path)
        if file_size < 100:
            return jsonify({"error": f"GLB file too small ({file_size} bytes)"}), 500
        
        print(f"[Akku Worker] Successfully generated {output_filename} ({file_size} bytes)")
        
        # Send file
        return send_file(
            output_path,
            mimetype='model/gltf-binary',
            as_attachment=True,
            download_name=output_filename
        )
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Generation timed out (>120s)"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/execute', methods=['POST'])
def execute_tool():
    """Execute a specific SDK tool (MCP-style endpoint)"""
    try:
        data = request.get_json()
        tool_name = data.get('tool', '')
        params = data.get('params', {})
        
        # This endpoint is for direct tool execution via Python
        # For now, we only support the generate_character tool via Blender
        if tool_name != "generate_character":
            return jsonify({
                "status": "error",
                "message": f"Tool '{tool_name}' must be executed through Blender. Use /generate endpoint."
            }), 400
        
        # Redirect to generate endpoint
        return generate()
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/generate_iterative', methods=['POST'])
def generate_iterative():
    """
    Autonomous 3D agent endpoint with self-verification loop.
    
    Workflow:
    1. Generate base mesh with initial parameters
    2. Capture screenshot
    3. Analyze screenshot (expects Gemini refinement params from Replit)
    4. Apply refinements
    5. Repeat steps 2-4 up to max_iterations times
    6. Export final GLB
    
    Request body:
    {
        "prompt": "Character description",
        "initial_params": {...},  // Initial SDK parameters
        "max_iterations": 3,       // Default 3
        "refinements": [...]       // Optional: pre-computed refinements per iteration
    }
    
    Response:
    {
        "status": "success",
        "iterations": [
            {"iteration": 1, "screenshot_path": "/tmp/...", "scene_info": {...}},
            ...
        ],
        "final_glb_path": "/tmp/final.glb",
        "total_iterations": 3
    }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'humanoid character')
        initial_params = data.get('initial_params', {})
        max_iterations = min(data.get('max_iterations', 3), 5)  # Cap at 5
        refinements = data.get('refinements', [])  # Pre-computed refinements (optional)
        
        print(f"\n{'='*60}")
        print(f"[Akku Iterative] Starting autonomous generation")
        print(f"  Prompt: {prompt}")
        print(f"  Max Iterations: {max_iterations}")
        print(f"  Initial Params: {json.dumps(initial_params, indent=2)}")
        print(f"{'='*60}\n")
        
        # Generate unique session ID
        session_id = f"iter_{int(time.time())}"
        output_dir = f"/tmp/akku/{session_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        iterations_log = []
        current_params = initial_params.copy()
        
        for iteration in range(1, max_iterations + 1):
            print(f"\n[Iteration {iteration}/{max_iterations}]")
            
            screenshot_path = f"{output_dir}/iter{iteration}.png"
            glb_path = f"{output_dir}/iter{iteration}.glb"
            
            # Build iteration-specific params
            iter_params = {
                "prompt": prompt,
                "style": current_params.get('style', {}).get('proportionType', 'stylized'),
                "poly_level": current_params.get('style', {}).get('polyLevel', 'medium'),
                "gender": current_params.get('style', {}).get('gender', 'male'),
                "body_type": current_params.get('bodyType', {}).get('preset', 'default'),
                "equipment": current_params.get('equipment', {}).get('armorStyle', 'default'),
                "output_path": glb_path,
                "screenshot_path": screenshot_path,
                "capture_screenshot": True  # Enable screenshot capture
            }
            
            # Pass full params as JSON for SDK
            params_json = json.dumps(current_params)
            
            # Build Blender command with screenshot capture
            cmd = [
                BLENDER_PATH,
                "--background",
                "--python", SDK_ENTRY_SCRIPT,
                "--",
                prompt,
                iter_params['style'],
                iter_params['poly_level'],
                glb_path,
                iter_params['gender'],
                json.dumps(current_params.get('bodyType', {})),
                "false",  # use_remesh
                iter_params['equipment'],
                params_json,
                screenshot_path  # Additional arg for screenshot capture
            ]
            
            # Run Blender
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            print(f"[Blender] stdout: {result.stdout[:500]}..." if len(result.stdout) > 500 else f"[Blender] stdout: {result.stdout}")
            
            # Check results
            glb_exists = os.path.exists(glb_path)
            screenshot_exists = os.path.exists(screenshot_path)
            glb_size = os.path.getsize(glb_path) if glb_exists else 0
            screenshot_size = os.path.getsize(screenshot_path) if screenshot_exists else 0
            
            # Get scene info from Blender output (parse from stdout)
            scene_info = {
                "mesh_count": 1,
                "total_vertices": 0,
                "total_faces": 0
            }
            
            # Try to extract scene info from stdout
            for line in result.stdout.split('\n'):
                if '"mesh_count":' in line or '"total_vertices":' in line:
                    try:
                        scene_info = json.loads(line)
                    except:
                        pass
            
            iteration_result = {
                "iteration": iteration,
                "glb_path": glb_path if glb_exists else None,
                "glb_size_bytes": glb_size,
                "screenshot_path": screenshot_path if screenshot_exists else None,
                "screenshot_size_bytes": screenshot_size,
                "scene_info": scene_info,
                "params_used": iter_params
            }
            iterations_log.append(iteration_result)
            
            print(f"[Iteration {iteration}] GLB: {glb_size}B, Screenshot: {screenshot_size}B")
            
            # Apply refinements if provided for next iteration
            if iteration < max_iterations and len(refinements) > iteration - 1:
                refinement = refinements[iteration - 1]
                print(f"[Refinement] Applying: {json.dumps(refinement)}")
                
                # Merge refinement into current params
                if 'bodyType' in refinement:
                    current_params['bodyType'] = {**current_params.get('bodyType', {}), **refinement['bodyType']}
                if 'style' in refinement:
                    current_params['style'] = {**current_params.get('style', {}), **refinement['style']}
                if 'shader' in refinement:
                    current_params['shader'] = {**current_params.get('shader', {}), **refinement['shader']}
                if 'equipment' in refinement:
                    current_params['equipment'] = {**current_params.get('equipment', {}), **refinement['equipment']}
        
        # Final result
        final_glb = iterations_log[-1].get('glb_path') if iterations_log else None
        
        response = {
            "status": "success",
            "session_id": session_id,
            "prompt": prompt,
            "iterations": iterations_log,
            "final_glb_path": final_glb,
            "final_glb_size_bytes": iterations_log[-1].get('glb_size_bytes', 0) if iterations_log else 0,
            "total_iterations": len(iterations_log)
        }
        
        print(f"\n[Akku Iterative] Completed {len(iterations_log)} iterations")
        print(f"  Final GLB: {final_glb}")
        
        return jsonify(response)
        
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "error": "Generation timed out (>120s per iteration)"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/screenshot/<session_id>/<filename>', methods=['GET'])
def get_screenshot(session_id, filename):
    """Retrieve screenshot from iterative generation session"""
    try:
        file_path = f"/tmp/akku/{session_id}/{filename}"
        if not os.path.exists(file_path):
            return jsonify({"error": "Screenshot not found"}), 404
        
        return send_file(file_path, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/glb/<session_id>/<filename>', methods=['GET'])
def get_glb(session_id, filename):
    """Retrieve GLB from iterative generation session"""
    try:
        file_path = f"/tmp/akku/{session_id}/{filename}"
        if not os.path.exists(file_path):
            return jsonify({"error": "GLB not found"}), 404
        
        return send_file(file_path, mimetype='model/gltf-binary', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download/<filename>', methods=['GET'])
def download_generated_glb(filename):
    """Download GLB from autonomous agent generation"""
    try:
        # Security: Only allow .glb files
        if not filename.endswith('.glb'):
            return jsonify({"error": "Invalid file type"}), 400
        
        # Security: Prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        file_path = f"/tmp/akku_generated/{filename}"
        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found: {filename}"}), 404
        
        return send_file(file_path, mimetype='model/gltf-binary', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/execute-code', methods=['POST'])
def execute_code():
    """
    Execute Gemini-generated Blender Python code
    This is the core of the Autonomous 3D Agent - LLM directly controls Blender
    """
    try:
        data = request.get_json()
        
        code = data.get('code', '')
        job_id = data.get('jobId', str(uuid.uuid4()))
        prompt = data.get('prompt', 'unknown')
        
        if not code:
            return jsonify({"error": "No code provided"}), 400
        
        print(f"\n{'='*60}")
        print(f"[Autonomous Agent] Executing Gemini-generated code")
        print(f"{'='*60}")
        print(f"  Job ID: {job_id}")
        print(f"  Prompt: {prompt}")
        print(f"  Code length: {len(code)} chars")
        print(f"{'='*60}\n")
        
        # Create temporary Python script
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_path = f"/tmp/akku_script_{job_id}_{timestamp}.py"
        output_filename = f"{job_id}_{timestamp}.glb"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Wrap the code to add GLB export at the end
        wrapped_code = f'''
{code}

# === AUTO-ADDED: Export to GLB ===
import bpy
output_path = "{output_path}"

# Ensure we're in object mode
if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# Select all mesh objects
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

# Export as GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True
)

print(f"[Akku] Exported to: {{output_path}}")
'''
        
        # Write script to file
        with open(script_path, 'w') as f:
            f.write(wrapped_code)
        
        print(f"[Autonomous Agent] Script written to: {script_path}")
        
        # Execute in Blender
        cmd = [
            BLENDER_PATH,
            "--background",
            "--python", script_path
        ]
        
        print(f"[Autonomous Agent] Running Blender...")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        elapsed = time.time() - start_time
        print(f"[Autonomous Agent] Blender completed in {elapsed:.2f}s")
        
        # Check output
        if result.returncode != 0:
            print(f"[ERROR] Blender stderr: {result.stderr}")
            return jsonify({
                "success": False,
                "error": f"Blender execution failed: {result.stderr[:500]}",
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else ""
            }), 500
        
        # Verify GLB was created
        if not os.path.exists(output_path):
            return jsonify({
                "success": False,
                "error": "GLB file was not created",
                "stdout": result.stdout[-1000:] if result.stdout else ""
            }), 500
        
        file_size = os.path.getsize(output_path)
        print(f"[Autonomous Agent] GLB created: {output_path} ({file_size} bytes)")
        
        # Cleanup temp script
        try:
            os.remove(script_path)
        except:
            pass
        
        return jsonify({
            "success": True,
            "glb_path": output_path,
            "glb_filename": output_filename,
            "file_size": file_size,
            "execution_time": elapsed
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Blender execution timed out (120s)"
        }), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Akku Engine GCP Worker v5.1.0")
    print("Autonomous 3D Agent with Code Execution")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
