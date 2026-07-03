import os
from pathlib import Path
import ee
from google.oauth2 import service_account

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ee_initialized = False  # prevents re-initialization

def initialize_earth_engine():
    """Initialize Earth Engine with service account credentials (local + Render support)"""
    global _ee_initialized

    if _ee_initialized:
        return
    try:
        # 1️⃣ Try Render secret file first
        key_path = os.environ.get("EE_KEY_PATH")

        if key_path:
            print("🔐 Using Render secret file for Earth Engine authentication")

            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/earthengine"],
            )
        else:
            # 2️⃣ Fallback to local file
            local_key = BASE_DIR / "gee_key" / "ee-key.json"

            print(f"💻 Using local Earth Engine key: {local_key}")

            credentials = service_account.Credentials.from_service_account_file(
                local_key,
                scopes=["https://www.googleapis.com/auth/earthengine"],
            )

        # Initialize Earth Engine
        ee.Initialize(credentials)

        print("✅ Earth Engine initialized successfully")

        _ee_initialized = True

    except Exception as e:
        print(f"❌ Earth Engine initialization failed: {e}")
