# Firestore Uploader

This folder contains a Python script to upload `output.txt` and `output_explanations.txt` into Firebase Firestore.

## Setup

1. Install dependencies if not already installed:

   ```powershell
   pip install firebase-admin
   ```

2. Provide Firebase credentials using one of these options:

   - Place `serviceAccountKey.json` at the repository root:
     `D:\Research\Code\AI-Based-Optimized-Energy-Utilization-system-Using-Edge-Controllers\serviceAccountKey.json`
   - Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the JSON key path.

## Usage

Run the script from the repository root or any folder:

```powershell
python firebase_uploader\upload_outputs_to_firestore.py
```

Or specify explicit paths:

```powershell
python firebase_uploader\upload_outputs_to_firestore.py --output output.txt --explanations output_explanations.txt --collection analysis --document outputs_latest
```

## Result

The script writes a Firestore document to the specified collection/document. By default it writes:

- Collection: `analysis`
- Document: `outputs_latest`

The document contains:

- `output_text`
- `explanations_text`
- `uploaded_at`
- `output_path`
- `explanations_path`

You can read this document later from any API or backend service.
