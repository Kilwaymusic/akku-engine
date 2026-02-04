"""
Akku Engine - GCP Worker Flask Server v3.5
Modular SDK architecture with Blender character generation
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import uuid
import os
import traceback
import json
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
        "version": "3.5.0",
        "sdk": "server/akku_sdk (modular)",
        "architecture": "mcp-style"
    })


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available SDK tools (MCP-style)"""
    tools = [
        {"name": "load_base_mesh", "description": "Load Mixamo FBX base mesh"},
        {"name": "apply_style", "description": "Apply style-based transformations"},
        {"name": "apply_body_type", "description": "Apply body type deformation"},
        {"name": "apply_stylized_shader", "description": "Apply edge/cavity shader"},
        {"name": "equip_item", "description": "Equip kitbash parts"},
        {"name": "export_glb", "description": "Export scene as GLB file"},
        {"name": "generate_character", "description": "Complete character generation pipeline"}
    ]
    return jsonify({"tools": tools})


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
        
        # Parse bodyType - can be JSON string with detailed params or simple preset name
        body_type_params = None
        if isinstance(body_type_raw, str):
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
        print(f"[Akku Worker v3.6] Starting generation")
        print(f"{'='*60}")
        print(f"  Job ID: {job_id}")
        print(f"  Prompt: {prompt}")
        print(f"  Style: {style}")
        print(f"  Poly Level: {poly_level}")
        print(f"  Gender: {gender}")
        print(f"  Body Type Params: {json.dumps(body_type_params)}")
        print(f"  Use Remesh: {use_remesh}")
        print(f"  Output: {output_path}")
        print(f"{'='*60}\n")
        
        # Build Blender command for modular SDK
        # Use safe entry script with arguments passed via command line
        # Pass body type params as JSON string for detailed control
        body_type_json = json.dumps(body_type_params)
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
            "true" if use_remesh else "false"
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


if __name__ == "__main__":
    print("=" * 60)
    print("Akku Engine GCP Worker v3.5")
    print("Modular SDK Character Generation Server")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
