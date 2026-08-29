#!/bin/bash
cd /root/pulse
exec /root/pulse/.venv/bin/uvicorn auth_service:app --host 127.0.0.1 --port 7072 --workers 1
