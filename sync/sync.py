from client import fetch_recent, extract_submission, fetch_all_submissions, compute_unique_solved
from db import init_db, get_meta, set_meta, get_known_slugs, save_problem, save_submission, push_recent_to_firebase, push_stats_to_firebase
from scraper import scrape_code_and_percentiles
from utils import compute_solved_last_7_days

USERNAME = "EricLucas"


def update_solved_week(all_subs):
    solved_count, _ = compute_solved_last_7_days(all_subs)
    set_meta("solved_week", solved_count)
    print(f"Solved last 7 days: {solved_count}")
    return solved_count


# -----------------------------
# MAIN SYNC
# -----------------------------
def sync():
    print("Initializing DB...")
    init_db()

    full_sync_done = get_meta("full_sync_done") == "true"

    # FULL SYNC: fetch all submissions and compute unique problems solved only first time
    if not full_sync_done:
        print("Running full submission sync...")

        all_subs = fetch_all_submissions()
        unique_slugs = compute_unique_solved(all_subs)

        for slug in unique_slugs:
            save_problem(slug, "true")

        total_unique = len(unique_slugs)
        set_meta("total_unique_solved", total_unique)
        set_meta("full_sync_done", "true")
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

    if not full_sync_done:
        new_slugs = {
            entry["titleSlug"]
            for entry in recent 
            if entry.get("statusDisplay") == "Accepted"
            }

    if new_slugs:
        if full_sync_done:
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
        
        rest_data = extract_submission(slug, entry["id"], entry)
        if rest_data is None:
            continue

        submission_id = rest_data["id"]

        full = {
            **rest_data,
            **scrape_code_and_percentiles(submission_id)
        }

        
        save_submission(full)
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

    print("Firebase sync complete.")
    print("Sync complete.")


    print("Sync complete.")


if __name__ == "__main__":
    sync()