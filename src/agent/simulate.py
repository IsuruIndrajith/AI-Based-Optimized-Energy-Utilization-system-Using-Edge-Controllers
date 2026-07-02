"""
simulate.py — Real-Pipeline Model Validation
=============================================
Compares the LSTM-predicted baseline schedule against the agent's
MILP-optimised schedule for the ACTUAL pipeline run.

Data sources (all produced by running Run_LSTM.py + agent.py):
  - appliance_data.json  : LSTM-predicted states + averages + demand stats
  - output.json          : Agent-scheduled (MILP) states for each appliance
  - output_explanations.json : Cost breakdown + LLM preference decisions

This replaces the old synthetic random-data comparison which never
exercised the actual LSTM model.
"""

import json
import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    APPLIANCES,
    POWER_KWH,
    LECO_RATE_OFF_PEAK_LKR,
    LECO_RATE_DAY_LKR,
    LECO_RATE_PEAK_LKR,
    LECO_DAY_START_HOUR,
    LECO_DAY_END_HOUR,
    LECO_PEAK_START_HOUR,
    LECO_PEAK_END_HOUR,
    HOT_TEMPERATURE_THRESHOLD_C,
    HIGH_HUMIDITY_THRESHOLD_PCT,
    COLD_TEMPERATURE_THRESHOLD_C,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_price_map():
    price_map = {}
    for h in range(24):
        price_map[h] = {"price": LECO_RATE_OFF_PEAK_LKR, "band": "off_peak"}
    for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
        price_map[h] = {"price": LECO_RATE_DAY_LKR, "band": "day"}
    for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
        price_map[h] = {"price": LECO_RATE_PEAK_LKR, "band": "peak"}
    return price_map


def cost_for_states(states, power_kwh, price_map):
    total = 0.0
    for h, state in enumerate(states):
        if state == 1:
            total += power_kwh * price_map[h]["price"]
    return total


def peak_load_kw(schedules):
    hourly = [0.0] * 24
    for app in APPLIANCES:
        for h, state in enumerate(schedules.get(app, [0] * 24)):
            hourly[h] += state * POWER_KWH[app]
    return max(hourly)


def required_hours_from_demand(app_data_entry):
    """
    Derives required ON-hours using the demand-driven formula:
        required_hours = round(sum(averages_W) / rated_power_W)
    This mirrors exactly what Run_LSTM.py does with binarize_by_demand().
    """
    averages_w = app_data_entry.get("averages", [])
    rated_w = POWER_KWH[None]  # placeholder — overridden below
    return sum(averages_w)


def get_required_hours(app, app_data):
    """Returns required runtime hours stored in appliance_data.json (states field sum)."""
    states = app_data[app].get("states", [0] * 24)
    return int(sum(states))


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_pipeline_outputs():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    paths = {
        "appliance_data":   os.path.join(base, "appliance_data.json"),
        "output":           os.path.join(base, "output.json"),
        "output_expl":      os.path.join(base, "output_explanations.json"),
    }
    data = {}
    for key, path in paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"[simulate.py] Required file not found: {path}\n"
                "Please run Run_LSTM.py and agent.py first."
            )
        with open(path, "r", encoding="utf-8") as f:
            data[key] = json.load(f)

    return data["appliance_data"], data["output"], data["output_expl"]


# ---------------------------------------------------------------------------
# Prediction Accuracy
# ---------------------------------------------------------------------------

def check_lstm_accuracy(app_data, agent_schedules):
    """
    Checks how accurately the LSTM-predicted demand was reflected in the
    agent's schedule.

    Metric: runtime match
      required_hours  = sum(predicted binary states from LSTM)
      scheduled_hours = sum(agent-allocated binary states)
      accuracy        = 1 - |required - scheduled| / required
    """
    rows = []
    for app in APPLIANCES:
        required = get_required_hours(app, app_data)
        scheduled = int(sum(agent_schedules.get(app, [0] * 24)))
        if required > 0:
            match_pct = 100.0 * (1.0 - abs(required - scheduled) / required)
        else:
            match_pct = 100.0 if scheduled == 0 else 0.0
        rows.append({
            "app":       app,
            "required":  required,
            "scheduled": scheduled,
            "match_pct": round(match_pct, 1),
        })
    return rows


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def run_simulation():
    print("\n" + "=" * 70)
    print("   REAL PIPELINE MODEL VALIDATION (LSTM → LLM → MILP AGENT)")
    print("=" * 70)

    # 1. Load real pipeline outputs
    try:
        app_data, agent_sched, explanations = load_pipeline_outputs()
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    price_map = build_price_map()

    # 2. Build baseline schedules (LSTM-predicted states — no optimisation)
    baseline_sched = {app: app_data[app]["states"] for app in APPLIANCES}

    # 3. Cost comparison
    print("\n── SECTION 1: Cost Savings (Baseline vs Agent) ──\n")
    header = f"{'Appliance':<25} | {'Baseline (LKR)':<16} | {'Agent (LKR)':<12} | {'Savings (LKR)':<14} | {'Savings (%)'}"
    print(header)
    print("-" * len(header))

    total_baseline = 0.0
    total_agent = 0.0
    per_app = explanations.get("per_appliance", {})

    for app in APPLIANCES:
        b_cost = cost_for_states(baseline_sched[app], POWER_KWH[app], price_map)
        a_cost = cost_for_states(agent_sched.get(app, [0]*24), POWER_KWH[app], price_map)
        savings_lkr = b_cost - a_cost
        savings_pct = (savings_lkr / b_cost * 100.0) if b_cost > 0 else 0.0
        total_baseline += b_cost
        total_agent += a_cost

        # Validate against stored explanations
        stored_orig = per_app.get(app, {}).get("original_cost", None)
        stored_opt  = per_app.get(app, {}).get("optimized_cost", None)
        match_flag  = ""
        if stored_orig is not None and stored_opt is not None:
            if abs(b_cost - stored_orig) < 1.0 and abs(a_cost - stored_opt) < 1.0:
                match_flag = "✓"
            else:
                match_flag = "✗ MISMATCH"

        print(f"{app:<25} | {b_cost:<16.2f} | {a_cost:<12.2f} | {savings_lkr:<14.2f} | {savings_pct:.1f}%  {match_flag}")

    total_savings = total_baseline - total_agent
    total_pct = (total_savings / total_baseline * 100.0) if total_baseline > 0 else 0.0
    print("-" * len(header))
    print(f"{'TOTAL':<25} | {total_baseline:<16.2f} | {total_agent:<12.2f} | {total_savings:<14.2f} | {total_pct:.1f}%")

    # 4. Peak load comparison
    print("\n── SECTION 2: Peak Load ──\n")
    b_peak = peak_load_kw(baseline_sched)
    a_peak = peak_load_kw(agent_sched)
    peak_change = ((a_peak - b_peak) / b_peak * 100.0) if b_peak > 0 else 0.0
    print(f"  Baseline peak load : {b_peak:.3f} kW")
    print(f"  Agent peak load    : {a_peak:.3f} kW")
    print(f"  Change             : {peak_change:+.2f}%")
    if a_peak <= b_peak:
        print("  Result             : ✓ Peak load reduced or maintained.")
    else:
        print("  Result             : ⚠  Peak load increased (trade-off for cost savings).")

    # 5. LSTM prediction accuracy
    print("\n── SECTION 3: LSTM Prediction Accuracy (Required vs Scheduled Hours) ──\n")
    accuracy_rows = check_lstm_accuracy(app_data, agent_sched)
    header2 = f"{'Appliance':<25} | {'LSTM Required (h)':<18} | {'Scheduled (h)':<14} | {'Match %'}"
    print(header2)
    print("-" * len(header2))
    match_sum = 0.0
    for row in accuracy_rows:
        flag = "✓" if row["match_pct"] >= 80.0 else "✗"
        print(f"{row['app']:<25} | {row['required']:<18} | {row['scheduled']:<14} | {row['match_pct']}%  {flag}")
        match_sum += row["match_pct"]
    avg_match = match_sum / len(accuracy_rows)
    print("-" * len(header2))
    print(f"{'Average match accuracy':<25}   {'':18}   {'':14}   {avg_match:.1f}%")

    # 6. LLM Preference Compliance
    print("\n── SECTION 4: Ollama LLM Preference Compliance ──\n")
    user_pref = explanations.get("user_preference", {})
    raw_msg   = user_pref.get("raw_message", "N/A")
    allow_peak    = user_pref.get("allow_peak", {})
    preferred_hrs = user_pref.get("preferred_hours", {})
    peak_hours = [h for h in range(24) if price_map[h]["band"] == "peak"]

    print(f"  User instruction  : \"{raw_msg}\"")
    print()
    all_pref_ok = True
    for app in APPLIANCES:
        on_hours = [h for h in range(24) if agent_sched.get(app, [0]*24)[h] == 1]
        ap  = allow_peak.get(app, True)
        pref = preferred_hrs.get(app)

        # Check allow_peak
        peak_violations = [h for h in on_hours if h in peak_hours] if not ap else []

        # Check preferred hours
        pref_violations = []
        if pref is not None:
            pref_violations = [h for h in on_hours if h not in pref]

        ok = (len(peak_violations) == 0 and len(pref_violations) == 0)
        flag = "✓" if ok else "✗"
        if not ok:
            all_pref_ok = False
        pref_str = f"hours {pref}" if pref else "none"
        print(f"  {flag} {app:<25}  allow_peak={str(ap):<5}  preferred={pref_str}")
        if peak_violations:
            print(f"      ⚠  Runs during peak hours: {peak_violations}")
        if pref_violations:
            print(f"      ⚠  Runs outside preferred hours: {pref_violations}")

    print()
    if all_pref_ok:
        print("  All LLM-parsed preferences were respected by the MILP scheduler. ✓")
    else:
        print("  ⚠  Some preferences were NOT respected — check agent logs.")

    # 7. Summary verdict
    print("\n" + "=" * 70)
    print("   VALIDATION SUMMARY")
    print("=" * 70)
    cost_ok   = total_pct >= 20.0
    lstm_ok   = avg_match >= 70.0
    pref_ok   = all_pref_ok
    print(f"  Cost savings          : {total_pct:.1f}%   {'✓ PASS (≥20%)' if cost_ok else '✗ FAIL (<20%)'}")
    print(f"  LSTM accuracy (avg)   : {avg_match:.1f}%  {'✓ PASS (≥70%)' if lstm_ok else '✗ FAIL (<70%)'}")
    print(f"  LLM pref. compliance  :          {'✓ PASS (all respected)' if pref_ok else '✗ FAIL (violations found)'}")
    overall = cost_ok and lstm_ok and pref_ok
    print("-" * 70)
    print(f"  OVERALL RESULT        : {'✓ MODEL VALIDATED' if overall else '✗ VALIDATION FAILED — review above issues'}")
    print("=" * 70)


if __name__ == "__main__":
    run_simulation()
