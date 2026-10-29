import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from relay import extraction,semantics
from relay.research import Research,validate_analysis,compare
from test_semantics import fixture,assessment

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Research(Path(self.tmp.name));self.papers=fixture();self.paper=self.papers[0]
        self.source=self.paper['metrics'][0]['quote'];self.result=copy.deepcopy(self.paper['metrics'][0]);self.paper['metrics']=[]
        self.p={'id':'a'*16,'papers':[self.paper],'protocol':self.paper['protocol'],'hypothesis':'Compare two approaches under a common study context','model':'test','revision':1,'status':'discovering','resultLimit':'all','tokens':0,'events':[]}
        self.r.projects=[self.p]
    def tearDown(self):self.tmp.cleanup()
    def run_extract(self,ask,source=None,chunks=None):
        with patch.object(self.r,'source',return_value=source or self.source),patch.object(self.r,'llm',side_effect=ask),patch.object(self.r,'checkpoint'),patch.object(self.r,'event'):
            if chunks is None:self.r.assess(self.p,self.paper)
            else:
                with patch('relay.research.extraction.passages',return_value=chunks):self.r.assess(self.p,self.paper)
    def test_passages_cover_every_character_without_disconnected_sampling(self):
        text=('A long section about arbitrary subject matter.\n'*1300)+'UNIQUE END RESULT'
        chunks=extraction.passages(text)
        self.assertEqual(extraction.covered_chars(chunks),len(text))
        self.assertTrue(all(text[c['start']:c['end']]==c['text'] for c in chunks))
        self.assertTrue(any('UNIQUE END RESULT' in c['text'] for c in chunks))
    def test_failed_repair_keeps_valid_first_pass_result(self):
        def ask(p,system,payload,kind,*args):
            if kind=='assess':return {'relevance':80,'rationale':'Relevant'}
            if kind=='extract-passage':return {'metrics':[self.result,dict(self.result,quote='A fabricated passage with 99.',value='99')]}
            if kind=='extract-repair':raise RuntimeError('Provider failed during repair')
            self.fail(kind)
        self.run_extract(ask)
        self.assertEqual(len(self.paper['metrics']),1)
        self.assertEqual(self.paper['coverage']['status'],'complete')
        self.assertEqual(self.paper['coverage']['rejected'],1)
        self.assertIn('repairError',self.paper['coverage']['attempts'][0])
    def test_no_source_does_not_spend_model_tokens(self):
        with patch.object(self.r,'source',return_value=''),patch.object(self.r,'llm') as model,patch.object(self.r,'checkpoint'):
            self.r.assess(self.p,self.paper)
        model.assert_not_called();self.assertEqual(self.paper['coverage']['status'],'no_text')
    def test_partial_failure_can_resume_without_reading_successful_passages_again(self):
        second=dict(self.result,method='Different source label',quote='Different source label reported 43 for adult participants in the north.',value='43')
        source=self.source+'\n'+second['quote'];chunks=[{'id':'one','start':0,'end':len(self.source),'text':self.source},{'id':'two','start':len(self.source),'end':len(source),'text':second['quote']}]
        def first(p,system,payload,kind,*args):
            if kind=='assess':return {'relevance':80,'rationale':'Relevant'}
            if payload['passage']['id']=='one':return {'metrics':[self.result]}
            raise RuntimeError('transient source-extraction failure')
        self.run_extract(first,source,chunks)
        self.assertEqual(self.paper['coverage']['status'],'partial');self.assertEqual(len(self.paper['metrics']),1)
        called=[]
        def retry(p,system,payload,kind,*args):
            called.append(payload['passage']['id']);return {'metrics':[second]}
        self.run_extract(retry,source,chunks)
        self.assertEqual(called,['two']);self.assertEqual(len(self.paper['metrics']),2)
        self.assertEqual(self.paper['coverage']['readPassages'],2);self.assertEqual(self.paper['coverage']['status'],'complete')
    def test_selected_limit_reports_partial_coverage_and_all_continues(self):
        self.p['resultLimit']=1
        second=dict(self.result,method='Second',quote='Second reported 43 for adult participants in the north.',value='43')
        source=self.source+'\n'+second['quote'];chunks=[{'id':'one','start':0,'end':len(self.source),'text':self.source},{'id':'two','start':len(self.source),'end':len(source),'text':second['quote']}]
        def ask(p,system,payload,kind,*args):
            return {'relevance':80,'rationale':'Relevant'} if kind=='assess' else {'metrics':[self.result if payload['passage']['id']=='one' else second]}
        self.run_extract(ask,source,chunks)
        self.assertEqual(self.paper['coverage']['status'],'partial');self.assertIn('count reached',self.paper['coverage']['stopReason'])
        self.p['resultLimit']='all';self.run_extract(ask,source,chunks)
        self.assertEqual(len(self.paper['metrics']),2);self.assertEqual(self.paper['coverage']['status'],'complete')
    def test_short_table_row_is_not_rejected_by_arbitrary_length(self):
        raw=dict(self.result,method='A',value='42',quote='| A | 42 |')
        p={'id':'p','protocol':self.p['protocol']};validate_analysis(p,{'metrics':[raw]},raw['quote'])
        self.assertEqual(len(p['metrics']),1)
    def test_explicit_distinction_is_required_not_optional_context(self):
        c=copy.deepcopy(self.p['protocol']);question='Compare approaches and distinguish location.'
        raw={'complete':True,'requirements':[{'quote':'distinguish location','criteria':['factor_location'],'role':'stratify','covered':True}],'gaps':[]}
        semantics.apply_plan_review(c,raw,question)
        self.assertEqual(c['factors'][1]['role'],'stratify');self.assertTrue(c['planReview']['complete'])
        papers=fixture()
        for paper in papers:paper['metrics'][0]['protocol']=c
        papers[0]['metrics'][0]['factor_location']='unknown'
        pair=semantics.candidate_pairs(papers)[1][0]
        record=semantics.validate_assessment(pair,assessment(pair),'test')
        self.assertEqual(semantics.render_pair(pair,record)['outcome'],'insufficient')
    def test_invented_requirement_quote_does_not_pass_coverage_review(self):
        c=copy.deepcopy(self.p['protocol'])
        semantics.apply_plan_review(c,{'complete':True,'requirements':[{'quote':'invented condition','criteria':['measurement'],'covered':True}]},self.p['hypothesis'])
        self.assertFalse(c['planReview']['complete'])
    def test_contract_review_is_required_for_verified_claim(self):
        papers=fixture();c=papers[0]['metrics'][0]['protocol'];c.update(question='Compare methods',planReview={'complete':True})
        papers[1]['metrics'][0]['protocol']=copy.deepcopy(c)
        pair=semantics.candidate_pairs(papers)[1][0];record=semantics.validate_assessment(pair,assessment(pair),'test');record['reviewed']=True;record['sourceReview']=copy.deepcopy(record)
        results=compare(papers,assessments={pair['id']:record})
        self.assertFalse(results['pairs'][0]['verified'])
        results=compare(papers,assessments={pair['id']:record},contract_review={'approved':True,'fingerprint':semantics.digest(c)})
        self.assertTrue(results['pairs'][0]['verified'])
    def test_source_address_resolves_exact_row_without_rewriting_cells(self):
        source='A study\n| Method | Outcome |\n| Approach A | 42 |\n'
        lines=extraction.indexed_lines(source)
        result=extraction.ground_output({'metrics':[{'method':'Approach A','value':'42','quote':'Approach A scored 42','valueLocation':{'line':'L3','column':2},'quoteLines':['L2','L3']}]},lines)
        m=result['metrics'][0]
        self.assertEqual(m['quote'],'| Approach A | 42 |');self.assertEqual(len(m['sourceEvidence']),2)
    def test_wrong_table_column_cannot_fall_back_to_a_different_value_in_row(self):
        source='| A | 42 | 43 |\n';lines=extraction.indexed_lines(source)
        result=extraction.ground_output({'metrics':[dict(self.result,value='43',quote='| A | 42 | 43 |',valueLocation={'line':'L1','column':2})]},lines)
        p={'id':'x','protocol':self.p['protocol']};validate_analysis(p,result,source)
        self.assertEqual(p['metrics'],[]);self.assertIn('addressed source cell',p['rejectionDetails'][0]['reason'])
    def test_model_cannot_cite_a_line_outside_supplied_passage(self):
        lines=extraction.indexed_lines('first\nsecond has 42\n')
        result=extraction.ground_output({'metrics':[{'value':'42','valueLocation':{'line':'L2','column':None}}]},lines,{'L1'})
        self.assertIn('not supplied',result['metrics'][0]['groundingError'])
    def test_unresolved_plan_stops_before_retrieval_or_extraction(self):
        with patch.object(self.r,'plan_protocol',return_value=False),patch('relay.research.referenced_paper') as fetch,patch.object(self.r,'assess') as assess:
            self.r.run(self.p)
        fetch.assert_not_called();assess.assert_not_called()
    def test_outside_scope_observations_stay_saved_but_are_not_paired(self):
        papers=fixture();c=papers[0]['metrics'][0]['protocol'];c['outcomes']=[{'id':'o1','label':'Requested finding','definition':'Requested population'}]
        for paper in papers:
            m=paper['metrics'][0];m['protocol']=copy.deepcopy(c);m['outcomeId']='o1';m['outcomeQuote']=m['quote']
        papers[0]['metrics'][0]['outcomeId']='outside_scope'
        result=semantics.compare(papers)
        self.assertEqual(result['outsideScopeResults'],1);self.assertEqual(result['pairs'],[])
        self.assertEqual(sum(len(p['metrics']) for p in papers),2)
    def test_not_applicable_measurement_cannot_be_a_green_comparison(self):
        pair=semantics.candidate_pairs(fixture())[1][0];raw=assessment(pair)
        raw['checks'][1]['status']='not_applicable'
        result=semantics.render_pair(pair,semantics.validate_assessment(pair,raw,'test'))
        self.assertEqual(result['outcome'],'insufficient')
    def test_replan_keeps_raw_observations_and_resets_semantic_review(self):
        self.paper['metrics']=[copy.deepcopy(self.result)];before=copy.deepcopy(self.paper['metrics'])
        with patch.object(self.r,'source',return_value=self.source),patch.object(self.r,'complete_context'),patch.object(self.r,'checkpoint'):
            self.r.rebind_evidence(self.p)
        after=self.paper['metrics']
        self.assertEqual([(m['value'],m['quote']) for m in before],[(m['value'],m['quote']) for m in after])
        self.assertFalse(after[0]['verified']);self.assertEqual(after[0]['entityId'],'unknown')
    def test_agent_cannot_approve_question_coverage_as_human(self):
        self.p['status']='review';self.p['protocol']['planReview']={'complete':True}
        with patch.object(self.r,'checkpoint'):
            self.r.review_contract({'id':self.p['id'],'revision':1,'approved':True,'actor':'agent'})
        self.assertFalse(self.p['contractReview']['approved'])

    def test_factor_object_shape_preserves_model_defined_values(self):
        raw=copy.deepcopy(self.p['protocol'])
        raw['factors']={f['key']:dict(f) for f in raw['factors']}
        canonical=semantics.contract(raw)
        self.assertEqual(canonical['factors'],self.p['protocol']['factors'])
    def test_reextraction_marks_existing_cited_claims_stale(self):
        self.p['draft']={'relatedWork':[{'citations':[self.paper['id']],'text':'A prior claim'}]}
        self.p['draftReviewed']=True
        def ask(p,system,payload,kind,*args):
            return {'metrics':[self.result]} if kind=='extract-passage' else {'relevance':80}
        self.run_extract(ask)
        self.assertTrue(self.p['draft']['relatedWork'][0]['stale'])
        self.assertFalse(self.p['draftReviewed'])

    def test_context_reference_resolves_source_text_without_model_requotation(self):
        m=copy.deepcopy(self.result);m['entityId']='unknown';m['entityQuote']='';self.paper['coverage']={}
        def ask(p,system,payload,kind,*args):
            ref=payload['notes'][0]['id']
            return {'updates':[{'id':m['id'],'fields':{'entityId':'e1'},'references':{'entityId':ref}}]}
        with patch.object(self.r,'llm',side_effect=ask),patch.object(self.r,'event'):
            self.r.complete_context(self.p,self.paper,[m],[{'quote':self.source,'scopeQuote':self.source}],self.source)
        self.assertEqual(m['entityId'],'e1');self.assertEqual(m['entityQuote'],self.source)

    def test_import_retains_more_than_twenty_papers(self):
        p=copy.deepcopy(self.p)
        p['papers']=[dict(copy.deepcopy(self.paper),id='paper'+str(i)) for i in range(30)]
        self.r.projects=[]
        self.r.import_project({'format':'relay-research/1','project':p})
        self.assertEqual(len(self.r.get(p['id'])['papers']),30)

    def test_pending_pairs_are_not_counted_as_failed_comparisons(self):
        result=semantics.compare(fixture())
        self.assertEqual(result['summary']['pending'],1)
        self.assertEqual(result['summary']['insufficient'],0)
        self.assertEqual(result['summary']['assessed'],0)
    def test_unassessed_pairs_do_not_become_manuscript_findings(self):
        self.p['papers']=fixture()
        pairs,packet=self.r.evidence_packet(self.p,self.p['papers'])
        self.assertEqual(pairs,[]);self.assertEqual(packet,[])

    def test_zero_is_a_valid_observation_not_missing(self):
        raw=dict(self.result,value=0,quote='The result was 0 for this experiment.')
        p={'id':'p','protocol':self.p['protocol']};validate_analysis(p,{'metrics':[raw]},raw['quote'])
        self.assertEqual(p['metrics'][0]['value'],'0')
    def test_context_note_addresses_are_resolved_from_supplied_lines(self):
        source='A setup condition.\nA different experiment.\n'
        out=extraction.ground_output({'contextNotes':[{'line':'L1','scopeLine':'L1'},{'line':'L2'}]},extraction.indexed_lines(source),{'L1'})
        self.assertEqual(out['contextNotes'][0]['quote'],'A setup condition.')
        self.assertEqual(out['contextNotes'][1]['quote'],'')

    def test_failed_large_passage_is_retried_in_smaller_windows(self):
        source=self.source+'\n'+('Source background.\n'*800)
        seen=[]
        def ask(p,system,payload,kind,*args):
            if kind=='assess':return {'relevance':80}
            text='\n'.join(line['text'] for line in payload['passage']['lines'])
            seen.append(len(text))
            if len(text)>6000:raise ValueError('truncated response')
            return {'metrics':[self.result]} if self.source in text else {'metrics':[]}
        self.run_extract(ask,source)
        self.assertTrue(any(n>6000 for n in seen));self.assertTrue(any(n<6000 for n in seen))
        self.assertEqual(self.paper['coverage']['status'],'complete')
        self.assertEqual(len(self.paper['metrics']),1)

    def test_green_judgment_requires_separate_source_recheck(self):
        papers=fixture();c=papers[0]['metrics'][0]['protocol'];c.update(question='Compare these approaches',planReview={'complete':True})
        papers[1]['metrics'][0]['protocol']=copy.deepcopy(c)
        pair=semantics.candidate_pairs(papers)[1][0];record=semantics.validate_assessment(pair,assessment(pair),'test')
        self.assertEqual(semantics.render_pair(pair,record)['outcome'],'insufficient')
        review=copy.deepcopy(record);review['checks'][1]['status']='conflict';review['checks'][1]['detail']='Original table reports different outcome populations.'
        record['sourceReview']=review
        self.assertEqual(semantics.render_pair(pair,record)['outcome'],'incompatible')
