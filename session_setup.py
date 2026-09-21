"""Create a session secret locally. Never print or commit the session."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description='Sign in locally and prepare the GitHub Actions LinkedIn session secret.')
    parser.add_argument('--upload', metavar='OWNER/REPO', help='Send the secret using an already authenticated GitHub CLI')
    parser.add_argument('--channel', choices=['chrome', 'msedge'], help='Use installed Chrome or Edge instead of bundled Chromium')
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, **({'channel': args.channel} if args.channel else {}))
        context = browser.new_context(locale='en-US')
        page = context.new_page()
        page.goto('https://www.linkedin.com/login')
        input('Sign in in the browser and finish any verification. Then press Enter here. ')
        state = context.storage_state()
        state = {'cookies': [c for c in state['cookies'] if c['domain'].lstrip('.') == 'linkedin.com' or c['domain'].endswith('.linkedin.com')], 'origins': []}
        if not any(c['name'] == 'li_at' and c['value'] for c in state['cookies']):
            browser.close()
            raise SystemExit('No signed-in LinkedIn cookie found. Sign-in was not completed; no secret saved.')
        payload = json.dumps(state)
        if len(payload.encode()) >= 48000:
            raise SystemExit('Session exceeds the GitHub secret size limit; no secret saved.')
        directory = Path(__file__).parent / '.auth'
        directory.mkdir(mode=0o700, exist_ok=True)
        target = directory / 'linkedin-session.json'
        target.write_text(payload, encoding='utf-8')
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        browser.close()
    if args.upload:
        result = subprocess.run(['gh', 'secret', 'set', 'LINKEDIN_STORAGE_STATE', '--repo', args.upload], input=payload, text=True, capture_output=True)
        if result.returncode:
            raise SystemExit('Secret upload failed. Check gh authentication/repository access. The local .auth/linkedin-session.json file is available for manual setup.')
        print('LINKEDIN_STORAGE_STATE uploaded to GitHub Actions secrets. You can run the Scan posts workflow now.')
    else:
        print('Session saved privately to .auth/linkedin-session.json. Add its contents as the repository Actions secret LINKEDIN_STORAGE_STATE. Do not commit, share, or paste it into chat.')

if __name__ == '__main__':
    main()
