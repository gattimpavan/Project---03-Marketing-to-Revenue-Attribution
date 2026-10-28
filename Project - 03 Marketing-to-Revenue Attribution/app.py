"""
Flask Application for Project - 03: Marketing-to-Revenue Attribution
Hosts the interactive Amazon executive dashboard, simulation REST APIs, AI lead scorer, and PDF download endpoint.
"""
import os
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_file

from models.data_generator import generate_marketing_attribution_data
from models.attribution_engine import AttributionEngine
from models.funnel_analyzer import FunnelAnalyzer
from models.leakage_detector import LeakageDetector
from models.lead_scorer import LeadScorer
from models.budget_optimizer import BudgetOptimizer
from report.generate_pdf_report import generate_pdf

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "customer_journeys.csv")
SPEND_PATH = os.path.join(DATA_DIR, "channel_spend.json")
REPORT_PATH = os.path.join(BASE_DIR, "report", "Amazon_Marketing_Revenue_Attribution_Report.pdf")

# Global Cache to ensure fast dashboard responsiveness
CACHE = {
    'df': None,
    'spend': None,
    'attr_engine': None,
    'funnel_engine': None,
    'leakage_detector': None,
    'lead_scorer': None,
    'budget_optimizer': None,
    'summary': None
}

def sanitize(val):
    """Converts numpy / pandas data types into JSON-serializable primitives."""
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    elif hasattr(val, "item"):
        return val.item()
    elif isinstance(val, dict):
        return {k: sanitize(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [sanitize(v) for v in val]
    return str(val)

def initialize_system():
    """Initializes datasets, trains AI models, and caches analytical summaries."""
    if not os.path.exists(CSV_PATH) or not os.path.exists(SPEND_PATH):
        df, spend = generate_marketing_attribution_data(DATA_DIR, n_journeys=25000)
    else:
        df = pd.read_csv(CSV_PATH)
        with open(SPEND_PATH) as f:
            spend = json.load(f)

    CACHE['df'] = df
    CACHE['spend'] = spend

    # 1. Attribution Engine
    attr_engine = AttributionEngine(df, spend)
    attr_comp = attr_engine.get_full_attribution_comparison()
    CACHE['attr_engine'] = attr_engine

    # 2. Funnel Analyzer
    funnel_engine = FunnelAnalyzer(df, spend)
    funnel_global = funnel_engine.get_global_funnel_metrics()
    channel_funnel = funnel_engine.get_channel_funnel_breakdown()
    segment_funnel = funnel_engine.get_segment_funnel_breakdown()
    CACHE['funnel_engine'] = funnel_engine

    # 3. Leakage Detector
    leakage_detector = LeakageDetector(df, spend)
    leakage_diag = leakage_detector.get_executive_diagnosis()
    CACHE['leakage_detector'] = leakage_detector

    # 4. Lead Scorer
    lead_scorer = LeadScorer(df)
    scorer_metrics = lead_scorer.train_and_evaluate()
    CACHE['lead_scorer'] = lead_scorer

    # 5. Budget Optimizer
    mkv_weights = attr_engine.compute_markov_chain_attribution()['markov_weights']
    budget_optimizer = BudgetOptimizer(df, spend, mkv_weights)
    scenarios = budget_optimizer.get_preconfigured_scenarios()
    CACHE['budget_optimizer'] = budget_optimizer

    # Assemble summary payload
    CACHE['summary'] = {
        'attribution': attr_comp,
        'funnel': funnel_global,
        'channel_funnel': channel_funnel,
        'segment_funnel': segment_funnel,
        'leakage': leakage_diag,
        'lead_scorer': {
            'metrics': scorer_metrics,
            'tier_summary': scorer_metrics['tier_summary']
        },
        'scenarios': scenarios,
        'channel_spend': spend
    }

    # Ensure PDF exists
    if not os.path.exists(REPORT_PATH):
        generate_pdf(REPORT_PATH)

# Initialize on startup
initialize_system()

@app.route("/")
def index():
    """Serves the main interactive executive dashboard."""
    return render_template("index.html")

@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Returns cached multi-touch attribution and funnel intelligence summary."""
    return jsonify(sanitize(CACHE['summary']))

@app.route("/api/score-lead", methods=["POST"])
def score_single_lead():
    """Interactive inference endpoint for lead testing."""
    data = request.get_json() or {}
    lead_dict = {
        'segment': data.get('segment', 'Enterprise B2B'),
        'device': data.get('device', 'Desktop'),
        'first_touch_channel': data.get('first_touch_channel', 'Paid Search (High Intent)'),
        'touchpoints_count': int(data.get('touchpoints_count', 3)),
        'unique_channels_count': int(data.get('unique_channels_count', 2))
    }
    result = CACHE['lead_scorer'].predict_single_lead(lead_dict)
    return jsonify(sanitize(result))

@app.route("/api/simulate-budget", methods=["POST"])
def simulate_budget():
    """Interactive what-if budget reallocation simulation endpoint."""
    new_spend_dict = request.get_json() or CACHE['spend']
    sim_result = CACHE['budget_optimizer'].simulate_reallocation(new_spend_dict)
    return jsonify(sanitize(sim_result))

@app.route("/api/download-pdf", methods=["GET"])
def download_pdf():
    """Delivers the executive PDF report."""
    if not os.path.exists(REPORT_PATH):
        generate_pdf(REPORT_PATH)
    return send_file(
        REPORT_PATH,
        as_attachment=True,
        download_name="Amazon_Marketing_Revenue_Attribution_Report.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="127.0.0.1", port=port, debug=False)
