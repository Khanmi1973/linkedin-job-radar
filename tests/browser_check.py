"""Synthetic browser extraction test; does not access LinkedIn."""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright

extract = Path(__file__).resolve().parents[1].joinpath('extract.js').read_text(encoding='utf-8')
with sync_playwright() as p:
    channel = os.environ.get('TEST_BROWSER_CHANNEL')
    browser = p.chromium.launch(headless=True, **({'channel': channel} if channel else {}))
    page = browser.new_page()
    page.set_content('''
      <div class="feed-shared-update-v2" data-urn="urn:li:activity:123456789">
        <div class="update-components-actor">
          <a href="https://www.linkedin.com/in/example/">
            <span class="update-components-actor__name"><span class="visually-hidden">Example Recruiter</span></span>
          </a>
          <span class="update-components-actor__sub-description">2h • Visible to anyone</span>
        </div>
        <div class="update-components-text">We are hiring a Python developer. Remote.</div>
      </div>
      <div class="feed-shared-update-v2" data-urn="urn:li:activity:234567890">
        <div class="update-components-actor">
          <a href="https://www.linkedin.com/company/example/"><span class="update-components-actor__name">Example Company</span></a>
          <span class="update-components-actor__sub-description">1d</span>
        </div>
        <div class="update-components-text">Hiring an accountant.</div>
      </div>
      <div class="feed-shared-update-v2">Not a post</div>
    ''')
    result = page.evaluate(extract)
    assert len(result) == 2, result
    assert result[0]['author'] == 'Example Recruiter', result
    assert result[0]['author_type'] == 'person', result
    assert result[0]['age'] == '2h', result
    assert result[0]['url'].endswith('123456789/'), result
    assert result[1]['author_type'] == 'company', result
    assert result[0]['public_visibility'] is True, result
    assert result[1]['public_visibility'] is False, result
    browser.close()
print('PASS: browser extraction, author types, age and permalink (synthetic fixtures)')
