"""
Multi-Touch Attribution Engine for Project - 03: Marketing-to-Revenue Attribution
Calculates First-Touch, Last-Touch, Linear, Time-Decay, Position-Based (U-Shaped),
and Data-Driven Markov Chain Attribution with Removal Effects.
"""
import json
import numpy as np
import pandas as pd
from collections import defaultdict

class AttributionEngine:
    def __init__(self, df_journeys, channel_spend):
        """
        Initializes the Attribution Engine with customer journeys and channel spend.
        df_journeys: DataFrame containing 'journey_path', 'channels_list', 'is_converted', 'realized_revenue'
        channel_spend: Dict of {channel_name: spend_usd}
        """
        self.df = df_journeys.copy()
        if isinstance(self.df['channels_list'].iloc[0], str):
            self.df['channels_list'] = self.df['channels_list'].apply(json.loads)
            
        self.channel_spend = channel_spend
        self.channels = sorted(list(channel_spend.keys()))
        self.total_spend = sum(channel_spend.values())
        self.total_revenue = float(self.df['realized_revenue'].sum())
        self.total_conversions = int(self.df['is_converted'].sum())
        
        self.results = {}

    def compute_rule_based_attribution(self):
        """Computes First-Touch, Last-Touch, Linear, Time-Decay, and Position-Based attribution."""
        fta_rev = defaultdict(float)
        fta_conv = defaultdict(float)
        
        lta_rev = defaultdict(float)
        lta_conv = defaultdict(float)
        
        linear_rev = defaultdict(float)
        linear_conv = defaultdict(float)
        
        decay_rev = defaultdict(float)
        decay_conv = defaultdict(float)
        
        pos_rev = defaultdict(float)
        pos_conv = defaultdict(float)

        converted_df = self.df[self.df['is_converted'] == 1]

        for _, row in converted_df.iterrows():
            path = row['channels_list']
            rev = row['realized_revenue']
            k = len(path)

            if k == 0:
                continue

            # First Touch
            fta_rev[path[0]] += rev
            fta_conv[path[0]] += 1

            # Last Touch
            lta_rev[path[-1]] += rev
            lta_conv[path[-1]] += 1

            # Linear
            for ch in path:
                linear_rev[ch] += rev / k
                linear_conv[ch] += 1.0 / k

            # Time Decay (half-life weighting: 2^(t - k))
            decay_weights = [2.0 ** (idx - k + 1) for idx in range(k)]
            sum_decay = sum(decay_weights)
            for idx, ch in enumerate(path):
                w = decay_weights[idx] / sum_decay
                decay_rev[ch] += rev * w
                decay_conv[ch] += 1.0 * w

            # Position-Based (U-Shaped: 40% First, 40% Last, 20% Middle)
            if k == 1:
                pos_rev[path[0]] += rev
                pos_conv[path[0]] += 1.0
            elif k == 2:
                pos_rev[path[0]] += rev * 0.5
                pos_conv[path[0]] += 0.5
                pos_rev[path[1]] += rev * 0.5
                pos_conv[path[1]] += 0.5
            else:
                pos_rev[path[0]] += rev * 0.4
                pos_conv[path[0]] += 0.4
                pos_rev[path[-1]] += rev * 0.4
                pos_conv[path[-1]] += 0.4
                middle_weight = 0.2 / (k - 2)
                for ch in path[1:-1]:
                    pos_rev[ch] += rev * middle_weight
                    pos_conv[ch] += 1.0 * middle_weight

        return {
            "first_touch": {"revenue": fta_rev, "conversions": fta_conv},
            "last_touch": {"revenue": lta_rev, "conversions": lta_conv},
            "linear": {"revenue": linear_rev, "conversions": linear_conv},
            "time_decay": {"revenue": decay_rev, "conversions": decay_conv},
            "position_based": {"revenue": pos_rev, "conversions": pos_conv}
        }

    def compute_markov_chain_attribution(self):
        """
        Computes Data-Driven Attribution using Higher-Order / 1st-Order Markov Chains
        with Removal Effect calculation across all multi-touch paths.
        """
        transitions = defaultdict(lambda: defaultdict(int))
        
        for _, row in self.df.iterrows():
            path = row['channels_list']
            converted = row['is_converted'] == 1
            
            if not path:
                continue

            # (Start) -> First Channel
            transitions['(Start)'][path[0]] += 1

            # Intermediate transitions
            for i in range(len(path) - 1):
                transitions[path[i]][path[i+1]] += 1

            # Channel -> (Conversion) or (Null)
            if converted:
                transitions[path[-1]]['(Conversion)'] += 1
            else:
                transitions[path[-1]]['(Null)'] += 1

        # Build state set
        all_states = set(self.channels)
        all_states.add('(Start)')
        all_states.add('(Conversion)')
        all_states.add('(Null)')
        state_list = sorted(list(all_states))
        state_idx = {s: i for i, s in enumerate(state_list)}
        n_states = len(state_list)

        # Transition Probability Matrix P
        P = np.zeros((n_states, n_states), dtype=float)
        for s_from, targets in transitions.items():
            total = sum(targets.values())
            if total > 0:
                for s_to, count in targets.items():
                    P[state_idx[s_from], state_idx[s_to]] = count / total

        # Absorbing states: (Conversion) and (Null)
        P[state_idx['(Conversion)'], state_idx['(Conversion)']] = 1.0
        P[state_idx['(Null)'], state_idx['(Null)']] = 1.0

        def calc_conversion_probability(P_mat):
            """Computes absorption probability from (Start) to (Conversion) via Fundamental Matrix."""
            # Transient states are non-absorbing
            transient = [s for s in state_list if s not in ['(Conversion)', '(Null)']]
            t_indices = [state_idx[s] for s in transient]
            conv_idx = state_idx['(Conversion)']

            # Q: transient to transient, R: transient to absorbing
            Q = P_mat[np.ix_(t_indices, t_indices)]
            R = P_mat[np.ix_(t_indices, [conv_idx])]

            I = np.eye(len(transient))
            try:
                # Fundamental matrix N = (I - Q)^-1
                N = np.linalg.inv(I - Q)
                B = np.dot(N, R)
                start_t_idx = transient.index('(Start)')
                return float(B[start_t_idx, 0])
            except np.linalg.LinAlgError:
                return 0.0

        base_conv_prob = calc_conversion_probability(P)

        removal_effects = {}
        for ch in self.channels:
            P_removed = P.copy()
            c_idx = state_idx[ch]
            # When channel is removed, transitions to it drop to 0 and redirect to (Null)
            P_removed[c_idx, :] = 0.0
            P_removed[c_idx, state_idx['(Null)']] = 1.0
            
            p_conv_without_c = calc_conversion_probability(P_removed)
            if base_conv_prob > 0:
                re = max(0.0, (base_conv_prob - p_conv_without_c) / base_conv_prob)
            else:
                re = 0.0
            removal_effects[ch] = re

        total_re = sum(removal_effects.values())
        markov_weights = {}
        for ch in self.channels:
            markov_weights[ch] = removal_effects[ch] / total_re if total_re > 0 else (1.0 / len(self.channels))

        markov_conv = {ch: markov_weights[ch] * self.total_conversions for ch in self.channels}
        markov_rev = {ch: markov_weights[ch] * self.total_revenue for ch in self.channels}

        return {
            "removal_effects": removal_effects,
            "markov_weights": markov_weights,
            "conversions": markov_conv,
            "revenue": markov_rev
        }

    def get_full_attribution_comparison(self):
        """Builds a comprehensive comparison matrix for all attribution models."""
        rule_based = self.compute_rule_based_attribution()
        markov = self.compute_markov_chain_attribution()

        models = {
            "first_touch": "First-Touch Attribution",
            "last_touch": "Last-Touch Attribution",
            "linear": "Linear Attribution",
            "time_decay": "Time-Decay Attribution",
            "position_based": "Position-Based (U-Shaped)",
            "markov_chain": "Markov Chain (Data-Driven AI)"
        }

        channel_data = []

        for ch in self.channels:
            spend = float(self.channel_spend.get(ch, 0.0))
            
            lta_r = float(rule_based["last_touch"]["revenue"].get(ch, 0.0))
            lta_c = float(rule_based["last_touch"]["conversions"].get(ch, 0.0))
            
            fta_r = float(rule_based["first_touch"]["revenue"].get(ch, 0.0))
            fta_c = float(rule_based["first_touch"]["conversions"].get(ch, 0.0))
            
            lin_r = float(rule_based["linear"]["revenue"].get(ch, 0.0))
            lin_c = float(rule_based["linear"]["conversions"].get(ch, 0.0))
            
            decay_r = float(rule_based["time_decay"]["revenue"].get(ch, 0.0))
            decay_c = float(rule_based["time_decay"]["conversions"].get(ch, 0.0))

            pos_r = float(rule_based["position_based"]["revenue"].get(ch, 0.0))
            pos_c = float(rule_based["position_based"]["conversions"].get(ch, 0.0))

            mkv_r = float(markov["revenue"].get(ch, 0.0))
            mkv_c = float(markov["conversions"].get(ch, 0.0))
            mkv_weight = float(markov["markov_weights"].get(ch, 0.0))
            mkv_re = float(markov["removal_effects"].get(ch, 0.0))

            # Financial KPIs
            lta_roas = (lta_r / spend) if spend > 0 else 0.0
            mkv_roas = (mkv_r / spend) if spend > 0 else 0.0
            mkv_cac = (spend / mkv_c) if mkv_c > 0 else 0.0
            lta_cac = (spend / lta_c) if lta_c > 0 else 0.0

            # Distortion index: Difference between LTA and Markov AI attribution
            distortion_pct = ((lta_r - mkv_r) / mkv_r * 100.0) if mkv_r > 0 else 0.0

            channel_data.append({
                "channel": ch,
                "spend": round(spend, 2),
                "spend_share": round((spend / self.total_spend) * 100, 2),
                "first_touch": {"revenue": round(fta_r, 2), "conversions": round(fta_c, 1), "roas": round(fta_r / spend, 2) if spend > 0 else 0},
                "last_touch": {"revenue": round(lta_r, 2), "conversions": round(lta_c, 1), "roas": round(lta_roas, 2), "cac": round(lta_cac, 2)},
                "linear": {"revenue": round(lin_r, 2), "conversions": round(lin_c, 1), "roas": round(lin_r / spend, 2) if spend > 0 else 0},
                "time_decay": {"revenue": round(decay_r, 2), "conversions": round(decay_c, 1), "roas": round(decay_r / spend, 2) if spend > 0 else 0},
                "position_based": {"revenue": round(pos_r, 2), "conversions": round(pos_c, 1), "roas": round(pos_r / spend, 2) if spend > 0 else 0},
                "markov_chain": {
                    "revenue": round(mkv_r, 2),
                    "conversions": round(mkv_c, 1),
                    "roas": round(mkv_roas, 2),
                    "cac": round(mkv_cac, 2),
                    "markov_weight": round(mkv_weight * 100, 2),
                    "removal_effect": round(mkv_re, 4)
                },
                "distortion_pct": round(distortion_pct, 1),
                "lta_distortion_status": "Over-Valued by LTA" if distortion_pct > 15 else ("Under-Valued by LTA" if distortion_pct < -15 else "Fairly Valued")
            })

        summary = {
            "total_spend": round(self.total_spend, 2),
            "total_realized_revenue": round(self.total_revenue, 2),
            "total_conversions": self.total_conversions,
            "overall_roas": round(self.total_revenue / self.total_spend, 2),
            "overall_cac": round(self.total_spend / self.total_conversions, 2),
            "channel_comparison": channel_data
        }
        return summary

if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(base_dir, "data", "customer_journeys.csv"))
    with open(os.path.join(base_dir, "data", "channel_spend.json")) as f:
        spend = json.load(f)
    engine = AttributionEngine(df, spend)
    comparison = engine.get_full_attribution_comparison()
    print("Multi-Touch Attribution Summary:")
    print(f"Total Spend: ${comparison['total_spend']:,.2f} | Realized Revenue: ${comparison['total_realized_revenue']:,.2f} | Overall ROAS: {comparison['overall_roas']}x")
    for ch in comparison['channel_comparison']:
        print(f"  • {ch['channel']:<30} | Spend: ${ch['spend']:>10,.0f} | Markov ROAS: {ch['markov_chain']['roas']:>4.2f}x | LTA ROAS: {ch['last_touch']['roas']:>4.2f}x | LTA Bias: {ch['distortion_pct']:>+6.1f}% ({ch['lta_distortion_status']})")
