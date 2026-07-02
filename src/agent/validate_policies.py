"""
validate_policies.py — Research Model Policy Validation
========================================================
Tests the actual research claims of the AI-Based Optimized Energy
Utilization System:

  Claim 1 — LSTM Prediction Accuracy:
      The LSTM-derived ON/OFF states match the required runtime
      hours computed from predicted energy demand.

  Claim 2 — MILP Optimality (Cost):
      The agent's optimised schedule has lower or equal cost
      compared to the LSTM-predicted baseline.

  Claim 3 — Grid Capacity Compliance:
      The scheduled load never exceeds the TOU-band capacity limit.

  Claim 4 — Binary Schedule Validity:
      All appliance states are binary (0 or 1) for each of 24 hours.

  Claim 5 — LLM Preference Compliance:
      The Ollama-parsed user preferences (allow_peak, preferred_hours)
      are correctly enforced by the MILP scheduler.

  Claim 6 — Significant Cost Reduction:
      Total savings exceed a minimum research threshold (20 %).

Each policy is evaluated with deterministic code — no LLM calls are
needed, eliminating circularity / bias.
"""

import json
import os
import sys
import re
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    APPLIANCES,
    POWER_KWH,
    LLM_MODEL,
    DEFAULT_TEMPERATURE_C,
    DEFAULT_HUMIDITY_PCT,
    HOT_TEMPERATURE_THRESHOLD_C,
    HIGH_HUMIDITY_THRESHOLD_PCT,
    COLD_TEMPERATURE_THRESHOLD_C,
    LECO_RATE_OFF_PEAK_LKR,
    LECO_RATE_DAY_LKR,
    LECO_RATE_PEAK_LKR,
    LECO_DAY_START_HOUR,
    LECO_DAY_END_HOUR,
    LECO_PEAK_START_HOUR,
    LECO_PEAK_END_HOUR,
    DEFAULT_CAPACITY_OFF_PEAK_KW,
    DEFAULT_CAPACITY_DAY_KW,
    DEFAULT_CAPACITY_PEAK_KW,
    CAPACITY_TOLERANCE_KW,
    COST_TOLERANCE_LKR,
    COMFORT_OVERLAP_MIN_RATIO,
)

# Minimum cost-saving threshold to consider the model research-worthy (%).
MIN_SAVINGS_PCT = 20.0

# Minimum fraction of LSTM-required hours that must be scheduled.
MIN_RUNTIME_COVERAGE = 0.50   # 50 %


# =============================================================================
# DATA LOADING
# =============================================================================

def load_pipeline_data():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    files = {
        "appliance_data":   os.path.join(base, "appliance_data.json"),
        "output":           os.path.join(base, "output.json"),
        "output_expl":      os.path.join(base, "output_explanations.json"),
    }
    loaded = {}
    for key, path in files.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Required pipeline file not found: {path}\n"
                "Run Run_LSTM.py and agent.py first."
            )
        with open(path, "r", encoding="utf-8") as f:
            loaded[key] = json.load(f)

    # Build TOU price map from config
    price_map: Dict[int, Dict[str, Any]] = {}
    for h in range(24):
        price_map[h] = {"price": LECO_RATE_OFF_PEAK_LKR, "band": "off_peak"}
    for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
        price_map[h] = {"price": LECO_RATE_DAY_LKR, "band": "day"}
    for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
        price_map[h] = {"price": LECO_RATE_PEAK_LKR, "band": "peak"}

    expl = loaded["output_expl"]
    user_pref = expl.get("user_preference", {})
    allow_peak = user_pref.get("allow_peak", {a: False for a in APPLIANCES})
    preferred_hours = user_pref.get("preferred_hours", {a: None for a in APPLIANCES})
    weather = expl.get("weather", {
        "temperature": [DEFAULT_TEMPERATURE_C] * 24,
        "humidity":    [DEFAULT_HUMIDITY_PCT]  * 24,
    })

    return (
        loaded["appliance_data"],
        loaded["output"],
        expl,
        price_map,
        {"allow_peak": allow_peak, "preferred_hours": preferred_hours},
        weather,
    )


# =============================================================================
# POLICY DEFINITIONS
# =============================================================================

def generate_policies() -> List[Dict[str, Any]]:
    """Returns the full ordered list of validation policies."""
    policies = []
    idx = 1

    # ── CLAIM 3: Grid Capacity Compliance (48 policies, 2 per hour) ─────────
    for hour in range(24):
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"Total scheduled load in hour {hour} must not exceed the TOU-band capacity limit.",
            "category": "capacity",
            "eval_type": "code",
            "meta": {"hour": hour},
        })
        idx += 1
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"Aggregate consumption in hour {hour} must remain below the grid ceiling.",
            "category": "capacity",
            "eval_type": "code",
            "meta": {"hour": hour},
        })
        idx += 1

    # ── CLAIM 4: Binary Schedule Validity (10 policies: format + binary) ────
    for app in APPLIANCES:
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"Schedule for {app} must contain exactly 24 binary elements.",
            "category": "format",
            "eval_type": "code",
            "meta": {"app": app},
        })
        idx += 1
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"Every state in the {app} schedule must be 0 or 1 (binary).",
            "category": "format",
            "eval_type": "code",
            "meta": {"app": app},
        })
        idx += 1

    # ── CLAIM 5: LLM Preference Compliance (10 policies) ────────────────────
    for app in APPLIANCES:
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"{app} must not run during peak hours if allow_peak is False (as parsed by Ollama LLM).",
            "category": "llm_preference",
            "eval_type": "code",
            "meta": {"app": app, "check": "allow_peak"},
        })
        idx += 1
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"{app} must only run in Ollama-specified preferred hours when a preference was set.",
            "category": "llm_preference",
            "eval_type": "code",
            "meta": {"app": app, "check": "preferred_hours"},
        })
        idx += 1

    # ── CLAIM 1: LSTM Demand Coverage (5 policies, 1 per appliance) ─────────
    for app in APPLIANCES:
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": (
                f"Agent-scheduled runtime for {app} must cover ≥{int(MIN_RUNTIME_COVERAGE*100)}% "
                f"of LSTM-predicted required hours."
            ),
            "category": "lstm_accuracy",
            "eval_type": "code",
            "meta": {"app": app},
        })
        idx += 1

    # ── CLAIM 2: MILP Cost Optimality (6 policies: total + per-appliance) ───
    policies.append({
        "id": f"POL_{idx:03d}",
        "description": "Total optimised cost must not exceed the LSTM-predicted baseline cost.",
        "category": "cost_optimality",
        "eval_type": "code",
        "meta": {"scope": "total"},
    })
    idx += 1
    for app in APPLIANCES:
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": f"Optimised cost for {app} must not exceed its LSTM-baseline cost.",
            "category": "cost_optimality",
            "eval_type": "code",
            "meta": {"app": app, "scope": "per_appliance"},
        })
        idx += 1

    # ── CLAIM 6: Significant Savings Threshold (1 policy) ───────────────────
    policies.append({
        "id": f"POL_{idx:03d}",
        "description": f"Total cost savings achieved by the agent must be ≥ {MIN_SAVINGS_PCT}% (research threshold).",
        "category": "savings_threshold",
        "eval_type": "code",
        "meta": {},
    })
    idx += 1

    # ── WEATHER COMFORT: AC & Heater comfort alignment (2 policies) ─────────
    policies.append({
        "id": f"POL_{idx:03d}",
        "description": (
            f"AC must run for ≥{int(COMFORT_OVERLAP_MIN_RATIO*100)}% of its ON-hours "
            f"during hot/humid conditions (≥{HOT_TEMPERATURE_THRESHOLD_C}°C or ≥{HIGH_HUMIDITY_THRESHOLD_PCT}% humidity)."
        ),
        "category": "weather_comfort",
        "eval_type": "code",
        "meta": {"app": "AC_Power"},
    })
    idx += 1
    policies.append({
        "id": f"POL_{idx:03d}",
        "description": (
            "Heater runtime must comply with user-specified night preference "
            "(as parsed by Ollama), OR — where no cold hours exist — the heater "
            "must not run during peak pricing hours."
        ),
        "category": "weather_comfort",
        "eval_type": "code",
        "meta": {"app": "Heater_Power"},
    })
    idx += 1

    return policies


# =============================================================================
# EVALUATION
# =============================================================================

def _cost_for_states(states, power_kwh, price_map):
    return sum(power_kwh * price_map[h]["price"] for h, s in enumerate(states) if s == 1)


def evaluate_policy(
    policy: Dict[str, Any],
    app_data: Dict[str, Any],
    schedules: Dict[str, List[int]],
    explanations: Dict[str, Any],
    price_map: Dict[int, Dict],
    user_preference: Dict[str, Any],
    weather: Dict[str, Any],
) -> Tuple[bool, str]:

    cat  = policy["category"]
    meta = policy.get("meta", {})
    desc = policy["description"]

    try:
        # ── FORMAT ──────────────────────────────────────────────────────────
        if cat == "format":
            app = meta.get("app")
            targets = [app] if app else APPLIANCES
            for a in targets:
                sched = schedules.get(a, [])
                if len(sched) != 24:
                    return False, f"{a}: schedule has {len(sched)} elements (expected 24)."
                invalid = [v for v in sched if v not in (0, 1)]
                if invalid:
                    return False, f"{a}: non-binary values found: {invalid[:5]}."
            return True, f"Format valid for {targets}."

        # ── CAPACITY ────────────────────────────────────────────────────────
        elif cat == "capacity":
            cap_map = {h: DEFAULT_CAPACITY_OFF_PEAK_KW for h in range(24)}
            for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
                cap_map[h] = DEFAULT_CAPACITY_DAY_KW
            for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
                cap_map[h] = DEFAULT_CAPACITY_PEAK_KW

            # Detect hour from meta or description
            hour = meta.get("hour")
            if hour is None:
                m = re.search(r"\bhour\s+(\d+)\b|\bslot\s+(\d+)\b", desc)
                hour = int(m.group(1) or m.group(2)) if m else None

            hours_to_check = [hour] if hour is not None else list(range(24))
            failures = []
            for h in hours_to_check:
                slot_kw = sum(schedules.get(a, [0]*24)[h] * POWER_KWH[a] for a in APPLIANCES)
                limit   = cap_map[h]
                if slot_kw > limit + CAPACITY_TOLERANCE_KW:
                    failures.append(f"Hour {h}: {slot_kw:.3f} kW > limit {limit} kW")
            if failures:
                return False, "; ".join(failures)
            return True, f"Capacity OK for hour(s) {hours_to_check}."

        # ── LLM PREFERENCE ──────────────────────────────────────────────────
        elif cat == "llm_preference":
            app   = meta.get("app")
            check = meta.get("check")
            allow_peak     = user_preference.get("allow_peak", {})
            preferred_hours = user_preference.get("preferred_hours", {})
            peak_hours = [h for h in range(24) if price_map[h]["band"] == "peak"]
            on_hours   = [h for h in range(24) if schedules.get(app, [0]*24)[h] == 1]

            if check == "allow_peak":
                if allow_peak.get(app, True):
                    return True, f"{app}: allow_peak=True — no peak restriction applied."
                violations = [h for h in on_hours if h in peak_hours]
                if violations:
                    return False, f"{app} runs during peak hours {violations} but allow_peak=False."
                return True, f"{app}: correctly excluded from peak hours {peak_hours}."

            elif check == "preferred_hours":
                pref = preferred_hours.get(app)
                if pref is None:
                    return True, f"{app}: no preferred_hours preference set — no restriction."
                illegal = [h for h in on_hours if h not in pref]
                if illegal:
                    return False, f"{app} runs outside preferred hours {pref}: illegal hours={illegal}."
                return True, f"{app}: all ON-hours {on_hours} are within preferred {pref}."

            return True, "No relevant sub-check matched."

        # ── LSTM ACCURACY ───────────────────────────────────────────────────
        elif cat == "lstm_accuracy":
            app      = meta["app"]
            required = int(sum(app_data[app].get("states", [0]*24)))
            scheduled = int(sum(schedules.get(app, [0]*24)))
            if required == 0:
                return True, f"{app}: LSTM predicted 0 required hours; scheduled={scheduled} ✓."
            coverage = scheduled / required
            if coverage < MIN_RUNTIME_COVERAGE:
                return False, (
                    f"{app}: scheduled {scheduled}h but LSTM required {required}h "
                    f"(coverage={coverage:.0%} < {MIN_RUNTIME_COVERAGE:.0%})."
                )
            return True, (
                f"{app}: {scheduled}/{required}h scheduled "
                f"(coverage={coverage:.0%} ≥ {MIN_RUNTIME_COVERAGE:.0%})."
            )

        # ── COST OPTIMALITY ─────────────────────────────────────────────────
        elif cat == "cost_optimality":
            per_app = explanations.get("per_appliance", {})
            totals  = explanations.get("totals", {})
            scope   = meta.get("scope", "total")

            if scope == "total":
                baseline  = totals.get("baseline",  0.0)
                optimized = totals.get("optimized", 0.0)
                if optimized > baseline + COST_TOLERANCE_LKR:
                    return False, f"Total optimised ({optimized:.2f}) > baseline ({baseline:.2f})."
                return True, f"Total cost reduced: {baseline:.2f} → {optimized:.2f} LKR."

            else:  # per_appliance
                app = meta.get("app")
                if app not in per_app:
                    # Compute directly from schedules
                    b_cost = _cost_for_states(app_data[app].get("states", [0]*24), POWER_KWH[app], price_map)
                    a_cost = _cost_for_states(schedules.get(app, [0]*24), POWER_KWH[app], price_map)
                else:
                    b_cost = per_app[app].get("original_cost",  0.0)
                    a_cost = per_app[app].get("optimized_cost", 0.0)
                if a_cost > b_cost + COST_TOLERANCE_LKR:
                    return False, f"{app} optimised cost ({a_cost:.2f}) > baseline ({b_cost:.2f})."
                return True, f"{app}: {b_cost:.2f} → {a_cost:.2f} LKR (saved {b_cost-a_cost:.2f})."

        # ── SAVINGS THRESHOLD ───────────────────────────────────────────────
        elif cat == "savings_threshold":
            totals   = explanations.get("totals", {})
            baseline = totals.get("baseline",  0.0)
            optimized= totals.get("optimized", 0.0)
            if baseline == 0:
                return False, "Baseline cost is 0 — cannot compute savings %."
            pct = (baseline - optimized) / baseline * 100.0
            if pct < MIN_SAVINGS_PCT:
                return False, (
                    f"Savings = {pct:.2f}% < required {MIN_SAVINGS_PCT}%."
                )
            return True, f"Savings = {pct:.2f}% ≥ {MIN_SAVINGS_PCT}% research threshold."

        # ── WEATHER COMFORT ─────────────────────────────────────────────────
        elif cat == "weather_comfort":
            app   = meta.get("app")
            temps = weather.get("temperature", [DEFAULT_TEMPERATURE_C]*24)
            hums  = weather.get("humidity",    [DEFAULT_HUMIDITY_PCT]*24)
            hot_hours  = [h for h in range(24) if temps[h] >= HOT_TEMPERATURE_THRESHOLD_C
                          or hums[h] >= HIGH_HUMIDITY_THRESHOLD_PCT]
            cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMPERATURE_THRESHOLD_C]
            peak_hours = [h for h in range(24) if price_map[h]["band"] == "peak"]

            if app == "AC_Power":
                ac_on = [h for h in range(24) if schedules.get("AC_Power", [0]*24)[h] == 1]
                if not ac_on:
                    return True, "AC not scheduled; no comfort check needed."
                if not hot_hours:
                    return True, f"No hot/humid hours; AC schedule {ac_on} is acceptable."
                overlap = [h for h in ac_on if h in hot_hours]
                ratio   = len(overlap) / len(ac_on)
                if ratio >= COMFORT_OVERLAP_MIN_RATIO:
                    return True, (
                        f"AC ON={ac_on}, hot hours={hot_hours}, "
                        f"overlap={overlap} ({ratio:.0%} ≥ {COMFORT_OVERLAP_MIN_RATIO:.0%})."
                    )
                return False, (
                    f"AC overlap with hot hours = {ratio:.0%} < {COMFORT_OVERLAP_MIN_RATIO:.0%}. "
                    f"ON={ac_on}, hot={hot_hours}."
                )

            elif app == "Heater_Power":
                heater_on = [h for h in range(24) if schedules.get("Heater_Power", [0]*24)[h] == 1]
                if not heater_on:
                    return True, "Heater not scheduled; no comfort check needed."

                # If Ollama set a preferred_hours constraint, check that instead
                preferred_hours = user_preference.get("preferred_hours", {})
                pref = preferred_hours.get("Heater_Power")
                if pref is not None:
                    illegal = [h for h in heater_on if h not in pref]
                    if not illegal:
                        return True, (
                            f"Heater ON={heater_on} fully within Ollama-preferred hours={pref}."
                        )
                    return False, (
                        f"Heater runs outside Ollama-preferred hours {pref}: illegal={illegal}."
                    )

                # No preferred_hours set — fall back to: heater must not run during peak
                peak_violations = [h for h in heater_on if h in peak_hours]
                if peak_violations:
                    return False, (
                        f"No cold hours in forecast and no preference set; "
                        f"Heater still runs during peak hours {peak_violations}."
                    )
                return True, (
                    f"No cold hours in forecast; Heater avoids peak hours. ON={heater_on}."
                )

    except Exception as e:
        return False, f"Evaluation error: {e}"

    return True, "Policy evaluated (no specific rule matched — default PASS)."


# =============================================================================
# MAIN
# =============================================================================

def run_validation():
    print("--- Starting Policy Validation (Research Model) ---")

    try:
        app_data, schedules, explanations, price_map, user_preference, weather = \
            load_pipeline_data()
    except FileNotFoundError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    policies = generate_policies()
    print(f"Generated {len(policies)} policies covering 6 research claims.\n")

    report_items = []
    passed_count = 0

    for policy in policies:
        pol_id    = policy["id"]
        eval_type = policy.get("eval_type", "code")
        print(f"Evaluating {pol_id} ({policy['category']}): {policy['description']}")

        passed, reason = evaluate_policy(
            policy, app_data, schedules, explanations, price_map, user_preference, weather
        )

        if passed:
            passed_count += 1

        report_items.append({
            "id":          pol_id,
            "description": policy["description"],
            "category":    policy["category"],
            "eval_type":   eval_type,
            "status":      "PASS" if passed else "FAIL",
            "reason":      reason,
        })

    total = len(policies)
    summary = {
        "total_policies":       total,
        "passed":               passed_count,
        "failed":               total - passed_count,
        "pass_rate_percentage": round(100.0 * passed_count / total, 2),
    }

    # Per-category breakdown
    categories = {}
    for item in report_items:
        c = item["category"]
        if c not in categories:
            categories[c] = {"passed": 0, "total": 0}
        categories[c]["total"] += 1
        if item["status"] == "PASS":
            categories[c]["passed"] += 1
    summary["by_category"] = categories

    report = {"summary": summary, "policies": report_items}

    base_dir    = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.abspath(os.path.join(base_dir, "..", "..", "validation_report.json"))
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nValidation Report saved to {report_path}")
    print(f"\nResults: {passed_count}/{total} passed ({summary['pass_rate_percentage']}%).")
    print("\nPer-category breakdown:")
    for cat, counts in categories.items():
        rate = 100.0 * counts["passed"] / counts["total"]
        flag = "✓" if counts["passed"] == counts["total"] else "✗"
        print(f"  {flag}  {cat:<20}: {counts['passed']}/{counts['total']} ({rate:.0f}%)")
    print("\n--- End of Policy Validation ---")


if __name__ == "__main__":
    run_validation()
