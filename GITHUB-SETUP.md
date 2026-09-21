# GitHub Pages + twice-daily LinkedIn scans

The cloud version uses Python + Playwright in GitHub Actions. GitHub Pages serves only the dashboard in `site/`. Your computer can be off during scheduled scans.

## Deploy

1. Create a repository named `linkedin-job-radar` under your GitHub account. Upload the project source, including `.github/workflows/scan.yml`. Do **not** upload `.venv`, `__pycache__`, `.auth`, a browser profile, or any session file.
2. If the repository name differs from `Khanmi1973/linkedin-job-radar`, update `repository` in `config.json`.
3. In repository **Settings → Pages → Build and deployment**, choose **GitHub Actions** as the source.
4. Under **Actions → Scan posts → Run workflow**, enable **Publish dashboard without accessing LinkedIn** for the first deployment. The public URL will be `https://<username>.github.io/<repository>/`.
5. Set up the LinkedIn session below, then run the workflow with that checkbox **off** for a live scan.

## Sign in locally once, refresh when requested

Run Setup.cmd first, then open a terminal in this folder:

```powershell
.venv\Scripts\python.exe session_setup.py
```

If the Chromium download is unavailable but Edge is installed:

```powershell
.venv\Scripts\python.exe session_setup.py --channel msedge
```

Sign in yourself in the browser and complete any verification. Return to the terminal and press Enter. The helper checks for a signed-in cookie and writes `.auth/linkedin-session.json`, which is gitignored. It never prints the secret.

In your repository, go to **Settings → Secrets and variables → Actions → New repository secret**. Name it **LINKEDIN_STORAGE_STATE** and paste the contents of that local JSON file as the secret value. Do not paste the contents into chat or put them in a source file.

If you use an authenticated GitHub CLI, the helper can upload it directly without printing it:

```powershell
.venv\Scripts\python.exe session_setup.py --upload Khanmi1973/linkedin-job-radar
```

This sends your LinkedIn session to GitHub's encrypted Actions-secret storage so the runner can access LinkedIn as you. The workflow passes it only to the collector and publishes only `site/`. Session data is never included in the cache, dashboard, artifact, or logs. The session grants access to your account: restrict who can edit workflows and remove the secret when you stop using the scanner.

GitHub-hosted IP addresses can be blocked or challenged by LinkedIn even with a valid session. Automated scans are not guaranteed. The collector stops on sign-in/verification/access restrictions; it does not bypass them. A fresh local session might still not work from GitHub. A self-hosted runner is a possible later deployment option, but requires a machine that stays online.

## Scheduled and manual runs

- Scheduled: **08:17 and 20:17 Asia/Karachi** (**03:17 and 15:17 UTC**), using `17 3,15 * * *`.
- On demand: dashboard **Run a scan** opens the workflow; click **Run workflow** while signed in to GitHub. Keep **initialize_only** off. There is no token in the public webpage and anonymous visitors cannot start scans.
- GitHub schedules run on a best-effort basis and may be delayed. Public-repository schedules can be disabled after 60 days without repository activity; re-enable the workflow if needed.
- Only one run at a time; 25-minute overall timeout; bounded query/scroll counts.
- Source pushes publish the interface without using your LinkedIn session. A scheduled or manual scan collects data.

Edit `config.json` to change collection queries, the scan age, and scroll limits. Dashboard keyword/sector/age filters apply immediately to collected posts; they do not modify the scheduled query configuration. Defaults collect member hiring posts from the last seven days using three searches. Sector detection and hiring classification are text heuristics.

## Results, privacy, and failure behavior

The Pages dashboard is **public**. The collector defaults to publishing only member posts with a recognized English public-visibility label. Posts without a confirmed label are excluded, including when the page markup changes. Do not turn `public_posts_only` off for a public site unless you have separately reviewed publication rights and scope.

Relative publication labels are approximate. Age filtering uses the earliest plausible date, and unknown dates are excluded unless the dashboard user opts in. Reposts may expose reshared timing; original publication time is not guaranteed. Text may be truncated when LinkedIn does not expose an expandable body.

Results are merged by post URL, capped at 1,000 posts, and retained for 30 days by default. The previous dataset lives in GitHub Actions cache (only public-post output, never session cookies). Cache retention/eviction is controlled by GitHub; this is not archival storage. If evicted, the next successful scan rebuilds from its current searches. Export CSV for durable personal copies.

A scan error keeps the restored previous results, updates the dashboard with the error category, and marks the workflow failed. A browser-install, test, or deployment failure happens before publication and leaves the last deployed site unchanged; check Actions for those failures. Site deployment success does not prove that LinkedIn collection succeeded.

## Tests

```powershell
python -m unittest discover -s tests -v
python tests/browser_check.py
node --check site/app.js
```

Browser fixtures are synthetic. A real end-to-end check requires your session and a successful live GitHub scan.

References: [GitHub workflow schedules/manual triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), [LinkedIn automation restrictions](https://www.linkedin.com/help/linkedin/answer/a1341387).
