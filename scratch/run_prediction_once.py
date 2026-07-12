import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "predictor")))
import Run_LSTM

if __name__ == "__main__":
    Run_LSTM.fill_initial_dummy_data()
    print("Running prediction on initial dummy data...")
    Run_LSTM.predict_on_buffer(Run_LSTM.data_buffer)
    print("Prediction finished successfully!")
