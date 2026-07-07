# AI-Based Optimized Energy Utilization System Using Edge Computing Controller

## 📌 Project Overview
This research develops an AI-based energy management system that predicts household energy consumption and optimizes appliance usage schedules. By combining Long Short-Term Memory (LSTM) forecasting with edge-based intelligence, the system helps users reduce energy costs and improve energy efficiency in domestic environments.

## 👥 Team & Supervision
* **Presented by:** Indrajith E.M.I. (2021/E/035) & Hettiarachchi H.P.M. (2021/E/051)
* **Supervisor:** Dr. A. Kaneswaren
* **Co-Supervisor:** Mr. Y. Pirunthapan

## 🚨 Problem Statement
Household electricity demand and energy costs are consistently increasing due to inefficient appliance usage. Traditional energy management systems rely on fixed schedules or manual controls, failing to adapt to real-time pricing and dynamic consumption patterns.

## 🎯 Aim and Significance
To develop an AI-based energy optimization system that predicts and schedules appliance usage based on real-time energy pricing and consumption patterns, thereby promoting cost reduction and efficient energy utilization.

## 🔬 Research Gap & Innovation
While most state-of-the-art research focuses solely on forecasting energy usage using LSTM or hybrid ML models, our research advances beyond prediction. We utilize forecasted data as input for **energy optimization and scheduling** through an AI-agent-based decision system. 
By integrating **Ollama (Llama 3.2)** reasoning at the edge level, the system enables automatic appliance scheduling based on live context, predicted demand, and specific user preferences.

## ⚙️ Implementation and Methodology
1. **Appliance Energy Demand Forecasting:** Utilizes an LSTM neural network to predict future power consumption, chosen for its capability to understand time-based usage patterns.
2. **Appliance State Generation:** Converts predicted power values into simple ON/OFF states using dynamic thresholding for appliance scheduling control signals.
3. **Live Context & Preferences Gathering:** Retrieves real-time Time-of-Use (TOU) tariff data via MQTT, live weather forecasts, and user scheduling preferences via Firebase Firestore.
4. **AI Agent-Based Decision Making:** An AI agent (Ollama/Llama 3.2) balances LSTM predictions, weather, live pricing, and user preferences to dynamically shift appliance usage to cheaper, off-peak hours.
5. **Firebase Integration:** Firebase Firestore serves as a scalable cloud database to store user preferences, optimized schedules, and analysis results, enabling real-time synchronization with client applications.
6. **Edge Computing:** AI and prediction models run locally on an Edge Controller to ensure user privacy, minimize latency, and maintain offline functionality.

## 🚀 Progress & Key Results
* **Customization:** Successfully added user preference-based customization so recommendations and schedules reflect actual user requirements.
* **LLM Refinement:** Refined LLM prompts to improve the consistency, accuracy, and relevance of the generated schedules and explanations.
* **Model Training:** Successfully trained LSTM models for various appliances (e.g., Vehicle Charger, Vacuum Cleaner, AC, TV) and modified predicted values to determine ON/OFF statuses.
* **Mobile App (v2.0):** Updated the Flutter-based mobile application with redesigned screens for better accessibility, displaying real-time energy predictions, cost analysis (Original vs. Optimized costs), and automated 24-hour schedules.

## ⚠️ Challenges Faced
* Collecting and maintaining consistent real-time TOU tariff data.
* Fine-tuning LSTM hyperparameters to maximize prediction accuracy.
* Balancing user preferences and comfort requirements to generate customized schedules.

## 📚 References
1. A. Lekidis and E. I. Papageorgiou, “Edge-Based Short-Term Energy Demand Prediction,” Jul. 2023.
2. S. Zhao, et al., “Residential energy consumption and price forecasting in smart homes based on the internet of energy,” *Sustainable Energy Technologies and Assessments*, Nov. 2024.
3. U. Ali, et al., “IoT-Driven Smart Energy Monitoring: Real-time Insights and AI-Based Unit Predictions,” Dec. 2023.
4. S. Zhu, K. Ota, and M. Dong, “Green AI for IIoT: Energy Efficient Intelligent Edge Computing for Industrial Internet of Things,” *IEEE Trans. on Green Communications*, Mar. 2022.
5. M. Zawish, et al., “Energy-Aware AI-Driven Framework for Edge-Computing-Based IoT Applications,” *IEEE Internet of Things Journal*, Mar. 2023.
6. Z. Severiche-Maury et al., “Forecasting Residential Energy Consumption with the Use of Long Short-Term Memory Recurrent Neural Networks,” Mar. 2025.
