import os
import secrets
from main import app  # Supondo que main.py esteja no mesmo diretório
from models import db, ApiKey

def seed_api_key():
    """
    Seeds the database with a default API key if none exist.
    """
    # Lê a variável de ambiente 'SERVER_NAME' ou usa um valor padrão
    server_name = os.getenv("SERVER_NAME", "localhost:5000")

    with app.app_context():
        db.create_all()  # Garante que as tabelas existam
        if not ApiKey.query.first():
            default_key = secrets.token_urlsafe(32)
            new_api_key = ApiKey(key=default_key, owner="default_user")
            db.session.add(new_api_key)
            db.session.commit()
            print(f"[SEED] Inserted default API key: {default_key}")
            print("[SEED] Please save this key securely. It will not be shown again.")
            print(f"[LINK] http://{server_name}")
        else:
            print("[SEED] API key(s) already exist. No new key inserted.")
            print(f"[LINK] http://{server_name}")

if __name__ == "__main__":
    seed_api_key()
