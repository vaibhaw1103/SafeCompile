# app.py
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import subprocess
import os
import uuid
import sys
import time
import logging
import threading
import queue
import shutil
import signal
import platform 

# Import your custom modules
from analyze import analyze_code 
from main import compile_and_run_c_code_in_docker, _cleanup_files_main 

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*", 
                    async_mode='threading', 
                    logger=True, 
                    engineio_logger=True,
                    max_http_buffer_size=100 * 1024 * 1024, 
                    ping_timeout=60, 
                    ping_interval=25) 

# --- Logging Configuration ---
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) 
if root_logger.hasHandlers():
    root_logger.handlers.clear()
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root_logger.addHandler(handler)
app.logger.setLevel(logging.INFO) 

# --- Directory Setup ---
TEMP_CODE_DIR = 'temp_code_files'
COMPILED_BINARIES_DIR = 'compiled_binaries'
PARSE_TREE_IMAGE_DIR = os.path.join('static', 'parse_trees')
for d in [TEMP_CODE_DIR, COMPILED_BINARIES_DIR, PARSE_TREE_IMAGE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

active_sessions = {} 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# --- NEW: Background Task for Analysis and Compilation ---
def analysis_and_run_task(sid, code, mode):
    """
    This function runs in a background thread to avoid blocking the server.
    It performs analysis, compilation, and execution, emitting results as they are ready.
    """
    c_filepath = os.path.join(TEMP_CODE_DIR, f"temp_code_{uuid.uuid4()}.c")
    exe_filepath_for_cleanup = None

    try:
        with open(c_filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        app.logger.info(f"Session {sid}: Code saved to {c_filepath}")

        # Step 1: Run Security Analysis and emit results
        app.logger.info(f"Session {sid}: Starting code analysis...")
        raw_analysis_results = analyze_code(code) 
        app.logger.info(f"Session {sid}: Analysis complete.")
        
        frontend_analysis_payload = {
            "analysis": {
                "gemini_findings": raw_analysis_results.get("gemini_findings", []),
                "insecure_function_findings": raw_analysis_results.get("insecure_function_findings", []), 
                "ml_vulnerable": raw_analysis_results.get("ml_vulnerable"),
                "ml_probability": raw_analysis_results.get("ml_probability"),
                "overall_safe": raw_analysis_results.get("overall_safe"),
            },
            "parse_tree": { 
                "image_path": raw_analysis_results.get("parse_tree_image"),
                "generated": raw_analysis_results.get("parse_tree_generated")
            }
        }
        socketio.emit('analysis_results', frontend_analysis_payload, room=sid)

        # Step 2: Compile & Run (if not in analyze-only mode)
        if mode == 'compile':
            app.logger.info(f"Session {sid}: Starting Docker-based compilation...")
            socketio.emit('terminal_output', {'output': '\x1b[33m[INFO]: Starting secure compilation...\x1b[0m\r\n'}, room=sid)

            compilation_execution_info = compile_and_run_c_code_in_docker(c_filepath, COMPILED_BINARIES_DIR, sid)
            
            socketio.emit('compiler_output', {"output": compilation_execution_info.get("compiler_output", "")}, room=sid)

            if compilation_execution_info["status"] == "success" and compilation_execution_info.get("docker_process") is not None: 
                docker_process = compilation_execution_info["docker_process"]
                exe_filepath_for_cleanup = compilation_execution_info.get("executable_path")

                input_queue = queue.Queue()
                active_sessions[sid] = {
                    'process_obj': docker_process,
                    'c_filepath': c_filepath, 
                    'exe_filepath': exe_filepath_for_cleanup, 
                    'input_queue': input_queue
                }

                # Start threads to handle I/O for the running process
                start_io_threads(sid, docker_process, input_queue)
                socketio.emit('program_started', {"message": f"Compilation started. Enter input if prompted."}, room=sid)
            else:
                error_msg = compilation_execution_info.get("error_message", "Compilation failed.")
                socketio.emit('execution_complete', {'success': False, 'error': error_msg}, room=sid)
                _cleanup_files_main(c_filepath, None)
                
        elif mode == 'analyze':
            socketio.emit('execution_complete', {"success": True, "message": "Analysis complete."}, room=sid)
            _cleanup_files_main(c_filepath, None)

    except Exception as e:
        app.logger.error(f"Session {sid}: Server error in background task: {e}", exc_info=True)
        socketio.emit('execution_complete', {"success": False, "error": f"Server error: {str(e)}"}, room=sid)
        _cleanup_files_main(c_filepath, exe_filepath_for_cleanup)

# --- NEW: Main Socket.IO handler now starts the background task ---
@socketio.on('compile_and_analyze')
def handle_compile_and_analyze(data):
    sid = request.sid
    code = data.get('code', '')
    mode = data.get('mode', 'compile') 
    app.logger.info(f"Session {sid}: Received request in mode: {mode}. Starting background task.")
    
    if not code:
        emit('execution_complete', {"success": False, "error": "No code provided."}, room=sid)
        return

    # Start the long-running process in the background
    socketio.start_background_task(analysis_and_run_task, sid, code, mode)

# --- I/O Threading Functions ---
def start_io_threads(sid, process, input_queue):
    # Thread to read stdout/stderr from Docker process
    def read_pipe(pipe, s_sid, is_stderr=False):
        try:
            # --- FIXED: Read in small chunks to avoid blocking on readline ---
            while True:
                chunk = pipe.read(1024)
                if not chunk:
                    break
                output = chunk.decode('utf-8', errors='ignore')
                if is_stderr:
                    output = f"\x1b[31m{output}\x1b[0m"
                socketio.emit('terminal_output', {'output': output}, room=s_sid)
        except Exception as e:
            app.logger.error(f"Session {s_sid}: Error reading from pipe: {e}", exc_info=True)
        finally:
            pipe.close()
            app.logger.info(f"Session {s_sid}: Pipe reader thread finished.")
            socketio.start_background_task(wait_and_cleanup_wrapper, s_sid)

    # Thread to write input to Docker process stdin
    def write_pipe_input(pipe, q, s_sid):
        while True:
            try:
                input_data = q.get() 
                if input_data is None: break
                pipe.write(input_data.encode('utf-8'))
                pipe.flush()
            except (ValueError, OSError):
                app.logger.debug(f"Session {s_sid}: STDIN pipe closed.")
                break
        app.logger.info(f"Session {s_sid}: Input writer thread finished.")

    stdout_reader = threading.Thread(target=read_pipe, args=(process.stdout, sid, False))
    stderr_reader = threading.Thread(target=read_pipe, args=(process.stderr, sid, True))
    input_writer = threading.Thread(target=write_pipe_input, args=(process.stdin, input_queue, sid))

    for t in [stdout_reader, stderr_reader, input_writer]:
        t.daemon = True
        t.start()

def wait_and_cleanup_wrapper(s_sid):
    if s_sid not in active_sessions:
        return

    session_data = active_sessions.get(s_sid)
    if not session_data:
        return 

    process_obj = session_data['process_obj']
    input_q = session_data.get('input_queue') 

    if input_q:
        input_q.put(None) 

    exit_code, success, error_message = None, False, None
    
    try:
        exit_code = process_obj.wait(timeout=30)
        success = (exit_code == 0)
        if not success: error_message = f"Program exited with non-zero code: {exit_code}"
    except subprocess.TimeoutExpired:
        process_obj.terminate()
        error_message = "Program execution timed out."
    except Exception as e:
        error_message = f"Error during program execution: {str(e)}"
    finally:
        socketio.emit('execution_complete', {"success": success, "error": error_message, "exit_code": exit_code}, room=s_sid) 
        
        if s_sid in active_sessions:
            c_fp = active_sessions[s_sid].get('c_filepath')
            exe_fp = active_sessions[s_sid].get('exe_filepath')
            _cleanup_files_main(c_fp, exe_fp)
            del active_sessions[s_sid] 
        app.logger.info(f"Session {s_sid}: Execution and cleanup complete.")

@socketio.on('terminal_input')
def handle_terminal_input(data):
    sid = request.sid
    session_data = active_sessions.get(sid)
    if session_data and session_data.get('input_queue'):
        session_data['input_queue'].put(data.get('input', ''))
    else:
        socketio.emit('terminal_output', {'output': '\x1b[31m[INFO]: No active program to receive input.\x1b[0m\r\n'}, room=sid) 

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    app.logger.info(f"Client {sid} disconnected.")
    if sid in active_sessions:
        session_data = active_sessions[sid]
        process_obj = session_data.get('process_obj')
        if process_obj and process_obj.poll() is None:
            process_obj.terminate()
        
        _cleanup_files_main(session_data.get('c_filepath'), session_data.get('exe_filepath'))
        del active_sessions[sid]
        app.logger.info(f"Session {sid}: Cleaned up session data on disconnect.")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
