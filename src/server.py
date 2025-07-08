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
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCRIPTS_LOCATION = "/workspace/src"

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory job store
JOBS = {}

# Format: (script_name, display_label, input_ext, output_ext)
PROCESSING_STEPS = [
    ("scene_downloader_wrapper.py", "Scene Search & Download", "", ""),  # date range → extracted folders
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

def process_job(batchname, input_path, date_range=None, path=11, row=31, cloud_cover=0.80):
    base = os.path.join(app.config['UPLOAD_FOLDER'], batchname)
    current_input = input_path

    for i, (script, label, input_ext, output_ext) in enumerate(PROCESSING_STEPS):
        JOBS[batchname]['status'] = label
        
        JOBS[batchname]['logs'].append(f"{label} started")

        # Special handling for scene downloader step
        if script == "scene_downloader_wrapper.py" and date_range:
            # Create output directory for this batch
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{batchname}_scenes")
            
            # Prepare date range JSON
            date_range_json = json.dumps({
                "start_date": date_range[0],
                "end_date": date_range[1],
                "path": path,
                "row": row,
                "cloud_cover": cloud_cover
            })
            
            # Run the scene downloader wrapper
            exit_code = stream_subprocess(
                ['python3', script, date_range_json, output_dir],
                batchname
            )
            
            if exit_code != 0:
                JOBS[batchname]['status'] = f"Failed at {label}"
                return
            
            # Set current_input to the output directory for next step
            current_input = output_dir
            continue

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

@app.route('/pipeline', methods=['POST'])
def start_pipeline():
    """
    Start the full pipeline with date range input
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        batchname = secure_filename(data.get('batchname', '').strip())
        if not batchname:
            return jsonify({"error": "Missing or invalid batch name"}), 400
        
        # Get date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "Both start_date and end_date are required"}), 400
        
        # Get optional parameters
        path = data.get('path', 11)
        row = data.get('row', 31)
        cloud_cover = data.get('cloud_cover', 0.80)
        
        # Initialize job
        JOBS[batchname] = {
            "name": batchname,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Initializing",
            "logs": deque(maxlen=2500)
        }
        
        # Start background thread for the full pipeline
        threading.Thread(
            target=process_job, 
            args=(batchname, None, (start_date, end_date), path, row, cloud_cover)
        ).start()
        
        return jsonify({
            "message": "Pipeline started successfully", 
            "batchname": batchname,
            "date_range": [start_date, end_date],
            "parameters": {
                "path": path,
                "row": row,
                "cloud_cover": cloud_cover
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Error starting pipeline: {str(e)}"}), 500

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
