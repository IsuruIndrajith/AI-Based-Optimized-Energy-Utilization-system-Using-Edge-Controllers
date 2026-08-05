# LSTM Power Forecasting for Smart Home Energy Management

This document provides a comprehensive explanation of the Long Short-Term Memory (LSTM) model used for power forecasting in the system, based on the implementation in the `notebooks/of_Research_LSTM.ipynb` notebook.

## Overview
The goal of this LSTM model is to predict the energy consumption (in Watts) of 5 different home appliances simultaneously:
1. Washing Machine
2. Heater
3. AC
4. Vehicle Charger
5. Vacuum Cleaner

The model uses historical time-series data to forecast the next power reading for all five appliances based on a sequence of the previous 24 readings.

---

## Step-by-Step Workflow

### 1. Data Loading and Preprocessing
- **Dataset:** The model loads the raw data from `appliance_power_data.csv`.
- **Cleaning:** The `Timestamp` column is dropped since the LSTM natively understands sequential patterns based on the row ordering.
- **Normalization:** The power values for all 5 appliances are scaled between 0 and 1 using `MinMaxScaler`. This ensures that appliances with high power draws (e.g., Vehicle Charger) don't dominate appliances with lower power draws (e.g., Vacuum Cleaner) during the neural network training process.

### 2. Sequence Generation (Sliding Window)
- **Time Steps (Sequence Length):** The model uses a sequence length of **24**. 
- **Windowing:** The `create_sequences()` function creates a sliding window over the normalized data. It groups 24 consecutive time steps as the input (`x`) to predict the 25th time step as the output label (`y`).

### 3. Data Splitting
The sequences are divided into three distinct datasets using `train_test_split`:
- **Training Set (70%):** Used to train the model weights.
- **Validation Set (20%):** Used to evaluate the model's performance during training after each epoch to monitor overfitting.
- **Testing Set (10%):** Held out completely to test the model's final accuracy on unseen data.

*Note: `shuffle=False` is used during training to maintain the chronological order of the time-series data.*

### 4. Model Architecture
The neural network is a `Sequential` model built with TensorFlow/Keras:
- **LSTM Layer:** A single Long Short-Term Memory layer with **128 units/neurons**. The `return_sequences=False` argument means it reads the entire sequence of 24 steps and outputs a single flattened vector capturing the temporal dependencies.
- **Dense Layer (Output):** A fully connected output layer with **5 units** corresponding to the predicted power of the 5 appliances at the next time step.
- **Total Parameters:** The model is lightweight and highly efficient, containing exactly **69,253** trainable parameters.

### 5. Model Compilation
- **Optimizer:** `Adam` optimizer with a learning rate of `0.001` is used to adjust the model weights efficiently.
- **Loss Function:** Mean Squared Error (`mse`), which heavily penalizes large forecasting errors.

### 6. Model Training
- **Epochs:** The model is trained for **50 epochs**.
- **Batch Size:** Processed in batches of **32** sequences at a time.
- **Convergence:** As seen in the notebook output, the training loss and validation loss steadily decrease, indicating that the model successfully learns the power usage patterns without significant overfitting.

### 7. Prediction & Inverse Transformation
- After training, the model generates predictions on the Test set.
- Because the model outputs normalized values (between 0 and 1), the `MinMaxScaler` is used to apply an **inverse transform**. This converts the predictions back into real-world units (Watts).
- The notebook iterates through the test predictions (e.g., `Time step 4203`, `4204`, etc.), printing out the raw predicted power in Watts for each appliance. *(Note: Regression models sometimes predict small negative values for 0-state appliances; these are typically clipped to 0 in production).*

---

## How it Fits into the Broader System
Once trained in this research notebook, the resulting model architecture and weights are exported and utilized by the edge controller (via `Run_LSTM.py`). In the live system:
1. It ingests 24 minutes of real-time MQTT sensor data.
2. Predicts the next minute of power for all 5 appliances.
3. Accumulates these predictions for a full 24-hour cycle.
4. Averages the minute-by-minute predictions into **hourly** required ON hours, feeding the results to the LangGraph AI agent for final cost-optimization scheduling.
