# 📝 Research Paper Writing Guide
### AI-Based Optimized Energy Utilization System Using Edge Controllers
#### EC8070 — Research Project III

> This guide maps each section of the EC8070 marking rubric to the **actual content we have built and documented** in this project. Use it as a blueprint to write your four-page paper.

---

## ⚡ Quick Facts

| Item | Detail |
|------|--------|
| **Max Pages** | 4 (strictly enforced — late = 0 marks) |
| **Formatting** | Justified text, content page, no typos |
| **Submission** | One member per group submits the manuscript |
| **Total Marks** | 100 marks across 10 sections |

---

## 📋 Section-by-Section Paper Blueprint

---

### 1. 🏷️ Title Block — (05 Marks)

**Target:** Clear, specific, and concise.

**Suggested Title:**
> *AI-Based Optimized Energy Utilization System Using Edge Computing Controllers with LSTM Prediction and LLM-Assisted Scheduling*

**Author block must include:**
- Full names of all group members in agreed order
- Student IDs / Registration numbers
- Department, Faculty, University
- Year / Semester

**Checklist:**
- [ ] Title reflects both LSTM prediction AND edge-agent optimization
- [ ] Author order confirmed with the group
- [ ] Affiliation is correctly spelled

---

### 2. 📄 Abstract — (10 Marks)

**Target:** ~150–200 words covering all four elements below.

**Draft Structure:**

| Element | What to Write (From Our Project) |
|---|---|
| **Purpose** | The research addresses the growing household energy waste problem by intelligently shifting appliance load away from expensive peak tariff hours. |
| **Methodology** | An LSTM model trained on historical appliance power data predicts 24-hour ON/OFF schedules; a multi-modal edge agent then re-optimizes them using Time-of-Use (TOU) pricing (from MQTT), real-time weather data (from Open-Meteo), and a local LLM (Llama 3.2 via Ollama) with hard constraint enforcement. |
| **Key Findings** | The system achieves measurable cost savings by shifting loads from peak (LKR 67/kWh) to off-peak (LKR 21/kWh) periods while maintaining the same total appliance runtime. |
| **Conclusion & Implication** | The edge-deployed pipeline demonstrates that low-cost hardware can perform meaningful AI-based energy optimization without cloud dependency, enabling scalable smart grid adoption. |

**Checklist:**
- [ ] All four elements are present
- [ ] Does not exceed ~200 words
- [ ] Written in past tense (research was conducted)
- [ ] No references cited in abstract

---

### 3. 🔑 Keywords — (05 Marks)

**Suggested keywords (6–8 terms):**

```
Edge Computing, Energy Optimization, LSTM, Time-of-Use Pricing,
LLM Scheduling, Smart Home, Demand Response, IoT
```

**Why each term:**
- **Edge Computing** — the agent runs on-device (e.g., Raspberry Pi)
- **LSTM** — the predictor model architecture
- **Time-of-Use Pricing** — the core tariff mechanism used
- **LLM Scheduling** — Llama 3.2 via Ollama optimizes schedules
- **Demand Response** — the energy management category
- **Smart Home / IoT** — the application domain

**Checklist:**
- [ ] 6–8 keywords provided
- [ ] Searchable by other researchers
- [ ] Not repeated from title (add new dimensions)

---

### 4. 📖 Introduction — (10 Marks)

**Target:** ~250–350 words. Structure as 5 paragraphs.

#### Paragraph 1 — Background
Rising electricity costs and increasing household energy consumption are driving demand for smart energy management. In Sri Lanka, domestic tariffs vary significantly across peak (LKR 67/kWh), day (LKR 35/kWh), and off-peak (LKR 21/kWh) bands under the Time-of-Use (TOU) pricing structure.

#### Paragraph 2 — Research Problem
Without intelligent scheduling, household appliances (washing machines, heaters, air conditioners, EV chargers, vacuum cleaners) are operated by users at arbitrary times, often coinciding with expensive peak tariff bands, leading to unnecessary energy expenditure.

#### Paragraph 3 — Aim and Objectives
- **Aim:** Design and implement an edge-deployable AI system that automatically optimizes home appliance schedules to minimize electricity bills.
- **Objectives:**
  1. Train an LSTM model to predict 24-hour appliance usage patterns.
  2. Develop an edge agent that fetches live TOU tariffs and weather data.
  3. Use a local LLM to intelligently re-schedule loads within hard constraints.
  4. Validate the savings and expose results via a mobile-accessible API.

#### Paragraph 4 — Literature Review *(cite 4–6 papers here)*
Reference prior work on:
- LSTM for time-series energy forecasting
- Demand-side management and peak-load shifting
- LLM-based reasoning for IoT/smart-grid applications
- Edge AI deployment on Raspberry Pi

#### Paragraph 5 — Expected Contributions
- A novel hybrid pipeline (LSTM + LLM + rule-based post-processing) running fully on an edge device.
- Weather-aware scheduling (heat/cold hours mapped to AC/heater preferences).
- Cloud integration (Firebase Firestore) with a Flutter mobile dashboard.

**Checklist:**
- [ ] Background, problem, aim, literature gap, and contributions all covered
- [ ] At least 4 in-text citations in this section
- [ ] Research gap is explicitly stated

---

### 5. 🔬 Methodology — (20 Marks)

> This is the **highest-weighted section**. Be thorough and reproducible.

**Target:** ~500–600 words + 1–2 architecture diagrams.

#### 5.1 System Architecture

Describe the two-stage pipeline:

```
Stage 1 — LSTM Predictor
MQTT (power telemetry) → Circular Buffer → MinMaxScaler
→ Overlapping 24-step sequences → LSTM model
→ Binarized ON/OFF states → appliance_data.txt

Stage 2 — Optimization Agent
appliance_data.txt + MQTT TOU tariffs + Open-Meteo weather
→ System Prompt → Llama 3.2 (local Ollama)
→ Peak redistribution + Runtime correction
→ Optimized schedule → Firestore → Flutter App
```

#### 5.2 LSTM Model (from `of_Research_LSTM.ipynb`)

| Step | Detail |
|---|---|
| **Dataset** | Synthetic/real appliance power data (CSV with 5 appliance columns) |
| **Preprocessing** | MinMaxScaler normalization, Timestamp column removal |
| **Sequence Length** | 24 time-steps (one past day used to predict next hour) |
| **Architecture** | `LSTM(64) → Dense(5)` |
| **Optimizer** | Adam |
| **Output** | Continuous power predictions → binarized to 0/1 using dynamic threshold |
| **Saved Artifacts** | `lstm_model.h5`, `scaler.pkl` |

#### 5.3 Edge Optimization Agent (from `src/agent/agent.py`)

| Component | Implementation |
|---|---|
| **TOU Data** | Subscribed via MQTT (`test.mosquitto.org`, topic: `power/tou_domestic`) |
| **Weather** | Open-Meteo REST API → 24h temperature & humidity for Colombo (6.9271 N, 79.8612 E) |
| **LLM** | Llama 3.2 (`llama3.2:latest`) via Ollama, temperature = 0.0 |
| **Constraints** | Peak hours avoided by default; user preference toggle supported |
| **Post-processing** | `redistribute_peak_violations()` + `enforce_required_ons_improved()` |
| **Output** | `output.txt` (schedules), `output_explanations.txt` (savings), Firestore |

#### 5.4 Weather-Aware Rules

| Condition | Applied Rule |
|---|---|
| Temp >= 28 C OR Humidity >= 80% | AC prioritized ON in those hours |
| Temp <= 20 C | Heater prioritized ON in cold hours |
| Other appliances | Scheduled purely by price minimization |

#### 5.5 Hard Constraint Post-Processing

1. **`redistribute_peak_violations()`** — Any ON-hour that falls in the peak band (where not permitted) is moved to the cheapest available non-peak hours.
2. **`enforce_required_ons_improved()`** — Ensures the total count of ON hours per appliance remains identical to the predicted baseline (prevents the optimizer from turning appliances off entirely to save money).

#### 5.6 Cost Calculation

Cost = Sum over 24 hours of: State(h) * Power_kWh * Price(h)

Savings = Original Cost - Optimized Cost (reported per appliance and in total).

#### 5.7 Data Flow and Ethical Considerations

- **Data:** Synthetic appliance data used; no personally identifiable information is collected.
- **Reproducibility:** Full source code and configuration available in the repository.
- **Limitations:** Real household data would improve LSTM accuracy; TOU tariff data assumes Sri Lanka domestic pricing.

**Checklist:**
- [ ] Architecture diagram included (use the Mermaid from `agent_explanation.md`)
- [ ] LSTM and Agent both described
- [ ] Post-processing rules explained with rationale
- [ ] Cost formula stated
- [ ] Ethical considerations addressed
- [ ] Limitations acknowledged

---

### 6. 📊 Results — (20 Marks)

> Second highest-weighted section. Show tables and figures.

**Target:** ~400–500 words + results tables.

#### 6.1 LSTM Prediction Accuracy

Report from the training notebook:
- Training/Validation Loss curves (plot from Cell 7 of notebook)
- RMSE or MAE on test set per appliance
- Visual comparison: actual vs. predicted power for one appliance

#### 6.2 Optimization Cost Savings

Create a table like:

| Appliance | Original Cost (LKR) | Optimized Cost (LKR) | Savings (LKR) |
|---|---|---|---|
| WashingMachine | e.g., 36.0 | e.g., 12.6 | 23.4 |
| Heater | e.g., 134.0 | e.g., 42.0 | 92.0 |
| AC | e.g., 80.4 | e.g., 50.4 | 30.0 |
| VehicleCharger | e.g., 46.2 | e.g., 46.2 | 0.0 |
| VacuumCleaner | e.g., 22.7 | e.g., 11.5 | 11.2 |
| **Total** | **319.3** | **162.7** | **156.6** |

> Pull actual numbers from your `output_explanations.txt`

#### 6.3 Schedule Before vs. After

Show a 24-hour schedule visualization for at least one appliance (e.g., WashingMachine):

```
Original:  0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 1 0 0 0 0 0 0 0 0
Optimized: 0 0 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
                                         Peak 18:30-22:30 avoided
```

#### 6.4 System Performance

- Agent execution time per cycle (single `main_once()` call)
- Loop interval (30 minutes)
- Firebase write latency (if measured)

**Checklist:**
- [ ] LSTM accuracy metrics reported
- [ ] Cost savings table included with real numbers from output
- [ ] At least one schedule visualization shown
- [ ] Results align directly with the stated objectives
- [ ] All figures/tables are numbered and captioned

---

### 7. 💬 Discussion — (10 Marks)

**Target:** ~200–300 words.

#### Points to cover:

1. **Interpretation:** Why did some appliances (e.g., VehicleCharger) show no savings? (Already scheduled in off-peak). Why did Heater show the most savings? (High kWh consumption × shifted from peak to off-peak).

2. **Contextualization:** Compare to related work — prior rule-only systems cannot adapt to weather; prior LLM-only systems lack hard constraint enforcement. Our hybrid approach addresses both gaps.

3. **Implications:** Edge deployment means this is accessible to households without cloud subscriptions. LLM can be replaced with smaller quantized models for even lower memory usage.

4. **Limitations:**
   - LSTM trained on synthetic data — real-world accuracy may differ.
   - TOU pricing hardcoded; live integration with LECO APIs would improve accuracy.
   - Ollama requires local GPU/CPU resources; very low-end edge devices may struggle.
   - MQTT broker is a public sandbox (`test.mosquitto.org`) — production needs a private broker.

5. **Future Directions:**
   - Replace Llama 3.2 with a fine-tuned domain-specific model.
   - Integrate reinforcement learning (Q-learning) for fully autonomous scheduling.
   - Add occupancy sensors and real-time feedback loops.
   - Deploy to Google Cloud Run for global access.

**Checklist:**
- [ ] Explains *why* results came out as they did
- [ ] Compares to at least 2 related works cited in the Introduction
- [ ] Lists at least 3 limitations
- [ ] Proposes at least 2 concrete future directions

---

### 8. ✅ Conclusion — (10 Marks)

**Target:** ~100–150 words. Short and impactful.

**Draft:**
> This study presented an AI-based optimized energy utilization system tailored for edge computing deployment. By combining LSTM-based appliance usage prediction with a local LLM (Llama 3.2), real-time TOU tariff ingestion, and weather-aware scheduling constraints, the system successfully shifted household load away from expensive peak hours. Experimental results demonstrate meaningful reductions in simulated electricity costs while preserving user-defined appliance runtime requirements. The system's modular, edge-native design makes it practical for deployment in resource-constrained environments without cloud dependency. Future work should integrate real household data, a private MQTT infrastructure, and a reinforcement learning layer to further improve scheduling autonomy and real-world applicability.

**Checklist:**
- [ ] Summarizes key findings in 2 sentences
- [ ] Restates how it answers the research question
- [ ] Acknowledges at least one limitation
- [ ] Ends with a forward-looking recommendation

---

### 9. 🗂️ Clarity & Organization — (05 Marks)

**Checklist:**
- [ ] All text is **justified** (not left-aligned)
- [ ] A **content/table of contents page** is included
- [ ] Sections are: Abstract, Keywords, Introduction, Methodology, Results, Discussion, Conclusion, References
- [ ] Grammar-checked with a tool (Grammarly, Word spell-check, etc.)
- [ ] No orphan headings at bottom of page
- [ ] Figures and tables have captions
- [ ] Font is consistent (e.g., Times New Roman 10pt or IEEE two-column template)

---

### 10. 📚 References — (05 Marks)

**Checklist:**
- [ ] Use **IEEE format** (numbered, e.g., `[1]`)
- [ ] Every reference is cited in-text; every in-text citation has a reference
- [ ] At least **6–8 references** from journals/conferences (IEEE, ACM, Elsevier)
- [ ] Publication years and author names are correct
- [ ] Avoid Wikipedia, random blogs — use Google Scholar

**Suggested reference areas to search:**
1. LSTM for energy consumption forecasting
2. Demand-side management / load shifting
3. LLM for IoT/smart grid reasoning
4. Edge AI / TinyML deployment
5. Time-of-Use pricing and demand response
6. Smart home appliance scheduling optimization

**Example IEEE format:**
```
[1] J. Doe and A. Smith, "LSTM-based energy forecasting for smart homes,"
    in Proc. IEEE ISGT, 2023, pp. 1-6.
```

---

## 🗺️ Where to Find Content for Each Section

| Paper Section | Source in This Repository |
|---|---|
| Architecture diagrams | `docs/agent_explanation.md` (Mermaid diagram), `docs/code_explanation.md` |
| LSTM explanation | `docs/of_Research_LSTM_Explanation.md`, `notebooks/of_Research_LSTM.ipynb` |
| Agent code details | `docs/agent_explanation.md`, `src/agent/agent.py` |
| Cost savings data | Run agent → read `output_explanations.txt` |
| Schedule output | Run agent → read `output.txt` |
| System setup steps | `docs/FIREBASE_SETUP_GUIDE.md`, `docs/QUICK_REFERENCE.md` |
| Flutter mobile app | `mobile-app/flutter_application_1/lib/pages/predictions_page.dart` |

---

## 📐 Page Budget (4-page limit)

| Section | Suggested Length |
|---|---|
| Title + Author block | ~2–3 lines |
| Abstract | ~150–200 words (~0.25 pages) |
| Keywords | 1 line |
| Introduction | ~300–350 words (~0.5 pages) |
| Methodology | ~500–600 words + 1 diagram (~1.2 pages) |
| Results | ~350–400 words + 1 table + 1 figure (~0.8 pages) |
| Discussion | ~200–250 words (~0.35 pages) |
| Conclusion | ~120–150 words (~0.2 pages) |
| References | 6–8 entries (~0.4 pages) |
| **Total** | **~4 pages** |

> If using an IEEE two-column template, this budget fits comfortably. If using a single-column format, be more aggressive with cutting.

---

## ✏️ Final Submission Checklist

- [ ] Title is clear and specific
- [ ] Abstract has all four elements (purpose, method, findings, conclusion)
- [ ] 6–8 diverse keywords
- [ ] Introduction has background, problem, aim, literature, and contributions
- [ ] Methodology is detailed enough to replicate (LSTM + Agent)
- [ ] Results include both LSTM accuracy AND cost savings table
- [ ] Discussion interprets results and compares to literature
- [ ] Conclusion summarizes, acknowledges limits, and recommends future work
- [ ] All pages are justified
- [ ] Content page is included
- [ ] Grammar and spelling checked
- [ ] IEEE-style references, all cited in-text
- [ ] Only ONE member has submitted
- [ ] Submitted **before** the deadline

---

*Generated from project documentation in `docs/` — last updated: 2026-07-04*
