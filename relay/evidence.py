"""Experimental evidence records, deterministic source checks, and three-outcome comparisons.

A reported number is only useful with its experimental context. This module keeps that context
explicit, checks each field against the retrieved source, and compares results without treating
missing context as proof of incompatibility.
"""
import hashlib, html, math, re
from html.parser import HTMLParser

# Context fields that travel with every reported number.
FIELDS = ('method', 'dataset', 'datasetVersion', 'split', 'horizon', 'aggregation', 'preprocessing',
          'metricDefinition', 'provenance', 'citedFrom', 'locator')
LABELS = {'method': 'Model', 'dataset': 'Dataset', 'datasetVersion': 'Dataset version', 'split': 'Train/val/test split',
          'horizon': 'Forecast horizon', 'aggregation': 'Aggregation', 'preprocessing': 'Preprocessing',
          'metricDefinition': 'Metric definition', 'provenance': 'Result provenance', 'citedFrom': 'Cited from',
          'locator': 'Source location', 'name': 'Metric', 'unit': 'Unit', 'value': 'Value', 'direction': 'Direction'}
# Fields whose absence prevents a comparison from being established.
REQUIRED = ('dataset', 'split', 'horizon')
UNKNOWN = {'', 'unknown', 'not reported', 'not stated', 'unspecified', 'n/a', 'na', 'none', 'null', '?', '-', 'not specified', 'not available', 'not given'}
# Benchmark sampling intervals documented by the datasets' original releases (DCRNN, STSGCN).
SENSORS = {207: 'metrla', 325: 'pemsbay', 358: 'pems03', 307: 'pems04', 883: 'pems07', 170: 'pems08'}
INTERVAL_MINUTES = {'metrla': 5, 'pemsbay': 5, 'pems03': 5, 'pems04': 5, 'pems07': 5, 'pems08': 5}


def flat(value):
    """Models sometimes return a field as an object or list; turn it into readable text."""
    if isinstance(value, dict): return ' '.join(f'{v} {k}' for k, v in value.items() if v not in (None, '', 'unknown'))
    if isinstance(value, (list, tuple)): return ' / '.join(flat(v) for v in value)
    return value


def norm(s):
    return ' '.join(str(flat(s) if s is not None else '').split())


def known(value):
    return norm(value).lower().strip(' .') not in UNKNOWN


def short_id(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- HTML to table-aware text

class SourceText(HTMLParser):
    """Plain text that keeps table rows on one line and expands row/column spans into a grid."""
    BLOCK = {'p', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'figcaption', 'caption', 'li', 'div', 'br', 'dd', 'dt', 'blockquote', 'article'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []; self.skip = 0; self.tables = []; self.figures = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'annotation', 'annotation-xml', 'nav', 'header', 'footer'): self.skip += 1; return
        if self.skip: return
        if tag == 'figure' and not self.tables: self.figures.append([])
        elif tag == 'table': self.tables.append({'rows': [], 'row': None, 'cell': None})
        elif self.tables and tag == 'tr': self.tables[-1]['row'] = []
        elif self.tables and tag in ('td', 'th'):
            t = self.tables[-1]
            if t['row'] is None: t['row'] = []
            span = lambda k: max(1, min(30, int(a.get(k) or 1))) if str(a.get(k) or '1').isdigit() else 1
            t['cell'] = {'text': [], 'colspan': span('colspan'), 'rowspan': span('rowspan')}
        elif tag in self.BLOCK: self.emit('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'annotation', 'annotation-xml', 'nav', 'header', 'footer'): self.skip = max(0, self.skip - 1); return
        if self.skip: return
        if self.tables and tag in ('td', 'th'):
            t = self.tables[-1]
            if t['cell'] is not None and t['row'] is not None:
                t['cell']['text'] = norm(''.join(t['cell']['text'])); t['row'].append(t['cell'])
            t['cell'] = None
        elif self.tables and tag == 'tr':
            t = self.tables[-1]
            if t['row'] is not None: t['rows'].append(t['row'])
            t['row'] = None
        elif self.tables and tag == 'table':
            t = self.tables.pop(); self.emit('\n' + '\n'.join(self.layout(t['rows'])) + '\n')
        elif tag == 'figure' and self.figures and not self.tables:
            # Captions may follow their table in the markup; keep the caption first so it labels its own table.
            lines = ''.join(self.figures.pop()).split('\n')
            captions = [l for l in lines if re.match(r'^\s*(Table|TABLE)\s*[IVX0-9]+', l)]
            self.emit('\n' + '\n'.join(captions + [l for l in lines if l not in captions]) + '\n')
        elif tag in self.BLOCK: self.emit('\n')

    def handle_data(self, data):
        if not self.skip: self.emit(data.replace('\n', ' '))

    def emit(self, text):
        if self.tables and self.tables[-1]['cell'] is not None: self.tables[-1]['cell']['text'].append(text)
        elif self.tables: pass  # whitespace between table tags
        elif self.figures: self.figures[-1].append(text)
        else: self.out.append(text)

    @staticmethod
    def layout(rows):
        grid, carry = [], {}
        for row in rows[:400]:
            line, col, cells = [], 0, list(row)
            while cells or any(c >= col for c in carry):
                if col in carry:
                    text, left = carry[col]; line.append(text)
                    if left <= 1: del carry[col]
                    else: carry[col] = (text, left - 1)
                    col += 1; continue
                if not cells: col += 1; continue
                cell = cells.pop(0)
                for k in range(cell['colspan']):
                    line.append(cell['text'])
                    if cell['rowspan'] > 1: carry[col + k] = (cell['text'], cell['rowspan'] - 1)
                col += cell['colspan']
                if col > 120: break
            if any(line): grid.append('| ' + ' | '.join(line))
        return grid

    def text(self):
        while self.figures: self.out.extend(self.figures.pop(0))
        t = ''.join(self.out)
        t = re.sub(r'[ \t ]+', ' ', t); t = re.sub(r' *\n *', '\n', t); return re.sub(r'\n{2,}', '\n', t).strip()


def html_to_text(markup):
    parser = SourceText(); parser.feed(markup); parser.close(); return parser.text()


# ---------------------------------------------------------------- normalizers

def dataset_identity(name, version=''):
    """Canonical dataset key; an ambiguous name such as "PeMS" is resolved by a documented sensor count."""
    key = dataset_key(name)
    if key in INTERVAL_MINUTES or key in ('pemsd7m',) or not version: return key
    m = re.search(r'(?i)(\d{3})\s*(?:traffic\s+|loop\s+)?(?:sensors|detectors|nodes)|#?sensors[^0-9]{0,12}(\d{3})|#nodes[^0-9]{0,12}(\d{3})', str(version))
    n = int(next(x for x in m.groups() if x)) if m else None
    return SENSORS.get(n, key) if key.startswith('pems') else key


def dataset_key(value):
    s = re.sub(r'[^a-z0-9]', '', norm(value).lower())
    s = re.sub(r'dataset$', '', s)
    m = re.fullmatch(r'pemsd?0?(\d)', s)
    if m: return 'pems0' + m[1]
    if s in ('metrla', 'metrlr', 'metr'): return 'metrla'
    if s in ('pemsbay', 'baypems'): return 'pemsbay'
    m = re.fullmatch(r'pemsd7\(?m\)?|pemsd7m', s)
    return 'pemsd7m' if m else s


def metric_key(value):
    s = norm(value).lower()
    for key, pattern in (('mape', r'\bmape\b|percentage'), ('rmse', r'\brmse\b|root mean squ'), ('mse', r'\bmse\b|mean squared'),
                         ('mae', r'\bmae\b|mean absolute error'), ('accuracy', r'accura'), ('f1', r'\bf1\b')):
        if re.search(pattern, s): return key
    return re.sub(r'[^a-z0-9]', '', s)


def numbers(text):
    return re.findall(r'\d+(?:\.\d+)?', str(text))


def split_key(value, strict=False):
    """Return train/val/test percentages, or None when the text cannot be parsed confidently.

    strict: only role-labelled numbers or an explicit a:b:c / a/b/c ratio count (used on paper sentences)."""
    s = norm(value).lower()
    if strict:
        if len(re.findall(r'\b(?:train|valid|val|test)', s)) < 2 and not re.search(r'\d\s*[:/]\s*\d+(?:\.\d+)?\s*[:/]\s*\d', s): return None
        m = re.search(r'\b(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\b', s)
        if m and not re.search(r'%', s[:m.start()][-30:]):
            k = split_key(m[0]); return k
        s = re.sub(r'\(\s*[^()]*?\b(?:19|20)\d\d[a-z]?\b[^()]*\)', ' ', s)  # drop citations with years
    if not known(s): return None
    roles = {}
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*%?\s*(?:of (?:the )?data )?(?:is |are )?(?:used )?(?:for |as )?(?:the )?(train|valid|val\b|test)', s):
        roles.setdefault(m[2][:3].replace('val', 'val'), float(m[1]))
    for m in re.finditer(r'(train\w*|valid\w*|val\b|test\w*)\s*(?:set|ing)?\s*(?:\(|:|=|of|with|ratio)?\s*(\d+(?:\.\d+)?)\s*%', s):
        roles.setdefault(m[1][:3], float(m[2]))
    if len(roles) == 3 and set(roles) == {'tra', 'val', 'tes'}:
        vals = [roles['tra'], roles['val'], roles['tes']]
    else:
        nums = [float(n) for n in numbers(s)]
        if len(nums) != 3: return None
        vals = nums
    total = sum(vals)
    if not total: return None
    pct = tuple(round(v * 100 / total) for v in vals)
    return pct if abs(sum(pct) - 100) <= 2 else None


RUNS = re.compile(r'(?:mean|average|avg|averaged)\s+(?:of|over|across)\s+(\d+|ten|five|three)\s+(?:independent\s+)?(?:runs|trials|seeds|times|repetitions)|(?:best|max\w*)\s+(?:of|among|over)\s+(\d+|five|ten|three)\s*(?:runs|trials|seeds|times)?|(\d+|ten|five|three)\s+(?:runs|trials|seeds|repetitions)|single run|one run|±|\+/-', re.I)
WORDS = {'three': 3, 'five': 5, 'ten': 10}


def runs_key(value):
    s = norm(value).lower(); m = RUNS.search(s)
    if not m: return None
    count = next((x for x in m.groups() if x), None)
    if count in WORDS: count = WORDS[count]
    elif count and count.isdigit(): count = int(count)
    else: count = None
    if 'best' in m[0] or 'max' in m[0]: return ('best', count)
    if 'single' in m[0] or 'one run' in m[0]: return ('single', 1)
    return ('mean', count)


def horizon_key(horizon, aggregation, dataset=''):
    """Canonical horizon: {'mode': single|average|None, 'minutes': int|None, 'steps': int|None}."""
    h, a = norm(horizon).lower(), norm(aggregation).lower()
    a_wo_runs = RUNS.sub(' ', a); h_wo_runs = RUNS.sub(' ', h)
    text = (h_wo_runs + ' ' + a_wo_runs)
    mode = None
    if re.search(r'averag|\bmean\b|all (?:prediction )?(?:steps|horizons|time slots)|\bavg\b|overall|across (?:all )?(?:\d+ )?(?:horizons|steps)', text): mode = 'average'
    elif re.search(r'single|per[- ]horizon|horizon\s*[:=]?\s*\d+|step\s*\d+|@\s*\d+|\d+(?:st|nd|rd|th)\s+(?:time slot|step)|ahead|\bat\s+\d+\s*(?:min|minutes)', h_wo_runs + ' ' + a_wo_runs) and not re.search(r'next\s+\d+\s+steps|\d+\s+steps?\s+(?:as )?(?:output|prediction)', h_wo_runs):
        mode = 'single'
    elif re.fullmatch(r'\s*(?:\d+\s*(?:min|minutes|mins)|\d+\s*hours?|1 hour|one hour)\s*', h_wo_runs) and not known(a_wo_runs.strip(' ,;')):
        mode = 'single'  # a column such as "15 min" or "1 hour" names one horizon
    if known(a) and mode is None and re.search(r'single|per horizon|individual', a): mode = 'single'
    minutes = steps = None
    m = re.search(r'(\d+)\s*(?:-|\s)?(?:min|minute|minutes|mins)\b|minutes?[\'"]?\s*[:=]\s*(\d+)', text)
    if m: minutes = int(m[1] or m[2])

    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hours|hr)\b|(one)\s+hour|\b(\d)\s*h\b', text)
    if m and minutes is None: minutes = int(float(m[1] or (1 if m[2] else m[3])) * 60)
    m = re.search(r'(?:horizon|step|@)\s*[:=]?\s*(\d+)|steps?[\'"]?\s*[:=]\s*(\d+)|(\d+)\s*(?:-|\s)?steps?\b|(\d+)(?:st|nd|rd|th)\s+(?:time slot|step)|(\d+)\s+(?:prediction )?horizons', text)
    if m: steps = int(next(x for x in m.groups() if x))
    interval = INTERVAL_MINUTES.get(dataset_key(dataset))
    if mode == 'average':
        # An average's horizon span is its longest horizon, e.g. "range 5-60 minutes".
        ends = [int(end) for _, end in re.findall(r'(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:min|minutes)', text)]
        if ends: minutes = max(ends)
        if interval and steps:  # 12 steps of 5 minutes span 60 minutes, whatever a stated sample rate says
            minutes = max(minutes or 0, steps * interval)
    converted = False
    if interval and steps and minutes is None: minutes = steps * interval; converted = True
    if interval and minutes and steps is None and minutes % interval == 0: steps = minutes // interval
    return {'mode': mode, 'minutes': minutes, 'steps': steps, 'converted': converted}


def describe_horizon(k):
    if not k['mode'] and not k['minutes'] and not k['steps']: return 'unknown'
    span = f"{k['minutes']} minutes" if k['minutes'] else (f"{k['steps']} steps" if k['steps'] else 'unstated length')
    return {'average': f'average over horizons up to {span}', 'single': f'single horizon at {span}'}.get(k['mode'], f'{span}, aggregation unknown')


def metric_definition_key(value):
    s = norm(value).lower()
    if not known(s): return None
    if re.search(r'non-?standard|inconsistent|different manner|(?:differs?|different) from .{0,50}(?:official|standard|original)|not consistent', s): return 'nonstandard'
    if re.search(r'unmasked|no mask|not masked|without mask|includ\w* zero|naive mae|all values|mask\w*\s*(?:=|:)?\s*none|thresh\w*\s*(?:=|:)?\s*none', s): return 'unmasked'
    if re.search(r'mask|exclud|ignor|missing values|null values|zero', s): return 'masked'
    return 'other:' + re.sub(r'[^a-z0-9]', '', s)[:40]


def provenance_key(value):
    s = norm(value).lower()
    if not known(s): return 'unknown'
    if re.search(r'cited|copied|reported (?:in|by|from)|taken from|from (?:the )?original|quoted from|literature', s): return 'cited'
    if re.search(r'reproduc|re-?run|re-?implement|our (?:own )?(?:run|experiment|implementation)|retrain', s): return 'reproduced'
    if re.search(r'\bown\b|proposed|this paper|ours', s): return 'own'
    return 'unknown'


ALIASES = {'gwnet': ('graphwavenet', 'gwnet', 'graphwave'), 'astgcn': ('astgcn', 'astgcnr')}


def alnum(value):
    return re.sub(r'[^a-z0-9]', '', norm(value).lower())


def mentions(method, text):
    """True when a method name (or a known alias) appears in text."""
    key, hay = method_key(method), alnum(text)
    if not key: return False
    return key in hay or alnum(method) in hay or any(a in hay for a in ALIASES.get(key, ()))


def method_key(value):
    s = re.sub(r'\(.*?\)|\[.*?\]|et al\.?|\d{4}[a-z]?', ' ', norm(value).lower())
    s = re.sub(r'\b(ours|our|model|proposed|method)\b', ' ', s)
    s = re.sub(r'[^a-z0-9]', '', s)
    return {'graphwavenet': 'gwnet', 'gwnet': 'gwnet', 'graphwave': 'gwnet'}.get(s, s)


# ---------------------------------------------------------------- source checks

STOP = {'the', 'and', 'for', 'with', 'from', 'over', 'into', 'per', 'all', 'are', 'was', 'were', 'each', 'data', 'using', 'used', 'set', 'sets', 'results', 'result'}


def supports(value, text):
    """True when every number and most content words of value occur in text."""
    t = norm(text).lower()
    nums = numbers(value)
    if nums:
        present = set(numbers(t))
        return all(n in present or n.rstrip('0').rstrip('.') in present for n in nums)
    words = [w for w in re.findall(r'[a-z][a-z0-9-]{2,}', norm(value).lower()) if w not in STOP]
    if not words: return True
    hits = sum(1 for w in words if w[:6] in t)
    return hits / len(words) >= 0.6


def split_supported(value, text):
    """A split is supported only by a sentence whose parsed split equals it."""
    target = split_key(value)
    if not target: return supports(value, text)
    for sentence in re.split(r'(?<=[.;])\s+|\n', norm(text) if '\n' not in text else text):
        if re.search(r'(?i)\btrain|\bvalid|\btest|\bsplit|\bratio\b|\bdivided\b|:\s*\d', sentence) and split_key(sentence, strict=True) == target: return True
        for m in re.finditer(r'\d+(?:\.\d+)?\s*[:/]\s*\d+(?:\.\d+)?\s*[:/]\s*\d+(?:\.\d+)?', sentence):
            if split_key(m[0]) == target: return True
    return False


def sentence_splits(sentence):
    """Every train/val/test split stated in one sentence: all a:b:c ratios, or the role-labelled percentages."""
    ratios = [split_key(m[0]) for m in re.finditer(r'\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?', sentence)]
    ratios = [k for k in ratios if k]
    if ratios: return ratios
    k = split_key(sentence, strict=True)
    return [k] if k else []


def dataset_sentence_splits(sentence, names):
    """Splits in a sentence that belong to the named dataset. When the sentence has several ratios, a ratio belongs to
    the dataset only if the dataset is named between the previous ratio and this one."""
    matches = list(re.finditer(r'\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?', sentence))
    if len(matches) <= 1: return sentence_splits(sentence) if any(n in alnum(sentence) for n in names) else []
    out, prev = [], 0
    for m in matches:
        segment = alnum(sentence[prev:m.start()])
        if any(n and n in segment for n in names):
            k = split_key(m[0])
            if k: out.append(k)
        prev = m.end()
    return out


def stated_splits(source):
    """Distinct train/val/test splits stated in sentences of the paper."""
    found = []
    for sentence in re.split(r'(?<=[.;])\s+|\n', source):
        if len(sentence) > 600 or not re.search(r'(?i)\btrain|\bsplit|\bratio\b|\bdivided\b', sentence): continue
        for k in sentence_splits(sentence):
            if k not in found: found.append(k)
    return found


def dataset_splits(source, dataset):
    """Splits stated within a few lines of a mention of this dataset."""
    if not known(dataset): return []
    lines = source.split('\n'); key = dataset_key(dataset); found = []
    names = {key, alnum(dataset)} | ({'pemsd' + key[-1], 'pems' + key[-1]} if re.fullmatch(r'pems0\d', key) else set())
    for i, line in enumerate(lines):
        if line.startswith('|') or not re.search(r'(?i)\btrain|\bsplit|\bratio\b|\bdivided\b', line): continue
        context = alnum(' '.join(lines[max(0, i - 3):i + 1]))
        if not any(n and n in context for n in names): continue
        for sentence in re.split(r'(?<=[.;])\s+', line):
            if not re.search(r'(?i)\btrain|\bsplit|\bratio\b|\bdivided\b', sentence) or not any(n in alnum(sentence) for n in names) and len(re.split(r'(?<=[.;])\s+', line)) > 1 and re.search(r'(?i)(?:metr|pems)', sentence): continue
            for k in dataset_sentence_splits(sentence, names):
                if k not in found: found.append(k)
    return found


def field_supported(field, value, text):
    return split_supported(value, text) if field == 'split' else supports(value, text)


def locate(source, quote):
    """Position of a quote within the normalized source, or -1."""
    s, q = norm(source), norm(quote)
    return s.find(q) if q else -1


def table_rows(source):
    """Yield (line_index, cells) for table lines."""
    for i, line in enumerate(source.split('\n')):
        if line.startswith('|'):
            yield i, [c.strip() for c in line[1:].split('|')]


def is_number_cell(cell):
    return bool(re.fullmatch(r'[-+]?\d+(?:\.\d+)?\s*%?\s*[*∗⋆†‡]*\s*(?:±\s*\d+(?:\.\d+)?)?\s*[*∗⋆†‡]*', cell.strip())) or cell.strip() in ('-', '—', 'N/A')


def cell_context(source, value, method='', name='', horizon=''):
    """Find the table cell that holds value and return its row labels, column headers, and caption.

    This is the row/column check: a quote containing the value does not establish that the
    value belongs to the extracted method, metric, and horizon. The header path does.
    """
    lines = source.split('\n'); value = norm(value)
    if not value: return None
    best = None
    for i, line in enumerate(lines):
        if not line.startswith('|') or value not in line: continue
        cells = [c.strip() for c in line[1:].split('|')]
        for j, cell in enumerate(cells):
            if not re.match(r'^[-+]?' + re.escape(value) + r'(?![\d])', cell): continue
            # Table block boundaries.
            start = i
            while start > 0 and lines[start - 1].startswith('|'): start -= 1
            end = i
            while end + 1 < len(lines) and lines[end + 1].startswith('|'): end += 1
            headers = []
            for k in range(start, i):
                hc = [c.strip() for c in lines[k][1:].split('|')]
                numeric = sum(is_number_cell(c) for c in hc)
                if numeric <= max(1, len(hc) // 4) and j < len(hc) and hc[j] and not is_number_cell(hc[j]):
                    if not headers or headers[-1] != hc[j]: headers.append(hc[j])
            labels = []
            for c in cells[:j]:
                if c and not is_number_cell(c) and c not in labels: labels.append(c)
            caption = ''
            for k in range(start - 1, max(-1, start - 4), -1):
                if re.match(r'^(Table|TABLE)\s*[IVX0-9]+', lines[k]): caption = lines[k][:400]; break
            path = ' / '.join(labels + headers)
            score = (mentions(method, path) if method else 0) * 3 \
                + (metric_key(name) == metric_key(' '.join(headers + labels)) or metric_key(name) in path.lower()) * 2 \
                + bool(horizon and supports(' '.join(numbers(horizon)[:1]) or horizon, path + ' ' + caption))
            candidate = {'line': i, 'row': line[:600], 'labels': labels, 'headers': headers, 'path': path[:400], 'caption': caption, 'score': score}
            if not best or score > best['score']: best = candidate
    return best


def window(source, quote, before=4000, after=2000):
    s = norm(source); pos = s.find(norm(quote))
    if pos < 0: return ''
    return s[max(0, pos - before):pos + len(norm(quote)) + after]


def is_proposed(method, source, title=''):
    """True when the paper presents this method as its own: title, an "(ours)" label, or a propose/introduce sentence."""
    if not known(method): return False
    if title and mentions(method, title): return True
    key = re.escape(re.sub(r'\s*\(.*?\)|\s*\[.*?\]', '', norm(method)).strip())
    if not key: return False
    if re.search(r'(?i)' + key + r'\s*\((?:ours|proposed)\)|\((?:ours|proposed)\)\s*' + key, source): return True
    for m in re.finditer(r'(?i)\b(?:we|this paper|our paper)\s+(?:\w+\s+){0,3}?(?:propose|present|introduce|develop|call|name|term|dub)\w*|\bour (?:proposed|novel) (?=[A-Z])', source):
        rest = re.sub(r'et al\.', 'et al', source[m.end():m.end() + 260])
        sentence = re.split(r'(?<=[A-Za-z0-9)])\.\s', rest)[0]
        if re.search(r'(?i)\bcompar\w*|\bagainst\b|such as|\bincluding\b|\bfollowing\b|widely used|\bon the\b|\bin table\b|\btable\s*\d', sentence): continue
        if re.search(r'\b' + key + r'\b', sentence): return True
    return False


PROBLEM = r'(?i)differen|inconsisten|incorrect|\berror\b|\bbug\b|mistake|wrong'
ACTION = r'(?i)\bwe\s+(?:have\s+)?(?:updated|corrected|revised|fixed)\b|\bcorrecting\b|\bcorrection of\b|errat(?:um|a)\b|(?:updates?|corrections?) (?:of|to) tables?'


def table_notes(source, caption):
    """Paragraphs that say this table was later updated or corrected because of a stated problem."""
    m = re.match(r'^(?:Table|TABLE)\s*([IVX]+|\d+)', caption or '')
    if not m or re.search(r'(?i)correction of', caption): return []
    n = re.escape(m[1]); notes = []
    for line in source.split('\n'):
        if line.startswith('|') or len(line) < 60: continue
        refs = re.search(r'(?i)tables?\s+(?:[IVX\d]+\s*(?:,|and|&)\s*)*' + n + r'\b', line)
        if refs and re.search(ACTION, line) and re.search(PROBLEM, line): notes.append(norm(line)[:1200])
    return notes[:3]


def resolve_bare_pems(source, dataset):
    """A bare "PeMS" name is resolved by the sensor count stated near it (325 sensors -> PEMS-BAY, and so on)."""
    if dataset_key(dataset) != 'pems': return None
    m = re.search(r'(?i)pems[^.]{0,220}?\b(\d{3})\s+(?:traffic\s+|loop\s+|road\s+)?(?:sensors|detectors|nodes)', source)
    if not m: return None
    key = SENSORS.get(int(m[1]))
    return {'pemsbay': 'PEMS-BAY', 'metrla': 'METR-LA'}.get(key, key.upper() if key else None)


def check_metric(metric, source, title=''):
    """Deterministic checks for one extracted number. Returns metric with `checks` and demoted fields.

    - value must be inside its quote, and the quote inside the retrieved source (done by caller).
    - each context field is marked quoted / nearby / document / unsupported / missing.
    - unsupported fields are demoted to unknown; the model's claim is kept for review.
    - the table cell path is compared with method, metric, and horizon.
    """
    if not known(metric.get('dataset', 'unknown')):
        # The table's column path often names the dataset (for example "PeMS / GMAN / 1 hour / MAE").
        cell0 = cell_context(source, metric.get('value', ''), metric.get('method', ''), metric.get('name', ''), metric.get('horizon', ''))
        tok = re.search(r'(?i)\b(pems(?:d?\d+|[- ]?bay)?|metr[- ]?la)\b', (cell0 or {}).get('path', ''))
        if tok: metric['dataset'] = tok[1]; metric['datasetFromColumn'] = True
    resolved = resolve_bare_pems(source, metric.get('dataset', ''))
    if resolved:
        metric['dataset'] = resolved
    near = window(source, metric.get('quote', ''))
    doc = norm(source)
    evidence = metric.get('evidence') if isinstance(metric.get('evidence'), dict) else {}
    support, rejected = {}, dict(metric.get('rejected') or {})
    for field in ('method', 'dataset', 'datasetVersion', 'split', 'horizon', 'aggregation', 'preprocessing', 'metricDefinition', 'citedFrom'):
        value = metric.get(field, 'unknown')
        if field == 'dataset' and known(value) and (metric.get('datasetFromColumn') or resolved):
            # Derived from the table column label or the paper's sensor count, not quoted in the result's own quote.
            support['dataset'] = 'derived'; continue
        if field == 'split' and known(value) and not split_key(value) and (evidence.get('split') or {}).get('origin', 'paper') == 'paper':
            rejected['split'] = {'value': value, 'reason': 'Not a train/validation/test split.'}; metric['split'] = value = 'unknown'
        if not known(value):
            if field == 'split':
                stated = dataset_splits(source, metric.get('dataset', '')) or (stated_splits(source) if len(stated_splits(source)) == 1 else [])
                if len(stated) == 1:
                    metric['split'] = '/'.join(map(str, stated[0])); support['split'] = 'document'; continue
            support[field] = 'missing'; continue
        if field == 'split' and (evidence.get('split') or {}).get('origin', 'paper') == 'paper':
            ds = dataset_splits(source, metric.get('dataset', ''))
            if len(ds) == 1 and split_key(value) != ds[0] and len(stated_splits(source)) > 1:
                rejected['split'] = {'value': value, 'reason': f"The paper states {'/'.join(map(str, ds[0]))} for {metric.get('dataset')}."}
                metric['split'] = '/'.join(map(str, ds[0])); support['split'] = 'document'; continue
        item = evidence.get(field) or {}
        fq = norm(item.get('quote', '')) if isinstance(item, dict) else ''
        origin = item.get('origin', 'paper') if isinstance(item, dict) else 'paper'
        if fq and origin != 'paper':
            support[field] = origin  # repository or researcher evidence, verified when it was accepted
            continue
        if fq and fq in doc and (field_supported(field, value, fq) or field in ('aggregation', 'metricDefinition', 'preprocessing')): support[field] = 'quoted'; continue
        if field == 'aggregation' and re.search(r'(?i)single|per[- ]horizon|individual', value) and not re.search(r'(?i)averag|mean|best', value):
            cell_text = metric.get('quote', '') + ' ' + (cell_context(source, metric.get('value', ''), metric.get('method', ''), metric.get('name', ''))  or {}).get('path', '')
            if re.search(r'(?i)\d+\s*(?:min|minutes|hour)|horizon\s*\d+|@\s*\d+|step\s*\d+', cell_text): support[field] = 'derived'; continue
        if field_supported(field, value, metric.get('quote', '')): support[field] = 'quoted'
        elif field == 'horizon' and (any(n in numbers(near) for n in numbers(value)) or not numbers(value)): support[field] = 'nearby'
        elif field_supported(field, value, near): support[field] = 'nearby'
        elif field_supported(field, value, source): support[field] = 'document'
        else:
            support[field] = 'unsupported'; rejected[field] = {'value': value, 'reason': 'Not found in the retrieved source text.'}
            metric[field] = 'unknown'
            if field == 'split':
                stated = stated_splits(source)
                if len(stated) == 1:
                    # Use what the paper states; keep the model's claim visible for review.
                    metric['split'] = '/'.join(map(str, stated[0])); support['split'] = 'document'
                    rejected['split']['reason'] = 'The paper states ' + metric['split'] + ' (train/val/test), not ' + value + '.'
    # Claims about repeated runs need a quote that mentions runs; protocol definitions need protocol content.
    agg = metric.get('aggregation', 'unknown')
    if known(agg) and runs_key(agg) and support.get('aggregation') not in ('repository', 'researcher'):
        item = evidence.get('aggregation') or {}
        aq = (item.get('quote', '') if isinstance(item, dict) else '') + ' ' + metric.get('quote', '')
        if not re.search(r'(?i)\bruns?\b|seeds?|repeat|repetition|trials?|\btimes\b|±|standard deviation', aq):
            rejected['aggregation'] = {'value': agg, 'reason': 'The quote does not mention repeated runs.'}
            metric['aggregation'] = 'unknown'; support['aggregation'] = 'unsupported'
    md = metric.get('metricDefinition', 'unknown')
    if known(md) and support.get('metricDefinition') not in ('repository', 'researcher') and not re.search(r'(?i)mask|exclud|ignor|missing|zero|null|normaliz|scale|inverse|correct|official|differ(?:s|ent)? from|non-?standard|consistent|thresh|nan|filter', md):
        rejected['metricDefinition'] = {'value': md[:300], 'reason': 'Generic metric formula without protocol detail.'}
        metric['metricDefinition'] = 'unknown'; support['metricDefinition'] = 'missing'
    # Averaging over horizons must be stated near the result, in a field quote, or in the table labels.
    avg_words = r'(?i)averag|\bmean\b|\bavg\b|all (?:predicted |prediction )?(?:\d+ )?(?:steps|horizons|time slots)'
    cell_now = cell_context(source, metric.get('value', ''), metric.get('method', ''), metric.get('name', ''))
    labels = ((cell_now or {}).get('path', '') + ' ' + (cell_now or {}).get('caption', ''))
    for field in ('horizon', 'aggregation'):
        val = metric.get(field, 'unknown')
        if not known(val) or support.get(field) in ('repository', 'researcher'): continue
        claim = RUNS.sub(' ', norm(val).lower())
        if re.search(avg_words, claim):
            item = evidence.get(field) or {}
            texts = [item.get('quote', '') if isinstance(item, dict) else '', metric.get('quote', ''), labels]
            if not any(re.search(avg_words, RUNS.sub(' ', t)) for t in texts) and not re.search(avg_words, RUNS.sub(' ', near)):
                rejected[field] = {'value': val, 'reason': 'The source does not say these results are averaged over horizons.'}
                metric[field] = 'unknown'; support[field] = 'unsupported'
    # A table marker whose legend says the value was reported elsewhere means the number is cited.
    raw_value = norm(metric.get('value', ''))
    marker = next((c for c in '*∗⋆†‡' if c in raw_value or (cell_now and re.search(re.escape(raw_value) + r'\s*' + re.escape(c), cell_now['row']))), None)
    if marker and provenance_key(metric.get('provenance', 'unknown')) != 'cited':
        legend = re.search(r'[^.\n]{0,160}' + re.escape(marker) + r'\s*(?:are|is|denotes?|indicates?|means?|marks?)\s+(?:the\s+)?(?:results?\s+)?(?:reported|copied|taken|quoted|from the original)[^.\n]{0,160}', source)
        if legend:
            metric['provenance'] = 'cited'; evidence['provenance'] = {'quote': norm(legend[0])[:400], 'origin': 'paper'}
            metric['evidence'] = evidence; rejected.pop('provenance', None)
    # Interpretive fields need their own quote unless they are the default for the paper's own method.
    prov = provenance_key(metric.get('provenance', 'unknown'))
    item = evidence.get('provenance') or {}
    pq = norm(item.get('quote', '')) if isinstance(item, dict) else ''
    words = {'cited': r'(?i)report|original|taken|copied|cite|from the paper|literature|\*|⋆|marked', 'reproduced': r'(?i)\brun\b|\bran\b|re-?run|reproduc|re-?implement|implement|retrain|official code|our experiments|unif|tuned|train(?:ed)? (?:all|the|each)'}
    if prov in ('cited', 'reproduced') and not (pq and (item.get('origin') not in (None, 'paper') or (pq in doc and re.search(words[prov], pq)))):
        rejected['provenance'] = {'value': metric.get('provenance'), 'reason': 'No source quote says how this number was obtained.'}
        metric['provenance'] = 'unknown'; prov = 'unknown'
    if prov == 'own' and not (pq and re.search(r'(?i)ours|propos|our (?:model|method)', pq)) and not is_proposed(metric.get('method', ''), source, title):
        rejected['provenance'] = {'value': 'own', 'reason': 'This model is not the paper\'s proposed method, and the paper does not say how the number was obtained.'}
        metric['provenance'] = 'unknown'; prov = 'unknown'
    support['provenance'] = 'missing' if prov == 'unknown' else ('quoted' if pq else 'default')
    metric['provenance'] = prov
    cell = cell_context(source, metric.get('value', ''), metric.get('method', ''), metric.get('name', ''), metric.get('horizon', ''))
    METRIC = r'(?i)\b(mae|rmse|mse|mape|wmape|smape|error|accuracy|f1|loss|absolute|squared|percentage)\b'
    if known(metric.get('name', 'unknown')) and not re.search(METRIC, str(metric.get('name'))):
        # A metric name that names no metric (for example a dataset such as "PeMSD4") is not evidence of a metric.
        metric['name'] = 'unknown'; rejected['name'] = {'value': str(metric.get('name', ''))[:80], 'reason': 'Not a metric name.'}
    if not known(metric.get('name', 'unknown')) and cell:
        found = re.search(r'(?i)\b(mae|rmse|mape|mse)\b', cell['path'])
        if found:
            metric['name'] = found[1].upper(); support['name'] = 'derived'
    cellcheck = None
    if cell:
        path = cell['path'] + ' ' + cell['caption']
        cellcheck = {'path': cell['path'], 'caption': cell['caption'][:240],
                     'method': bool(known(metric.get('method')) and mentions(metric['method'], cell['path'])),
                     'metric': metric_key(metric.get('name', '')) in (metric_key(h) for h in cell['headers'] + cell['labels']) or metric_key(metric.get('name', '')) in path.lower(),
                     'horizon': (not known(metric.get('horizon'))) or supports(' '.join(numbers(metric.get('horizon', ''))[:1]) or metric['horizon'], path)}
        cellcheck['ok'] = cellcheck['method'] and cellcheck['metric']
        hz = re.search(r'(?i)horizon\s*\d+(?:\s*\(\d+\s*min\))?|@\s*\d+|\b\d+\s*(?:min|minutes|mins)\b|\b\d+\s*hours?\b|\b1 hour\b|\bavg\.?|\baverage\b|\bmean\b', cell['path'])
        cellcheck['horizonLabel'] = hz[0] if hz else ''
    notes = table_notes(source, (cell or {}).get('caption', ''))
    if notes and not metric_definition_key(metric.get('metricDefinition')) == 'nonstandard':
        # The paper itself says this table was computed differently and later corrected.
        problem = re.search(r'[^.]*(?:' + PROBLEM[4:] + r')[^.]*\.', notes[0], re.I)
        statement = norm(problem[0] if problem else notes[0])[:600]
        if known(metric.get('metricDefinition')) and support.get('metricDefinition') not in ('repository', 'researcher'):
            rejected['metricDefinition'] = {'value': metric['metricDefinition'], 'reason': 'Superseded by the paper\'s own correction note.'}
        if support.get('metricDefinition') not in ('repository', 'researcher'):
            metric['metricDefinition'] = 'non-standard per the paper\'s later correction: ' + statement
            evidence['metricDefinition'] = {'quote': statement, 'origin': 'paper'}; metric['evidence'] = evidence
            support['metricDefinition'] = 'quoted'; metric['superseded'] = True
    metric['checks'] = {'support': support, 'cell': cellcheck}
    metric['rejected'] = rejected
    metric['missing'] = [f for f in ('dataset', 'split', 'horizon', 'aggregation', 'metricDefinition', 'preprocessing', 'provenance') if not known(metric.get(f)) or (f == 'provenance' and metric.get(f) == 'unknown')]
    return metric


# ---------------------------------------------------------------- comparisons

def row(paper, metric):
    cell = (metric.get('checks') or {}).get('cell') or {}
    return {'paper': paper['id'], 'title': paper.get('title', ''), 'metric': metric.get('id'), 'verified': bool(metric.get('verified')), 'cellHorizon': cell.get('horizonLabel', ''),
            **{k: metric.get(k, 'unknown') for k in FIELDS + ('name', 'value', 'unit', 'direction', 'quote')}}


def month_range(text):
    """(first, last) (year, month) mentioned in a dataset description, or None."""
    months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    found = []
    for m in re.finditer(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(?:\d{1,2}(?:st|nd|rd|th)?,?\s*)?(\d{4})', text): found.append((int(m[2]), months[m[1].lower()]))
    for m in re.finditer(r'(?i)\b\d{1,2}/(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*/(\d{4})', text): found.append((int(m[2]), months[m[1].lower()]))
    for m in re.finditer(r'\b(0?[1-9]|1[0-2])/(\d{4})\b', text): found.append((int(m[2]), int(m[1])))
    return (min(found), max(found)) if len(found) >= 2 else None


def compare_pair(a, b):
    """Compare two reported results. Outcome is comparable, incompatible, or insufficient."""
    checks, caveats = [], []
    def add(field, status, detail): checks.append({'field': field, 'status': status, 'detail': detail})
    ta, tb = a['title'][:70], b['title'][:70]
    ma, mb = metric_key(a['name']), metric_key(b['name'])
    if not known(a['name']) or not known(b['name']): add('name', 'missing', 'The metric name is not stated for one result.')
    elif ma != mb: add('name', 'conflict', f"Different metrics: {a['name']} vs {b['name']}.")
    else: add('name', 'match', a['name'])
    da, db = dataset_identity(a['dataset'], a.get('datasetVersion', '')), dataset_identity(b['dataset'], b.get('datasetVersion', ''))
    if not known(a['dataset']) or not known(b['dataset']):
        add('dataset', 'missing', f"The dataset is unknown for {ta if not known(a['dataset']) else tb}.")
    elif da != db: add('dataset', 'conflict', f"Different datasets: {a['dataset']} vs {b['dataset']}.")
    else: add('dataset', 'match', a['dataset'])
    sa, sb = split_key(a['split']), split_key(b['split'])
    if not known(a['split']) or not known(b['split']):
        add('split', 'missing', f"The train/val/test split is unknown for {ta if not known(a['split']) else tb}.")
    elif sa and sb:
        if sa != sb: add('split', 'conflict', f"Different splits: {'/'.join(map(str, sa))} vs {'/'.join(map(str, sb))} (train/val/test).")
        else: add('split', 'match', '/'.join(map(str, sa)))
    elif norm(a['split']).lower() == norm(b['split']).lower(): add('split', 'match', a['split'])
    else: add('split', 'missing', f"The splits could not be normalized: \"{a['split']}\" vs \"{b['split']}\". Normalize them before comparing.")
    def hkey(r):
        k = horizon_key(r['horizon'], r['aggregation'], r['dataset'])
        label = r.get('cellHorizon') or ''
        if label and (not k['mode'] or not (k['minutes'] or k['steps'])):
            # The table column names the horizon (for example "Horizon 3", "60 min", or "Avg."): source-grounded.
            averaged = re.search(r'(?i)avg|average|mean', label)
            k2 = horizon_key(('average over ' if averaged else 'horizon ') + label + ' ' + (r['horizon'] if known(r['horizon']) else ''), 'average' if averaged else 'single horizon', r['dataset'])
            k = dict(k2, mode=k['mode'] or k2['mode'], minutes=k['minutes'] or k2['minutes'], steps=k['steps'] or k2['steps'], fromCell=True)
        return k
    ha, hb = hkey(a), hkey(b)
    if not ha['mode'] or not hb['mode']:
        who = ta if not ha['mode'] else tb
        add('horizon', 'missing', f"It is not stated whether the result for {who} is a single horizon or an average over horizons.")
    elif ha['mode'] != hb['mode']:
        add('horizon', 'conflict', f"These results use different horizon aggregation: {describe_horizon(ha)} vs {describe_horizon(hb)}.")
    else:
        la, lb = (ha['minutes'], hb['minutes']) if ha['minutes'] and hb['minutes'] else (ha['steps'], hb['steps'])
        if not la or not lb: add('horizon', 'missing', f"The horizon length cannot be matched: {describe_horizon(ha)} vs {describe_horizon(hb)}.")
        elif la != lb: add('horizon', 'conflict', f"These results use different horizons: {describe_horizon(ha)} vs {describe_horizon(hb)}.")
        else:
            add('horizon', 'match', describe_horizon(ha) + (' (steps converted with the dataset\'s 5-minute interval)' if ha['converted'] or hb['converted'] else '') + (' (horizon read from the table column)' if ha.get('fromCell') or hb.get('fromCell') else ''))
    ka, kb = metric_definition_key(a['metricDefinition']), metric_definition_key(b['metricDefinition'])
    if 'nonstandard' in (ka, kb) and ka != kb:
        add('metricDefinition', 'conflict', f"The source states that one metric was computed differently from the standard protocol: \"{a['metricDefinition'] if ka == 'nonstandard' else b['metricDefinition']}\".")
    elif ka and kb and ka != kb and not (ka.startswith('other:') or kb.startswith('other:')):
        add('metricDefinition', 'conflict', f"Different metric definitions: {a['metricDefinition']} vs {b['metricDefinition']}.")
    elif ka and kb and ka == kb: add('metricDefinition', 'match', a['metricDefinition'])
    else:
        add('metricDefinition', 'caveat', 'Metric definition (for example masking of missing values) is not stated for ' + (ta if not ka else tb) + '.')
        caveats.append(checks[-1]['detail'])
    ra_, rb_ = month_range(str(a.get('datasetVersion', ''))), month_range(str(b.get('datasetVersion', '')))
    if ra_ and rb_ and ra_ != rb_:
        caveats.append(f"Dataset time ranges differ: \"{norm(a['datasetVersion'])[:90]}\" vs \"{norm(b['datasetVersion'])[:90]}\".")
    ra, rb = runs_key(a['aggregation']), runs_key(b['aggregation'])
    if ra and rb and ra != rb: caveats.append(f"Run aggregation differs: {norm(a['aggregation'])[:80]} vs {norm(b['aggregation'])[:80]}.")
    for r, t in ((ra, ta), (rb, tb)):
        if r and r[0] == 'best': caveats.append(f"{t} reports the best of several runs, which favours that value.")
    # Independence: a cited copy of another paper's result is not separate evidence.
    independent, independence = True, ''
    same_method = method_key(a['method']) == method_key(b['method']) and method_key(a['method'])
    if a['paper'] == b['paper']:
        independent, independence = False, 'Both values come from one paper. They share a protocol but are a single source, not independent replication.'
    elif same_method:
        pa, pb = provenance_key(a['provenance']), provenance_key(b['provenance'])
        if 'cited' in (pa, pb) and a['value'] == b['value']:
            independent, independence = False, 'One value is cited from another paper. The two rows are the same underlying result.'
        elif a['value'] == b['value'] and 'own' in (pa, pb):
            independent, independence = False, 'The values are identical and one paper does not state where its number came from. Treat it as a possible copy.'
        elif 'cited' in (pa, pb):
            independent, independence = False, 'One value is cited from another source but does not match it exactly. Check the transcription.'
    statuses = [c['status'] for c in checks]
    outcome = 'incompatible' if 'conflict' in statuses else ('insufficient' if 'missing' in statuses else 'comparable')
    explanation = [c['detail'] for c in checks if c['status'] in ('conflict', 'missing')]
    favours = delta = relative = None
    try:
        va, vb = float(numbers(a['value'])[0]), float(numbers(b['value'])[0])
        if outcome == 'comparable' and a['direction'] == b['direction'] and a['direction'] in ('lower', 'higher') and math.isfinite(va) and math.isfinite(vb):
            better = (va < vb) if a['direction'] == 'lower' else (va > vb)
            favours = None if va == vb else ('a' if better else 'b')
            delta = round(abs(va - vb), 6); relative = round(100 * delta / max(abs(va), abs(vb)), 2) if max(abs(va), abs(vb)) else None
    except (IndexError, ValueError): pass
    if outcome == 'comparable':
        explanation = ['Dataset, split, horizon, and metric match.' + (' Values are human-verified.' if a['verified'] and b['verified'] else ' Extraction is not yet human-verified.')]
    return {'id': short_id(*sorted([f"{a['paper']}:{a['metric']}", f"{b['paper']}:{b['metric']}"])), 'a': a, 'b': b,
            'outcome': outcome, 'checks': checks, 'explanation': explanation, 'caveats': caveats,
            'independent': independent, 'independence': independence, 'verified': a['verified'] and b['verified'],
            'favours': favours, 'delta': delta, 'relative': relative}


def compare(papers, selected=None):
    rows = [row(p, m) for p in papers if not selected or p['id'] in selected for m in p.get('metrics', [])]
    pairs, skipped, horizons = [], 0, 0
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a['paper'] == b['paper']: continue
            if metric_key(a['name']) != metric_key(b['name']): continue
            if known(a['dataset']) and known(b['dataset']) and dataset_identity(a['dataset'], a.get('datasetVersion', '')) != dataset_identity(b['dataset'], b.get('datasetVersion', '')): skipped += 1; continue
            pair = compare_pair(a, b)
            hz = next((c for c in pair['checks'] if c['field'] == 'horizon'), None)
            if pair['outcome'] == 'incompatible' and hz and hz['status'] == 'conflict' and 'different horizons:' in hz['detail'] \
                    and sum(c['status'] == 'conflict' for c in pair['checks']) == 1 and 'single horizon' in hz['detail'] and 'average' not in hz['detail']:
                horizons += 1; continue  # 15 vs 60 minutes: nobody would compare these; counted, not listed
            pairs.append(pair)
    order = {'comparable': 0, 'incompatible': 1, 'insufficient': 2}
    pairs.sort(key=lambda x: (order[x['outcome']], x['a']['dataset'], x['a']['name']))
    summary = {k: sum(p['outcome'] == k for p in pairs) for k in order}
    summary['differentDataset'] = skipped; summary['differentHorizon'] = horizons
    return {'pairs': pairs[:400], 'summary': summary, 'rows': len(rows)}


# ---------------------------------------------------------------- retrieval for investigation

FIELD_QUERIES = {
    'split': r'split|training set|for training|train(?:ing)?\W{1,3}(?:validation|valid)|7\s*:\s*1\s*:\s*2|6\s*:\s*2\s*:\s*2|\d+\s*%\s*(?:of (?:the )?data)?\s*(?:is |are )?(?:used )?(?:for|as) (?:train|test|valid)|chronological',
    'horizon': r'horizon|steps? ahead|minutes? ahead|hour ahead|@\s?\d+|prediction length|predict the (?:next|following)|future \d+|\d+\s*steps',
    'aggregation': r'averag|mean of|over (?:all )?\d+ (?:prediction )?horizons|all steps|repeat|\bruns\b|seeds|times and report|best performance|standard deviation|±',
    'metricDefinition': r'missing values? (?:are|is) (?:excluded|ignored)|mask|null[_ ]?val|not_equal|zero|evaluation metric|calculat|correct(?:ion|ed)|official|mae_thresh|mape_thresh',
    'preprocessing': r'normaliz|z-?score|min-?max|interpolat|missing values|aggregated into|StandardScaler|scaler',
    'datasetVersion': r'\bsensors\b|ranging from|time range|from (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d|#time|timesteps',
    'provenance': r'reported (?:in|by|from)|original paper|taken from|we (?:re-?)?run|reproduc|official code|results with|marked with|\*|⋆|copied|literature|unify the evaluation',
    'dataset': r'\bdatasets? (?:is|are|contains?|consists?|records?)\b|released by|collected from',
    'method': r'\bbaselines?\b',
}


def passages(source, fields, method='', limit=8, size=900):
    """Rank source lines for the requested fields; return short passages with locations."""
    lines = [l for l in source.split('\n')]
    pattern = re.compile('|'.join(f'(?:{FIELD_QUERIES[f]})' for f in fields if f in FIELD_QUERIES) or 'experiment', re.I)
    mk = method_key(method)
    scored = []
    section = 'Front matter'
    for i, line in enumerate(lines):
        if re.match(r'^(?:\d+(?:\.\d+)*\.?\s+|[A-Z]\s+|Appendix\s+[A-Z]\s*)[A-Z][A-Za-z0-9 ,:&-]{3,80}$', line) and len(line) < 90: section = line.strip()
        if line.startswith('|') or len(line) < 40: continue
        hits = len(pattern.findall(line))
        if not hits: continue
        score = hits + (2 if mk and mk in method_key(line) else 0) + (2 if re.search(r'(?i)appendix|correction|update', section + line[:120]) else 0)
        if re.search(r'(?i)experiment|setup|setting|dataset|evaluation|metric|implement|baseline|result|appendix|reproduc', section): score += 2
        if re.search(r'(?i)related work|introduction|abstract|conclusion', section): score -= 3
        if score <= 0: continue
        scored.append((score, i, section))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out, used = [], set()
    for score, i, section in scored:
        if i in used or len(out) >= limit: continue
        text = lines[i]
        m = pattern.search(text)
        start = max(0, (m.start() if m else 0) - size // 2)
        snippet = text[start:start + size]
        out.append({'id': f'P{len(out) + 1}', 'origin': 'paper', 'location': section[:90], 'text': snippet})
        used.add(i)
    return out


GITHUB = re.compile(r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?=[\s/)\],.;:]|$)')


def repository_links(source):
    """Author code links, preferring ones introduced as the paper's own code."""
    found = []
    for m in GITHUB.finditer(source):
        owner, repo = m[1], m[2].rstrip('.')
        if owner.lower() in ('features', 'orgs', 'topics', 'about') or repo.lower() in ('issues', 'pulls'): continue
        context = source[max(0, m.start() - 200):m.start()].lower()
        own = bool(re.search(r'our code|code is available|codes? (?:and datasets )?(?:are |is )?available|source code|implementation|we implement|repository|artifact', context))
        issue = '/issues' in source[m.end():m.end() + 10]
        found.append({'owner': owner, 'repo': repo, 'url': f'https://github.com/{owner}/{repo}', 'own': own and not issue})
    seen, ordered = set(), []
    for f in sorted(found, key=lambda x: not x['own']):
        if f['url'].lower() not in seen: seen.add(f['url'].lower()); ordered.append(f)
    return ordered[:4]


REPO_FILES = re.compile(r'(?i)(readme|metric|eval|test|config|\.conf$|\.ya?ml$|data_?prep|generate_training|dataloader|load_dataset|train|run|util)')


def code_passages(files, fields, limit=8):
    """Relevant lines (with a little context) from repository files."""
    pattern = re.compile('|'.join(f'(?:{FIELD_QUERIES[f]})' for f in fields if f in FIELD_QUERIES)
                         + r'|ratio|train_?(?:size|rate|ratio)|val(?:id)?_?(?:size|ratio)|test_?(?:size|ratio)|num_(?:train|test|val)|\*\s*0\.[1-9]|horizon|out_steps|mask|null|thresh|mean\(', re.I)
    out = []
    for f in files:
        lines = f['text'].split('\n')
        hits = [i for i, l in enumerate(lines) if pattern.search(l)]
        blocks, last = [], -10
        for i in hits:
            if i - last > 6: blocks.append([i, i])
            else: blocks[-1][1] = i
            last = i
        for s, e in blocks[:4]:
            text = '\n'.join(lines[max(0, s - 3):min(len(lines), e + 4)])[:1200]
            out.append({'id': f'R{len(out) + 1}', 'origin': 'repository', 'location': f"{f['path']}@{f['sha'][:10]} lines {max(1, s - 2)}-{min(len(lines), e + 4)}",
                        'url': f['url'], 'text': text})
            if len(out) >= limit: return out
    return out
