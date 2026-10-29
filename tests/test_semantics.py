"""Controlled fixtures test generic safeguards, not scientific accuracy."""
import copy
import unittest
from unittest.mock import patch
from relay import semantics as s
from relay.research import validate_analysis, compare, referenced_paper


def fixture(topic='materials', finding='42'):
    protocol=s.contract({'task':topic,'entities':[{'label':'Approach A','definition':'First intervention'},{'label':'Approach B','definition':'Second intervention'}],
        'factors':[{'key':'population','label':'Study context','role':'match','rule':'Same study context'}, {'key':'location','label':'Location','role':'context','rule':'Describe differences'}]})
    papers=[]
    for n in (1,2):
        quote=f'Approach {n} reported {finding} for adult participants in the north.'
        m={'id':str(n),'method':f'Unrelated source name {n}','name':'Reported finding','value':finding,'quote':quote,'entityId':f'e{n}','entityQuote':quote,
           'protocol':copy.deepcopy(protocol),'factor_population':'adult participants','factor_location':'north','verified':True,
           'evidence':{k:{'quote':quote,'origin':'paper'} for k in ('factor_population','factor_location')}}
        s.validate_metric(m,quote)
        papers.append({'id':f'p{n}','title':topic,'protocol':protocol,'metrics':[m]})
    return papers


def assessment(pair):
    return {'checks':[{'criterion':key,'status':'match','reason':'Supported in the supplied context','refs':['a.'+ref,'b.'+ref]}
        for key,ref in [('entity','entity'),('measurement','result'),('factor_population','factor_population'),('factor_location','factor_location')]]}


class GenericComparisonTests(unittest.TestCase):
    def test_different_topics_use_identical_engine_and_explicit_ids(self):
        for topic in ('education','materials science','economics','qualitative interviews','machine learning'):
            with self.subTest(topic=topic):
                papers=fixture(topic);pair=s.candidate_pairs(papers)[1][0]
                record=s.validate_assessment(pair,assessment(pair),'test-model')
                result=compare(papers,assessments={pair['id']:record})
                self.assertEqual(result['engine'],'generic-v3')
                self.assertEqual(result['pairs'][0]['outcome'],'comparable')
                self.assertFalse(result['pairs'][0]['verified'])
                self.assertIsNone(result['pairs'][0]['favours'])
    def test_names_do_not_assign_entities(self):
        papers=fixture();papers[1]['metrics'][0]['entityId']='unknown'
        result=s.compare(papers)
        self.assertEqual(result['unassigned'],1)
        self.assertEqual(result['pairs'][0]['outcome'],'insufficient')
        self.assertEqual(s.compare(papers,entities=['e1','e2'])['pairs'],[])
    def test_source_containment_does_not_approve_semantic_assignment(self):
        pair=s.candidate_pairs(fixture())[1][0];raw=assessment(pair)
        raw['checks'][0]['status']='unknown'
        record=s.validate_assessment(pair,raw,'test')
        self.assertEqual(s.render_pair(pair,record)['outcome'],'insufficient')
    def test_invalid_reference_cannot_decide_a_pair(self):
        pair=s.candidate_pairs(fixture())[1][0];raw=assessment(pair)
        raw['checks'][1]['refs']=['a.invented','b.result']
        record=s.validate_assessment(pair,raw,'test')
        self.assertEqual(s.render_pair(pair,record)['outcome'],'insufficient')
    def test_unrelated_quotes_do_not_settle_measurement(self):
        pair=s.candidate_pairs(fixture())[1][0];raw=assessment(pair)
        raw['checks'][1]['refs']=['a.entity','b.entity']
        self.assertEqual(s.render_pair(pair,s.validate_assessment(pair,raw,'test'))['outcome'],'insufficient')
    def test_omitted_criteria_remain_unknown(self):
        pair=s.candidate_pairs(fixture())[1][0]
        self.assertEqual(s.render_pair(pair,s.validate_assessment(pair,{'checks':[]},'test'))['outcome'],'insufficient')
    def test_context_conflicts_do_not_gate_but_match_conflicts_do(self):
        pair=s.candidate_pairs(fixture())[1][0];raw=assessment(pair)
        raw['checks'][-1]['status']='conflict'
        self.assertEqual(s.render_pair(pair,s.validate_assessment(pair,raw,'test'))['outcome'],'comparable')
        raw['checks'][-2]['status']='conflict'
        self.assertEqual(s.render_pair(pair,s.validate_assessment(pair,raw,'test'))['outcome'],'incompatible')
    def test_human_review_requires_both_evidence_reviews(self):
        pair=s.candidate_pairs(fixture())[1][0];record=s.validate_assessment(pair,assessment(pair),'test');record['reviewed']=True
        self.assertTrue(s.render_pair(pair,record)['verified'])
        pair['b']['verified']=False
        self.assertFalse(s.render_pair(pair,record)['verified'])
    def test_fact_or_contract_change_invalidates_review(self):
        for target,key,value in [('metric','value','43'),('metric','entityQuote','new evidence'),('contract','task','new question')]:
            papers=fixture();pair=s.candidate_pairs(papers)[1][0];record=s.validate_assessment(pair,assessment(pair),'test');record['reviewed']=True
            m=papers[0]['metrics'][0]; (m if target=='metric' else m['protocol'])[key]=value
            changed=s.candidate_pairs(papers)[1][0]
            result=s.render_pair(changed,record)
            self.assertTrue(result['stale']);self.assertFalse(result['verified'])
    def test_unsupported_values_and_membership_are_withheld(self):
        m=fixture()[0]['metrics'][0];m['factor_population']='children';m['entityQuote']='not in source'
        s.validate_metric(m,m['quote'])
        self.assertEqual(m['factor_population'],'unknown');self.assertEqual(m['entityId'],'unknown')
    def test_qualitative_finding_is_not_rejected_for_lacking_digits(self):
        papers=fixture(finding='greater belonging');p=papers[0];m=copy.deepcopy(p['metrics'][0])
        validate_analysis(p,{'metrics':[m]},m['quote'])
        self.assertEqual(p['metrics'][0]['value'],'greater belonging')
    def test_different_contracts_remain_unresolved(self):
        papers=fixture();papers[1]['metrics'][0]['protocol']['task']='Different question'
        pair=s.candidate_pairs(papers)[1][0]
        self.assertEqual(s.render_pair(pair,s.validate_assessment(pair,assessment(pair),'test'))['outcome'],'insufficient')
    def test_doi_reference_uses_general_metadata_lookup(self):
        with patch('relay.research.fetch',return_value='{"id":"https://openalex.org/W123","display_name":"A social science study"}') as fetch:
            paper=referenced_paper('10.1234/example')
        self.assertEqual(paper['id'],'W123');self.assertIn('doi.org/10.1234/example',fetch.call_args.args[0])

if __name__=='__main__':unittest.main()

class GenericExecutionTests(unittest.TestCase):
    def test_audits_are_bounded_cached_and_explicitly_retryable(self):
        import tempfile
        from pathlib import Path
        from relay.research import Research
        with tempfile.TemporaryDirectory() as root:
            r=Research(Path(root));papers=fixture()
            for paper in papers:
                original=paper['metrics'][0]
                paper['metrics']=[dict(copy.deepcopy(original),id=str(i)) for i in range(5)]
            p={'id':'a'*16,'papers':papers,'protocol':papers[0]['protocol'],'model':'test','revision':1,'status':'review','events':[]}
            calls=[]
            def llm(project,system,payload,*args):
                calls.append(payload)
                return {'assessments':[dict(assessment(x),pair=x['id']) for x in payload['pairs']]}
            with patch.object(r,'llm',side_effect=llm),patch.object(r,'event'),patch.object(r,'checkpoint'):
                r.audit_comparisons(p)
                self.assertEqual(len(calls),4);self.assertEqual(len(p['comparisonAssessments']),12)
                self.assertTrue(all(len(c['pairs'])<=3 for c in calls))
                r.audit_comparisons(p);r.audit_comparisons(p)
                self.assertEqual(len(p['comparisonAssessments']),25)
                count=len(calls);r.audit_comparisons(p);self.assertEqual(len(calls),count)
                pair=next(iter(p['comparisonAssessments']));r.audit_comparisons(p,retry_pair=pair)
                self.assertEqual(len(calls),count+1)
    def test_agent_cannot_mark_assessment_human_reviewed(self):
        import tempfile
        from pathlib import Path
        from relay.research import Research
        with tempfile.TemporaryDirectory() as root:
            r=Research(Path(root));papers=fixture();pair=s.candidate_pairs(papers)[1][0]
            p={'id':'a'*16,'papers':papers,'revision':1,'status':'review','comparisonAssessments':{pair['id']:s.validate_assessment(pair,assessment(pair),'test')}}
            r.projects=[p]
            with patch.object(r,'checkpoint'):
                r.review_comparison({'id':p['id'],'revision':1,'pair':pair['id'],'approved':True,'actor':'agent'})
            self.assertFalse(p['comparisonAssessments'][pair['id']]['reviewed'])
