import time
import requests
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt
import json
import os

# ---------------------------------------------------------------------------
# Load grid capacity limits from external config (capacity_config.json).
# This file sits at the project root and can be edited without touching code.
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'capacity_config.json')
)
_FALLBACK_CAPACITIES = {"day": 3.5, "peak": 1.5, "off_peak": 5.0}


def load_capacity_config() -> dict:
    """Read capacity_config.json and return band→kW mapping.
    Falls back to _FALLBACK_CAPACITIES if the file is absent or malformed."""
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        # Validate expected keys
        caps = {
            band: float(cfg.get(band, _FALLBACK_CAPACITIES[band]))
            for band in ("day", "peak", "off_peak")
        }
        print(f"[TOU Publisher] Capacity loaded from {_CONFIG_PATH}: {caps}")
        return caps
    except Exception as e:
        print(f"[TOU Publisher] Could not read capacity_config.json ({e}). Using fallback defaults.")
        return dict(_FALLBACK_CAPACITIES)


while True:
    try:
        # -- 1. Scrape the page --
        url = "https://www.leco.lk/pages_e.php?id=86"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", class_="table")
        if not table:
            raise Exception("Could not find table with TOU data!")

        tou_found = False
        tou_data = {}
        rows = table.find_all("tr")

        for i, row in enumerate(rows):
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cols:
                continue
            if "Domestic – Optional Time of Use Tariff" in cols[0]:
                tou_found = True
                continue
            if tou_found and ("Day(" in cols[0] or "Peak" in cols[0] or "Off-peak" in cols[0]):
                label = None
                time_range = None
                rate = None

                if "Day(" in cols[0]:
                    label = "day"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                elif "Peak" in cols[0]:
                    label = "peak"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                elif "Off-peak" in cols[0]:
                    label = "off_peak"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                    for dash in ['\u2013', '\u2014', '–', '—']:
                        time_range = time_range.replace(dash, '-')

                try:
                    rate = float(cols[1].replace(",", ""))
                except:
                    rate = None

                tou_data[label] = {
                    "rate": rate,
                    "time": time_range,
                    "capacity": None   # filled below from capacity_config.json
                }
            elif tou_found and not ("Day(" in cols[0] or "Peak" in cols[0] or "Off-peak" in cols[0]):
                break

        # -- 2. Attach capacity values read from capacity_config.json --
        capacities = load_capacity_config()
        for band in ("day", "peak", "off_peak"):
            if band in tou_data:
                tou_data[band]["capacity"] = capacities[band]

        tou_data["currency"] = "LKR"

        print("TOU data to publish:", tou_data)

        # -- 3. Publish to MQTT broker --
        MQTT_BROKER = "test.mosquitto.org"
        MQTT_PORT = 1883
        MQTT_TOPIC = "power/tou_domestic"

        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        payload = json.dumps(tou_data)
        print(f"Publishing TOU data: {payload}")
        client.publish(MQTT_TOPIC, payload=payload, qos=1, retain=True)
        print(f"Published TOU data to MQTT topic {MQTT_TOPIC}: {payload}")

        client.disconnect()

    except Exception as e:
        print("Error:", e)

    print("Waiting 5 minutes before next update...\n")
    time.sleep(300)
