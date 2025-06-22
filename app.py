# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import subprocess
import os
import uuid
import sys
import time
import logging

from analyze import analyze_code

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configure logging
app.logger.setLevel(logging.INFO)

TEMP_CODE_DIR = 'temp_code_files'
if not os.path.exists(TEMP_CODE_DIR):
    os.makedirs(TEMP_CODE_DIR)

# This will store paths to compiled executables that need input for a later run.
# Key: session_id (UUID), Value: executable_filepath
# NOTE: In a production system, this should be replaced with a more robust,
# persistent, and secure storage mechanism (e.g., a database, temporary file storage with expiry,
# or more advanced containerization) to manage multiple concurrent users and prevent memory leaks.
# For this demonstration, a simple dictionary is used.
compiled_executables = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Helper function to clean up files safely
def _cleanup_files(c_filepath, exe_filepath):
    """Safely attempts to remove compiled executable and source file."""
    if exe_filepath and os.path.exists(exe_filepath):
        # Add a small delay to ensure OS releases file handle, especially on Windows
        time.sleep(0.1)
        try:
            os.remove(exe_filepath)
            app.logger.info(f"Cleaned up executable: {exe_filepath}")
        except PermissionError:
            app.logger.warning(f"Permission denied when trying to remove executable: {exe_filepath}. It might still be in use.")
        except Exception as e:
            app.logger.error(f"Error removing executable {exe_filepath}: {e}")

    if c_filepath and os.path.exists(c_filepath):
        try:
            os.remove(c_filepath)
            app.logger.info(f"Cleaned up C source file: {c_filepath}")
        except Exception as e:
            app.logger.error(f"Error removing C source file {c_filepath}: {e}")


@app.route('/analyze_and_compile', methods=['POST'])
def analyze_and_compile():
    code = request.json.get('code', '')
    if not code:
        return jsonify({"error": "No code provided."}), 400

    analysis_results = {}
    compiler_output = ""
    program_output = ""
    execution_error = ""
    needs_input = False # Flag to indicate if the program will require user input
    session_id = str(uuid.uuid4()) # Unique ID for this compilation/execution session

    c_filepath = None
    exe_filepath = None

    try:
        # 1. Detect if code *might* need user input (simple heuristic)
        # We look for common C input functions. This is a heuristic and not foolproof.
        input_keywords = ['scanf', 'gets', 'fgets', 'getchar', 'read']
        if any(keyword in code for keyword in input_keywords):
            needs_input = True
            app.logger.info(f"Input function detected in code (session: {session_id}). Setting needs_input = True.")

        # 2. Perform security analysis
        analysis_results = analyze_code(code)

        # 3. Compile the C code
        # Use session_id in filename to easily link executable to session
        unique_c_filename = f"user_code_{session_id}.c"
        c_filepath = os.path.join(TEMP_CODE_DIR, unique_c_filename)

        with open(c_filepath, 'w') as f:
            f.write(code)

        if sys.platform == "win32":
            exe_filepath = c_filepath.replace('.c', '.exe')
        else:
            exe_filepath = c_filepath.replace('.c', '')

        compile_command = ['gcc', c_filepath, '-o', exe_filepath]
        compile_process = subprocess.run(compile_command, capture_output=True, text=True, timeout=10)
        compiler_output = compile_process.stdout + compile_process.stderr

        if compile_process.returncode == 0:
            compiler_output += "\n✅ Program compiled successfully."
            if needs_input:
                # If input is needed, store executable for later run and inform frontend
                compiled_executables[session_id] = exe_filepath
                program_output = "Program requires input. Please enter values below and click 'Run Program'."
                app.logger.info(f"Executable {exe_filepath} stored for session {session_id}")
            else:
                # If no input is needed, run immediately
                app.logger.info(f"Executing program for session {session_id} (no input detected).")
                # Increased timeout to 10 seconds for initial execution
                execute_process = subprocess.run([exe_filepath], capture_output=True, text=True, timeout=10)
                # Capture both stdout and stderr for program output
                program_output = execute_process.stdout + execute_process.stderr
                if execute_process.stderr:
                    # If stderr exists, we still concatenate it to program_output, but also store it as execution_error
                    # for clarity on the server side (though frontend will display it via program_output)
                    execution_error = execute_process.stderr
                # Clean up executable immediately if it was run fully
                _cleanup_files(c_filepath, exe_filepath)
                # Remove from compiled_executables if it was run immediately
                if session_id in compiled_executables:
                    del compiled_executables[session_id]
        else:
            execution_error = "Compilation failed. See compiler output for details."
            # If compilation fails, ensure no dangling executable reference and cleanup
            if session_id in compiled_executables:
                del compiled_executables[session_id]
            _cleanup_files(c_filepath, exe_filepath) # Attempt to cleanup even if compilation failed

    except subprocess.TimeoutExpired as e:
        execution_error = f"Compilation or initial program execution timed out: {e}."
        _cleanup_files(c_filepath, exe_filepath)
        if session_id in compiled_executables:
            del compiled_executables[session_id]
    except Exception as e:
        execution_error = f"An unexpected error occurred during compilation or execution: {str(e)}"
        _cleanup_files(c_filepath, exe_filepath)
        if session_id in compiled_executables:
            del compiled_executables[session_id]
    finally:
        # Only clean up C file here. Executable cleanup depends on needs_input flag and /execute_with_input route.
        if c_filepath and os.path.exists(c_filepath):
            try:
                os.remove(c_filepath)
            except Exception as e:
                app.logger.error(f"Error removing C source file {c_filepath}: {e}")

    compilation_execution_results = {
        "compiler_output": compiler_output,
        "program_output": program_output,
        "error_message": execution_error if execution_error else None
    }

    response_data = {
        "analysis": analysis_results,
        "compilation_execution": compilation_execution_results,
        "needs_input": needs_input,
        "session_id": session_id if needs_input else None # Only send session ID if input is needed
    }
    return jsonify(response_data)


@app.route('/execute_with_input', methods=['POST'])
def execute_with_input():
    """
    New API endpoint to execute a previously compiled program with user-provided input.
    """
    session_id = request.json.get('session_id')
    input_data = request.json.get('input', '')

    program_output = ""
    execution_error = ""
    exe_filepath = None

    if not session_id:
        return jsonify({"error": "No session ID provided for execution."}), 400

    # Retrieve the path to the executable using the session ID
    exe_filepath = compiled_executables.get(session_id)

    if not exe_filepath or not os.path.exists(exe_filepath):
        # This can happen if the server restarted, or file was manually deleted, or ID is invalid
        app.logger.warning(f"Executable for session {session_id} not found or session expired.")
        return jsonify({"error": "Program not found or session expired. Please re-compile the code."}), 404

    try:
        app.logger.info(f"Executing {exe_filepath} with provided input for session {session_id}")
        app.logger.info(f"Input received for session {session_id}: '{input_data}'") # Log the received input

        # Ensure the input ends with a newline to simulate "Enter" press
        if input_data and not input_data.endswith('\n'):
            input_data += '\n'
            app.logger.info(f"Appended newline to input: '{input_data}'") # Log the modified input

        # Execute the program, passing input_data to stdin
        # Increased timeout to 10 seconds for interactive execution
        execute_process = subprocess.run(
            [exe_filepath],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10 # Max 10 seconds for execution
        )
        # Capture both stdout and stderr for program output
        program_output = execute_process.stdout + execute_process.stderr
        if execute_process.stderr:
            execution_error = execute_process.stderr # Still keep this for server-side logging/distinction

    except subprocess.TimeoutExpired:
        execution_error = "Program execution timed out."
    except Exception as e:
        execution_error = f"An error occurred during program execution: {str(e)}"
    finally:
        # Always clean up the executable after it's run via this endpoint
        _cleanup_files(None, exe_filepath) # C file was already cleaned up in analyze_and_compile
        # Remove the session ID from the dictionary after it's used
        if session_id in compiled_executables:
            del compiled_executables[session_id]
            app.logger.info(f"Removed session {session_id} from compiled_executables.")

    return jsonify({
        "program_output": program_output,
        "error_message": execution_error
    })


@app.route('/analyze_code_only', methods=['POST'])
def analyze_code_only():
    code = request.json.get('code', '')
    if not code:
        return jsonify({"error": "No code provided for analysis."}), 400

    try:
        analysis_results = analyze_code(code)
        return jsonify({"analysis": analysis_results})
    except Exception as e:
        app.logger.error(f"Error during analysis: {e}")
        return jsonify({"error": f"An internal server error occurred during analysis: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
