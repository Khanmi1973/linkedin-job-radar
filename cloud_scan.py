"""Bounded GitHub Actions collector. Authentication data never enters published output."""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core import Filters, SECTORS, age_bounds

ROOT = Path(__file__).parent

def normalized(post, now):
    low, high = age_bounds(post.get('age', ''), now)
    return {key: post.get(key, '') for key in ('author', 'author_url', 'author_type', 'text', 'url', 'age')} | {
        'id': post['url'], 'collected_at': now.isoformat(),
        'published_earliest': (now-timedelta(hours=high)).isoformat() if high is not None else None,
        'published_latest': (now-timedelta(hours=low)).isoformat() if low is not None else None,
        'sectors': [sector for sector in SECTORS if sector not in ('Any sector', 'Custom sector') and
                    Filters(sector=sector, age='Any time', hiring_only=False, people_only=False).matches(post, now)]
    }

def merge_posts(old, new, now, retention=30, maximum=1000):
    merged = {p['id']: p for p in old if p.get('id')}
    for post in new:
        previous = merged.get(post['id'])
        if previous:
            post['first_seen'] = previous.get('first_seen', previous.get('collected_at'))
        else:
            post['first_seen'] = post['collected_at']
        merged[post['id']] = post
    cutoff = now-timedelta(days=retention)
    def recent(post):
        try:
            return datetime.fromisoformat(post.get('published_latest') or post['first_seen']) >= cutoff
        except (ValueError, TypeError, KeyError):
            return False
    return sorted((p for p in merged.values() if recent(p)), key=lambda p: p.get('published_latest') or p['collected_at'], reverse=True)[:maximum]

def collect(config, state):
    from playwright.sync_api import sync_playwright
    posts, readable, excluded = {}, 0, 0
    script = ROOT.joinpath('extract.js').read_text(encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state, locale='en-US', viewport={'width': 1365, 'height': 900})
        page = context.new_page()
        page.set_default_timeout(10000)
        try:
            for query in config['queries'][:10]:
                filters = Filters(keywords=query, age=config['scan_age'], hiring_only=False)
                response = page.goto(filters.search_url(), wait_until='domcontentloaded', timeout=45000)
                if response and response.status in (403, 429):
                    raise RuntimeError('access_restricted')
                page.wait_for_timeout(3000)
                seen, stale = set(), 0
                for step in range(min(30, config['max_scrolls_per_query'])+1):
                    if any(part in page.url for part in ('/login', '/checkpoint', '/challenge', '/authwall')):
                        raise RuntimeError('session_needs_refresh')
                    for button in page.locator('button.feed-shared-inline-show-more-text__see-more-less-toggle, button.update-components-text__see-more-less-toggle').all()[:20]:
                        try:
                            if button.is_visible():
                                button.click(timeout=700)
                        except Exception:
                            pass
                    batch = page.evaluate(script)
                    fresh = 0
                    for post in batch:
                        if post['id'] in seen:
                            continue
                        seen.add(post['id'])
                        readable += 1
                        fresh += 1
                        if config.get('public_posts_only', True) and not post.get('public_visibility'):
                            excluded += 1
                            continue
                        if not post['url'] or not Filters(age=config['scan_age']).matches(post):
                            continue
                        posts[post['url']] = normalized(post, datetime.now(timezone.utc))
                    stale = stale+1 if not fresh else 0
                    if stale >= 3 or step >= config['max_scrolls_per_query']:
                        break
                    page.evaluate('window.scrollBy(0, Math.max(700, window.innerHeight * .85))')
                    page.wait_for_timeout(3000)
                page.wait_for_timeout(1500)
            if not readable:
                raise RuntimeError('no_readable_posts')
            return list(posts.values()), readable, excluded
        finally:
            context.close()
            browser.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initialize', action='store_true', help='Build an honest empty dashboard without a scan')
    args = parser.parse_args()
    config = json.loads(ROOT.joinpath('config.json').read_text(encoding='utf-8'))
    target = ROOT / 'site' / 'data.json'
    old = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {'posts': [], 'last_success': None}
    now = datetime.now(timezone.utc)
    result = dict(old, repository=config['repository'], last_attempt=now.isoformat(), schedule='08:17 and 20:17 Asia/Karachi (03:17 and 15:17 UTC)')
    status = 'not_configured'
    exit_code = 0
    try:
        if args.initialize:
            status = 'awaiting_first_scan'
        elif not os.environ.get('LINKEDIN_STORAGE_STATE'):
            raise RuntimeError('missing_session_secret')
        else:
            try:
                state = json.loads(os.environ['LINKEDIN_STORAGE_STATE'])
                if not isinstance(state.get('cookies'), list) or not any(c.get('name') == 'li_at' for c in state['cookies']):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise RuntimeError('invalid_session_secret') from None
            fresh, readable, excluded = collect(config, state)
            result['posts'] = merge_posts(old['posts'], fresh, now, config['retention_days'], config['max_posts'])
            result.update(last_success=now.isoformat(), found_this_scan=len(fresh), readable_this_scan=readable, excluded_visibility=excluded)
            status = 'success'
    except Exception as error:
        known = {'missing_session_secret', 'invalid_session_secret', 'session_needs_refresh', 'access_restricted', 'no_readable_posts'}
        status = str(error) if str(error) in known else 'scan_failed'
        exit_code = 1
        # Do not log browser exception messages: they can contain session-bearing URLs.
        print(f'Scan stopped: {status}. Previous results retained.', file=sys.stderr)
    result['status'] = status
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Dashboard status: {status}; {len(result["posts"])} retained posts.')
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
