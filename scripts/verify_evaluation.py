"""Rebuild the evaluation table from the recorded run files in eval/results/.

Run from the repository root:  python3 scripts/verify_evaluation.py
Every number printed comes from the committed JSON records; nothing is typed in.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pct(value):
    # Round half up, the usual convention for reporting.
    return f"{int(value * 100 + 0.5)}%" if value is not None else "n/a"


def main():
    rows = ['| Run | Split | System | Accuracy | Comparable precision / recall | Wrongly accepted | Coverage |',
            '|---|---|---|---|---|---|---|']
    for path in sorted((ROOT / 'eval/results').glob('*.json')):
        if path.name.startswith('.'): continue  # macOS metadata files are not records
        record = json.loads(path.read_text(encoding='utf-8'))
        for key, label in (('relay', 'Relay'), ('baseline', 'Single-pass baseline')):
            s = record['summary'].get(key)
            if not s: continue
            rows.append(f"| {path.stem} | {record['split']} | {label} | {pct(s['accuracy'])} | "
                        f"{pct(s['comparablePrecision'])} / {pct(s['comparableRecall'])} | "
                        f"{s['incorrectlyAccepted']} / {s['goldNotComparable']} | {pct(s['coverage'])} |")
    print('\n'.join(rows))
    print('\nLabels: annotated by an AI coding agent; not checked by a domain researcher.')


if __name__ == '__main__':
    main()
