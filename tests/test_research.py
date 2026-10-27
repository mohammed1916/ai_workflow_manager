import copy, tempfile, unittest
from pathlib import Path
from relay.research import Research, abstract_text, validate_analysis, compare, manuscript
from relay.core import RelayError

class ResearchTests(unittest.TestCase):
    def paper(self,id='W1'):
        return {'id':id,'title':'Graph forecasts','year':2024,'authors':['A & B'],'url':'https://example.org/paper','reviewed':True,'evidence':'On PEMS04, the test MAE is 18.2 at 60 minutes.','metrics':[]}
    def metric(self):
        return {'name':'MAE','value':'18.2','dataset':'PEMS04','split':'60/20/20','horizon':'60 minutes','unit':'vehicles','protocol':'all nodes, standard scaling','direction':'lower','method':'Graph','quote':'On PEMS04, the test MAE is 18.2 at 60 minutes.','verified':True}
    def test_topic_normalization_is_idempotent(self):
        from relay.research import canonical_topic
        for topic in ('Graph + attention hybrids','Graph neural networks','Transformer models'):
            self.assertEqual(canonical_topic(canonical_topic(topic)),topic)
    def test_markdown_prose_becomes_escaped_latex(self):
        from relay.research import tex_prose
        text=tex_prose('### Design\n1. **Data**: A & B\n2. Evaluate.\n\nDone.')
        self.assertIn(r'\subsection{Design}',text)
        self.assertIn(r'\begin{enumerate}',text)
        self.assertIn(r'\textbf{Data}: A \& B',text)
        self.assertNotIn('**',text)
    def test_inverted_abstract(self):
        self.assertEqual(abstract_text({'world':[1],'Hello':[0]}),'Hello world')
    def test_rejects_fabricated_quote_and_value(self):
        p=self.paper();m=self.metric();m['value']='2.1'
        validate_analysis(p,{'metrics':[m]});self.assertEqual(p['metrics'],[])
        m=self.metric();m['quote']='Invented performance 18.2 is excellent.'
        validate_analysis(p,{'metrics':[m]});self.assertEqual(p['metrics'],[])
    def test_extraction_never_self_verifies(self):
        p=self.paper();validate_analysis(p,{'metrics':[self.metric()],'relevance':500})
        self.assertFalse(p['metrics'][0]['verified']);self.assertEqual(p['relevance'],100)
    def test_unknown_context_is_insufficient_not_incompatible(self):
        a,b=self.paper(),self.paper('W2');a['metrics']=[dict(self.metric(),id='1')];b['metrics']=[dict(self.metric(),id='2',split='unknown')]
        pair=compare([a,b])['pairs'][0]
        self.assertEqual(pair['outcome'],'insufficient');self.assertIsNone(pair['favours'])
    def test_matching_experiments_favour_lower_error(self):
        a,b=self.paper(),self.paper('W2');a['metrics']=[dict(self.metric(),id='1')];b['metrics']=[dict(self.metric(),id='2',value='19.5')]
        pair=compare([a,b])['pairs'][0]
        self.assertEqual(pair['outcome'],'comparable');self.assertEqual(pair['favours'],'a');self.assertTrue(pair['verified'])
        b['metrics'][0]['horizon']='15 minutes'
        result=compare([a,b])
        self.assertEqual(result['pairs'],[]);self.assertEqual(result['summary']['differentHorizon'],1)
    def test_same_paper_is_not_paired(self):
        p=self.paper();p['metrics']=[dict(self.metric(),id='1'),dict(self.metric(),id='2')]
        self.assertEqual(compare([p])['pairs'],[])
    def test_unverified_comparable_pair_is_marked_unverified(self):
        a,b=self.paper(),self.paper('W2');a['metrics']=[dict(self.metric(),id='1',verified=False)];b['metrics']=[dict(self.metric(),id='2',value='19.5')]
        pair=compare([a,b])['pairs'][0]
        self.assertFalse(pair['verified']);self.assertIn('not yet human-verified',pair['explanation'][0])
    def test_nan_is_not_ranked(self):
        a,b=self.paper(),self.paper('W2');a['metrics']=[dict(self.metric(),id='1')];b['metrics']=[dict(self.metric(),id='2',value='nan')]
        self.assertIsNone(compare([a,b])['pairs'][0]['favours'])
    def test_manuscript_escapes_tex_and_cites_known_papers(self):
        tex,bib=manuscript({'hypothesis':'Does A & B improve 5%?','papers':[self.paper()]},{'abstract':'Proposed study.','relatedWork':[{'text':'Prior work.','citations':['W1','fake']}],'study':'Evaluate.'})
        self.assertIn(r'A \& B',tex);self.assertIn(r'\cite{W1}',tex);self.assertNotIn('fake',tex);self.assertIn(r'A \& B',bib)
    def test_stale_review_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));r.projects=[{'id':'p','status':'review','revision':2,'papers':[self.paper()]}]
            with self.assertRaises(RelayError) as e:r.update({'id':'p','revision':1,'action':'review'})
            self.assertEqual(e.exception.code,'STALE_REVISION')
    def test_draft_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));p=self.paper();p['reviewed']=False
            r.projects=[{'id':'p','status':'review','revision':1,'papers':[p]}]
            with self.assertRaises(RelayError) as e:r.draft({'id':'p','revision':1})
            self.assertEqual(e.exception.code,'REVIEW_REQUIRED')
    def test_interrupted_agent_on_restart(self):
        with tempfile.TemporaryDirectory() as d:
            r=Research(Path(d));r.projects=[{'id':'p','status':'discovering','papers':[]}];r.save()
            self.assertEqual(Research(Path(d)).projects[0]['status'],'interrupted')

if __name__=='__main__':unittest.main()

class CompilerIsolationTests(unittest.TestCase):
    def test_compiler_can_render_but_cannot_read_sibling_file(self):
        import sys
        binary=Path(__file__).resolve().parents[1]/'.relay/bin/tectonic'
        if sys.platform!='darwin' or not binary.exists(): self.skipTest('Local macOS Tectonic not installed')
        from relay.latex import compile_tex
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d);(parent/'private.tex').write_text('THISISPRIVATE');folder=parent/'manuscript';folder.mkdir()
            for body,success in [('Public manuscript.',True),(r'\input{../private.tex}',False),(r'\input{'+str(parent/'private.tex')+'}',False)]:
                (folder/'main.tex').write_text(r'\documentclass{article}\begin{document}'+body+r'\end{document}')
                r=compile_tex(binary,folder,30)
                self.assertEqual(r.returncode==0,success,r.stderr)
