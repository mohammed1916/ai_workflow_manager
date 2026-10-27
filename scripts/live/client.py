"""Minimal Relay API client for live acceptance runs (same requests the browser makes)."""
import json, os, sys, time, urllib.request
BASE = os.environ.get('RELAY_URL','http://127.0.0.1:4280').rstrip('/')
def call(path, data=None, token=None):
    req = urllib.request.Request(BASE + '/api/' + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (token or ''), 'Origin': BASE} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read(); return json.loads(body) if r.headers.get('Content-Type', '').startswith('application/json') else body
    except urllib.error.HTTPError as e:
        raise SystemExit(f'{path}: HTTP {e.code} {e.read()[:300]}')
def token(): return call('state')['token']
def project(pid): return next(p for p in call('research')['projects'] if p['id'] == pid)
def wait(pid, quiet=False, limit=1800):
    start = time.time(); last = ''
    while time.time() - start < limit:
        p = project(pid)
        if p.get('activeStep') != last and not quiet: last = p.get('activeStep'); print(f'[{time.time()-start:5.0f}s] {last}', flush=True)
        if p['status'] not in ('discovering', 'drafting', 'investigating'): return p
        time.sleep(4)
    raise SystemExit('timeout')
