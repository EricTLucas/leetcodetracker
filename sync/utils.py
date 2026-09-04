from datetime import datetime, UTC, timedelta

def get_7day_start():
    today = datetime.now(UTC)
    start = today - timedelta(days=7)
    return start

def compute_solved_last_7_days(all_subs):
    seven_days_ago = get_7day_start().timestamp()

    slugs = set()

    for s in all_subs:
        if s["statusDisplay"] != "Accepted":
            continue

        ts = s["timestamp"]

        try:
            ts = int(ts)
        except (TypeError, ValueError):
            continue

        if ts >= seven_days_ago:
            slugs.add(s["titleSlug"])

    return len(slugs), slugs