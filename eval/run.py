"""Evaluate Relay's evidence pipeline against a single-pass model baseline on annotated comparison cases.

    python3 eval/run.py --validate                 # check gold quotes and target cells against the sources
    python3 eval/run.py --split dev                # run both systems on development cases
    python3 eval/run.py --split heldout            # run once on held-out cases after development is frozen

Both systems use the same model and the same paper text (arXiv HTML converted with Relay's table-aware parser).
Paper text is cached in eval/.cache (not committed). Results go to eval/results/.
"""
import argparse, concurrent.futures, hashlib, json, re, sys, threading, time, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from relay.core import read_config  # noqa: E402
from relay.evidence import (html_to_text, cell_context, mentions, norm, compare_pair, split_key, horizon_key, metric_definition_key,  # noqa: E402
                            provenance_key, dataset_key, known)
from relay.research import model_call, target_context, investigate_metric  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE, RESULTS = HERE / '.cache', HERE / 'results'
POLICY = None


def source(arxiv):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f'{arxiv}.html'
    if not path.exists():
        req = urllib.request.Request(f'https://arxiv.org/html/{arxiv}', headers={'User-Agent': 'RelayResearch-eval/0.4'})
        with urllib.request.urlopen(req, timeout=60) as r: path.write_bytes(r.read())
    text = html_to_text(path.read_text(encoding='utf-8', errors='replace'))
    return text, hashlib.sha256(text.encode()).hexdigest()


def squash(s): return re.sub(r'\s+', ' ', str(s)).strip()


def validate(data, texts):
    problems = []
    for t in data['targets']:
        text = texts[t['paper']][0]
        for q in t['goldQuotes']:
            if squash(q) not in squash(text): problems.append(f"{t['id']}: gold quote not found: {q[:80]}")
        cell = cell_context(text, t['value'], t['methodHint'], t['name'])
        if not cell: problems.append(f"{t['id']}: value {t['value']} not located in a table cell")
        elif not mentions(t['methodHint'], cell['path']) and 'Forward-backward' not in cell['path']:
            problems.append(f"{t['id']}: cell path '{cell['path']}' does not name {t['methodHint']}")
    return problems


# ---------------------------------------------------------------- scoring

def score_fields(pred, gold):
    """Field-level correctness with the same normalizers the app uses."""
    out = {}
    out['method'] = bool(known(pred.get('method')) and (mentions(gold['method'], pred.get('method', '')) or mentions(pred.get('method', ''), gold['method'])))
    pd = dataset_key(pred.get('dataset', '')) if known(pred.get('dataset')) else None
    out['dataset'] = pd == gold['dataset']
    ps = split_key(pred.get('split', '')) if known(pred.get('split')) else None
    out['split'] = (list(ps) if ps else None) == gold['split']
    hk = horizon_key(pred.get('horizon', ''), pred.get('aggregation', ''), pred.get('dataset', ''))
    gm, gmin = gold['horizon']['mode'], gold['horizon']['minutes']
    out['horizon'] = hk['mode'] == gm and (gm is None or hk['minutes'] == gmin)
    md = metric_definition_key(pred.get('metricDefinition', ''))
    md = md if md in ('masked', 'unmasked', 'nonstandard') else None
    out['metricDefinition'] = md == gold['metricDefinition']
    out['provenance'] = provenance_key(pred.get('provenance', '')) == gold['provenance']
    # Hallucination: a specific value where the paper states none.
    hall = {}
    if gold['split'] is None: hall['split'] = ps is not None
    if gm is None: hall['horizon'] = hk['mode'] is not None
    if gold['metricDefinition'] is None: hall['metricDefinition'] = md is not None
    if gold['provenance'] == 'unknown': hall['provenance'] = provenance_key(pred.get('provenance', '')) != 'unknown'
    return out, hall


def summarize(rows, key):
    """Outcome metrics; coverage is reported next to accuracy so refusing every comparison cannot look like success."""
    n = len(rows); gold = [r['gold'] for r in rows]; pred = [r[key] for r in rows]
    ok = sum(g == p for g, p in zip(gold, pred))
    tp = sum(g == p == 'comparable' for g, p in zip(gold, pred))
    pc = sum(p == 'comparable' for p in pred); gc = sum(g == 'comparable' for g in gold)
    wrong_accept = sum(p == 'comparable' and g != 'comparable' for g, p in zip(gold, pred))
    decisive = sum(p in ('comparable', 'incompatible') for p in pred)
    return {'cases': n, 'accuracy': round(ok / n, 3) if n else None, 'comparablePrecision': round(tp / pc, 3) if pc else None,
            'comparableRecall': round(tp / gc, 3) if gc else None, 'incorrectlyAccepted': wrong_accept, 'goldNotComparable': n - gc,
            'coverage': round(decisive / n, 3) if n else None, 'failed': sum(p == 'error' for p in pred),
            'confusion': {g: dict(Counter(p for gg, p in zip(gold, pred) if gg == g)) for g in ('comparable', 'incompatible', 'insufficient')}}


# ---------------------------------------------------------------- systems

class Meter:
    def __init__(self): self.lock = threading.Lock(); self.calls = []
    def ask(self, cfg, provider, model, max_tokens):
        def call(system, payload, kind):
            record = {}
            try: return model_call(cfg, provider, model, system, payload, kind, max_tokens, None, record)
            finally:
                with self.lock: self.calls.append(record)
        return call
    def totals(self, kinds=None):
        cs = [c for c in self.calls if not kinds or c.get('kind') in kinds]
        return {'calls': len(cs), 'failed': sum(not c.get('ok') for c in cs), 'recovered': sum(c.get('attempts', 1) > 1 or c.get('repaired') for c in cs),
                'tokens': sum(c.get('totalTokens', 0) for c in cs), 'modelSeconds': round(sum(c.get('ms', 0) for c in cs) / 1000, 1)}


def relay_target(t, texts, titles, ask, investigate=True):
    text = texts[t['paper']][0]; started = time.monotonic()
    try:
        m = target_context(ask, t['paper'], titles[t['paper']], text, t['value'], t['methodHint'])
    except Exception as e:
        return {'error': str(e)[:200], 'seconds': round(time.monotonic() - started, 1)}
    base = {k: m.get(k, 'unknown') for k in ('method', 'name', 'value', 'unit', 'direction', 'dataset', 'datasetVersion', 'split', 'horizon', 'aggregation', 'preprocessing', 'metricDefinition', 'provenance', 'citedFrom', 'locator', 'quote')}
    base['cellHorizon'] = ((m.get('checks') or {}).get('cell') or {}).get('horizonLabel', '')
    result = {'extract': base, 'cell': ((m.get('checks') or {}).get('cell') or {}).get('path'), 'rejected': m.get('rejected', {})}
    fields = [f for f in ('split', 'horizon', 'aggregation', 'metricDefinition', 'provenance') if f in m.get('missing', [])]
    final = dict(base)
    if investigate and fields:
        try:
            proposals, unresolved, _ = investigate_metric(ask, titles[t['paper']], text, m, fields)
            accepted = {}
            for prop in proposals:  # evaluation auto-accepts verified proposals; the app asks the researcher
                accepted.setdefault(prop['field'], prop)
            for f, prop in accepted.items(): final[f] = prop['value']
            result['proposals'] = [{k: p[k] for k in ('field', 'value', 'quote')} for p in accepted.values()]
        except Exception as e:
            result['investigationError'] = str(e)[:200]
    result['final'] = final; result['seconds'] = round(time.monotonic() - started, 1)
    return result


BASELINE = ('You compare two reported results for an ML researcher. For each target, find the number in the paper text and report its experimental context. '
            'Then decide whether the two results can be compared under the policy. Return {"a":{"method","dataset","split","horizon","aggregation","metricDefinition","provenance"},'
            '"b":{same fields},"outcome":"comparable, incompatible, or insufficient","independent":true or false,"explanation":"short reason"}. '
            'Use "unknown" for anything the paper does not state. split is train/val/test percentages; horizon gives minutes or steps; aggregation says single horizon or average over horizons; '
            'metricDefinition gives protocol details such as masking or a stated non-standard calculation; provenance is own, reproduced, cited, or unknown. '
            'independent is false when one value is a copy of the other paper\'s result or both come from one paper.')


def baseline_case(c, by_id, texts, titles, ask):
    a, b = by_id[c['a']], by_id[c['b']]; started = time.monotonic()
    docs = {'paperA': {'title': titles[a['paper']], 'text': texts[a['paper']][0]}}
    if b['paper'] != a['paper']: docs['paperB'] = {'title': titles[b['paper']], 'text': texts[b['paper']][0]}
    payload = {'policy': POLICY, 'a': {'paper': 'paperA', 'value': a['value'], 'methodHint': a['methodHint'], 'metric': a['name']},
               'b': {'paper': 'paperB' if b['paper'] != a['paper'] else 'paperA', 'value': b['value'], 'methodHint': b['methodHint'], 'metric': b['name']}, 'documents': docs}
    try:
        r = ask(BASELINE, payload, 'baseline')
        out = str(r.get('outcome', '')).lower().strip()
        return {'outcome': out if out in ('comparable', 'incompatible', 'insufficient') else 'error', 'independent': r.get('independent'), 'a': r.get('a') or {}, 'b': r.get('b') or {},
                'explanation': str(r.get('explanation', ''))[:500], 'seconds': round(time.monotonic() - started, 1)}
    except Exception as e:
        return {'outcome': 'error', 'error': str(e)[:200], 'a': {}, 'b': {}, 'seconds': round(time.monotonic() - started, 1)}


def relay_outcome(ra, rb, ta, tb, stage):
    if 'error' in ra or 'error' in rb: return 'error', None, []
    def rowof(r, t): return dict(r[stage], paper=t['paper'], title=t['paper'], metric=t['id'], verified=False)
    pair = compare_pair(rowof(ra, ta), rowof(rb, tb))
    return pair['outcome'], pair['independent'], pair['explanation']


def main():
    global POLICY
    ap = argparse.ArgumentParser()
    ap.add_argument('--validate', action='store_true'); ap.add_argument('--split', default='dev', choices=('dev', 'heldout', 'all'))
    ap.add_argument('--provider', default='nebius'); ap.add_argument('--model', default='nvidia/nemotron-3-super-120b-a12b')
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--systems', default='relay,baseline')
    args = ap.parse_args()
    data = json.loads((HERE / 'cases.json').read_text()); POLICY = data['policy']
    names = {p['arxiv']: p['name'] for p in data['papers']}
    texts = {a: source(a) for a in names}
    problems = validate(data, texts)
    if args.validate or problems:
        print('\n'.join(problems) or f"All {sum(len(t['goldQuotes']) for t in data['targets'])} gold quotes and {len(data['targets'])} target cells verified against the sources.")
        if problems or args.validate: return
    cases = [c for c in data['cases'] if args.split == 'all' or (c['heldOut'] if args.split == 'heldout' else not c['heldOut'])]
    by_id = {t['id']: t for t in data['targets']}
    needed = sorted({c['a'] for c in cases} | {c['b'] for c in cases})
    cfg = read_config(ROOT); systems = args.systems.split(',')
    meter = Meter(); ask = meter.ask(cfg, args.provider, args.model, 16000); base_ask = meter.ask(cfg, args.provider, args.model, 16000)
    started = time.monotonic(); relay, baseline = {}, {}
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        jobs = {}
        if 'relay' in systems: jobs.update({pool.submit(relay_target, by_id[t], texts, names, ask): ('relay', t) for t in needed})
        if 'baseline' in systems: jobs.update({pool.submit(baseline_case, c, by_id, texts, names, base_ask): ('baseline', c['id']) for c in cases})
        for i, f in enumerate(concurrent.futures.as_completed(jobs), 1):
            kind, key = jobs[f]; (relay if kind == 'relay' else baseline)[key] = f.result()
            print(f'[{time.monotonic() - started:6.0f}s] {i}/{len(jobs)} {kind} {key}', flush=True)
    rows, target_rows = [], []
    for c in cases:
        row = {'case': c['id'], 'gold': c['gold']['outcome'], 'goldIndependent': c['gold']['independent'], 'heldOut': c['heldOut'], 'why': c['why']}
        if 'relay' in systems:
            for stage, key in (('extract', 'relayExtract'), ('final', 'relay')):
                out, ind, expl = relay_outcome(relay[c['a']], relay[c['b']], by_id[c['a']], by_id[c['b']], stage)
                row[key] = out; row[key + 'Independent'] = ind; row[key + 'Explanation'] = expl
        if 'baseline' in systems:
            b = baseline[c['id']]; row['baseline'] = b['outcome']; row['baselineIndependent'] = b.get('independent'); row['baselineExplanation'] = b.get('explanation')
        rows.append(row)
    field_scores = {}
    if 'relay' in systems:
        for stage in ('extract', 'final'):
            agg, hall = Counter(), Counter(); hall_n = Counter(); n = 0
            for t in needed:
                r = relay[t]
                if 'error' in r: n += 1; continue
                ok, h = score_fields(r[stage], by_id[t]['gold']); n += 1
                agg.update({k: int(v) for k, v in ok.items()}); hall.update({k: int(v) for k, v in h.items()}); hall_n.update({k: 1 for k in h})
                if stage == 'final': target_rows.append({'target': t, 'fields': ok, 'hallucinated': h, 'pred': {k: r['final'].get(k) for k in ('method', 'dataset', 'split', 'horizon', 'aggregation', 'metricDefinition', 'provenance')}, 'gold': by_id[t]['gold'], 'cell': r.get('cell'), 'proposals': r.get('proposals', [])})
            field_scores['relay' if stage == 'final' else 'relayExtract'] = {'targets': n, 'accuracy': {k: round(agg[k] / n, 3) for k in ('method', 'dataset', 'split', 'horizon', 'metricDefinition', 'provenance')},
                                                                              'hallucinationRate': {k: round(hall[k] / hall_n[k], 3) for k in hall_n}, 'errors': sum('error' in relay[t] for t in needed)}
    if 'baseline' in systems:
        agg, hall, hall_n, n = Counter(), Counter(), Counter(), 0
        for c in cases:
            b = baseline[c['id']]
            for side in ('a', 'b'):
                if not b.get(side): continue
                ok, h = score_fields(b[side], by_id[c[side]]['gold']); n += 1
                agg.update({k: int(v) for k, v in ok.items()}); hall.update({k: int(v) for k, v in h.items()}); hall_n.update({k: 1 for k in h})
        field_scores['baseline'] = {'targetInstances': n, 'accuracy': {k: round(agg[k] / n, 3) for k in ('method', 'dataset', 'split', 'horizon', 'metricDefinition', 'provenance')} if n else {},
                                    'hallucinationRate': {k: round(hall[k] / hall_n[k], 3) for k in hall_n}}
    summary = {k: summarize(rows, k) for k in ('relay', 'relayExtract', 'baseline') if rows and k in rows[0]}
    for k in summary:
        ind = [(r['goldIndependent'], r.get(k + 'Independent')) for r in rows if r.get(k + 'Independent') is not None]
        summary[k]['independenceAccuracy'] = round(sum(g == bool(p) for g, p in ind) / len(ind), 3) if ind else None
    cost = {'relay': meter.totals({'target', 'investigate'}), 'baseline': meter.totals({'baseline'}), 'wallSeconds': round(time.monotonic() - started)}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    out = {'when': stamp, 'split': args.split, 'provider': args.provider, 'model': args.model, 'sources': {a: texts[a][1] for a in names}, 'summary': summary,
           'fields': field_scores, 'cost': cost, 'cases': rows, 'targets': target_rows, 'relayRaw': relay, 'baselineRaw': baseline}
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f'{stamp}-{args.split}.json'; path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({'summary': summary, 'fields': field_scores, 'cost': cost}, indent=1)); print('saved', path.relative_to(ROOT))


if __name__ == '__main__': main()
