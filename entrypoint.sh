#!/bin/sh
# entrypoint.sh

sleep 5
# Or if using Flask-Migrate:
# flask db upgrade

# Run the seed script to ensure at least one API key is present
python src/seed.py

# Now start the Flask application using Gunicorn
exec gunicorn --bind 0.0.0.0:5000 src.main:app
