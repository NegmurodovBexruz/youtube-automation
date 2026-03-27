#!/bin/bash
set -e

rm -f /tmp/.X99-lock

Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &

sleep 1

echo "Starting Uvicorn..."
exec uvicorn api.app:app --host 0.0.0.0 --port 8000