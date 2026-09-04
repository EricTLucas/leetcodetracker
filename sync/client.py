import os
import re
import requests
import time
from dotenv import load_dotenv
from db import toTitle

# Load .env from project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

LEETCODE_COOKIE = os.getenv("LEETCODE_COOKIE")
if not LEETCODE_COOKIE:
    raise RuntimeError("LEETCODE_COOKIE not found in .env")

# Extract csrftoken for CSRF header
match = re.search(r"csrftoken=([^;]+)", LEETCODE_COOKIE)
CSRFTOKEN = match.group(1) if match else ""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://leetcode.com",
    "X-CSRFToken": CSRFTOKEN,
    "Cookie": LEETCODE_COOKIE
}

GRAPHQL_URL = "https://leetcode.com/graphql"
REST_URL = "https://leetcode.com/api/submissions/{slug}/"
DETAIL_URL = "https://leetcode.com/submissions/detail/{id}/"


# -----------------------------
# GraphQL: recent submissions
# -----------------------------
RECENT_SUBMISSIONS_QUERY = """
query recentAcSubmissions($username: String!) {
  recentSubmissionList(username: $username) {
    id
    title
    titleSlug
    statusDisplay
    lang
    timestamp
  }
}
"""

ALL_SUBMISSIONS_QUERY = """
query submissionList($offset: Int!, $limit: Int!) {
  submissionList(offset: $offset, limit: $limit) {
    submissions {
      id
      title
      titleSlug
      statusDisplay
      lang
      timestamp
      runtime
      memory
    }
    hasNext
  }
}
"""

def lc_query(query, variables=None):
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)

    if resp.status_code != 200:
        print("GRAPHQL ERROR:", resp.text)
        resp.raise_for_status()

    return resp.json()["data"]

def fetch_recent(username):
    data = lc_query(RECENT_SUBMISSIONS_QUERY, {"username": username})
    return data["recentSubmissionList"]

def fetch_all_submissions():
    submissions = []
    offset = 0
    limit = 20  # LeetCode max page size

    while True:
        data = lc_query(ALL_SUBMISSIONS_QUERY, {
            "offset": offset,
            "limit": limit
        })
        
        page = data["submissionList"]
        subs = page["submissions"]

        submissions.extend(subs)

        if not page["hasNext"]:
            break

        offset += limit

    return submissions

def compute_unique_solved(submissions):
    slugs = {s["titleSlug"] for s in submissions if s["statusDisplay"] == "Accepted"}
    return slugs


def count_unique_problems():
    subs = fetch_all_submissions()
    slugs = {s["titleSlug"] for s in subs if s["statusDisplay"] == "Accepted"}
    return len(slugs), slugs




# -----------------------------
# REST: old judge submissions
# -----------------------------
def fetch_rest_details(slug):
    url = REST_URL.format(slug=slug)
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code == 403:
        return None  # REST unavailable for this problem

    if resp.status_code != 200:
        print("REST ERROR:", resp.text)
        resp.raise_for_status()

    return resp.json()

def fetch_rest_details_retry(slug, retries=5, delay=1.5):
    url = f"https://leetcode.com/api/submissions/{slug}/"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)

            # Cloudflare challenge returns HTML instead of JSON
            if resp.headers.get("Content-Type", "").startswith("text/html"):
                print(f"REST attempt {attempt}: Cloudflare HTML, retrying...")
                time.sleep(delay)
                continue

            # 403 Forbidden (new judge or transient failure)
            if resp.status_code == 403:
                print(f"REST attempt {attempt}: 403 Forbidden, retrying...")
                time.sleep(delay)
                continue

            # 404 Not Found (transient for some submissions)
            if resp.status_code == 404:
                print(f"REST attempt {attempt}: 404 Not Found, retrying...")
                time.sleep(delay)
                continue

            # 200 OK but empty or malformed JSON
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    print(f"REST attempt {attempt}: invalid JSON, retrying...")
                    time.sleep(delay)
                    continue

                # If JSON is empty or missing expected fields, retry
                if not data or "submissions_dump" not in data:
                    print(f"REST attempt {attempt}: incomplete JSON, retrying...")
                    time.sleep(delay)
                    continue

                # SUCCESS
                return data

        except requests.exceptions.RequestException as e:
            print(f"REST attempt {attempt}: network error {e}, retrying...")
            time.sleep(delay)

    print(f"REST failed after {retries} attempts for slug {slug}")
    return None




# -----------------------------
# Unified extractor
# -----------------------------
def extract_submission(slug, submission_id, recent_entry):
    # Skip non-accepted submissions
    
    if recent_entry["statusDisplay"] != "Accepted":
        print("Not Accepted, skipping REST and Playwright for", slug)   
        return None

    # Try REST first
    rest = fetch_rest_details_retry(slug)
    if rest is not None:
        dump = rest.get("submissions_dump", [])
        accepted = next((s for s in dump if s.get("status_display") == "Accepted"), None)
        if accepted:
            print("REST succeeded for", slug)
            return {
                "id": accepted["id"],
                "title_slug": slug,
                "lang": accepted.get("lang"),
                "timestamp": accepted.get("timestamp"),
                "title": toTitle(slug),
                "status": "Accepted",
                "code": None,
                "runtime": None,
                "memory": None,
                "runtime_percentile": None,
                "memory_percentile": None
            }

    # REST failed → fallback to Playwright
    print("REST failed for", slug)
    return None
