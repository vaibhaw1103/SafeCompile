import torch
import joblib
import numpy as np
from transformers import RobertaTokenizer, RobertaModel

# === Load CodeBERT ===
codebert_model_name = "microsoft/codebert-base"
tokenizer = RobertaTokenizer.from_pretrained(codebert_model_name)
codebert = RobertaModel.from_pretrained(codebert_model_name)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
codebert = codebert.to(device)
codebert.eval()

# === Load Trained ML Model (XGBoost or other sklearn model) ===
# This file assumes 'vuln_xgb_model.pkl' exists in the same directory.
# If you don't have this, the ML prediction will use a dummy/mock output.
try:
    ml_model = joblib.load("vuln_xgb_model.pkl")  
except FileNotFoundError:
    print("WARNING: 'vuln_xgb_model.pkl' not found. ML prediction will use a dummy/mock output.")
    # Create a dummy model for demonstration if the actual model isn't available
    class DummyXGBoostModel:
        def predict_proba(self, X):
            # Simulate a probability based on a simple heuristic or random chance
            # For demonstration, let's say if the input vector sum is high, higher prob
            prob = np.random.rand(X.shape[0], 2) # Random 2-class probability
            prob = prob / prob.sum(axis=1, keepdims=True) # Normalize to sum to 1
            # Artificially make one class more likely
            prob[:, 1] = np.clip(prob[:, 1] * 1.5, 0.1, 0.9) 
            prob[:, 0] = 1 - prob[:, 1]
            return prob

    ml_model = DummyXGBoostModel()
except Exception as e:
    print(f"ERROR: Failed to load ML model 'vuln_xgb_model.pkl': {e}. ML prediction will use a dummy/mock output.")
    class FallbackXGBoostModel: # Another dummy if joblib fails
        def predict_proba(self, X):
            prob = np.random.rand(X.shape[0], 2) 
            prob = prob / prob.sum(axis=1, keepdims=True)
            return prob
    ml_model = FallbackXGBoostModel()


# === Inference Function ===
def predict_vulnerability(code: str, threshold: float = 0.5):
    """
    Predict whether a given code snippet is vulnerable using CodeBERT + ML.
    Returns: (is_vulnerable: bool, probability: float)
    """
    if ml_model is None:
        print("ERROR: ML model is not loaded. Cannot perform prediction.")
        return False, 0.0 # Default to safe if model not loaded

    # Tokenize and send to device
    inputs = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=256)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = codebert(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        vector = cls_embedding.cpu().numpy()

    # ML prediction
    # ml_model.predict_proba returns probabilities for [class_0, class_1]
    prob = ml_model.predict_proba(vector)[0][1]  # Probability of vulnerable class (assuming class 1 is vulnerable)
    is_vuln = prob >= threshold

    return is_vuln, prob

