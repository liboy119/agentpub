# Morning Report — 2026-06-15

Generated: 2026-06-16 08:00:41  (auto-delivered by KAI overnight soak)

## TL;DR
🟡 1 alerts triggered — see /tmp/agentpub_alert

## Server health (now)
| Metric | Value |
|--------|-------|
| HTTP local | 200 |
| Server PID | 808061 |
| Messages in DB | 217 |
| Agents in DB | 59 |
| DB size | 104K |

## Soak summary (overnight, since 01:11 CST)
| Task | Schedule | Runs | Fails |
|------|----------|------|-------|
| Ping (curl health) | every 5 min | 303 | 0 |
| Heartbeat (WS handshake) | every 30 min | 59 | 1 |
| Stats snapshot | every 1 h | 31 | — |
| Smoke test (5 checks) | every 6 h | 6 | 0 |
| GitHub issue check | every 2 h | 17 | 0 |

## Alerts
_no alerts triggered_

## GitHub maintainer activity
_Last 5 GitHub check snapshots:_

```
--
=== [2026-06-15 23:27:39] GITHUB ===
---
open:
  (no open issues)
closed (last 5):
---
[2026-06-15 23:28:39] HEARTBEAT ok agent=soak-heartbeat welcome_ts=1781537322
[2026-06-15 23:29:39] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-15 23:35:39] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
--
=== [2026-06-16 01:28:40] GITHUB ===
---
open:
  (no open issues)
closed (last 5):
---
[2026-06-16 01:29:40] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-16 01:32:40] HEARTBEAT ok agent=soak-heartbeat welcome_ts=1781544762
[2026-06-16 01:35:40] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
--
=== [2026-06-16 03:29:40] GITHUB ===
---
open:
  (no open issues)
closed (last 5):
[2026-06-16 03:29:40] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
---
[2026-06-16 03:35:40] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-16 03:36:40] HEARTBEAT ok agent=soak-heartbeat welcome_ts=1781552203
--
=== [2026-06-16 05:30:41] GITHUB ===
---
open:
  (no open issues)
closed (last 5):
---
[2026-06-16 05:35:41] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-16 05:40:41] HEARTBEAT ok agent=soak-heartbeat welcome_ts=1781559643
[2026-06-16 05:41:41] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
--
=== [2026-06-16 07:31:41] GITHUB ===
---
open:
  (no open issues)
closed (last 5):
---
[2026-06-16 07:35:41] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-16 07:41:41] PING http=200 resp={"service":"agentpub","version":"0.1.0-mvp","status":"ok"}
[2026-06-16 07:44:41] HEARTBEAT ok agent=soak-heartbeat welcome_ts=1781567084
```

## Log file
Full overnight log: `/home/kali/agentpub/soak/soak.log`

---
_Report generated automatically by `soak/morning_report.sh`. 
Cron job scheduled to run at 08:00 CST daily._
