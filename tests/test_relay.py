import copy, json, tempfile, threading, time, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from relay.core import Store, RelayError, validate_plan, digest, generate_plan
from relay.server import make_handler

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.store=Store(self.root)
        (self.store.inbox/'notes.md').write_text('Maya will prepare onboarding by Friday. Decision: private beta.')
    def tearDown(self):
        deadline=time.monotonic()+3
        while self.store.active and time.monotonic()<deadline: time.sleep(.01)
        self.temp.cleanup()
    def plan(self):
        run=self.store.create('Create a brief',['file:notes.md'],'demo')
        self.wait(run,'review'); return run
    def wait(self,run,status):
        deadline=time.monotonic()+3
        while run['status'] not in (status,'failed') and time.monotonic()<deadline: time.sleep(.01)
        self.assertEqual(run['status'],status,run.get('error'))
    def test_no_files_before_approval_then_exact_verified_outputs(self):
        run=self.plan(); self.assertEqual(list(self.store.outbox.iterdir()),[])
        self.store.approve(run['id'],run['revision']); self.wait(run,'complete')
        self.assertEqual(len(run['outputs']),2)
        for output in run['outputs']:
            actual=(self.root/output['path']).read_text()
            self.assertEqual(digest(actual),output['sha256'])
            self.assertEqual(actual,run['plan']['steps'][output['step']]['content'])
    def test_human_edit_is_executed(self):
        run=self.plan(); self.store.edit(run['id'],1,0,'# Human correction\n')
        self.assertEqual(run['revision'],2)
        self.store.approve(run['id'],2);self.wait(run,'complete')
        self.assertEqual((self.root/run['outputs'][0]['path']).read_text(),'# Human correction\n')
    def test_stale_revision_rejected(self):
        run=self.plan();self.store.edit(run['id'],1,0,'Updated')
        with self.assertRaisesRegex(RelayError,'another window'):self.store.approve(run['id'],1)
        self.assertEqual(run['status'],'review')
    def test_changed_source_blocks_execution(self):
        run=self.plan();(self.store.inbox/'notes.md').write_text('Human changed their mind')
        with self.assertRaisesRegex(RelayError,'source changed'):self.store.approve(run['id'],1)
        self.assertEqual(list(self.store.outbox.iterdir()),[])
    def test_removed_source_blocks_execution(self):
        run=self.plan();(self.store.inbox/'notes.md').unlink()
        with self.assertRaises(RelayError):self.store.approve(run['id'],1)
    def test_double_approval_does_not_duplicate(self):
        run=self.plan();self.store.approve(run['id'],1)
        with self.assertRaises(RelayError):self.store.approve(run['id'],1)
        self.wait(run,'complete');self.assertEqual(len(list(self.store.outbox.iterdir())),1)
    def test_rejection_cannot_execute(self):
        run=self.plan();self.store.reject(run['id'],1,'Use a checklist')
        self.assertEqual(run['feedback'],'Use a checklist')
        with self.assertRaises(RelayError):self.store.approve(run['id'],1)
    def test_path_traversal_rejected(self):
        run=self.plan()
        for name in ('../../.env','/tmp/x.md','x.sh','../x.md','x/brief.md'):
            p=copy.deepcopy(run['plan']);p['steps'][0]['filename']=name
            with self.assertRaises(RelayError):validate_plan(p)
    def test_malformed_csv_and_json_rejected(self):
        for name,content in [('bad.csv','# comment\nOwner,Task\nMaya,Write'),('bad.json','{invalid}')]:
            with self.assertRaises(RelayError):validate_plan({'title':'Formats','steps':[{'kind':'write_file','title':'Save','filename':name,'content':content}]})
    def test_valid_csv_source_column(self):
        validate_plan({'title':'Formats','steps':[{'kind':'write_file','title':'Save','filename':'good.csv','content':'Owner,Task,Source\nMaya,Write,notes.md'}]})
    def test_duplicate_outputs_rejected(self):
        run=self.plan();p=copy.deepcopy(run['plan']);p['steps'][1]['filename']='RESEARCH-BRIEF.md'
        with self.assertRaises(RelayError):validate_plan(p)
    def test_arbitrary_commands_rejected(self):
        with self.assertRaises(RelayError):validate_plan({'title':'Unsafe','steps':[{'kind':'shell','title':'Run','command':'rm'}]})
    def test_dangerous_urls_rejected(self):
        run=self.plan()
        for url in ('file:///etc/passwd','javascript:alert(1)','http://example.com','https://user:pass@example.com'):
            p=copy.deepcopy(run['plan']);p['steps'].append({'kind':'open_url','title':'Open','url':url})
            with self.assertRaises(RelayError):validate_plan(p)
    def test_symlink_source_ignored(self):
        (self.store.inbox/'linked.md').symlink_to(self.store.inbox/'notes.md')
        self.assertEqual(len(self.store.sources()),1)
    def test_existing_output_folder_never_overwritten(self):
        run=self.plan();folder=self.store.outbox/run['id'];folder.mkdir();(folder/'research-brief.md').write_text('KEEP')
        self.store.approve(run['id'],1);self.wait(run,'failed')
        self.assertEqual((folder/'research-brief.md').read_text(),'KEEP')
    def test_restart_recovers_interrupted_workflow(self):
        run=self.plan();run['status']='running';self.store.save();restored=Store(self.root)
        self.assertEqual(restored.run(run['id'])['status'],'interrupted')
    def test_no_key_not_silently_demonstrated(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaisesRegex(RelayError,'NEBIUS_API_KEY'):self.store.create('Make a brief',['file:notes.md'],'live')
    def test_sources_limit_and_missing_sources(self):
        for sources in ([],['missing'],['file:notes.md']*9):
            with self.assertRaises(RelayError):self.store.create('Make a brief',sources,'demo')
    def test_provider_repairs_invalid_json(self):
        run=self.plan();calls=[];logs=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,*a):
                return json.dumps({'choices':[{'message':{'content':'bad json' if len(calls)==1 else json.dumps(run['plan'])}}],'usage':{'total_tokens':123}}).encode()
        def fake(req,timeout): calls.append(json.loads(req.data));return Response()
        with patch.dict('os.environ',{'NEBIUS_API_KEY':'test'},clear=True),patch('urllib.request.urlopen',fake):
            plan,model,usage=generate_plan(self.root,run,lambda *a:logs.append(a))
        self.assertEqual(len(calls),2);self.assertEqual(usage['total_tokens'],246)
        self.assertIn('validation',calls[1]['messages'][-1]['content']);self.assertTrue(model.startswith('nvidia/'))
    def test_provider_errors_are_not_demo_success(self):
        run=self.plan()
        with patch.dict('os.environ',{'NEBIUS_API_KEY':'secret'},clear=True),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('u',401,'Unauthorized',{},None)):
            with self.assertRaisesRegex(RelayError,'HTTP 401'):generate_plan(self.root,run,lambda *a:None)
    def test_unofficial_endpoint_rejected(self):
        run=self.plan()
        with patch.dict('os.environ',{'NEBIUS_API_KEY':'secret','NEBIUS_BASE_URL':'https://evil.test/v1'},clear=True):
            with self.assertRaisesRegex(RelayError,'official Nebius'):generate_plan(self.root,run,lambda *a:None)

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),lambda *a:None)
        self.port=self.server.server_address[1];self.server.RequestHandlerClass=make_handler(self.store,self.port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def req(self,path,data=None,headers=None):
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
        try:
            with urllib.request.urlopen(req) as res:return res.status,res.read(),dict(res.headers)
        except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
    def test_cross_site_state_read_blocked(self):
        code,_,_=self.req('/api/state',headers={'Origin':'https://evil.test'});self.assertEqual(code,403)
    def test_dns_rebinding_host_blocked(self):
        code,_,_=self.req('/api/state',headers={'Host':'evil.test'});self.assertEqual(code,403)
    def test_no_token_blocks_mutation(self):
        code,_,_=self.req('/api/clips',{'name':'n','content':'a'}, {'Content-Type':'application/json'});self.assertEqual(code,403)
    def test_extension_pair_can_only_add_source(self):
        headers={'Content-Type':'application/json','Origin':'chrome-extension://example','Authorization':'Bearer '+self.store.pair_token}
        code,body,_=self.req('/api/clips',{'name':'n','content':'a'},headers);self.assertEqual(code,200)
        code,_,_=self.req('/api/approve',{'id':'any'},headers);self.assertEqual(code,403)
    def test_html_navigation_and_static_assets(self):
        code,body,_=self.req('/',headers={'Sec-Fetch-Site':'cross-site'});self.assertEqual(code,200);self.assertIn(b'Relay',body)
        code,_,_=self.req('/app.js');self.assertEqual(code,200)
    def test_cross_site_fetch_and_path_traversal(self):
        code,_,_=self.req('/api/state',headers={'Sec-Fetch-Site':'cross-site'});self.assertEqual(code,403)
        code,_,_=self.req('/%2e%2e/.env');self.assertEqual(code,404)
    def test_valid_source_write(self):
        code,_,_=self.req('/api/clips',{'name':'note','content':'text'},{'Content-Type':'application/json','Authorization':'Bearer '+self.store.token})
        self.assertEqual(code,200);self.assertEqual(len(self.store.sources()),1)

if __name__=='__main__':unittest.main()
