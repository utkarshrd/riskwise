import json
from pathlib import Path
from typing import Any

import joblib
from backend.app.core.config import settings
from rapidfuzz import fuzz

EXEMPLARS: dict[str, list[str]] = {
    "CALCULATE_EMI": [
        "calculate loan emi", "what is my monthly emi", "monthly payment on loan",
        "car loan emi", "home loan emi", "loan installment calculation",
        "emi for principal at interest rate for tenure"
    ],
    "PERSONAL_STRESS_TEST": [
        "stress test my personal finances", "what is my emergency runway",
        "debt to income ratio calculation", "personal cash flow stress",
        "am i overleveraged with expenses and emi", "how many months of runway do i have"
    ],
    "ANALYZE_PORTFOLIO_RISK": [
        "analyze portfolio risk", "what is annualized volatility",
        "calculate portfolio var and cvar", "drawdown and correlation for holdings",
        "risk analysis for portfolio"
    ],
    "VALIDATE_VAR_MODEL": [
        "run rolling out of sample var validation", "validate var model with kupiec test",
        "christoffersen independence test", "backtest value at risk model",
        "check basel traffic light zone exceptions"
    ],
    "CREDIT_RISK_EXPLAIN": [
        "why was my credit score rejected", "explain borrower default risk with shap",
        "top features driving credit risk", "credit score explanation and risk band"
    ],
    "FINANCIAL_EDUCATION_RAG": [
        "what is basel iii framework", "rbi prudential guidelines for retail loans",
        "sebi retail risk disclosure rules", "difference between var and cvar expected shortfall",
        "what is population stability index psi drift"
    ]
}


class ScoredIntentClassifier:
    def __init__(self, artifacts_dir: Path | None = None):
        self.artifacts_dir = artifacts_dir or (settings.ARTIFACTS_DIR / "intent_classifier")
        self.vectorizer_file = self.artifacts_dir / "vectorizer.joblib"
        self.model_file = self.artifacts_dir / "model.joblib"
        self.meta_file = self.artifacts_dir / "metadata.json"

        self.vectorizer = None
        self.model = None
        self.threshold = 0.35
        self.classes: list[str] = []
        self._load()

    def _load(self):
        if self.vectorizer_file.exists() and self.model_file.exists():
            self.vectorizer = joblib.load(self.vectorizer_file)
            self.model = joblib.load(self.model_file)
            self.classes = list(self.model.classes_)
            if self.meta_file.exists():
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.threshold = meta.get("confidence_threshold", 0.35)

    def classify(self, text: str) -> dict[str, Any]:
        """
        Classifies user query into an intent with confidence and top-2 intents.
        Uses logistic regression probabilities blended with rapidfuzz token similarity.
        """
        if not self.model or not self.vectorizer:
            return {
                "top_intent": "GENERAL_CONVERSATION",
                "confidence": 0.50,
                "top_2_intents": [{"intent": "GENERAL_CONVERSATION", "confidence": 0.50}],
                "needs_clarification": False
            }

        # 1. Model probabilities
        vec = self.vectorizer.transform([text])
        probs = self.model.predict_proba(vec)[0]
        prob_dict = {cls_name: float(probs[i]) for i, cls_name in enumerate(self.classes)}

        # 2. Fuzzy exemplar matching
        clean_text = text.lower()
        fuzzy_scores: dict[str, float] = {}
        for intent, exemplars in EXEMPLARS.items():
            max_sim = 0.0
            for ex in exemplars:
                sim = fuzz.token_set_ratio(clean_text, ex)
                max_sim = max(max_sim, sim)
            fuzzy_scores[intent] = max_sim / 100.0  # normalize 0 to 1

        # 3. Blend scores (0.65 model + 0.35 fuzzy match)
        blended: dict[str, float] = {}
        for cls_name in self.classes:
            m_score = prob_dict.get(cls_name, 0.0)
            f_score = fuzzy_scores.get(cls_name, 0.0)
            blended[cls_name] = 0.65 * m_score + 0.35 * f_score

        # Normalize blended distribution
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}

        sorted_intents = sorted(blended.items(), key=lambda x: x[1], reverse=True)
        top_intent, top_conf = sorted_intents[0]
        top_2 = [
            {"intent": sorted_intents[0][0], "confidence": round(sorted_intents[0][1], 4)},
            {"intent": sorted_intents[1][0], "confidence": round(sorted_intents[1][1], 4)}
        ]

        needs_clarification = (top_conf < self.threshold) and (top_intent not in ["GENERAL_CONVERSATION"])

        return {
            "top_intent": top_intent,
            "confidence": round(top_conf, 4),
            "top_2_intents": top_2,
            "needs_clarification": needs_clarification
        }
