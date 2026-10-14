"""Run the real Ship24 and eBay calls once with the keys saved in the app, to check the parsing.

    .venv\\Scripts\\python scripts\\live_check.py ship24 <tracking number>
    .venv\\Scripts\\python scripts\\live_check.py ebay
    add --exe to use the keys saved by the exe instead of the source version

Keys are read from the app's database and never printed. Each Ship24 check uses your plan's quota.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

import db  # noqa: E402
import ebay  # noqa: E402
import ship24  # noqa: E402


def shape(value):
    """Field names and types only, so the output shows the structure without dumping data."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(value[0])] if value else []
    return type(value).__name__


def check_ship24(api_key, tracking_number):
    raw = requests.post(
        ship24.TRACK_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"trackingNumber": tracking_number},
        timeout=90,
    )
    print("HTTP", raw.status_code)
    print("raw shape:", shape(raw.json()))
    milestone, events = ship24.track(api_key, tracking_number)
    print("parsed milestone:", milestone, "->", ship24.MILESTONE_STATUS.get(milestone, "(status kept)"))
    for event in events[:5]:
        print("  ", event)
    print(f"{len(events)} events parsed")


def check_ebay(settings):
    keys = [settings.get(k) for k in ("ebay_client_id", "ebay_client_secret", "ebay_refresh_token")]
    if not all(keys):
        sys.exit("Connect eBay in the app's Settings tab first.")
    token = ebay.access_token(*keys)
    for name, fetch in (("active listings", ebay.active_listings), ("best offers", ebay.best_offers),
                        ("orders", ebay.orders)):
        rows = fetch(token)
        print(f"{name}: {len(rows)}", "| first:", rows[0] if rows else "-")


def main():
    args = [a for a in sys.argv[1:] if a != "--exe"]
    if "--exe" in sys.argv:
        db.DB_PATH = Path(os.environ["APPDATA"]) / "LogisticsTracker" / "tracker.db"
    if not args or args[0] not in ("ship24", "ebay") or (args[0] == "ship24" and len(args) < 2):
        sys.exit(__doc__)
    db.init()
    settings = db.settings()
    if args[0] == "ship24":
        if not settings.get("ship24_api_key"):
            sys.exit("Save a Ship24 API key in the app's Settings tab first.")
        check_ship24(settings["ship24_api_key"], args[1])
    else:
        check_ebay(settings)


if __name__ == "__main__":
    main()
