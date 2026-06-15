# 📘 Explanation of `of_Research_LSTM.ipynb`
### AI-Based Optimized Energy Utilization System Using Edge Controllers

This file explains **every line and every function** in the LSTM notebook in simple language.  
The notebook builds an LSTM (Long Short-Term Memory) neural network to **predict future power consumption** of household appliances (Washing Machine, Heater, AC, Vehicle Charger, Vacuum Cleaner).

---

## 🗂️ Table of Contents

1. [Cell 1 — Import Libraries](#cell-1--import-libraries)
2. [Cell 2 — Load & Normalize Data](#cell-2--load--normalize-data)
3. [Cell 3 — Create Sequences Function](#cell-3--create-sequences-function)
4. [Cell 4 — Split Data into Train/Val/Test](#cell-4--split-data-into-trainvaltest)
5. [Cell 5 — Build the LSTM Model](#cell-5--build-the-lstm-model)
6. [Cell 6 — Train the Model](#cell-6--train-the-model)
7. [Cell 7 — Plot Loss (First Version)](#cell-7--plot-loss-first-version)
8. [Cell 8 — Full Evaluation & Visualization](#cell-8--full-evaluation--visualization)
9. [Cell 9 — Save the Model](#cell-9--save-the-model)
10. [Cell 10 — Save the Scaler](#cell-10--save-the-scaler)
11. [Cell 11 — Load Model & Predict Daily Power](#cell-11--load-model--predict-daily-power)
12. [Cell 12 — Binarize Power Values (ON/OFF)](#cell-12--binarize-power-values-onoff)
13. [Cell 13 — Apply Binarization per Appliance](#cell-13--apply-binarization-per-appliance)
14. [Cell 14 — Save Results to Text File](#cell-14--save-results-to-text-file)
15. [Cell 15 — Read and Display Saved File](#cell-15--read-and-display-saved-file)

---

## Cell 1 — Import Libraries

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `import numpy as np` | NumPy lets us work with arrays and do fast math operations. We use it to create arrays for our sequences. |
| 2 | `import pandas as pd` | Pandas lets us read CSV files and work with tables (DataFrames). We use it to load our appliance data. |
| 3 | `import matplotlib.pyplot as plt` | Matplotlib lets us draw charts and graphs. We use it to plot training loss and predictions. |
| 4 | `from sklearn.model_selection import train_test_split` | This function automatically splits our data into training, validation, and test sets randomly. |
| 5 | `from sklearn.preprocessing import MinMaxScaler` | This tool scales all numbers to be between 0 and 1. LSTMs train much better on small normalized numbers. |
| 6 | `from tensorflow.keras.models import Sequential` | Sequential is the simplest way to build a neural network — you add layers one after another. |
| 7 | `from tensorflow.keras.layers import LSTM, Dense` | `LSTM` is the special memory-based layer that understands time patterns. `Dense` is a normal fully-connected output layer. |
| 8 | `from tensorflow.keras.optimizers import Adam` | Adam is a smart learning algorithm that adjusts itself during training to improve faster. |

---

## Cell 2 — Load & Normalize Data

```python
df = pd.read_csv("/content/appliance_power_data.csv")

if 'Timestamp' in df.columns:
    df.drop(columns=['Timestamp'], inplace=True)

# Normalize the data for all appliance columns
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(df)
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `df = pd.read_csv("/content/appliance_power_data.csv")` | Reads the CSV file that contains power usage data for 5 appliances into a table called `df`. |
| 3 | `if 'Timestamp' in df.columns:` | Checks whether the CSV has a "Timestamp" column (like "2024-01-01 00:00:00"). |
| 4 | `df.drop(columns=['Timestamp'], inplace=True)` | Removes the Timestamp column because LSTM uses position in the sequence for time, not dates. `inplace=True` means change the table directly without making a copy. |
| 7 | `scaler = MinMaxScaler()` | Creates a scaling tool. It will learn the minimum and maximum of each column. |
| 8 | `scaled_data = scaler.fit_transform(df)` | `fit` = learns the min/max from the data. `transform` = converts all values to be between 0 and 1. This is stored as a NumPy array. |

> **Why normalize?** Power values might be like 2000W for AC and 50W for a vacuum. If we don't normalize, the LSTM will pay too much attention to the large numbers and ignore small ones.

---

## Cell 3 — Create Sequences Function

```python
def create_sequences(data, seq_length=24):
    x, y = [], []
    for i in range(len(data) - seq_length):
        x.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(x), np.array(y)

x, y = create_sequences(scaled_data, seq_length=24)
```

### Function: `create_sequences(data, seq_length=24)`

**Purpose:** Convert raw time-series data into input-output pairs that the LSTM can learn from.

**Why do we need this?** An LSTM learns patterns over time. So we need to say: *"Given the last 24 minutes of power usage, predict the next minute's usage."*

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `def create_sequences(data, seq_length=24):` | Defines a function. `data` = the normalized data. `seq_length=24` = use 24 past time steps (e.g., 24 minutes) to predict 1 future step. |
| 2 | `x, y = [], []` | Creates two empty lists: `x` will hold input windows, `y` will hold the correct answer for each window. |
| 3 | `for i in range(len(data) - seq_length):` | Loops through every possible starting position in the data. Stops `seq_length` steps before the end so we always have a "next" value to predict. |
| 4 | `x.append(data[i:i+seq_length])` | Takes a window of 24 rows (minutes) from position `i` to `i+24`. This is the input — what the model sees. |
| 5 | `y.append(data[i+seq_length])` | Takes the row at position `i+24` — the very next time step (minute) after the window. This is the correct answer the model should predict. |
| 6 | `return np.array(x), np.array(y)` | Converts the lists to NumPy arrays (required by Keras/TensorFlow). |
| 8 | `x, y = create_sequences(scaled_data, seq_length=24)` | Calls the function on our normalized data. Result: `x` has shape `(samples, 24, 5)` and `y` has shape `(samples, 5)`. |

> **Example:** If data has 10,000 rows, then `x` will have 9,976 sequences (10,000 - 24 = 9,976), and `y` will have 9,976 corresponding target values. Each row represents a 1-minute time step.

---

## Cell 4 — Split Data into Train/Val/Test

```python
x_train, x_temp, y_train, y_temp = train_test_split(x, y, test_size=0.3, random_state=42)
x_val, x_test, y_val, y_test = train_test_split(x_temp, y_temp, test_size=1/3, random_state=42)
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `train_test_split(x, y, test_size=0.3, random_state=42)` | Splits data into 70% for training (`x_train`, `y_train`) and 30% temporarily (`x_temp`, `y_temp`). `random_state=42` ensures the same random split every time you run the code (reproducibility). |
| 2 | `train_test_split(x_temp, y_temp, test_size=1/3, random_state=42)` | Splits the 30% temporary set again: 1/3 of 30% = **10%** for testing, and 2/3 of 30% = **20%** for validation. |

> **Final split:** 70% Training | 20% Validation | 10% Testing
> - **Training:** Used to teach the model.
> - **Validation:** Used during training to check if the model is overfitting (memorizing instead of learning).
> - **Testing:** Used after training to get the final, unbiased accuracy score.

---

## Cell 5 — Build the LSTM Model

```python
model = Sequential()
model.add(LSTM(128, return_sequences=False, input_shape=(x_train.shape[1], x_train.shape[2])))
model.add(Dense(x_train.shape[2]))  # One output per appliance

model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
model.summary()
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `model = Sequential()` | Creates an empty "stack" of layers that we will build up one by one. |
| 2 | `model.add(LSTM(128, ...))` | Adds an LSTM layer with **128 memory units**. More units = more complex patterns the model can learn. |
| 2 | `return_sequences=False` | The LSTM only outputs **one final value** at the end of the 24-step sequence (not one per step). This is correct for many-to-one prediction. |
| 2 | `input_shape=(x_train.shape[1], x_train.shape[2])` | Tells Keras the input shape: `shape[1]` = 24 (time steps), `shape[2]` = 5 (number of appliances/features). |
| 3 | `model.add(Dense(x_train.shape[2]))` | Adds a Dense (fully connected) output layer with **5 neurons** — one for each appliance. This produces the final prediction. |
| 5 | `optimizer=Adam(learning_rate=0.001)` | Adam optimizer with a learning rate of 0.001. This controls how big each update step is during training. |
| 5 | `loss='mse'` | Mean Squared Error — measures how far off the predictions are from the real values. The model tries to minimize this. |
| 6 | `model.summary()` | Prints a table showing each layer, its output shape, and number of trainable parameters. |

> **Model Architecture:**
> - Input → LSTM(128) → Dense(5) → Output
> - Total parameters: ~69,253 (about 270 KB)
> - LSTM layer has 68,608 parameters; Dense layer has 645 parameters.

---

## Cell 6 — Train the Model

```python
history = model.fit(
    x_train, y_train,
    validation_data=(x_val, y_val),
    epochs=50,
    batch_size=32,
    shuffle=False
)
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `history = model.fit(...)` | Trains the model. Stores training history (loss values per epoch) in `history` so we can plot it later. |
| 2 | `x_train, y_train` | The training data: inputs and correct answers. |
| 3 | `validation_data=(x_val, y_val)` | After each epoch, the model also checks its accuracy on validation data. We use this to detect overfitting. |
| 4 | `epochs=50` | The model will see the entire training dataset **50 times**. More epochs = more learning (but can overfit). |
| 5 | `batch_size=32` | Instead of updating model weights after every single sample, it updates after every 32 samples. This is faster and more stable. |
| 6 | `shuffle=False` | **Very important for time-series!** We do NOT shuffle because the order of data matters. Hour 1 must come before Hour 2. |

> **Training Result:** The loss starts at ~0.018 and drops to ~0.002 by epoch 50 — the model is learning well!

---

## Cell 7 — Plot Loss (First Version)

```python
# Plot loss
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.legend()
plt.title("Loss over Epochs")
plt.xlabel("Epoch")
plt.ylabel("MSE Loss")
plt.show()

# Evaluate
mse = model.evaluate(x_test, y_test)
print(f"Test MSE: {mse}")
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 2 | `plt.plot(history.history['loss'], label='Train Loss')` | Draws the training loss curve. `history.history['loss']` is a list of loss values, one per epoch. |
| 3 | `plt.plot(history.history['val_loss'], label='Val Loss')` | Draws the validation loss curve. If this is much higher than train loss, the model is overfitting. |
| 4 | `plt.legend()` | Shows a legend box so we can tell which line is which. |
| 5 | `plt.title("Loss over Epochs")` | Adds a title to the chart. |
| 6-7 | `plt.xlabel / plt.ylabel` | Labels the X-axis (Epoch number) and Y-axis (loss value). |
| 8 | `plt.show()` | Displays the chart. |
| 11 | `mse = model.evaluate(x_test, y_test)` | Runs the model on the test set and returns the MSE loss. This is our final accuracy score. |
| 12 | `print(f"Test MSE: {mse}")` | Prints the test MSE value. Lower = better predictions. |

---

## Cell 8 — Full Evaluation & Visualization

```python
# Plot loss
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.legend()
plt.title("Loss over Epochs")
plt.xlabel("Epoch")
plt.ylabel("MSE Loss")
plt.show()

# Evaluate
mse = model.evaluate(x_test, y_test)
print(f"Test MSE: {mse}")

# Predict on the test set
y_pred = model.predict(x_test)

y_test_inv = scaler.inverse_transform(y_test)
y_pred_inv = scaler.inverse_transform(y_pred)

appliance_names = df.columns

for i in range(len(appliance_names)):
    plt.figure(figsize=(30, 6))
    plt.plot(y_test_inv[0:100, i], label='Actual')
    plt.plot(y_pred_inv[0:100, i], label='Predicted')
    plt.title(f"{appliance_names[i]} Power Consumption")
    plt.xlabel("Sample")
    plt.ylabel("Power")
    plt.legend()
    plt.grid(True)
    plt.show()

for i in range(len(appliance_names)):
    plt.figure(figsize=(30, 6))
    plt.plot(y_test_inv[200:300, i], label='Actual')
    plt.plot(y_pred_inv[200:300, i], label='Predicted')
    plt.title(f"{appliance_names[i]} Power Consumption")
    plt.xlabel("Sample")
    plt.ylabel("Power")
    plt.legend()
    plt.grid(True)
    plt.show()
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1-9 | Loss plot | Same as Cell 7 — plots train vs. validation loss (duplicate in the notebook). |
| 11-12 | `model.evaluate / print` | Gets and prints the final test MSE (same as Cell 7). |
| 14 | `y_pred = model.predict(x_test)` | Runs the trained model on all test inputs. Returns predicted (normalized) power values. |
| 16 | `y_test_inv = scaler.inverse_transform(y_test)` | **Converts normalized test values back to real Watts.** We scaled data to 0–1 earlier; now we undo that so charts show real power values. |
| 17 | `y_pred_inv = scaler.inverse_transform(y_pred)` | **Converts predicted normalized values back to real Watts.** Same reason as above. |
| 19 | `appliance_names = df.columns` | Gets the column names from the DataFrame: ['WashingMachine_Power', 'Heater_Power', 'AC_Power', 'VehicleCharger_Power', 'VacuumCleaner_Power'] |
| 21 | `for i in range(len(appliance_names)):` | Loops through all 5 appliances so we make one chart per appliance. |
| 22 | `plt.figure(figsize=(30, 6))` | Creates a wide figure (30 wide, 6 tall) so the time-series plots are easy to read. |
| 23 | `plt.plot(y_test_inv[0:100, i], label='Actual')` | Plots the first 100 actual power values for appliance `i`. |
| 24 | `plt.plot(y_pred_inv[0:100, i], label='Predicted')` | Plots the first 100 predicted power values for appliance `i`. |
| 25 | `plt.title(...)` | Adds a title showing which appliance this chart is for. |
| 28 | `plt.grid(True)` | Adds a grid to the chart for easier reading. |
| 31-40 | Second for loop | Plots samples 200–300 instead of 0–100, showing a different time window for comparison. |

---

## Cell 9 — Save the Model

```python
model.save('my_lstm_model.h5')
model.save('my_lstm_model.keras')
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `model.save('my_lstm_model.h5')` | Saves the trained model in the older **HDF5 format** (`.h5`). This includes the architecture, weights, and optimizer state. |
| 2 | `model.save('my_lstm_model.keras')` | Saves in the newer **Keras format** (`.keras`). This is the recommended modern format for TensorFlow 2.x+. |

> **Why save two formats?** For compatibility — `.h5` works with older code and libraries; `.keras` is the future-proof format.

---

## Cell 10 — Save the Scaler

```python
import pickle

# Save the scaler
with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `import pickle` | Pickle is a Python library that can convert any Python object (like our scaler) into bytes that can be saved to a file. |
| 4 | `with open('scaler.pkl', 'wb') as f:` | Opens a file called `scaler.pkl` in **write-binary** mode (`'wb'`). The `with` block automatically closes the file when done. |
| 5 | `pickle.dump(scaler, f)` | Serializes (converts) the scaler object and writes it to the file. |

> **Why save the scaler?** When we use the model later to make predictions, we must normalize new data using the **same min/max values** that were used during training. The saved scaler stores those values.

---

## Cell 11 — Load Model & Predict Daily Power

```python
from tensorflow.keras.models import load_model
import pickle

model = load_model('my_lstm_model.keras')
with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

x_test_day = x_train[:5000]

# Predict for all sequences in the day at once
all_day_predictions_scaled = model.predict(x_test_day)

# Inverse transform if necessary
all_day_predictions = scaler.inverse_transform(all_day_predictions_scaled)

print("Predicted power consumption for all day:")
print(all_day_predictions)

appliance_names = df.columns
for i, prediction in enumerate(all_day_predictions):
    print(f"Time step {i+1}:")
    for j, appliance in enumerate(appliance_names):
        print(f"  {appliance}: {prediction[j]}")
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `from tensorflow.keras.models import load_model` | Imports the function to reload a saved Keras model. |
| 3 | `model = load_model('my_lstm_model.keras')` | Loads the saved LSTM model from disk with all its trained weights. |
| 4-5 | `with open('scaler.pkl', 'rb') as f: scaler = pickle.load(f)` | Loads the saved scaler from disk. `'rb'` = read-binary mode. |
| 7 | `x_test_day = x_train[:5000]` | Takes the **first 5000 sequences** from the training data. Despite the name, this is actually selecting from `x_train`. This simulates "one day" of data to predict. |
| 10 | `all_day_predictions_scaled = model.predict(x_test_day)` | Runs the model on all 5000 sequences at once and gets the normalized predictions. |
| 13 | `all_day_predictions = scaler.inverse_transform(all_day_predictions_scaled)` | Converts the predictions from 0–1 scale back to real Watts. |
| 15-16 | `print(...)` | Prints the full array of predicted power values. |
| 18 | `appliance_names = df.columns` | Gets the list of appliance names from the original DataFrame. |
| 19 | `for i, prediction in enumerate(all_day_predictions):` | Loops through each time step's prediction. `enumerate` gives both the index `i` and the value `prediction`. |
| 20 | `print(f"Time step {i+1}:")` | Prints the time step number (starting from 1 for human readability). |
| 21-22 | `for j, appliance in enumerate(appliance_names): print(...)` | For each appliance at this time step, prints the predicted watt value. |

---

## Cell 12 — Binarize Power Values (ON/OFF)

```python
import numpy as np

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
```

### Function: `binarize_power_values(power_values, threshold_ratio=0.6)`

**Purpose:** Converts continuous power values (e.g., 1500W, 20W, 2800W) into simple ON (1) or OFF (0) states.

**Why do we need this?** Edge controllers need simple binary commands — either turn a device ON or OFF. The LSTM gives us power numbers, but we need to decide: "Is this appliance currently ON or OFF?"

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `import numpy as np` | Re-imports NumPy (safe to do again). |
| 3 | `def binarize_power_values(power_values, threshold_ratio=0.6):` | Defines the function. Default `threshold_ratio=0.6` means: if power ≥ 60% of the maximum power, the device is ON. |
| 4-12 | `""" ... """` | Docstring — explains what the function does, its inputs, and outputs. Good documentation practice. |
| 13 | `power_values = np.array(power_values)` | Converts the input to a NumPy array, so we can use NumPy math operations on it. |
| 14 | `threshold = threshold_ratio * np.max(power_values)` | Calculates the threshold: `0.6 × max_power`. E.g., if max AC power = 3000W, threshold = 1800W. |
| 15 | `binary_states = (power_values >= threshold).astype(int)` | Compares each value to the threshold. Returns `True`/`False`, then `.astype(int)` converts to `1`/`0`. |
| 16 | `return binary_states` | Returns the array of 1s and 0s. |

> **Example:** Power values = [2800, 50, 2500, 30, 2900]. Max = 2900. Threshold = 0.6 × 2900 = 1740. Result = [1, 0, 1, 0, 1]

---

## Cell 13 — Apply Binarization per Appliance

```python
binary_average_states = {}

for appliance_name, avg_values in averages.items():
    # Set different threshold_ratio based on appliance name
    if appliance_name in ['WashingMachine_Power', 'Heater_Power', 'AC_Power']:
        threshold_ratio = 0.6
    else:
        threshold_ratio = 0.8

    binary_states = binarize_power_values(avg_values, threshold_ratio=threshold_ratio)
    binary_average_states[appliance_name] = binary_states

# Print the binarized states for the first few windows for each appliance
for appliance_name, binary_states in binary_average_states.items():
    print(f"--- {appliance_name} Binary States ---")
    print(binary_states[:24])
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `binary_average_states = {}` | Creates an empty dictionary to store the ON/OFF results for each appliance. |
| 3 | `for appliance_name, avg_values in averages.items():` | Loops through each appliance name and its averaged power values. `averages` is a dictionary computed earlier in the notebook. |
| 5 | `if appliance_name in ['WashingMachine_Power', 'Heater_Power', 'AC_Power']:` | Checks if the appliance is a **high-power** device. |
| 6 | `threshold_ratio = 0.6` | High-power devices use a **lower threshold** (60%) — easier to turn ON. These devices use a lot of power even at partial capacity. |
| 8 | `threshold_ratio = 0.8` | Low-power devices (Vehicle Charger, Vacuum) use a **higher threshold** (80%) — harder to turn ON. We only want to mark them as ON when they're clearly running. |
| 10 | `binary_states = binarize_power_values(avg_values, threshold_ratio=threshold_ratio)` | Calls our binarization function with the appropriate threshold for this appliance. |
| 11 | `binary_average_states[appliance_name] = binary_states` | Stores the result in our dictionary under the appliance name. |
| 13-15 | Print loop | Loops through the dictionary and prints the first 24 binary states (first 24 hours) for each appliance. |

---

## Cell 14 — Save Results to Text File

```python
with open('appliance_data.txt', 'w') as f:
    for appliance_name in appliance_names:
        f.write(f"--- {appliance_name} ---\n")
        f.write("States:\n")

        if appliance_name in states:
            np.savetxt(f, states[appliance_name].reshape(1, -1), fmt='%d', delimiter=', ')
        else:
            f.write("States data not available\n")

        f.write("Averages:\n")

        if appliance_name in averages:
            np.savetxt(f, averages[appliance_name].reshape(1, -1), fmt='%.4f', delimiter=', ')
        else:
            f.write("Averages data not available\n")

        f.write("Binary Average States:\n")

        if appliance_name in binary_average_states:
            np.savetxt(f, binary_average_states[appliance_name].reshape(1, -1), fmt='%d', delimiter=', ')
        else:
            f.write("Binary average states data not available\n")

        f.write("\n")

print("States, averages, and binary average states saved to appliance_data.txt")
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `with open('appliance_data.txt', 'w') as f:` | Opens a text file for writing (`'w'`). The `with` block handles closing the file automatically. |
| 2 | `for appliance_name in appliance_names:` | Loops through each appliance to write its data. |
| 3 | `f.write(f"--- {appliance_name} ---\n")` | Writes a header line like `--- WashingMachine_Power ---`. `\n` = new line. |
| 4 | `f.write("States:\n")` | Writes a sub-header "States:" before the state data. |
| 6 | `if appliance_name in states:` | Checks if state data is available for this appliance before trying to write it (prevents errors). |
| 7 | `np.savetxt(f, states[appliance_name].reshape(1, -1), fmt='%d', delimiter=', ')` | **Saves the ON/OFF states** as a single row of integers (`%d`), comma-separated. `.reshape(1, -1)` flattens the array into one row. |
| 9 | `f.write("States data not available\n")` | Fallback message if no state data exists for this appliance. |
| 11-16 | Averages section | Same structure as States — writes the average power values with 4 decimal places (`%.4f`). |
| 18-23 | Binary Average States section | Same structure — writes the binary (0/1) versions of the averages. |
| 25 | `f.write("\n")` | Adds a blank line between appliances for readability. |
| 27 | `print("States, averages...")` | Confirms to the user that saving was successful. |

---

## Cell 15 — Read and Display Saved File

```python
file_path = '/content/appliance_data.txt'

try:
    with open(file_path, 'r') as f:
        file_content = f.read()
        print("Contents of the file:")
        print(file_content)
except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")
```

### Line-by-Line Explanation

| Line | Code | Why We Use It |
|------|------|---------------|
| 1 | `file_path = '/content/appliance_data.txt'` | Stores the file path as a variable so it's easy to change later. |
| 3 | `try:` | Starts a try-except block — a way to handle errors gracefully instead of crashing the program. |
| 4 | `with open(file_path, 'r') as f:` | Opens the file for **reading** (`'r'`). |
| 5 | `file_content = f.read()` | Reads the entire file content into a string variable. |
| 6-7 | `print(...)` | Prints the file content to the screen for verification. |
| 8 | `except FileNotFoundError:` | Catches the specific error if the file doesn't exist at that path. |
| 9 | `print(f"Error: The file '{file_path}' was not found.")` | Prints a helpful error message telling the user which file wasn't found. |
| 10 | `except Exception as e:` | Catches any other unexpected errors. `e` holds the error message. |
| 11 | `print(f"An error occurred: {e}")` | Prints whatever unexpected error occurred, for debugging. |

---

## 🧠 Overall Pipeline Summary

```
Raw CSV Data
    │
    ▼
Load with Pandas → Remove Timestamp → Normalize with MinMaxScaler (0 to 1)
    │
    ▼
Create Sliding Windows of 24 hours → (x: input sequences, y: next hour targets)
    │
    ▼
Split: 70% Train | 20% Validation | 10% Test
    │
    ▼
Build LSTM Model: Input(24,5) → LSTM(128) → Dense(5) → Output(5 appliances)
    │
    ▼
Train for 50 epochs (batch_size=32, shuffle=False)
    │
    ▼
Evaluate on Test Set → Plot Actual vs. Predicted for each appliance
    │
    ▼
Save Model (.h5 and .keras) + Save Scaler (.pkl)
    │
    ▼
Reload → Predict 5000 time steps → Inverse Transform back to Watts
    │
    ▼
Binarize Predictions: High power (≥ threshold) → ON (1), Low power → OFF (0)
    │
    ▼
Save States + Averages + Binary States to appliance_data.txt
```

---

## 📊 Key Concepts Glossary

| Term | Simple Explanation |
|------|-------------------|
| **LSTM** | A type of neural network that has "memory" — it can remember past time steps when making predictions. |
| **Sequence** | A series of data points in time order. E.g., 24 hours of power readings. |
| **Epoch** | One full pass through all training data. Running 50 epochs means the model sees all data 50 times. |
| **Batch Size** | The number of samples processed before the model updates its weights. Smaller = slower but more precise. |
| **MSE (Mean Squared Error)** | How wrong the predictions are on average (lower is better). Squaring makes big mistakes count more. |
| **Normalization** | Scaling data to 0–1 range so the model doesn't get confused by very large or very small numbers. |
| **Inverse Transform** | Undoing normalization to get values back in their original units (Watts). |
| **Binarization** | Converting continuous numbers to 0 or 1 (OFF or ON). |
| **Threshold** | The cutoff value used to decide ON vs. OFF. Power above threshold = ON. |
| **Overfitting** | When a model memorizes training data too well and performs poorly on new data. Validation loss helps detect this. |

---

*This document was auto-generated to explain the notebook `of_Research_LSTM.ipynb` in simple language.*
