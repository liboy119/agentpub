#!/bin/bash
# Start AgentPub uvicorn server detached.
# Run as foreground: script exits immediately, uvicorn keeps running.
cd /home/kali/agentpub
source .venv/bin/activate
setsid nohup uvicorn server.main:app --host 0.0.0.0 --port 7700 --log-level info >/home/kali/agentpub/nohup.out 2>&1 </dev/null &
disown
exit 0
