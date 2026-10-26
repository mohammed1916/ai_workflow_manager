"""Immutable execution checkpoints and non-destructive research branches."""
import copy, json, secrets, threading
from .core import RelayError, digest, now, read_config
from .providers import models

class ExecutionHistory:
    def checkpoint(self,p,kind,label,status='complete',details=None):
        with self.lock:
            nodes=p.setdefault('execution',[])
            node={'id':secrets.token_hex(8),'kind':kind,'label':label,'status':status,'at':now(),
                  'parent':nodes[-1]['id'] if nodes else None,'revision':p['revision'],
                  'paperCount':len(p['papers']),'metricCount':sum(len(x.get('metrics',[])) for x in p['papers']),
                  'tokens':p.get('tokens',0),'details':details or {}}
            snapshot={k:copy.deepcopy(v) for k,v in p.items() if k not in ('execution','events','activeStep')}
            blob=json.dumps(snapshot,ensure_ascii=False,sort_keys=True)
            node['sha256']=digest(blob)
            folder=self.root/'.relay/checkpoints'/p['id']; folder.mkdir(parents=True,exist_ok=True)
            (folder/(node['id']+'.json')).write_text(blob)
            nodes.append(node); self.save()
            return node

    def get_checkpoint(self,project_id,node_id):
        with self.lock:
            p=self.get(project_id)
            node=next((n for n in p.get('execution',[]) if n['id']==node_id),None)
            if not node: raise RelayError('CHECKPOINT_NOT_FOUND','Choose an existing execution checkpoint.',404)
            path=self.root/'.relay/checkpoints'/p['id']/(node['id']+'.json')
            if not path.is_file() or path.is_symlink(): raise RelayError('CHECKPOINT_MISSING','This saved checkpoint is missing. The current project is preserved.',404)
            blob=path.read_text()
            if digest(blob)!=node['sha256']: raise RelayError('CHECKPOINT_CHANGED','Checkpoint integrity check failed. Branching was blocked.',409)
            return copy.deepcopy(node),json.loads(blob)

    def inspect_checkpoint(self,project_id,node_id):
        node,snapshot=self.get_checkpoint(project_id,node_id)
        for paper in snapshot['papers']: paper.pop('evidence',None)
        return {'node':node,'snapshot':snapshot}

    def branch(self,data):
        action=data.get('next','snapshot')
        if action not in ('snapshot','synthesize','draft','assess','search'): raise RelayError('INVALID_STEP','Choose a supported continuation.')
        node,snapshot=self.get_checkpoint(data.get('id'),data.get('node'))
        hypothesis=str(data.get('hypothesis') or snapshot['hypothesis']).strip()
        if not 10<=len(hypothesis)<=2000: raise RelayError('HYPOTHESIS_REQUIRED','Write a hypothesis between 10 and 2,000 characters.')
        provider=data.get('provider') or snapshot['provider']; model=data.get('model') or snapshot['model']
        if action!='snapshot' and model not in models(read_config(self.root),provider)['models']:
            raise RelayError('INVALID_MODEL','Choose a currently available provider model.')
        if action in ('synthesize','assess') and not snapshot['papers']: raise RelayError('NO_EVIDENCE','This checkpoint has no papers. Continue with discovery instead.')
        if action=='draft' and not any(x.get('reviewed') for x in snapshot['papers']): raise RelayError('REVIEW_REQUIRED','Select reviewed papers in the branch before drafting.')
        changed=hypothesis!=snapshot['hypothesis']
        if changed and action in ('synthesize','draft'): raise RelayError('REASSESS_REQUIRED','For a changed hypothesis, choose Reassess evidence or New discovery first.')
        with self.lock:
            if action!='snapshot' and sum(p['status'] in ('discovering','drafting') for p in self.projects)>=2:
                raise RelayError('BUSY','Two agents are already running. You can still create an editable checkpoint copy.')
            p=copy.deepcopy(snapshot)
            p.update(id=secrets.token_hex(8),created=now(),hypothesis=hypothesis,provider=provider,model=model,
                     revision=1,tokens=0,events=[],execution=[],status='review',
                     branchName=str(data.get('name') or 'Alternative path')[:100],
                     parentProject=data['id'],parentNode=node['id'],rootProject=snapshot.get('rootProject',data['id']),
                     inheritedTokens=snapshot.get('tokens',0),draftReviewed=False)
            p.pop('error',None); p.pop('compile',None)
            p['feedback']=str(data.get('feedback',''))[:3000]
            if changed or action in ('assess','search'):
                p.update(tex='',bib='',suggestions=[],synthesis='',draftReviewed=False)
                p.pop('draft',None)
            if changed:
                for paper in p['papers']:
                    paper.update(relevance=0,assessmentStale=True,rationale='Hypothesis changed. Reassess this paper for the new question.')
            if action=='search': p.update(papers=[],queries=[],criteria=[])
            if action!='snapshot': p['status']='drafting' if action=='draft' else 'discovering'
            self.projects.insert(0,p)
            self.checkpoint(p,'branch','Branched from '+node['label'],details={'sourceProject':data['id'],'sourceNode':node['id'],'next':action,'inheritedRevision':node['revision']})
            self.event(p,'Created an independent branch. The parent checkpoint is unchanged.')
        if action!='snapshot': threading.Thread(target=self.continue_branch,args=(p,action),daemon=True).start()
        return {'id':p['id'],'parentProject':p['parentProject'],'parentNode':p['parentNode']}

    def continue_branch(self,p,action):
        try:
            if action=='search': self.run(p); return
            if action=='draft': self.write(p,[copy.deepcopy(x) for x in p['papers'] if x.get('reviewed')]); return
            if action=='assess':
                from .research import analysis_text, validate_analysis
                for paper in p['papers']:
                    self.event(p,'Reassessing hypothesis fit: '+paper['title'][:100])
                    a=self.llm(p,'Assess hypothesis fit from source text. Return JSON with relevance (0 to 100), rationale, topic, and limitations. Distinguish unknown context from demonstrated limitations. Do not extract or change numeric metrics.',{'hypothesis':p['hypothesis'],'title':paper['title'],'text':analysis_text(paper.get('evidence','')),'feedback':p.get('feedback','')})
                    with self.lock:
                        metrics=copy.deepcopy(paper['metrics']); validate_analysis(paper,a); paper['metrics']=metrics; paper.pop('assessmentStale',None)
                        p['revision']+=1
                        self.checkpoint(p,'assessment','Reassessed '+paper['title'][:85],details={'paper':paper['id']})
            self.synthesize(p)
            with self.lock:
                p['status']='review'; p['revision']+=1
                self.checkpoint(p,'ready','Continuation completed')
            self.event(p,'Branch execution completed. Its evidence and outputs are ready to inspect.')
        except Exception as e:
            with self.lock:
                p.update(status='error',error=str(e)[:350])
                self.checkpoint(p,'failure','Continuation failed',status='failed',details={'error':p['error']})
