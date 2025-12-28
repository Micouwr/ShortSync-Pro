#!/bin/bash
# docker/entrypoint.sh

set -e

echo "🚀 ShortSync Pro - Starting up..."

# Wait for database if needed
if [ -n "${DB_HOST}" ]; then
  echo "⏳ Waiting for database..."
  while ! nc -z ${DB_HOST} ${DB_PORT:-5432}; do
    sleep 1
  done
  echo "✅ Database is ready"
fi

# Wait for Redis if needed
if [ -n "${REDIS_HOST}" ]; then
  echo "⏳ Waiting for Redis..."
  while ! nc -z ${REDIS_HOST} ${REDIS_PORT:-6379}; do
    sleep 1
  done
  echo "✅ Redis is ready"
fi

# Initialize database if needed
if [ -n "${INIT_DB}" ]; then
  echo "📦 Initializing database..."
  python -c "
from bot.database import init_db
init_db()
print('Database initialized')
"
fi

# Run migrations if needed
if [ -n "${RUN_MIGRATIONS}" ]; then
  echo "🔄 Running migrations..."
  alembic upgrade head
fi

# Run the main application
echo "🚀 Starting ShortSync Pro..."
exec "$@"
