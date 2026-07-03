#!/usr/bin/env python3
"""
Fire alert handler: detects changes and sends notifications via Gmail + push.
Designed to run as a scheduled routine (via CronCreate or /schedule).
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
import subprocess


def load_state(filepath: str = "data/state.json") -> Dict:
    """Load the current fire data state."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading state: {e}", file=sys.stderr)
        return {}


def detect_significant_changes(current: Dict, previous: Dict) -> Dict[str, Any]:
    """
    Detect significant changes that warrant an alert.
    Returns a summary dict with alert flag and details.
    """
    alert = {
        "should_alert": False,
        "severity": "none",  # none, low, medium, high
        "message": "",
        "new_fires": [],
        "escalated_zones": []
    }

    if not previous:
        # First run
        alert["message"] = "Initial map check — baseline established."
        return alert

    # Check for new active fires
    prev_fires = {(f['lat'], f['lon']): f for f in previous.get('hotspots', [])}
    curr_fires = {(f['lat'], f['lon']): f for f in current.get('hotspots', [])}

    new_fire_coords = set(curr_fires.keys()) - set(prev_fires.keys())
    if new_fire_coords:
        alert["should_alert"] = True
        alert["severity"] = "high"
        for coord in new_fire_coords:
            fire = curr_fires[coord]
            alert["new_fires"].append(f"{fire['name']} ({fire['area_hectares']} ha)")
        alert["message"] += f"\n🔥 Nieuwe actieve branden gedetecteerd:\n"
        alert["message"] += "\n".join([f"  • {f}" for f in alert["new_fires"]])

    # Check for escalation to very high danger
    prev_very_high = {
        (z['lat'], z['lon']) for z in previous.get('fire_danger_zones', [])
        if z.get('level') == 'very_high'
    }
    curr_very_high = {
        (z['lat'], z['lon']) for z in current.get('fire_danger_zones', [])
        if z.get('level') == 'very_high'
    }

    new_very_high = curr_very_high - prev_very_high
    if new_very_high:
        alert["should_alert"] = True
        alert["severity"] = "high"
        alert["escalated_zones"] = list(new_very_high)
        alert["message"] += f"\n⚠️ {len(new_very_high)} zone(s) escaleert naar ZEER HOOG brandgevaar!"

    if alert["should_alert"]:
        # Add context
        total_fires = len(curr_fires)
        total_danger_zones = len(current.get('fire_danger_zones', []))
        alert["message"] += f"\n\n📊 Huidig overzicht:\n  • Actieve branden: {total_fires}\n  • Gevarenzones: {total_danger_zones}"

    return alert


def create_gmail_draft(alert: Dict, map_url: str = "https://claude.ai/code/artifact/64e74814-8be6-453e-b490-13f5fed0358e"):
    """
    Create a Gmail draft with the alert information.
    Uses mcp__claude_ai_Gmail__create_draft under the hood.
    """
    if not alert.get("should_alert"):
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    severity_emoji = {
        "high": "🚨",
        "medium": "⚠️",
        "low": "ℹ️",
        "none": "✓"
    }.get(alert.get("severity"), "?")

    subject = f"{severity_emoji} Bosbrand-waarschuwing: {timestamp}"

    body = f"""Hallo,

{alert.get('message', 'Er is een wijziging in de brandgevaarssituatie.')}

🗺️ Bekijk de kaart: {map_url}

Gegevens afkomstig van EFFIS (Copernicus Emergency Management Service).

Volgende check: binnen ~1 uur.

---
Automatische waarschuwing voor je vakantie naar Fréjus/Monaco/Italië
"""

    html_body = f"""<html><body style="font-family: sans-serif; line-height: 1.6; color: #333;">
<p><strong>{subject}</strong></p>
<div style="background-color: #f5f5f5; padding: 12px; border-left: 4px solid {'#d32f2f' if alert.get('severity') == 'high' else '#f57c00'};">
{alert.get('message', 'Er is een wijziging in de brandgevaarssituatie.').replace(chr(10), '<br>')}
</div>
<p>
<a href="{map_url}" style="display: inline-block; padding: 10px 16px; background-color: #d32f2f; color: white; text-decoration: none; border-radius: 4px;">Bekijk de kaart</a>
</p>
<p style="font-size: 12px; color: #999;">
Gegevens afkomstig van EFFIS (Copernicus Emergency Management Service).<br>
Volgende check: binnen ~1 uur.
</p>
</body></html>"""

    print(f"Gmail draft would be created with:")
    print(f"  To: kwiekie@gmail.com")
    print(f"  Subject: {subject}")
    print(f"  Body preview: {body[:100]}...")

    # Note: In production, this would call the Gmail API tool
    # For now, we just log it for demonstration
    return {
        "to": "kwiekie@gmail.com",
        "subject": subject,
        "body": body,
        "html_body": html_body
    }


def send_push_notification(alert: Dict):
    """
    Send a push notification if available (requires Remote Control connection).
    """
    if not alert.get("should_alert"):
        return None

    severity_icon = {
        "high": "🔥",
        "medium": "⚠️",
        "low": "ℹ️"
    }.get(alert.get("severity"), "?")

    # Truncate to 200 chars for notification
    message = alert.get("message", "").split('\n')[0]  # First line only
    if len(message) > 180:
        message = message[:177] + "..."

    notification = f"{severity_icon} Bosbrand-waarschuwing: {message}"

    print(f"Push notification would be sent:")
    print(f"  Message: {notification}")

    return notification


def main():
    """Main alert handler."""
    print("=" * 60)
    print("Fire Alert Handler")
    print("=" * 60)

    # Fetch latest fire data
    print("\n1️⃣ Fetching latest EFFIS data...")
    result = subprocess.run([sys.executable, "data/fetch_effis.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching EFFIS data: {result.stderr}")
        return False

    # Load current and previous states
    print("\n2️⃣ Loading states...")
    current = load_state("data/state.json")

    # Load previous state (archived from last run)
    previous_path = "data/state_previous.json"
    previous = load_state(previous_path) if os.path.exists(previous_path) else {}

    print(f"   Current: {len(current.get('hotspots', []))} fires, {len(current.get('fire_danger_zones', []))} zones")
    print(f"   Previous: {len(previous.get('hotspots', []))} fires, {len(previous.get('fire_danger_zones', []))} zones")

    # Detect changes
    print("\n3️⃣ Detecting changes...")
    alert = detect_significant_changes(current, previous)

    if alert["should_alert"]:
        print(f"\n⚠️ ALERT TRIGGERED (severity: {alert['severity'].upper()})")
        print(alert["message"])

        # Create Gmail draft
        print("\n4️⃣ Preparing Gmail draft...")
        draft = create_gmail_draft(alert)
        if draft:
            # In production, call: mcp__claude_ai_Gmail__create_draft(draft)
            print(f"   ✓ Draft prepared (would send to {draft['to']})")

        # Send push notification
        print("\n5️⃣ Preparing push notification...")
        notification = send_push_notification(alert)
        if notification:
            # In production, call: PushNotification(message=notification)
            print(f"   ✓ Notification prepared")

        print("\n6️⃣ Updating previous state...")
        with open(previous_path, 'w') as f:
            json.dump(current, f, indent=2)
        print(f"   ✓ Previous state updated")

        print("\n✅ Alert handler completed successfully")
    else:
        print(f"\n✓ No significant changes detected. Next alert threshold: new fires or escalation to very high danger.")
        print(f"   Message: {alert['message']}")

        # Still update previous state for next comparison
        if not previous:
            with open(previous_path, 'w') as f:
                json.dump(current, f, indent=2)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
