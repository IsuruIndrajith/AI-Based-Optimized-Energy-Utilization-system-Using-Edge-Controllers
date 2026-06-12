#!/usr/bin/env python3
"""
WALKTHROUGH: Replace Old API with Firestore-based API
=======================================================

This script guides you through the complete process with visual feedback.

Usage:
    python SETUP_WALKTHROUGH.py
"""

def print_section(title, number=None):
    """Print a formatted section header."""
    border = "=" * 70
    if number:
        print(f"\n{border}")
        print(f"  STEP {number}: {title}")
        print(f"{border}\n")
    else:
        print(f"\n{border}")
        print(f"  {title}")
        print(f"{border}\n")


def print_instruction(text, indent=0):
    """Print an instruction."""
    prefix = "  " * indent + "→ "
    print(prefix + text)


def print_code_block(code, language=""):
    """Print a code block."""
    print(f"  ```{language}")
    for line in code.split("\n"):
        print(f"  {line}")
    print(f"  ```\n")


def print_success(text):
    """Print success message."""
    print(f"  ✅ {text}\n")


def print_warning(text):
    """Print warning message."""
    print(f"  ⚠️  {text}\n")


def print_error(text):
    """Print error message."""
    print(f"  ❌ {text}\n")


def print_menu(options):
    """Print a menu and return choice."""
    print("\n  Choose one:")
    for i, option in enumerate(options, 1):
        print(f"    {i}. {option}")
    while True:
        try:
            choice = int(input("\n  Your choice (1-{}): ".format(len(options))))
            if 1 <= choice <= len(options):
                return choice
            print("  Invalid choice. Try again.")
        except ValueError:
            print("  Please enter a number.")


def main():
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  FIRESTORE MIGRATION: Replace Old API with Firestore API".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    print("\n\nThis walkthrough will help you:")
    print("  1. Set up Firebase and Firestore")
    print("  2. Configure security rules")
    print("  3. Deploy the new Firestore API")
    print("  4. Update your Flutter app")
    print("  5. Test everything end-to-end")

    # Phase Selection
    print_section("Which phase do you need help with?", 0)
    phases = [
        "Phase 1: Firebase Account & Firestore Setup",
        "Phase 2: Service Account Credentials",
        "Phase 3: Firestore Security Rules",
        "Phase 4: Deploy Firestore API",
        "Phase 5: Update Flutter App",
        "Phase 6: Test Everything",
        "Show Complete Checklist",
    ]
    choice = print_menu(phases)

    if choice == 1:
        phase_1_setup()
    elif choice == 2:
        phase_2_credentials()
    elif choice == 3:
        phase_3_security()
    elif choice == 4:
        phase_4_deploy()
    elif choice == 5:
        phase_5_flutter()
    elif choice == 6:
        phase_6_test()
    elif choice == 7:
        show_checklist()


def phase_1_setup():
    print_section("Firebase Account & Firestore Setup", 1)

    print("You need to create a Firebase project with Firestore database.\n")

    print_instruction("Visit: https://console.firebase.google.com", 1)
    print_instruction("Click: 'Create a new project' or 'Add project'", 1)
    print_instruction("Enter project name: energy-optimization-system", 1)
    print_instruction("Click: Continue", 1)
    print_instruction("(Skip Google Analytics if you want)", 1)
    print_instruction("Select region closest to you (or asia-south1)", 1)
    print_instruction("Click: Create project", 1)
    print_instruction("Wait 2-3 minutes for project creation", 1)

    print("\n" + "=" * 70)
    print("\nOnce project is created, set up Firestore:\n")

    print_instruction("Go to: Build → Firestore Database", 1)
    print_instruction("Click: Create Database", 1)
    print_instruction("Choose: Start in PRODUCTION mode (not test mode!)", 1)
    print_instruction("Select region: asia-south1", 1)
    print_instruction("Click: Create", 1)
    print_instruction("Wait for database to be ready", 1)

    print_success("Firestore database is now ready!")
    print("\nNext: Run the script again and select 'Phase 2: Service Account Credentials'")


def phase_2_credentials():
    print_section("Service Account Credentials", 2)

    print("You need to download Firebase credentials for your backend.\n")

    print_instruction("In Firebase Console, click: ⚙️ Settings (top-left)", 1)
    print_instruction("Go to: Project settings tab", 1)
    print_instruction("Click: Service Accounts tab", 1)
    print_instruction("Click: Generate new private key", 1)
    print_instruction("A JSON file will download", 1)
    print_instruction("Rename it to: serviceAccountKey.json", 1)
    print_instruction("Move it to your project root:", 1)
    print_instruction("D:\\Research\\Code\\AI-Based-Optimized-Energy-Utilization-system-Using-Edge-Controllers\\", 2)

    print("\n" + "=" * 70)
    print("\nVerify the file looks like this:\n")
    print_code_block('''{
  "type": "service_account",
  "project_id": "energy-optimization-system-abc123",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...",
  "client_email": "firebase-adminsdk-xyz@PROJECT_ID.iam.gserviceaccount.com",
  ...
}''', "json")

    print_warning("NEVER commit this file to git or share it!")
    print("Add this to .gitignore:")
    print_code_block("serviceAccountKey.json")

    print_success("Credentials downloaded and saved!")
    print("\nNext: Run the script again and select 'Phase 3: Firestore Security Rules'")


def phase_3_security():
    print_section("Firestore Security Rules", 3)

    print("Set up security rules so your app can read the data.\n")

    print_instruction("In Firebase Console:", 1)
    print_instruction("Go to: Build → Firestore Database", 1)
    print_instruction("Click: Rules tab", 1)
    print_instruction("Copy and replace the entire content with:", 1)

    print_code_block('''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Allow public READ for mobile app
    match /analysis/{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    
    match /schedules/{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    
    // Block everything else
    match /{document=**} {
      allow read, write: if false;
    }
  }
}''', "firestore")

    print_instruction("Click: Publish", 1)
    print_instruction("Wait for green checkmark (deployment complete)", 1)

    print_success("Security rules published!")
    print("\nNext: Run the script again and select 'Phase 4: Deploy Firestore API'")


def phase_4_deploy():
    print_section("Deploy Firestore API", 4)

    print("Start the new Flask API that reads from Firestore.\n")

    print("Step 1: Install dependencies\n")
    print_code_block("pip install firebase-admin flask flask-cors", "powershell")

    print("Step 2: Populate Firestore with data\n")
    print("Choose one:")
    print_instruction("Option A: Run the agent (generates analysis + schedules)", 1)
    print_code_block("python src/agent/agent.py", "powershell")

    print_instruction("Option B: Upload output files manually", 1)
    print_code_block("python firebase_uploader/upload_outputs_to_firestore.py", "powershell")

    print("Step 3: Start the API server\n")
    print_code_block("python backend/server_firestore.py", "powershell")

    print_instruction("The API will be available at:", 1)
    print_code_block("http://localhost:8080/analysis\nhttp://localhost:8080/schedules", "url")

    print_success("API server is running!")
    print("\nNext: Run the script again and select 'Phase 5: Update Flutter App'")


def phase_5_flutter():
    print_section("Update Flutter App", 5)

    print("Update the Flutter app to use the new API endpoint.\n")

    print("File to edit:")
    print_instruction("lib/pages/predictions_page.dart", 1)

    print("\nFind this line (around line 32):\n")
    print_code_block(
        'Uri.parse("https://energy-api-632525537450.asia-south1.run.app/analysis")',
        "dart"
    )

    print("\nReplace with ONE of these:\n")

    print_instruction("For Android Emulator:", 1)
    print_code_block('Uri.parse("http://10.0.2.2:8080/analysis")', "dart")

    print_instruction("For Physical Device (replace 192.168.1.100 with your PC's IP):", 1)
    print_code_block('Uri.parse("http://192.168.1.100:8080/analysis")', "dart")

    print_instruction("To find your PC's IP, run in PowerShell:", 1)
    print_code_block("ipconfig", "powershell")
    print("Look for: IPv4 Address (e.g., 192.168.x.x)")

    print_instruction("For Cloud Run (after deploying):", 1)
    print_code_block(
        'Uri.parse("https://your-deployed-api.asia-south1.run.app/analysis")',
        "dart"
    )

    print_success("Flutter app endpoint updated!")
    print("\nNext: Run the script again and select 'Phase 6: Test Everything'")


def phase_6_test():
    print_section("Test Everything", 6)

    print("Verify all components are working.\n")

    print("✓ Test 1: Firebase Connection\n")
    print_code_block('''python -c "
import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
doc = db.collection('analysis').document('latest').get()
print('✅ Firestore connected!' if doc.exists else '⚠ No data yet')
"''', "powershell")

    print("✓ Test 2: API Endpoints (in another terminal)\n")
    print("Make sure server_firestore.py is running, then:\n")
    print_code_block('''curl http://localhost:8080/health
curl http://localhost:8080/analysis
curl http://localhost:8080/schedules''', "powershell")

    print("✓ Test 3: Flutter App\n")
    print_instruction("Start emulator or connect physical device", 1)
    print_code_block("flutter run", "powershell")
    print_instruction("Check console output for API responses", 1)
    print_instruction("Verify appliance data is displayed", 1)

    print_success("All tests passed!")
    print("\nYour system is now using Firestore API instead of the old one!")


def show_checklist():
    print_section("Complete Firestore Setup Checklist", 0)

    checklist = [
        ("Firebase Account", "https://console.firebase.google.com"),
        ("Firebase Project Created", "energy-optimization-system"),
        ("Firestore Database Created", "production mode, asia-south1"),
        ("Service Account Key Downloaded", "serviceAccountKey.json at root"),
        ("Dependencies Installed", "firebase-admin, flask, flask-cors"),
        ("Firestore Data Populated", "agent.py or uploader script run"),
        ("Security Rules Published", "public read, private write"),
        ("API Server Running", "python backend/server_firestore.py"),
        ("API Endpoints Tested", "/analysis, /schedules, /health working"),
        ("Flutter App Updated", "lib/pages/predictions_page.dart endpoint changed"),
        ("Flutter App Tested", "data displaying correctly"),
    ]

    for i, (item, detail) in enumerate(checklist, 1):
        status = "☐"
        print(f"  {status} {i:2}. {item:<40} ({detail})")

    print("\n\n📚 Documentation Files:")
    files = [
        "FIREBASE_SETUP_GUIDE.md - Complete 7-phase setup guide",
        "FLUTTER_ENDPOINT_UPDATE.md - Flutter code update instructions",
        "FIRESTORE_SECURITY_RULES.md - Security rules configuration",
        "QUICK_REFERENCE.md - Quick lookup and troubleshooting",
        "setup_firebase.py - Automated setup checker",
    ]

    for doc in files:
        print(f"    📄 {doc}")

    print("\n\n🎯 Next Steps:")
    print("    1. Run each phase of this walkthrough")
    print("    2. Refer to documentation files for detailed info")
    print("    3. Test your API: curl http://localhost:8080/analysis")
    print("    4. Update Flutter app and test")
    print("    5. (Optional) Deploy to Cloud Run for production")

    print("\n\n💬 Need Help?")
    print("    • Check QUICK_REFERENCE.md for troubleshooting")
    print("    • Read FIREBASE_SETUP_GUIDE.md for detailed steps")
    print("    • Visit https://firebase.google.com/docs/firestore")


if __name__ == "__main__":
    main()
