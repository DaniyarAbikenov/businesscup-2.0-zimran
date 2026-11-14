#!/bin/sh
# Applies database migrations once. Reads DATABASE_URL (or POSTGRES_URL) from the environment. Never commit the URL.
#   DATABASE_URL='postgresql://...neon.tech/neondb?sslmode=require' scripts/migrate.sh
# or, after `vercel env pull .env.production.local`:  set -a; . ./.env.production.local; set +a; scripts/migrate.sh
set -e
cd "$(dirname "$0")/../backend"
pip install -q -r ../requirements.txt
python -m alembic upgrade head
