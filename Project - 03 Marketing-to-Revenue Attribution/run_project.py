"""
Master Orchestrator for Project - 03: Marketing-to-Revenue Attribution
Executes customer journey telemetry data generation, multi-touch Markov AI attribution,
funnel leakage diagnostics, predictive lead scoring, compiles the publication-grade PDF report,
and launches the interactive executive web dashboard.
"""
import os
import sys
import argparse

import os
import sys
import argparse

# Force UTF-8 stdout if supported
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from models.data_generator import generate_marketing_attribution_data
from models.attribution_engine import AttributionEngine
from models.funnel_analyzer import FunnelAnalyzer
from models.leakage_detector import LeakageDetector
from models.lead_scorer import LeadScorer
from models.budget_optimizer import BudgetOptimizer
from report.generate_pdf_report import generate_pdf
import pandas as pd
import json

def main():
    parser = argparse.ArgumentParser(description="Master runner for Project - 03: Marketing-to-Revenue Attribution")
    parser.add_argument("--no-server", action="store_true", help="Generate models, analytics, and PDF without launching web server.")
    parser.add_argument("--port", type=int, default=5002, help="Port to run Flask web dashboard on (default: 5002).")
    args = parser.parse_args()

    print("=" * 88)
    print(" PROJECT - 03: MARKETING-TO-REVENUE ATTRIBUTION")
    print(" Amazon Multi-Touch Customer Journey & Funnel Leakage Intelligence System")
    print("=" * 88)

    data_dir = os.path.join(base_dir, "data")
    csv_path = os.path.join(data_dir, "customer_journeys.csv")
    spend_path = os.path.join(data_dir, "channel_spend.json")
    report_path = os.path.join(base_dir, "report", "Amazon_Marketing_Revenue_Attribution_Report.pdf")

    # Step 1: Data Verification / Generation
    print("\n[Step 1/5] Checking and loading multi-channel customer journey telemetry...")
    if not os.path.exists(csv_path) or not os.path.exists(spend_path):
        df, spend = generate_marketing_attribution_data(data_dir, n_journeys=25000)
    else:
        df = pd.read_csv(csv_path)
        with open(spend_path) as f:
            spend = json.load(f)
    print(f"  [+] Ingested {len(df):,} customer journeys across 8 marketing channels.")
    print(f"  [+] Recorded Total Leads: {df['is_lead'].sum():,} | Realized Revenue: ${df['realized_revenue'].sum():,.2f}")

    # Step 2: Multi-Touch Attribution Engine
    print("\n[Step 2/5] Computing Multi-Touch Attribution (LTA, FTA, Linear vs Markov Chain AI)...")
    attr_engine = AttributionEngine(df, spend)
    attr_comp = attr_engine.get_full_attribution_comparison()
    print(f"  [+] Overall Marketing Spend: ${attr_comp['total_spend']:,.2f} | Blended ROAS: {attr_comp['overall_roas']}x")
    for c in attr_comp['channel_comparison']:
        print(f"    * {c['channel']:<28} | Spend: ${c['spend']:>9,.0f} | Markov ROAS: {c['markov_chain']['roas']:>4.2f}x | LTA Bias: {c['distortion_pct']:>+5.1f}%")

    # Step 3: Funnel Leakage & AI Root Cause Diagnostics
    print("\n[Step 3/5] Conducting Funnel Audit & Training Predictive Lead Scorer...")
    funnel_engine = FunnelAnalyzer(df, spend)
    funnel_metrics = funnel_engine.get_global_funnel_metrics()
    print(f"  [+] Funnel Leakage Audit: Identified ${funnel_metrics['total_dollar_leakage']:,.2f} in unrealized pipeline equity.")
    print(f"    * Stage 4 Product Activation Chasm: {funnel_metrics['stages'][3]['drop_off_rate']}% drop-off (${funnel_metrics['stages'][3]['estimated_dollar_loss']:,.2f} lost)")

    leakage_detector = LeakageDetector(df, spend)
    diag = leakage_detector.get_executive_diagnosis()
    top_culprit = diag['culprits']['primary_leakage_source']
    top_engine = diag['culprits']['primary_growth_engine']
    print(f"  [+] Vanity Lead Trap Identified: {top_culprit['channel']} (Discrepancy: {top_culprit['discrepancy_index']:+.1f}%)")
    print(f"  [+] High-Yield Growth Engine:   {top_engine['channel']} (Discrepancy: {top_engine['discrepancy_index']:+.1f}%)")

    lead_scorer = LeadScorer(df)
    scorer_metrics = lead_scorer.train_and_evaluate()
    print(f"  [+] Predictive Lead Scorer Model Converged | ROC-AUC: {scorer_metrics['roc_auc']} | Accuracy: {scorer_metrics['accuracy']*100:.1f}%")
    for t in scorer_metrics['tier_summary']:
        print(f"    * {t['tier']:<32} | Leads: {t['count']:>5,} ({t['share']:>4.1f}%) | Real Win Rate: {t['actual_conversion_rate']:>4.1f}% | Avg LTV: ${t['avg_predicted_ltv']:>6,.2f}")

    # Step 4: Executive PDF Report Compilation
    print("\n[Step 4/5] Generating Publication-Grade Executive PDF Report...")
    pdf_file = generate_pdf(report_path)
    file_size_kb = round(os.path.getsize(pdf_file) / 1024, 1)
    print(f"  [+] Executive Intelligence PDF generated successfully: {pdf_file} ({file_size_kb} KB)")

    # Step 5: Web Dashboard Launch
    if args.no_server:
        print("\n[Step 5/5] Skipping server launch (--no-server flag passed). Execution complete.")
        return

    print("\n[Step 5/5] Starting Flask Interactive Executive Web Server...")
    print(f"  [+] Dashboard URL:        http://127.0.0.1:{args.port}")
    print(f"  [+] Direct PDF Download:  http://127.0.0.1:{args.port}/api/download-pdf")
    print(f"  [+] Interactive Scorer:   http://127.0.0.1:{args.port}#lead-scorer-tab")
    print(f"  [+] What-If Simulator:    http://127.0.0.1:{args.port}#simulator-tab")
    print(f"\nLaunching Flask development server on port {args.port} (Press Ctrl+C to stop)...")

    from app import app
    app.run(host="127.0.0.1", port=args.port, debug=False)

if __name__ == "__main__":
    main()
