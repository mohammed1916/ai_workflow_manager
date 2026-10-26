from __future__ import annotations
import argparse, json, mimetypes, secrets, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .core import Store, RelayError, read_config, digest

ROOT=Path(__file__).resolve().parent.parent

def make_handler(store,port):
    origin=f'http://127.0.0.1:{port}'
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
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            request_origin=self.headers.get('Origin','')
            if self.path=='/api/clips' and request_origin.startswith('chrome-extension://'):
                self.send_header('Access-Control-Allow-Origin',request_origin)
                self.send_header('Vary','Origin')
            self.end_headers(); self.wfile.write(body)
        def guard(self,mutation=False):
            if self.headers.get('Host')!=f'127.0.0.1:{port}': raise RelayError('INVALID_HOST','Open Relay at '+origin,403)
            request_origin=self.headers.get('Origin','')
            extension=self.path=='/api/clips' and request_origin.startswith('chrome-extension://')
            if request_origin and request_origin!=origin and not extension: raise RelayError('ORIGIN_DENIED','This origin is not allowed.',403)
            if self.headers.get('Sec-Fetch-Site')=='cross-site' and not extension and (mutation or self.path.startswith('/api/')): raise RelayError('ORIGIN_DENIED','Cross-site access is not allowed.',403)
            if mutation:
                token=self.headers.get('Authorization','').removeprefix('Bearer ')
                expected=store.pair_token if extension else store.token
                if not secrets.compare_digest(token,expected): raise RelayError('UNAUTHORIZED','Refresh Relay or re-pair the extension.',403)
        def do_OPTIONS(self):
            if self.path!='/api/clips' or not self.headers.get('Origin','').startswith('chrome-extension://'):
                self.respond({'error':'Origin denied'},403); return
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
            self.send_header('Access-Control-Allow-Methods','POST')
            self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization')
            self.end_headers()
        def do_GET(self):
            try:
                self.guard()
                route=unquote(urlsplit(self.path).path)
                if route=='/api/state':
                    with store.lock:
                        cfg=read_config(store.root)
                        self.respond({'token':store.token,'providers':{'ollama':bool(cfg.get('OLLAMA_TEST_API_KEY') or cfg.get('OLLAMA_API_KEY')),'nebius':bool(cfg.get('NEBIUS_API_KEY'))},'configured':bool(cfg.get('NEBIUS_API_KEY') or cfg.get('OLLAMA_TEST_API_KEY') or cfg.get('OLLAMA_API_KEY')),'model':cfg.get('NEBIUS_MODEL','nvidia/nemotron-3-super-120b-a12b'),'platform':sys.platform,'sources':store.sources(),'runs':store.state['runs']})
                elif route=='/api/models':
                    from .providers import models
                    from urllib.parse import parse_qs
                    provider=parse_qs(urlsplit(self.path).query).get('provider',['ollama'])[0]
                    self.respond(models(read_config(store.root),provider))
                elif route=='/api/pair': self.respond({'token':store.pair_token,'endpoint':origin})
                elif route.startswith('/api/output/'):
                    parts=route.split('/')
                    if len(parts)!=5: raise RelayError('NOT_FOUND','File not found.',404)
                    with store.lock:
                        run=store.run(parts[3]); item=next((o for o in run['outputs'] if o['filename']==parts[4]),None)
                        if not item: raise RelayError('NOT_FOUND','File not found.',404)
                        path=store.root/item['path']
                        if path.is_symlink() or not path.resolve().is_relative_to(store.outbox.resolve()): raise RelayError('INVALID_PATH','Unsafe output path.',403)
                        self.respond(path.read_bytes(),content_type='application/zip' if path.suffix=='.zip' else 'text/plain; charset=utf-8')
                else:
                    path=ROOT/'web'/('index.html' if route=='/' else route.lstrip('/'))
                    if not path.resolve().is_relative_to((ROOT/'web').resolve()) or not path.is_file(): raise RelayError('NOT_FOUND','Page not found.',404)
                    self.respond(path.read_bytes(),content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            except RelayError as e: self.respond({'error':str(e),'code':e.code},e.status)
            except Exception: self.respond({'error':'Could not read the requested resource.','code':'READ_ERROR'},500)
        def do_POST(self):
            try:
                self.guard(True)
                if 'application/json' not in self.headers.get('Content-Type',''): raise RelayError('INVALID_CONTENT_TYPE','Use JSON.')
                size=int(self.headers.get('Content-Length',0))
                if size<1 or size>300000: raise RelayError('BODY_LIMIT','Request body too large or empty.',413)
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise RelayError('INVALID_BODY','Use a JSON object.')
                if self.path=='/api/clips': result=store.add_clip(data)
                elif self.path=='/api/sources/remove':
                    with store.lock:
                        store.state['clips']=[s for s in store.state['clips'] if s['id']!=data.get('id')]; store.save(); result={'ok':True}
                elif self.path=='/api/runs': result=store.create(data.get('goal'),data.get('sources'),data.get('mode'),data.get('recipe','brief'),data.get('feedback',''),data.get('provider','nebius'),data.get('model'))
                elif self.path=='/api/approve': result=store.approve(data.get('id'),data.get('revision'))
                elif self.path=='/api/edit': result=store.edit(data.get('id'),data.get('revision'),data.get('index'),data.get('content'))
                elif self.path=='/api/reject': result=store.reject(data.get('id'),data.get('revision'),data.get('reason',''))
                elif self.path=='/api/cancel': result=store.cancel(data.get('id'))
                elif self.path=='/api/reveal':
                    if sys.platform!='darwin': raise RelayError('MAC_REQUIRED','Finder requires macOS.')
                    with store.lock:
                        run=store.run(data.get('id'))
                        if not run['outputs']: raise RelayError('NO_OUTPUT','This workflow has no saved files.')
                        path=store.outbox/run['id']
                        if path.is_symlink() or not path.exists(): raise RelayError('MISSING_OUTPUT','Output folder is missing.')
                        subprocess.run(['/usr/bin/open',str(path)],check=True,timeout=10)
                    result={'ok':True}
                else: raise RelayError('NOT_FOUND','Unknown action.',404)
                self.respond(result)
            except RelayError as e: self.respond({'error':str(e),'code':e.code},e.status)
            except (ValueError,TypeError): self.respond({'error':'Invalid request.','code':'INVALID_BODY'},400)
            except Exception: self.respond({'error':'The operation failed. Existing outputs have been preserved.','code':'OPERATION_FAILED'},500)
    return Handler

def main():
    parser=argparse.ArgumentParser(description='Relay local workflow companion')
    parser.add_argument('--port',type=int,default=int(read_config(ROOT).get('RELAY_PORT','4280')))
    args=parser.parse_args()
    store=Store(ROOT)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(store,args.port))
    print(f'Relay is ready at http://127.0.0.1:{args.port}',flush=True)
    print('Local only. API keys stay on the companion. Ctrl+C to stop.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
if __name__=='__main__': main()
