"""
validate_policies_multiscenario.py
===================================
Runs the agent pipeline 10 times under varying scenarios (weather, constraints, pricing, capacity).
Extracts performance metrics for 4 headline policies (W01, U01, CS01, CAP01) and aggregates results.
"""

import os
import sys
import json
import re
import statistics
from unittest.mock import patch

# Ensure we can import agent and validate_policies
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agent
import validate_policies

# ============================================================================
# 1. SCENARIO GENERATOR
# ============================================================================

def build_scenarios():
    scenarios = []

    def make_price_map(off_peak, day, peak):
        pm = {}
        for h in range(24):
            if h < 5 or h >= 22: pm[h] = {"price": off_peak, "band": "off_peak"}
            elif 5 <= h < 18: pm[h] = {"price": day, "band": "day"}
            else: pm[h] = {"price": peak, "band": "peak"}
        return pm

    def make_cap_map(off_peak, day, peak):
        cm = {}
        for h in range(24):
            if h < 5 or h >= 22: cm[h] = off_peak
            elif 5 <= h < 18: cm[h] = day
            else: cm[h] = peak
        return cm
        
    def make_weather(temp_val, hum_val):
        return {"temperature": [temp_val]*24, "humidity": [hum_val]*24}

    std_price = make_price_map(33.0, 47.0, 106.0)
    std_cap   = make_cap_map(5.0, 5.0, 4.0)
    std_weath = make_weather(26.0, 60.0)

    # S01: Baseline
    scenarios.append({
        "id": "S01",
        "desc": "Baseline (Normal day, no constraints)",
        "weather": std_weath,
        "user_preference": {"raw_message": "I have no specific preferences today."},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S02: Extreme Heat
    scenarios.append({
        "id": "S02",
        "desc": "Extreme Heat (Temp > 28C all day)",
        "weather": make_weather(32.0, 70.0),
        "user_preference": {"raw_message": "Keep it cool, I have no specific constraints."},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S03: Extreme Cold
    scenarios.append({
        "id": "S03",
        "desc": "Extreme Cold (Temp < 20C all day)",
        "weather": make_weather(15.0, 50.0),
        "user_preference": {"raw_message": "It is freezing today."},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S04: Strict Peak User
    scenarios.append({
        "id": "S04",
        "desc": "Strict Peak Restriction on WM",
        "weather": std_weath,
        "user_preference": {"raw_message": "Do not run the washing machine during peak hours under any circumstance."},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S05: Narrow Preferred Window
    scenarios.append({
        "id": "S05",
        "desc": "Narrow Preferred Window (Heater 02:00-06:00)",
        "weather": make_weather(18.0, 60.0),
        "user_preference": {"raw_message": "Run the heater only between 02:00 and 06:00."},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S06: Hyper-Expensive Peak
    scenarios.append({
        "id": "S06",
        "desc": "Hyper-Expensive Peak (Peak = 300 LKR)",
        "weather": std_weath,
        "user_preference": {"raw_message": "Save as much money as possible."},
        "price_map": make_price_map(33.0, 47.0, 300.0),
        "capacity_map": std_cap
    })

    # S07: Grid Constrained
    scenarios.append({
        "id": "S07",
        "desc": "Grid Constrained (Global 3.0 kW Limit)",
        "weather": std_weath,
        "user_preference": {"raw_message": ""},
        "price_map": std_price,
        "capacity_map": make_cap_map(3.0, 3.0, 3.0)
    })

    # S08: Flat Tariff
    scenarios.append({
        "id": "S08",
        "desc": "Flat Tariff (All bands = 30 LKR)",
        "weather": std_weath,
        "user_preference": {"raw_message": ""},
        "price_map": make_price_map(30.0, 30.0, 30.0),
        "capacity_map": std_cap
    })

    # S09: High Humidity
    scenarios.append({
        "id": "S09",
        "desc": "High Humidity Day (>80% RH)",
        "weather": make_weather(26.0, 85.0),
        "user_preference": {"raw_message": ""},
        "price_map": std_price,
        "capacity_map": std_cap
    })

    # S10: Conflicting Constraints
    scenarios.append({
        "id": "S10",
        "desc": "Impossible Request (Peak permitted but low capacity)",
        "weather": std_weath,
        "user_preference": {"raw_message": "Please run the washing machine and heater during the evening peak hours."},
        "price_map": std_price,
        "capacity_map": make_cap_map(5.0, 5.0, 1.5)
    })

    return scenarios

# ============================================================================
# 2. METRIC EXTRACTION REGEX
# ============================================================================

def extract_metric(pid: str, passed: bool, reason: str) -> float:
    if pid == "W01":
        if "skipped" in reason or "not expected" in reason or "not scheduled" in reason:
            return None
        m = re.search(r'overlap=.*?\(([\d\.]+)%', reason)
        if m: return float(m.group(1))
        
    elif pid == "CS01":
        m = re.search(r'Savings =\s*([0-9\.]+)\s*LKR', reason)
        if m:
            m2 = re.search(r'Baseline \(([0-9\.]+)\)', reason)
            if m2:
                base = float(m2.group(1))
                sav = float(m.group(1))
                return (sav/base*100) if base > 0 else 0.0
            
    return None

# ============================================================================
# 3. RUNNER & AGGREGATOR
# ============================================================================

def run_all():
    scenarios = build_scenarios()
    results = []
    print(f"Starting Multi-Scenario Run ({len(scenarios)} Scenarios)...")

    for s in scenarios:
        print(f"\n{'='*60}")
        print(f"Running {s['id']}: {s['desc']}")
        
        def mock_weather(): return s["weather"]
        def mock_user_pref(): return s["user_preference"]["raw_message"]
        def mock_tou_capacity(*args, **kwargs): return {"capacity_map": s["capacity_map"]}
        def mock_build_price_map(tou_json): return s["price_map"], "LKR"
            
        with patch('agent.fetch_weather_24h', side_effect=mock_weather), \
             patch('agent.get_user_preference', side_effect=mock_user_pref), \
             patch('agent.get_tou_and_capacity', side_effect=mock_tou_capacity), \
             patch('agent.build_price_map', side_effect=mock_build_price_map):
             
            try:
                # Run the decision loop once
                agent.main_once()
            except Exception as e:
                print(f"Agent failed in scenario {s['id']}: {e}")
            
        try:
            app_data, schedules, explanations, price_map, capacity_map, user_preference, weather = \
                validate_policies.load_pipeline_data()
        except Exception as e:
            print(f"Failed to load pipeline data for {s['id']}: {e}")
            continue
            
        target_policies = [
            {
                "id": "W01",
                "description": "AC comfort overlap >= 40%",
                "category": "weather",
                "meta": {"app": "AC_Power"}
            },
            {
                "id": "U01",
                "description": "peak-restricted appliances have zero peak hours",
                "category": "user_preference",
                "meta": {"app": "WashingMachine_Power", "check": "allow_peak"}
            },
            {
                "id": "CS01",
                "description": "optimized cost < baseline cost",
                "category": "cost_savings",
                "meta": {}
            },
            {
                "id": "CAP01",
                "description": "no hour exceeds TOU-band capacity",
                "category": "capacity",
                "meta": {"hour": None}
            }
        ]
        scenario_res = {"id": s["id"], "desc": s["desc"], "policies": {}}
        
        for pol in target_policies:
            passed, reason = validate_policies.evaluate_policy(
                pol, app_data, schedules, explanations,
                price_map, user_preference, weather, capacity_map=capacity_map
            )
            metric = extract_metric(pol["id"], passed, reason)
            scenario_res["policies"][pol["id"]] = {
                "passed": passed,
                "reason": reason,
                "metric": metric
            }
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {pol['id']} -> {reason}")
            
        results.append(scenario_res)

    summary = {}
    for pid in ["W01", "U01", "CS01", "CAP01"]:
        passes = sum(1 for r in results if r["policies"][pid]["passed"])
        metrics = [r["policies"][pid]["metric"] for r in results if r["policies"][pid]["metric"] is not None]
        
        summ = {"pass_rate_%": (passes / len(results)) * 100}
        if metrics:
            summ["mean"] = round(statistics.mean(metrics), 2)
            summ["min"] = round(min(metrics), 2)
            summ["max"] = round(max(metrics), 2)
            if len(metrics) > 1:
                summ["std"] = round(statistics.stdev(metrics), 2)
        summary[pid] = summ

    print(f"\n{'='*60}")
    print(f"  MULTI-SCENARIO SUMMARY (10 Runs)")
    print(f"{'='*60}")
    print(f"ID   | W01  | U01  | CS01 | CAP01 | Description")
    print(f"------------------------------------------------------------")
    for r in results:
        w = "PASS" if r["policies"]["W01"]["passed"] else "FAIL"
        u = "PASS" if r["policies"]["U01"]["passed"] else "FAIL"
        c = "PASS" if r["policies"]["CS01"]["passed"] else "FAIL"
        p = "PASS" if r["policies"]["CAP01"]["passed"] else "FAIL"
        print(f"{r['id']}  | {w:<4} | {u:<4} | {c:<4} | {p:<5} | {r['desc']}")

    print(f"\nAggregate Statistics:")
    for pid, s in summary.items():
        print(f"  {pid}: {s}")

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "validation_report_multiscenario.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"scenarios": results, "summary": summary}, f, indent=2)
    print(f"\nSaved full report to {out_file}")

if __name__ == "__main__":
    run_all()
