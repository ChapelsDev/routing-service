import os
from models import db
from main import app  # or from src.main import app if main.py is in src/

# Build the same path you used in main.py
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'routes.db')
def delete_db():
    """Delete the SQLite database file from instance folder"""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[✔️] Database deleted successfully at {db_path}.")
    else:
        print(f"[❌] No database found at {db_path}.")

def recreate_db():
    """Recreate the database schema"""
    with app.app_context():
        db.create_all()
        print("[✔️] Database schema created successfully.")

def seed_data():
    """Optional: Add test data to the database"""
    from models import Route
    import json
    from datetime import datetime

    sample_route = Route(
        id="test-route",
        user_id="12345",
        origin=json.dumps({"address": "New York, NY"}),
        destination=json.dumps({"address": "Washington, DC"}),
        preferences=str(["scenic", "restaurants"]),
        details="Test route for database seeding",
        created_at=datetime.utcnow()
    )

    with app.app_context():
        db.session.add(sample_route)
        db.session.commit()
        print("[✔️] Test data added successfully.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database Management CLI")
    parser.add_argument("command", choices=["delete", "recreate", "seed"], help="Choose a command")

    args = parser.parse_args()

    if args.command == "delete":
        delete_db()
    elif args.command == "recreate":
        recreate_db()
    elif args.command == "seed":
        seed_data()
