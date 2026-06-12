# Quick Reference: Firebase Setup & API Endpoints

## 🚀 What You're Building

```
Old System:                    New System:
────────────────────          ────────────────────
Local Files          →    Firestore DB
output.txt                  collection: "analysis"
output_explanations.txt     collection: "schedules"
         ↓                           ↓
   server.py            →    server_firestore.py
 (reads from disk)             (reads from Firestore)
         ↓                           ↓
   Flask API            →      Flask API
 /analysis endpoint           /analysis endpoint
 /schedules endpoint          /schedules endpoint
         ↓                           ↓
   Flutter App          →      Flutter App
(predictions_page.dart)      (predictions_page.dart)
```

---

## 📋 Quick Setup Checklist

- [ ] **1. Create Firebase Account**
  - Visit https://console.firebase.google.com/
  - Create new project

- [ ] **2. Create Firestore Database**
  - In Firebase Console → Build → Firestore Database
  - Choose production mode
  - Select region: asia-south1

- [ ] **3. Download Service Account Key**
  - Firebase Console → Settings (⚙) → Service Accounts
  - Click "Generate new private key"
  - Save as `serviceAccountKey.json` at project root

- [ ] **4. Install Dependencies**
  ```powershell
  pip install firebase-admin flask flask-cors
  ```

- [ ] **5. Populate Firestore**
  ```powershell
  python src/agent/agent.py
  # OR
  python firebase_uploader/upload_outputs_to_firestore.py
  ```

- [ ] **6. Start Firestore API**
  ```powershell
  python backend/server_firestore.py
  ```

- [ ] **7. Update Flutter App**
  - Change endpoint in `predictions_page.dart`
  - Use `http://10.0.2.2:8080` for Android emulator

- [ ] **8. Test API**
  ```powershell
  curl http://localhost:8080/analysis
  ```

---

## 🔗 API Endpoints

### Local Development (Your Computer)

```
http://localhost:8080/analysis       # Get cost analysis
http://localhost:8080/schedules      # Get energy schedules
http://localhost:8080/health         # Check status
http://localhost:8080/               # API documentation
```

### Android Emulator
```
http://10.0.2.2:8080/analysis
http://10.0.2.2:8080/schedules
```

### Physical Device (Replace with your PC IP)
```
http://192.168.1.100:8080/analysis   # Use your actual PC IP
http://192.168.1.100:8080/schedules
```

### Cloud Run (After Deployment)
```
https://energy-api-firestore-xyz.asia-south1.run.app/analysis
https://energy-api-firestore-xyz.asia-south1.run.app/schedules
```

---

## 📁 File Locations

```
Project Root/
├── serviceAccountKey.json                    ← Firebase credentials (DOWNLOAD)
├── FIREBASE_SETUP_GUIDE.md                  ← Full setup guide (READ THIS FIRST)
├── FLUTTER_ENDPOINT_UPDATE.md               ← Flutter code updates
├── setup_firebase.py                        ← Quick setup script
├── backend/
│   ├── server.py                            ← Old file-based API
│   └── server_firestore.py                  ← NEW Firestore API ⭐
├── firebase_uploader/
│   ├── upload_outputs_to_firestore.py      ← Manual uploader
│   └── README.md
├── src/agent/
│   └── agent.py                             ← Writes to Firestore ⭐
└── mobile-app/flutter_application_1/lib/pages/
    └── predictions_page.dart                ← Update endpoint ⭐
```

---

## 🔑 Key Steps Explained

### Step 1: Download Firebase Credentials
1. Go to https://console.firebase.google.com
2. Open your project → Settings (⚙) → Service Accounts
3. Click "Generate new private key"
4. Save file as `serviceAccountKey.json` in project root
5. **NEVER commit this file to git**

### Step 2: Create Firestore Collections
Two collections will be auto-created when data is written:
- `analysis` → document `latest` (costs & savings)
- `schedules` → document `latest` (energy schedules)

### Step 3: Populate Firestore
Run one of these:
```powershell
# Option A: Agent writes both collections
python src/agent/agent.py

# Option B: Manual upload of output files
python firebase_uploader/upload_outputs_to_firestore.py
```

### Step 4: Start API Server
```powershell
python backend/server_firestore.py
# Runs on http://localhost:8080
```

### Step 5: Update Flutter
In `predictions_page.dart`, line 32:
```dart
// CHANGE FROM:
Uri.parse("https://energy-api-632525537450.asia-south1.run.app/analysis")

// TO:
Uri.parse("http://10.0.2.2:8080/analysis")  // Android emulator
// OR
Uri.parse("http://192.168.1.100:8080/analysis")  // Your PC IP
```

---

## 🧪 Testing

### Test 1: Firebase Connection
```powershell
python -c "
import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
doc = db.collection('analysis').document('latest').get()
print('✅ Firestore connected!' if doc.exists else '⚠ No data yet')
"
```

### Test 2: API Endpoints
```powershell
# Test analysis endpoint
curl http://localhost:8080/analysis

# Test schedules endpoint
curl http://localhost:8080/schedules

# Test health check
curl http://localhost:8080/health
```

### Test 3: Flutter App
1. Start emulator or connect device
2. Run: `flutter run`
3. Check console for API responses

---

## 🚨 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: firebase_admin` | `pip install firebase-admin` |
| `[Errno 2] No such file: serviceAccountKey.json` | Download from Firebase Console |
| `PERMISSION_DENIED` in Firestore | Use production mode database |
| `Connection refused` on localhost | Start Flask server first |
| `10.0.2.2` not working on emulator | Make sure server is running on PC |
| `analysis/latest` not found | Run agent.py to populate data |
| Flutter app shows empty data | Check API endpoint in predictions_page.dart |

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `FIREBASE_SETUP_GUIDE.md` | Detailed step-by-step Firebase setup (7 phases) |
| `FLUTTER_ENDPOINT_UPDATE.md` | How to update Flutter endpoints |
| `setup_firebase.py` | Automated setup checker script |
| `backend/server_firestore.py` | New Firestore-based API server |
| `firebase_uploader/README.md` | Manual data upload tool |

---

## 🎯 Data Flow Diagram

```
┌──────────────────┐
│   Data Sources   │
├──────────────────┤
│ agent.py         │
│ (analysis +      │
│  schedules)      │
└────────┬─────────┘
         │ write
         ▼
    ┌──────────────────────┐
    │   Firestore DB       │
    ├──────────────────────┤
    │ ✓ analysis/latest    │
    │ ✓ schedules/latest   │
    └────────┬─────────────┘
             │ read via HTTP
             ▼
    ┌──────────────────────┐
    │  server_firestore.py │
    ├──────────────────────┤
    │ GET /analysis        │
    │ GET /schedules       │
    │ GET /health          │
    └────────┬─────────────┘
             │ HTTP JSON
             ▼
    ┌──────────────────────┐
    │   Flutter App        │
    ├──────────────────────┤
    │ predictions_page.dart│
    │ (displays costs,     │
    │  savings, schedules) │
    └──────────────────────┘
```

---

## 💡 Tips & Best Practices

✅ **DO:**
- Store `serviceAccountKey.json` safely (never commit to git)
- Set up `.gitignore` to exclude the key file
- Use environment variables for production configs
- Test API locally before deploying to Cloud Run
- Monitor Firestore read/write usage (billed per operation)

❌ **DON'T:**
- Commit credentials to GitHub
- Share `serviceAccountKey.json` publicly
- Use test mode for Firestore in production
- Keep server running with `debug=True` in production
- Hardcode API URLs (use environment variables)

---

## 📞 Need Help?

Refer to these official docs:
- [Firebase Console](https://console.firebase.google.com)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Firebase Admin SDK (Python)](https://firebase.google.com/docs/database/admin/start)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flutter HTTP Package](https://pub.dev/packages/http)

---

**Last Updated:** 2026-06-12
**System:** Energy Optimization using Firestore + Flask + Flutter
