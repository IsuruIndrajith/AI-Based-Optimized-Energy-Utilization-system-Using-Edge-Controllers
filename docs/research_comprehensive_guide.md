# AI-Based Optimized Energy Utilization System Using Edge Controllers
## Comprehensive Research Documentation & System Architecture Guide

---

## 1. Executive Summary & Research Motivation

Rapid urbanization and increasing reliance on high-power domestic appliances (HVAC, Water Heaters, EV Chargers, Washing Machines) have significantly amplified peak load burdens on electrical distribution grids. Traditional residential energy management systems rely on static timer schedules or rule-based heuristics that fail to adapt dynamically to variable Time-of-Use (TOU) tariffs, changing microclimate conditions, dynamic grid capacity limits, and natural-language user preferences.

This project implements an **AI-based Optimized Energy Utilization System deployed on Edge Controllers**. It integrates:
1. **Deep Learning Demand Forecasting**: A multi-output Long Short-Term Memory (LSTM) network predicting 24-hour appliance-level energy consumption.
2. **Natural Language Preference Parsing**: A local Large Language Model (Ollama with `llama3.2`) that translates unconstrained user prompts (e.g., *"Do not run the washing machine after 6 PM"*) into strict scheduling rules.
3. **Multi-Objective Optimization Engine**: A hybrid heuristic solver embedded within a **LangGraph state graph** that optimizes energy cost while strictly enforcing grid capacity constraints, binary schedule constraints, and thermal comfort bounds.
4. **Deterministic Policy Validation Engine**: A 40-scenario controlled benchmark framework evaluating Grid Capacity Compliance, Cost Reduction, Weather Comfort Alignment, and User Preference Compliance without LLM bias.

---

## 2. Core Research Claims & Objectives

The research system is benchmarked against six core scientific claims:

| Claim ID | Title | Objective & Validation Criteria |
| :--- | :--- | :--- |
| **Claim 1** | **LSTM Forecasting Accuracy** | Multi-step LSTM accurately predicts 24-hour individual and aggregate power consumption patterns. |
| **Claim 2** | **Grid Capacity Compliance** | Total scheduled household demand $P_{\text{total}}(t)$ must never exceed grid capacity $C_{\text{band}}(t)$ at any hour $t \in [0, 23]$. |
| **Claim 3** | **Binary Schedule Validity** | Appliance schedules must consist of valid binary states $S_a(t) \in \{0, 1\}$ across all 24 hours. |
| **Claim 4** | **LLM Preference Compliance** | User natural-language constraints (`allow_peak`, `preferred_hours`) parsed by Ollama must be 100% satisfied by the generated schedule. |
| **Claim 5** | **Cost Reduction** | The optimized schedule must achieve demonstrable cost savings compared to un-optimized baseline demand ($\ge 20\%$ cost reduction target). |
| **Claim 6** | **Weather Comfort Alignment** | High-power environmental appliances (AC / Heater) must run during extreme weather windows (hot/humid or cold) to preserve user comfort. |

---

## 3. Comprehensive System Architecture

The edge architecture consists of decoupled microservices communicating asynchronously via MQTT and local filesystem/cloud JSON stores.

```
                  ┌─────────────────────────────────────────┐
                  │          External Interfaces            │
                  │   Open-Meteo API / Firebase / MQTT      │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Edge Controller                                 │
│                                                                             │
│  ┌───────────────────────┐             ┌─────────────────────────────────┐  │
│  │   MQTT Publishers     │             │     LSTM Predictor Node         │  │
│  │  - Sensor Telemetry   ├────────────►│  - Preprocessing & MinMaxScaler │  │
│  │  - TOU Tariff Maps    │             │  - 24-step Neural Inference     │  │
│  └───────────────────────┘             └────────────────┬────────────────┘  │
│                                                         │                   │
│                                                         ▼                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │               LangGraph Multi-Agent Decision Engine                   │  │
│  │                                                                       │  │
│  │  1. fetch_data_node          (MQTT, Open-Meteo, Forecast, Time Lock)  │  │
│  │  2. parse_preferences_node (Ollama llama3.2 NLP extraction)           │  │
│  │  3. schedule_allocation_node (Heuristic / Constraint Solver)          │  │
│  │  4. write_results_node       (JSON Artifacts & Cloud Sync)            │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
│                                     │                                       │
│                                     ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              Deterministic Policy Validation Framework                │  │
│  │  - 40 Controlled Scenarios (CS01, CAP01, W01, U01)                    │  │
│  │  - Automated Plotting & LaTeX Report Generation                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component & Module Deep Dive

### 4.1 Centralized Configuration (`src/config.py`)
Houses canonical appliance definitions, default fallback values, and LECO (Lanka Electricity Company) 2024 TOU domestic tariff schedules:

* **Target Appliances (`APPLIANCES`)**:
  * `WashingMachine_Power` ($0.6 \text{ kW}$)
  * `Heater_Power` ($2.0 \text{ kW}$)
  * `AC_Power` ($1.2 \text{ kW}$)
  * `VehicleCharger_Power` ($2.2 \text{ kW}$)
  * `VacuumCleaner_Power` ($1.1 \text{ kW}$)

* **LECO TOU Tariff Rates**:
  * **Off-Peak** (`22:30 – 05:30`): $33.0 \text{ LKR/kWh}$, Capacity Limit: $6.0 \text{ kW}$
  * **Day** (`05:30 – 18:30`): $47.0 \text{ LKR/kWh}$, Capacity Limit: $4.0 \text{ kW}$
  * **Peak** (`18:30 – 22:30`): $106.0 \text{ LKR/kWh}$, Capacity Limit: $2.5 \text{ kW}$

---

### 4.2 Deep Learning Demand Forecasting (`src/predictor/Run_LSTM.py`)
* **Model Architecture**: Multi-layer LSTM model saved as `my_lstm_model.keras` ($575 \text{ KB}$).
* **Feature Scaling**: Uses `sklearn.preprocessing.MinMaxScaler` (`scaler.pkl`).
* **Input Buffer**: Accumulates 1,464 historical sensor samples ($61 \text{ days} \times 24 \text{ hours}$).
* **Output Payload (`appliance_data.json`)**: Produces 24 hourly power predictions ($W$) per appliance, alongside aggregate household energy demand.

---

### 4.3 MQTT Telemetry & Grid Simulation (`src/mqtt/`)
* **`publish_dummy_sensor.py`**: Publishes synthetic real-time power telemetry for active household appliances to MQTT broker (`localhost:1883`).
* **`publish_tou_test.py`**: Reads `capacity_config.json` and broadcasts dynamic TOU pricing structure and grid capacity thresholds to topic `power/tou_domestic`.

---

### 4.4 Agent Decision Engine (`src/agent/agent.py`)
Built on **LangGraph state graph**, executing a 4-node decision loop:

1. **`fetch_data_node`**:
   * Collects MQTT TOU pricing, weather forecast from Open-Meteo (`Colombo, LK`), and predictions from `appliance_data.json`.
   * **Elapsed Time Lock**: Detects local wall-clock hour $H_{\text{current}}$. Locks hours $0 \dots (H_{\text{current}} - 1)$ to OFF (`0`) to prevent rescheduling past hours.

2. **`parse_preferences_node`**:
   * Sends user raw text (from Firestore or CLI) to Ollama (`llama3.2:latest`).
   * Extracts structured JSON:
     * `allow_peak`: Boolean mask per appliance.
     * `preferred_hours`: Allowed hour index lists or `null`.

3. **`schedule_allocation_node`**:
   * Computes required daily operating hours $req\_h = \text{round}\left(\frac{\sum P_{\text{predicted}}}{P_{\text{rated}}}\right)$.
   * Filters candidate slots by removing peak hours if `allow_peak=False` or non-preferred hours if `preferred_hours` is set.
   * Applies comfort score bias ($\text{AC\_COMFORT\_SCORE\_BIAS} = -100.0$) during hot ($T \ge 28^\circ\text{C}$) or humid ($RH \ge 80\%$) hours.
   * Allocates load greedily respecting remaining slot grid capacity ($C_{\text{band}}(t)$).

4. **`write_results_node`**:
   * Exports finalized binary schedule to `output.json`.
   * Calculates baseline vs optimized cost comparison and exports explanations to `output_explanations.json`.

---

### 4.5 Multi-Scenario Controlled Benchmark (`src/agent/validate_policies_multiscenario.py`)
Executes a controlled 40-scenario benchmark grouped into 4 distinct testing categories:

1. **Group CS01 (Varying TOU Pricing)**: Tests cost reduction across 10 tariff variations ranging from cheap flat rates to hyper-peak tariffs ($400 \text{ LKR/kWh}$).
2. **Group CAP01 (Varying Grid Capacity)**: Tests capacity compliance under tight grid limits ($1.0 \text{ kW} – 10.0 \text{ kW}$).
3. **Group W01 (Varying Microclimate)**: Tests AC/Heater comfort alignment across ambient temperatures ($14^\circ\text{C} – 38^\circ\text{C}$) and humidity levels ($50\% – 90\%$).
4. **Group U01 (Natural Language User Preferences)**: Tests LLM extraction and schedule compliance across 10 diverse natural-language user prompts.

---

## 5. Mathematical Formulation

### 5.1 Required Operating Hours
$$\text{req\_h}_a = \text{clamp}\left( \text{round}\left( \frac{\sum_{t=0}^{23} P_{a,\text{predicted}}(t)}{P_{a,\text{rated}} \cdot 1000} \right), 0, 24 \right)$$

### 5.2 Objective Function (Cost Minimization)
$$\min_{S_a(t) \in \{0, 1\}} \sum_{t=0}^{23} \sum_{a \in \mathcal{A}} S_a(t) \cdot P_{a,\text{rated}} \cdot \text{Tariff}(t) + \sum_{t=0}^{23} \text{ComfortPenalty}(t)$$

### 5.3 Operational Constraints
1. **Grid Capacity Limit**:
   $$\sum_{a \in \mathcal{A}} S_a(t) \cdot P_{a,\text{rated}} \le C_{\text{band}}(t), \quad \forall t \in [0, 23]$$

2. **Time Exclusion Constraint**:
   $$S_a(t) = 0, \quad \forall t \in \text{PeakHours} \quad \text{if } \text{allow\_peak}_a = \text{False}$$

3. **Time Window Constraint**:
   $$S_a(t) = 0, \quad \forall t \notin \text{preferred\_hours}_a \quad \text{if } \text{preferred\_hours}_a \neq \text{null}$$

4. **Elapsed Time Lock**:
   $$S_a(t) = 0, \quad \forall t < H_{\text{current}}$$

---

## 6. Execution & Deployment Guide

### 6.1 Running in Windows / WSL Environment
1. **Fix Shell Line Endings & Set Execution Permissions**:
   ```bash
   sed -i 's/\r$//' run_files_new.sh
   chmod +x run_files_new.sh
   ```

2. **Execute Full Orchestration Script**:
   ```bash
   ./run_files_new.sh
   ```

3. **Run 40-Scenario Policy Validation Suite**:
   ```bash
   python src/agent/validate_policies_multiscenario.py
   ```

4. **Generate Visualization Plots**:
   ```bash
   python plot_policy_validation.py
   python plot_validation.py
   ```

---

## 7. Artifact Directory Structure

```
.
├── docs/                                 # Research documentation, thesis, & paper source
│   ├── research_comprehensive_guide.md   # [This Document] Full System Guide
│   ├── research_flow.md                  # Workflow diagram & theoretical pipeline
│   ├── architecture.mmd                  # Mermaid diagram source for system architecture
│   ├── research_paper.tex                # IEEE conference format publication paper
│   └── research_thesis.tex               # Full academic thesis chapter draft
├── src/                                  # Source codebase
│   ├── config.py                         # System constants, appliance power, LECO rates
│   ├── agent/                            # LangGraph agent & validation modules
│   │   ├── agent.py                      # Main decision engine & node definitions
│   │   ├── validate_policies.py          # Deterministic policy rules engine
│   │   ├── validate_policies_multiscenario.py # 40-scenario controlled benchmark
│   │   ├── benchmark.py                  # Performance benchmark scripts
│   │   └── simulate.py                   # Simulation runner
│   ├── predictor/                        # Deep learning forecast modules
│   │   ├── Run_LSTM.py                   # 24-hour demand prediction script
│   │   └── my_lstm_model.keras           # Trained multi-output Keras model
│   └── mqtt/                             # MQTT publisher services
│       ├── publish_dummy_sensor.py       # Live power telemetry simulator
│       └── publish_tou_test.py           # TOU tariff & capacity publisher
├── run_files_new.sh                      # Shell orchestrator script
├── appliance_data.json                   # Generated LSTM appliance power forecasts
├── output.json                           # Final optimized 24-hour binary schedule
├── output_explanations.json              # Baseline vs optimized cost breakdown
└── validation_report_multiscenario.json # 40-scenario benchmark evaluation report
```
