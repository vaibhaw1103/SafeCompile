# app.py
# This is the Flask backend for your SafeCompile web GUI.

import os
import uuid
from flask import Flask, request, render_template, jsonify

# IMPORTANT: Ensure your analyze.py and main.py files are in the same directory as this app.py
# We will import the core logic from them.
from analyze import analyze_code
from main import compile_and_run_c_code # This function handles clang compilation and execution

app = Flask(__name__)
# Configure a temporary directory to save user-submitted C code files
UPLOAD_FOLDER = 'temp_code_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the upload directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    """
    Renders the main HTML page for the SafeCompile GUI.
    """
    return render_template('index.html')

@app.route('/analyze_and_compile', methods=['POST'])
def analyze_and_compile_endpoint():
    """
    API endpoint to receive C code, run analysis, compile, and execute.
    Returns JSON response with all results.
    """
    # Get the C code string from the incoming JSON request
    code_string = request.json.get('code', '')

    if not code_string:
        return jsonify({"error": "No code provided for analysis."}), 400

    # Generate a unique filename for the temporary C file
    temp_filename = os.path.join(app.config['UPLOAD_FOLDER'], f"user_code_{uuid.uuid4()}.c")
    
    # Initialize results dictionaries
    analysis_results = {}
    compilation_execution_results = {}
    
    try:
        # Save the user's code to a temporary file
        with open(temp_filename, 'w') as f:
            f.write(code_string)

        # --- Step 1: Run Security Analysis ---
        # Call your existing analyze_code function
        analysis_results = analyze_code(code_string)
        
        # --- Step 2: Run Compilation and Execution ---
        # Call your existing compile_and_run_c_code function
        # This function is designed to compile and run regardless of analysis verdict
        compilation_execution_results = compile_and_run_c_code(temp_filename)

        # Combine all results into a single JSON response
        full_report = {
            "analysis": analysis_results,
            "compilation_execution": compilation_execution_results
        }
        return jsonify(full_report)

    except Exception as e:
        # Catch any unexpected errors during the process
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500
    finally:
        # Ensure the temporary C file is cleaned up
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError as e:
                print(f"Warning: Could not remove temporary file {temp_filename}: {e}")
        
        # The compiled executable cleanup is handled by compile_and_run_c_code itself


if __name__ == '__main__':
    # Run the Flask development server
    # In a production environment, you would use a WSGI server like Gunicorn or uWSGI
    app.run(debug=True, port=5000) # debug=True for development, auto-reloads on code changes