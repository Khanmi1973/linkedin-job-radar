"""Filtering and export rules, independent of the browser and desktop UI."""
import csv
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse

SECTORS = {
    "Any sector": [],
    "Technology": ["software", "developer", "engineer", "data", "IT", "cybersecurity", "devops", "python"],
    "Finance & Accounting": ["finance", "accountant", "accounting", "audit", "banking", "financial"],
    "Healthcare": ["healthcare", "nurse", "medical", "doctor", "pharmacist", "hospital"],
    "Marketing & Sales": ["marketing", "sales", "SEO", "copywriter", "business development"],
    "Engineering & Construction": ["civil", "mechanical", "electrical", "construction", "quantity surveyor"],
    "Education": ["teacher", "education", "lecturer", "professor", "instructor"],
    "HR & Recruitment": ["human resources", "HR", "recruiter", "talent acquisition"],
    "Operations & Logistics": ["operations", "logistics", "supply chain", "warehouse", "procurement"],
    "Design & Creative": ["designer", "design", "creative", "animator", "video editor"],
    "Hospitality": ["hotel", "hospitality", "chef", "restaurant", "tourism"],
    "Custom sector": [],
}
AGES = {"Last 24 hours": 24, "Last 3 days": 72, "Last 7 days": 168,
        "Last 30 days": 720, "Any time": None}
HIRING = re.compile(r"\b(hiring|vacanc(?:y|ies)|job opening|open positions?|join (?:our|the) team|"
                    r"we(?:'re| are) (?:looking|recruiting)|seeking (?:a|an)|apply now|"
                    r"send (?:your |us your )?(?:cv|resume)|recruiting for)\b", re.I)

def terms(value):
    return [x.strip() for x in value.split(',') if x.strip()]

def contains(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I))

def age_bounds(label, now=None):
    """Return a lower/upper age in hours. Rounded labels are intervals, not exact dates."""
    now = now or datetime.now(timezone.utc)
    try:
        date = datetime.fromisoformat(label.replace('Z', '+00:00'))
        if date.tzinfo:
            hours = (now - date).total_seconds() / 3600
            return (hours, hours) if hours >= 0 else (None, None)
    except (ValueError, AttributeError):
        pass
    value = (label or '').strip().lower()
    if value in ('now', 'just now'):
        return 0, 1 / 60
    match = re.search(r'(?<!\w)(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|months?|mo|years?|yr|y)\b', value)
    if not match:
        return None, None
    number, unit = int(match[1]), match[2]
    scale = 720 if unit.startswith('mo') else {'s': 1/3600, 'm': 1/60, 'h': 1, 'd': 24, 'w': 168, 'y': 8760}[unit[0]]
    return number * scale, (number + 1) * scale

@dataclass
class Filters:
    keywords: str = ''
    keyword_mode: str = 'Any keyword'
    sector: str = 'Any sector'
    custom_sector: str = ''
    age: str = 'Last 24 hours'
    location: str = ''
    exclude: str = ''
    people_only: bool = True
    hiring_only: bool = True
    include_unknown_age: bool = False

    def sector_terms(self):
        return terms(self.custom_sector) if self.sector == 'Custom sector' else SECTORS.get(self.sector, [])

    def matches(self, post, now=None):
        text = post.get('text', '')
        if self.people_only and post.get('author_type') != 'person':
            return False
        if self.hiring_only and not HIRING.search(text):
            return False
        keys = terms(self.keywords)
        if keys and not (all if self.keyword_mode == 'All keywords' else any)(contains(text, x) for x in keys):
            return False
        sector = self.sector_terms()
        if sector and not any(contains(text, x) for x in sector):
            return False
        if self.location and not any(contains(text, x) for x in terms(self.location)):
            return False
        if any(contains(text, x) for x in terms(self.exclude)):
            return False
        limit = AGES[self.age]
        if limit is not None:
            # Relative labels are anchored to collection time so saved posts age correctly.
            anchor = now or datetime.now(timezone.utc)
            collected = post.get('collected_at')
            try:
                at = datetime.fromisoformat(collected) if collected else anchor
                if not at.tzinfo:
                    at = anchor
            except ValueError:
                at = anchor
            low, high = age_bounds(post.get('age', ''), at)
            if high is None:
                return self.include_unknown_age
            elapsed = max(0, (anchor-at).total_seconds()/3600)
            if high + elapsed > limit:
                return False
        return True

    def search_url(self):
        def quoted(value):
            return '"' + value.replace('"', '').strip() + '"'
        keys = terms(self.keywords)
        operator = ' AND ' if self.keyword_mode == 'All keywords' else ' OR '
        parts = ['(' + operator.join(map(quoted, keys)) + ')'] if keys else []
        if self.hiring_only:
            parts.append('(hiring OR vacancy OR "job opening" OR "join our team" OR "we are looking" OR "apply now")')
        # Sectors are applied locally: adding every sector term can make LinkedIn reject long queries.
        if self.location:
            parts.append('(' + ' OR '.join(map(quoted, terms(self.location))) + ')')
        params = {'keywords': ' AND '.join(parts) or 'hiring', 'sortBy': '"date_posted"', 'origin': 'FACETED_SEARCH'}
        limit = AGES[self.age]
        if limit:
            params['datePosted'] = '"' + ('past-24h' if limit <= 24 else 'past-week' if limit <= 168 else 'past-month') + '"'
        return 'https://www.linkedin.com/search/results/content/?' + urlencode(params)

def safe_url(value):
    try:
        url = urlparse(value)
        return url.scheme == 'https' and (url.hostname == 'linkedin.com' or (url.hostname or '').endswith('.linkedin.com'))
    except ValueError:
        return False

def export_csv(path, posts):
    columns = ['author', 'author_url', 'author_type', 'age', 'text', 'url', 'collected_at']
    def safe(value):
        value = str(value or '')
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
    with open(path, 'w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: safe(post.get(key, '')) for key in columns} for post in posts)
