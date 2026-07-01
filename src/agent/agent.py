import paho.mqtt.client as mqtt
import time
import ast
import json
from langchain_ollama import ChatOllama
import ollama
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple, Any, Optional, TypedDict
import requests
import os
import sys
from zoneinfo import ZoneInfo
from langgraph.graph import StateGraph, END

# Load centralised configuration (no hard-coded thresholds below this point)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import (
    APPLIANCES,
    POWER_KWH,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_TIMEOUT_SECONDS,
    MQTT_FETCH_TIMEOUT_SECONDS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LOCATION_LAT,
    LOCATION_LON,
    LOCATION_TZ,
    DEFAULT_TEMPERATURE_C,
    DEFAULT_HUMIDITY_PCT,
    HOT_TEMPERATURE_THRESHOLD_C,
    HIGH_HUMIDITY_THRESHOLD_PCT,
    COLD_TEMPERATURE_THRESHOLD_C,
    AC_COMFORT_SCORE_BIAS,
    HEATER_COMFORT_SCORE_BIAS,
    DEFAULT_CAPACITY_OFF_PEAK_KW,
    DEFAULT_CAPACITY_DAY_KW,
    DEFAULT_CAPACITY_PEAK_KW,
    FALLBACK_SLOT_CAPACITY_KW,
    AGENT_LOOP_INTERVAL_SECONDS,
)

# =========================
# RUNTIME DEFAULTS
# =========================
DEFAULT_USER_MSG = "Allow AC_Power ON during peak hours"

# =========================
# FIREBASE INITIALIZATION
# =========================
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'serviceAccountKey.json'))

    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        print(f"Firebase initialized successfully using key: {key_path}")
    else:
        firebase_admin.initialize_app()
        print("Firebase initialized using default credentials.")
    db = firestore.client()
except Exception as e:
    print(f"Firebase initialization skipped/failed: {e}")

# APPLIANCES, POWER_KWH, LLM_MODEL, and location constants are imported from config.py

# =========================
# WEATHER INTEGRATION
# =========================
def fetch_weather_24h(
    lat: float = LOCATION_LAT,
    lon: float = LOCATION_LON,
    tz:  str   = LOCATION_TZ,
):
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&hourly=temperature_2m,relative_humidity_2m"
            "&forecast_days=2"
            f"&timezone={tz}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        times = data["hourly"]["time"]
        temps = data["hourly"]["temperature_2m"]
        hums  = data["hourly"]["relative_humidity_2m"]

        now_local = datetime.now(ZoneInfo(tz)).replace(minute=0, second=0, microsecond=0)
        target = now_local.strftime("%Y-%m-%dT%H:00")

        try:
            start_idx = times.index(target)
        except ValueError:
            start_idx = next((i for i, t in enumerate(times) if t > target), 0)

        sel_temps = []
        sel_hums  = []
        for k in range(24):
            idx = (start_idx + k) % len(times)
            sel_temps.append(temps[idx])
            sel_hums.append(hums[idx])

        sel_temps = [int(round(x)) for x in sel_temps]
        sel_hums  = [int(round(x)) for x in sel_hums]

        return {
            "temperature": sel_temps,
            "humidity":    sel_hums,
        }
    except Exception as e:
        print(f"[Agent] Weather fetch failed: {e}. Using defaults.")
        return {
            "temperature": [DEFAULT_TEMPERATURE_C] * 24,
            "humidity":    [DEFAULT_HUMIDITY_PCT]  * 24,
        }

# =========================
# UTILS
# =========================
def parse_price_num(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        m = re.search(r"[-+]?\d*\.?\d+", val)
        if m:
            return float(m.group(0))
    return 0.0

def fix_length(arr: List[int]) -> List[int]:
    arr = [int(x) & 1 for x in list(arr)]
    if len(arr) < 24:
        arr = arr + [0] * (24 - len(arr))
    if len(arr) > 24:
        arr = arr[:24]
    return arr

def time_range_to_hours(start_time: str, end_time: str) -> List[int]:
    def parse_hhmm(s: str) -> int:
        h, m = map(int, s.strip().split(":"))
        if h == 24 and m == 0:
            return 24 * 60
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid HH:MM: {s}")
        return h * 60 + m

    s = parse_hhmm(start_time)
    e = parse_hhmm(end_time)
    if e <= s:
        e += 24 * 60  # overnight

    h_start = s // 60
    h_end   = e // 60  
    hours = [(h % 24) for h in range(h_start, h_end)]
    return sorted(set(hours))

def build_price_map(tou_json: Dict) -> Tuple[Dict[int, Dict], str]:
    for period, values in tou_json.items():
        if period in ("day", "peak", "off_peak"):
            start, end = values["time"].split(" - ")
            tou_json[period]["hours"] = time_range_to_hours(start.strip(), end.strip())

    currency = tou_json.get("currency", "LKR")

    def get_rate_value(band: dict) -> float:
        return parse_price_num(band.get("rate", band.get("price", band.get("tariff", 0))))

    day_price = get_rate_value(tou_json["day"])
    peak_price = get_rate_value(tou_json["peak"])
    off_peak_price = get_rate_value(tou_json["off_peak"])

    price_map: Dict[int, Dict] = {h: {"price": off_peak_price, "band": "off_peak"} for h in range(24)}

    for h in tou_json["day"]["hours"]:
        price_map[h] = {"price": day_price, "band": "day"}
    for h in tou_json["peak"]["hours"]:
        price_map[h] = {"price": peak_price, "band": "peak"}
    for h in tou_json["off_peak"]["hours"]:
        price_map[h] = {"price": off_peak_price, "band": "off_peak"}

    return price_map, currency

def cost_for_states(states: List[int], power_kwh: float, price_map: Dict[int, Dict]) -> float:
    return sum(int(states[h]) * power_kwh * price_map[h]["price"] for h in range(24))

def compare_and_pair_moves(orig: List[int], opt: List[int]) -> List[Tuple[int, int]]:
    removed = [h for h in range(24) if orig[h] == 1 and opt[h] == 0]
    added   = [h for h in range(24) if orig[h] == 0 and opt[h] == 1]
    pairs = []
    for i in range(min(len(removed), len(added))):
        pairs.append((removed[i], added[i]))
    return pairs

def explain_changes(appliance: str,
                    orig: List[int],
                    opt: List[int],
                    price_map: Dict[int, Dict],
                    power_kwh: float) -> Tuple[List[str], float]:
    reasons: List[str] = []
    pairs = compare_and_pair_moves(orig, opt)
    saved_total = 0.0

    if not pairs and orig == opt:
        reasons.append("No changes were required; schedule already avoided peak hours.")
    else:
        for fr, to in pairs:
            pf, bf = price_map[fr]["price"], price_map[fr]["band"]
            pt, bt = price_map[to]["price"], price_map[to]["band"]
            delta = (pf - pt) * power_kwh
            saved_total += max(0.0, delta)
            if bf == "peak" and bt != "peak":
                reasons.append(f"Shifted hour {fr:02d}:00 ({bf}, {pf}) → {to:02d}:00 ({bt}, {pt}) to avoid peak pricing.")
            elif pf > pt:
                reasons.append(f"Moved {fr:02d}:00 → {to:02d}:00 to a cheaper band ({bf}->{bt}).")
            else:
                reasons.append(f"Adjusted {fr:02d}:00 → {to:02d}:00 to respect constraints; no direct price advantage.")

    peak_on_after = [h for h in range(24) if opt[h] == 1 and price_map[h]["band"] == "peak"]
    if peak_on_after:
        hours_str = ", ".join(f"{h:02d}:00" for h in peak_on_after)
        reasons.append(f"Peak hours retained at [{hours_str}] per user permission/instruction.")

    reasons.append(f"Original ON hours: {[h for h in range(24) if orig[h]==1]}")
    reasons.append(f"Optimized ON hours: {[h for h in range(24) if opt[h]==1]}")
    if saved_total > 0:
        reasons.append(f"Estimated savings for {appliance}: {saved_total:.2f} (currency units).")

    return reasons, saved_total

# =========================
# LANGGRAPH STATE DEFINITION
# =========================
class AgentState(TypedDict):
    appliance_demand: Dict[str, Any]
    aggregate_forecast: List[float]
    tou_and_capacity: Dict[str, Any]
    weather: Dict[str, Any]
    user_preference: Dict[str, Any]  # contains 'raw_message', 'allow_peak', and 'preferred_hours'
    price_map: Dict[int, Dict[str, Any]]
    currency: str
    schedules: Dict[str, List[int]]
    explanations: Dict[str, Any]
    error: Optional[str]

# =========================
# TOOL DEFINITIONS
# =========================
def get_appliance_demand() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.abspath(os.path.join(base_dir, '..', '..', 'appliance_data.json'))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Appliance forecast data file not found at {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    demand = {}
    for app in APPLIANCES:
        if app in data:
            orig_states = fix_length(data[app].get("states", [0]*24))
            demand[app] = {
                "required_hours": sum(orig_states),
                "power_rating": POWER_KWH.get(app, 1.0),
                "original_states": orig_states
            }
        else:
            demand[app] = {
                "required_hours": 0,
                "power_rating": POWER_KWH.get(app, 1.0),
                "original_states": [0]*24
            }
    return demand

def get_aggregate_forecast() -> List[float]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.abspath(os.path.join(base_dir, '..', '..', 'aggregate_power_forecast.json'))
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f).get("aggregate_forecast", [0.0]*24)
    
    # Fallback to loading from appliance_data.json
    path_app = os.path.abspath(os.path.join(base_dir, '..', '..', 'appliance_data.json'))
    if os.path.exists(path_app):
        with open(path_app, 'r', encoding='utf-8') as f:
            return json.load(f).get("aggregate_forecast", [0.0]*24)
    
    return [0.0]*24

def get_tou_and_capacity(timeout: int = 30) -> Dict[str, Any]:
    result: Dict[str, str] = {}
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.v5)
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe(MQTT_TOPIC)
            else:
                result['error'] = f"Failed to connect, reason code: {reason_code}"
    except AttributeError:
        client = mqtt.Client()
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                client.subscribe(MQTT_TOPIC)
            else:
                result['error'] = f"Failed to connect, return code: {rc}"

    def on_message(client, userdata, msg):
        result['payload'] = msg.payload.decode(errors="ignore")
        client.disconnect()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    for _ in range(timeout):
        if 'payload' in result or 'error' in result:
            break
        time.sleep(1)
    client.loop_stop()
    
    payload_str = result.get('payload', None)
    if not payload_str:
        raise RuntimeError("MQTT fetch failed: " + result.get('error', 'Timeout waiting for TOU data'))
    
    return json.loads(payload_str)

def get_user_preference() -> str:
    if db is None:
        print("[Agent] Firestore not initialized. Using default user message.")
        return DEFAULT_USER_MSG

    try:
        doc_ref = db.collection("preferences").document("latest")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            msg = data.get("message") or data.get("instruction")
            if msg:
                print(f"[Agent] Retrieved user message from Firestore: '{msg}'")
                return str(msg)
        print("[Agent] User message document/field not found in Firestore. Using default.")
    except Exception as e:
        print(f"[Agent] Failed to read user message from Firestore: {e}. Using default.")
    
    return DEFAULT_USER_MSG

def allocate_schedule(demand: Dict[str, Any],
                      price_map: Dict[int, Dict[str, Any]],
                      capacity_map: Dict[int, float],
                      allow_peak: Dict[str, bool],
                      preferred_hours: Dict[str, Optional[List[int]]],
                      weather: Dict[str, Any]) -> Dict[str, List[int]]:
    schedules: Dict[str, List[int]] = {a: [0]*24 for a in APPLIANCES}
    slot_remaining_capacity = [capacity_map.get(h, FALLBACK_SLOT_CAPACITY_KW) for h in range(24)]

    # Compute comfort indices from weather
    temps = weather.get("temperature", [DEFAULT_TEMPERATURE_C] * 24)
    hums  = weather.get("humidity",    [DEFAULT_HUMIDITY_PCT]  * 24)
    hot_hours  = [h for h in range(24)
                  if temps[h] >= HOT_TEMPERATURE_THRESHOLD_C or hums[h] >= HIGH_HUMIDITY_THRESHOLD_PCT]
    cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMPERATURE_THRESHOLD_C]

    # Helper to check if a slot is adjacent to hot hours
    def is_hot_or_adjacent(h: int) -> bool:
        if h in hot_hours:
            return True
        for dh in [-1, 1]:
            if (h + dh) % 24 in hot_hours:
                return True
        return False

    # Sort appliances by priority: comfort-sensitive and constrained first, then by power rating
    def get_appliance_priority(app: str) -> float:
        score = 0.0
        if app in ['AC_Power', 'Heater_Power']:
            score -= 20.0
        if preferred_hours.get(app) is not None:
            score -= 10.0
        score -= demand[app]["power_rating"]
        return score

    sorted_apps = sorted(APPLIANCES, key=get_appliance_priority)

    # Scrape peak hours from price map
    peak_hours = [h for h in range(24) if price_map[h]["band"] == "peak"]

    for app in sorted_apps:
        req_h = demand[app]["required_hours"]
        p_rating = demand[app]["power_rating"]
        if req_h <= 0:
            continue

        # Find candidate slots
        candidates = list(range(24))
        # User constraint: Peak hours
        if not allow_peak.get(app, False):
            candidates = [h for h in candidates if h not in peak_hours]
        # Custom time constraints
        if preferred_hours.get(app) is not None:
            candidates = [h for h in candidates if h in preferred_hours[app]]

        # Score candidates
        scored_slots = []
        for h in candidates:
            score = price_map[h]["price"]  # Minimize cost
            # Comfort adjustment
            if app == 'AC_Power' and is_hot_or_adjacent(h):
                score += AC_COMFORT_SCORE_BIAS     # Make hot slots extremely attractive
            elif app == 'Heater_Power' and h in cold_hours:
                score += HEATER_COMFORT_SCORE_BIAS # Make cold slots extremely attractive
            scored_slots.append((h, score))

        # Sort slots by score ascending
        scored_slots.sort(key=lambda x: x[1])

        # Allocate greedily respecting capacity
        allocated_count = 0
        allocated_hours = []

        # Pass 1: Strict capacity limit enforcement
        for h, _ in scored_slots:
            if allocated_count >= req_h:
                break
            if slot_remaining_capacity[h] >= p_rating:
                schedules[app][h] = 1
                slot_remaining_capacity[h] -= p_rating
                allocated_hours.append(h)
                allocated_count += 1

        # Pass 2: Soft fallback (if strict capacity limit prevents scheduling the required runtime)
        if allocated_count < req_h:
            print(f"[Agent] Strict capacity limit exceeded for {app}; seeking soft fallback slots.")
            remaining_slots = [h for h, _ in scored_slots if h not in allocated_hours]
            # Sort remaining by least capacity violation (remaining capacity descending), then price
            remaining_slots.sort(key=lambda h: (-slot_remaining_capacity[h], price_map[h]["price"]))
            for h in remaining_slots:
                if allocated_count >= req_h:
                    break
                schedules[app][h] = 1
                slot_remaining_capacity[h] -= p_rating
                allocated_count += 1

    return schedules

# =========================
# GRAPH NODE FUNCTIONS
# =========================
def fetch_data_node(state: AgentState) -> AgentState:
    print("[Node: Fetch Data] Loading files and fetching MQTT/Weather/Firestore...")
    new_state = state.copy()
    try:
        new_state["appliance_demand"] = get_appliance_demand()
        new_state["aggregate_forecast"] = get_aggregate_forecast()
        
        # MQTT TOU & Capacity
        tou_json = get_tou_and_capacity(timeout=MQTT_FETCH_TIMEOUT_SECONDS)
        price_map, currency = build_price_map(tou_json)
        new_state["tou_and_capacity"] = tou_json
        new_state["price_map"] = price_map
        new_state["currency"] = currency

        # Weather
        new_state["weather"] = fetch_weather_24h()
        
        # User message
        new_state["user_preference"] = {
            "raw_message": get_user_preference(),
            "allow_peak": {a: False for a in APPLIANCES},
            "preferred_hours": {a: None for a in APPLIANCES}
        }
        new_state["error"] = None
    except Exception as e:
        print(f"[Node: Fetch Data] Error encountered: {e}")
        new_state["error"] = str(e)
    return new_state

def parse_preferences_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    
    print("[Node: Parse Preferences] Reaching LLM (Ollama) to parse natural language preferences...")
    new_state = state.copy()
    raw_msg = state["user_preference"]["raw_message"]
    
    allow_peak = {a: False for a in APPLIANCES}
    preferred_hours = {a: None for a in APPLIANCES}

    try:
        resp = requests.get("http://localhost:11434", timeout=3)
        if resp.status_code == 200:
            llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
            prompt = f"""
Analyze the user instruction and determine:
1. If peak hours are allowed (true/false) for each appliance.
2. If the user specifies preferred or restricted hour indices (0-23) for any appliance (e.g. 'before 10 AM' -> [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).

Appliances: {list(APPLIANCES)}
User Instruction: "{raw_msg}"

Respond ONLY with a JSON object containing keys: 'allow_peak' (dict) and 'preferred_hours' (dict). No markdown, no comments.
Example:
{{
  "allow_peak": {{
    "AC_Power": true,
    "Heater_Power": false
  }},
  "preferred_hours": {{
    "WashingMachine_Power": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  }}
}}
"""
            out = llm.invoke(prompt).content.strip()
            if out.startswith("```"):
                lines = out.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                out = "\n".join(lines).strip()
            
            parsed = json.loads(out)
            
            # Map values back to canonical appliance names
            parsed_allow = parsed.get("allow_peak", {})
            parsed_pref = parsed.get("preferred_hours", {})

            for appliance in APPLIANCES:
                for k, v in parsed_allow.items():
                    if k.lower() in appliance.lower() or appliance.lower() in k.lower():
                        allow_peak[appliance] = bool(v)
                        break
                
                for k, v in parsed_pref.items():
                    if k.lower() in appliance.lower() or appliance.lower() in k.lower():
                        if isinstance(v, list):
                            preferred_hours[appliance] = [int(h) for h in v]
                        break
    except Exception as e:
        print(f"[Node: Parse Preferences] LLM preference parsing failed: {e}. Using defaults.")

    new_state["user_preference"]["allow_peak"] = allow_peak
    new_state["user_preference"]["preferred_hours"] = preferred_hours
    return new_state

def schedule_allocation_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    print("[Node: Schedule Allocation] Executing capacity-constrained scheduling...")
    new_state = state.copy()
    
    # Map capacity from TOU windows
    # Convert Day, Peak, Off-peak bands to hourly capacity values
    capacity_map = {}
    tou = state["tou_and_capacity"]
    price_map = state["price_map"]
    
    # Available capacity from MQTT
    cap_day      = parse_price_num(tou.get("day",      {}).get("capacity", DEFAULT_CAPACITY_DAY_KW))
    cap_peak     = parse_price_num(tou.get("peak",     {}).get("capacity", DEFAULT_CAPACITY_PEAK_KW))
    cap_off_peak = parse_price_num(tou.get("off_peak", {}).get("capacity", DEFAULT_CAPACITY_OFF_PEAK_KW))
    
    for h in range(24):
        band = price_map[h]["band"]
        if band == "day":
            capacity_map[h] = cap_day
        elif band == "peak":
            capacity_map[h] = cap_peak
        else:
            capacity_map[h] = cap_off_peak

    try:
        opt_schedules = allocate_schedule(
            demand=state["appliance_demand"],
            price_map=state["price_map"],
            capacity_map=capacity_map,
            allow_peak=state["user_preference"]["allow_peak"],
            preferred_hours=state["user_preference"]["preferred_hours"],
            weather=state["weather"]
        )
        new_state["schedules"] = opt_schedules
    except Exception as e:
        new_state["error"] = f"Allocation failed: {e}"
        
    return new_state

def write_results_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    print("[Node: Write Results] Writing JSON outputs and updating Firestore...")
    new_state = state.copy()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output.json'))
    output_explanations_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output_explanations.json'))
    
    schedules = state["schedules"]
    price_map = state["price_map"]
    currency = state["currency"]
    demand = state["appliance_demand"]

    # Write schedules JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedules, f, indent=2)

    # Cost & Explanation Report
    explanations = {
        "per_appliance": {},
        "totals": {"baseline": 0.0, "optimized": 0.0, "savings": 0.0, "percent_savings": 0.0}
    }

    for a in APPLIANCES:
        orig = demand[a]["original_states"]
        opt = schedules[a]
        power_kwh = demand[a]["power_rating"]

        base_cost = cost_for_states(orig, power_kwh, price_map)
        opt_cost  = cost_for_states(opt, power_kwh, price_map)
        reasons, _ = explain_changes(a, orig, opt, price_map, power_kwh)

        explanations["per_appliance"][a] = {
            "original_cost": base_cost,
            "optimized_cost": opt_cost,
            "savings": max(0.0, base_cost - opt_cost),
            "reasons": reasons
        }
        explanations["totals"]["baseline"]  += base_cost
        explanations["totals"]["optimized"] += opt_cost

    explanations["totals"]["savings"] = max(0.0, explanations["totals"]["baseline"] - explanations["totals"]["optimized"])
    if explanations["totals"]["baseline"] > 0:
        explanations["totals"]["percent_savings"] = round(
            100.0 * explanations["totals"]["savings"] / explanations["totals"]["baseline"], 2
        )
    
    # Embed runtime context so the standalone validator can access it
    explanations["user_preference"] = {
        "allow_peak":      state["user_preference"].get("allow_peak",      {a: False for a in APPLIANCES}),
        "preferred_hours": state["user_preference"].get("preferred_hours", {a: None  for a in APPLIANCES}),
        "raw_message":     state["user_preference"].get("raw_message", ""),
    }
    explanations["weather"] = state.get(
        "weather",
        {"temperature": [DEFAULT_TEMPERATURE_C] * 24, "humidity": [DEFAULT_HUMIDITY_PCT] * 24},
    )

    with open(output_explanations_path, 'w', encoding='utf-8') as f:
        json.dump(explanations, f, indent=2)

    # Firestore update
    if db is not None:
        try:
            analysis_data = {}
            for a in APPLIANCES:
                app_info = explanations["per_appliance"][a]
                clean_name = a.replace("_Power", "")
                analysis_data[clean_name] = {
                    "original_cost": round(app_info["original_cost"], 2),
                    "optimized_cost": round(app_info["optimized_cost"], 2),
                    "savings": round(app_info["savings"], 2)
                }
            analysis_data["updated_at"] = datetime.now().isoformat()
            db.collection("analysis").document("latest").set(analysis_data)
            
            schedules_data = {}
            for a in APPLIANCES:
                clean_name = a.replace("_Power", "")
                schedules_data[clean_name] = schedules[a]
            db.collection("schedules").document("latest").set(schedules_data)
            print("Successfully updated Firestore documents.")
        except Exception as fe:
            print(f"Firestore update failed: {fe}")

    new_state["explanations"] = explanations
    return new_state

def fallback_revert_node(state: AgentState) -> AgentState:
    print(f"[Node: Fallback Revert] Execution triggered. Reverting to original predicted states...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output.json'))
    output_explanations_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output_explanations.json'))
    
    fallback_schedules = {}
    try:
        demand = get_appliance_demand()
        for a in APPLIANCES:
            fallback_schedules[a] = demand[a]["original_states"]
    except Exception as e:
        print(f"Failed to read demands for fallback: {e}")
        fallback_schedules = {a: [0]*24 for a in APPLIANCES}

    # Write fallback schedules JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fallback_schedules, f, indent=2)

    # Simple placeholder explanations JSON
    explanations = {
        "error": state.get("error", "General failure occurred"),
        "fallback_active": True,
        "per_appliance": {a: {"original_cost": 0.0, "optimized_cost": 0.0, "savings": 0.0, "reasons": ["Fallback active"]} for a in APPLIANCES},
        "totals": {"baseline": 0.0, "optimized": 0.0, "savings": 0.0, "percent_savings": 0.0}
    }
    with open(output_explanations_path, 'w', encoding='utf-8') as f:
        json.dump(explanations, f, indent=2)
        
    return state

# =========================
# ROUTING FUNCTION
# =========================
def route_after_fetch(state: AgentState):
    if state.get("error"):
        return "fallback_revert"
    return "parse_preferences"

def route_after_parse(state: AgentState):
    if state.get("error"):
        return "fallback_revert"
    return "schedule_allocation"

# =========================
# COMPILE LANGGRAPH GRAPH
# =========================
builder = StateGraph(AgentState)

builder.add_node("fetch_data", fetch_data_node)
builder.add_node("parse_preferences", parse_preferences_node)
builder.add_node("schedule_allocation", schedule_allocation_node)
builder.add_node("write_results", write_results_node)
builder.add_node("fallback_revert", fallback_revert_node)

builder.set_entry_point("fetch_data")

builder.add_conditional_edges(
    "fetch_data",
    route_after_fetch,
    {
        "fallback_revert": "fallback_revert",
        "parse_preferences": "parse_preferences"
    }
)

builder.add_conditional_edges(
    "parse_preferences",
    route_after_parse,
    {
        "fallback_revert": "fallback_revert",
        "schedule_allocation": "schedule_allocation"
    }
)

builder.add_edge("schedule_allocation", "write_results")
builder.add_edge("write_results", END)
builder.add_edge("fallback_revert", END)

graph = builder.compile()

# =========================
# MAIN LOOP
# =========================
def main_once():
    print("\n--- Starting Decision Loop (LangGraph Agent) ---")
    initial_state: AgentState = {
        "appliance_demand": {},
        "aggregate_forecast": [],
        "tou_and_capacity": {},
        "weather": {},
        "user_preference": {},
        "price_map": {},
        "currency": "LKR",
        "schedules": {},
        "explanations": {},
        "error": None
    }
    
    graph.invoke(initial_state)
    print("--- End of Decision Loop ---")

def main_loop():
    while True:
        try:
            main_once()
        except Exception as ex:
            print(f"Error in main loop execution: {ex}")
        print(f"Waiting {AGENT_LOOP_INTERVAL_SECONDS // 60} minutes for next run...")
        time.sleep(AGENT_LOOP_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
