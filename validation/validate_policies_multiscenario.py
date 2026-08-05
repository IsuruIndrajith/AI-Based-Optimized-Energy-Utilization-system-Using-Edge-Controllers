"""
validate_policies_multiscenario.py
===================================
Controlled experiment: 40 scenarios total, 10 per policy.

For each policy group, ONE variable changes across 10 scenarios.
Everything else stays STATIC. Only that group's policy is evaluated.

  CS01  — vary TOU prices only       → check cost savings
  CAP01 — vary grid capacity only    → check capacity compliance
  W01   — vary temperature/humidity  → check AC comfort alignment
  U01   — vary user preference msg   → check WM peak restriction

Final result:
  CS01 : X/10 passed
  CAP01: X/10 passed
  W01  : X/10 passed
  U01  : X/10 passed
"""

import os
import sys
import json
import re
import statistics
import requests
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agent
import validate_policies

# ============================================================================
# HELPERS
# ============================================================================

def make_price_map(off_peak, day, peak):
    pm = {}
    for h in range(24):
        if h < 5 or h >= 22:  pm[h] = {"price": off_peak, "band": "off_peak"}
        elif 5 <= h < 18:     pm[h] = {"price": day,      "band": "day"}
        else:                  pm[h] = {"price": peak,     "band": "peak"}
    return pm

def make_cap_map(off_peak, day, peak):
    cm = {}
    for h in range(24):
        if h < 5 or h >= 22:  cm[h] = off_peak
        elif 5 <= h < 18:     cm[h] = day
        else:                  cm[h] = peak
    return cm

def make_weather(temp, hum):
    return {"temperature": [temp] * 24, "humidity": [hum] * 24}

# ── STATIC DEFAULTS (shared across all groups except their own variable) ──────
STATIC_PRICE   = make_price_map(33.0, 47.0, 106.0)   # LECO standard
STATIC_CAP     = make_cap_map(6.0, 4.0, 2.5)          # standard TOU capacity
STATIC_WEATHER = make_weather(26.0, 60.0)              # mild, no AC/Heater pressure
STATIC_PREF    = "No specific preferences today."      # neutral user message


# ============================================================================
# 1. SCENARIO DEFINITIONS
# ============================================================================

def build_scenarios():
    """
    Returns 40 scenarios in 4 groups of 10.
    Each group changes ONLY its variable; everything else is static.
    """
    scenarios = []

    # ── GROUP CS01: Vary TOU Prices only ─────────────────────────────────────
    # Static: weather=mild(26°C/60%), capacity=standard, user_pref=neutral
    # Variable: off_peak / day / peak tariff rates (LKR/kWh)
    # Policy checked: CS01 — optimized cost < baseline cost
    cs_rates = [
        (10.0,  20.0,   40.0,  "Very cheap rates — small absolute savings"),
        (20.0,  35.0,   70.0,  "Low rates — moderate TOU gap"),
        (33.0,  47.0,  106.0,  "Standard LECO rates"),
        (33.0,  47.0,  150.0,  "Higher peak tariff (150 LKR)"),
        (33.0,  47.0,  200.0,  "Expensive peak (200 LKR)"),
        (33.0,  47.0,  250.0,  "Very expensive peak (250 LKR)"),
        (33.0,  47.0,  300.0,  "Hyper peak tariff (300 LKR)"),
        (33.0,  47.0,  400.0,  "Extreme peak tariff (400 LKR)"),
        (10.0,  47.0,  106.0,  "Very cheap off-peak (10 LKR) — big shift incentive"),
        (20.0,  100.0, 200.0,  "Expensive day + peak — shift to night"),
    ]
    for i, (op, d, pk, desc) in enumerate(cs_rates, 1):
        scenarios.append({
            "id":           f"CS-S{i:02d}",
            "policy_group": "CS01",
            "policy_label": "Cost Savings",
            "desc":         f"CS01 | off_peak={op} day={d} peak={pk} LKR — {desc}",
            "weather":      STATIC_WEATHER,
            "user_preference": {"raw_message": STATIC_PREF},
            "price_map":    make_price_map(op, d, pk),
            "capacity_map": STATIC_CAP,
        })

    # ── GROUP CAP01: Vary Grid Capacity only ──────────────────────────────────
    # Static: weather=mild, price=LECO standard, user_pref=neutral
    # Variable: off_peak / day / peak capacity limits (kW)
    # Policy checked: CAP01 — total load never exceeds capacity at any hour
    cap_values = [
        (6.0, 4.0,  2.5,  "Standard TOU capacity"),
        (6.0, 4.0,  2.0,  "Tighter peak capacity (2.0 kW)"),
        (6.0, 4.0,  1.5,  "Tight peak capacity (1.5 kW)"),
        (6.0, 4.0,  1.0,  "Very tight peak capacity (1.0 kW)"),
        (6.0, 3.0,  2.5,  "Tighter day capacity (3.0 kW)"),
        (6.0, 2.0,  2.5,  "Very tight day capacity (2.0 kW)"),
        (5.0, 3.0,  1.5,  "Tight all bands"),
        (3.0, 3.0,  3.0,  "Global 3.0 kW limit (all equal)"),
        (8.0, 10.0, 2.5,  "High day capacity — solar abundance (10 kW)"),
        (8.0, 5.0,  3.0,  "Relaxed all bands — generous capacity"),
    ]
    for i, (op, d, pk, desc) in enumerate(cap_values, 1):
        scenarios.append({
            "id":           f"CAP-S{i:02d}",
            "policy_group": "CAP01",
            "policy_label": "Grid Capacity",
            "desc":         f"CAP01 | off_peak={op} day={d} peak={pk} kW — {desc}",
            "weather":      STATIC_WEATHER,
            "user_preference": {"raw_message": STATIC_PREF},
            "price_map":    STATIC_PRICE,
            "capacity_map": make_cap_map(op, d, pk),
        })

    # ── GROUP W01: Vary Weather only ──────────────────────────────────────────
    # Static: price=LECO standard, capacity=standard, user_pref=neutral
    # Variable: temperature (°C) and humidity (%)
    # Policy checked: W01 — AC ON hours overlap with hot/humid hours
    weather_values = [
        (14.0, 50.0, "Very cold day — heater zone, no AC needed"),
        (18.0, 55.0, "Cold day — mild, neither AC nor heater forced"),
        (22.0, 58.0, "Mild temperature — borderline cool"),
        (24.0, 60.0, "Comfortable — no strong comfort preference"),
        (26.0, 65.0, "Slightly warm — near AC threshold"),
        (28.0, 70.0, "Borderline hot (28°C threshold)"),
        (30.0, 72.0, "Warm day — AC desirable"),
        (32.0, 75.0, "Hot day — AC strongly preferred"),
        (35.0, 80.0, "Very hot + humid — AC essential"),
        (38.0, 90.0, "Extreme heat + humidity — AC must run"),
    ]
    for i, (temp, hum, desc) in enumerate(weather_values, 1):
        scenarios.append({
            "id":           f"W-S{i:02d}",
            "policy_group": "W01",
            "policy_label": "Weather Comfort",
            "desc":         f"W01 | temp={temp}°C hum={hum}% — {desc}",
            "weather":      make_weather(temp, hum),
            "user_preference": {"raw_message": STATIC_PREF},
            "price_map":    STATIC_PRICE,
            "capacity_map": STATIC_CAP,
        })

    # ── GROUP U01: Vary User Preference only ──────────────────────────────────
    # Static: weather=mild, price=LECO standard, capacity=standard
    # Variable: user's natural-language preference message
    # Policy checked: U01 — WashingMachine not scheduled during peak hours
    user_prefs = [
        "I have no specific preferences today.",
        "Please do not run the washing machine during peak hours.",
        "Run the washing machine before 9 AM only.",
        "Run the washing machine only between midnight and 5 AM.",
        "Keep all heavy appliances off during the evening peak period.",
        "The washing machine should not run after 6 PM.",
        "Run the washing machine as early in the morning as possible.",
        "Do not use the washing machine between 6 PM and 10 PM.",
        "Minimize electricity cost. Avoid peak hours for all appliances.",
        "Washing machine must only run during off-peak hours at night.",
    ]
    for i, pref in enumerate(user_prefs, 1):
        scenarios.append({
            "id":           f"U-S{i:02d}",
            "policy_group": "U01",
            "policy_label": "User Preference",
            "desc":         f"U01 | pref={i:02d} — \"{pref[:60]}\"",
            "weather":      STATIC_WEATHER,
            "user_preference": {"raw_message": pref},
            "price_map":    STATIC_PRICE,
            "capacity_map": STATIC_CAP,
        })

    return scenarios


# ============================================================================
# 2. POLICY DEFINITIONS (one per group — only that policy is evaluated)
# ============================================================================

GROUP_POLICY = {
    "CS01": {
        "id":          "CS01",
        "description": "Optimized schedule cost must be less than the LSTM baseline cost.",
        "category":    "cost_savings",
        "meta":        {},
    },
    "CAP01": {
        "id":          "CAP01",
        "description": "Total scheduled load must not exceed TOU-band capacity at any hour.",
        "category":    "capacity",
        "meta":        {"hour": None},
    },
    "W01": {
        "id":          "W01",
        "description": "AC must run during hot/humid hours (comfort alignment).",
        "category":    "weather",
        "meta":        {"app": "AC_Power"},
    },
    "U01": {
        "id":          "U01",
        "description": "WashingMachine must not run during peak hours (allow_peak=False).",
        "category":    "user_preference",
        "meta":        {"app": "WashingMachine_Power", "check": "allow_peak"},
    },
}


# ============================================================================
# 3. METRIC EXTRACTION
# ============================================================================

def extract_metric(grp: str, reason: str):
    """Extract a numeric metric from the policy reason string."""
    if grp == "CS01":
        # e.g. "Savings = 1234.56 LKR (45.67%)."
        m = re.search(r'\(([0-9\.]+)%\)', reason)
        if m:
            return float(m.group(1))
    elif grp == "W01":
        # e.g. "overlap=[...] (80% >= 1%)."
        m = re.search(r'overlap=.*?\(([0-9\.]+)%', reason)
        if m:
            return float(m.group(1))
    return None


# ============================================================================
# 4. RUNNER
# ============================================================================

def run_all():
    # ── Ollama availability check ─────────────────────────────────────────────
    print("Checking Ollama availability...")
    try:
        resp = requests.get("http://localhost:11434", timeout=5)
        if resp.status_code != 200:
            raise ConnectionError(f"Ollama responded with HTTP {resp.status_code}")
        print("Ollama is running. LLM-only scheduling enabled.\n")
    except Exception as e:
        print(f"\nOllama is NOT running — cannot proceed.")
        print(f"   Reason : {e}")
        print(f"   Fix    : run 'ollama serve' in another terminal, then retry.")
        sys.exit(1)

    scenarios = build_scenarios()
    groups    = ["CS01", "CAP01", "W01", "U01"]
    results   = {g: [] for g in groups}

    print(f"Running 40 scenarios — 10 per policy group\n"
          f"Each group changes ONE variable; only its own policy is evaluated.\n")

    for s in scenarios:
        grp = s["policy_group"]
        pol = GROUP_POLICY[grp]

        print(f"{'─'*64}")
        print(f"  [{grp}]  {s['id']}  {s['desc']}")

        # ── Mock external services with scenario-specific values ──────────────
        def mock_weather(_s=s):        return _s["weather"]
        def mock_user_pref(_s=s):      return _s["user_preference"]["raw_message"]
        def mock_tou(*a, **kw):        return {"capacity_map": s["capacity_map"]}
        def mock_price_map(tou_json):  return s["price_map"], "LKR"

        agent_ok = False
        with patch("agent.fetch_weather_24h",    side_effect=mock_weather), \
             patch("agent.get_user_preference",  side_effect=mock_user_pref), \
             patch("agent.get_tou_and_capacity", side_effect=mock_tou), \
             patch("agent.build_price_map",      side_effect=mock_price_map):
            try:
                agent.main_once()
                agent_ok = True
            except Exception as e:
                print(f"  SKIPPED — LLM failed: {e}")

        if not agent_ok:
            continue

        # ── Load the schedule the LLM just produced ───────────────────────────
        try:
            (app_data, schedules, explanations,
             price_map, capacity_map,
             user_preference, weather) = validate_policies.load_pipeline_data()
        except Exception as e:
            print(f"  Could not load pipeline data: {e}")
            continue

        # ── Evaluate ONLY this group's policy ─────────────────────────────────
        passed, reason = validate_policies.evaluate_policy(
            pol, app_data, schedules, explanations,
            price_map, user_preference, weather,
            capacity_map=capacity_map,
        )
        metric = extract_metric(grp, reason)
        status = "PASS " if passed else "FAIL "
        print(f"  {status}  {reason[:90]}")

        results[grp].append({
            "id":     s["id"],
            "desc":   s["desc"],
            "passed": passed,
            "reason": reason,
            "metric": metric,
        })

    # ============================================================================
    # 5. SUMMARY
    # ============================================================================
    print(f"\n{'='*64}")
    print(f"  FINAL RESULTS — Controlled Policy Validation (40 Scenarios)")
    print(f"{'='*64}")
    print(f"\n  {'Policy':<8} {'Label':<18} {'Pass/Total':<14} {'Rate':<8}  Variable Changed")
    print(f"  {'─'*70}")

    variable_labels = {
        "CS01":  "TOU price rates",
        "CAP01": "Grid capacity (kW)",
        "W01":   "Temperature / Humidity",
        "U01":   "User preference message",
    }

    group_summaries = {}
    for grp in groups:
        grp_res = results[grp]
        total   = len(grp_res)
        passed  = sum(1 for r in grp_res if r["passed"])
        rate    = f"{passed}/{total}" if total > 0 else "0/0"
        pct     = round(passed / total * 100, 1) if total > 0 else 0.0

        metrics = [r["metric"] for r in grp_res if r["metric"] is not None]
        summ    = {"passed": passed, "total": total, "pass_rate_%": pct}
        if metrics:
            summ["metric_mean"] = round(statistics.mean(metrics), 2)
            summ["metric_min"]  = round(min(metrics), 2)
            summ["metric_max"]  = round(max(metrics), 2)
            if len(metrics) > 1:
                summ["metric_std"] = round(statistics.stdev(metrics), 2)
        group_summaries[grp] = summ

        label_map = {"CS01": "Cost Savings", "CAP01": "Grid Capacity",
                     "W01": "Weather Comfort", "U01": "User Preference"}
        print(f"  {grp:<8} {label_map[grp]:<18} {rate:<14} {pct:>5.1f}%   {variable_labels[grp]}")

    # Per-group detail
    for grp in groups:
        grp_res = results[grp]
        if not grp_res:
            continue
        label_map = {"CS01": "Cost Savings", "CAP01": "Grid Capacity",
                     "W01": "Weather Comfort", "U01": "User Preference"}
        print(f"\n  ── {grp} ({label_map[grp]}) — per-scenario breakdown ──")
        print(f"  {'ID':<10} {'Result':<10}  Description")
        print(f"  {'─'*60}")
        for r in grp_res:
            res = "PASS " if r["passed"] else "FAIL "
            print(f"  {r['id']:<10} {res:<10}  {r['desc'][:55]}")
        s = group_summaries[grp]
        print(f"\n  → {s['passed']}/{s['total']} passed ({s['pass_rate_%']}%)", end="")
        if "metric_mean" in s:
            print(f"   |  metric mean={s['metric_mean']}  "
                  f"min={s['metric_min']}  max={s['metric_max']}", end="")
        print()

    # Save JSON report
    out_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..",
                     "validation_report_multiscenario.json")
    )
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(
            {"scenarios": {g: results[g] for g in groups},
             "summary":   group_summaries},
            f, indent=2,
        )
    print(f"\n  Full report → {out_file}\n")

    # Generate Summary Plot
    plot_results(group_summaries)


def plot_results(group_summaries):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        plots_dir = os.path.join(base_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        groups = ["CS01", "CAP01", "W01", "U01"]
        labels = ["Cost Savings\n(CS01)", "Grid Capacity\n(CAP01)", "Weather Comfort\n(W01)", "User Preference\n(U01)"]
        pass_rates = [group_summaries[g]["pass_rate_%"] for g in groups]
        passed_counts = [group_summaries[g]["passed"] for g in groups]
        total_counts = [group_summaries[g]["total"] for g in groups]

        plt.style.use('ggplot')
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ['#2E75B6', '#4CAF50', '#795548', '#9C27B0']
        bars = ax.bar(labels, pass_rates, color=colors, edgecolor='black', width=0.55, zorder=3)

        ax.set_ylabel("Pass Rate (%)", fontsize=12, fontweight='bold')
        ax.set_title("Controlled Policy Validation Results (10 Scenarios per Policy)", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylim(0, 115)
        ax.yaxis.grid(True, linestyle='--', alpha=0.7, zorder=0)

        for bar, passed, total, pct in zip(bars, passed_counts, total_counts, pass_rates):
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{pct:.1f}%\n({passed}/{total})",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

        plt.tight_layout()
        out_png = os.path.join(plots_dir, "multiscenario_validation_summary.png")
        out_pdf = os.path.join(plots_dir, "multiscenario_validation_summary.pdf")
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        plt.savefig(out_pdf, bbox_inches='tight')
        plt.close()

        print(f" Summary plots generated:\n  - {out_png}\n  - {out_pdf}\n")
    except Exception as e:
        print(f" Could not generate plot: {e}")


if __name__ == "__main__":
    run_all()

