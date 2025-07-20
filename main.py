# main.py
import subprocess
import os
import uuid
import shutil
import logging
import sys
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEMP_CODE_DIR = 'temp_code_files'
COMPILED_BINARIES_DIR = 'compiled_binaries'

# Docker Image to use for C compilation and execution
DOCKER_C_IMAGE = "gcc:latest" 

def compile_and_run_c_code_in_docker(c_file_path, output_dir, session_id):
    """
    Compiles a C source file and then runs the executable inside a Docker container.
    This function now returns information including the subprocess.Popen object
    for the Docker run command, to allow for interactive input/output streaming via Socket.IO.

    Args:
        c_file_path (str): The path to the C source file on the host.
        output_dir (str): Directory on the host where the compiled executable will be stored.
        session_id (str): The Socket.IO session ID for logging purposes.

    Returns:
        dict: A dictionary containing:
              - "status": "success" or "failed"
              - "compiler_output": Full output from the GCC compilation.
              - "error_message": Detailed error message if status is "failed".
              - "docker_process": The subprocess.Popen object for the running Docker container (if successful).
              - "executable_path": The host path to the compiled executable.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate a unique executable name (no .exe needed inside Linux container, but for host reference)
    exe_name_base = f"temp_exec_{uuid.uuid4().hex}" # Use hex for cleaner names
    # The executable name INSIDE the container will be just exe_name_base
    executable_name_in_container = exe_name_base 
    # The path on the host where the executable will be saved
    executable_path_on_host = os.path.join(output_dir, exe_name_base)
    
    # 1. Docker Compilation
    logger.info(f"Session {session_id}: Starting Docker compilation for {c_file_path}")
    
    # Define paths inside the container - ALWAYS USE FORWARD SLASHES FOR DOCKER INTERNAL PATHS
    container_source_dir = "/app/src"
    container_output_dir = "/app/bin"
    
    # Ensure paths inside container use forward slashes
    container_c_filepath = f"{container_source_dir}/{os.path.basename(c_file_path)}"
    container_executable_path = f"{container_output_dir}/{executable_name_in_container}"

    # Construct the Docker compile command
    docker_compile_command = [
        "docker", "run", "--rm",
        "-v", f"{os.path.abspath(os.path.dirname(c_file_path))}:{container_source_dir}",
        "-v", f"{os.path.abspath(output_dir)}:{container_output_dir}",
        DOCKER_C_IMAGE,
        "gcc", container_c_filepath, "-o", container_executable_path,
        "-Wall", "-Wextra", "-pedantic", "-std=c11", "-g"
    ]

    compile_status = {
        "status": "failed",
        "compiler_output": "",
        "error_message": "",
        "executable_path": None, # Initialize as None
        "docker_process": None # Will store the Popen object for the execution phase
    }

    try:
        compile_result = subprocess.run(
            docker_compile_command,
            capture_output=True,
            text=True, # Capture output as text
            check=False, # Do not raise CalledProcessError for non-zero exit codes
            timeout=10 # Timeout for compilation
        )
        compile_status["compiler_output"] = compile_result.stdout + compile_result.stderr

        if compile_result.returncode == 0:
            logger.info(f"Session {session_id}: Docker compilation successful.")
            # Give the filesystem a moment to sync, especially on Windows/Docker Desktop
            time.sleep(0.1) 

            # Verify executable exists on host (due to bind mount)
            if os.path.exists(executable_path_on_host):
                compile_status["status"] = "success" # Set status to success if compilation and file check pass
                compile_status["executable_path"] = executable_path_on_host
            else:
                compile_status["error_message"] = "Compilation reported success, but executable not found on host. Check Docker mounts or filesystem sync."
                logger.error(f"Session {session_id}: {compile_status['error_message']}")
                return compile_status # Return early with failed status

        else:
            compile_status["error_message"] = f"Docker compilation failed with exit code {compile_result.returncode}. Output: {compile_status['compiler_output']}"
            logger.error(f"Session {session_id}: {compile_status['error_message']}")
            return compile_status # Return early with failed status

    except FileNotFoundError:
        compile_status["error_message"] = "Docker command not found. Please ensure Docker is installed and in your system's PATH."
        logger.error(f"Session {session_id}: {compile_status['error_message']}")
        return compile_status
    except subprocess.TimeoutExpired:
        compile_status["error_message"] = "Docker compilation timed out."
        logger.error(f"Session {session_id}: {compile_status['error_message']}")
        return compile_status
    except Exception as e:
        compile_status["error_message"] = f"An unexpected error occurred during Docker compilation: {e}"
        logger.error(f"Session {session_id}: {compile_status['error_message']}", exc_info=True)
        return compile_status

    # 2. Docker Execution (only if compilation was successful)
    if compile_status["status"] == "success": # Only proceed if compilation was truly successful
        logger.info(f"Session {session_id}: Starting Docker execution for {executable_path_on_host}")

        docker_run_command = [
            "docker", "run", "-i", "--rm",
            "--network=none", 
            "--cap-drop=ALL", 
            "--memory=50m", 
            "--cpus=0.5",   
            "-v", f"{os.path.abspath(output_dir)}:{container_output_dir}:ro", # Read-only mount for executable
            DOCKER_C_IMAGE,
            "stdbuf", "-o0", container_executable_path # Use stdbuf -o0 for unbuffered stdout
        ]
        
        logger.info(f"Session {session_id}: Docker run command: {' '.join(docker_run_command)}")

        try:
            docker_process = subprocess.Popen(
                docker_run_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0, # CRITICAL: 0 for unbuffered I/O
                universal_newlines=False # CRITICAL: Work with bytes for terminal compatibility
            )
            compile_status["docker_process"] = docker_process # Store the Popen object
            logger.info(f"Session {session_id}: Docker container execution started with PID {docker_process.pid}")

        except FileNotFoundError:
            compile_status["status"] = "failed"
            compile_status["error_message"] = "Docker command not found during execution phase. Ensure Docker is installed."
            logger.error(f"Session {session_id}: {compile_status['error_message']}")
        except Exception as e:
            compile_status["status"] = "failed"
            compile_status["error_message"] = f"An unexpected error occurred during Docker execution setup: {e}"
            logger.error(f"Session {session_id}: {compile_status['error_message']}", exc_info=True)
            
    return compile_status

def _cleanup_files_main(c_filepath, exe_filepath=None):
    """
    Cleans up the temporary C source file and optionally the compiled executable.
    This is a helper to be called from app.py.
    """
    if c_filepath and os.path.exists(c_filepath):
        try:
            os.remove(c_filepath)
            logger.info(f"Cleaned up C file: {c_filepath}")
        except OSError as e:
            logger.warning(f"Error deleting C file {c_filepath}: {e}")
    
    if exe_filepath and os.path.exists(exe_filepath):
        try:
            os.remove(exe_filepath)
            logger.info(f"Cleaned up executable: {exe_filepath}")
        except OSError as e:
            logger.warning(f"Error deleting executable {exe_filepath}: {e}")

