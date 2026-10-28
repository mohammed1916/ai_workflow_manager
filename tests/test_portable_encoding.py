"""Windows defaults to a legacy text encoding. Every file read or write must name UTF-8 explicitly."""
import re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EncodingTests(unittest.TestCase):
    def test_every_text_read_and_write_names_utf8(self):
        offenders = []
        for folder in ('relay', 'scripts'):
            for path in (ROOT / folder).rglob('*.py'):
                if path.name.startswith('._'): continue
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                    if re.search(r'\.(read_text|write_text)\(', line) and 'encoding' not in line:
                        offenders.append(f'{path.relative_to(ROOT)}:{number}')
        self.assertEqual(offenders, [])

    def test_unicode_source_text_round_trips_through_the_store(self):
        import tempfile
        from relay.research import Research
        text = 'Mean MAE α = 2.99 ± 0.04 — “quoted” ∗ 𝐗'
        with tempfile.TemporaryDirectory() as d:
            r = Research(Path(d))
            paper = {'_full': text}
            r.store_source(paper)
            self.assertEqual(r.source(paper), text)


if __name__ == '__main__': unittest.main()
