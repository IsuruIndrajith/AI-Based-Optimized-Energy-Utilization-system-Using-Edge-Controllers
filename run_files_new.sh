#!/bin/bash

PROJECT_DIR="$(pwd)"

# --- Start Ollama LLM Server ---
echo "[+] Checking Ollama server..."
if curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "[OK] Ollama is already running at localhost:11434."
else
    echo "[+] Starting Ollama server..."
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "[+] Ollama started (PID $OLLAMA_PID). Waiting 5s to be ready..."
    sleep 5
fi

# --- Start MQTT Broker (Mosquitto) ---
echo "[+] Starting Mosquitto MQTT broker..."
sudo service mosquitto start || sudo systemctl start mosquitto || mosquitto -d 2>/dev/null
echo "[OK] Mosquitto broker setup complete."

# --- MQTT Publishers (background) ---
echo "[+] Starting MQTT Publisher scripts..."
(
    source .venv/bin/activate
    python3 src/mqtt/publish_tou_test.py &
    python3 src/mqtt/publish_dummy_sensor.py &
    deactivate
    echo "[OK] MQTT Publishers finished."
) &

sleep 10

# --- LSTM Predictor  ---
echo "[+] Running LSTM Predictor (waiting for it to write appliance_data.txt)..."
source .venv/bin/activate
timeout 120 python3 src/predictor/Run_LSTM.py
deactivate
echo "[OK] LSTM Predictor finished. appliance_data.txt is ready."

# --- LLM Agent  ---
echo "[+] Starting LLM Agent script (with Ollama LLM scheduling)..."
(
    source .venv/bin/activate
    python3 src/agent/agent.py
    deactivate
    echo "[OK] LLM Agent finished."
) &

echo ""
echo "------------------------------------"
echo "[OK] All scripts executing."
echo "[OK] MQTT Publisher running in background."
echo "[OK] LLM Agent running with Ollama-powered scheduling."
echo "------------------------------------"

wait
