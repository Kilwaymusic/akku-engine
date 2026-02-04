"""
Akku Engine - GCP Worker Flask Server
Serves the Blender character generation API
"""

from flask import Flask, request, jsonify, send_file
import subprocess
import uuid
import os
import traceback

app = Flask(__name__)

# Configuration
BASE_DIR = "/home/composerkil/akku-engine"
SCRIPT_PATH = os.path.join(BASE_DIR, "akku-sdk.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
BLENDER_PATH = "blender"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "version": "2.0.0", "sdk": "akku-sdk"})

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a 3D character based on prompt"""
    try:
        data = request.get_json()
        
        prompt = data.get('prompt', 'default character')
        style = data.get('style', 'stylized')
        poly_level = data.get('polyLevel', 'medium')
        job_id = data.get('jobId', str(uuid.uuid4()))
        gender = data.get('gender', None)
        
        # Output path
        output_filename = f"{job_id}.glb"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"[Akku Worker] Starting generation for job {job_id}")
        print(f"  Prompt: {prompt}")
        print(f"  Style: {style}")
        print(f"  Poly Level: {poly_level}")
        
        # Build Blender command
        cmd = [
            BLENDER_PATH,
            "--background",
            "--python", SCRIPT_PATH,
            "--",
            "--prompt", prompt,
            "--style", style,
            "--poly-level", poly_level,
            "--output", output_path
        ]
        
        if gender:
            cmd.extend(["--gender", gender])
        
        # Run Blender
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"[Akku Worker] Blender stdout:\n{result.stdout}")
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

@app.route('/status', methods=['GET'])
def status():
    """Get server status"""
    return jsonify({
        "status": "running",
        "sdk_path": SCRIPT_PATH,
        "sdk_exists": os.path.exists(SCRIPT_PATH),
        "output_dir": OUTPUT_DIR,
        "blender_available": subprocess.run(["which", BLENDER_PATH], capture_output=True).returncode == 0
    })

if __name__ == '__main__':
    print("[Akku Worker] Starting Flask server on port 5000...")
    print(f"[Akku Worker] SDK Path: {SCRIPT_PATH}")
    print(f"[Akku Worker] Output Dir: {OUTPUT_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=False)
