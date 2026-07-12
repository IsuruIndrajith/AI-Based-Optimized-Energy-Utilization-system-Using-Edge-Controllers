import os
import sys
import json
import argparse
from typing import Dict, Any, List

# Setup paths
workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(workspace_dir, "src"))

from agent.agent import solve_llm_schedule, APPLIANCES, POWER_KWH, get_appliance_demand
from agent.validate_policies import generate_policies, evaluate_policy
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

def generate_plot(schedules, capacity_map, price_map, scenario_name, output_filename):
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(14, 7))
    
    hours = np.arange(24)
    
    # 1. Plot Background TOU Bands
    for h in hours:
        band = price_map[h]["band"]
        if band == "off_peak":
            color = "#e6f5d0" # light green
        elif band == "day":
            color = "#fdf0d5" # light yellow
        else:
            color = "#fbdcce" # light red
        ax.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.5, zorder=0)

    # 2. Plot Stacked Appliance Power
    bottom = np.zeros(24)
    colors = plt.get_cmap('Set2')(np.linspace(0, 1, len(APPLIANCES)))
    
    for idx, app in enumerate(APPLIANCES):
        power = POWER_KWH.get(app, 1.0)
        sched = np.array(schedules.get(app, [0]*24))
        app_load = sched * power
        
        ax.bar(hours, app_load, bottom=bottom, label=app.replace("_Power", ""), 
               color=colors[idx], edgecolor='white', width=0.8, zorder=3)
        bottom += app_load

    # 3. Plot Capacity Limit Line
    cap_values = [capacity_map[h] for h in hours]
    ax.step(hours, cap_values, where='mid', color='black', linewidth=2.5, 
            linestyle='--', label='Grid Capacity Limit', zorder=4)

    # Formatting
    ax.set_title(f"Optimized Schedule: {scenario_name}", fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel("Hour of Day", fontsize=12, fontweight='bold')
    ax.set_ylabel("Power Consumption (kW)", fontsize=12, fontweight='bold')
    ax.set_xticks(hours)
    ax.set_xlim(-0.6, 23.6)
    
    # Custom legend for TOU bands
    import matplotlib.lines as mlines
    p1 = patches.Patch(color='#e6f5d0', label='Off-Peak')
    p2 = patches.Patch(color='#fdf0d5', label='Day')
    p3 = patches.Patch(color='#fbdcce', label='Peak')
    
    handles, labels = ax.get_legend_handles_labels()
    # Add TOU legends to the handles
    handles.extend([p1, p2, p3])
    labels.extend(['Off-Peak Rate', 'Day Rate', 'Peak Rate'])
    
    ax.legend(handles=handles, labels=labels, loc='upper right', bbox_to_anchor=(1.15, 1), fontsize=10)
    plt.tight_layout()
    
    os.makedirs(os.path.join(workspace_dir, "plots"), exist_ok=True)
    filepath = os.path.join(workspace_dir, "plots", output_filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n📊 Plot saved to: plots/{output_filename}")

def make_price_map(off_peak_rate: float, day_rate: float, peak_rate: float):
    price_map = {}
    for h in range(24):
        if h in range(22, 24) or h in range(0, 5):
            price_map[h] = {"price": off_peak_rate, "band": "off_peak"}
        elif h in range(5, 18):
            price_map[h] = {"price": day_rate, "band": "day"}
        else:
            price_map[h] = {"price": peak_rate, "band": "peak"}
    return price_map

def make_capacity_map(off_peak_cap: float, day_cap: float, peak_cap: float):
    capacity_map = {}
    for h in range(24):
        if h in range(22, 24) or h in range(0, 5):
            capacity_map[h] = off_peak_cap
        elif h in range(5, 18):
            capacity_map[h] = day_cap
        else:
            capacity_map[h] = peak_cap
    return capacity_map

def validate_scenario(
    scenario_name: str,
    off_peak_rate: float,
    day_rate: float,
    peak_rate: float,
    off_peak_cap: float,
    day_cap: float,
    peak_cap: float,
    weather_temp: float,
    weather_humidity: float,
    allow_peak: bool = False
):
    print(f"\n{'='*60}")
    print(f"RUNNING: {scenario_name}")
    print(f"Rates (LKR): OffPeak={off_peak_rate}, Day={day_rate}, Peak={peak_rate}")
    print(f"Capacity (kW): OffPeak={off_peak_cap}, Day={day_cap}, Peak={peak_cap}")
    print(f"Weather: {weather_temp}°C, {weather_humidity}% humidity")
    print(f"{'='*60}")

    # Load data
    try:
        appliance_data = get_appliance_demand()
    except FileNotFoundError as e:
        print(f"Error loading appliance demand data: {e}")
        return

    price_map = make_price_map(off_peak_rate, day_rate, peak_rate)
    capacity_map = make_capacity_map(off_peak_cap, day_cap, peak_cap)
    weather = {
        "temperature": [weather_temp] * 24,
        "humidity": [weather_humidity] * 24
    }
    user_preference = {
        "allow_peak": {a: allow_peak for a in APPLIANCES},
        "preferred_hours": {a: None for a in APPLIANCES}
    }

    # 1. Run Scheduler
    backend_used = "unknown"
    try:
        schedules, backend_used = solve_llm_schedule(
            demand=appliance_data,
            price_map=price_map,
            capacity_map=capacity_map,
            allow_peak=user_preference["allow_peak"],
            preferred_hours=user_preference["preferred_hours"],
            weather=weather
        )
        print(f"\n[Scheduler backend used: {backend_used.upper()}]")
        if backend_used == "greedy_fallback":
            print("  ⚠️  WARNING: Ollama was unavailable — results reflect "
                  "the greedy fallback algorithm, NOT the LLM scheduler.")
    except Exception as e:
        print(f"Scheduling failed: {e}")
        return None

    print("\n[Generated Schedules]")
    for app, sched in schedules.items():
        print(f"  {app:<22}: {sched}")

    # Calculate costs
    total_cost = 0.0
    baseline_cost = 0.0
    for app in APPLIANCES:
        power = POWER_KWH.get(app, 1.0)
        # Optimized Cost
        sched = schedules[app]
        app_cost = sum(sched[h] * power * price_map[h]["price"] for h in range(24))
        total_cost += app_cost
        
        # Baseline Cost
        avg_list = appliance_data[app].get("averages", [0.0]*24)
        base_app_cost = sum((avg_list[h] / 1000.0) * price_map[h]["price"] for h in range(24))
        baseline_cost += base_app_cost
        
    print(f"\nCost Analysis:")
    print(f"  Baseline Cost (LSTM-derived peaks): {baseline_cost:.2f} LKR")
    print(f"  Optimized Cost: {total_cost:.2f} LKR")
    savings = baseline_cost - total_cost
    savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0
    print(f"  Savings vs LSTM Baseline: {savings:.2f} LKR ({savings_pct:.1f}%)")

    # Fix 7: Compute naive baseline (appliances ON from hour 0) for independent comparison
    naive_cost = 0.0
    for app in APPLIANCES:
        power = POWER_KWH.get(app, 1.0)
        naive_states = appliance_data[app].get("naive_baseline_states", [0]*24)
        naive_cost += sum(naive_states[h] * power * price_map[h]["price"] for h in range(24))
    naive_savings_pct = ((naive_cost - total_cost) / naive_cost * 100) if naive_cost > 0 else 0
    print(f"  Naive Baseline Cost (hour-0-first): {naive_cost:.2f} LKR")
    print(f"  Savings vs Naive Baseline: {naive_cost - total_cost:.2f} LKR ({naive_savings_pct:.1f}%)")

    # 2. Run Policy Validation
    print("\n[Running Policy Validation...]")
    policies = generate_policies()
    passed_count = 0
    failures = []

    mock_expl = {
        "totals": {
            "baseline": baseline_cost,
            "optimized": total_cost
        },
        "weather": weather,
        "user_preference": user_preference
    }

    for pol in policies:
        passed, reason = evaluate_policy(
            policy=pol,
            app_data=appliance_data,
            schedules=schedules,
            explanations=mock_expl,
            price_map=price_map,
            user_preference=user_preference,
            weather=weather,
            capacity_map=capacity_map
        )
        if passed:
            passed_count += 1
        else:
            failures.append((pol["id"], pol["description"], reason))

    pass_rate = 100.0 * passed_count / len(policies)
    print(f"Validation Pass Rate: {passed_count}/{len(policies)} ({pass_rate:.1f}%)")

    if failures:
        print("\nFailures:")
        for fid, desc, reason in failures:
            print(f"  ❌ {fid} | {desc}")
            print(f"       Reason: {reason}")
    else:
        print("\n✅ All policies passed successfully!")

    # 3. Generate Plot
    safe_name = scenario_name.split(':')[0].replace(" ", "_").lower()
    generate_plot(schedules, capacity_map, price_map, scenario_name, f"{safe_name}_plot.png")
    
    return {
        "scenario_name": scenario_name,
        "backend_used": backend_used,
        "policies": policies,
        "failures": failures,
        "passed_count": passed_count,
        "total": len(policies),
        "optimized_cost": total_cost,
        "baseline_cost": baseline_cost,
        "naive_cost": naive_cost,
    }

def generate_summary_plot(results_list, output_filename="policy_summary_plot.png"):
    if not results_list:
        return
        
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Aggregate by category across all scenarios run
    # A scenario passes a category only if ALL policies in that category pass
    categories = {}
    valid_results = [r for r in results_list if r is not None]
    total_scenarios = len(valid_results)
    
    # First, collect all unique categories
    for res in valid_results:
        for pol in res["policies"]:
            cat = pol["category"]
            if cat not in categories:
                categories[cat] = {"scenarios_passed": 0, "scenarios_failed": 0}
                
    for res in valid_results:
        # Determine pass/fail per category for THIS scenario
        cat_status = {cat: True for cat in categories.keys()}
        
        failed_ids = set(f[0] for f in res["failures"])
        for pol in res["policies"]:
            if pol["id"] in failed_ids:
                cat_status[pol["category"]] = False
                
        # Update overall counts
        for cat, passed in cat_status.items():
            if passed:
                categories[cat]["scenarios_passed"] += 1
            else:
                categories[cat]["scenarios_failed"] += 1
                
    cat_names = list(categories.keys())
    cat_names.sort() # sort alphabetically
    
    pass_counts = [categories[c]["scenarios_passed"] for c in cat_names]
    fail_counts = [categories[c]["scenarios_failed"] for c in cat_names]
    
    y_pos = np.arange(len(cat_names))
    
    ax.barh(y_pos, pass_counts, color='#4daf4a', edgecolor='white', label='Scenarios Passed')
    ax.barh(y_pos, fail_counts, left=pass_counts, color='#e41a1c', edgecolor='white', label='Scenarios Failed')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cat_names], fontsize=12, fontweight='bold')
    ax.set_xlabel(f"Number of Scenarios (out of {total_scenarios})", fontsize=12, fontweight='bold')
    ax.set_title("Category Success Rate Across Scenarios", fontsize=16, fontweight='bold', pad=20)
    
    # Add text for overall pass/fail
    # A scenario perfectly passes if it passes ALL categories
    perfect_scenarios = 0
    for res in valid_results:
        if not res["failures"]:
            perfect_scenarios += 1
            
    overall_pct = (perfect_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
    stats_text = f"Perfect Scenarios: {perfect_scenarios}/{total_scenarios} ({overall_pct:.1f}%)"
    ax.text(0.5, -0.15, stats_text, ha='center', va='center', transform=ax.transAxes, 
            fontsize=14, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))
    
    # Add values on the bars
    for i, (p, f) in enumerate(zip(pass_counts, fail_counts)):
        if p > 0:
            ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold')
        if f > 0:
            ax.text(p + f/2, i, str(f), ha='center', va='center', color='white', fontweight='bold')
            
    ax.legend(loc='upper right', fontsize=12)
    plt.tight_layout()
    
    os.makedirs(os.path.join(workspace_dir, "plots"), exist_ok=True)
    filepath = os.path.join(workspace_dir, "plots", output_filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n📈 Summary Plot saved to: plots/{output_filename}")

def main():
    parser = argparse.ArgumentParser(description="Validate LLM Schedules under different constraints")
    parser.add_argument("--off-peak-rate", type=float, default=33.0, help="Off-peak tariff (LKR/kWh)")
    parser.add_argument("--day-rate", type=float, default=47.0, help="Day tariff (LKR/kWh)")
    parser.add_argument("--peak-rate", type=float, default=106.0, help="Peak tariff (LKR/kWh)")
    
    parser.add_argument("--off-peak-cap", type=float, default=6.0, help="Off-peak capacity limit (kW)")
    parser.add_argument("--day-cap", type=float, default=4.0, help="Day capacity limit (kW)")
    parser.add_argument("--peak-cap", type=float, default=2.5, help="Peak capacity limit (kW)")
    
    parser.add_argument("--temp", type=float, default=25.0, help="Constant temperature (°C)")
    parser.add_argument("--humidity", type=float, default=60.0, help="Constant humidity (%)")
    
    parser.add_argument("--allow-peak", action="store_true", help="Allow appliances to run in peak hours")
    
    parser.add_argument("--run-all-scenarios", action="store_true", help="Run a suite of predefined scenarios")
    
    args = parser.parse_args()
    results = []

    if args.run_all_scenarios:
        # Scenario 1: Baseline
        r1 = validate_scenario(
            "Scenario 1: Baseline", 
            33.0, 47.0, 106.0, 
            6.0, 4.0, 2.5, 
            25.0, 60.0, False
        )
        results.append(r1)
        # Scenario 2: Low Grid Capacity
        r2 = validate_scenario(
            "Scenario 2: Low Grid Capacity", 
            33.0, 47.0, 106.0, 
            5.0, 1.2, 1.0, 
            25.0, 60.0, False
        )
        results.append(r2)
        # Scenario 3: High Peak Tariff & Hot Weather
        r3 = validate_scenario(
            "Scenario 3: High Peak Tariff & Hot Weather (AC preferred)", 
            33.0, 47.0, 250.0, 
            6.0, 4.0, 2.5, 
            32.0, 80.0, False
        )
        results.append(r3)
        # Scenario 4: Extremely Cold Night (Heater preferred)
        r4 = validate_scenario(
            "Scenario 4: Extremely Cold Night", 
            33.0, 47.0, 106.0, 
            6.0, 4.0, 2.5, 
            15.0, 50.0, False
        )
        results.append(r4)
        # Scenario 5: Zero Grid Capacity During Peak
        r5 = validate_scenario(
            "Scenario 5: Zero Peak Capacity", 
            33.0, 47.0, 106.0, 
            6.0, 4.0, 0.0, 
            25.0, 60.0, False
        )
        results.append(r5)
        # Scenario 6: Flat Tariff (No TOU Difference)
        r6 = validate_scenario(
            "Scenario 6: Flat Tariff", 
            40.0, 40.0, 40.0, 
            5.0, 5.0, 5.0, 
            25.0, 60.0, False
        )
        results.append(r6)
        # Scenario 7: Super Hot & High Humidity (AC stress test)
        r7 = validate_scenario(
            "Scenario 7: Extreme Heat & Humidity", 
            33.0, 47.0, 106.0, 
            6.0, 4.0, 2.5, 
            38.0, 95.0, False
        )
        results.append(r7)
        # Scenario 8: Allow Peak Usage (User override)
        r8 = validate_scenario(
            "Scenario 8: Allow Peak Usage", 
            33.0, 47.0, 106.0, 
            6.0, 4.0, 2.5, 
            25.0, 60.0, True
        )
        results.append(r8)
        # Scenario 9: High Day Capacity (Solar Abundance)
        r9 = validate_scenario(
            "Scenario 9: High Day Capacity", 
            33.0, 47.0, 106.0, 
            6.0, 10.0, 2.5, 
            25.0, 60.0, False
        )
        results.append(r9)
        # Scenario 10: Highly Restrictive Constraints
        r10 = validate_scenario(
            "Scenario 10: Highly Restrictive", 
            50.0, 80.0, 200.0, 
            3.0, 2.0, 1.0, 
            25.0, 60.0, False
        )
        results.append(r10)
    else:
        # Run custom user scenario from CLI arguments
        r = validate_scenario(
            "Custom Scenario",
            args.off_peak_rate, args.day_rate, args.peak_rate,
            args.off_peak_cap, args.day_cap, args.peak_cap,
            args.temp, args.humidity, args.allow_peak
        )
        results.append(r)
        
    generate_summary_plot(results)

    # Print backend summary
    print("\n=" * 50)
    print("SCHEDULER BACKEND SUMMARY")
    print("=" * 50)
    for r in results:
        if r is None: continue
        backend = r.get("backend_used", "unknown")
        icon = "✅" if backend == "llm" else "⚠️ "
        print(f"  {icon} {r['scenario_name']}: {backend.upper()}")

if __name__ == "__main__":
    main()
