"""Open a normal Edge window, attaching automation only after manual login."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
import socket
import subprocess

PROFILE_ROOT = Path(__file__).resolve().parents[1] / "playwright_profile"


def edge_executable():
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        root = os.environ.get(variable)
        if root:
            candidate = Path(root) / "Microsoft/Edge/Application/msedge.exe"
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError("Microsoft Edge is required for sync. Install Edge and rerun sync.cmd.")


def existing_port(profile):
    """Find only the browser process belonging to this tracker's profile."""
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name = 'msedge.exe'\" | "
        "Select-Object -ExpandProperty CommandLine | ConvertTo-Json -Compress",
    ], capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("Could not check the tracker browser. Close its Edge window and rerun sync.cmd.")
    commands = json.loads(result.stdout or "null") or []
    if isinstance(commands, str):
        commands = [commands]
    for command in commands:
        if not command or "--type=" in command:
            continue
        directory = re.search(r'--user-data-dir=(?:"([^"]+)"|(\S+))', command)
        if not directory:
            continue
        if Path(directory.group(1) or directory.group(2)).resolve() != profile.resolve():
            continue
        port = re.search(r"--remote-debugging-port=(\d+)", command)
        if not port:
            raise RuntimeError("The tracker Edge window has no sync connection. Close that window and rerun sync.cmd.")
        return int(port.group(1))
    return None


def wait_for_browser(port, timeout=30):
    # connect_over_cdp fails immediately if Edge hasn't opened its port yet.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener.open(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                if json.load(response).get("webSocketDebuggerUrl"):
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError("The tracker Edge window is not ready. Keep it open during sync. If it is already open, close that tracker window and rerun sync.cmd.")


def launch_browser(playwright):
    profile = PROFILE_ROOT / "manual-edge"
    port = existing_port(profile)
    if port is None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        subprocess.Popen([
            edge_executable(),
            f"--user-data-dir={profile}",
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "https://leetcode.com/",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Reusing the existing tracker Edge window.")
    wait_for_browser(port)
    input("In the Edge window, sign in to LeetCode if needed. Leave it open, then press Enter here to sync: ")
    wait_for_browser(port)
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=30000)
    return browser.contexts[0]


def close_browser(context):
    # Closing a context attached over CDP only disconnects it. Explicitly close
    # our dedicated browser so the next run can use a fresh debugging endpoint.
    try:
        context.browser.new_browser_cdp_session().send("Browser.close")
    except Exception:
        # A closed window must not hide the original sync error.
        print("Tracker browser was already closed or disconnected.")
