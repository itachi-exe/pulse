#!/bin/bash
cd /root/pulse
set -a && [ -f /root/pulse/.env ] && source /root/pulse/.env && set +a
exec /root/pulse/.venv/bin/uvicorn auth_service:app --host 127.0.0.1 --port 7072 --workers 1
