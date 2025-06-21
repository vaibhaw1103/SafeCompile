# analyze.py
import os
# Assume lexer, parser_custom, ml_predict are correctly imported and their functions available
# --- START OF FIX: Use tokenize_code function directly ---
from lexer import tokenize_code # Correctly import the function
# --- END OF FIX ---
from parser_custom import Parser
# Make sure this import matches your ml_predict file and function name
from ml_predict import predict_vulnerability 

# IMPORTANT: If your ml_predict.py uses numpy extensively and returns numpy arrays or types,
# you might need to import numpy here to correctly handle its types.
# For example: import numpy as np

# Helper function to convert potentially non-JSON-serializable types (like numpy.float32)
# to native Python types (float, int, etc.)
def convert_to_serializable(obj):
    """
    Recursively converts non-JSON-serializable objects (like numpy types)
    into standard Python types.
    """
    if isinstance(obj, (float, int, str, bool, type(None))):
        return obj
    
    # Check for numpy types. If your ml_predict uses numpy, this is crucial.
    # We check for the 'item()' method, which numpy scalars have to convert to native Python types.
    # You might need to import numpy as np and use isinstance(obj, np.generic) for broader coverage
    # if you encounter similar issues with other numpy data types.
    if hasattr(obj, 'item') and callable(obj.item):
        return obj.item() # Convert numpy scalar to a native Python type

    if isinstance(obj, list):
        return [convert_to_serializable(elem) for elem in obj]
    
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    
    # Fallback for any other complex objects that might not be serializable
    return str(obj) 

# --- START OF FIX: Reverted StaticAnalyzer and analyze_code to original structure ---
class StaticAnalyzer:
    def __init__(self, parser_warnings):
        self.parser_warnings = parser_warnings
        self.static_vulnerabilities = []
        # In a more advanced AST-based system, this would traverse the AST.
        # For now, we're treating parser warnings as static vulnerabilities.
        self._process_parser_warnings()

    def _process_parser_warnings(self):
        # Your parser currently puts formatted strings into its warnings list.
        # We'll just copy those over as static issues.
        self.static_vulnerabilities.extend(self.parser_warnings)

    def get_vulnerabilities(self):
        return self.static_vulnerabilities

def analyze_code(code: str, ml_threshold: float = 0.5):
    """
    Runs static + ML analysis on the code.
    Returns a dictionary with detailed analysis results.
    """
    report_messages = [] # Initialize the list that main.py expects!

    # === Lexical Analysis ===
    # --- START OF FIX: Call tokenize_code directly ---
    tokens = tokenize_code(code) # Call the function directly
    # --- END OF FIX ---
    report_messages.append(f"Lexical analysis generated {len(tokens)} tokens.")

    # === Static Rule-Based Parsing & Analysis ===
    parser = Parser(tokens)
    # The parser currently prints warnings *and* returns them.
    # We use this returned list as our initial static findings for StaticAnalyzer.
    parser_generated_warnings = parser.parse()

    static_analyzer = StaticAnalyzer(parser_generated_warnings)
    static_issues = static_analyzer.get_vulnerabilities()

    if static_issues:
        report_messages.append("\nStatic Analysis Findings:")
        for issue in static_issues:
            report_messages.append(f"  - {issue}")
    else:
        report_messages.append("No direct static rule violations detected by parser-based rules.")

    # === ML-Based Prediction ===
    # --- START OF FIX: Ensure ml_prediction_raw is handled for serialization ---
    ml_prediction_raw = predict_vulnerability(code, ml_threshold)
    ml_vulnerable, ml_prob = convert_to_serializable(ml_prediction_raw[0]), convert_to_serializable(ml_prediction_raw[1])
    # --- END OF FIX ---

    report_messages.append(f"\nML Prediction (CodeBERT + XGBoost):")
    report_messages.append(f"  - Probability of Vulnerability: {ml_prob:.4f}")
    if ml_vulnerable:
        report_messages.append(f"  - ML Model Verdict: VULNERABLE (above threshold {ml_threshold})")
    else:
        report_messages.append(f"  - ML Model Verdict: SAFE (below threshold {ml_threshold})")


    # === Combine Verdicts ===
    # If there are any static issues OR the ML model predicts vulnerable, then it's not overall safe.
    overall_safe = not static_issues and not ml_vulnerable

    if not overall_safe:
        report_messages.append("\nOVERALL VERDICT: ❌ VULNERABILITY DETECTED!")
    else:
        report_messages.append("\nOVERALL VERDICT: ✅ Code appears SAFE.")

    return {
        "static_issues": convert_to_serializable(static_issues), # Ensure static_issues are serializable
        "ml_vulnerable": convert_to_serializable(ml_vulnerable),
        "ml_probability": convert_to_serializable(ml_prob),
        "overall_safe": convert_to_serializable(overall_safe),
        "report_messages": convert_to_serializable(report_messages) # THIS IS THE KEY main.py expects!
    }
# --- END OF FIX ---
