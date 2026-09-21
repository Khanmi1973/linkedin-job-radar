() => {
  const roots = [...document.querySelectorAll('[data-urn*="urn:li:activity:"], [data-id*="urn:li:activity:"], .feed-shared-update-v2, .occludable-update')];
  const seen = new Set();
  const clean = el => el ? el.innerText.trim() : '';
  return roots.flatMap(root => {
    const body = root.querySelector('.update-components-text, .feed-shared-update-v2__description, .feed-shared-text, [data-test-id="main-feed-activity-card__commentary"]');
    if (!body || !clean(body)) return [];
    const actor = root.querySelector('.update-components-actor, .feed-shared-actor, .base-main-feed-card__actor');
    const link = actor?.querySelector('a[href*="/in/"], a[href*="/company/"], a[href*="/school/"]');
    const name = actor?.querySelector('.update-components-actor__name .visually-hidden, .update-components-actor__name, .feed-shared-actor__name, .base-main-feed-card__title');
    const time = root.querySelector('time[datetime]');
    const subtitle = actor?.querySelector('.update-components-actor__sub-description, .feed-shared-actor__sub-description');
    const subtitleText = clean(subtitle);
    const visibilityText = subtitleText + ' ' + [...(subtitle?.querySelectorAll('[aria-label], [title]') || [])].map(el => (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).join(' ');
    const relative = subtitleText.match(/\b\d+\s*(?:mo|[smhdwy])\b/i)?.[0] || subtitleText.match(/\b\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b/i)?.[0] || '';
    const activity = (root.getAttribute('data-urn') || root.getAttribute('data-id') || '').match(/urn:li:activity:(\d+)/)?.[1];
    const permalink = root.querySelector('a[href*="/feed/update/urn:li:activity:"], a[href*="/posts/"]');
    const url = activity ? `https://www.linkedin.com/feed/update/urn:li:activity:${activity}/` : (permalink?.href?.split('?')[0] || '');
    const text = clean(body);
    const authorUrl = link?.href?.split('?')[0] || '';
    const key = url || authorUrl + '\n' + text;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{id: key, author: clean(name).split('\n')[0] || 'Unknown author', author_url: authorUrl,
      author_type: authorUrl.includes('/in/') ? 'person' : /\/(company|school)\//.test(authorUrl) ? 'company' : 'unknown',
      age: time?.getAttribute('datetime') || relative, text, url,
      public_visibility: /visible to anyone|anyone on or off linkedin/i.test(visibilityText)}];
  });
}
