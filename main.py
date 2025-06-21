# main.py (Only the compile_and_run_c_code function is changed)

import sys
import os
import subprocess

# Import your analysis modules
from analyze import analyze_code

def compile_and_run_c_code(c_filepath, output_dir="compiled_binaries"):
    """
    Compiles the C file using clang and runs the executable if compilation is successful.
    Returns a dictionary with compilation and execution status and output,
    suitable for displaying in a report.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename_without_ext = os.path.splitext(os.path.basename(c_filepath))[0]
    
    # --- START OF FIX ---
    # Append .exe extension for Windows systems
    output_executable_name = filename_without_ext
    if sys.platform == "win32": # Check if the operating system is Windows
        output_executable_name += ".exe"
    # --- END OF FIX ---

    output_executable_path = os.path.join(output_dir, output_executable_name)

    compile_results = {
        "status": "not_attempted",
        "compiler_output": "",
        "program_output": "",
        "error_message": "",
        "executable_path": output_executable_path # Store for potential cleanup
    }

    print(f"\n--- Attempting to compile: {c_filepath} ---")
    # Using clang for compilation. You can add more flags like -Werror etc.
    compile_command = ['clang', c_filepath, '-o', output_executable_path, '-Wextra', '-Wall']

    try:
        process = subprocess.run(
            compile_command,
            capture_output=True,
            text=True,
            check=False
        )
        compile_results["compiler_output"] = process.stdout + process.stderr

        if process.returncode == 0:
            print("Compilation successful!")
            print(f"Executable created at: {output_executable_path}")
            compile_results["status"] = "success"

            print("\n--- Running the compiled program ---")
            try:
                # Use the full path with .exe for execution
                run_process = subprocess.run(
                    [output_executable_path], # THIS LINE IS CORRECTED
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10 # Add a timeout for program execution to prevent infinite loops
                )
                compile_results["program_output"] = run_process.stdout
                if run_process.stderr:
                    compile_results["program_output"] += "\nProgram Errors/Warnings (Stderr):\n" + run_process.stderr

            except subprocess.TimeoutExpired:
                compile_results["program_output"] = "Program execution timed out after 10 seconds."
                compile_results["status"] = "execution_timeout"
                print("Program execution timed out.")
            except FileNotFoundError:
                # This FileNotFoundError should now ideally not happen if the .exe logic is correct
                compile_results["error_message"] = f"Error: Compiled executable not found at {output_executable_path}."
                compile_results["status"] = "execution_failed"
            except Exception as e:
                compile_results["error_message"] = f"An unexpected error occurred while running the program: {e}"
                compile_results["status"] = "execution_failed"

        else:
            print("Compilation failed!")
            compile_results["status"] = "failed"
            compile_results["error_message"] = "Compilation failed. Check compiler output for details."

    except FileNotFoundError:
        compile_results["status"] = "compiler_not_found"
        compile_results["error_message"] = "Error: 'clang' command not found. Please ensure Clang is installed and in your PATH."
    except Exception as e:
        compile_results["status"] = "internal_error"
        compile_results["error_message"] = f"An unexpected error occurred during the compilation process: {e}"

    return compile_results

# ... rest of your main.py code remains the same ...

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_c_file>")
        sys.exit(1)

    c_file_path = sys.argv[1]

    if not os.path.exists(c_file_path):
        print(f"❌ Error: C file '{c_file_path}' not found.")
        sys.exit(1)

    try:
        with open(c_file_path, 'r') as f:
            code_string = f.read()
    except Exception as e:
        print(f"❌ Error reading file '{c_file_path}': {e}")
        sys.exit(1)

    print(f"\n--- Starting security analysis for: {c_file_path} ---")

    # Perform the security analysis
    analysis_results = analyze_code(code_string)

    print("\n--- Security Analysis Report ---")
    for msg in analysis_results["report_messages"]:
        print(msg)

    if analysis_results["overall_safe"]:
        print("\n✅ Overall verdict: Code appears SAFE based on combined analysis.")
    else:
        print("\n⚠️ Overall verdict: POTENTIAL SECURITY VULNERABILITY DETECTED!")
        print("Proceeding with compilation for demonstration purposes, but be cautious!")

    print("\n--- Attempting Compilation and Execution regardless of analysis verdict ---")
    compilation_execution_results = compile_and_run_c_code(c_file_path)

    print("\n--- Compilation & Execution Report ---")
    print(f"Status: {compilation_execution_results['status'].replace('_', ' ').title()}")

    if compilation_execution_results["compiler_output"]:
        print("\nCompiler Output (Stdout/Stderr):")
        print(compilation_execution_results["compiler_output"])

    if compilation_execution_results["program_output"]:
        print("\nProgram Output:")
        print(compilation_execution_results["program_output"])

    if compilation_execution_results["error_message"]:
        print(f"\nError: {compilation_execution_results['error_message']}")

    # Clean up the compiled executable if it was successfully created
    if (compilation_execution_results["status"] == "success" or
        compilation_execution_results["status"] == "execution_timeout") and \
       os.path.exists(compilation_execution_results["executable_path"]):
        try:
            os.remove(compilation_execution_results["executable_path"])
            print(f"\nCleaned up executable: {compilation_execution_results['executable_path']}")
        except OSError as e:
            print(f"Warning: Could not remove executable {compilation_execution_results['executable_path']}: {e}")

    print("\n--- All Processes Finished ---")


if __name__ == "__main__":
    main()