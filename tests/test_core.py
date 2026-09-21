import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Filters, age_bounds, export_csv, safe_url

NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)

def post(**overrides):
    value = dict(author='Recruiter', author_type='person', text='We are hiring a Python developer. Remote in Pakistan.',
                 age='2h', collected_at=NOW.isoformat(), url='https://www.linkedin.com/feed/update/urn:li:activity:123/')
    value.update(overrides)
    return value

class FilterTests(unittest.TestCase):
    def test_hiring_person(self):
        self.assertTrue(Filters().matches(post(), NOW))
        self.assertFalse(Filters().matches(post(author_type='company'), NOW))
        self.assertFalse(Filters().matches(post(author_type='unknown'), NOW))
        self.assertFalse(Filters().matches(post(text='Looking for a job as a Python developer'), NOW))

    def test_keyword_modes_and_word_boundaries(self):
        self.assertTrue(Filters(keywords='Python, Java').matches(post(), NOW))
        self.assertFalse(Filters(keywords='Python, Java', keyword_mode='All keywords').matches(post(), NOW))
        self.assertFalse(Filters(keywords='IT').matches(post(text='Hiring writer with ambition'), NOW))
        self.assertTrue(Filters(keywords='C++').matches(post(text='Hiring C++ developer'), NOW))

    def test_sector_location_exclusion(self):
        self.assertTrue(Filters(sector='Technology', location='remote').matches(post(), NOW))
        self.assertFalse(Filters(sector='Healthcare').matches(post(), NOW))
        self.assertFalse(Filters(exclude='Python').matches(post(), NOW))
        self.assertTrue(Filters(sector='Custom sector', custom_sector='developer').matches(post(), NOW))

    def test_age_boundaries(self):
        self.assertTrue(Filters().matches(post(age='23h'), NOW))
        self.assertFalse(Filters().matches(post(age='24h'), NOW))
        self.assertFalse(Filters().matches(post(age='1d'), NOW))
        self.assertFalse(Filters().matches(post(age=''), NOW))
        self.assertTrue(Filters(include_unknown_age=True).matches(post(age=''), NOW))
        self.assertFalse(Filters().matches(post(age='23h'), NOW + timedelta(minutes=1)))
        self.assertTrue(Filters(age='Any time').matches(post(age=''), NOW))

    def test_exact_timestamp(self):
        self.assertTrue(Filters().matches(post(age=(NOW-timedelta(hours=23, minutes=59)).isoformat()), NOW))
        self.assertFalse(Filters().matches(post(age=(NOW-timedelta(hours=25)).isoformat()), NOW))
        self.assertEqual(age_bounds('1mo', NOW), (720, 1440))
        self.assertEqual(age_bounds('2 minutes ago', NOW), (2/60, 3/60))

    def test_query_is_posts_and_encoded(self):
        url = Filters(keywords='C++, R&D', age='Last 3 days').search_url()
        self.assertEqual(urlparse(url).path, '/search/results/content/')
        query = parse_qs(urlparse(url).query)
        self.assertIn('"C++" OR "R&D"', query['keywords'][0])
        self.assertEqual(query['datePosted'], ['"past-week"'])

    def test_link_validation(self):
        self.assertTrue(safe_url(post()['url']))
        self.assertFalse(safe_url('https://linkedin.com.attacker.example/path'))
        self.assertFalse(safe_url('javascript:alert(1)'))

    def test_csv_unicode_and_formula(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'results.csv'
            export_csv(path, [post(author='=1+1', text='Hiring — café\nSecond line')])
            value = path.read_text(encoding='utf-8-sig')
            self.assertIn("'=1+1", value)
            self.assertIn('Hiring — café', value)

if __name__ == '__main__':
    unittest.main()
