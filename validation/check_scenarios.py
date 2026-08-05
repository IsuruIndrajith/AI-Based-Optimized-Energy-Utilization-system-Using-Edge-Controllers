import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from validate_policies_multiscenario import build_scenarios

s = build_scenarios()
groups = {}
for x in s:
    groups.setdefault(x["policy_group"], []).append(x["id"])

for g, v in groups.items():
    print(f"{g}: {len(v)} scenarios -> {v}")
print(f"\nTotal: {len(s)} scenarios")
