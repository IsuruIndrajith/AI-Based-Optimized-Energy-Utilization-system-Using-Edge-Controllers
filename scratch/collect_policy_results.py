"""Collect policy validation results and save to JSON."""
import sys, os, json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "validation")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from validate_policies import generate_policies, evaluate_policy, load_pipeline_data

ad, sched, expl, pm, user_pref, weather = load_pipeline_data()
policies = generate_policies()
results  = []
passed   = 0

for pol in policies:
    ok, reason = evaluate_policy(pol, ad, sched, expl, pm, user_pref, weather)
    if ok:
        passed += 1
    results.append({
        "id":          pol["id"],
        "category":    pol["category"],
        "description": pol["description"],
        "status":      "PASS" if ok else "FAIL",
        "reason":      reason,
    })

out = {
    "total":   len(policies),
    "passed":  passed,
    "failed":  len(policies) - passed,
    "results": results,
}

out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "policy_results.json"))
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print(f"Saved {len(policies)} policy results → {out_path}")
print(f"PASS: {passed}  FAIL: {len(policies)-passed}  ({passed/len(policies)*100:.1f}%)")
