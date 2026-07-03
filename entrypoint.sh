#!/bin/bash
set -e

# Fire Alert System - Docker Entrypoint
# Handles scheduled EFFIS checks and alerts via Gmail

echo "🔥 Fire Alert System (Docker)"
echo "================================"

# Create cron job for daily 10:00 AM UTC check
CRON_SCHEDULE="0 10 * * *"
CRON_JOB="$CRON_SCHEDULE cd /app && python3 alert_handler.py >> /app/data/cron.log 2>&1"

# Setup cron
echo "📅 Setting up cron schedule: $CRON_SCHEDULE (10:00 AM UTC daily)"
echo "$CRON_JOB" | crontab -

# Start cron daemon
echo "⚙️ Starting cron daemon..."
cron

# Run initial check (optional - on first startup)
if [ ! -f "/app/data/state.json" ]; then
    echo "🚀 Running initial EFFIS data fetch..."
    python3 /app/alert_handler.py
else
    echo "✓ Previous state found. Cron will handle next check."
fi

# Keep container running
echo "✓ Container running. Cron will execute daily at 10:00 AM UTC."
tail -f /dev/null
