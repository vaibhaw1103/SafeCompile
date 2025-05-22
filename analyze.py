from lexer import tokenize_code
from parser_custom import Parser
from ml_predict import predict_vulnerability

def analyze_code(code: str, threshold: float = 0.5):
    """
    Runs static + ML analysis on the code.
    Returns:
        {
            "static_issues": [...],
            "ml_vulnerable": bool,
            "ml_probability": float,
            "overall_safe": bool
        }
    """
    # === Lexical Analysis ===
    tokens = tokenize_code(code)

    # === Static Rule-Based Parsing ===
    parser = Parser(tokens)
    static_warnings = parser.parse()  # warnings list

    # === ML-Based Prediction ===
    ml_vulnerable, ml_prob = predict_vulnerability(code, threshold)

    # === Combine Verdicts ===
    overall_safe = not static_warnings and not ml_vulnerable

    return {
        "static_issues": static_warnings,
        "ml_vulnerable": ml_vulnerable,
        "ml_probability": ml_prob,
        "overall_safe": overall_safe
    }
