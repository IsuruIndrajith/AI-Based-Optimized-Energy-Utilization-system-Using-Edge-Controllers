import paho.mqtt.client as mqtt
import json
import random
import time

# MQTT broker details
broker = "localhost"   # Replace with your actual broker IP if needed
port = 1883
topic = "home/power"

# Create MQTT client and connect
client = mqtt.Client()
client.connect(broker, port, 60)

def generate_fake_data():
    """
    Simulate realistic appliance power values
    """
    data = {
        "WashingMachine_Power": round(random.uniform(0, 2500) if random.random() < 0.2 else 0, 2),  # ~20% of time ON
        "Heater_Power": round(random.uniform(0, 2000) if random.random() < 0.4 else 0, 2),           # ~40% ON
        "AC_Power": round(random.uniform(1200, 3000) if random.random() < 0.5 else 0, 2),            # ~50% ON
        "VehicleCharger_Power": round(random.uniform(0, 3500) if random.random() < 0.1 else 0, 2),   # ~10% ON
        "VacuumCleaner_Power": round(random.uniform(800, 1200) if random.random() < 0.15 else 0, 2)  # ~15% ON
    }
    return data

try:
    print("📡 MQTT Publisher running... Press Ctrl+C to stop.")
    while True:
        fake_data = generate_fake_data()
        payload = json.dumps(fake_data)
        client.publish(topic, payload)
        print(f"Published: {payload}")
        time.sleep(0.5)  # send every 5 seconds

except KeyboardInterrupt:
    print("\nExiting...")
    client.disconnect()
