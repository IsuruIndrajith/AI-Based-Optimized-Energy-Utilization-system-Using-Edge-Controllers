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


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def upload_outputs(
    db,
    output_path: str,
    explanations_path: str,
    collection_name: str,
    document_id: str,
):
    output_text = read_text_file(output_path)
    explanations_text = read_text_file(explanations_path)

    doc_ref = db.collection(collection_name).document(document_id)
    payload = {
        "output_text": output_text,
        "explanations_text": explanations_text,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "output_path": os.path.abspath(output_path),
        "explanations_path": os.path.abspath(explanations_path),
    }
    doc_ref.set(payload)
    print(f"Uploaded Firestore document: {collection_name}/{document_id}")


def parse_args() -> argparse.Namespace:
    repo_root = get_repo_root()
    default_output = os.path.join(repo_root, "output.txt")
    default_explanations = os.path.join(repo_root, "output_explanations.txt")

    parser = argparse.ArgumentParser(
        description="Upload output.txt and output_explanations.txt contents to Firebase Firestore."
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help="Path to output.txt",
    )
    parser.add_argument(
        "--explanations",
        default=default_explanations,
        help="Path to output_explanations.txt",
    )
    parser.add_argument(
        "--collection",
        default="analysis",
        help="Firestore collection name to write into",
    )
    parser.add_argument(
        "--document",
        default="outputs_latest",
        help="Firestore document ID to write/update",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="Path to the Firebase service account JSON file (optional). If omitted, uses GOOGLE_APPLICATION_CREDENTIALS or serviceAccountKey.json at repo root.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not os.path.exists(args.output):
        raise FileNotFoundError(f"output file not found: {args.output}")
    if not os.path.exists(args.explanations):
        raise FileNotFoundError(f"explanations file not found: {args.explanations}")

    db = initialize_firestore(args.service_account)
    upload_outputs(
        db,
        args.output,
        args.explanations,
        args.collection,
        args.document,
    )
