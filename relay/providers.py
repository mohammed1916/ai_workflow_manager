"""Server-only provider credentials and live model discovery."""
import json, urllib.request, urllib.error
from urllib.parse import urlparse

def key_message():
    import os
    if os.environ.get('RELAY_HOSTED')=='1': return 'Paste your API key in the model menu first. Visitors bring their own key.'
    return 'Configure OLLAMA_TEST_API_KEY or NEBIUS_API_KEY for the selected provider.'


KEY_FIELDS = {'nebius': 'NEBIUS_API_KEY', 'ollama': 'OLLAMA_TEST_API_KEY', 'tavily': 'TAVILY_API_KEY'}


def with_key(cfg, provider, key):
    """Return a copy of cfg with one visitor-supplied key for a provider. The key is never written anywhere."""
    if not key: return cfg
    out = dict(cfg); out[KEY_FIELDS[provider]] = key
    return out


def settings(cfg, provider):
    from .core import RelayError
    if provider=='ollama':
        return {'name':'Ollama Cloud','base':'https://ollama.com','key':cfg.get('OLLAMA_TEST_API_KEY') or cfg.get('OLLAMA_API_KEY',''),'model':cfg.get('OLLAMA_MODEL','gpt-oss:120b')}
    if provider!='nebius': raise RelayError('INVALID_PROVIDER','Choose Ollama Cloud or Nebius.')
    base=cfg.get('NEBIUS_BASE_URL','https://api.tokenfactory.nebius.com/v1').rstrip('/')
    if urlparse(base).scheme!='https' or urlparse(base).hostname not in ('api.tokenfactory.nebius.com','api.tokenfactory.us-central1.nebius.com'):
        raise RelayError('INVALID_ENDPOINT','Use an official Nebius Token Factory HTTPS endpoint.')
    return {'name':'Nebius Token Factory','base':base,'key':cfg.get('NEBIUS_API_KEY',''),'model':cfg.get('NEBIUS_MODEL','nvidia/nemotron-3-super-120b-a12b')}

def request(config, path, payload=None, timeout=90):
    from .core import RelayError
    if not config['key']: raise RelayError('KEY_REQUIRED', key_message())
    req=urllib.request.Request(config['base']+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Authorization':'Bearer '+config['key'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:return json.loads(response.read(4000000))
    except urllib.error.HTTPError as e:
        error=RelayError('PROVIDER_ERROR',f"{config['name']} returned HTTP {e.code}. Check the key, model access and usage limits. No actions ran.")
        error.provider_status=e.code  # lets callers retry rate limits and server errors only
        raise error from None
    except (urllib.error.URLError,TimeoutError,ConnectionError):
        error=RelayError('PROVIDER_UNAVAILABLE',f"{config['name']} could not be reached or timed out. No actions ran.")
        error.provider_status=None
        raise error from None

def models(cfg, provider):
    config=settings(cfg,provider)
    raw=request(config,'/api/tags' if provider=='ollama' else '/models')
    ids=sorted(set(x.get('name' if provider=='ollama' else 'id','') for x in raw.get('models' if provider=='ollama' else 'data',[]) if isinstance(x,dict)))
    return {'provider':provider,'models':[m for m in ids if m],'default':config['model']}

def complete(cfg,provider,model,messages,max_tokens=8000,timeout=90):
    config=settings(cfg,provider)
    if provider=='ollama':
        raw=request(config,'/api/chat',{'model':model,'messages':messages,'stream':False,'format':'json','options':{'temperature':0.2,'num_predict':max_tokens}},timeout)
        p,c=raw.get('prompt_eval_count',0),raw.get('eval_count',0)
        return raw.get('message',{}).get('content'),{'prompt_tokens':p,'completion_tokens':c,'total_tokens':p+c}
    raw=request(config,'/chat/completions',{'model':model,'messages':messages,'temperature':0.2,'max_tokens':max_tokens,'response_format':{'type':'json_object'}},timeout)
    choice=raw.get('choices',[{}])[0]
    usage=dict(raw.get('usage') or {}); usage['finish_reason']=choice.get('finish_reason')
    return choice.get('message',{}).get('content'),usage
