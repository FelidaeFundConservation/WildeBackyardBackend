#!/bin/bash
# Start WildeBackyard Backend Server

cd "$(dirname "$0")"

# Kill any existing backend server on port 8000
echo "Stopping existing backend server..."
pkill -f "manage.py runserver 8000"
sleep 1

# Start the backend server
echo "Starting backend server on port 8000..."
source .venv/bin/activate
python manage.py runserver 8000 --settings=config.settings.local
