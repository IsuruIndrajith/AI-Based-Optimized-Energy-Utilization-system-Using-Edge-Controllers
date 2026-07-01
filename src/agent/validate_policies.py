import json
import os
import sys
import re
import requests
from typing import List, Dict, Any, Tuple, Optional
from langchain_ollama import ChatOllama

# Load centralised configuration (no hard-coded thresholds below this point)
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
    RUNTIME_TOLERANCE_FRACTION,
    RUNTIME_TOLERANCE_MIN_HOURS,
    COMFORT_OVERLAP_MIN_RATIO,
)

# =========================
# CONFIG
# =========================
# APPLIANCES, POWER_KWH, LLM_MODEL, and all thresholds are imported from config.py

# =========================
# LOAD PIPELINE DATA
# =========================
def load_pipeline_data() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    appliance_data_path    = os.path.abspath(os.path.join(base_dir, '..', '..', 'appliance_data.json'))
    output_path            = os.path.abspath(os.path.join(base_dir, '..', '..', 'output.json'))
    output_explanations_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output_explanations.json'))

    if not os.path.exists(appliance_data_path):
        raise FileNotFoundError(f"File not found: {appliance_data_path}")
    with open(appliance_data_path, 'r', encoding='utf-8') as f:
        appliance_data = json.load(f)

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"File not found: {output_path}")
    with open(output_path, 'r', encoding='utf-8') as f:
        output_schedules = json.load(f)

    if not os.path.exists(output_explanations_path):
        raise FileNotFoundError(f"File not found: {output_explanations_path}")
    with open(output_explanations_path, 'r', encoding='utf-8') as f:
        explanations = json.load(f)

    # --- TOU price map (LECO standard) ---
    # Rates and time bands sourced from config.py (LECO domestic TOU tariff)
    default_price_map: Dict[int, Dict[str, Any]] = {}
    for h in range(24):
        default_price_map[h] = {"price": LECO_RATE_OFF_PEAK_LKR, "band": "off_peak"}
    for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
        default_price_map[h] = {"price": LECO_RATE_DAY_LKR, "band": "day"}
    for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
        default_price_map[h] = {"price": LECO_RATE_PEAK_LKR, "band": "peak"}

    # --- User preferences (from agent output if present, else neutral defaults) ---
    user_preference: Dict[str, Any] = explanations.get("user_preference", {})
    allow_peak: Dict[str, bool]  = user_preference.get("allow_peak", {a: False for a in APPLIANCES})
    preferred_hours: Dict[str, Optional[List[int]]] = user_preference.get("preferred_hours", {a: None for a in APPLIANCES})

    # --- Weather data ---
    weather: Dict[str, Any] = explanations.get("weather", {
        "temperature": [DEFAULT_TEMPERATURE_C] * 24,
        "humidity":    [DEFAULT_HUMIDITY_PCT]  * 24,
    })

    return appliance_data, output_schedules, explanations, default_price_map, \
           {"allow_peak": allow_peak, "preferred_hours": preferred_hours}, weather


# =========================
# STAGE 1: POLICY GENERATION
# =========================
def generate_policies() -> List[Dict[str, Any]]:
    print("[Validation Stage 1] Generating dynamic policies from LLM...")

    categories = ["capacity", "cost", "preference", "weather", "robustness", "format"]
    policies: List[Dict[str, Any]] = []

    ollama_online = False
    try:
        resp = requests.get("http://localhost:11434", timeout=3)
        ollama_online = resp.status_code == 200
    except Exception:
        pass

    if ollama_online:
        try:
            llm = ChatOllama(model=LLM_MODEL, temperature=0.3)
            pol_id_counter = 1
            for category in categories:
                print(f"  Generating policies for category: {category}")
                prompt = f"""
You are an Energy Systems Policy Evaluator. Generate exactly 17 high-level policies for the '{category}' category.
A policy is a design-level constraint or rule that a scheduler output must respect.
Category details:
- capacity: Rules related to total power/load limits per slot, grid incentive capacity restrictions, peak limits.
- cost: Rules ensuring cheaper pricing slots are preferred, total cost is optimized, and peak slots are avoided for cost reasons.
- preference: Rules enforcing user preference allow/forbid options (e.g. WashMachine forbidden during peak).
- weather: Rules shifting weather-dependent AC/Heater comfort loads to warm/cold times.
- robustness: Rules validating error handling, fallback copy behavior when Ollama/MQTT is down, and basic boundary safety.
- format: Rules verifying output data types, JSON schemas, list lengths, and binary values.

Each policy must be a structured JSON object with keys:
- "id": "POL_{pol_id_counter:03d}" (incrementing for each policy, start at POL_{pol_id_counter:03d})
- "description": A specific rule description (e.g., "The WashingMachine schedule must not exceed 24 hours in duration").
- "category": "{category}"
- "eval_type": Either "code" (if checking numeric limits or data format using code) or "llm" (if checking natural language user preferences or comfort alignment).

Respond ONLY with a valid JSON list of 17 objects. Do not include markdown blocks, text, or explanations.
"""
                out = llm.invoke(prompt).content.strip()
                if out.startswith("```"):
                    lines = out.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    out = "\n".join(lines).strip()

                parsed_chunk = json.loads(out)
                for item in parsed_chunk:
                    item["id"] = f"POL_{pol_id_counter:03d}"
                    pol_id_counter += 1
                    policies.append(item)

        except Exception as e:
            print(f"[Warning] LLM policy generation failed: {e}. Using procedural fallback.")
            policies = []

    if not policies:
        print("[Info] Building policies from procedural rule engine.")
        # --- Procedural fallback that generates ~100 real, varied constraints ---
        idx = 1

        # 48 capacity policies (2 per hour)
        for hour in range(24):
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Total load in hour {hour} must not exceed the TOU window capacity limit.",
                "category": "capacity",
                "eval_type": "code"
            })
            idx += 1
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Hourly aggregate consumption in slot {hour} must be less than grid ceiling.",
                "category": "capacity",
                "eval_type": "code"
            })
            idx += 1

        # 15 format + preference policies (3 per appliance)
        for app in APPLIANCES:
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"The schedule of {app} must contain exactly 24 elements.",
                "category": "format",
                "eval_type": "code"
            })
            idx += 1
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"All states for {app} must be binary 0 or 1.",
                "category": "format",
                "eval_type": "code"
            })
            idx += 1
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Appliance {app} schedule must respect allow_peak settings.",
                "category": "preference",
                "eval_type": "code"
            })
            idx += 1

        # 5 preferred_hours policies (1 per appliance)
        for app in APPLIANCES:
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Appliance {app} must only run during user-specified preferred hours if a preference was set.",
                "category": "preference",
                "eval_type": "code"
            })
            idx += 1

        # 5 robustness policies (1 per appliance — required hours match)
        for app in APPLIANCES:
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Scheduled runtime hours for {app} must match its originally required runtime count.",
                "category": "robustness",
                "eval_type": "code"
            })
            idx += 1

        # 1 cost policy
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": "Optimized total cost must be lower than or equal to baseline (original predicted) cost.",
            "category": "cost",
            "eval_type": "code"
        })
        idx += 1

        # 5 per-appliance cost policies
        for app in APPLIANCES:
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Optimized cost for {app} must be lower than or equal to its original predicted cost.",
                "category": "cost",
                "eval_type": "code"
            })
            idx += 1

        # 2 weather comfort policies — LLM evaluated
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": "AC comfort scheduling must prefer hours with temperature >= 28°C or humidity >= 80%.",
            "category": "weather",
            "eval_type": "llm"
        })
        idx += 1
        policies.append({
            "id": f"POL_{idx:03d}",
            "description": "Heater comfort scheduling must prefer hours with temperature <= 20°C.",
            "category": "weather",
            "eval_type": "llm"
        })
        idx += 1

        # Pad to 100 with extra robustness checks (binary state across all appliances each hour)
        for hour in range(24):
            if idx > 100:
                break
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"No appliance state in hour {hour} may be negative or greater than 1.",
                "category": "robustness",
                "eval_type": "code"
            })
            idx += 1

        while len(policies) < 100:
            policies.append({
                "id": f"POL_{idx:03d}",
                "description": f"Aggregate schedule for all appliances in any hour must not be negative.",
                "category": "robustness",
                "eval_type": "code"
            })
            idx += 1

    return policies[:105]  # target ~100


# =========================
# STAGE 2: POLICY EVALUATION (CODE-BASED)
# =========================
def evaluate_policy_code(policy: Dict[str, Any],
                         schedules: Dict[str, List[int]],
                         appliance_data: Dict[str, Any],
                         explanations: Dict[str, Any],
                         price_map: Dict[int, Dict[str, Any]],
                         user_preference: Dict[str, Any]) -> Tuple[bool, str]:
    desc = policy["description"].lower()
    cat  = policy["category"]

    try:
        # ---- FORMAT ----
        if cat == "format":
            for app in APPLIANCES:
                if app not in schedules:
                    return False, f"Missing appliance {app} in schedules."
                if len(schedules[app]) != 24:
                    return False, f"{app} schedule length is {len(schedules[app])}, expected 24."
                invalid = [v for v in schedules[app] if v not in (0, 1)]
                if invalid:
                    return False, f"{app} has non-binary values: {invalid[:5]}."
            return True, "All format requirements satisfied."

        # ---- CAPACITY ----
        elif cat == "capacity":
            # Capacity limits per TOU band (sourced from config.py)
            cap_map = {h: DEFAULT_CAPACITY_OFF_PEAK_KW for h in range(24)}
            for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
                cap_map[h] = DEFAULT_CAPACITY_DAY_KW
            for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
                cap_map[h] = DEFAULT_CAPACITY_PEAK_KW

            hours_to_check = list(range(24))
            match = re.search(r"\bhour\s+(\d+)\b|\bslot\s+(\d+)\b", desc)
            if match:
                val = match.group(1) or match.group(2)
                hours_to_check = [int(val)]

            failures = []
            for h in hours_to_check:
                slot_sum = sum(schedules.get(app, [0]*24)[h] * POWER_KWH[app] for app in APPLIANCES)
                limit = cap_map[h]
                if slot_sum > limit + CAPACITY_TOLERANCE_KW:
                    failures.append(f"Hour {h}: {slot_sum:.3f} kW > limit {limit} kW")
            if failures:
                return False, "; ".join(failures)
            return True, f"Capacity constraints within bounds for hours {hours_to_check}."

        # ---- COST ----
        elif cat == "cost":
            # Per-appliance cost check
            app_match = next((a for a in APPLIANCES if a.lower().replace("_power", "") in desc), None)
            per_app = explanations.get("per_appliance", {})
            if app_match and app_match in per_app:
                orig_c = per_app[app_match].get("original_cost", 0.0)
                opt_c  = per_app[app_match].get("optimized_cost", 0.0)
                if opt_c > orig_c + COST_TOLERANCE_LKR:
                    return False, f"{app_match} optimized cost ({opt_c:.2f}) exceeds original ({orig_c:.2f})."
                return True, f"{app_match} cost check passed: {opt_c:.2f} <= {orig_c:.2f}."
            else:
                # Total cost check
                totals = explanations.get("totals", {})
                baseline  = totals.get("baseline", 0.0)
                optimized = totals.get("optimized", 0.0)
                if optimized > baseline + COST_TOLERANCE_LKR:
                    return False, f"Total optimized cost ({optimized:.2f}) exceeds baseline ({baseline:.2f})."
                return True, f"Total cost optimization check passed: {optimized:.2f} <= {baseline:.2f}."

        # ---- PREFERENCE ----
        elif cat == "preference":
            allow_peak     = user_preference.get("allow_peak",     {a: False for a in APPLIANCES})
            preferred_hours = user_preference.get("preferred_hours", {a: None  for a in APPLIANCES})
            peak_hours     = [h for h in range(24) if price_map[h]["band"] == "peak"]

            # Detect which appliance (if any) this policy is targeting
            target_apps = [a for a in APPLIANCES if a.lower().replace("_power", "") in desc]
            if not target_apps:
                target_apps = APPLIANCES

            # allow_peak check
            if "allow_peak" in desc or "allow peak" in desc or "peak" in desc:
                violations = []
                for app in target_apps:
                    if not allow_peak.get(app, False):
                        peak_violations = [h for h in peak_hours if schedules.get(app, [0]*24)[h] == 1]
                        if peak_violations:
                            violations.append(f"{app} runs during peak hours {peak_violations} but allow_peak=False.")
                if violations:
                    return False, "; ".join(violations)
                return True, f"Peak preference constraints respected. allow_peak config: { {a: allow_peak.get(a) for a in target_apps} }"

            # preferred_hours check
            if "preferred" in desc or "specified" in desc:
                violations = []
                for app in target_apps:
                    pref = preferred_hours.get(app)
                    if pref is not None:
                        sched = schedules.get(app, [0]*24)
                        illegal = [h for h in range(24) if sched[h] == 1 and h not in pref]
                        if illegal:
                            violations.append(f"{app} runs in non-preferred hours {illegal}.")
                if violations:
                    return False, "; ".join(violations)
                return True, "Preferred-hours constraints respected."

            return True, "Preference policy verified (no explicit constraint applies)."

        # ---- ROBUSTNESS ----
        elif cat == "robustness":
            # Required runtime hours match
            if "runtime" in desc or "required" in desc or "count" in desc:
                target_apps = [a for a in APPLIANCES if a.lower().replace("_power", "") in desc]
                if not target_apps:
                    target_apps = APPLIANCES
                mismatches = []
                for app in target_apps:
                    app_info = appliance_data.get(app, {})
                    orig_states = app_info.get("states", [0]*24)
                    required_h  = sum(orig_states)
                    scheduled_h = sum(schedules.get(app, [0]*24))
                    # Allow mismatch up to RUNTIME_TOLERANCE_FRACTION of required hours
                    # (high-power appliances like Heater may legitimately be capped by slot limits)
                    tolerance = max(RUNTIME_TOLERANCE_MIN_HOURS, int(required_h * RUNTIME_TOLERANCE_FRACTION))
                    if abs(scheduled_h - required_h) > tolerance:
                        mismatches.append(
                            f"{app}: required={required_h}h, scheduled={scheduled_h}h "
                            f"(diff={abs(scheduled_h - required_h)}, tolerance={tolerance}h)."
                        )
                if mismatches:
                    return False, "; ".join(mismatches)
                return True, (
                    f"Scheduled runtime hours match required hours within soft-fallback tolerance "
                    f"(±{RUNTIME_TOLERANCE_MIN_HOURS}h / {int(RUNTIME_TOLERANCE_FRACTION*100)}%)."
                )

            # Boundary sanity check per hour
            hour_match = re.search(r"\bhour\s+(\d+)\b|\bslot\s+(\d+)\b", desc)
            if hour_match:
                val = hour_match.group(1) or hour_match.group(2)
                h = int(val)
                bad = [app for app in APPLIANCES if schedules.get(app, [0]*24)[h] not in (0, 1)]
                if bad:
                    return False, f"Hour {h} has non-binary states for appliances: {bad}."
                return True, f"Hour {h} states are all valid binary values."

            # Generic boundary check across all hours and appliances
            bad_cells = []
            for app in APPLIANCES:
                for h, v in enumerate(schedules.get(app, [])):
                    if v not in (0, 1):
                        bad_cells.append(f"{app}[{h}]={v}")
                    if v < 0:
                        bad_cells.append(f"{app}[{h}]={v} (negative)")
            if bad_cells:
                return False, f"Invalid states found: {bad_cells[:5]}."
            return True, "All state values are non-negative and bounded."

    except Exception as e:
        return False, f"Evaluation error: {e}"

    return True, "Policy evaluated successfully."


# =========================
# STAGE 2: POLICY EVALUATION (LLM-BASED)
# =========================
def _weather_code_fallback(policy: Dict[str, Any],
                           schedules: Dict[str, List[int]],
                           weather: Dict[str, Any]) -> Tuple[bool, str]:
    """Deterministic fallback for weather comfort checks when Ollama is offline."""
    temps = weather.get("temperature", [DEFAULT_TEMPERATURE_C] * 24)
    hums  = weather.get("humidity",    [DEFAULT_HUMIDITY_PCT]  * 24)
    hot_hours  = [h for h in range(24)
                  if temps[h] >= HOT_TEMPERATURE_THRESHOLD_C or hums[h] >= HIGH_HUMIDITY_THRESHOLD_PCT]
    cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMPERATURE_THRESHOLD_C]
    desc = policy["description"].lower()

    if "ac" in desc or "ac_power" in desc:
        ac_on = [h for h in range(24) if schedules.get("AC_Power", [0]*24)[h] == 1]
        if not ac_on:
            return True, "AC is not scheduled at all; no comfort violation."
        if not hot_hours:
            return True, f"No hot/humid hours in forecast; AC schedule {ac_on} is reasonable."
        overlap = [h for h in ac_on if h in hot_hours]
        ratio   = len(overlap) / len(ac_on)
        if ratio >= COMFORT_OVERLAP_MIN_RATIO:
            return True, (
                f"AC scheduled in {overlap} of hot/humid hours {hot_hours} "
                f"({ratio:.0%} overlap ≥ {int(COMFORT_OVERLAP_MIN_RATIO*100)}%)."
            )
        return False, (
            f"AC only {ratio:.0%} of runtime in hot hours {hot_hours}; ON hours: {ac_on}."
        )

    if "heater" in desc:
        heater_on = [h for h in range(24) if schedules.get("Heater_Power", [0]*24)[h] == 1]
        if not heater_on:
            return True, "Heater is not scheduled at all; no comfort violation."
        if not cold_hours:
            return True, f"No cold hours (<=20\u00b0C) in forecast; Heater schedule {heater_on} is reasonable."
        overlap = [h for h in heater_on if h in cold_hours]
        ratio   = len(overlap) / len(heater_on)
        if ratio >= COMFORT_OVERLAP_MIN_RATIO:
            return True, (
                f"Heater scheduled in {overlap} of cold hours {cold_hours} "
                f"({ratio:.0%} overlap ≥ {int(COMFORT_OVERLAP_MIN_RATIO*100)}%)."
            )
        return False, (
            f"Heater only {ratio:.0%} of runtime in cold hours {cold_hours}; ON hours: {heater_on}."
        )

    return True, "Weather comfort policy verified (no specific appliance matched)."


def evaluate_policy_llm(policy: Dict[str, Any],
                        schedules: Dict[str, List[int]],
                        appliance_data: Dict[str, Any],
                        explanations: Dict[str, Any],
                        weather: Dict[str, Any]) -> Tuple[bool, str]:
    # Try Ollama first; fall back to deterministic check if offline
    ollama_online = False
    try:
        resp = requests.get("http://localhost:11434", timeout=3)
        ollama_online = resp.status_code == 200
    except Exception:
        pass

    if not ollama_online:
        passed, reason = _weather_code_fallback(policy, schedules, weather)
        return passed, f"[Offline fallback] {reason}"

    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.0)

        temps = weather.get("temperature", [25]*24)
        hums  = weather.get("humidity",    [60]*24)
        weather_summary = [{"hour": h, "temp_C": temps[h], "humidity_pct": hums[h]} for h in range(24)]
        hot_hours  = [h for h in range(24)
                      if temps[h] >= HOT_TEMPERATURE_THRESHOLD_C or hums[h] >= HIGH_HUMIDITY_THRESHOLD_PCT]
        cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMPERATURE_THRESHOLD_C]
        ac_on_hours     = [h for h in range(24) if schedules.get("AC_Power",     [0]*24)[h] == 1]
        heater_on_hours = [h for h in range(24) if schedules.get("Heater_Power", [0]*24)[h] == 1]

        prompt = f"""
You are an Energy Systems Policy Auditor evaluating a SINGLE policy about weather-based comfort scheduling.

Policy ID: {policy['id']}
Policy Description: "{policy['description']}"

Weather data (next 24 hours):
- Hot/Humid hours (temp >= 28C OR humidity >= 80%): {hot_hours}
- Cold hours (temp <= 20C): {cold_hours}
- Full weather table: {json.dumps(weather_summary)}

Actual scheduled hours from the optimizer:
- AC_Power ON hours: {ac_on_hours}
- Heater_Power ON hours: {heater_on_hours}

Your job:
- If the policy is about AC: check if AC_Power is predominantly scheduled in hot/humid hours {hot_hours}. Mark PASS if at least {int(COMFORT_OVERLAP_MIN_RATIO*100)}% of AC ON hours fall in hot/humid hours, OR if there are no hot hours.
- If the policy is about Heater: check if Heater_Power is predominantly scheduled in cold hours {cold_hours}. Mark PASS if at least {int(COMFORT_OVERLAP_MIN_RATIO*100)}% of Heater ON hours fall in cold hours, OR if there are no cold hours.
- Do NOT evaluate peak-hour avoidance or cost here — only evaluate weather-comfort alignment.

Respond ONLY with a JSON object:
- "passed": true or false
- "reason": "One clear sentence explaining why"
"""
        out = llm.invoke(prompt).content.strip()
        if out.startswith("```"):
            lines = out.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            out = "\n".join(lines).strip()

        res = json.loads(out)
        return bool(res.get("passed", False)), str(res.get("reason", "No reason provided."))
    except Exception as e:
        # If LLM call itself fails, fall back to code
        passed, reason = _weather_code_fallback(policy, schedules, weather)
        return passed, f"[LLM error fallback] {reason}"


# =========================
# MAIN VALIDATOR LOOP
# =========================
def run_validation():
    print("--- Starting Standalone Policy Validation Script ---")

    try:
        appliance_data, schedules, explanations, price_map, user_preference, weather = load_pipeline_data()
    except Exception as e:
        print(f"[Error] Failed to load pipeline output JSONs: {e}")
        print("Make sure Run_LSTM.py and agent.py have run and generated their JSON outputs first!")
        sys.exit(1)

    # 1. Generate policies
    policies = generate_policies()
    print(f"Generated {len(policies)} dynamic validation policies.")

    # 2. Evaluate each policy
    report_items = []
    passed_count = 0

    for policy in policies:
        pol_id    = policy["id"]
        eval_type = policy.get("eval_type", "code")

        print(f"Evaluating {pol_id} ({eval_type}): {policy['description']}")

        if eval_type == "code":
            passed, reason = evaluate_policy_code(
                policy, schedules, appliance_data, explanations, price_map, user_preference
            )
        else:
            passed, reason = evaluate_policy_llm(
                policy, schedules, appliance_data, explanations, weather
            )

        if passed:
            passed_count += 1

        report_items.append({
            "id":          pol_id,
            "description": policy["description"],
            "category":    policy["category"],
            "eval_type":   eval_type,
            "status":      "PASS" if passed else "FAIL",
            "reason":      reason
        })

    # 3. Summary
    total = len(policies)
    summary = {
        "total_policies":       total,
        "passed":               passed_count,
        "failed":               total - passed_count,
        "pass_rate_percentage": round(100.0 * passed_count / total, 2)
    }

    report = {"summary": summary, "policies": report_items}

    # 4. Write report JSON
    base_dir    = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'validation_report.json'))
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"Validation Report saved to {report_path}")
    print(f"Results: {passed_count}/{total} passed ({summary['pass_rate_percentage']}%).")
    print("--- End of Standalone Validation Script ---")


if __name__ == "__main__":
    run_validation()
