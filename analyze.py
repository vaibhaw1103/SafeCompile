# analyze.py
import logging
import os
import uuid
import shutil
import json
import re
from datetime import datetime
import numpy as np
from openai import OpenAI

# Import custom modules
from lexer import tokenize_code
from parser_custom import Parser
from ml_predict import predict_vulnerability
from visualize_tree import create_parse_tree_graph

# --- Directory and Logging Setup ---
TEMP_CODE_DIR = 'temp_code_files'
if not os.path.exists(TEMP_CODE_DIR):
    os.makedirs(TEMP_CODE_DIR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PARSE_TREE_IMAGE_DIR = os.path.join('static', 'parse_trees')
if not os.path.exists(PARSE_TREE_IMAGE_DIR):
    os.makedirs(PARSE_TREE_IMAGE_DIR)

# --- ENHANCED AI ANALYSIS FUNCTION ---
def get_ai_analysis_improved(code: str):
    """
    Uses the OpenRouter API to perform an expert-level security analysis of C code.
    This version includes more robust error handling and JSON parsing.
    """
    response_text = "" # Initialize to handle potential API errors
    try:
        # --- MODIFIED SECTION ---
        # Load the API key from an environment variable ONLY.
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        # If the key is not found, log an error and exit gracefully.
        if not api_key:
            logger.error("CRITICAL: OPENROUTER_API_KEY environment variable not set.")
            return [] # Return an empty list to gracefully fail
        # --- END OF MODIFIED SECTION ---
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    except Exception as e:
        logger.error(f"OpenRouter API key not configured correctly: {e}")
        return []

    numbered_code = "\\n".join([f"{i+1}: {line}" for i, line in enumerate(code.splitlines())])

    prompt = f"""
    You are an expert C security engineer. Analyze the following C code for security vulnerabilities.
    **CRITICAL INSTRUCTION**: The user's code is provided below with line numbers. When you report a `line_number` in your JSON response, you MUST use the exact line number provided in the input. Do not count lines yourself.

    Focus on common C pitfalls like Buffer Overflows, Format String Vulnerabilities, Integer Overflows, etc.

    For each issue you find, provide a JSON object with these keys:
    - "title": A short, descriptive title for the vulnerability.
    - "line_number": The exact integer line number from the provided, numbered code.
    - "severity": "Critical", "High", "Medium", or "Low".
    - "explanation": A clear explanation of the risk.
    - "suggestion": A concrete fix, including a corrected code snippet if possible.

    Return the output as a valid JSON list of objects. If no issues are found, return an empty list [].

    Numbered C Code to analyze:
    ```c
    {numbered_code}
    ```
    """

    try:
        response = client.chat.completions.create(
            model="mistralai/devstral-medium", # Updated model
            messages=[
                {"role": "system", "content": "You are a comprehensive security auditor. Analyze ALL vulnerability types. Return only a valid JSON array of objects."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )

        response_text = response.choices[0].message.content.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1).strip()
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1).strip()
        if response_text.endswith("```"):
            response_text = response_text.rsplit("```", 1)[0].strip()

        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
        else:
            json_string = response_text

        results = json.loads(json_string)
        
        if isinstance(results, dict):
            for key, value in results.items():
                if isinstance(value, list):
                    results = value
                    break
        
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict) and 'line_number' in r]
        
        logger.warning(f"AI response was valid JSON but not a list. Response: {json_string[:200]}")
        return []

    except json.JSONDecodeError:
        logger.error(f"JSON parsing error in AI analysis. Raw response was: {response_text[:500]}...")
        return []
    except Exception as e:
        logger.error(f"Error in enhanced AI analysis (e.g., rate limit): {e}", exc_info=True)
        return []

# --- DEDICATED ANALYSIS FUNCTIONS ---

def _analyze_arithmetic_operations(code: str):
    """
    Dedicated arithmetic vulnerability detection with comprehensive pattern matching.
    """
    vulnerabilities = []
    lines = code.splitlines()
    input_variables = set()
    
    input_patterns = [
        (r'scanf\s*\([^,]*,\s*&(\w+)', 'scanf input'),
        (r'(\w+)\s*=\s*atoi\s*\(', 'atoi conversion'),
        (r'(\w+)\s*=\s*argv', 'command line argument'), 
        (r'fgets\s*\((\w+)', 'file input'),
    ]
    
    for line_num, line in enumerate(lines, 1):
        for pattern, input_type in input_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                input_variables.add(match)
    
    arithmetic_patterns = [
        (r'(\w+)\s*=\s*(\w+)\s*[\+\-\*\/]\s*(\w+)\s*;', 'arithmetic'),
        (r'(\w+)\s*[\+\-\*\/]=\s*(\w+)\s*;', 'compound arithmetic'),
        (r'\w+\[\s*([^\]]+)\s*\]', 'array indexing arithmetic'),
        (r'malloc\s*\(\s*([^\)]+)\)', 'malloc with arithmetic')
    ]
    
    for line_num, line in enumerate(lines, 1):
        for pattern, op_type in arithmetic_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                op_vars = re.findall(r'\b\w+\b', str(match))
                uses_input = any(var in input_variables for var in op_vars)
                
                context_start = max(0, line_num - 3)
                context_end = min(len(lines), line_num + 2)
                context = '\n'.join(lines[context_start:context_end])
                has_bounds_check = bool(re.search(r'(if\s*\(.*[<>]=?)|(INT_MAX)|(INT_MIN)', context, re.IGNORECASE))

                if uses_input and not has_bounds_check:
                    severity = "High"
                elif not has_bounds_check:
                    severity = "Medium"
                else:
                    continue
                
                vulnerabilities.append({
                    'title': f'Integer Overflow Risk in {op_type.title()}',
                    'line_number': line_num, 'severity': severity,
                    'explanation': f'Arithmetic operation without explicit bounds checking detected. {"It involves user-controlled data, increasing risk." if uses_input else ""}',
                    'suggestion': 'Validate inputs and add bounds checking before the operation. Example: if (a > INT_MAX - b) { /* handle overflow */ }.',
                    'type': 'arithmetic_vulnerability'
                })
    return vulnerabilities

def _analyze_with_pattern_matching(code: str):
    """Traditional pattern matching for known function vulnerabilities."""
    patterns = {
        'gets': {'pattern': r'gets\s*\(', 'title': 'Unsafe gets() Usage', 'severity': 'Critical'},
        'strcpy': {'pattern': r'strcpy\s*\(', 'title': 'Unsafe strcpy() Usage', 'severity': 'High'},
        'sprintf': {'pattern': r'sprintf\s*\(', 'title': 'Unsafe sprintf() Usage', 'severity': 'High'},
        'printf_format': {'pattern': r'printf\s*\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\)', 'title': 'Format String Vulnerability', 'severity': 'Medium'}
    }
    results = []
    lines = code.splitlines()
    for name, info in patterns.items():
        for line_num, line in enumerate(lines, 1):
            if re.search(info['pattern'], line):
                results.append({
                    'title': info['title'], 'line_number': line_num, 'severity': info['severity'],
                    'explanation': 'This function is known to be insecure and can lead to vulnerabilities.',
                    'suggestion': 'Consult documentation for safer alternatives like fgets, strncpy, or snprintf.',
                    'type': 'function_vulnerability'
                })
    return results

def _deduplicate_findings(results: list) -> list:
    """Removes duplicate findings based on line number and title, prioritizing more detailed ones."""
    unique_findings = {}
    for finding in results:
        line_num = finding.get('line_number')
        title = finding.get('title', '').lower()
        key = (line_num, title)
        
        if key not in unique_findings or ('suggestion' in finding and 'suggestion' not in unique_findings[key]):
            unique_findings[key] = finding
            
    return list(unique_findings.values())

def _create_error_finding(title: str, line_number: int, error_msg: str):
    """Creates a structured error message for the frontend."""
    return {
        'title': title, 'line_number': line_number, 'severity': 'Critical',
        'explanation': f'A system error occurred: {error_msg}',
        'suggestion': 'Please check the system configuration or code and try again.',
        'type': 'system_error'
    }

def convert_to_serializable(obj):
    """Converts numpy and other non-serializable types to JSON-friendly formats."""
    if isinstance(obj, (float, int, str, bool, type(None))):
        return obj
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, (list, tuple)):
        return [convert_to_serializable(elem) for elem in obj]
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    return str(obj)

# --- MAIN ANALYSIS FUNCTION ---
def analyze_code(code: str, ml_threshold: float = 0.5):
    """
    Main analysis function with comprehensive, multi-layered security detection.
    """
    all_findings = []
    
    # Layer 1: AI Analysis (most comprehensive)
    ai_findings = get_ai_analysis_improved(code)
    all_findings.extend(ai_findings)

    # Layer 2: Dedicated Arithmetic Analysis
    arithmetic_findings = _analyze_arithmetic_operations(code)
    all_findings.extend(arithmetic_findings)
    
    # Layer 3: Fallback Pattern Matching
    pattern_findings = _analyze_with_pattern_matching(code)
    all_findings.extend(pattern_findings)

    # Layer 4: Custom Parser Analysis
    logger.info("Running custom parser-based analysis.")
    tokens = tokenize_code(code)
    parser = Parser(tokens)
    _, parser_insecure_function_issues, parse_tree_root = parser.parse()
    all_findings.extend(parser_insecure_function_issues)
    
    # Deduplicate all findings
    final_findings = _deduplicate_findings(all_findings)
    
    # Generate Parse Tree Image
    parse_tree_image_path = None
    parse_tree_generated = False
    if parse_tree_root:
        image_filename_base = f"parse_tree_{uuid.uuid4().hex}"
        output_path_for_graphviz = os.path.join(PARSE_TREE_IMAGE_DIR, image_filename_base)
        try:
            if shutil.which("dot"):
                create_parse_tree_graph(parse_tree_root, output_path_for_graphviz)
                final_image_path_on_host = f"{output_path_for_graphviz}.png"
                if os.path.exists(final_image_path_on_host) and os.path.getsize(final_image_path_on_host) > 0:
                    parse_tree_image_path = os.path.join('parse_trees', f"{image_filename_base}.png").replace('\\', '/')
                    parse_tree_generated = True
            else:
                logger.error("Graphviz 'dot' executable not found in PATH.")
        except Exception as e:
            logger.error(f"Error during parse tree visualization: {e}", exc_info=True)

    # Layer 5: ML Prediction
    ml_vulnerable = False
    ml_probability = 0.0
    logger.info("Running ML prediction...")
    try:
        ml_vulnerable, ml_probability = predict_vulnerability(code, ml_threshold)
    except Exception as e:
        logger.error(f"Error during ML prediction: {e}", exc_info=True)

    overall_safe = not bool(final_findings) and not ml_vulnerable

    return {
        "gemini_findings": convert_to_serializable(final_findings),
        "insecure_function_findings": [], 
        "ml_vulnerable": convert_to_serializable(ml_vulnerable),
        "ml_probability": convert_to_serializable(ml_probability),
        "overall_safe": convert_to_serializable(overall_safe),
        "report_messages": [],
        "parse_tree_image": parse_tree_image_path,
        "parse_tree_generated": parse_tree_generated,
    }