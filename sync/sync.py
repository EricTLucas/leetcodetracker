"""Manual sync: python sync/sync.py (or run sync.cmd)."""
import sys
from client import LeetCodeClient, compute_unique_solved
from scraper import scrape_code_and_percentiles
from browser import launch_browser, close_browser
from utils import compute_solved_last_7_days

USERNAME = "EricLucas"


def pending_submissions(all_subs, saved):
    # One complete, latest accepted submission per problem, including older gaps.
    latest = {}
    for entry in sorted(all_subs, key=lambda s: int(s["timestamp"]), reverse=True):
        if entry["statusDisplay"] == "Accepted":
            latest.setdefault(entry["titleSlug"], entry)
    for slug, entry in latest.items():
        old = saved.get(slug, {})
        if str(old.get("id")) != str(entry["id"]) or any(
            old.get(field) in (None, "") for field in
            ("code", "runtime", "memory", "runtime_percentile", "memory_percentile")
        ):
            yield entry


def sync():
    from playwright.sync_api import sync_playwright
    import db

    with sync_playwright() as p:
        context = launch_browser(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://leetcode.com/", wait_until="domcontentloaded")
            client = LeetCodeClient(context)
            client.ensure_login(page, USERNAME)
            print("Fetching complete submission history...")
            all_subs = client.fetch_all_submissions()
            unique_slugs = compute_unique_solved(all_subs)
            solved_week, _ = compute_solved_last_7_days(all_subs)
            db.init_db()
            saved = db.get_saved_submissions()
            failures = []
            for entry in pending_submissions(all_subs, saved):
                slug = entry["titleSlug"]
                print(f"Fetching {slug}...")
                try:
                    details = scrape_code_and_percentiles(page, entry["id"])
                    if any(details.get(key) in (None, "") for key in
                           ("code", "runtime", "memory", "runtime_percentile", "memory_percentile")):
                        raise RuntimeError("Incomplete submission details")
                    db.save_submission({
                        **details,
                        "title_slug": slug,
                        "title": entry.get("title") or db.toTitle(slug),
                        "lang": entry["lang"],
                        "timestamp": int(entry["timestamp"]),
                        "status": "Accepted",
                    })
                    db.save_problem(slug, "true")
                except Exception as exc:
                    failures.append(slug)
                    print(f"Could not save {slug}: {exc}")
            if failures:
                raise RuntimeError(f"{len(failures)} submission(s) failed. Saved progress is retained; rerun to retry. Sync totals were not published.")
            recent = sorted(all_subs, key=lambda s: int(s["timestamp"]), reverse=True)[:20]
            db.push_recent_to_firebase(recent)
            db.push_stats_to_firebase(len(unique_slugs), solved_week)
            print(f"Firebase sync complete: {len(unique_slugs)} solved, {solved_week} in the last 7 days.")
        finally:
            close_browser(context)


if __name__ == "__main__":
    try:
        sync()
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Sync did not complete: {exc}", file=sys.stderr)
        sys.exit(1)
