import sys, json, time; sys.path.insert(0, '.')
from client import *
time.sleep(3)
t = token()
r = call('research/start', {'hypothesis': 'Before I adopt published METR-LA and PEMS04 results as baselines, which reported comparisons between GTS, Graph WaveNet, MTGNN, AGCRN, and STAEformer hold under matched protocols?',
                            'provider': 'nebius', 'model': 'nvidia/nemotron-3-super-120b-a12b', 'seeds': ['2101.06861', '1906.00121', '2005.11650', '2007.02842', '2308.10425'], 'seedOnly': True}, t)
pid = r['id']; open('project_id', 'w').write(pid); print('project', pid, flush=True)
p = wait(pid)
gts = next(x for x in p['papers'] if 'Discrete Graph' in x['title'])
print('checking 2.99 in GTS', flush=True)
call('research/update', {'id': pid, 'revision': p['revision'], 'action': 'check', 'paper': gts['id'], 'value': '2.99', 'method': 'GTS'}, t)
p = wait(pid)
print('done', p['status'], p.get('error'), flush=True)
