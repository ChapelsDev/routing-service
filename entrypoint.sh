#!/bin/sh
set -e

# --- Espera pelo Postgres ----------------------------------------------------
# Extrai host e porto da DATABASE_URL (ex.: postgresql+psycopg://user:pwd@db:5432/rota_db)
host_port=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+):([0-9]+).*|\1 \2|')
db_host=$(echo "$host_port" | cut -d' ' -f1)
db_port=$(echo "$host_port" | cut -d' ' -f2)

echo "[ENTRYPOINT] Waiting for Postgres at $db_host:$db_port ..."
while ! nc -z "$db_host" "$db_port"; do
  sleep 1
done
echo "[ENTRYPOINT] Postgres is up!"

# --- Migrations / seed -------------------------------------------------------
python src/seed.py

# --- Arranca Gunicorn --------------------------------------------------------
exec gunicorn --bind 0.0.0.0:5000 src.main:app
