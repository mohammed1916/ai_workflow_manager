"""Archived v1/v2 comparator helpers. Never used for new generic investigations."""
import re


def kind(key, label=''):
    s=(key+' '+label).lower().replace('_',' ')
    if re.search(r'evaluation partition|train.*val.*split|dataset split|eval.*split|validation split',s): return 'partition'
    if re.search(r'resolution|image size|input size',s): return 'resolution'
    if re.search(r'capacity|parameter|model size',s): return 'capacity'
    if re.search(r'distill|teacher',s): return 'distillation'
    if re.search(r'pretrain|training data scope|external data',s): return 'training_data'
    return key


def partition(value):
    s=str(value).lower().strip().replace('_',' ')
    # Strip only descriptive wrappers, never fold train/test into validation.
    s=re.sub(r'\b(imagenet[- ]?1k|imagenet|ilsvrc[- ]?2012|evaluation|official|standard|partition|split|set)\b',' ',s)
    s=' '.join(s.split())
    return {'val':'validation','valid':'validation','validation':'validation','test':'test','training':'train','train':'train'}.get(s)


def resolution(value):
    s=str(value).lower().replace('×','x').replace('²','^2')
    s=re.sub(r'\\(?:times|cdot)', 'x',s)
    s=re.sub(r'[{}()]','',s)
    s=re.sub(r'\b(pixels?|px)\b','',s).strip()
    m=re.fullmatch(r'(\d{2,4})\s*x\s*(\d{2,4})',s)
    if m: return tuple(map(int,m.groups()))
    m=re.fullmatch(r'(\d{2,4})\s*\^\s*2',s)
    if m: return (int(m[1]),int(m[1]))
    # Bare side lengths, including legacy flattened superscripts, are ambiguous.
    return None


def count(value):
    m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(m|million|b|billion)\s*(?:parameters?|params?)?\s*',str(value).lower())
    if not m:return None
    scale=1e9 if m[2] in ('b','billion') else 1e6
    v=float(m[1])*scale
    decimals=len(m[1].split('.')[1]) if '.' in m[1] else 0
    return v, .5*scale/(10**decimals)


def definition(value, dataset='', split=''):
    s=str(value).lower().replace('–','-')
    s=re.sub(r'top[ -]?([15])',r'top-\1',s)
    s=re.sub(r'\bimagenet[- ]?1k\b','imagenet',s)
    # Remove redundant context only if it is independently established for this row.
    if 'imagenet' in str(dataset).lower():
        s=re.sub(r'\bon imagenet\b','',s)
    if partition(split)=='validation': s=re.sub(r'\bvalidation (?:set|partition)\b','',s)
    s=re.sub(r'\b(on|the)\b','',s)
    return ' '.join(s.split()).strip(' .')


def match_condition(field, label, a, b, row_a=None, row_b=None):
    """Return status, explanation; uncertainty is never silently promoted to equality."""
    a,b=str(a).strip(),str(b).strip(); k=kind(field,label)
    if k=='resolution':
        ra,rb=resolution(a),resolution(b)
        if ra and rb:return ('match' if ra==rb else 'conflict'),f'Image dimensions: {ra[0]} × {ra[1]} vs {rb[0]} × {rb[1]}.'
        if re.fullmatch(r'\d{4}',a) or re.fullmatch(r'\d{4}',b):return 'missing','Possible flattened superscript in resolution. Inspect the original table; no pixel dimension is inferred.'
    if a.casefold()==b.casefold():return 'match',a
    if k=='capacity':
        ca,cb=count(a),count(b)
        if ca and cb:
            if ca[0]==cb[0]:return 'match','Parameter counts agree after unit conversion.'
            if abs(ca[0]-cb[0]) <= ca[1]+cb[1] or abs(ca[0]-cb[0])/max(ca[0],cb[0])<=.02:
                return 'missing','Close or rounded parameter counts need capacity review; neither equality nor incompatibility is established.'
            return 'conflict','Reported parameter counts differ beyond rounding; model capacity is not matched.'
    if field=='unit':
        u=lambda x: {'percent':'%','percentage':'%'}.get(x.lower(),x.lower())
        if u(a)==u(b):return 'match','Equivalent unit notation.'
    if field=='metricDefinition' and row_a and row_b:
        if definition(a,row_a['dataset'],row_a['split'])==definition(b,row_b['dataset'],row_b['split']):
            return 'match','Metric descriptions agree after removing independently matched dataset/partition wording.'
    if k=='partition' and partition(a) and partition(b):
        return ('match' if partition(a)==partition(b) else 'conflict'),'Named evaluation partitions compared.'
    if k=='resolution':return 'missing','Resolution notation needs source review; a bare number does not establish both image dimensions.'
    na,nb=re.findall(r'\d+(?:\.\d+)?',a),re.findall(r'\d+(?:\.\d+)?',b)
    form=lambda x:re.sub(r'\d+(?:\.\d+)?','#',x).casefold()
    if na and nb and na!=nb and form(a)==form(b):return 'conflict','Recorded numerical settings differ.'
    return 'missing','Equivalence needs review; different wording does not establish incompatibility.'


def method_matches(value, target):
    # Historical views can select an exact reported label; no inferred family membership.
    return str(value).strip().casefold() == str(target).strip().casefold()


def non_distilled_requested(protocol):
    text=' '.join(str(protocol.get(k,'')) for k in ('question','direction'))
    return bool(re.search(r'compare\s+(?:only\s+)?non[ -]distilled|non[ -]distilled[^.]{0,100}\bonly\b|\bonly[^.]{0,60}non[ -]distilled|only (?:models )?(?:without|no) distillation',text,re.I))


def distillation_state(value):
    s=str(value).lower().strip()
    if re.search(r'non[ -]distill|no distill|without distill',s) or s in ('no','none','not used','false'):return 'none'
    if re.search(r'distill|teacher|\bhard\b|\bsoft\b',s) or s in ('yes','true'):return 'used'
    return None
