import paho.mqtt.client as mqtt
import json
import numpy as np
import pickle
import random
from tensorflow.keras.models import load_model
import threading
import pandas as pd  

import os

# --- Configurations ---
broker = "localhost"
port = 1883
topic = "home/power"

base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, 'my_lstm_model.keras')
scaler_path = os.path.join(base_dir, 'scaler.pkl')
output_file = os.path.abspath(os.path.join(base_dir, '..', '..', 'appliance_data.txt'))

appliance_names = [
    'WashingMachine_Power',
    'Heater_Power',
    'AC_Power',
    'VehicleCharger_Power',
    'VacuumCleaner_Power'
]
seq_length = 24
initial_fill_samples = 1464 
max_buffer_size = 1464

# --- Load model and scaler ---
model = load_model(model_path)
with open(scaler_path, 'rb') as f:
    scaler = pickle.load(f)

# --- Buffers and Locks ---
data_buffer = []
daily_prediction_store = []
buffer_lock = threading.Lock()
buffer_pointer = 0

states = {}
averages = {}
binary_average_states = {}

# --- Dummy Sample Generator ---
def generate_dummy_sample():
    # Appliance power ratings (max values)
    appliance_max_power = {
        'WashingMachine': 2500,
        'AC': 3000,
        'Heater': 2000,
        'VehicleCharger': 3500,
        'VacuumCleaner': 1200
    }
    # Appliance usage patterns (minutes ON per day)
    patterns = {
        'WashingMachine': {'sessions': 1, 'duration': 120},
        'Heater': {'sessions': 6, 'duration': 30},
        'AC': {'sessions': 2, 'duration': 300},
        'VehicleCharger': {'sessions': 1, 'duration': 300},
        'VacuumCleaner': {'sessions': 3, 'duration': 60}
    }
    # Total minutes in a day
    total_minutes = 1440

    # Generate ON/OFF schedules for each appliance
    schedules = {}
    for app, pat in patterns.items():
        on_minutes = []
        if app == 'VehicleCharger':
            # Prefer night: random start between 22:00 and 2:00 (1320-120)
            start = random.randint(1200, 1380)
            on_minutes = list(range(start, start + pat['duration']))
        else:
            for _ in range(pat['sessions']):
                start = random.randint(0, total_minutes - pat['duration'])
                on_minutes += list(range(start, start + pat['duration']))
        schedules[app] = set(on_minutes)

    # Internal pointer to track current minute in simulation
    if not hasattr(generate_dummy_sample, "minute"):
        generate_dummy_sample.minute = 0

    minute = generate_dummy_sample.minute

    # For each appliance, determine ON/OFF state and assign power
    sample = []
    for app in ['WashingMachine_Power', 'Heater_Power', 'AC_Power', 'VehicleCharger_Power', 'VacuumCleaner_Power']:
        if minute in schedules[app.replace('_Power', '')]:
            power = random.uniform(0.8, 1.0) * appliance_max_power[app.replace('_Power', '')]
        else:
            power = random.uniform(0, 5)
        sample.append(power)

    # Advance minute pointer
    generate_dummy_sample.minute = (minute + 1) % total_minutes

    return sample

# --- Fill Initial Buffer ---
def fill_initial_dummy_data():
    print(f"Filling initial buffer with {initial_fill_samples} dummy samples...")
    with buffer_lock:
        for _ in range(initial_fill_samples):
            data_buffer.append(generate_dummy_sample())
    print("Initial dummy data fill complete.")

def binarize_power_values(power_values, threshold_ratio=0.6):
    """
    Convert continuous power predictions to binary ON/OFF states based on dynamic threshold.

    Parameters:
    - power_values: List or np.array of predicted power values
    - threshold_ratio: Fraction of the max value to determine ON/OFF threshold

    Returns:
    - binary_states: List of 1s (ON) and 0s (OFF)
    """
    power_values = np.array(power_values)
    threshold = threshold_ratio * np.max(power_values)
    binary_states = (power_values >= threshold).astype(int)
    return binary_states

# --- Process and Save States & Averages ---
def process_and_save_predictions(all_day_predictions, appliance_names, output_filename=output_file):
    window_size = 60
    target_windows = 24  # Always produce exactly 24 hourly states
    num_windows = len(all_day_predictions) // window_size

    # If we have more windows than needed, use the last 24; if fewer, use what we have
    num_windows = min(num_windows, target_windows)

    for idx, appliance_name in enumerate(appliance_names):
        power_series = all_day_predictions[:, idx]
        # Use only the last (target_windows * window_size) predictions
        power_series = power_series[-(num_windows * window_size):]
        avg_list = []

        # Compute averages for each window
        for i in range(num_windows):
            window = power_series[i * window_size : (i + 1) * window_size]
            avg = np.mean(window)
            avg_list.append(avg)

        # Pad to exactly 24 if fewer windows (edge case)
        while len(avg_list) < target_windows:
            avg_list.append(avg_list[-1] if avg_list else 0.0)

        # Set different threshold_ratio based on appliance name
        if appliance_name in ['AC_Power', 'Heater_Power', 'WashingMachine_Power']:
            threshold_ratio = 0.6
        else:
            threshold_ratio = 0.8

        binary_states = binarize_power_values(avg_list, threshold_ratio=threshold_ratio)
        
        # Populate global dictionaries
        averages[appliance_name] = np.array(avg_list)
        binary_average_states[appliance_name] = binary_states
        
        # For compatibility with agent.py which parses "States:" as the ON/OFF states
        states[appliance_name] = binary_states

    with open(output_filename, 'w') as f:
        for appliance_name in appliance_names:
            f.write(f"--- {appliance_name} ---\n")
            f.write("States:\n")
            if appliance_name in states:
                states_line = ', '.join(map(str, states[appliance_name].tolist()))
                f.write(states_line + '\n')
            else:
                f.write("States data not available\n")
                
            f.write("Averages:\n")
            if appliance_name in averages:
                avg_line = ', '.join(map(lambda val: f"{val:.4f}", averages[appliance_name].tolist()))
                f.write(avg_line + '\n')
            else:
                f.write("Averages data not available\n")
                
            f.write("Binary Average States:\n")
            if appliance_name in binary_average_states:
                binary_line = ', '.join(map(str, binary_average_states[appliance_name].tolist()))
                f.write(binary_line + '\n')
            else:
                f.write("Binary average states data not available\n")
            f.write("\n")

    print(f"Predictions and binary states saved to {output_filename}")

# --- Run Prediction ---
def predict_on_buffer(buffer):
    global daily_prediction_store
    data_array = np.array(buffer)
    df = pd.DataFrame(data_array, columns=appliance_names)
    scaled_data = scaler.transform(df)

    x = [scaled_data[i:i + seq_length] for i in range(len(scaled_data) - seq_length)]
    x = np.array(x)

    preds_scaled = model.predict(x, verbose=0)
    preds = scaler.inverse_transform(preds_scaled)

    # Use only the latest prediction for each appliance
    latest_pred = preds[-1]  # shape: (num_appliances,)
    print("\n--- Appliance Averages and Binary States (Latest Prediction) ---")
    for idx, appliance in enumerate(appliance_names):
        avg = latest_pred[idx]
        # Set threshold_ratio based on appliance type
        threshold_ratio = 0.6 if appliance in ['AC_Power', 'Heater_Power', 'WashingMachine_Power'] else 0.8
        threshold = threshold_ratio * np.max(latest_pred)
        binary_state = int(avg >= threshold)
        print(f"{appliance}: Average={avg:.4f}, Binary State={binary_state}")

    daily_prediction_store.extend(preds.tolist())
    if len(daily_prediction_store) > 1440:
        daily_prediction_store = daily_prediction_store[-1440:]  # Keep last 24 hours

    # Always update the file with the latest predictions
    process_and_save_predictions(np.array(daily_prediction_store), appliance_names)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(topic)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global data_buffer, buffer_pointer
    try:
        payload = json.loads(msg.payload.decode())
        values = [float(payload[appliance]) for appliance in appliance_names]

        with buffer_lock:
            if len(data_buffer) < max_buffer_size:
                data_buffer.append(values)
                print(f"Added sensor sample at index {len(data_buffer)-1}: {values}")
            else:
                data_buffer[buffer_pointer] = values
                print(f"Replaced sensor sample at index {buffer_pointer}: {values}")
                buffer_pointer = (buffer_pointer + 1) % max_buffer_size

            if len(data_buffer) >= seq_length + 30 and len(data_buffer) % 30 == 0:
                if len(data_buffer) == max_buffer_size:
                    ordered_buffer = data_buffer[buffer_pointer:] + data_buffer[:buffer_pointer]
                else:
                    ordered_buffer = data_buffer
                print("\nRunning prediction on buffered data (last 30 samples)...")
                recent_buffer = ordered_buffer[-(seq_length + 30):]
                predict_on_buffer(recent_buffer)
    except Exception as e:
        print(" Error processing MQTT message:", e)

def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to MQTT broker at {broker}:{port}...")
    client.connect(broker, port, 60)
    client.loop_forever()

# --- Main Execution ---
if __name__ == "__main__":
    fill_initial_dummy_data()
    with buffer_lock:
        print("\nRunning prediction on initial dummy data...")
        predict_on_buffer(data_buffer)
        data_buffer = []
    mqtt_loop()
