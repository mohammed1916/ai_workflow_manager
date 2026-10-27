"""Optional web search for missing experimental context. Runs only when a visitor has supplied a Tavily key."""
import json, urllib.error, urllib.request
from .core import RelayError

ENDPOINT = 'https://api.tavily.com/search'
CONTENT_LIMIT = 3000


def search(key, query, max_results=4, timeout=20):
    """Return web passages (ids W1..Wn) for a query. Errors never include the key."""
    if not key: raise RelayError('TAVILY_KEY_REQUIRED', 'Add a Tavily key in Model settings to search the web.')
    body = json.dumps({'query': query, 'max_results': max_results}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method='POST',
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = json.loads(response.read(2000000))
    except urllib.error.HTTPError as e:
        raise RelayError('TAVILY_ERROR', f'Tavily returned HTTP {e.code}. Check the key and usage limits.', 502) from None
    except (OSError, TimeoutError, ConnectionError):
        raise RelayError('TAVILY_ERROR', 'Tavily could not be reached or timed out.', 502) from None
    except ValueError:
        raise RelayError('TAVILY_ERROR', 'Tavily returned an unreadable response.', 502) from None
    results = raw.get('results') if isinstance(raw, dict) else None
    out = []
    for item in (results or []):
        if not isinstance(item, dict) or len(out) >= max_results: continue
        content = str(item.get('content') or '').strip()[:CONTENT_LIMIT]
        url = str(item.get('url') or '').strip()[:500]
        if not content or not url: continue
        title = ' '.join(str(item.get('title') or url).split())[:90]
        out.append({'id': f'W{len(out) + 1}', 'origin': 'web', 'location': title, 'url': url, 'text': content})
    return out
