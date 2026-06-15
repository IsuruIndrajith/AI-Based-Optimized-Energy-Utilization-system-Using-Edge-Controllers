# Firestore Migration: Complete Index

## 📖 Documentation & Guides (Read These First)

Start with **one** of these depending on your learning style:

### 🚀 For Quick Start (5 minutes)
**File:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- Quick checklist
- Common issues & fixes
- Copy-paste commands

### 📚 For Complete Setup (Step-by-Step)
**File:** [FIREBASE_SETUP_GUIDE.md](FIREBASE_SETUP_GUIDE.md)
- 7 detailed phases
- Firebase account creation
- Service account generation
- API deployment

### 🎯 For Interactive Walkthrough
**File:** Run this command in PowerShell:
```powershell
python SETUP_WALKTHROUGH.py
```
- Phase-by-phase guidance
- Visual instructions
- Code examples

### 🛡️ For Security Configuration
**File:** [FIRESTORE_SECURITY_RULES.md](FIRESTORE_SECURITY_RULES.md)
- Firestore security rules
- Permission management
- Troubleshooting auth issues

### 📱 For Flutter App Updates
**File:** [FLUTTER_ENDPOINT_UPDATE.md](FLUTTER_ENDPOINT_UPDATE.md)
- How to update predictions_page.dart
- Local vs. production endpoints
- Testing on emulator/device

---

## 🔧 Scripts & Tools

### Setup & Validation
| Script | Purpose | Run with |
|--------|---------|----------|
| `setup_firebase.py` | Check Firebase connection, install deps | `python setup_firebase.py` |
| `SETUP_WALKTHROUGH.py` | Interactive phase-by-phase guide | `python SETUP_WALKTHROUGH.py` |

### Data Upload
| Script | Purpose | Location |
|--------|---------|----------|
| `firebase_uploader/upload_outputs_to_firestore.py` | Manual data upload | `python firebase_uploader/upload_outputs_to_firestore.py` |

### API Servers
| Server | Purpose | Location | Run with |
|--------|---------|----------|----------|
| `backend/server.py` | Old file-based API | `backend/` | `python backend/server.py` |
| `backend/server_firestore.py` | **NEW** Firestore API ⭐ | `backend/` | `python backend/server_firestore.py` |

### Data Writers
| Script | Purpose | Location |
|--------|---------|----------|
| `src/agent/agent.py` | Generates analysis & writes to Firestore | `src/agent/` |

---

## 📁 Project Structure

```
Project Root/
│
├── 📄 FIREBASE_SETUP_GUIDE.md              ← Start here for complete setup
├── 📄 QUICK_REFERENCE.md                   ← Quick lookup guide
├── 📄 FLUTTER_ENDPOINT_UPDATE.md           ← Update Flutter app
├── 📄 FIRESTORE_SECURITY_RULES.md          ← Security configuration
├── 🐍 SETUP_WALKTHROUGH.py                 ← Interactive walkthrough
├── 🔑 serviceAccountKey.json              ← Firebase credentials (YOU DOWNLOAD)
│
├── 📁 backend/
│   ├── server.py                           ← Old API (file-based)
│   ├── server_firestore.py                 ← NEW API (Firestore) ⭐
│   └── requirements.txt
│
├── 📁 firebase_uploader/
│   ├── upload_outputs_to_firestore.py     ← Manual data uploader
│   └── README.md                           ← Usage instructions
│
├── 📁 src/
│   └── agent/
│       └── agent.py                        ← Writes to Firestore
│
└── 📁 mobile-app/flutter_application_1/
    └── lib/pages/
        └── predictions_page.dart           ← Update endpoint here
```

---

## 🎯 Quick Setup Flow

```
1. CREATE FIREBASE ACCOUNT
   └─→ https://console.firebase.google.com
   
2. CREATE FIRESTORE DATABASE
   └─→ Firebase Console → Build → Firestore Database
   
3. DOWNLOAD SERVICE ACCOUNT KEY
   └─→ Firebase Console → Settings → Service Accounts → Generate Key
   └─→ Save as: serviceAccountKey.json
   
4. CONFIGURE SECURITY RULES
   └─→ Firebase Console → Firestore → Rules
   └─→ Use rules from FIRESTORE_SECURITY_RULES.md
   
5. POPULATE FIRESTORE
   └─→ python src/agent/agent.py
   └─→ OR: python firebase_uploader/upload_outputs_to_firestore.py
   
6. START API SERVER
   └─→ python backend/server_firestore.py
   └─→ Runs on: http://localhost:8080
   
7. UPDATE FLUTTER APP
   └─→ Edit: lib/pages/predictions_page.dart
   └─→ Change endpoint to: http://10.0.2.2:8080/analysis
   
8. TEST
   └─→ flutter run
   └─→ curl http://localhost:8080/analysis
   └─→ Verify data displays correctly
```

---

## 🧪 Testing & Validation

### Check 1: Firestore Connection ✅
```powershell
python setup_firebase.py
```
Expected: ✅ Connected to Firestore

### Check 2: Data Population ✅
```powershell
python src/agent/agent.py
```
Expected: ✅ Successfully updated analysis/latest in Firestore

### Check 3: API Endpoints ✅
```powershell
# Terminal 1: Start API
python backend/server_firestore.py

# Terminal 2: Test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/analysis
curl http://localhost:8080/schedules
```
Expected: JSON responses with appliance data

### Check 4: Flutter Integration ✅
```powershell
flutter run
```
Expected: App displays appliance costs & savings from Firestore

---

## 🐛 Troubleshooting by Issue

### "ModuleNotFoundError: firebase_admin"
```powershell
pip install firebase-admin
pip install flask flask-cors
```

### "serviceAccountKey.json not found"
1. Download from Firebase Console (Settings → Service Accounts)
2. Save to project root with exact name: `serviceAccountKey.json`
3. Re-run: `python setup_firebase.py`

### "PERMISSION_DENIED" error
1. Check Firestore security rules in Firebase Console
2. Use rules from: [FIRESTORE_SECURITY_RULES.md](FIRESTORE_SECURITY_RULES.md)
3. Publish rules and wait for green checkmark

### "Connection refused" on http://localhost:8080
1. Start API server: `python backend/server_firestore.py`
2. Wait for "🚀 Starting Flask API server" message
3. Test: `curl http://localhost:8080/health`

### Flutter shows empty data
1. Check endpoint in `predictions_page.dart`
2. For Android emulator use: `http://10.0.2.2:8080/analysis`
3. Verify API server is running
4. Check: `curl http://localhost:8080/analysis` returns data

### "analysis/latest" not found in Firestore
1. Run agent to populate: `python src/agent/agent.py`
2. Or upload manually: `python firebase_uploader/upload_outputs_to_firestore.py`
3. Wait a few seconds
4. Check Firestore Console to verify documents exist

### Data not updating in real-time
1. App re-fetches every 30 minutes (see `predictions_page.dart`)
2. Manually refresh app to see latest data
3. Check if agent is running: `python src/agent/agent.py`

**For more troubleshooting:** See [QUICK_REFERENCE.md](QUICK_REFERENCE.md#-troubleshooting)

---

## 📊 Architecture Overview

### Old System (File-based)
```
agent.py ──→ output.txt ──→ server.py /analysis ──→ Flutter App
             output_explanations.txt
```

### New System (Firestore-based)
```
agent.py ──→ Firestore DB ──→ server_firestore.py /analysis ──→ Flutter App
             (analysis/latest)
             (schedules/latest)
```

### Benefits of New System
✅ Real-time data updates  
✅ Scalable to multiple devices  
✅ Easy API integration  
✅ Cloud-based (no local files needed)  
✅ Can deploy globally  

---

## 🚀 Next Steps

### Phase 1: Setup (Today)
- [ ] Read [FIREBASE_SETUP_GUIDE.md](FIREBASE_SETUP_GUIDE.md)
- [ ] Create Firebase account and Firestore database
- [ ] Download service account key
- [ ] Run: `python setup_firebase.py`

### Phase 2: Deploy (Today)
- [ ] Run: `python src/agent/agent.py`
- [ ] Run: `python backend/server_firestore.py`
- [ ] Test: `curl http://localhost:8080/analysis`

### Phase 3: Integration (Today/Tomorrow)
- [ ] Update Flutter app endpoint
- [ ] Test on Android emulator or physical device
- [ ] Verify data displays correctly

### Phase 4: Production (Optional)
- [ ] Deploy to Google Cloud Run
- [ ] Update Flutter endpoint to production URL
- [ ] Set up monitoring and alerts
- [ ] Document your setup

---

## 📞 Support Resources

**Official Docs:**
- [Firebase Console](https://console.firebase.google.com)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Firebase Admin SDK (Python)](https://firebase.google.com/docs/database/admin/start)
- [Flask Documentation](https://flask.palletsprojects.com/)

**This Project:**
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Cheat sheet
- [FIREBASE_SETUP_GUIDE.md](FIREBASE_SETUP_GUIDE.md) - Detailed guide
- [FIRESTORE_SECURITY_RULES.md](FIRESTORE_SECURITY_RULES.md) - Security setup
- [FLUTTER_ENDPOINT_UPDATE.md](FLUTTER_ENDPOINT_UPDATE.md) - App integration

**Interactive:**
- Run: `python SETUP_WALKTHROUGH.py`

---

## ✨ Key Files Created for You

| File | Size | Purpose |
|------|------|---------|
| `backend/server_firestore.py` | 250 lines | NEW Firestore API server |
| `FIREBASE_SETUP_GUIDE.md` | 400 lines | Complete setup guide |
| `QUICK_REFERENCE.md` | 350 lines | Quick lookup reference |
| `FIRESTORE_SECURITY_RULES.md` | 250 lines | Security configuration |
| `FLUTTER_ENDPOINT_UPDATE.md` | 200 lines | App integration guide |
| `SETUP_WALKTHROUGH.py` | 400 lines | Interactive walkthrough |
| `setup_firebase.py` | 200 lines | Setup validation script |
| `firebase_uploader/upload_outputs_to_firestore.py` | 150 lines | Manual uploader |

**Total:** ~2000 lines of guides + code ready for production

---

## 🎓 Learning Path

**Beginner** (Just want it working)
→ Read: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)  
→ Run: `python SETUP_WALKTHROUGH.py`  
→ Done in 30 minutes

**Intermediate** (Want to understand)
→ Read: [FIREBASE_SETUP_GUIDE.md](FIREBASE_SETUP_GUIDE.md)  
→ Read: [FIRESTORE_SECURITY_RULES.md](FIRESTORE_SECURITY_RULES.md)  
→ Done in 2 hours

**Advanced** (Want full details)
→ Read all documentation  
→ Review: `backend/server_firestore.py`  
→ Review: `src/agent/agent.py`  
→ Deploy to Cloud Run  
→ Done in 4 hours

---

**Last Updated:** 2026-06-12  
**Status:** Ready for production  
**Support:** See documentation files above

