"""
Firestore-based API Server

Reads analysis and schedules data from Firestore instead of local files.
Replaces the old server.py that read from output.txt and output_explanations.txt.

Firestore structure:
- Collection: "analysis" → Document: "latest" → Fields: appliance data + updated_at
- Collection: "schedules" → Document: "latest" → Fields: appliance schedules + updated_at
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, make_response
from flask_cors import CORS

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError as exc:
    raise ImportError(
        "firebase-admin is required. Install with: pip install firebase-admin"
    ) from exc

# ===========================
# Flask Setup
# ===========================
app = Flask(__name__)
CORS(app)  # Allow all origins (restrict this in production)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================
# Firebase Initialization
# ===========================
db = None


def init_firebase():
    """Initialize Firebase Admin SDK with Firestore."""
    global db

    if firebase_admin._apps:
        db = firestore.client()
        logger.info("✅ Using existing Firebase app instance")
        return db

    # Priority 1: serviceAccountKey.json at project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    key_path = os.path.join(project_root, "serviceAccountKey.json")

    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        logger.info(f"✅ Firebase initialized with service account: {key_path}")
    # Priority 2: GOOGLE_APPLICATION_CREDENTIALS environment variable
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        firebase_admin.initialize_app()
        logger.info("✅ Firebase initialized with GOOGLE_APPLICATION_CREDENTIALS")
    # Priority 3: Default credentials (gcloud auth)
    else:
        try:
            firebase_admin.initialize_app()
            logger.info("✅ Firebase initialized with default credentials")
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            raise

    db = firestore.client()
    return db


# ===========================
# API Endpoints
# ===========================


@app.route("/analysis", methods=["GET"])
def get_analysis():
    """
    Fetch analysis data from Firestore (analysis/latest).
    
    Returns JSON like:
    {
        "WashingMachine": {
            "original_cost": 50.5,
            "optimized_cost": 35.2,
            "savings": 15.3
        },
        "Heater": {...},
        "updated_at": "2026-06-12T10:30:00"
    }
    """
    try:
        if db is None:
            return make_response(
                jsonify({"error": "Firestore not initialized"}),
                500,
            )

        doc = db.collection("analysis").document("latest").get()
        if not doc.exists:
            logger.warning("Document 'analysis/latest' not found in Firestore")
            return make_response(
                jsonify({"error": "No analysis data available"}),
                404,
            )

        data = doc.to_dict()
        logger.info(f"✅ Retrieved analysis data with {len(data) - 1} appliances")
        return jsonify(data)

    except Exception as e:
        logger.exception(f"❌ Error in /analysis: {e}")
        return make_response(
            jsonify({"error": "Internal server error", "details": str(e)}),
            500,
        )


@app.route("/schedules", methods=["GET"])
def get_schedules():
    """
    Fetch schedules data from Firestore (schedules/latest).
    
    Returns JSON like:
    {
        "WashingMachine": [[1,0,0,1,...], ...],
        "Heater": [[0,1,1,0,...], ...],
        "updated_at": "2026-06-12T10:30:00"
    }
    """
    try:
        if db is None:
            return make_response(
                jsonify({"error": "Firestore not initialized", "schedules": {}}),
                500,
            )

        doc = db.collection("schedules").document("latest").get()
        if not doc.exists:
            logger.warning("Document 'schedules/latest' not found in Firestore")
            return make_response(
                jsonify({"error": "No schedules data available", "schedules": {}}),
                404,
            )

        data = doc.to_dict()
        logger.info(f"✅ Retrieved schedules data with {len(data) - 1} appliances")
        return jsonify(data)

    except Exception as e:
        logger.exception(f"❌ Error in /schedules: {e}")
        return make_response(
            jsonify(
                {
                    "error": "Internal server error",
                    "details": str(e),
                    "schedules": {},
                }
            ),
            500,
        )


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify API and Firestore connectivity.
    """
    try:
        if db is None:
            return make_response(
                jsonify({
                    "status": "unhealthy",
                    "reason": "Firestore not initialized",
                }),
                503,
            )

        # Try a simple read to verify Firestore connection
        db.collection("analysis").document("latest").get()

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "firestore": "connected",
        })
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return make_response(
            jsonify({
                "status": "unhealthy",
                "reason": str(e),
            }),
            503,
        )


@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API documentation."""
    return jsonify({
        "service": "Energy Optimization API (Firestore-based)",
        "version": "2.0",
        "endpoints": {
            "/analysis": "GET → Retrieves appliance analysis data (costs & savings)",
            "/schedules": "GET → Retrieves optimized energy schedules",
            "/health": "GET → Health check & Firestore connectivity status",
            "/": "GET → This endpoint",
        },
        "firestore_collections": {
            "analysis": "Document 'latest' contains cost analysis",
            "schedules": "Document 'latest' contains energy schedules",
        },
        "data_format": {
            "analysis": {
                "example_appliance": {
                    "original_cost": 50.5,
                    "optimized_cost": 35.2,
                    "savings": 15.3,
                },
                "updated_at": "ISO 8601 timestamp",
            },
            "schedules": {
                "example_appliance": "Array of hourly binary schedules",
                "updated_at": "ISO 8601 timestamp",
            },
        },
    })


# ===========================
# Error Handlers
# ===========================
@app.errorhandler(404)
def not_found(error):
    return make_response(
        jsonify({"error": "Endpoint not found"}),
        404,
    )


@app.errorhandler(500)
def server_error(error):
    return make_response(
        jsonify({"error": "Internal server error"}),
        500,
    )


# ===========================
# Main
# ===========================
if __name__ == "__main__":
    logger.info("Initializing Firestore connection...")
    init_firebase()

    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    logger.info(f"🚀 Starting Flask API server on 0.0.0.0:{port}")
    logger.info(f"📚 Firestore collections: 'analysis' and 'schedules'")
    logger.info(f"🌐 API docs available at http://localhost:{port}/")

    app.run(host="0.0.0.0", port=port, debug=debug)
