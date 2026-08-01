#!/bin/bash
# Stop WildeBackyard Backend Server

echo "Stopping backend server (port 8000)..."
pkill -f "manage.py runserver 8000"
echo "Backend server stopped."
