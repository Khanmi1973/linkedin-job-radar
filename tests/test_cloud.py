import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloud_scan

NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)

class CloudTests(unittest.TestCase):
    def test_normalization_does_not_leak_extra_fields(self):
        raw = {'text': 'Hiring Python developer', 'age': '2h', 'url': 'https://www.linkedin.com/posts/example', 'cookies': 'SECRET', 'author_type': 'person'}
        post = cloud_scan.normalized(raw, NOW)
        self.assertNotIn('cookies', post)
        self.assertEqual(post['published_earliest'], (NOW-timedelta(hours=3)).isoformat())
        self.assertIn('Technology', post['sectors'])

    def test_dedup_retention(self):
        raw = {'text': 'Hiring Python developer', 'age': '2h', 'url': 'https://www.linkedin.com/posts/example'}
        fresh = cloud_scan.normalized(raw, NOW)
        old = dict(fresh, first_seen=(NOW-timedelta(days=2)).isoformat())
        ancient = dict(old, id='old', published_latest=(NOW-timedelta(days=40)).isoformat())
        result = cloud_scan.merge_posts([old, ancient], [fresh], NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['first_seen'], old['first_seen'])

    def test_missing_secret_preserves_previous_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'site').mkdir()
            (root/'config.json').write_text(json.dumps({'repository':'owner/repo'}))
            previous = {'posts':[{'id':'retained'}], 'last_success':NOW.isoformat()}
            (root/'site/data.json').write_text(json.dumps(previous))
            with patch.object(cloud_scan,'ROOT',root), patch.dict(os.environ,{},clear=True), patch.object(sys,'argv',['cloud_scan.py']):
                self.assertEqual(cloud_scan.main(),1)
            current=json.loads((root/'site/data.json').read_text())
            self.assertEqual(current['posts'],previous['posts'])
            self.assertEqual(current['last_success'],previous['last_success'])
            self.assertEqual(current['status'],'missing_session_secret')

    def test_errors_do_not_expose_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config.json').write_text(json.dumps({'repository':'owner/repo'}))
            with patch.object(cloud_scan,'ROOT',root), patch.dict(os.environ,{'LINKEDIN_STORAGE_STATE':json.dumps({'cookies':[{'name':'li_at','value':'SECRET'}]})}), patch.object(sys,'argv',['cloud_scan.py']), patch.object(cloud_scan,'collect',side_effect=Exception('SECRET')):
                self.assertEqual(cloud_scan.main(),1)
            output=(root/'site/data.json').read_text()
            self.assertNotIn('SECRET',output)
            self.assertIn('scan_failed',output)

if __name__ == '__main__':
    unittest.main()
