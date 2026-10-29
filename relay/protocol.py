"""Question-specific comparison contracts. Never infer missing result values from a contract."""
import re
from .matching import kind, non_distilled_requested

PLAN = '''Plan a source-grounded comparison for this research question and researcher direction.
Return {"queries":[two scholarly search strings],"protocol":{"task":"forecasting, classification, or general","targetMethods":["first model family","second model family"],"factors":[{"key":"short_snake_case","label":"Readable experimental condition","reason":"Why matching it is needed for this question"}]}}.
Use targetMethods only for an explicit two-family comparison, otherwise return an empty list. Restrictions such as non-distilled must be represented as a factor even when both sides must have the same value. Choose 2 to 8 essential experimental conditions, not outcome metrics. For image classification consider external pretraining data, input resolution, model capacity, distillation/teacher, and evaluation protocol. For other research choose the relevant population, intervention, evaluation design, budget or protocol. Forecasting horizon is handled separately ONLY for forecasting. Dataset, metric identity, units, evaluation partition and provenance are handled separately. Do not invent experimental values. If the user explicitly excludes a factor, omit it and explain the narrowed scope in the search queries only if relevant. These are proposed criteria, not verified facts.'''

def contract(raw):
    raw = raw if isinstance(raw, dict) else {}
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
    if non_distilled_requested(protocol) and not any(kind(f['key'],f.get('label',''))=='distillation' for f in protocol.get('factors',[])):
        protocol.setdefault('factors',[]).append({'key':'factor_distillation','label':'Distillation','reason':'The question restricts comparison to non-distilled results.'})
    return protocol
