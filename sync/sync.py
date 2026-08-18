from client import fetch_recent, extract_submission, fetch_all_submissions, compute_unique_solved
from db import init_db, save_submission_with_retry, get_conn, get_meta, set_meta, get_known_slugs, save_problem
from scraper import scrape_code_and_percentiles
import os
import json
from datetime import datetime, UTC, timedelta
import firebase_admin
from firebase_admin import credentials, firestore


USERNAME = "EricLucas"

raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(raw)

cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()


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

        # normalize timestamp
        try:
            ts = int(ts)
        except (TypeError, ValueError):
            continue

        if ts >= seven_days_ago:
            slugs.add(s["titleSlug"])

    return len(slugs), slugs




# -----------------------------
# NEW: update solved_week meta
# -----------------------------
def update_solved_week(all_subs):
    solved_count, slugs = compute_solved_last_7_days(all_subs)
    set_meta("solved_week", solved_count)
    print(f"Solved last 7 days: {solved_count}")
    return solved_count


def push_stats_to_firebase(total_unique, solved_week):
    db.collection("leetcode").document("stats").set({
        "total_unique_solved": total_unique,
        "solved_week": solved_week,
        "last_sync": datetime.now(UTC).isoformat()
    })
    print("Pushed stats to Firebase.")


def push_recent_to_firebase(recent):
    batch = db.batch()
    col = db.collection("leetcode").document("recent").collection("items")

    for sub in recent:
        doc = col.document(sub["titleSlug"])
        batch.set(doc, sub)

    batch.commit()
    print("Pushed recent submissions to Firebase.")


def push_problems_to_firebase():
    # Pull all problems from SQLite
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM submissions ORDER BY timestamp DESC").fetchall()

    batch = db.batch()
    col = db.collection("leetcode").document("problems").collection("items")

    for row in rows:
        slug = row["title_slug"]
        doc = col.document(slug)
        batch.set(doc, dict(row))

    batch.commit()
    print("Pushed full problem data to Firebase.")



# -----------------------------
# MAIN SYNC
# -----------------------------
def sync():
    print("Initializing DB...")
    init_db()

    full_sync_done = get_meta("full_sync_done") == "true"

    # -----------------------------------
    # FULL SYNC (first run only)
    # -----------------------------------
    if not full_sync_done:
        print("Running full submission sync...")

        all_subs = fetch_all_submissions()
        unique_slugs = compute_unique_solved(all_subs)

        # Mark all unique problems as solved
        for slug in unique_slugs:
            save_problem(slug, "true")

        total_unique = len(unique_slugs)
        set_meta("total_unique_solved", total_unique)
        set_meta("full_sync_done", "true")

        # NEW: compute solved this week
        update_solved_week(all_subs)

        print(f"Full sync complete. Total unique solved: {total_unique}")

    else:
        print("Full sync already done. Using recent submissions...")

    # -----------------------------------
    # RECENT SUBMISSIONS
    # -----------------------------------
    print("Fetching recent submissions...")
    recent = fetch_recent(USERNAME)
    print(f"Found {len(recent)} recent submissions.")

    known_slugs = get_known_slugs()
    current_total = int(get_meta("total_unique_solved") or 0)

    # -----------------------------------
    # Identify NEW unique solves
    # -----------------------------------
    new_slugs = {
        entry["titleSlug"]
        for entry in recent
        if entry.get("statusDisplay") == "Accepted"
    } - known_slugs

    if new_slugs:
        current_total += len(new_slugs)
        set_meta("total_unique_solved", current_total)

        for slug in new_slugs:
            save_problem(slug, "true")

        print(f"New unique problems solved: {new_slugs}")
        print(f"Updated total unique problems solved: {current_total}")
    else:
        print("No new unique problems solved.")

    for entry in recent:
        slug = entry["titleSlug"]

        if slug not in new_slugs:
            print(f"Skipping {slug}, already saved.")
            continue

        print(f"Fetching details for NEW slug {slug}...")

        rest_data = extract_submission(slug, entry)
        if rest_data is None:
            continue

        submission_id = rest_data["id"]

        full = {
            **rest_data,
            **scrape_code_and_percentiles(submission_id)
        }

        save_submission_with_retry(full)
        print(f"Saved {slug}.")


    # -----------------------------------
    # NEW: recompute solved this week
    # -----------------------------------
    all_subs = fetch_all_submissions()
    solved_week = update_solved_week(all_subs)

    # -----------------------------------
    # NEW: push everything to Firebase
    # -----------------------------------
    push_stats_to_firebase(current_total, solved_week)
    push_recent_to_firebase(recent)
    push_problems_to_firebase()

    print("Firebase sync complete.")
    print("Sync complete.")


    print("Sync complete.")


if __name__ == "__main__":
    sync()