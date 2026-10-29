"""Question-specific comparison contracts. Never infer missing result values from a contract."""
import re
from .legacy_matching import kind, non_distilled_requested

from .semantics import PLAN


def contract(raw):
    raw = raw if isinstance(raw, dict) else {}
    if raw.get('version')==3:
        from .semantics import contract as generic_contract
        return generic_contract(raw)
    task = raw.get('task') if raw.get('task') in ('forecasting','classification','general') else 'general'
    factors = []
    for f in (raw.get('factors') or [])[:8]:
        if not isinstance(f, dict): continue
        key = re.sub('[^a-z0-9_]', '', str(f.get('key','')).lower())[:40]
        if not key or any(x['key'] == 'factor_'+key for x in factors): continue
        semantic=kind(key,str(f.get('label','')))
        if semantic=='partition': continue
        if any(kind(x['key'],x['label'])==semantic for x in factors): continue
        factors.append({'key':'factor_'+key, 'label':str(f.get('label') or key)[:90], 'reason':str(f.get('reason') or '')[:250]})
    targets=raw.get('targetMethods',[])
    targets=[str(x).strip()[:80] for x in targets[:2] if isinstance(x,str) and x.strip()] if isinstance(targets,list) else []
    return {'version':2,'targetMethods':targets if len(targets)==2 else [], 'task':task, 'factors':factors, 'review':'Ready for human review'}

def protocol_of(metric):
    value = metric.get('protocol',{})
    return value if isinstance(value,dict) else {}

def factor_keys(metric):
    return [f['key'] for f in protocol_of(metric).get('factors',[]) if isinstance(f,dict) and re.fullmatch(r'factor_[a-z0-9_]{1,40}',str(f.get('key','')))]

def forecasting(metric):
    return protocol_of(metric).get('task','forecasting') == 'forecasting'


def enforce_scope(protocol):
    """Add an explicit eligibility field for a requested subset; never populate its value."""
    if protocol.get('version')==3: return protocol
    if non_distilled_requested(protocol) and not any(kind(f['key'],f.get('label',''))=='distillation' for f in protocol.get('factors',[])):
        protocol.setdefault('factors',[]).append({'key':'factor_distillation','label':'Distillation','reason':'The question restricts comparison to non-distilled results.'})
    return protocol
