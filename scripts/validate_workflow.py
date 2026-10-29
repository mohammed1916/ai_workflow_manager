"""Run a real, isolated research workflow and export its evidence and call receipts."""
import argparse
import json
import secrets
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from relay.core import now, read_config
from relay.limits import count
from relay.research import Research, compare


def workload(value):
    parsed = 'all' if value == 'all' else int(value)
    count(parsed, 10, 'Workload')
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', required=True)
    parser.add_argument('--seed', action='append', default=[])
    parser.add_argument('--discover', action='store_true', help='Include scholarly and configured web discovery')
    parser.add_argument('--model')
    parser.add_argument('--papers', type=workload, default=6)
    parser.add_argument('--results', type=workload, default=10)
    parser.add_argument('--comparisons', type=workload, default=6)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 10 <= len(args.question) <= 2000:parser.error('Question must contain 10 to 2,000 characters.')
    if not args.seed and not args.discover:parser.error('Supply a seed or enable --discover.')
    cfg = read_config(ROOT)
    if not cfg.get('NEBIUS_API_KEY'):parser.error('Configure NEBIUS_API_KEY locally; do not place it in command arguments.')
    root = Path(tempfile.mkdtemp(prefix='relay-validation-'))
    research = Research(root)
    project = {'id':secrets.token_hex(8),'hypothesis':args.question,'provider':'nebius',
               'model':args.model or cfg.get('NEBIUS_MODEL','nvidia/nemotron-3-super-120b-a12b'),
               'created':now(),'status':'discovering','revision':1,'tokens':0,'events':[],'papers':[],
               'queries':[],'seeds':args.seed,'seedOnly':not args.discover,'paperLimit':args.papers,
               'resultLimit':args.results,'comparisonLimit':args.comparisons,'calls':[],
               'proposals':[],'corrections':[],'suggestions':[],'tex':'','bib':''}
    research.projects=[project];research.keys[project['id']]=cfg
    original=research.event
    def progress(p,message):
        print(message,flush=True);original(p,message)
    research.event=progress
    print('Isolated state:',root,flush=True)
    research.run(project)
    comparison=compare(project['papers'],assessments=project.get('comparisonAssessments',{}))
    receipt={'kind':'Live provider validation; provisional output, no human review or scientific accuracy claim.',
             'created':now(),'calls':project['calls'],'project':research.export_project(project['id']),
             'summary':{'status':project['status'],'tokens':project['tokens'],'comparisons':comparison['summary'],
                        'coverage':comparison.get('coverage'),'error':project.get('error')}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt['summary'],indent=2))
    return 0 if project['status']=='review' else 1

if __name__=='__main__':raise SystemExit(main())
