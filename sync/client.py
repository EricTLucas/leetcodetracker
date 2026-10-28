"""LeetCode requests share the interactive browser's current login."""

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

class LeetCodeClient:
    def __init__(self, context):
        self.context = context

    def query(self, query, variables=None):
        cookies = self.context.cookies("https://leetcode.com")
        csrf = next((c["value"] for c in cookies if c["name"] == "csrftoken"), "")
        response = self.context.request.post(
            "https://leetcode.com/graphql/",
            data={"query": query, "variables": variables or {}},
            headers={"Referer": "https://leetcode.com/", "X-CSRFToken": csrf},
            timeout=60000,
        )
        if not response.ok:
            raise RuntimeError(f"LeetCode request failed (HTTP {response.status}). Rerun sync and check sign-in.")
        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError("LeetCode returned a verification page. Complete verification in the browser and rerun.") from exc
        if result.get("errors") or not result.get("data"):
            raise RuntimeError("LeetCode returned an API error; no sync was completed.")
        return result["data"]

    def ensure_login(self, page, username):
        query = "query { userStatus { isSignedIn username } }"
        for attempt in range(2):
            try:
                user = self.query(query).get("userStatus") or {}
                if user.get("isSignedIn") and user.get("username", "").lower() == username.lower():
                    return
            except RuntimeError:
                pass
            if attempt == 0:
                page.goto("https://leetcode.com/accounts/login/", wait_until="domcontentloaded")
                input(f"Sign in as {username} and complete any verification in the browser. Leave it open, then press Enter here: ")
        raise RuntimeError(f"Could not verify login as {username}. Firebase was not updated.")

    def fetch_all_submissions(self):
        submissions = []
        offset = 0
        seen = set()
        while True:
            data = self.query(ALL_SUBMISSIONS_QUERY, {"offset": offset, "limit": 20})
            page = data.get("submissionList")
            if not isinstance(page, dict) or not isinstance(page.get("submissions"), list) or not isinstance(page.get("hasNext"), bool):
                raise RuntimeError("Incomplete submission history; refusing to publish partial totals.")
            rows = page["submissions"]
            ids = {str(row["id"]) for row in rows}
            if (page["hasNext"] and not rows) or seen.intersection(ids):
                raise RuntimeError("Submission pagination stalled; rerun sync.")
            seen.update(ids)
            submissions.extend(rows)
            if not page["hasNext"]:
                return submissions
            offset += len(rows)


def compute_unique_solved(submissions):
    return {s["titleSlug"] for s in submissions if s["statusDisplay"] == "Accepted"}
