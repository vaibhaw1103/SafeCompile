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
ml_model = joblib.load("vuln_xgb_model.pkl")  # change to your model file

# === Inference Function ===
def predict_vulnerability(code: str, threshold: float = 0.5):
    """
    Predict whether a given code snippet is vulnerable using CodeBERT + ML.
    Returns: (is_vulnerable: bool, probability: float)
    """
    # Tokenize and send to device
    inputs = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=256)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = codebert(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        vector = cls_embedding.cpu().numpy()

    # ML prediction
    prob = ml_model.predict_proba(vector)[0][1]  # Probability of vulnerable class
    is_vuln = prob >= threshold

    return is_vuln, prob
