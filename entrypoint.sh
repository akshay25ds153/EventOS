#!/bin/sh

# Exit immediately on error
set -e

# Wait for PostgreSQL if DB_HOST is set
if [ -n "$DB_HOST" ]; then
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    python -c "
import socket
import time
import os

host = os.environ.get('DB_HOST')
port = int(os.environ.get('DB_PORT', 5432))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        time.sleep(1)
"
    echo "PostgreSQL is online!"
fi

# Apply migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run Celery worker or Gunicorn WSGI depending on command args
if [ "$1" = "celery" ]; then
    echo "Booting up Celery Worker..."
    exec celery -A EventManagement worker --loglevel=info
else
    echo "Booting up Gunicorn WSGI Web Server..."
    exec gunicorn EventManagement.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
