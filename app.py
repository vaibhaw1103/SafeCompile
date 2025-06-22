# app.py
# This is the Flask backend for your SafeCompile web GUI.

import os
import uuid
from flask import Flask, request, render_template, jsonify, send_from_directory # NEW: import send_from_directory

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

# Create directory for parse tree images if it doesn't exist
PARSE_TREE_IMAGE_DIR = os.path.join('static', 'parse_trees') # Moved this here as it's an app-wide config
if not os.path.exists(PARSE_TREE_IMAGE_DIR):
    os.makedirs(PARSE_TREE_IMAGE_DIR)


@app.route('/')
def index():
    """
    Renders the main HTML page for the SafeCompile GUI.
    """
    return render_template('index.html')

# Route to serve the generated parse tree images
@app.route('/static/parse_trees/<filename>') # Changed route to reflect static serving
def serve_parse_tree_image(filename):
    """
    Serves the generated parse tree images from the static/parse_trees directory.
    """
    return send_from_directory(os.path.join(app.root_path, 'static', 'parse_trees'), filename) # Corrected path


@app.route('/analyze_and_compile', methods=['POST'])
def analyze_and_compile_endpoint():
    """
    API endpoint to receive C code, run analysis, compile, and execute.
    Returns JSON response with all results.
    """
    code_string = request.json.get('code', '')

    if not code_string:
        return jsonify({"error": "No code provided for analysis."}), 400

    temp_filename = os.path.join(app.config['UPLOAD_FOLDER'], f"user_code_{uuid.uuid4()}.c")
    
    # Initialize results dictionaries (these will be populated or stay empty on error)
    analysis_output = {} # This will directly hold the dict from analyze_code
    compilation_execution_results = {}
    
    try:
        with open(temp_filename, 'w') as f:
            f.write(code_string)

        # --- Step 1: Run Security Analysis (now includes parse tree generation) ---
        # The analyze_code function already returns the dictionary in the format
        # expected by the frontend under the 'analysis' key.
        analysis_output = analyze_code(code_string)
        
        # --- Step 2: Run Compilation and Execution ---
        compilation_execution_results = compile_and_run_c_code(temp_filename)

        # Combine all results into a single JSON response
        full_report = {
            "analysis": analysis_output, # Directly use the output from analyze_code
            "compilation_execution": compilation_execution_results,
            # The parse_tree info is already INSIDE analysis_output.
            # No need for a separate 'parse_tree' top-level key if 'analyze_code'
            # already includes 'parse_tree_image' and 'parse_tree_generated'
            # within its returned dictionary.
            # If analyze_code returns 'parse_tree_image' and 'parse_tree_generated'
            # at its top level, then the frontend should access data.analysis.parse_tree_image.
            # Your script.js is already doing this: data.parse_tree.generated, data.parse_tree.image_path
            # Let's adjust script.js to look under data.analysis.parse_tree_...
            # OR make analyze_code return parse_tree details in a nested dictionary
            # as previously discussed.

            # Re-reading script.js:
            # data.parse_tree && data.parse_tree.generated && data.parse_tree.image_path
            # This implies script.js expects a top-level 'parse_tree' key.
            # But analyze_code returns parse_tree_image and parse_tree_generated at its root.

            # To fix this, let's adjust the structure of analysis_output in analyze.py
            # to nest parse_tree information correctly, OR update app.py to construct it.

            # Given analyze.py already has them at root level of its return dict,
            # it's better to pass them from analyze_output to full_report['parse_tree']
            # as script.js expects.

            "parse_tree": { # Re-add this explicit nesting as script.js expects
                "image_path": analysis_output.get("parse_tree_image"),
                "generated": analysis_output.get("parse_tree_generated")
            }
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


# app.py
# ... (rest of your code) ...

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000) # ADD host='0.0.0.0'