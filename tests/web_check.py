"""Exercise the public dashboard with synthetic posts; no LinkedIn connection."""
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
now=datetime.now(timezone.utc)
posts=[{'author':'Fixture Recruiter','text':'We are hiring a Python developer. Remote in Dubai.','sectors':['Technology'],'published_earliest':(now-timedelta(hours=3)).isoformat(),'published_latest':(now-timedelta(hours=2)).isoformat(),'collected_at':now.isoformat(),'url':'https://www.linkedin.com/posts/fixture'},
       {'author':'Fixture Hiring Manager','text':'Hiring a nurse in London.','sectors':['Healthcare'],'published_earliest':(now-timedelta(days=3)).isoformat(),'published_latest':(now-timedelta(days=2)).isoformat(),'collected_at':now.isoformat(),'url':'https://www.linkedin.com/posts/fixture2'}]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        channel=os.environ.get('TEST_BROWSER_CHANNEL')
        browser=p.chromium.launch(headless=True,**({'channel':channel} if channel else {}))
        page=browser.new_page(viewport={'width':1280,'height':1000})
        page.route('**/data.json',lambda route:route.fulfill(content_type='application/json',body=json.dumps({'posts':posts,'status':'success','last_success':now.isoformat(),'repository':'Khanmi1973/linkedin-job-radar'})))
        page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='domcontentloaded')
        page.wait_for_selector('.card')
        assert page.locator('.card').count()==2
        page.locator('#age').select_option('24')
        assert page.locator('.card').count()==1
        page.locator('#keywords').fill('nurse')
        assert page.locator('.card').count()==0
        page.locator('#reset').click()
        page.locator('#sector').select_option('Healthcare')
        assert page.locator('.card').count()==1
        assert 'nurse' in page.locator('.posttext').inner_text()
        with page.expect_download() as download:
            page.locator('#export').click()
        assert download.value.suggested_filename=='linkedin-hiring-posts.csv'
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#reset').click()
        page.locator('#keywords').fill('C++')
        assert page.locator('.card').count()==0
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print('PASS: dashboard rendering, age/keyword/sector filters, CSV download and mobile layout (synthetic fixtures)')
