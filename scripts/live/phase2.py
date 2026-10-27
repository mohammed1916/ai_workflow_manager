import sys, json; sys.path.insert(0, '.')
from client import *
pid = open('project_id').read(); t = token()
def gapped(pairs):
    # Pairs with a missing or conflicting context field; investigate the first few on distinct papers.
    picked, seen = [], set()
    for x in pairs:
        if any(c['status'] in ('missing', 'conflict') and c['field'] != 'name' for c in x['checks']) and x['outcome'] != 'comparable':
            key = (x['a']['paper'], x['b']['paper'])
            if key not in seen: seen.add(key); picked.append(x)
    return picked[:2]
for pair in gapped(call('research/compare', {'id': pid, 'papers': []}, t)['pairs']):
    values = {pair['a']['value'], pair['b']['value']}
    p = project(pid); r = call('research/compare', {'id': pid, 'papers': []}, t)
    fields = sorted({f for c in pair['checks'] if c['status'] in ('missing', 'conflict', 'caveat') and c['field'] != 'name' for f in (['horizon', 'aggregation'] if c['field'] == 'horizon' else [c['field']])})
    print('investigating', values, pair['outcome'], fields, flush=True)
    call('research/investigate', {'id': pid, 'revision': p['revision'], 'pair': pair['id'], 'repository': True,
                                  'targets': [{'paper': pair['a']['paper'], 'metric': pair['a']['metric'], 'fields': fields}, {'paper': pair['b']['paper'], 'metric': pair['b']['metric'], 'fields': fields}]}, t)
    p = wait(pid)
    print('status', p['status'], p.get('error'), flush=True)
p = project(pid)
for x in p['proposals']: print(json.dumps({k: x[k] for k in ('method', 'result', 'field', 'current', 'value', 'origin', 'location', 'quote', 'explanation')})[:700])
for n in p['execution']:
    if n['kind'] == 'investigation': print('NODE', n['label'], json.dumps(n['details'])[:500])
