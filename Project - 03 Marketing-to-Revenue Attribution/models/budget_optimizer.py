"""
Algorithmic Budget Optimization & What-If Simulator for Project - 03: Marketing-to-Revenue Attribution
Simulates reallocating marketing spend across channels based on Markov Chain data-driven efficiencies.
Projects incremental revenue lift, ROAS gains, and vanity lead reduction.
"""
import os
import json
import numpy as np
import pandas as pd

class BudgetOptimizer:
    def __init__(self, df_journeys, channel_spend, markov_weights):
        self.df = df_journeys.copy()
        self.channel_spend = channel_spend.copy()
        self.markov_weights = markov_weights.copy()
        self.total_baseline_spend = sum(channel_spend.values())
        self.total_baseline_revenue = float(self.df['realized_revenue'].sum())
        
        # Calculate empirical baseline channel ROAS
        self.baseline_channel_rev = {}
        for ch, spend in channel_spend.items():
            # Attributed revenue via Markov weights
            self.baseline_channel_rev[ch] = self.markov_weights.get(ch, 0.125) * self.total_baseline_revenue

    def simulate_reallocation(self, new_spend_dict):
        """
        Simulates the financial impact of adjusting channel spends.
        new_spend_dict: {channel_name: new_spend_usd}
        Applies diminishing marginal returns (power elasticity: alpha = 0.72) to model realistic saturation.
        """
        simulated_channel_results = []
        total_new_spend = sum(new_spend_dict.values())
        total_simulated_revenue = 0.0

        for ch, old_spend in self.channel_spend.items():
            new_spend = float(new_spend_dict.get(ch, old_spend))
            old_rev = self.baseline_channel_rev[ch]

            # Diminishing marginal returns formula: Rev_new = Rev_old * (Spend_new / Spend_old)^alpha
            alpha = 0.72 if ch in ["Paid Search (High Intent)", "LinkedIn B2B / Enterprise"] else 0.55 # Vanity channels saturate faster
            if old_spend > 0:
                spend_ratio = max(0.05, new_spend / old_spend)
                new_rev = old_rev * (spend_ratio ** alpha)
            else:
                new_rev = 0.0

            total_simulated_revenue += new_rev
            sim_roas = (new_rev / new_spend) if new_spend > 0 else 0.0
            old_roas = (old_rev / old_spend) if old_spend > 0 else 0.0

            simulated_channel_results.append({
                "channel": ch,
                "current_spend": round(old_spend, 2),
                "simulated_spend": round(new_spend, 2),
                "spend_delta": round(new_spend - old_spend, 2),
                "spend_delta_pct": round(((new_spend - old_spend) / old_spend * 100), 1) if old_spend > 0 else 0,
                "current_revenue": round(old_rev, 2),
                "simulated_revenue": round(new_rev, 2),
                "revenue_delta": round(new_rev - old_rev, 2),
                "current_roas": round(old_roas, 2),
                "simulated_roas": round(sim_roas, 2)
            })

        net_rev_lift = total_simulated_revenue - self.total_baseline_revenue
        baseline_roas = self.total_baseline_revenue / self.total_baseline_spend if self.total_baseline_spend > 0 else 0
        new_roas = total_simulated_revenue / total_new_spend if total_new_spend > 0 else 0

        return {
            "baseline_spend": round(self.total_baseline_spend, 2),
            "simulated_spend": round(total_new_spend, 2),
            "spend_difference": round(total_new_spend - self.total_baseline_spend, 2),
            "baseline_revenue": round(self.total_baseline_revenue, 2),
            "simulated_revenue": round(total_simulated_revenue, 2),
            "net_revenue_lift": round(net_rev_lift, 2),
            "revenue_lift_pct": round((net_rev_lift / self.total_baseline_revenue) * 100, 2),
            "baseline_roas": round(baseline_roas, 2),
            "simulated_roas": round(new_roas, 2),
            "roas_improvement": round(new_roas - baseline_roas, 2),
            "channel_details": simulated_channel_results
        }

    def get_preconfigured_scenarios(self):
        """Returns 4 executive strategic budget scenarios."""
        # 1. Baseline
        scenarios = {
            "baseline": {
                "name": "Status Quo (High Vanity Leads, Revenue Drag)",
                "description": "Current marketing spend allocation with heavy investment in broad social and affiliate channels.",
                "spends": self.channel_spend
            },
            "attribution_optimized": {
                "name": "AI Attribution-Guided Realignment (Recommended)",
                "description": "Cuts 35% from Social and 40% from Affiliate; reinvests into High-Intent Search, LinkedIn B2B, and Email Nurture.",
                "spends": {
                    "Paid Search (High Intent)": self.channel_spend["Paid Search (High Intent)"] * 1.30,
                    "Social Ads (Meta/Instagram)": self.channel_spend["Social Ads (Meta/Instagram)"] * 0.65,
                    "Amazon DSP / Display": self.channel_spend["Amazon DSP / Display"] * 0.90,
                    "Prime Video / Streaming Ads": self.channel_spend["Prime Video / Streaming Ads"] * 1.05,
                    "LinkedIn B2B / Enterprise": self.channel_spend["LinkedIn B2B / Enterprise"] * 1.45,
                    "Affiliate & Partners": self.channel_spend["Affiliate & Partners"] * 0.60,
                    "Email & Nurture": self.channel_spend["Email & Nurture"] * 1.60,
                    "Organic Search / Direct": self.channel_spend["Organic Search / Direct"] * 1.25
                }
            },
            "enterprise_growth": {
                "name": "Aggressive B2B & Enterprise Maximizer",
                "description": "Double down on high-LTV B2B channels, reducing consumer top-of-funnel promo spend by 50%.",
                "spends": {
                    "Paid Search (High Intent)": self.channel_spend["Paid Search (High Intent)"] * 1.40,
                    "Social Ads (Meta/Instagram)": self.channel_spend["Social Ads (Meta/Instagram)"] * 0.50,
                    "Amazon DSP / Display": self.channel_spend["Amazon DSP / Display"] * 0.80,
                    "Prime Video / Streaming Ads": self.channel_spend["Prime Video / Streaming Ads"] * 0.85,
                    "LinkedIn B2B / Enterprise": self.channel_spend["LinkedIn B2B / Enterprise"] * 1.80,
                    "Affiliate & Partners": self.channel_spend["Affiliate & Partners"] * 0.50,
                    "Email & Nurture": self.channel_spend["Email & Nurture"] * 1.80,
                    "Organic Search / Direct": self.channel_spend["Organic Search / Direct"] * 1.30
                }
            },
            "margin_preservation": {
                "name": "Cost Rationalization & Profit Preservation",
                "description": "Cuts total marketing expenditure by 18% by eliminating vanity leads while holding revenue constant.",
                "spends": {
                    "Paid Search (High Intent)": self.channel_spend["Paid Search (High Intent)"] * 1.05,
                    "Social Ads (Meta/Instagram)": self.channel_spend["Social Ads (Meta/Instagram)"] * 0.45,
                    "Amazon DSP / Display": self.channel_spend["Amazon DSP / Display"] * 0.75,
                    "Prime Video / Streaming Ads": self.channel_spend["Prime Video / Streaming Ads"] * 0.70,
                    "LinkedIn B2B / Enterprise": self.channel_spend["LinkedIn B2B / Enterprise"] * 1.20,
                    "Affiliate & Partners": self.channel_spend["Affiliate & Partners"] * 0.45,
                    "Email & Nurture": self.channel_spend["Email & Nurture"] * 1.30,
                    "Organic Search / Direct": self.channel_spend["Organic Search / Direct"] * 1.10
                }
            }
        }

        results = {}
        for key, sc in scenarios.items():
            sim = self.simulate_reallocation(sc["spends"])
            results[key] = {
                "name": sc["name"],
                "description": sc["description"],
                "metrics": sim
            }
        return results

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(base_dir, "data", "customer_journeys.csv"))
    with open(os.path.join(base_dir, "data", "channel_spend.json")) as f:
        spend = json.load(f)
    
    from attribution_engine import AttributionEngine
    attr_engine = AttributionEngine(df, spend)
    mkv = attr_engine.compute_markov_chain_attribution()

    optimizer = BudgetOptimizer(df, spend, mkv['markov_weights'])
    scenarios = optimizer.get_preconfigured_scenarios()
    rec = scenarios['attribution_optimized']['metrics']
    print("Optimization Simulation:")
    print(f"Baseline Spend: ${rec['baseline_spend']:,.2f} -> Simulated Spend: ${rec['simulated_spend']:,.2f}")
    print(f"Baseline Revenue: ${rec['baseline_revenue']:,.2f} -> Simulated Revenue: ${rec['simulated_revenue']:,.2f}")
    print(f"Net Revenue Lift: ${rec['net_revenue_lift']:+,.2f} ({rec['revenue_lift_pct']:+.2f}%)")
    print(f"ROAS Change: {rec['baseline_roas']}x -> {rec['simulated_roas']}x ({rec['roas_improvement']:+.2f}x)")
