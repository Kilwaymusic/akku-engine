"""
Akku Engine - GCP Worker Flask Server v3.0
MCP-style architecture with Blender character generation
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import uuid
import os
import traceback
import json

app = Flask(__name__)

# Configuration
BASE_DIR = "/home/composerkil/akku-engine"
SDK_SCRIPT = os.path.join(BASE_DIR, "akku-sdk.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
BLENDER_PATH = "blender"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "3.0.0",
        "sdk": "akku-sdk-v3",
        "architecture": "mcp-style"
    })


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available SDK tools (MCP-style)"""
    tools = [
        {"name": "load_base_mesh", "description": "Load Mixamo FBX base mesh"},
        {"name": "apply_style", "description": "Apply style-based transformations"},
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
        
        # Output path
        output_filename = f"{job_id}.glb"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"\n{'='*60}")
        print(f"[Akku Worker v3.0] Starting generation")
        print(f"{'='*60}")
        print(f"  Job ID: {job_id}")
        print(f"  Prompt: {prompt}")
        print(f"  Style: {style}")
        print(f"  Poly Level: {poly_level}")
        print(f"  Gender: {gender}")
        print(f"  Output: {output_path}")
        print(f"{'='*60}\n")
        
        # Build Blender command for SDK v3 (positional arguments)
        cmd = [
            BLENDER_PATH,
            "--background",
            "--python", SDK_SCRIPT,
            "--",
            prompt,
            style,
            poly_level,
            output_path,
            gender
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
    print("Akku Engine GCP Worker v3.0")
    print("MCP-Style Character Generation Server")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
