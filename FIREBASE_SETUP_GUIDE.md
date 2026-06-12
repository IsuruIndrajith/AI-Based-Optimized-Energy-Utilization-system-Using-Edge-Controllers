# Complete Firebase + Firestore Setup Guide

This guide walks you through setting up Firebase, creating a Firestore database, generating credentials, and deploying APIs.

## Phase 1: Firebase Account & Project Creation

### Step 1: Create a Google Account (if you don't have one)
1. Go to [https://accounts.google.com/signup](https://accounts.google.com/signup)
2. Complete the registration

### Step 2: Create a Firebase Project
1. Visit [https://console.firebase.google.com/](https://console.firebase.google.com/)
2. Click **"Create a new project"** or **"Add project"**
3. Enter project name: `energy-optimization-system` (or any name)
4. Click **Continue**
5. (Optional) Enable Google Analytics → Click **Continue**
6. Select region (Google Cloud location) → Click **Create project**
7. Wait for project creation to complete

---

## Phase 2: Set Up Firestore Database

### Step 3: Create a Firestore Database
1. In Firebase Console, go to **Build** → **Firestore Database**
2. Click **Create Database**
3. Choose **Start in production mode** (NOT test mode, for security)
4. Select region: **asia-south1** (or closest to you, matches your current API)
5. Click **Create**

### Step 4: Firestore Collection Structure
Once Firestore is created, you need two collections:

**Collection 1: `analysis`**
- Document: `latest`
  ```json
  {
    "WashingMachine": {
      "original_cost": 50.5,
      "optimized_cost": 35.2,
      "savings": 15.3
    },
    "Heater": {
      "original_cost": 120.0,
      "optimized_cost": 85.0,
      "savings": 35.0
    },
    "updated_at": "2026-06-12T10:30:00"
  }
  ```

**Collection 2: `schedules`**
- Document: `latest`
  ```json
  {
    "WashingMachine": [[1,0,0,1,0,...], ...],
    "Heater": [[0,1,1,0,1,...], ...],
    "updated_at": "2026-06-12T10:30:00"
  }
  ```

---

## Phase 3: Service Account Credentials

### Step 5: Generate Service Account Key
1. In Firebase Console, click the **⚙ Settings icon** (top-left) → **Project settings**
2. Go to **Service accounts** tab
3. Click **Generate new private key** button
4. A JSON file (`FILENAME-123abc.json`) will download
5. **Save this file as `serviceAccountKey.json`** in your project root:
   ```
   D:\Research\Code\AI-Based-Optimized-Energy-Utilization-system-Using-Edge-Controllers\serviceAccountKey.json
   ```

### Step 6: Verify Credentials File
- The JSON file should look like:
  ```json
  {
    "type": "service_account",
    "project_id": "energy-optimization-system-abc123",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "client_email": "firebase-adminsdk-xyz@PROJECT_ID.iam.gserviceaccount.com",
    "client_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "...",
    "client_x509_cert_url": "..."
  }
  ```

---

## Phase 4: Data Upload Pipeline

### Step 7: Upload Data from Agent to Firestore

The `src/agent/agent.py` script **already writes to Firestore**. When you run it:

```powershell
python src/agent/agent.py
```

It will:
1. Generate analysis results
2. Create schedules
3. Write both to `analysis/latest` and `schedules/latest` in Firestore

### Step 8: Use the Firebase Uploader Script

For manual uploads of `output.txt` and `output_explanations.txt`:

```powershell
pip install firebase-admin

python firebase_uploader\upload_outputs_to_firestore.py
```

---

## Phase 5: Deploy Firestore-Based API

### Step 9: Update Backend Server

Use the new Firestore-based API server (`backend/server_firestore.py`). This reads directly from Firestore instead of local files.

```powershell
# Install Firebase Admin
pip install firebase-admin flask flask-cors

# Run the Firestore API server
python backend\server_firestore.py
```

The API now serves from Firestore:
- `GET http://localhost:8080/analysis` → Reads from `analysis/latest`
- `GET http://localhost:8080/schedules` → Reads from `schedules/latest`

---

## Phase 6: Update Flutter App

### Step 10: Update API Endpoint in Flutter

Update `lib/pages/predictions_page.dart`:

Change from:
```dart
https://energy-api-632525537450.asia-south1.run.app/analysis
```

To your **local API** (during development):
```dart
http://10.0.2.2:8080/analysis  // For Android emulator
// OR
http://localhost:8080/analysis  // For physical device on same network
```

Or if deployed:
```dart
https://your-new-api-url.run.app/analysis
```

---

## Phase 7: Deploy to Google Cloud Run (Optional)

### Step 11: Deploy Firestore API to Cloud Run

1. Install Google Cloud CLI: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. Authenticate:
   ```powershell
   gcloud auth login
   gcloud config set project energy-optimization-system
   ```
3. Deploy:
   ```powershell
   cd backend
   gcloud run deploy energy-api --source . --region asia-south1 --allow-unauthenticated
   ```
4. Copy the deployed URL from output (e.g., `https://energy-api-xyz.asia-south1.run.app`)
5. Update Flutter app to use this URL

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| `ServiceAccountKey.json not found` | Ensure file is at repo root with exact name |
| `PERMISSION_DENIED` error in Firestore | Check Firestore security rules (use production mode or update rules) |
| Flask API returns 404 | Ensure `analysis/latest` and `schedules/latest` documents exist in Firestore |
| `firebase_admin` import error | Run `pip install firebase-admin` |
| Flutter app can't reach localhost API | Use `10.0.2.2:8080` for Android emulator, or device IP for physical device |

---

## File Structure After Setup

```
project-root/
├── serviceAccountKey.json         ← Downloaded from Firebase
├── backend/
│   ├── server.py                 ← Old file-based API
│   ├── server_firestore.py       ← NEW Firestore-based API
│   └── requirements.txt
├── firebase_uploader/
│   └── upload_outputs_to_firestore.py
├── src/
│   └── agent/
│       └── agent.py              ← Writes to Firestore
├── mobile-app/flutter_application_1/
│   └── lib/pages/
│       └── predictions_page.dart  ← Update endpoint here
└── FIREBASE_SETUP_GUIDE.md        ← This file
```

---

## Summary of Data Flow

```
┌─────────────────┐
│   Agent Script  │ ─── (writes analysis + schedules)
│   (agent.py)    │
└────────┬────────┘
         │
         ▼
    ┌──────────────────┐
    │  Firestore DB    │
    ├──────────────────┤
    │ analysis/latest  │
    │ schedules/latest │
    └────────┬─────────┘
             │
             ▼ (reads from)
    ┌─────────────────────────┐
    │  Flask API Server       │
    │ (server_firestore.py)   │
    │ /analysis               │
    │ /schedules              │
    └────────┬────────────────┘
             │
             ▼ (HTTP requests)
    ┌─────────────────────────┐
    │  Flutter Mobile App     │
    │  (predictions_page.dart)│
    └─────────────────────────┘
```

---

## Next Steps

1. ✅ Create Firebase account & project
2. ✅ Create Firestore database
3. ✅ Download `serviceAccountKey.json`
4. ✅ Place JSON file at project root
5. ✅ Run `src/agent/agent.py` to populate Firestore
6. ✅ Run `backend/server_firestore.py` to start API
7. ✅ Test API endpoints: `http://localhost:8080/analysis`
8. ✅ Update Flutter app to use new API
9. ✅ (Optional) Deploy to Cloud Run

For questions, refer to [Firebase Documentation](https://firebase.google.com/docs/firestore) or [Flask-Firebase Guide](https://firebase.google.com/docs/firestore/quickstart).
