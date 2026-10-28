"""
Data Generator for Project - 03: Marketing-to-Revenue Attribution
Simulates Amazon's multi-channel marketing campaigns, customer journeys,
funnel progression, and revenue attribution data.
"""
import os
import json
import numpy as np
import pandas as pd

def generate_marketing_attribution_data(output_dir, n_journeys=25000, seed=42):
    """
    Generates realistic multi-touch customer journeys capturing Amazon's marketing funnel:
    Campaign Exposure -> Clicks -> Lead Capture (MQL) -> Activation -> Paid Conversion -> Revenue Realization.
    Explicitly simulates the 'Leaky Funnel' paradox: high lead volume from vanity channels
    with low monetization vs high-intent channels with high revenue contribution.
    """
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    channels = [
        "Paid Search (High Intent)",
        "Social Ads (Meta/Instagram)",
        "Amazon DSP / Display",
        "Prime Video / Streaming Ads",
        "LinkedIn B2B / Enterprise",
        "Affiliate & Partners",
        "Email & Nurture",
        "Organic Search / Direct"
    ]

    # Channel spend allocation ($ total marketing budget = $4.85 Million)
    channel_spend = {
        "Paid Search (High Intent)": 1350000.0,
        "Social Ads (Meta/Instagram)": 1200000.0,  # High spend, vanity trap!
        "Amazon DSP / Display": 680000.0,
        "Prime Video / Streaming Ads": 550000.0,
        "LinkedIn B2B / Enterprise": 480000.0,
        "Affiliate & Partners": 320000.0,          # High leads, low LTV
        "Email & Nurture": 150000.0,
        "Organic Search / Direct": 120000.0        # SEO & brand direct
    }

    # First touch probability distribution
    first_touch_probs = [0.22, 0.32, 0.16, 0.12, 0.06, 0.07, 0.01, 0.04]
    first_touch_probs = np.array(first_touch_probs) / sum(first_touch_probs)

    # Transition probabilities to subsequent touchpoints
    next_touch_weights = {
        "Paid Search (High Intent)": [0.10, 0.05, 0.05, 0.05, 0.05, 0.05, 0.35, 0.30],
        "Social Ads (Meta/Instagram)": [0.15, 0.25, 0.15, 0.05, 0.05, 0.10, 0.15, 0.10],
        "Amazon DSP / Display": [0.30, 0.10, 0.15, 0.05, 0.05, 0.05, 0.15, 0.15],
        "Prime Video / Streaming Ads": [0.35, 0.10, 0.15, 0.05, 0.05, 0.05, 0.10, 0.15],
        "LinkedIn B2B / Enterprise": [0.20, 0.05, 0.05, 0.05, 0.25, 0.05, 0.20, 0.15],
        "Affiliate & Partners": [0.15, 0.20, 0.10, 0.05, 0.05, 0.20, 0.15, 0.10],
        "Email & Nurture": [0.25, 0.05, 0.05, 0.05, 0.10, 0.05, 0.20, 0.25],
        "Organic Search / Direct": [0.20, 0.05, 0.05, 0.05, 0.05, 0.05, 0.25, 0.30]
    }

    segments = ["Enterprise B2B", "Mid-Market", "SMB Merchant", "Individual Creator"]
    segment_probs = [0.12, 0.28, 0.42, 0.18]

    devices = ["Desktop", "Mobile", "Tablet"]
    device_probs = [0.54, 0.38, 0.08]

    regions = ["North America (US/CA)", "Europe (UK/DE/FR)", "Asia-Pacific (JP/AU/IN)", "Latin America"]
    region_probs = [0.55, 0.25, 0.15, 0.05]

    data_rows = []

    for i in range(1, n_journeys + 1):
        customer_id = f"AMZN-CUST-{100000 + i}"
        segment = np.random.choice(segments, p=segment_probs)
        device = np.random.choice(devices, p=device_probs)
        region = np.random.choice(regions, p=region_probs)

        # Generate number of touchpoints (1 to 5)
        n_touches = np.random.choice([1, 2, 3, 4, 5], p=[0.42, 0.28, 0.18, 0.08, 0.04])
        
        # Build path
        path = []
        first_ch = np.random.choice(channels, p=first_touch_probs)
        path.append(first_ch)

        for _ in range(1, n_touches):
            prev_ch = path[-1]
            probs = next_touch_weights[prev_ch]
            probs = np.array(probs) / sum(probs)
            next_ch = np.random.choice(channels, p=probs)
            path.append(next_ch)

        last_ch = path[-1]
        path_str = " > ".join(path)
        unique_channels = list(dict.fromkeys(path))

        # Funnel stage dynamics
        # Exposure and click are 100% for logged journeys
        exposure = 1
        click = 1

        # Lead generation probability based on channel mix:
        # Social Ads & Affiliate have very high lead capture rate (cheap promos, free trials, low friction forms)
        lead_capture_prob = 0.50
        if "Social Ads (Meta/Instagram)" in path or "Affiliate & Partners" in path:
            lead_capture_prob += 0.32
        if "Paid Search (High Intent)" in path:
            lead_capture_prob += 0.15
        if "LinkedIn B2B / Enterprise" in path:
            lead_capture_prob += 0.10
        lead_capture_prob = min(0.95, max(0.15, lead_capture_prob))
        
        is_lead = 1 if np.random.rand() < lead_capture_prob else 0

        # Activation (The First Chasm: Ghost Lead trap!)
        # Channels like Social Ads and Affiliates generate leads who bounce or never activate!
        is_activated = 0
        is_converted = 0
        realized_revenue = 0.0
        twelve_month_ltv = 0.0
        lead_quality_score = 0.0
        days_to_convert = 0

        if is_lead == 1:
            # Base activation probability
            base_act_prob = 0.35
            
            # Penalize vanity lead sources
            if path[0] == "Social Ads (Meta/Instagram)" and len(path) == 1:
                base_act_prob = 0.11 # Severe ghost lead drop-off
            elif path[0] == "Affiliate & Partners" and len(path) == 1:
                base_act_prob = 0.14
            elif "LinkedIn B2B / Enterprise" in path:
                base_act_prob = 0.62 # Highly qualified
            elif "Paid Search (High Intent)" in path:
                base_act_prob = 0.55
            elif "Organic Search / Direct" in path:
                base_act_prob = 0.58

            # Multi-touch boost (users with >= 3 touchpoints activate at 1.4x higher rate)
            if len(path) >= 3:
                base_act_prob *= 1.35
            if "Email & Nurture" in path:
                base_act_prob *= 1.25

            base_act_prob = min(0.88, max(0.05, base_act_prob))
            is_activated = 1 if np.random.rand() < base_act_prob else 0

            # Conversion to Paid Revenue
            if is_activated == 1:
                base_conv_prob = 0.38
                if "Paid Search (High Intent)" in path:
                    base_conv_prob += 0.22
                if "LinkedIn B2B / Enterprise" in path:
                    base_conv_prob += 0.28
                if segment == "Enterprise B2B":
                    base_conv_prob += 0.15
                elif segment == "Individual Creator":
                    base_conv_prob -= 0.12
                
                # If purely single-touch social/affiliate, conversion is low
                if path == ["Social Ads (Meta/Instagram)"]:
                    base_conv_prob = 0.08
                if path == ["Affiliate & Partners"]:
                    base_conv_prob = 0.10

                base_conv_prob = min(0.85, max(0.04, base_conv_prob))
                is_converted = 1 if np.random.rand() < base_conv_prob else 0

                if is_converted == 1:
                    # Revenue realization based on segment & channels
                    if segment == "Enterprise B2B":
                        realized_revenue = np.random.normal(7500, 1800)
                        twelve_month_ltv = realized_revenue * np.random.uniform(2.5, 4.0)
                    elif segment == "Mid-Market":
                        realized_revenue = np.random.normal(2400, 600)
                        twelve_month_ltv = realized_revenue * np.random.uniform(2.0, 3.2)
                    elif segment == "SMB Merchant":
                        realized_revenue = np.random.normal(850, 220)
                        twelve_month_ltv = realized_revenue * np.random.uniform(1.8, 2.5)
                    else: # Individual Creator
                        realized_revenue = np.random.normal(280, 80)
                        twelve_month_ltv = realized_revenue * np.random.uniform(1.2, 1.8)

                    realized_revenue = round(max(50.0, realized_revenue), 2)
                    twelve_month_ltv = round(max(realized_revenue, twelve_month_ltv), 2)
                    days_to_convert = int(np.random.gamma(shape=2.5, scale=4.0) + (len(path) * 2.5))
                    days_to_convert = min(75, max(1, days_to_convert))

            # Calculate composite Lead Quality Score (0 to 100)
            lq = 20.0
            if "LinkedIn B2B / Enterprise" in path:
                lq += 35.0
            if "Paid Search (High Intent)" in path:
                lq += 25.0
            if "Email & Nurture" in path:
                lq += 15.0
            if segment == "Enterprise B2B":
                lq += 20.0
            elif segment == "Mid-Market":
                lq += 12.0
            if len(path) >= 3:
                lq += 15.0
            if path[0] == "Social Ads (Meta/Instagram)" and len(path) == 1:
                lq -= 15.0
            if path[0] == "Affiliate & Partners" and len(path) == 1:
                lq -= 10.0
            
            lead_quality_score = round(min(98.0, max(5.0, lq + np.random.normal(0, 5))), 1)

        # Estimate journey cost
        touch_cost_map = {
            "Paid Search (High Intent)": 48.0,
            "Social Ads (Meta/Instagram)": 14.0,
            "Amazon DSP / Display": 22.0,
            "Prime Video / Streaming Ads": 32.0,
            "LinkedIn B2B / Enterprise": 85.0,
            "Affiliate & Partners": 16.0,
            "Email & Nurture": 3.0,
            "Organic Search / Direct": 2.0
        }
        journey_cost = sum(touch_cost_map.get(ch, 10.0) for ch in path)

        data_rows.append({
            "customer_id": customer_id,
            "segment": segment,
            "device": device,
            "region": region,
            "touchpoints_count": n_touches,
            "journey_path": path_str,
            "first_touch_channel": path[0],
            "last_touch_channel": path[-1],
            "channels_list": json.dumps(path),
            "unique_channels_count": len(unique_channels),
            "exposure": exposure,
            "click": click,
            "is_lead": is_lead,
            "is_activated": is_activated,
            "is_converted": is_converted,
            "realized_revenue": realized_revenue,
            "twelve_month_ltv": twelve_month_ltv,
            "lead_quality_score": lead_quality_score,
            "days_to_convert": days_to_convert,
            "journey_cost": journey_cost
        })

    df = pd.DataFrame(data_rows)
    csv_file = os.path.join(output_dir, "customer_journeys.csv")
    df.to_csv(csv_file, index=False)

    # Save marketing spend meta json
    spend_file = os.path.join(output_dir, "channel_spend.json")
    with open(spend_file, "w") as f:
        json.dump(channel_spend, f, indent=2)

    return df, channel_spend

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    df, spend = generate_marketing_attribution_data(data_dir, n_journeys=25000)
    print(f"Generated {len(df):,} customer journeys.")
    print(f"Total Leads: {df['is_lead'].sum():,}")
    print(f"Total Activated: {df['is_activated'].sum():,}")
    print(f"Total Paid Conversions: {df['is_converted'].sum():,}")
    print(f"Total Realized Revenue: ${df['realized_revenue'].sum():,.2f}")
