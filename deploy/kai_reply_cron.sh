#!/bin/bash
# KAI reply cron — read #general, find @cz-builder-001 messages, reply via LLM.
# Runs every 5 min via crontab.
# Note: PYTHONPATH must be empty (hermes venv would otherwise leak in).
# sampson 2026-06-30: LLM is the default (no --invoke-hermes flag needed anymore;
# passing it now causes "unrecognized arguments" since we removed it in f39f97d).

unset PYTHONPATH
unset SSL_CERT_FILE
cd /home/kali/桌面/agent/agentpub
./.venv/bin/python /home/kali/桌面/agent/agentpub/deploy/kai_reply_cron.py \
    --target cz-builder-001 \
    --limit 200 \
    >> /home/kali/桌面/agent/agentpub/logs/kai_reply_cron.log 2>&1
