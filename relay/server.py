from __future__ import annotations
import argparse, json, mimetypes, os, re, secrets, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .core import RelayError, read_config
from types import SimpleNamespace
from .providers import with_key

ROOT=Path(__file__).resolve().parent.parent

def make_handler(store,port):
    from .research import Research, compare
    research=Research(store.root)
    origin=f'http://127.0.0.1:{port}'
    hosts={f'127.0.0.1:{port}', f'localhost:{port}'}
    origins={f'http://{h}' for h in hosts}
    public=os.environ.get('RELAY_PUBLIC_HOST','').strip()
    if public: hosts.add(public); origins.update({f'https://{public}', f'http://{public}'})
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def respond(self,data,status=200,content_type='application/json'):
            body=json.dumps(data).encode() if content_type=='application/json' else data
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"frame-ancestors 'self'" if content_type=='application/pdf' else "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'")
            self.end_headers(); self.wfile.write(body)
        def guard(self,mutation=False):
            if self.headers.get('Host') not in hosts: raise RelayError('INVALID_HOST','Open Relay at '+origin,403)
            request_origin=self.headers.get('Origin','')
            if request_origin and request_origin not in origins: raise RelayError('ORIGIN_DENIED','This origin is not allowed.',403)
            if self.headers.get('Sec-Fetch-Site')=='cross-site' and (mutation or self.path.startswith('/api/')): raise RelayError('ORIGIN_DENIED','Cross-site access is not allowed.',403)
            if mutation:
                token=self.headers.get('Authorization','').removeprefix('Bearer ')
                expected=store.token
                if not secrets.compare_digest(token,expected): raise RelayError('UNAUTHORIZED','Refresh Relay to renew the session token.',403)
        def do_GET(self):
            try:
                self.guard()
                route=unquote(urlsplit(self.path).path)
                if route=='/api/state':
                    cfg=read_config(store.root)
                    self.respond({'token':store.token,'providers':{'ollama':bool(cfg.get('OLLAMA_TEST_API_KEY') or cfg.get('OLLAMA_API_KEY')),'nebius':bool(cfg.get('NEBIUS_API_KEY'))},'configured':bool(cfg.get('NEBIUS_API_KEY') or cfg.get('OLLAMA_TEST_API_KEY') or cfg.get('OLLAMA_API_KEY')),'model':cfg.get('NEBIUS_MODEL','nvidia/nemotron-3-super-120b-a12b'),'platform':sys.platform,'hosted':os.environ.get('RELAY_HOSTED')=='1'})
                elif route=='/api/desk':
                    from .desk import overview
                    self.respond(overview(store.root,research))
                elif route=='/api/submission/export':
                    from scripts.package_submission import build
                    path,_=build()
                    self.respond(path.read_bytes(),content_type='application/zip')
                elif route=='/api/schema':
                    from .desk import schema
                    self.respond(schema())
                elif route=='/api/research/source':
                    from urllib.parse import parse_qs
                    from .core import digest
                    q=parse_qs(urlsplit(self.path).query)
                    with research.lock:
                        paper=research.paper(research.get(q.get('id',[''])[0]),q.get('paper',[''])[0])
                        text=research.source(paper)
                        self.respond({'text':text,'sha256':digest(text),'url':paper.get('evidenceUrl'),'kind':paper.get('evidenceKind')})
                elif route=='/README.md': self.respond((ROOT/'README.md').read_bytes(),content_type='text/plain; charset=utf-8')
                elif route=='/api/research/samples': self.respond(research.samples())
                elif route=='/api/research':
                    # Only projects the browser names by id are returned; nothing is listed globally.
                    from urllib.parse import parse_qs
                    wanted=[x for x in parse_qs(urlsplit(self.path).query).get('ids',[''])[0].split(',') if re.fullmatch(r'[a-f0-9]{16}',x)][:200]
                    self.respond(research.state(wanted))
                elif route=='/api/research/checkpoint':
                    from urllib.parse import parse_qs
                    q=parse_qs(urlsplit(self.path).query)
                    self.respond(research.inspect_checkpoint(q.get('id',[''])[0],q.get('node',[''])[0]))
                elif route=='/api/research/project':
                    from urllib.parse import parse_qs
                    pid=parse_qs(urlsplit(self.path).query).get('id',[''])[0]
                    if not re.fullmatch(r'[a-f0-9]{16}',pid): raise RelayError('NOT_FOUND','Research project not found.',404)
                    self.respond(research.export_project(pid))
                elif route.startswith('/api/research/export/'):
                    self.respond(research.bundle(route.split('/')[-1]),content_type='application/zip')
                elif route.startswith('/api/research/pdf/'):
                    parts=route.split('/')
                    if len(parts)!=6 or not all(__import__('re').fullmatch(r'[a-f0-9]{16}',x) for x in parts[4:]): raise RelayError('NOT_FOUND','PDF not found.',404)
                    path=store.root/'.relay/latex'/parts[4]/parts[5]/'main.pdf'
                    if not path.is_file(): raise RelayError('NOT_FOUND','PDF not found.',404)
                    self.respond(path.read_bytes(),content_type='application/pdf')
                elif route=='/api/models':
                    from .providers import models
                    from urllib.parse import parse_qs
                    provider=parse_qs(urlsplit(self.path).query).get('provider',['ollama'])[0]
                    hk=self.headers.get('X-Provider-Key','').strip() if self.headers.get('X-Provider','')==provider else ''
                    self.respond(models(with_key(read_config(store.root),provider,hk or None),provider))
                else:
                    path=ROOT/'web'/('research.html' if route in ('/','/index.html') else route.lstrip('/'))
                    if not path.resolve().is_relative_to((ROOT/'web').resolve()) or not path.is_file(): raise RelayError('NOT_FOUND','Page not found.',404)
                    self.respond(path.read_bytes(),content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            except RelayError as e: self.respond({'error':str(e),'code':e.code},e.status)
            except Exception: self.respond({'error':'Could not read the requested resource.','code':'READ_ERROR'},500)
        def do_POST(self):
            try:
                self.guard(True)
                if 'application/json' not in self.headers.get('Content-Type',''): raise RelayError('INVALID_CONTENT_TYPE','Use JSON.')
                size=int(self.headers.get('Content-Length',0))
                limit=8000000 if self.path=='/api/research/import' else 300000
                if size<1 or size>limit: raise RelayError('BODY_LIMIT','Request body too large or empty.',413)
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise RelayError('INVALID_BODY','Use a JSON object.')
                key=self.headers.get('X-Provider-Key','').strip(); provider=self.headers.get('X-Provider','nebius').strip()
                if key and (provider not in ('nebius','ollama') or len(key)>400): raise RelayError('INVALID_KEY','Check the provider and key.',400)
                tkey=self.headers.get('X-Tavily-Key','').strip()
                if tkey and len(tkey)>400: raise RelayError('INVALID_KEY','Check the Tavily key.',400)
                if self.path.startswith('/api/research/'):
                    if self.path=='/api/research/start':
                        if key: data['providerKey']=key
                        if tkey: data['tavilyKey']=tkey
                    elif data.get('id'):
                        if key: research.set_key(data['id'],provider,key)
                        if tkey: research.set_key(data['id'],'tavily',tkey)
                if self.path=='/api/desk/load':
                    from .desk import load_study, load_discovery
                    result=load_discovery(store.root,research) if data.get('study')=='discovery' else load_study(store.root,research)
                elif self.path=='/api/research/start': result=research.start(data)
                elif self.path=='/api/research/branch': result=research.branch(data)
                elif self.path=='/api/research/update': result=research.update(data)
                elif self.path=='/api/research/draft': result=research.draft(data)
                elif self.path=='/api/research/import': result=research.import_project(data)
                elif self.path=='/api/research/investigate': result=research.investigate(data)
                elif self.path=='/api/research/regenerate': result=research.regenerate(data)
                elif self.path=='/api/research/compile': result=research.compile(data)
                elif self.path=='/api/research/compare':
                    with research.lock:
                        p=research.get(data.get('id')); chosen=set(data.get('papers') or [])
                        methods=data.get('methods')
                        if methods is not None and (not isinstance(methods,list) or len(methods) not in (0,2) or any(not isinstance(x,str) or not x.strip() or len(x)>80 for x in methods)): raise RelayError('INVALID_SCOPE','Use two model family names or clear the model filter.')
                        result=compare(p['papers'],chosen if len(chosen)>=2 else None,methods)
                else: raise RelayError('NOT_FOUND','Unknown action.',404)
                self.respond(result)
            except RelayError as e: self.respond({'error':str(e),'code':e.code},e.status)
            except (ValueError,TypeError): self.respond({'error':'Invalid request.','code':'INVALID_BODY'},400)
            except Exception: self.respond({'error':'The operation failed. Existing outputs have been preserved.','code':'OPERATION_FAILED'},500)
    return Handler

def main():
    parser=argparse.ArgumentParser(description='Relay local workflow companion')
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT') or read_config(ROOT).get('RELAY_PORT','4280')))
    args=parser.parse_args()
    store=SimpleNamespace(root=ROOT,token=secrets.token_urlsafe(32))
    server=ThreadingHTTPServer((os.environ.get('RELAY_HOST','127.0.0.1'),args.port),make_handler(store,args.port))
    print(f'Relay is ready at http://127.0.0.1:{args.port}',flush=True)
    print('Local only. API keys stay on the companion. Ctrl+C to stop.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
if __name__=='__main__': main()
