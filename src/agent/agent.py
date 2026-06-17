import paho.mqtt.client as mqtt
import time
import ast
import json
from langchain_ollama import ChatOllama
import ollama
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple
import requests
import os
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "power/tou_domestic"
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

APPLIANCES = [
    'WashingMachine_Power',
    'Heater_Power',
    'AC_Power',
    'VehicleCharger_Power',
    'VacuumCleaner_Power'
]
#Typical Rated Power of appliances
POWER_KWH: Dict[str, float] = {
    'WashingMachine_Power': 0.6,   
    'Heater_Power':         2.0,
    'AC_Power':             1.2,
    'VehicleCharger_Power': 2.2,
    'VacuumCleaner_Power':  1.1,
}

LLM_MODEL = "llama3.2:latest"
LLM_TEMP = 0.0


# =========================
#WEATHER INTIGRATION
# =========================
def fetch_weather_24h(lat: float, lon: float, tz: str = "Asia/Colombo"):

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
        "humidity":    sel_hums     
    }

# --- Colombo, Sri Lanka ---
LAT, LON = 6.9271, 79.8612



# =========================
# MQTT / INPUT
# =========================
def get_mqtt_power_data(timeout: int = 5):

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
    return result.get('payload', result.get('error', 'No data received'))


def get_firestore_user_message() -> str:

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


def read_appliance_status(filename: str) -> Dict[str, Dict[str, List[int]]]:

    status: Dict[str, Dict[str, List[int]]] = {}
    current_appliance = None
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("---") and line.endswith("---"):
            current_appliance = line.replace("-", "").strip()
            status[current_appliance] = {"states": []}
            i += 1
        elif line.lower() == "states:" and current_appliance:
            i += 1
            status[current_appliance]["states"] = [int(x.strip()) for x in lines[i].split(",") if x.strip()]
            i += 1
        else:
            i += 1
    return status

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


def extract_first_array(text: str):

    text = re.sub(r"```[\w\W]*?```", "", text)  # strip fenced blocks
    m = re.search(r"\[[^\[\]]{1,2000}\]", text, re.S)
    return m.group(0) if m else None

# =========================
# PRICE MAP (per hour)
# =========================
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

# =========================
# COSTS + EXPLANATIONS
# =========================
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
        reasons.append(f"Peak hours retained at [{hours_str}] per user permission for this appliance.")

    reasons.append(f"Original ON hours: {[h for h in range(24) if orig[h]==1]}")
    reasons.append(f"Optimized ON hours: {[h for h in range(24) if opt[h]==1]}")
    if saved_total > 0:
        reasons.append(f"Estimated savings for {appliance}: {saved_total:.2f} (currency units).")

    return reasons, saved_total

# =========================
# SCHEDULING RULES / POST
# =========================
def redistribute_peak_violations(schedules: Dict[str, List[int]], tou_json, allow_peak: Dict[str, bool]):
   
    peak_hours = tou_json["peak"]["hours"]
    off_peak_hours = tou_json["off_peak"]["hours"]
    day_hours = tou_json["day"]["hours"]

    for appliance, arr in schedules.items():
        if allow_peak.get(appliance, False):
            continue

        removed_on_count = 0
        for h in peak_hours:
            if arr[h] == 1:
                removed_on_count += 1
                arr[h] = 0

        total_on = sum(arr) + removed_on_count
        filled = sum(arr)
        for hour_list in [off_peak_hours, day_hours, range(24)]:
            for h in hour_list:
                if h in peak_hours:
                    continue
                if arr[h] == 0 and filled < total_on:
                    arr[h] = 1
                    filled += 1
            if filled >= total_on:
                break
        schedules[appliance] = arr
    return schedules



# =========================
# LLM PROMPTS
# =========================
def build_system_prompt(APPLIANCES, status, tou_json, weather, i, allow_peak, user_msg: str):
    appliance = APPLIANCES[i]
    original = status[appliance]["states"]

    # Weather context 
    temps = weather.get("temperature", [25]*24)
    hums  = weather.get("humidity",    [60]*24)

    HOT_TEMP = 28      # °C: 
    HUMID_HOT = 80     # %RH
    COLD_TEMP = 20     # °C: 

    hot_hours  = [h for h in range(24) if temps[h] >= HOT_TEMP or hums[h] >= HUMID_HOT]
    cold_hours = [h for h in range(24) if temps[h] <= COLD_TEMP]

    allow_peak_str = (
        f"For {appliance}, you ARE allowed to schedule ONs during peak hours if needed.\n"
        if allow_peak.get(appliance, False)
        else f"For {appliance}, you are NOT allowed to schedule ONs during peak hours.\n"
    )

    user_instruction = ""
    if user_msg and user_msg.strip():
        user_instruction = f"  • User Request: \"{user_msg}\". Adjust the scheduling of '{appliance}' to satisfy this request (e.g. if the user says 'wash clothes before 10 AM', ensure all ON/1 hours for '{appliance}' are scheduled before hour index 10).\n"

    if appliance == "AC_Power":
        comfort_guidance = (
            f"""Comfort-aware scheduling:
  • Prioritize hours in or adjacent to hot_hours {hot_hours} (T≥{HOT_TEMP}°C or RH≥{HUMID_HOT}%).
  • If peak is not allowed, use the nearest off-peak hours bordering those hot periods.
  • Keep the exact same number of 1s as the original (do not invent extra runtime).
"""
        )
    elif appliance == "Heater_Power":
        comfort_guidance = (
            f"""Comfort-aware scheduling:
  • Prioritize cold_hours {cold_hours} (T≤{COLD_TEMP}°C).
  • Prefer off-peak first, then day; avoid peak unless explicitly allowed.
  • Keep the exact same number of 1s as the original.
"""
        )
    else:
        comfort_guidance = (
            """Weather-neutral scheduling:
  • Ignore temperature/humidity; prefer off-peak first, then day.
  • Avoid peak hours unless explicitly allowed.
  • Keep the exact same number of 1s as the original.
"""
        )

    prompt = f"""You are an Energy Scheduling Expert for a smart home.
Given a single appliance, propose a 24-hour ON/OFF array (0=OFF, 1=ON) obeying the rules.

APPLIANCE: {appliance}
Original predicted states (24h): {original}

Time bands (hour indices 0..23):
  Day: {tou_json['day']['hours']}
  Peak: {tou_json['peak']['hours']}
  Off-peak: {tou_json['off_peak']['hours']}

Weather for next 24 hours (index-aligned with the states):
  temperature_C: {temps}
  humidity_pct: {hums}

Rules (must follow all):
  • Keep exactly the same number of 1s as in the original list.
  • If any 1 is in a peak hour and peak is not allowed, move it to off-peak if possible, otherwise to day.
  • Use only 0 and 1. Length must be 24.
{user_instruction}{allow_peak_str}{comfort_guidance}
Return only a Python list of 24 zeros or ones (no markdown, no commentary).
"""
    return prompt

# =========================
# OUTPUT WRITERS
# =========================
def write_schedules(schedules: Dict[str, List[int]]):
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output.txt'))
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Optimised Appliance Schedules (24-hour ON/OFF)\n\n")
        for name in APPLIANCES:
            arr = schedules.get(name, [])
            if len(arr) != 24:
                raise ValueError(f"{name} does not have exactly 24 states.")
            f.write(f"--- {name} ---\n")
            f.write(f"States: {arr}\n\n")
    print(f"Optimised ON/OFF schedules saved to {output_path}")


def write_explanations(explanations: Dict, currency: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_explanations_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'output_explanations.txt'))
    with open(output_explanations_path, 'w', encoding='utf-8') as f:
        f.write("Scheduling Rationale and Cost Analysis\n")
        f.write("======================================\n\n")
        for name, info in explanations["per_appliance"].items():
            f.write(f"--- {name} ---\n")
            f.write(f"Original cost: {info['original_cost']:.2f} {currency}\n")
            f.write(f"Optimized cost: {info['optimized_cost']:.2f} {currency}\n")
            f.write(f"Savings: {info['savings']:.2f} {currency}\n")
            f.write("Reasons:\n")
            for r in info["reasons"]:
                f.write(f"  - {r}\n")
            f.write("\n")

        f.write("=== TOTALS ===\n")
        f.write(f"Baseline total cost: {explanations['totals']['baseline']:.2f} {currency}\n")
        f.write(f"Optimized total cost: {explanations['totals']['optimized']:.2f} {currency}\n")
        f.write(f"Total savings: {explanations['totals']['savings']:.2f} {currency}\n")
        if explanations['totals']['baseline'] > 0:
            pct = 100.0 * explanations['totals']['savings'] / explanations['totals']['baseline']
            f.write(f"Percent savings: {pct:.2f}%\n")
    print(f"Explanations and cost report saved to {output_explanations_path}")

# =========================
# MAIN LOOP
# =========================
def parse_user_preferences(user_msg: str) -> Dict[str, bool]:
   
    allow_peak: Dict[str, bool] = {appliance: False for appliance in APPLIANCES}
    if not user_msg or not user_msg.strip():
        return allow_peak

    try:
        resp = requests.get("http://localhost:11434", timeout=3)
        if resp.status_code == 200:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model=LLM_MODEL, temperature=0.0)
            prompt = f"""
Analyze the user instruction and determine if peak hours are allowed for each appliance.
Appliances: {list(APPLIANCES)}
User Instruction: "{user_msg}"

For each appliance, set to true if the user permits/allows running during peak hours, and false otherwise.
Respond ONLY with a JSON object. No markdown, no comments.
Example:
{{
  "AC_Power": true,
  "Heater_Power": false
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
            for appliance in APPLIANCES:
                for k, v in parsed.items():
                    if k.lower() in appliance.lower() or appliance.lower() in k.lower():
                        allow_peak[appliance] = bool(v)
                        break
            return allow_peak
    except Exception as e:
        print(f"[Agent] LLM preference parsing failed/skipped: {e}.")

    return allow_peak


def main_once():
    # Read original states
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    appliance_data_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'appliance_data.txt'))
    status = read_appliance_status(appliance_data_path)

    # TOU from MQTT
    print("[Agent] Fetching TOU rates from MQTT broker (timeout=30s)...")
    tou_json_raw = get_mqtt_power_data(timeout=30)
    print(f"[Agent] MQTT raw payload: {tou_json_raw[:120]}")
    try:
        tou_json = json.loads(tou_json_raw)
    except Exception as e:
        print("Failed to parse TOU JSON from MQTT:", e)
        print("Raw payload:", tou_json_raw)
        return

    price_map, currency = build_price_map(tou_json)

    # Weather 
    weather = fetch_weather_24h(LAT, LON)

    # User preferences from Firestore
    print("[Agent] Fetching user instructions from Firestore...")
    user_msg = get_firestore_user_message()
    allow_peak = parse_user_preferences(user_msg)

    # Build schedules using LLM
    llm = None
    try:
        resp = requests.get("http://localhost:11434", timeout=3)
        print(f"[Agent] Ollama reachable (status {resp.status_code}). Using LLM ({LLM_MODEL}) for scheduling.")
        llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMP)
    except Exception as e:
        print(f"[Agent] WARNING: Ollama unreachable: {e}.")
        print(f"[Agent] Falling back: copying appliance states from appliance_data.txt directly to output.txt...")
        fallback_schedules = {
            a: fix_length(status.get(a, {}).get("states", [0]*24))
            for a in APPLIANCES
        }
        write_schedules(fallback_schedules)
        print(f"[Agent] Fallback output written. Exiting.")
        return

    schedules: Dict[str, List[int]] = {}
    required_ons: Dict[str, int] = {}

    print(f"[Agent] Running LLM schedule optimization for {len(APPLIANCES)} appliances...")

    for i, appliance in enumerate(APPLIANCES):
        original = fix_length(status.get(appliance, {}).get("states", [0]*24))
        required_ons[appliance] = sum(original)
        print(f"[Agent]   Processing {appliance} (original ON hours: {sum(original)})")

        sys_prompt = build_system_prompt(APPLIANCES, status, tou_json, weather, i, allow_peak, user_msg)
        user_prompt = "Output ONLY the Python array for this appliance. No explanations, no markdown."
        max_retries = 5
        out = None
        for attempt in range(max_retries):
            try:
                print(f"[Agent]     LLM invoking {LLM_MODEL} for {appliance} (attempt {attempt+1})... (may take 2-5 min on CPU)")
                response = llm.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ])
                out = response.content
                print(f"[Agent]     LLM response received ({len(out)} chars): {out[:80].strip()}...")
                break
            except ollama._types.ResponseError as e:
                print(f"Ollama error: {e}. Retrying in 10s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(10)
            except Exception as e:
                print(f"Unexpected error: {e}. Retrying in 10s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(10)

        if not out:
            print(f"LLM failed for {appliance} after {max_retries} attempts; using original states.")
            schedules[appliance] = original
        else:
            try:
                arr_txt = extract_first_array(out)
                if arr_txt is None:
                    raise ValueError("No list found in LLM output.")
                arr = fix_length(ast.literal_eval(arr_txt))
                schedules[appliance] = arr
            except Exception as e:
                print(f"LLM output parse error for {appliance}: {e}. Using original states.")
                schedules[appliance] = original

    # Post-process schedules
    schedules = redistribute_peak_violations(schedules, tou_json, allow_peak)

    # Validate values
    for a in APPLIANCES:
        arr = schedules[a]
        assert len(arr) == 24, f"{a} does not have 24 elements"
        assert all(v in [0, 1] for v in arr), f"{a} contains non-binary values"
        if not allow_peak.get(a, False):
            for h in tou_json["peak"]["hours"]:
                if arr[h] == 1:
                    raise AssertionError(f"{a} ON during forbidden peak hour {h}")

    # WRITE schedules file
    write_schedules(schedules)

    # COST & REASONS FILE
    explanations = {
        "per_appliance": {},
        "totals": {"baseline": 0.0, "optimized": 0.0, "savings": 0.0}
    }

    for a in APPLIANCES:
        original = fix_length(status.get(a, {}).get("states", [0]*24))
        optimized = schedules[a]
        power_kwh = POWER_KWH.get(a, 1.0)

        base_cost = cost_for_states(original, power_kwh, price_map)
        opt_cost  = cost_for_states(optimized, power_kwh, price_map)
        reasons, _ = explain_changes(a, original, optimized, price_map, power_kwh)

        explanations["per_appliance"][a] = {
            "original_cost": base_cost,
            "optimized_cost": opt_cost,
            "savings": max(0.0, base_cost - opt_cost),
            "reasons": reasons
        }
        explanations["totals"]["baseline"]  += base_cost
        explanations["totals"]["optimized"] += opt_cost

    explanations["totals"]["savings"] = max(0.0, explanations["totals"]["baseline"] - explanations["totals"]["optimized"])
    write_explanations(explanations, currency)

    # WRITE TO FIRESTORE
    if db is not None:
        try:
            print("Writing outputs to Firestore...")
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
            print("Successfully updated analysis/latest in Firestore.")

            schedules_data = {}
            for a in APPLIANCES:
                clean_name = a.replace("_Power", "")
                schedules_data[clean_name] = schedules[a]
                
            db.collection("schedules").document("latest").set(schedules_data)
            print("Successfully updated schedules/latest in Firestore.")
        except Exception as fe:
            print(f"Failed to write to Firestore: {fe}")


def main_loop():
    while True:
        main_once()
        print("Waiting 30 minutes for next run...")
        time.sleep(1800)


if __name__ == "__main__":
    main_loop()
