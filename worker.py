from flask import Flask, request, send_file
import subprocess
import os
import uuid

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', 'default')
    job_id = str(uuid.uuid4())
    output_path = f"outputs/{job_id}.glb"
    
    # 디렉토리 생성
    os.makedirs("outputs", exist_ok=True)

    # Blender 실행 명령어 (기존 Replit에서 쓰던 파일명 기준)
    # Replit에 있던 generate_humanoid.py 파일을 이 폴더로 옮겨야 합니다.
    cmd = [
        "blender", "-b", "-P", "generate_humanoid.py", "--",
        "--prompt", prompt, "--output", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return send_file(output_path)
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
