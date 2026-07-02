import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from typing import Dict, List, Any, Tuple, Optional
import os
import sys

# Add src to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    APPLIANCES,
    POWER_KWH,
    DEFAULT_TEMPERATURE_C,
    DEFAULT_HUMIDITY_PCT,
    HOT_TEMPERATURE_THRESHOLD_C,
    HIGH_HUMIDITY_THRESHOLD_PCT,
    COLD_TEMPERATURE_THRESHOLD_C,
    AC_COMFORT_SCORE_BIAS,
    HEATER_COMFORT_SCORE_BIAS,
    FALLBACK_SLOT_CAPACITY_KW,
)

def solve_milp_schedule(
    demand: Dict[str, Any],
    price_map: Dict[int, Dict[str, Any]],
    capacity_map: Dict[int, float],
    allow_peak: Dict[str, bool],
    preferred_hours: Dict[str, Optional[List[int]]],
    weather: Dict[str, Any]
) -> Dict[str, List[int]]:
    """
    Solves the optimal home energy management scheduling problem using Mixed-Integer Linear Programming (MILP).
    Ensures feasibility by including slack variables for soft capacity limits.
    """
    N_apps = len(APPLIANCES)
    T = 24
    
    # Decision variables layout:
    # x[a * 24 + t] for a in 0..N_apps-1, t in 0..23 (binary)
    # s[t] for t in 0..23 (continuous, slack for capacity limit)
    num_vars = N_apps * T + T
    
    # 1. Objective Function coefficients
    c = np.zeros(num_vars)
    
    # Comfort indices
    temps = weather.get("temperature", [DEFAULT_TEMPERATURE_C] * 24)
    hums  = weather.get("humidity",    [DEFAULT_HUMIDITY_PCT]  * 24)
    hot_hours  = [h for h in range(24)
                  if temps[h] >= HOT_TEMPERATURE_THRESHOLD_C or hums[h] >= HIGH_HUMIDITY_THRESHOLD_PCT]
    cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMPERATURE_THRESHOLD_C]
    
    def is_hot_or_adjacent(h: int) -> bool:
        if h in hot_hours:
            return True
        for dh in [-1, 1]:
            if (h + dh) % 24 in hot_hours:
                return True
        return False
        
    for a_idx, app in enumerate(APPLIANCES):
        p_rating = demand[app]["power_rating"]
        for t in range(T):
            score = price_map[t]["price"]
            if app == 'AC_Power' and is_hot_or_adjacent(t):
                score += AC_COMFORT_SCORE_BIAS
            elif app == 'Heater_Power' and t in cold_hours:
                score += HEATER_COMFORT_SCORE_BIAS
            
            c[a_idx * T + t] = p_rating * score
            
    # Slack variables penalty (very high penalty for capacity violation)
    penalty = 1e6
    for t in range(T):
        c[N_apps * T + t] = penalty
        
    # 2. Integrality
    # First N_apps * T are binary (integer), last T are continuous
    integrality = np.zeros(num_vars)
    integrality[:N_apps * T] = 1 # 1 means integer constraint
    
    # 3. Bounds
    lower_bounds = np.zeros(num_vars)
    upper_bounds = np.ones(num_vars)
    # Slack variables can go up to infinity
    upper_bounds[N_apps * T:] = np.inf
    
    # Enforce user constraints by setting upper bounds of disallowed slots to 0
    peak_hours = [h for h in range(24) if price_map[h]["band"] == "peak"]
    for a_idx, app in enumerate(APPLIANCES):
        # Peak hours allowed?
        if not allow_peak.get(app, False):
            for t in peak_hours:
                upper_bounds[a_idx * T + t] = 0.0
        # Preferred hours?
        pref = preferred_hours.get(app)
        if pref is not None:
            for t in range(T):
                if t not in pref:
                    upper_bounds[a_idx * T + t] = 0.0
                    
    bounds = Bounds(lower_bounds, upper_bounds)
    
    # 4. Constraints
    A_matrix = []
    lb_constraints = []
    ub_constraints = []
    
    # Constraint Type A: Runtime constraints
    # For each appliance: sum_{t} x_{a, t} = RequiredHours
    for a_idx, app in enumerate(APPLIANCES):
        req_h = demand[app]["required_hours"]
        # Limit to the actual available candidate slots count if user preferences are overly restrictive
        allowed_slots_count = int(sum(upper_bounds[a_idx * T: (a_idx + 1) * T]))
        actual_target = min(req_h, allowed_slots_count)
        
        row = np.zeros(num_vars)
        row[a_idx * T: (a_idx + 1) * T] = 1.0
        A_matrix.append(row)
        lb_constraints.append(actual_target)
        ub_constraints.append(actual_target)
        
    # Constraint Type B: Capacity constraints
    # For each hour t: sum_{a} x_{a, t} * Power_a - s_t <= Capacity_t
    # -> sum_{a} x_{a, t} * Power_a - s_t <= Capacity_t
    for t in range(T):
        row = np.zeros(num_vars)
        for a_idx, app in enumerate(APPLIANCES):
            p_rating = demand[app]["power_rating"]
            row[a_idx * T + t] = p_rating
        # -s_t
        row[N_apps * T + t] = -1.0
        A_matrix.append(row)
        lb_constraints.append(-np.inf)
        ub_constraints.append(capacity_map.get(t, FALLBACK_SLOT_CAPACITY_KW))
        
    A = np.array(A_matrix)
    lb = np.array(lb_constraints)
    ub = np.array(ub_constraints)
    
    constraints = LinearConstraint(A, lb, ub)
    
    # Solve
    res = milp(c=c, bounds=bounds, constraints=constraints, integrality=integrality)
    
    # Parse output
    schedules = {a: [0]*24 for a in APPLIANCES}
    if res.success:
        x_opt = res.x[:N_apps * T]
        for a_idx, app in enumerate(APPLIANCES):
            for t in range(T):
                val = x_opt[a_idx * T + t]
                # Rounding since MILP returns floats close to integers
                schedules[app][t] = int(round(val))
    else:
        print(f"[MILP Solver Warning] Optimization failed with message: {res.message}. Falling back to zero schedule.")
        
    return schedules
