import requests

TRACK_URL = "https://api.ship24.com/public/v1/trackers/track"

# Ship24 milestone -> shipment status; others (pending, exception) leave it alone
MILESTONE_STATUS = {
    "info_received": "label_created",
    "in_transit": "shipped",
    "out_for_delivery": "shipped",
    "failed_attempt": "shipped",
    "available_for_pickup": "shipped",
    "delivered": "delivered",
}


def track(api_key, tracking_number):
    """Return (milestone, events newest first) for a tracking number."""
    response = requests.post(
        TRACK_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"trackingNumber": tracking_number},
        timeout=90,  # the first lookup of a number can take up to a minute
    )
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Ship24: HTTP {response.status_code}")
    if not response.ok:
        errors = body.get("errors") or [{}]
        raise RuntimeError(f"Ship24: {errors[0].get('message', response.status_code)}")

    tracking = body["data"]["trackings"][0]
    events = sorted(tracking["events"], key=lambda e: e["occurrenceDatetime"], reverse=True)
    return tracking["shipment"]["statusMilestone"], events
