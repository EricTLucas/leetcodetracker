import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sync"))
from client import LeetCodeClient, compute_unique_solved
from sync import pending_submissions
from scraper import normalize_code, with_unit


def submission(id=1, slug="two-sum", status="Accepted", timestamp="100"):
    return {"id": id, "titleSlug": slug, "statusDisplay": status, "timestamp": timestamp}


class SyncTests(unittest.TestCase):
    def test_missing_details_retry_even_for_previously_known_problem(self):
        row = submission()
        self.assertEqual(list(pending_submissions([row], {})), [row])
        self.assertEqual(list(pending_submissions([row], {"two-sum": {"id": 1}})), [row])

    def test_complete_saved_solution_skips_but_newer_solution_updates(self):
        old = {"id": "1", **{k: "value" for k in
               ("code", "runtime", "memory", "runtime_percentile", "memory_percentile")}}
        self.assertEqual(list(pending_submissions([submission()], {"two-sum": old})), [])
        newer = submission(2, timestamp="200")
        self.assertEqual(list(pending_submissions([submission(), newer], {"two-sum": old})), [newer])

    def test_totals_use_all_unique_accepted_and_ignore_failed_attempts(self):
        rows = [submission(), submission(2), submission(3, "other"), submission(4, "failed", "Wrong Answer")]
        self.assertEqual(compute_unique_solved(rows), {"two-sum", "other"})
        self.assertEqual(len(list(pending_submissions(rows, {}))), 2)

    def test_history_pagination_and_incomplete_response(self):
        client = LeetCodeClient(Mock())
        client.query = Mock(side_effect=[
            {"submissionList": {"submissions": [submission()], "hasNext": True}},
            {"submissionList": {"submissions": [submission(2)], "hasNext": False}}])
        self.assertEqual(len(client.fetch_all_submissions()), 2)
        client.query = Mock(return_value={"submissionList": {"submissions": [], "hasNext": True}})
        with self.assertRaises(RuntimeError):
            client.fetch_all_submissions()
        client.query = Mock(return_value={"submissionList": None})
        with self.assertRaises(RuntimeError):
            client.fetch_all_submissions()

    def test_expired_login_prompts_then_rechecks_identity(self):
        client = LeetCodeClient(Mock())
        client.query = Mock(side_effect=[{"userStatus": {"isSignedIn": False}},
            {"userStatus": {"isSignedIn": True, "username": "EricLucas"}}])
        with patch("builtins.input") as prompt:
            client.ensure_login(Mock(), "EricLucas")
        prompt.assert_called_once()

    def test_wrong_account_stops_sync(self):
        client = LeetCodeClient(Mock())
        client.query = Mock(return_value={"userStatus": {"isSignedIn": True, "username": "someone-else"}})
        with patch("builtins.input"), self.assertRaises(RuntimeError):
            client.ensure_login(Mock(), "EricLucas")

    def test_api_errors_are_not_silently_empty_history(self):
        context = Mock()
        context.cookies.return_value = [{"name": "csrftoken", "value": "fresh"}]
        response = context.request.post.return_value
        response.ok = True
        response.json.return_value = {"errors": [{"message": "unauthorized"}], "data": None}
        with self.assertRaises(RuntimeError):
            LeetCodeClient(context).query("query {}")
        self.assertEqual(context.request.post.call_args.kwargs["headers"]["X-CSRFToken"], "fresh")

    def run_mock_sync(self, fail=False):
        import types
        from sync import sync
        context = Mock()
        context.pages = [Mock()]
        playwright = Mock()
        playwright.chromium.launch_persistent_context.return_value = context
        manager = Mock()
        manager.__enter__ = Mock(return_value=playwright)
        manager.__exit__ = Mock(return_value=False)
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = Mock(return_value=manager)
        fake_db = Mock()
        fake_db.get_saved_submissions.return_value = {}
        row = {**submission(), "lang": "python3", "title": "Two Sum"}
        details = {"id": 1, "code": "pass", "runtime": "1ms", "memory": "1MB",
                   "runtime_percentile": "50%", "memory_percentile": "50%"}
        with patch.dict(sys.modules, {"playwright.sync_api": api, "db": fake_db}), \
             patch("sync.launch_browser", return_value=context), \
             patch("sync.LeetCodeClient") as client, \
             patch("sync.scrape_code_and_percentiles") as scrape:
            client.return_value.fetch_all_submissions.return_value = [row]
            if fail:
                scrape.side_effect = RuntimeError("download failed")
                with self.assertRaises(RuntimeError):
                    sync()
            else:
                scrape.return_value = details
                sync()
        context.browser.new_browser_cdp_session.return_value.send.assert_called_once_with("Browser.close")
        return fake_db

    def test_failed_scrape_does_not_mark_problem_or_publish_success(self):
        db = self.run_mock_sync(fail=True)
        db.save_problem.assert_not_called()
        db.push_stats_to_firebase.assert_not_called()

    def test_first_sync_publishes_correct_total_and_matching_details(self):
        db = self.run_mock_sync()
        db.push_stats_to_firebase.assert_called_once_with(1, 0)
        self.assertEqual(db.save_submission.call_args.args[0]["id"], 1)
        self.assertIsInstance(db.save_submission.call_args.args[0]["timestamp"], int)
        self.assertEqual(db.save_submission.call_args.args[0]["title_slug"], "two-sum")

    def test_browser_connects_only_after_manual_login(self):
        from browser import launch_browser
        playwright = Mock()
        context = Mock()
        playwright.chromium.connect_over_cdp.return_value.contexts = [context]
        def confirm_login(*args):
            playwright.chromium.connect_over_cdp.assert_not_called()
        with patch("browser.edge_executable", return_value="msedge.exe"), \
             patch("browser.subprocess.Popen") as launch, \
             patch("browser.existing_port", return_value=None), \
             patch("browser.wait_for_browser"), \
             patch("builtins.input", side_effect=confirm_login):
            self.assertIs(launch_browser(playwright), context)
        args = launch.call_args.args[0]
        self.assertIn("--remote-debugging-address=127.0.0.1", args)
        self.assertFalse(any("enable-automation" in arg or "AutomationControlled" in arg for arg in args))
        playwright.chromium.connect_over_cdp.assert_called_once()

    def test_existing_tracker_browser_reuses_its_actual_port(self):
        from browser import launch_browser
        playwright = Mock()
        playwright.chromium.connect_over_cdp.return_value.contexts = [Mock()]
        with patch("browser.existing_port", return_value=64280), \
             patch("browser.wait_for_browser") as ready, \
             patch("browser.subprocess.Popen") as launch, patch("builtins.input"):
            launch_browser(playwright)
        launch.assert_not_called()
        self.assertEqual(ready.call_count, 2)
        playwright.chromium.connect_over_cdp.assert_called_once_with("http://127.0.0.1:64280", timeout=30000)

    def test_process_discovery_ignores_other_profiles_and_renderers(self):
        import json
        from browser import existing_port, PROFILE_ROOT
        profile = PROFILE_ROOT / "manual-edge"
        commands = [
            'msedge.exe --user-data-dir="C:/unrelated" --remote-debugging-port=1111',
            f'msedge.exe --type=renderer --user-data-dir="{profile}" --remote-debugging-port=2222',
            f'msedge.exe --user-data-dir="{profile}" --remote-debugging-port=3333',
        ]
        with patch("browser.subprocess.run", return_value=Mock(returncode=0, stdout=json.dumps(commands))):
            self.assertEqual(existing_port(profile), 3333)

    def test_browser_readiness_retries_a_slow_start(self):
        from browser import wait_for_browser
        import io
        opener = Mock()
        opener.open.side_effect = [OSError("refused"), io.StringIO('{"webSocketDebuggerUrl":"ws://127.0.0.1/devtools/browser/test"}')]
        with patch("browser.urllib.request.build_opener", return_value=opener), patch("browser.time.sleep"):
            wait_for_browser(1234)
        self.assertEqual(opener.open.call_count, 2)

    def test_closed_browser_cleanup_does_not_mask_sync_error(self):
        from browser import close_browser
        context = Mock()
        context.browser.new_browser_cdp_session.side_effect = RuntimeError("closed")
        close_browser(context)

    def test_code_and_units_are_preserved(self):
        raw = '123 + 456\nprint("\\n")'
        self.assertEqual(normalize_code(raw), raw)
        self.assertEqual(with_unit("12 ms", "ms"), "12 ms")
        self.assertEqual(with_unit("12", "ms"), "12ms")


if __name__ == "__main__":
    unittest.main()
