"""
Quick Setup Script for Firebase + Firestore

Run this after completing the FIREBASE_SETUP_GUIDE.md steps 1-6.
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a shell command and report result."""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
    else:
        print(f"❌ {description} - FAILED")
        return False
    return True


def check_file_exists(path, description):
    """Check if a required file exists."""
    if os.path.exists(path):
        print(f"✅ {description} found: {path}")
        return True
    else:
        print(f"❌ {description} NOT found: {path}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         Firebase + Firestore Quick Setup for Energy System          ║
║                                                                      ║
║  This script will set up everything after Firebase credentials      ║
║  have been downloaded and placed at the project root.               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    # Determine project root
    project_root = os.path.abspath(os.path.dirname(__file__))
    service_account_key = os.path.join(project_root, "serviceAccountKey.json")

    # Step 1: Check for service account key
    print("\n[STEP 1] Checking for Firebase Service Account Key...")
    if not check_file_exists(service_account_key, "serviceAccountKey.json"):
        print("\n❌ SETUP CANNOT CONTINUE")
        print(f"\n   Please download your Firebase service account key from:")
        print(f"   Firebase Console → Project Settings → Service Accounts → Generate Private Key")
        print(f"\n   Save it as: {service_account_key}")
        sys.exit(1)

    # Step 2: Install dependencies
    print("\n[STEP 2] Installing Python dependencies...")
    deps = [
        ("firebase-admin", "pip install firebase-admin"),
        ("flask", "pip install flask"),
        ("flask-cors", "pip install flask-cors"),
    ]

    for package_name, install_cmd in deps:
        try:
            __import__(package_name.replace("-", "_"))
            print(f"✅ {package_name} is already installed")
        except ImportError:
            if run_command(install_cmd, f"Install {package_name}"):
                print(f"✅ {package_name} installed successfully")
            else:
                print(f"⚠ Could not install {package_name}, continuing anyway...")

    # Step 3: Test Firebase connection
    print("\n[STEP 3] Testing Firebase connection...")
    test_code = f"""
import os
os.chdir('{project_root}')
import firebase_admin
from firebase_admin import credentials, firestore

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('{service_account_key}')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    # Try to read a document to verify connection
    doc = db.collection("analysis").document("latest").get()
    
    if doc.exists:
        print("✅ Successfully connected to Firestore")
        print(f"✅ Found analysis data with {{len(doc.to_dict())}} fields")
    else:
        print("⚠ Connected to Firestore, but 'analysis/latest' document not found yet")
        print("  (This is OK - it will be created when your agent.py runs)")
        
except Exception as e:
    print(f"❌ Failed to connect: {{e}}")
    import traceback
    traceback.print_exc()
"""

    result = subprocess.run([sys.executable, "-c", test_code])
    if result.returncode != 0:
        print("\n⚠ Firebase connection test failed. Possible reasons:")
        print("  1. serviceAccountKey.json is invalid")
        print("  2. Firestore database not created yet")
        print("  3. Network connectivity issue")

    # Step 4: Quick test of Flask API
    print("\n[STEP 4] Firebase setup complete!")
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("""
1. Populate Firestore with data:
   
   # Run the agent to write analysis/latest and schedules/latest
   python src/agent/agent.py
   
   OR
   
   # Upload output files manually
   python firebase_uploader/upload_outputs_to_firestore.py

2. Start the Firestore API server:
   
   python backend/server_firestore.py
   
   # The API will run on http://localhost:8080
   
3. Test the API endpoints:
   
   # In another terminal:
   curl http://localhost:8080/analysis
   curl http://localhost:8080/schedules
   curl http://localhost:8080/health

4. Update your Flutter app:
   
   In lib/pages/predictions_page.dart, change:
   
   FROM: https://energy-api-632525537450.asia-south1.run.app/analysis
   TO:   http://10.0.2.2:8080/analysis  (for Android emulator)
         OR your actual device/server IP

5. (Optional) Deploy to Google Cloud Run:
   
   cd backend
   gcloud run deploy energy-api \\
     --source . \\
     --region asia-south1 \\
     --allow-unauthenticated

For more details, see: FIREBASE_SETUP_GUIDE.md
    """)
    print("="*60)


if __name__ == "__main__":
    main()
