import os
import tarfile
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from collections import deque
import subprocess
import shutil

SCRIPTS_LOCATION = "/workspace/src"

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory job store
JOBS = {}


# Format: (script_name, display_label, input_ext, output_ext)
PROCESSING_STEPS = [
    ("tar_extraction.py", "Extracting TAR.GZ", ".tar.gz", ""),         # outputs folder
    ("new_l2gen.py", "Running l2gen", "", ".nc"),                         # folder → .nc
    ("seadas_gpt.py", "Running SeaDAS GPT", ".nc", "")                    # .nc → folder
]

def stream_subprocess(command, batchname):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    for line in process.stdout:
        JOBS[batchname]['logs'].append(line.strip())

    process.stdout.close()
    return process.wait()

def process_job(batchname, input_path):
    base = os.path.join(app.config['UPLOAD_FOLDER'], batchname)
    current_input = input_path

    for i, (script, label, input_ext, output_ext) in enumerate(PROCESSING_STEPS):
        JOBS[batchname]['status'] = label
        
        JOBS[batchname]['logs'].append(f"{label} started")

        # Build output path
        if output_ext == "":
            output_path = f"{base}_{label.replace(' ', '_').lower()}"
        else:
            output_path = f"{base}_{label.replace(' ', '_').lower()}{output_ext}"

        try:
            exit_code = stream_subprocess(
                ['python3', script, current_input, output_path],
                batchname
            )

            if exit_code != 0:
                JOBS[batchname]['status'] = f"Failed at {label}"
                return
            
            # Delete current_input only if not the last step
            if i < len(PROCESSING_STEPS) - 1:
                try:
                    if os.path.isdir(current_input):
                        shutil.rmtree(current_input)
                    elif os.path.exists(current_input):
                        os.remove(current_input)
                except Exception as cleanup_err:
                    print(f"Warning: Failed to delete {current_input}: {cleanup_err}")

            current_input = output_path

        except Exception as e:
            JOBS[batchname]['status'] = f"Error at {label}: {str(e)}"
            return

    JOBS[batchname]['status'] = "Done"
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files or 'batchname' not in request.form:
        return jsonify({"error": "Missing file or batch name"}), 400

    file = request.files['file']
    batchname = secure_filename(request.form['batchname'].strip())

    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith('.tar.gz'):
        return jsonify({"error": "Only .tar.gz files allowed"}), 400

    filename = f"{batchname}.tar.gz"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    JOBS[batchname] = {
        "name": batchname,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Uploaded",
        "logs": deque(maxlen=2500)
    }

    # Start background thread
    threading.Thread(target=process_job, args=(batchname, filepath)).start()

    return jsonify({"message": "Upload successful", "filename": filename})

@app.route('/delete/<batchname>', methods=['DELETE'])
def delete_job(batchname):
    job = JOBS.get(batchname)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Remove uploaded tar.gz and all derived files
    base = os.path.join(app.config['UPLOAD_FOLDER'], batchname)
    try:
        # Delete all files/folders that start with batchname
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            if f.startswith(batchname):
                path = os.path.join(app.config['UPLOAD_FOLDER'], f)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

        del JOBS[batchname]
        return jsonify({"message": f"Deleted job {batchname}"})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')  # A form with enctype="multipart/form-data"    

@app.route('/jobs', methods=['GET'])
def jobs():
    stripped = [
        {k: v for k, v in job.items() if k != "logs"}
        for job in JOBS.values()
    ]
    return jsonify(stripped)

@app.route('/logs/<batchname>', methods=['GET'])
def get_logs(batchname):
    job = JOBS.get(batchname)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"logs": list(job['logs'])})

if __name__ == '__main__':
    app.run(debug=True)
