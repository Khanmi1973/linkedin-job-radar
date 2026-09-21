# LinkedIn Job Post Finder

**GitHub-hosted version:** see [GITHUB-SETUP.md](GITHUB-SETUP.md) for the mobile dashboard, twice-daily GitHub Actions scans, manual scans, and signed-in session setup. The desktop app below remains available as an optional local tool.

A standalone Python desktop application for finding hiring announcements in **member posts**, rather than LinkedIn's Jobs listings. No paid API key is required.

## Start on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ with **Add Python to PATH** enabled (the standard installer includes Tkinter).
2. Extract the complete ZIP to a folder.
3. Double-click **Setup.cmd** once. This installs Playwright and its Chromium browser in an isolated Python environment.
4. Double-click **Start.cmd**.
5. Click **Open browser / Sign in**. Sign in to LinkedIn yourself in the browser that opens, completing verification if requested.
6. Return to the app, choose filters, and click **Find posts**. Keep the browser open while collecting.
7. Select a result to read it, double-click to open its LinkedIn URL, or **Export CSV**.

Your password is entered directly on LinkedIn. The app uses a separate browser profile; it does not read another browser's cookies. Search can take roughly 30–60 seconds for ten scrolls. Stop interrupts collection after the current operation; navigation may take up to 45 seconds to time out. Closing the app waits for the browser worker to close cleanly.

## Filters

- **Keywords:** comma-separated terms/phrases, with Any or All matching. Example: `Python, backend, Django`.
- **Sector:** a transparent keyword heuristic applied to post text, not a verified author-industry classification. Choose Custom sector to supply your own comma-separated terms. Presets are in `core.py`.
- **Post age:** last 24 hours, 3 days, 7 days, 30 days, or any time. LinkedIn's search date filter is requested and the app also filters locally. Search URL parameters are undocumented and may change; inspect the browser filters if needed.
- **Location / remote:** any comma-separated phrase in post text; this is not geolocation. Example: `Pakistan, remote`.
- **Exclude:** reject posts containing any listed term or phrase.
- **People only:** requires a recognized `/in/` author profile link. Company and unknown author types are excluded; uncheck to include them.
- **Require hiring language:** heuristic detection of phrases such as hiring, vacancy, join our team, apply now. May miss unusual wording or include discussion of hiring; review posts before applying.
- **Unknown ages:** excluded from age-limited searches by default. Explicitly opt in to include them.
- **Maximum scrolls:** 0 collects the first loaded results; 10 is the default; 50 is the maximum. Collection also stops after three consecutive passes without new posts.

Post ages such as `23h` are rounded intervals. The app conservatively excludes any interval that could exceed your limit (`1d` is not definitely within 24 hours). Exact ISO timestamps are used when the page exposes them. Saved results age relative to collection time. English relative-time labels are supported; other languages can produce unknown ages. LinkedIn may truncate post text or show repost metadata; the app cannot guarantee the original author's publication time for reposts.

**Apply filters to saved results** operates without another search. Changing search terms cannot retrieve posts that were never collected: use Find posts for a new collection. Results accumulate across searches, with duplicate post links merged. CSV includes author, profile URL, author type, age label, text, post URL, and collection timestamp. Cells are protected against common spreadsheet formula injection.

## Local data

Results and settings: `%LOCALAPPDATA%\LinkedInJobFinder\results.json`

Separate signed-in browser profile: `%LOCALAPPDATA%\LinkedInJobFinder\browser-profile`

Treat the browser profile as sensitive. Do not share it. Use Clear saved results to remove collected posts. To remove the saved sign-in, close the app and remove the browser-profile folder. No telemetry or external data upload is implemented.

## Limits and troubleshooting

LinkedIn prohibits scraping/automation in its terms and may restrict accounts: https://www.linkedin.com/help/linkedin/answer/a1341387 . This app does not bypass sign-in, CAPTCHAs, access controls, or request restrictions, and makes no guarantee of account safety or complete search coverage.

- **No readable posts:** check the visible browser for sign-in, verification, empty search results, or a changed LinkedIn layout. Broaden keywords and try a larger age window. DOM selectors live in `extract.js` and may require maintenance when LinkedIn changes its markup.
- **Collected posts but no matches:** broaden local filters. Unknown author types and ages can be excluded by the defaults. Sector and location match the post body only.
- **Missing browser executable:** rerun Setup.cmd.
- **Browser profile in use:** close the other app instance and its browser before retrying.
- **Access challenge or restriction:** collection stops; handle verification manually or use normal LinkedIn browsing. There is no automatic retry or evasion.

## Other operating systems / development

Create a virtual environment, install `requirements.txt`, run `python -m playwright install chromium`, then `python app.py`. Linux may need system Tkinter and Playwright browser dependencies. The Windows launchers are convenience wrappers.

Run deterministic checks with `python -m unittest discover -s tests -v`. Run browser extraction checks with `python tests/browser_check.py` after browser installation. Fixtures are synthetic; live LinkedIn collection requires your own signed-in session and is not verified by these tests.

Official references: https://playwright.dev/python/docs/library and https://www.linkedin.com/help/linkedin/answer/a526104 .
