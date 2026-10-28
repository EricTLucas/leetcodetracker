# LeetCode tracker

The website reads the existing Firebase collections. To update them on Windows,
run this from the repository folder:

```powershell
.\sync.cmd
```

Requires Python 3.11+ and `firebase-service-account.json` in the repository root.
The command creates a local Python environment and installs dependencies
automatically on first use (internet access required).

Microsoft Edge opens using a dedicated saved profile under `playwright_profile/manual-edge`
in the repository root. Microsoft Edge must be installed on Windows.
Each run opens Edge normally and waits before connecting the sync.
If the session expired, sign in as **EricLucas**, complete any verification,
leave the browser open, and press Enter in the terminal when prompted. No copied
cookie or `.env` update is needed. Do not run two syncs at the same time.

Every run checks the complete submission history, recomputes solved counts, and
saves the latest accepted solution for each problem. Already saved complete
solutions are skipped. Missing details and newer accepted submissions are retried,
including problems missed by earlier runs. The first repaired sync may take longer
while it fills these gaps. If a download fails, existing successful saves remain,
the command exits with an error, and the next run retries unfinished work.
`last_sync` and totals are published only when all details are saved successfully.

The website UI and Firebase collection/field layout are unchanged. Keep the service
account file, browser profile, and `.env` private; they are ignored by Git.

For an existing Python environment with the dependencies and Chromium installed,
`python sync/sync.py` also works from any working directory when given the full
path to the script.

Run the offline regression checks with `python -m unittest discover -s tests`.
