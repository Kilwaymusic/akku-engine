from flask import Flask, request, jsonify, send_file
import subprocess, uuid, os, traceback, json

app = Flask(__name__)
BASE_DIR = "/home/composerkil/akku-engine"
SDK_ENTRY_SCRIPT = os.path.join(BASE_DIR, "akku_sdk", "run.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
BLENDER_PATH = "blender"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "version": "3.6.0"})

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'default character')
        style = data.get('style', 'stylized')
        poly_level = data.get('polyLevel', 'medium')
        job_id = data.get('jobId', str(uuid.uuid4()))
        gender = data.get('gender', 'male')
        body_type_raw = data.get('bodyType', 'auto')
        use_remesh = data.get('useRemesh', False)
        
        if isinstance(body_type_raw, str):
            try:
                body_type_params = json.loads(body_type_raw)
            except:
                body_type_params = {"preset": body_type_raw}
        elif isinstance(body_type_raw, dict):
            body_type_params = body_type_raw
        else:
            body_type_params = {"preset": "auto"}
        
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.glb")
        print(f"\n[Akku v3.6] Job: {job_id}, Prompt: {prompt}")
        print(f"  Body Params: {json.dumps(body_type_params)}")
        
        cmd = [BLENDER_PATH, "--background", "--python", SDK_ENTRY_SCRIPT, "--",
               prompt, style, poly_level, output_path, gender,
               json.dumps(body_type_params), "true" if use_remesh else "false"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr: print(result.stderr)
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
            return jsonify({"error": "GLB generation failed"}), 500
        
        return send_file(output_path, mimetype='model/gltf-binary',
                         as_attachment=True, download_name=f"{job_id}.glb")
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Akku Worker v3.6")
    app.run(host='0.0.0.0', port=5000, debug=True)
