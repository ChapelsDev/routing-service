
import secrets
from main import app  # Direct import assuming seed.py, main.py, and models.py are in the same directory.
from models import db, ApiKey

def seed_api_key():
    """
    Seeds the database with a default API key if none exist.
    """
    with app.app_context():
        db.create_all()  # Ensure tables exist.
        if not ApiKey.query.first():
            default_key = secrets.token_urlsafe(32)
            new_api_key = ApiKey(key=default_key, owner="default_user")
            db.session.add(new_api_key)
            db.session.commit()
            print(f"[SEED] Inserted default API key: {default_key}")
            print("[SEED] Please save this key securely. It will not be shown again.")
            print("[LINK] http://localhost:5000")
        else:
            print("[SEED] API key(s) already exist. No new key inserted.")
            print("[LINK] http://localhost:5000")

if __name__ == "__main__":
    seed_api_key()
