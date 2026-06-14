import argparse
import os
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError as exc:
    raise ImportError(
        "firebase-admin is required. Install it with `pip install firebase-admin`."
    ) from exc


def get_repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def initialize_firestore(service_account_path: str | None = None):
    if firebase_admin._apps:
        return firestore.client()

    if service_account_path:
        service_account_path = os.path.abspath(service_account_path)
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Service account file not found: {service_account_path}")
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        print(f"Initialized Firebase using service account: {service_account_path}")
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        firebase_admin.initialize_app()
        print("Initialized Firebase using GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    else:
        default_key = os.path.join(get_repo_root(), "serviceAccountKey.json")
        if os.path.exists(default_key):
            cred = credentials.Certificate(default_key)
            firebase_admin.initialize_app(cred)
            print(f"Initialized Firebase using default key at: {default_key}")
        else:
            firebase_admin.initialize_app()
            print("Initialized Firebase using default credentials.")

    return firestore.client()


def send_user_message(db, message: str, collection_name: str, document_id: str):
    doc_ref = db.collection(collection_name).document(document_id)
    payload = {
        "message": message,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    doc_ref.set(payload)
    print(f"Uploaded user preference message to Firestore: {collection_name}/{document_id} -> '{message}'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload user preference message to Firebase Firestore."
    )
    parser.add_argument(
        "--message", "-m",
        required=True,
        help="User instruction message to send (e.g., 'Allow AC_Power ON during peak hours')",
    )
    parser.add_argument(
        "--collection",
        default="preferences",
        help="Firestore collection name to write into",
    )
    parser.add_argument(
        "--document",
        default="latest",
        help="Firestore document ID to write/update",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="Path to the Firebase service account JSON file (optional).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    db = initialize_firestore(args.service_account)
    send_user_message(
        db,
        args.message,
        args.collection,
        args.document,
    )
