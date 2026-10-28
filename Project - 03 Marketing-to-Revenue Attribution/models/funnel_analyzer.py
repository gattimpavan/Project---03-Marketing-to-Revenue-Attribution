"""
Funnel Analytics Engine for Project - 03: Marketing-to-Revenue Attribution
Traces end-to-end customer progression from Campaign Exposure through Clicks,
Lead Ingestion, Activation, Paid Conversion, and LTV Realization.
Quantifies stage drop-offs and lost dollar pipeline value.
"""
import os
import json
import numpy as np
import pandas as pd

class FunnelAnalyzer:
    def __init__(self, df_journeys, channel_spend):
        self.df = df_journeys.copy()
        self.channel_spend = channel_spend
        self.total_journeys = len(self.df)
        self.total_spend = sum(channel_spend.values())

    def get_global_funnel_metrics(self):
        """Computes aggregate funnel progression, conversion rates, and dollar leakage."""
        n_exposure = len(self.df)
        n_clicks = int(self.df['click'].sum())
        n_leads = int(self.df['is_lead'].sum())
        n_activated = int(self.df['is_activated'].sum())
        n_converted = int(self.df['is_converted'].sum())
        
        total_revenue = float(self.df['realized_revenue'].sum())
        total_ltv = float(self.df['twelve_month_ltv'].sum())
        avg_revenue_per_converted = total_revenue / n_converted if n_converted > 0 else 0
        avg_ltv_per_converted = total_ltv / n_converted if n_converted > 0 else 0

        # Estimated potential pipeline value at each stage if benchmark conversion held:
        # Benchmark activation = 65%, Benchmark converted from activated = 55%
        # Leakage 1: Leads that failed to activate
        lost_activations = (n_leads * 0.65) - n_activated
        dollar_leakage_activation = max(0.0, lost_activations * 0.55 * avg_revenue_per_converted)

        # Leakage 2: Activated users who abandoned before paid conversion
        lost_conversions = (n_activated * 0.55) - n_converted
        dollar_leakage_conversion = max(0.0, lost_conversions * avg_revenue_per_converted)

        stages = [
            {
                "stage_id": 1,
                "stage_name": "Campaign Exposure",
                "count": n_exposure,
                "conversion_from_prev": 100.0,
                "cumulative_conversion": 100.0,
                "drop_off_count": 0,
                "drop_off_rate": 0.0,
                "estimated_dollar_loss": 0.0,
                "description": "Multi-channel ad impressions delivered across Amazon DSP, Search, Video, Social & Partners"
            },
            {
                "stage_id": 2,
                "stage_name": "Engagement / Clicks",
                "count": n_clicks,
                "conversion_from_prev": 100.0,
                "cumulative_conversion": 100.0,
                "drop_off_count": 0,
                "drop_off_rate": 0.0,
                "estimated_dollar_loss": 0.0,
                "description": "Prospect clicks through to Amazon landing pages, product hubs, or store portals"
            },
            {
                "stage_id": 3,
                "stage_name": "Lead Ingestion (MQL)",
                "count": n_leads,
                "conversion_from_prev": round((n_leads / n_clicks) * 100, 2),
                "cumulative_conversion": round((n_leads / n_exposure) * 100, 2),
                "drop_off_count": n_clicks - n_leads,
                "drop_off_rate": round(((n_clicks - n_leads) / n_clicks) * 100, 2),
                "estimated_dollar_loss": round((n_clicks - n_leads) * 0.35 * 0.55 * avg_revenue_per_converted * 0.25, 2),
                "description": "Account registration, free trial signup, whitepaper download, or merchant lead inquiry"
            },
            {
                "stage_id": 4,
                "stage_name": "Product Activation",
                "count": n_activated,
                "conversion_from_prev": round((n_activated / n_leads) * 100, 2),
                "cumulative_conversion": round((n_activated / n_exposure) * 100, 2),
                "drop_off_count": n_leads - n_activated,
                "drop_off_rate": round(((n_leads - n_activated) / n_leads) * 100, 2),
                "estimated_dollar_loss": round(dollar_leakage_activation, 2),
                "description": "Crucial activation milestone: API key creation, catalog sync, first ad campaign test, or workspace setup"
            },
            {
                "stage_id": 5,
                "stage_name": "Paid Conversion (Customer Won)",
                "count": n_converted,
                "conversion_from_prev": round((n_converted / n_activated) * 100, 2),
                "cumulative_conversion": round((n_converted / n_exposure) * 100, 2),
                "drop_off_count": n_activated - n_converted,
                "drop_off_rate": round(((n_activated - n_converted) / n_activated) * 100, 2),
                "estimated_dollar_loss": round(dollar_leakage_conversion, 2),
                "description": "First paid invoice, active subscription billing, or verified transaction commission"
            },
            {
                "stage_id": 6,
                "stage_name": "12-Month LTV Realization",
                "count": n_converted,
                "conversion_from_prev": 100.0,
                "cumulative_conversion": round((n_converted / n_exposure) * 100, 2),
                "drop_off_count": 0,
                "drop_off_rate": 0.0,
                "estimated_dollar_loss": 0.0,
                "description": "Retained revenue, contract expansion, and recurring SaaS/merchant gross merchandise volume"
            }
        ]

        total_dollar_leakage = round(dollar_leakage_activation + dollar_leakage_conversion, 2)

        return {
            "total_journeys": n_exposure,
            "total_leads": n_leads,
            "total_activated": n_activated,
            "total_converted": n_converted,
            "total_revenue": round(total_revenue, 2),
            "total_ltv": round(total_ltv, 2),
            "avg_order_value": round(avg_revenue_per_converted, 2),
            "lead_to_conversion_rate": round((n_converted / n_leads) * 100, 2),
            "overall_leakage_rate": round((1.0 - (n_converted / n_leads)) * 100, 2),
            "total_dollar_leakage": total_dollar_leakage,
            "stages": stages
        }

    def get_channel_funnel_breakdown(self):
        """Analyzes funnel leakage and efficiency metrics sliced by first-touch marketing channel."""
        channel_stats = []

        grouped = self.df.groupby('first_touch_channel')
        for ch, group in grouped:
            spend = float(self.channel_spend.get(ch, 0.0))
            n_tot = len(group)
            n_lead = int(group['is_lead'].sum())
            n_act = int(group['is_activated'].sum())
            n_conv = int(group['is_converted'].sum())
            rev = float(group['realized_revenue'].sum())
            ltv = float(group['twelve_month_ltv'].sum())

            # Costs & efficiency
            cpl = (spend / n_lead) if n_lead > 0 else 0.0
            cac = (spend / n_conv) if n_conv > 0 else 0.0
            roas = (rev / spend) if spend > 0 else 0.0

            # Conversion & drop-off rates
            lead_rate = (n_lead / n_tot * 100) if n_tot > 0 else 0
            act_rate = (n_act / n_lead * 100) if n_lead > 0 else 0
            conv_rate = (n_conv / n_act * 100) if n_act > 0 else 0
            lead_to_rev_rate = (n_conv / n_lead * 100) if n_lead > 0 else 0
            
            # Vanity Lead Ratio (% of leads from this channel that never convert to revenue)
            vanity_lead_pct = ((n_lead - n_conv) / n_lead * 100) if n_lead > 0 else 0.0

            # Average Quality Score
            avg_lq = float(group[group['is_lead'] == 1]['lead_quality_score'].mean()) if n_lead > 0 else 0.0

            channel_stats.append({
                "channel": ch,
                "spend": round(spend, 2),
                "total_prospects": n_tot,
                "leads_generated": n_lead,
                "activated_users": n_act,
                "paid_conversions": n_conv,
                "realized_revenue": round(rev, 2),
                "twelve_month_ltv": round(ltv, 2),
                "cpl": round(cpl, 2),
                "cac": round(cac, 2),
                "roas": round(roas, 2),
                "lead_capture_rate": round(lead_rate, 1),
                "activation_rate": round(act_rate, 1),
                "activation_to_paid_rate": round(conv_rate, 1),
                "lead_to_paid_rate": round(lead_to_rev_rate, 1),
                "vanity_lead_pct": round(vanity_lead_pct, 1),
                "avg_lead_quality": round(avg_lq, 1),
                "funnel_health": "Critical Leakage" if vanity_lead_pct > 80 else ("Moderate Drag" if vanity_lead_pct > 65 else "High Yield")
            })

        channel_stats.sort(key=lambda x: x['realized_revenue'], reverse=True)
        return channel_stats

    def get_segment_funnel_breakdown(self):
        """Analyzes funnel progression by customer segment."""
        segment_stats = []
        for seg, group in self.df.groupby('segment'):
            n_tot = len(group)
            n_lead = int(group['is_lead'].sum())
            n_act = int(group['is_activated'].sum())
            n_conv = int(group['is_converted'].sum())
            rev = float(group['realized_revenue'].sum())
            
            segment_stats.append({
                "segment": seg,
                "prospects": n_tot,
                "leads": n_lead,
                "activated": n_act,
                "conversions": n_conv,
                "revenue": round(rev, 2),
                "lead_to_paid_rate": round((n_conv / n_lead * 100) if n_lead > 0 else 0, 1),
                "avg_deal_size": round((rev / n_conv) if n_conv > 0 else 0, 2)
            })
        segment_stats.sort(key=lambda x: x['revenue'], reverse=True)
        return segment_stats

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(base_dir, "data", "customer_journeys.csv"))
    with open(os.path.join(base_dir, "data", "channel_spend.json")) as f:
        spend = json.load(f)
    analyzer = FunnelAnalyzer(df, spend)
    global_metrics = analyzer.get_global_funnel_metrics()
    print("Funnel Analytics Summary:")
    print(f"Total Leads: {global_metrics['total_leads']:,} | Total Converted: {global_metrics['total_converted']:,}")
    print(f"Lead-to-Revenue Conversion Rate: {global_metrics['lead_to_conversion_rate']}%")
    print(f"Total Dollar Leakage: ${global_metrics['total_dollar_leakage']:,.2f}")
    for stage in global_metrics['stages']:
        print(f"  Stage {stage['stage_id']}: {stage['stage_name']:<25} | Count: {stage['count']:>6,} | Drop-off: {stage['drop_off_rate']:>5.1f}% | Dollar Loss: ${stage['estimated_dollar_loss']:>10,.2f}")
