# clang_analyzer.py
import clang.cindex
import os
import sys

# CRITICAL FIX: Import CursorKind for direct enum comparison
from clang.cindex import CursorKind as CK 

# --- Configuration for libclang ---
# This part is CRUCIAL. If clang.cindex.LibclangError occurs,
# you'll need to uncomment ONE of the lines below that matches your OS and set the correct path to libclang.dll/so/dylib.
# Make sure there is NO LEADING WHITESPACE before the uncommented line.

# For Windows:
# IMPORTANT: This path has been set based on your provided location,
# but now points to the directory containing libclang.dll, not the file itself.
# clang.cindex.Config.set_library_path("B:/clang+llvm-18.1.8-x86_64-pc-windows-msvc/clang+llvm-18.1.8-x86_64-pc-windows-msvc/bin") # Corrected path
# If the above doesn't work, ensure libclang.dll is directly in your system's PATH, or provide the *absolute path* to the directory.
# If you are in a virtual environment, ensure libclang is accessible within that environment.

# Manual setting for specific OS if auto-detection fails
if sys.platform == "win32":
    # Try the common default installation path first
    default_llvm_bin = "C:/Program Files/LLVM/bin"
    if os.path.exists(os.path.join(default_llvm_bin, "libclang.dll")):
        clang.cindex.Config.set_library_path(default_llvm_bin)
        print(f"DEBUG: libclang path set to default: {default_llvm_bin}")
    else:
        # Fallback to the user-provided specific path if default is not found
        user_provided_path_dir = "B:/clang+llvm-18.1.8-x86_64-pc-windows-msvc/clang+llvm-18.1.8-x86_64-pc-windows-msvc/bin"
        if os.path.exists(os.path.join(user_provided_path_dir, "libclang.dll")):
            clang.cindex.Config.set_library_path(user_provided_path_dir)
            print(f"DEBUG: libclang path set to user-provided: {user_provided_path_dir}")
        else:
            print(f"DEBUG: libclang.dll not found at default ({default_llvm_bin}) or user-provided path ({user_provided_path_dir}). Clang analysis might fail.")

# For Linux (adjust version, e.g., llvm-14, llvm-15, llvm-17):
# clang.cindex.Config.set_library_path("/usr/lib/llvm-14/lib")
# For macOS (Homebrew, adjust path if llvm is installed elsewhere):
# clang.cindex.Config.set_library_path("/usr/local/opt/llvm/lib")


# --- Insecure Function Definitions ---
INSECURE_FUNCTIONS_INFO = {
    "gets": {"fix": "use fgets() with size limits", "cwe": "CWE-120: Buffer Overflow"},
    "strcpy": {"fix": "use strncpy() with size limit", "cwe": "CWE-120: Buffer Overflow"},
    "strcat": {"fix": "use strncat() with size limit", "cwe": "CWE-120: Buffer Overflow"},
    "scanf": {"fix": "specify field width and check return value", "cwe": "CWE-120: Buffer Overflow"},
    "sprintf": {"fix": "use snprintf() to prevent buffer overflows", "cwe": "CWE-120: Buffer Overflow"},
    "system": {"fix": "avoid executing external commands directly; use safer APIs or validate input rigorously", "cwe": "CWE-78: Command Injection"},
    "eval": {"fix": "avoid code injection; parse inputs safely if necessary", "cwe": "CWE-94: Code Injection"}, 
    "popen": {"fix": "avoid executing external commands directly; use safer APIs", "cwe": "CWE-78: Command Injection"},
    "vsprintf": {"fix": "use vsnprintf() to prevent buffer overflows", "cwe": "CWE-120: Buffer Overflow"},
    "malloc": {"fix": "always check return value for NULL; handle allocation failures", "cwe": "CWE-391: Unchecked Error Condition"},
    "calloc": {"fix": "always check return value for NULL; handle allocation failures", "cwe": "CWE-391: Unchecked Error Condition"},
    "realloc": {"fix": "always check return value for NULL; handle allocation failures and temporary pointer assignment", "cwe": "CWE-391: Unchecked Error Condition"},
}

# --- Parse Tree Node (Re-used for visualization compatibility) ---
from parse_tree_node import ParseTreeNode

def create_simplified_parse_tree(cursor: clang.cindex.Cursor):
    """
    Recursively converts a clang.cindex.Cursor (AST node) into your ParseTreeNode structure.
    This allows visualize_tree.py to still be used.
    """
    if not cursor:
        return None

    node_label = cursor.displayname if cursor.displayname else \
                 cursor.spelling if cursor.spelling else \
                 cursor.kind.name 
    
    if cursor.kind == CK.DECL_REF_EXPR:
        node_label = f"Ref: {cursor.spelling}"
    elif cursor.kind == CK.CALL_EXPR:
        node_label = f"Call: {cursor.spelling.split('(')[0] if '(' in cursor.spelling else cursor.spelling}"
    elif cursor.kind == CK.INTEGER_LITERAL:
        node_label = f"Int: {cursor.spelling}"
    elif cursor.kind == CK.STRING_LITERAL:
        node_label = f"String: {cursor.spelling}"
    elif cursor.kind == CK.VAR_DECL:
        node_label = f"Var Decl: {cursor.spelling}"
    elif cursor.kind == CK.FUNCTION_DECL:
        node_label = f"Func Decl: {cursor.spelling}"
    # CRITICAL FIX: Direct comparison for operator kinds
    elif cursor.kind in (CK.BINARY_OPERATOR, CK.UNARY_OPERATOR): 
        # Use spelling if available, otherwise just the kind name
        node_label = f"Op: {cursor.spelling if cursor.spelling else cursor.kind.name}"


    is_terminal = not bool(list(cursor.get_children())) or \
                  cursor.kind.is_literal() or \
                  cursor.kind in [CK.DECL_REF_EXPR]
    
    node_value = cursor.spelling if is_terminal and cursor.spelling else None

    node = ParseTreeNode(name=node_label, value=node_value, is_terminal=is_terminal)

    for child_cursor in cursor.get_children():
        child_node = create_simplified_parse_tree(child_cursor)
        if child_node: 
            node.add_child(child_node)

    return node


def analyze_with_clang(file_path: str):
    """
    Analyzes a C code file using libclang to detect insecure function calls
    and capture clang diagnostics. Does NOT generate parse tree here.

    Args:
        file_path (str): The path to the C source file to analyze.

    Returns:
        tuple: (list of insecure_function_findings, clang_ast_root, list of clang_diagnostics)
        insecure_function_findings: List of dicts, e.g.,
            [{'type': 'insecure_function', 'function': 'gets', 'fix': '...', 'cwe': '...', 'location': {'line': X, 'column': Y}}]
        clang_ast_root: The root of the Clang AST (clang.cindex.Cursor object).
        clang_diagnostics: List of dicts for Clang's own warnings/errors.
    """
    try:
        index = clang.cindex.Index.create()
    except clang.cindex.LibclangError as e:
        error_message = f"CRITICAL ERROR: libclang library not found or could not be loaded. Please ensure LLVM/Clang is installed correctly and its 'bin' directory is in your system's PATH, or set clang.cindex.Config.set_library_path(). Details: {str(e)}"
        print(error_message) 
        return [], None, [{'type': 'error', 'message': error_message, 'location': None}]

    # Arguments for parsing C code
    # -fsyntax-only: only parse, don't compile (faster)
    args = ['-x', 'c', '-Wall', '-Wextra', '-Wpedantic', '-std=c11', '-fsyntax-only'] 
    
    # Parse the file
    tu = index.parse(file_path, args=args, options=0) 

    insecure_function_findings = []
    clang_diagnostics = []

    # Collect Clang's own diagnostics (warnings, errors)
    for diag in tu.diagnostics:
        location = {
            'file': diag.location.file.name if diag.location.file else 'unknown',
            'line': diag.location.line,
            'column': diag.location.column
        }
        clang_diagnostics.append({
            'severity': str(diag.severity).split('.')[-1].lower(), # e.g., 'error', 'warning'
            'message': diag.spelling,
            'location': location
        })

    # Traverse the AST to find insecure function calls
    def find_insecure_calls(cursor):
        # Only check call expressions
        if cursor.kind == CK.CALL_EXPR: 
            # The function being called is usually the first child or a specific kind of child
            # For direct calls, the child would be a DeclRefExpr pointing to the function declaration
            function_name_cursor = None
            for child in cursor.get_children():
                if child.kind in [CK.DECL_REF_EXPR, CK.MEMBER_REF_EXPR]:
                    function_name_cursor = child
                    break

            if function_name_cursor and function_name_cursor.spelling:
                called_function_name = function_name_cursor.spelling
                
                if called_function_name in INSECURE_FUNCTIONS_INFO:
                    info = INSECURE_FUNCTIONS_INFO[called_function_name]
                    location = {
                        'file': cursor.location.file.name if cursor.location.file else 'unknown',
                        'line': cursor.location.line,
                        'column': cursor.location.column
                    }
                    insecure_function_findings.append({
                        'type': 'insecure_function',
                        'function': called_function_name,
                        'message': f"Potential insecure function call: '{called_function_name}'",
                        'fix': info['fix'],
                        'cwe': info['cwe'],
                        'location': location
                    })

        # Recurse for all children
        for child in cursor.get_children():
            find_insecure_calls(child)

    # Start traversal from the translation unit's cursor (root of the AST)
    if tu.cursor:
        find_insecure_calls(tu.cursor)
        clang_ast_root = tu.cursor # Return the actual Clang AST root
    else:
        clang_ast_root = None # No AST generated

    return insecure_function_findings, clang_ast_root, clang_diagnostics

