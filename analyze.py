# analyze.py
import os
import uuid
from lexer import tokenize_code
from parser_custom import Parser
from ml_predict import predict_vulnerability 

import numpy as np
from visualize_tree import create_parse_tree_graph 

# Helper function to convert potentially non-JSON-serializable types
def convert_to_serializable(obj):
    """
    Recursively converts non-JSON-serializable objects (like numpy types)
    into standard Python types.
    """
    if isinstance(obj, (float, int, str, bool, type(None))):
        return obj
    
    # Check for numpy types. This is crucial for ML model outputs.
    if isinstance(obj, np.generic): # Covers various numpy scalar types
        return obj.item() # Convert numpy scalar to a native Python type

    if isinstance(obj, list):
        return [convert_to_serializable(elem) for elem in obj]
    
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    
    # Fallback for any other complex objects that might not be serializable
    return str(obj) 

class StaticAnalyzer:
    def __init__(self, parser_warnings):
        self.parser_warnings = parser_warnings
        self.static_vulnerabilities = []
        self._process_parser_warnings()

    def _process_parser_warnings(self):
        self.static_vulnerabilities.extend(self.parser_warnings)

    def get_vulnerabilities(self):
        return self.static_vulnerabilities

def analyze_code(code: str, ml_threshold: float = 0.5):
    print("DEBUG: analyze_code started.")
    report_messages = []
    parse_tree_image_path = None
    parse_tree_generated = False

    try:
        # Step 1: Lexical Analysis
        print("DEBUG: Starting lexical analysis.")
        tokens = tokenize_code(code)
        report_messages.append(f"Lexical analysis generated {len(tokens)} tokens.")
        print("DEBUG: Lexical analysis finished.")

        # Step 2: Syntactic Analysis (Parsing) and Parse Tree Generation
        print("DEBUG: Initializing parser.")
        parser = Parser(tokens)
        
        print("DEBUG: Starting parsing and parse tree construction.")
        parser_generated_warnings, parse_tree_root = parser.parse()
        print("DEBUG: Parsing and parse tree construction finished.")
        
        analysis_warnings_from_parser = list(parser_generated_warnings)
        
        static_analyzer = StaticAnalyzer(analysis_warnings_from_parser)
        static_issues = static_analyzer.get_vulnerabilities()

        if static_issues:
            report_messages.append("\nStatic Analysis Findings (Parser-based):")
            for issue in static_issues:
                report_messages.append(f"  - {issue}")
        else:
            report_messages.append("No direct static rule violations detected by parser-based rules.")

        # NEW: Generate Parse Tree Image
        if parse_tree_root:
            print("DEBUG: Parse tree root exists, attempting image generation.")
            image_dir = os.path.join('static', 'parse_trees')
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            image_filename = f"parse_tree_{uuid.uuid4()}"
            full_image_path = os.path.join(image_dir, image_filename)

            try:
                # The create_parse_tree_graph function will also have debug prints
                create_parse_tree_graph(parse_tree_root, full_image_path)
                
                # --- NEW FILE EXISTENCE AND SIZE CHECK ---
                if os.path.exists(full_image_path) and os.path.getsize(full_image_path) > 0:
                # ADD THE .png EXTENSION HERE
                    parse_tree_image_path = os.path.join('parse_trees', f"{image_filename}.png").replace('\\', '/')
                    parse_tree_generated = True
                    report_messages.append(f"Parse tree image generated: {parse_tree_image_path}")
                    print(f"DEBUG: Parse tree image successfully generated and verified at {full_image_path}")
                else:
                    parse_tree_image_path = None # Ensure it's None if file isn't valid
                    parse_tree_generated = False
                    report_messages.append(f"❌ Parse tree image file was not created or is empty at {full_image_path}.")
                    print(f"DEBUG: Parse tree image creation or verification FAILED: File not found or empty after render call: {full_image_path}")
                    # Don't re-raise here, let the other analysis steps continue, but mark as failed for frontend
                # --- END NEW CHECK ---

            except Exception as e:
                report_messages.append(f"❌ Parse tree visualization error: {e}. Ensure Graphviz is installed and in PATH.")
                parse_tree_generated = False
                parse_tree_image_path = None
                print(f"DEBUG: Parse tree image generation failed (caught exception): {e}")
                # Don't re-raise here, let the other analysis steps continue
        else:
            report_messages.append("⚠️ Parse tree could not be generated (possible parsing errors or empty code).")
            print("DEBUG: Parse tree root was None, skipping image generation.")


        # === ML-Based Prediction ===
        print("DEBUG: Starting ML prediction.")
        ml_prediction_raw = predict_vulnerability(code, ml_threshold)
        ml_vulnerable, ml_prob = convert_to_serializable(ml_prediction_raw[0]), convert_to_serializable(ml_prediction_raw[1])
        print("DEBUG: ML prediction finished.")

        report_messages.append(f"\nML Prediction (CodeBERT + XGBoost):")
        report_messages.append(f"  - Probability of Vulnerability: {ml_prob:.4f}")
        if ml_vulnerable:
            report_messages.append(f"  - ML Model Verdict: VULNERABLE (above threshold {ml_threshold})")
        else:
            report_messages.append(f"  - ML Model Verdict: SAFE (below threshold {ml_threshold})")


        # === Combine Verdicts ===
        overall_safe = not static_issues and not ml_vulnerable

        if not overall_safe:
            report_messages.append("\nOVERALL VERDICT: ❌ VULNERABILITY DETECTED!")
        else:
            report_messages.append("\nOVERALL VERDICT: ✅ Code appears SAFE.")

    except Exception as e:
        report_messages.append(f"Major analysis error: {str(e)}")
        print(f"DEBUG: Major analysis error caught in analyze_code: {e}")

    print("DEBUG: analyze_code finished.")
    return {
        "static_issues": convert_to_serializable(static_issues),
        "ml_vulnerable": convert_to_serializable(ml_vulnerable),
        "ml_probability": convert_to_serializable(ml_prob),
        "overall_safe": convert_to_serializable(overall_safe),
        "report_messages": convert_to_serializable(report_messages),
        "parse_tree_image": parse_tree_image_path,
        "parse_tree_generated": parse_tree_generated
    }
