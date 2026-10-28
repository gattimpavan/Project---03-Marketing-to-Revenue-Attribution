"""
Predictive AI Lead Quality & Revenue Scorer for Project - 03: Marketing-to-Revenue Attribution
Trains supervised ensemble classifiers and regressors to predict conversion probability,
lead tier, and expected 12-month customer lifetime value (LTV).
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score, roc_curve
from sklearn.model_selection import train_test_split

class LeadScorer:
    def __init__(self, df_journeys):
        self.df = df_journeys[df_journeys['is_lead'] == 1].copy()
        self.clf = None
        self.reg = None
        self.feature_columns = None
        self.metrics = {}
        self.roc_data = {}

    def prepare_features(self, df_input):
        """Encodes features for training and inference."""
        features = ['segment', 'device', 'first_touch_channel', 'touchpoints_count', 'unique_channels_count']
        encoded = pd.get_dummies(df_input[features], drop_first=False)
        return encoded

    def train_and_evaluate(self):
        """Trains conversion classifier and LTV regressor on lead dataset."""
        features = ['segment', 'device', 'first_touch_channel', 'touchpoints_count', 'unique_channels_count']
        X_all = pd.get_dummies(self.df[features], drop_first=False, dtype=float)
        self.feature_columns = list(X_all.columns)
        
        y_conv = self.df['is_converted']
        y_ltv = self.df['twelve_month_ltv']

        X_train, X_test, y_train, y_test = train_test_split(
            X_all, y_conv, test_size=0.25, random_state=42, stratify=y_conv
        )

        # 1. Classification Model for Conversion Probability
        self.clf = RandomForestClassifier(n_estimators=120, max_depth=7, random_state=42)
        self.clf.fit(X_train, y_train)

        y_pred_proba = self.clf.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        auc = roc_auc_score(y_test, y_pred_proba)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # ROC Curve points for charts
        fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
        # Sample ~30 points for JSON serialization
        idx_step = max(1, len(fpr) // 30)
        self.roc_data = {
            "fpr": [round(float(v), 4) for v in fpr[::idx_step]],
            "tpr": [round(float(v), 4) for v in tpr[::idx_step]]
        }

        # 2. Regression Model for LTV
        # Train on converted leads for positive value estimation
        conv_mask = self.df['is_converted'] == 1
        X_conv = X_all[conv_mask]
        y_conv_ltv = y_ltv[conv_mask]
        
        self.reg = RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42)
        self.reg.fit(X_conv, y_conv_ltv)

        # Feature importances
        imp = pd.Series(self.clf.feature_importances_, index=self.feature_columns).sort_values(ascending=False)
        top_imp = [{"feature": k, "weight": round(float(v) * 100, 2)} for k, v in imp.head(10).items()]

        self.metrics = {
            "roc_auc": round(float(auc), 4),
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "top_features": top_imp
        }

        # Score the whole leads dataset for tier assignment
        all_probas = self.clf.predict_proba(X_all)[:, 1]
        self.df['ai_conv_probability'] = np.round(all_probas, 3)
        
        # Predicted LTV: P(Conv) * Expected LTV
        raw_ltv_pred = self.reg.predict(X_all)
        self.df['ai_predicted_ltv'] = np.round(all_probas * raw_ltv_pred, 2)

        # Assign Lead Tier
        def assign_tier(p):
            if p >= 0.50:
                return "Tier 1: High-Yield Strategic MQL"
            elif p >= 0.25:
                return "Tier 2: Mid-Potential Nurture"
            else:
                return "Tier 3: Vanity / Ghost Lead"

        self.df['ai_lead_tier'] = self.df['ai_conv_probability'].apply(assign_tier)

        tier_summary = []
        for tier_name, group in self.df.groupby('ai_lead_tier'):
            tier_summary.append({
                "tier": tier_name,
                "count": len(group),
                "share": round(len(group) / len(self.df) * 100, 1),
                "actual_conversion_rate": round(float(group['is_converted'].mean()) * 100, 1),
                "avg_realized_revenue": round(float(group['realized_revenue'].mean()), 2),
                "avg_predicted_ltv": round(float(group['ai_predicted_ltv'].mean()), 2)
            })

        tier_summary.sort(key=lambda x: x['actual_conversion_rate'], reverse=True)
        self.metrics["tier_summary"] = tier_summary

        return self.metrics

    def predict_single_lead(self, lead_dict):
        """
        Interactive inference endpoint for dashboard what-if lead testing.
        """
        if self.clf is None or self.reg is None:
            self.train_and_evaluate()

        df_single = pd.DataFrame([lead_dict])
        X_encoded = pd.get_dummies(df_single, drop_first=False, dtype=float)
        
        # Align columns with training set
        X_aligned = pd.DataFrame(0.0, index=[0], columns=self.feature_columns, dtype=float)
        for col in X_encoded.columns:
            if col in X_aligned.columns:
                X_aligned.loc[0, col] = float(X_encoded.loc[0, col])

        p_conv = float(self.clf.predict_proba(X_aligned)[0, 1])
        base_ltv = float(self.reg.predict(X_aligned)[0])
        expected_ltv = round(p_conv * base_ltv, 2)

        if p_conv >= 0.50:
            tier = "Tier 1: High-Yield Strategic MQL"
            tier_class = "success"
            action = "Fast-track to Enterprise Account Executive for priority consultative onboarding."
        elif p_conv >= 0.25:
            tier = "Tier 2: Mid-Potential Nurture"
            tier_class = "warning"
            action = "Enroll in automated product walkthrough sequence; trigger mid-funnel demo invite."
        else:
            tier = "Tier 3: Vanity / Ghost Lead"
            tier_class = "danger"
            action = "Deprioritize human sales resources; deploy self-serve onboarding gate to filter bot/promo traffic."

        return {
            "conversion_probability": round(p_conv * 100, 1),
            "expected_12m_ltv": expected_ltv,
            "lead_tier": tier,
            "tier_class": tier_class,
            "recommended_action": action,
            "lead_quality_score": round(p_conv * 100, 1)
        }

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(base_dir, "data", "customer_journeys.csv"))
    scorer = LeadScorer(df)
    metrics = scorer.train_and_evaluate()
    print("AI Lead Scorer Performance:")
    print(f"ROC-AUC: {metrics['roc_auc']} | Accuracy: {metrics['accuracy']*100:.1f}% | Precision: {metrics['precision']} | Recall: {metrics['recall']}")
    print("\nLead Tier Summary:")
    for t in metrics['tier_summary']:
        print(f"  • {t['tier']:<32} | Count: {t['count']:>6,} ({t['share']:>4.1f}%) | Real Conversion: {t['actual_conversion_rate']:>5.1f}% | Avg LTV: ${t['avg_predicted_ltv']:>7,.2f}")
    
    test_lead = {
        'segment': 'Enterprise B2B',
        'device': 'Desktop',
        'first_touch_channel': 'Paid Search (High Intent)',
        'touchpoints_count': 3,
        'unique_channels_count': 2
    }
    pred = scorer.predict_single_lead(test_lead)
    print(f"\nTest Inference: {test_lead['segment']} via {test_lead['first_touch_channel']} -> P(Conv): {pred['conversion_probability']}% | Tier: {pred['lead_tier']}")
