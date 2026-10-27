"""Remaining journey on the final code. Decisions are made by this script, not by a human reviewer; the saved record says so."""
import sys, json; sys.path.insert(0, '.')
from client import *
pid = open('project_id').read(); t = token()
p = wait(pid, quiet=True); print('start', p['status'], p.get('error'), flush=True)
for x in p['papers']:
    p = project(pid)
    call('research/update', {'id': pid, 'revision': p['revision'], 'action': 'review', 'actor': 'agent', 'paper': x['id'], 'reviewed': True, 'verified': [],
                             'note': 'Reviewed by test script for drafting; not human-verified.', 'metrics': []}, t)
print('reviewed', len(p['papers']), flush=True)
p = project(pid)
for prop in [x for x in p.get('proposals', []) if x['status'] == 'pending']:
    p = project(pid)
    try:
        r = call('research/update', {'id': pid, 'revision': p['revision'], 'action': 'proposal', 'actor': 'agent', 'proposal': prop['id'], 'decision': 'accept', 'value': prop['value']}, t)
        print('accepted', prop['field'], prop['value'][:60], '->', r.get('correction'), flush=True)
    except SystemExit as e: print('skip', prop['field'], str(e)[:120], flush=True)
p = wait(pid, quiet=True); print('after accept', p['status'], flush=True)
p = project(pid)
call('research/draft', {'id': pid, 'revision': p['revision'], 'feedback': 'Propose which baselines to re-run under one protocol. Do not claim we have run experiments.'}, t)
p = wait(pid, quiet=True); print('draft', p['status'], p.get('error'), flush=True)
if p.get('draft'):
    d = p['draft']; print('claims', {s: [i['claim'] for i in d[s]] for s in ('relatedWork', 'comparisons')}, flush=True)
p = project(pid)
r = call('research/compile', {'id': pid, 'revision': p['revision']}, t); print('compile ok', r['ok'], flush=True)
z = call('research/export/' + pid, None, t); open('export.zip', 'wb').write(z); print('zip bytes', len(z), flush=True)
p = project(pid)
corr = next((c for c in p.get('corrections', [])), None)
if corr:
    b = call('research/branch', {'id': pid, 'node': corr['beforeNode'], 'next': 'snapshot', 'name': 'Before correction (test)'}, t)
    print('branch', b['id'], flush=True)
rec = project(pid); rec.pop('tex', None); rec.pop('bib', None)
rec['_recordNote'] = 'Live run on the final code. Reviews, proposal decisions, and draft acceptance were made by a test script, not a human reviewer.'
open('record.json', 'w').write(json.dumps(rec, indent=1, ensure_ascii=False))
print('record saved; calls', len(rec['calls']), 'tokens', rec['tokens'], flush=True)
