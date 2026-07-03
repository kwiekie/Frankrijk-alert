# 🔥 Fire Alert System - Docker Setup

## Quick Start

```bash
cd /Users/m.lange/Frankrijk

# Build & start
docker-compose up -d

# View logs
docker-compose logs -f fire-alert

# Stop
docker-compose down
```

## What It Does

- **fire-alert service**: Runs cron job at **10:00 AM UTC daily**
  - Fetches EFFIS fire data
  - Detects changes
  - Creates Gmail drafts + push notifications
  - Logs to `./data/cron.log`

- **web service** (optional): Serves `./data` on http://localhost:8080
  - View `state.json`, logs, etc. via browser

## Volumes

```
./data/                    # Persistent fire data
  ├── state.json          # Current fire situation
  ├── state_previous.json  # Previous state (for change detection)
  ├── fetch_effis.py      # EFFIS data fetcher
  └── cron.log            # Cron execution log
```

## Environment

- **TZ=UTC** — All timestamps in UTC
- Cron schedule: `0 10 * * *` (10:00 AM UTC, daily)

## Modify Schedule

Edit `entrypoint.sh` line with `CRON_SCHEDULE`:

```bash
# Examples:
# 0 9 * * *      = 9:00 AM UTC daily
# 0 10 * * 1-5   = 10:00 AM UTC weekdays only
# 0 */6 * * *    = Every 6 hours
```

Then rebuild:
```bash
docker-compose up -d --build
```

## View Logs

```bash
# Live cron logs
docker-compose logs -f fire-alert

# Cron job log file
cat ./data/cron.log

# Docker container logs
docker logs france-fire-alert -f
```

## Troubleshooting

**Container exits immediately?**
```bash
docker-compose logs fire-alert
```

**Cron not running?**
```bash
docker-compose exec fire-alert crontab -l
```

**Gmail not working?**
- Ensure Gmail MCP is set up in your Claude Code environment
- Check `alert_handler.py` creates drafts (doesn't send automatically)

## Cleanup

```bash
# Stop & remove containers
docker-compose down

# Remove image
docker rmi france-fire-alert

# Clean all
docker-compose down -v
```
