#!/bin/bash
# A2A discovery cron - runs hourly
# Looks for new A2A endpoints, logs discoveries to data/a2a_discoveries.jsonl

/home/kali/桌面/agent/agentpub/.venv/bin/python /home/kali/桌面/agent/agentpub/deploy/a2a_scanner.py >> /home/kali/桌面/agent/agentpub/logs/a2a_scanner.log 2>&1