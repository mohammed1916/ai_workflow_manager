"""Source coverage and non-destructive accumulation, independent of research domain."""
import copy
import hashlib


def passages(text, size=14000, overlap=900):
    """Walk the complete retrieved text, prefer line boundaries, and retain overlap."""
    if size<=overlap or overlap<0:raise ValueError('Invalid passage size')
    out=[];start=0
    while start<len(text):
        end=min(start+size,len(text))
        if end<len(text):
            boundary=text.rfind('\n',start+size//2,end)
            if boundary>start:end=boundary+1
        body=text[start:end]
        out.append({'id':hashlib.sha256(body.encode()).hexdigest()[:16],'start':start,'end':end,'text':body})
        if end==len(text):break
        start=max(start+1,end-overlap)
    return out


def merge(existing,incoming):
    """Keep accepted results; only merge independently validated supporting fields."""
    out=copy.deepcopy(existing);by_id={m['id']:m for m in out}
    for item in incoming:
        if item['id'] not in by_id:
            saved=copy.deepcopy(item);out.append(saved);by_id[item['id']]=saved;continue
        saved=by_id[item['id']]
        for key,value in item.items():
            if (key.startswith('factor_') or key in ('entityId','entityQuote','outcomeId','outcomeQuote','measurementQuote')) and saved.get(key) in (None,'','unknown') and value not in (None,'','unknown'):
                saved[key]=copy.deepcopy(value)
                if key in item.get('evidence',{}):saved.setdefault('evidence',{})[key]=copy.deepcopy(item['evidence'][key])
        # Never transfer verification from a new model result.
    return out


def covered_chars(chunks):
    end=0;count=0
    for c in sorted(chunks,key=lambda x:x['start']):
        count+=max(0,c['end']-max(end,c['start']));end=max(end,c['end'])
    return count


def coverage_summary(papers):
    total=sum(len(p.get('metrics',[])) for p in papers)
    return {'papers':len(papers),'withResults':sum(bool(p.get('metrics')) for p in papers),
            'withoutResults':sum(not p.get('metrics') for p in papers),'results':total,
            'failed':sum(p.get('coverage',{}).get('status')=='failed' for p in papers),
            'partial':sum(p.get('coverage',{}).get('status')=='partial' for p in papers),
            'unrecorded':sum(not p.get('coverage') for p in papers)}


def indexed_lines(source):
    lines=[];offset=0
    for index,text in enumerate(source.splitlines(keepends=True)):
        content=text.rstrip('\r\n');item={'id':'L'+str(index+1),'text':content,'start':offset,'end':offset+len(text)}
        if content.lstrip().startswith('|'):
            cells=content.strip().split('|')[1:]
            if cells and not cells[-1].strip():cells.pop()
            item['cells']=[{'column':i+1,'text':value.strip()} for i,value in enumerate(cells)]
        lines.append(item);offset+=len(text)
    return lines


def ground_output(raw,lines,allowed=None):
    """Resolve source addresses, never guess a table cell or scientific identity."""
    out=copy.deepcopy(raw);by_id={line['id']:line for line in lines if allowed is None or line['id'] in allowed}
    for note in out.get('contextNotes',[]):
        if not isinstance(note,dict):continue
        line=by_id.get(note.get('line'));scope=by_id.get(note.get('scopeLine'))
        if line:
            note['quote']=line['text'];note['scopeQuote']=(scope or line)['text']
        elif note.get('line'):note['quote']=''
    for metric in out.get('metrics',[]):
        if not isinstance(metric,dict):continue
        metric.pop('sourceEvidence',None)
        ids=metric.get('quoteLines',[]);ids=ids if isinstance(ids,list) else []
        location=metric.get('valueLocation') or {};location=location if isinstance(location,dict) else {}
        line=by_id.get(location.get('line'))
        if line:
            column=location.get('column')
            if isinstance(column,str) and column.isdigit():column=int(column)
            cell=next((c for c in line.get('cells',[]) if c['column']==column),None)
            value=str(metric.get('value',''))
            if (cell and value and value in cell['text']) or (column is None and value and value in line['text']):
                metric['quote']=line['text'];ids=[line['id']]+ids
            else:metric['groundingError']='The reported value is not present in the addressed source cell.'
        elif location.get('line'):
            metric['groundingError']='The cited source line was not supplied in this passage.'
        elif ids and all(isinstance(i,str) and i in by_id for i in ids):
            value=str(metric.get('value',''))
            candidates=[by_id[i] for i in ids if value and value in by_id[i]['text']]
            if len(candidates)==1:metric['quote']=candidates[0]['text']
        # Context addresses resolve literal text only; semantic applicability is audited later.
        locations=metric.get('fieldLocations',{})
        if isinstance(locations,dict):
            for key,address in locations.items():
                if not key.startswith('factor_') or not isinstance(address,dict):continue
                support_line=by_id.get(address.get('line'));quote=''
                if support_line:
                    column=address.get('column')
                    if isinstance(column,str) and column.isdigit():column=int(column)
                    if column is None:quote=support_line['text']
                    else:quote=next((c['text'] for c in support_line.get('cells',[]) if c['column']==column),'')
                    if quote:ids.append(support_line['id'])
                metric.setdefault('evidence',{})[key]=quote
        metric['sourceEvidence']=[{'line':i,'quote':by_id[i]['text']} for i in dict.fromkeys(i for i in ids if isinstance(i,str) and i in by_id)]
    return out


def split_passage(chunk, size=4500):
    if len(chunk['text'])<=size:return []
    children=passages(chunk['text'],size=size,overlap=500)
    for child in children:
        child['start']+=chunk['start'];child['end']+=chunk['start']
    return children


def resume_passages(chunks, attempts):
    latest={a['passage']:a.get('status') for a in attempts}
    out=[]
    for chunk in chunks:
        children=split_passage(chunk) if latest.get(chunk['id']) in ('failed','split') else []
        out.extend(children or [chunk])
    return out


def table_context(source, refs):
    """Return original table blocks and surrounding prose for addressed evidence."""
    lines=source.splitlines();spans=[]
    for key in refs:
        if not key.startswith('source_L') or not key[8:].isdigit():continue
        index=int(key[8:])-1
        if not 0<=index<len(lines):continue
        start=end=index
        while start>0 and lines[start-1].lstrip().startswith('|'):start-=1
        while end+1<len(lines) and lines[end+1].lstrip().startswith('|'):end+=1
        spans.append((max(0,start-3),min(len(lines),end+4)))
    if not spans:
        quote=' '.join(str(refs.get('result',{}).get('quote','')).split())
        for i,line in enumerate(lines):
            if quote and quote in ' '.join(line.split()):spans.append((max(0,i-3),min(len(lines),i+4)))
    selected=set(i for start,end in spans for i in range(start,end))
    return '\n'.join('L'+str(i+1)+': '+lines[i] for i in sorted(selected))
