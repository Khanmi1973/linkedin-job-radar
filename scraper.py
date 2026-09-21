"""Single browser-owner thread; no cookies or passwords are exported."""
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

EXTRACT = Path(__file__).with_name('extract.js').read_text(encoding='utf-8')

class BrowserWorker(threading.Thread):
    def __init__(self, events, data_dir):
        super().__init__(daemon=True)
        self.events, self.data_dir = events, data_dir
        self.commands = queue.Queue()
        self.cancel = threading.Event()
        self.closing = threading.Event()

    def status(self, message):
        self.events.put(('status', message))

    def run(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.events.put(('error', 'Playwright is missing. Close the app and run Setup.cmd first.'))
            return
        context = None
        with sync_playwright() as playwright:
            try:
                while not self.closing.is_set():
                    try:
                        command, payload = self.commands.get(timeout=.2)
                    except queue.Empty:
                        if context and context.pages:
                            try:
                                context.pages[0].wait_for_timeout(100)
                            except Exception:
                                context = None
                        continue
                    try:
                        if context is None or not context.pages:
                            if context:
                                context.close()
                            context = playwright.chromium.launch_persistent_context(
                                str(self.data_dir / 'browser-profile'), headless=False,
                                viewport={'width': 1280, 'height': 850})
                            context.set_default_timeout(8000)
                        page = context.pages[0]
                        if command == 'login':
                            page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded', timeout=45000)
                            self.status('Sign in in the browser, then return here and click Find posts.')
                        elif command == 'search':
                            filters, max_scrolls = payload
                            self.collect(page, filters, max_scrolls)
                    except Exception as error:
                        self.events.put(('error', str(error)))
                    finally:
                        self.events.put(('done', None))
            finally:
                if context:
                    context.close()

    def collect(self, page, filters, max_scrolls):
        self.status('Opening LinkedIn post search…')
        response = page.goto(filters.search_url(), wait_until='domcontentloaded', timeout=45000)
        if response and response.status in (403, 429):
            raise RuntimeError('LinkedIn restricted this request. Collection stopped; try normal browsing instead.')
        page.wait_for_timeout(2500)
        seen, stale, total = set(), 0, 0
        for step in range(max_scrolls + 1):
            if self.cancel.is_set() or self.closing.is_set():
                self.status(f'Stopped. Collected {total} unique posts.')
                return
            if any(path in page.url for path in ('/login', '/checkpoint', '/authwall', '/challenge')):
                raise RuntimeError('LinkedIn needs sign-in or verification. Complete it yourself in the browser, then click Find posts again.')
            # Expand commentary only; never click Connect, Like, Apply, or Send.
            buttons = page.locator('button.feed-shared-inline-show-more-text__see-more-less-toggle, button.update-components-text__see-more-less-toggle')
            for index in range(min(buttons.count(), 20)):
                if self.cancel.is_set():
                    break
                try:
                    if buttons.nth(index).is_visible():
                        buttons.nth(index).click(timeout=800)
                except Exception:
                    pass
            raw = page.evaluate(EXTRACT)
            new = []
            for post in raw:
                if post['id'] not in seen:
                    seen.add(post['id'])
                    post['collected_at'] = datetime.now(timezone.utc).isoformat()
                    new.append(post)
            total += len(new)
            if new:
                self.events.put(('posts', new))
            stale = stale + 1 if not new else 0
            self.status(f'Collected {total} posts • scroll {step}/{max_scrolls} • filters applied in the app')
            if stale >= 3 or step == max_scrolls:
                break
            page.evaluate('window.scrollBy(0, Math.max(700, window.innerHeight * 0.85))')
            for _ in range(12):
                if self.cancel.is_set() or self.closing.is_set():
                    break
                page.wait_for_timeout(250)
        self.status(f'Finished: {total} unique posts collected.' if total else
                    'No readable posts found. Check the browser: sign in, broaden the search, or check for a changed LinkedIn layout.')
