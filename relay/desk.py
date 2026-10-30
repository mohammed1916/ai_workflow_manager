"""Research desk, reproducible saved examples, and the application's API description."""
import copy
import base64
import gzip
import json
import secrets
from pathlib import Path
from .core import RelayError, digest, now

API = [
    {'method':'POST','path':'/api/research/stop','purpose':'Stop one investigation cooperatively; preserve saved results. An in-flight provider request may finish and be billed.','example':{'id':'PROJECT'}},
    {'method':'POST','path':'/api/research/scan-tables','purpose':'Inventory tables from retrieved text without inference; pause for source selection.','example':{'id':'PROJECT'}},
    {'method':'POST','path':'/api/research/extract-selected','purpose':'Extract selected source rows and pause for comparison selection.','example':{'id':'PROJECT','revision':1,'selections':[{'paper':'PAPER','table':'TABLE','rows':['L10','L11']}]}},
    {'method':'GET','path':'/api/desk','purpose':'Recent research runs, source coverage, and explicitly recorded validation.'},
    {'method':'GET','path':'/api/submission/export','purpose':'Download the source test build with README, license, data, and tests. Excludes local credentials and private state.'},
    {'method':'GET','path':'/api/schema','purpose':'API catalog and request examples. Mutations use the session bearer token from /api/state.'},
    {'method':'GET','path':'/api/research','purpose':'All research projects, evidence metadata, proposals, drafts, and model-call records.'},
    {'method':'GET','path':'/api/research/source?id=PROJECT&paper=PAPER','purpose':'Retrieved source text and its content hash.'},
    {'method':'GET','path':'/api/research/checkpoint?id=PROJECT&node=NODE','purpose':'Inspect an immutable saved execution state.'},
    {'method':'GET','path':'/api/models?provider=nebius','purpose':'Fetch models available from the configured provider.'},
    {'method':'POST','path':'/api/desk/load','purpose':'Load the recorded Nebius study into the workspace. Idempotent; does not call a model. Downloads public source text if not cached.','example':{}},
    {'method':'POST','path':'/api/research/start','purpose':'Discover and assess papers for a new question. Starts background model work.',
     'example':{'hypothesis':'Which traffic-forecasting baselines use comparable experimental protocols?','provider':'nebius','model':'nvidia/nemotron-3-super-120b-a12b','seeds':['2101.06861','1906.00121'],'seedOnly':False,'paperLimit':10,'resultLimit':10,'comparisonLimit':'all'}},
    {'method':'POST','path':'/api/research/investigate','purpose':'Investigate up to two results and selected fields, with optional direction text. Returns source-backed proposals for human review.',
     'example':{'id':'PROJECT','revision':1,'repository':True,'targets':[{'paper':'PAPER','metric':'METRIC','fields':['split','metricDefinition']}]}},
    {'method':'POST','path':'/api/research/update','purpose':'Review evidence, check a number, add a paper, accept/reject a proposal, apply a correction, amend-draft with structured source-reviewed prose, or save a manuscript. Requires the current revision.',
     'example':{'id':'PROJECT','revision':1,'action':'correct','actor':'agent','paper':'PAPER','metric':'METRIC','field':'metricDefinition','value':'non-standard evaluation','note':'Source-backed reason for this correction.'}},
    {'method':'POST','path':'/api/research/compare','purpose':'Compute comparisons from the current evidence. No model call.', 'example':{'id':'PROJECT','papers':[]}},
    {'method':'POST','path':'/api/research/assess-comparisons','purpose':'Assess the selected total in small calls; limit accepts a positive count or all.', 'example':{'id':'PROJECT','revision':1,'entities':['e1','e2'],'limit':'all'}},
    {'method':'POST','path':'/api/research/review-contract','purpose':'Record human review of the question-to-criteria mapping; does not verify results.', 'example':{'id':'PROJECT','revision':1,'approved':True,'note':'Checked every question requirement.'}},
    {'method':'POST','path':'/api/research/review-comparison','purpose':'Record review of the current evidence assessment.', 'example':{'id':'PROJECT','revision':1,'pair':'PAIR','approved':True,'note':'Checked source applicability.'}},
    {'method':'POST','path':'/api/research/branch','purpose':'Copy a checkpoint, or continue with search, relevance assessment, criteria revision using inherited observations (next: plan), source re-extraction (next: extract), synthesis, or drafting.',
     'example':{'id':'PROJECT','node':'NODE','next':'snapshot','name':'Alternative experiment'}},
    {'method':'POST','path':'/api/research/draft','purpose':'Generate a proposed-study manuscript from reviewed sources.',
     'example':{'id':'PROJECT','revision':1,'feedback':'Explain incompatible baselines and propose a common evaluation protocol. Do not claim experiments were conducted.'}},
    {'method':'POST','path':'/api/research/regenerate','purpose':'Rewrite manuscript claims affected by corrections.', 'example':{'id':'PROJECT','revision':1}},
    {'method':'POST','path':'/api/research/compile','purpose':'Compile the current LaTeX in the local compiler sandbox.', 'example':{'id':'PROJECT','revision':1}},
    {'method':'GET','path':'/api/research/export/PROJECT','purpose':'Download main.tex, references.bib, and evidence.json as an Overleaf-compatible ZIP.'},
]


def schema():
    return {'version':'1.0','authentication':'GET /api/state returns the local session token; send Authorization: Bearer TOKEN for POST. Provider keys stay on the server or in request headers, never in saved data.',
            'reviewActors':['researcher','agent'],'endpoints':API}


def evaluation(root):
    runs=[]
    for path in sorted((root/'eval/results').glob('*.json')):
        if path.name.startswith('.') or path.name < '20261027-063613': continue
        record=json.loads(path.read_text(encoding='utf-8'))
        runs.append({'id':path.stem,'when':record.get('when'),'split':record['split'],'model':record['model'],
                     'relay':record['summary'].get('relay'),'baseline':record['summary'].get('baseline'),'cost':record.get('cost',{})})
    return {'runs':runs,'limitations':['Labels were annotated by an AI coding agent; there is no independent domain-researcher validation.',
        'Development and held-out cases share papers. The held-out results are optimistic and are not a clean generalization test.',
        'These recorded runs evaluate the earlier traffic comparator, not the new question-specific contracts. Model outputs vary; cross-domain accuracy is not established.']}


def overview(root, research):
    featured=next((p for p in research.projects if p.get('studyKey')=='nebius-benchmark-audit-v1' and not p.get('parentProject')),None)
    path=root/'data/research/workflow-validation.json'
    validation=None
    if path.exists():
        receipt=json.loads(path.read_text(encoding='utf-8'));project=receipt['project']['project']
        validation={'title':project['hypothesis'],'description':receipt['kind'],'papers':len(project['papers']),'results':sum(len(x.get('metrics',[])) for x in project['papers']),'tokens':project.get('tokens',0)}
    guided_path=root/'data/research/guided-study.json'
    guided=None
    if guided_path.exists():
        recorded=json.loads(guided_path.read_text(encoding='utf-8'))
        project=recorded['project']['project']
        guided={'title':project['hypothesis'],'id':project['id'],'results':sum(len(x['metrics']) for x in project['papers']),'summary':recorded.get('summary',{}),'calls':len(recorded.get('calls',[]))}
    return {'guidedStudy':guided,'featured':{'id':featured['id'],'status':featured['status'],'papers':len(featured['papers']),'tokens':featured.get('tokens',0),
                        'calls':len(featured.get('calls',[])),'compiled':bool(featured.get('compile',{}).get('ok'))} if featured else None,
            'recent':[{'id':p['id'],'title':p.get('branchName') or p['hypothesis'],'status':p['status'],'papers':len(p['papers']),'results':sum(len(x.get('metrics',[])) for x in p['papers']),'tokens':p.get('tokens',0),'calls':len(p.get('calls',[])),'provider':p['provider'],'model':p['model']} for p in research.projects if p.get('provider')=='nebius' and p.get('studyKey') not in ('nebius-benchmark-audit-v1','nebius-discovery-v1') and not p.get('parentProject')][:4],
            'findings':[],'workflowValidation':validation,'evaluation':evaluation(root),
            'scope':'Source-backed quantitative and qualitative comparisons. Recorded accuracy evaluation covers traffic forecasting; other domains require validation.',
            'review':'Recorded study · Ready for human review.',
            'readiness':{'runtime':'Nebius Token Factory / NVIDIA Nemotron research calls are recorded in the prepared study.',
                         'remaining':['Final public demo-video URL and Devpost submission are still required.','Independent researcher validation has not been performed.']}}


def load_study(root, research):
    """Install two recorded states without fabricating the missing intermediate checkpoints."""
    from .research import html_to_text, fetch, SOURCE_LIMIT, manuscript
    with research.lock:
        existing=next((p for p in research.projects if p.get('studyKey')=='nebius-benchmark-audit-v1' and not p.get('parentProject')),None)
        if existing:return {'id':existing['id'],'loaded':False}
    records=[json.loads((root/'data/research'/name).read_text(encoding='utf-8')) for name in ('before-correction.json','after-correction.json')]
    # Validate every content-addressed source before changing any project state.
    texts={}
    for paper in records[-1]['papers']:
        path=root/'eval/.cache'/(paper['arxiv']+'.html')
        raw=path.read_text(encoding='utf-8') if path.exists() else fetch(paper['evidenceUrl'])
        text=html_to_text(raw, preserve_math=False)[:SOURCE_LIMIT]
        if digest(text)!=paper['sourceRef']:
            raise RelayError('SOURCE_CHANGED','The public source differs from the recorded version. The saved study was not loaded; use a fresh investigation instead.',409)
        texts[paper['sourceRef']]=text
    with research.lock:
        existing=next((p for p in research.projects if p.get('studyKey')=='nebius-benchmark-audit-v1' and not p.get('parentProject')),None)
        if existing:return {'id':existing['id'],'loaded':False}
        source_dir=root/'.relay/sources';source_dir.mkdir(parents=True,exist_ok=True)
        for ref,text in texts.items():(source_dir/(ref+'.txt')).write_text(text, encoding='utf-8')
        pid=secrets.token_hex(8)
        def prepare(record):
            p=copy.deepcopy(record)
            p.update(id=pid,status='review',execution=[],studyKey='nebius-benchmark-audit-v1',branchName='Nebius study · benchmark evidence audit',draftReviewed=False)
            p['archive']={'originalProject':record['id'],'recordedAt':record['created'],'importedAt':now(),'executionSteps':len(record.get('execution',[])),
                          'note':record.get('_recordNote',''),'recordedExecution':record.get('execution',[])}
            p.pop('error',None);p.pop('compile',None)
            for paper in p['papers']:
                paper['evidence']=texts[paper['sourceRef']][:65000]
                if paper.get('reviewed'):paper['reviewActor']='agent'
            for c in p.get('corrections',[]):c['beforeNode']=None;c['actor']='agent'
            if p.get('draft'):p['tex'],p['bib']=manuscript(p,p['draft'])
            return p
        p=prepare(records[0]);research.projects.insert(0,p)
        before=research.checkpoint(p,'import','Recorded live study · before final correction',details={'note':'Imported saved snapshot. Historical intermediate checkpoints are not available locally.'})
        after=prepare(records[1]);after['execution']=p['execution']
        before_ids={c['id'] for c in records[0].get('corrections',[])}
        for c in after.get('corrections',[]):
            if c['id'] not in before_ids:c['beforeNode']=before['id']
        research.projects[0]=after
        research.checkpoint(after,'import','Recorded live study · corrected and regenerated',details={'note':'Imported second recorded snapshot, with original model-call provenance. No new inference was performed during import.'})
        research.event(after,'Prepared for inspection through the research desk. Agent review only; independent researcher review remains open.')
        return {'id':pid,'loaded':True}


def load_discovery(root, research):
    """Replay the saved open-search result as one honest imported snapshot."""
    from .research import html_to_text, fetch, SOURCE_LIMIT, ARXIV_ID
    record=json.loads((root/'data/research/discovery-study.json').read_text(encoding='utf-8'))
    with research.lock:
        existing=next((p for p in research.projects if p['id']==record['id'] or (p.get('studyKey')=='nebius-discovery-v1' and not p.get('parentProject'))),None)
        if existing:return {'id':existing['id'],'loaded':False}
    sources={}
    for paper in record['papers']:
        if not paper.get('sourceRef'):continue
        aid=ARXIV_ID.search(paper.get('evidenceUrl',''))
        if not aid:raise RelayError('SOURCE_MISSING','Recorded source has no arXiv locator.')
        cache=root/'eval/.cache'/(aid[1]+'.html')
        text=html_to_text(cache.read_text(encoding='utf-8') if cache.exists() else fetch(paper['evidenceUrl']), preserve_math=False)[:SOURCE_LIMIT]
        if digest(text)!=paper['sourceRef']:raise RelayError('SOURCE_CHANGED','The source version differs from the recorded discovery. Start a fresh investigation.',409)
        sources[paper['sourceRef']]=text
    with research.lock:
        existing=next((p for p in research.projects if p['id']==record['id'] or (p.get('studyKey')=='nebius-discovery-v1' and not p.get('parentProject'))),None)
        if existing:return {'id':existing['id'],'loaded':False}
        p=copy.deepcopy(record);p.update(id=secrets.token_hex(8),execution=[],status='review',studyKey='nebius-discovery-v1',draftReviewed=False)
        p.pop('compile',None);p.pop('error',None)
        p['archive']={'originalProject':record['id'],'recordedAt':record['created'],'importedAt':now(),'note':record['_recordNote'],'recordedExecution':record.get('execution',[])}
        for paper in p['papers']:
            paper['evidence']=sources.get(paper.get('sourceRef'),paper.get('abstract',''))[:65000]
            if paper.get('reviewed'):paper['reviewActor']='agent'
        folder=root/'.relay/sources';folder.mkdir(parents=True,exist_ok=True)
        for ref,text in sources.items():(folder/(ref+'.txt')).write_text(text, encoding='utf-8')
        research.projects.insert(0,p)
        research.checkpoint(p,'import','Recorded discovery and manuscript',details={'note':'Imported final snapshot of an API-run study, not reconstructed intermediate executions.'})
        return {'id':p['id'],'loaded':True}


def load_validation(root,research,filename='workflow-validation.json'):
    path=root/'data/research'/filename
    if not path.exists():raise RelayError('NOT_FOUND','No recorded workflow validation is installed.',404)
    receipt=json.loads(path.read_text(encoding='utf-8'));document=copy.deepcopy(receipt['project'])
    for paper in document['project']['papers']:
        if paper.get('sourceRef') and digest(paper.get('evidence',''))!=paper['sourceRef']:
            raise RelayError('SOURCE_CHANGED','Recorded source hash does not match its evidence; import stopped.',409)
    recorded_checkpoints=receipt.get('checkpoints',[])
    for item in recorded_checkpoints:
        if 'snapshotGzip' in item:item['snapshot']=json.loads(gzip.decompress(base64.b64decode(item['snapshotGzip'])))
        blob=json.dumps(item['snapshot'],ensure_ascii=False,sort_keys=True)
        if digest(blob)!=item['node']['sha256'] or item['snapshot']['id']!=document['project']['id']:
            raise RelayError('CHECKPOINT_CHANGED','Recorded checkpoint integrity check failed.',409)
    document['project']['archive']=document['project'].get('archive') or True
    document['project']['studyKey']='guided-study-v1' if filename=='guided-study.json' else 'generic-workflow-validation-v1'
    result=research.import_project(document)
    result['id']=document['project']['id']
    p=research.get(result['id'])
    if not result.get('existing'):
        p['calls']=receipt.get('calls',[])
        if recorded_checkpoints:
            folder=root/'.relay/checkpoints'/p['id'];folder.mkdir(parents=True,exist_ok=True)
            for item in recorded_checkpoints:
                (folder/(item['node']['id']+'.json')).write_text(json.dumps(item['snapshot'],ensure_ascii=False,sort_keys=True),encoding='utf-8')
            p['execution']=[copy.deepcopy(item['node']) for item in recorded_checkpoints]
        research.checkpoint(p,'validation-import','Recorded live validation imported without new inference',details={'receipt':'data/research/'+filename,'humanReviewed':False})
    return result
