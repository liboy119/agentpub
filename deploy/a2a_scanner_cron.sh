#!/bin/bash
# A2A discovery cron - runs every 15 min
# Broadcasts AgentPub invitation to known A2A endpoints + discovers new agents.
# Note: PYTHONPATH must be empty so agentpub venv is used, not hermes venv.

unset PYTHONPATH
unset SSL_CERT_FILE
cd /home/kali/桌面/agent/agentpub
./.venv/bin/python /home/kali/桌面/agent/agentpub/deploy/a2a_scanner.py >> /home/kali/桌面/agent/agentpub/logs/a2a_scanner.log 2>&1
