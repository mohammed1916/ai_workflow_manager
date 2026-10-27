# Evaluation: comparison checks against a single-pass baseline

Status: 27 October 2026. Annotation by an AI coding agent, not yet reviewed by a domain researcher. The rules were tuned on the development split, and some development papers also appear in held-out cases. Treat held-out numbers as optimistic.

## What is measured

Each case asks whether two reported results can be compared: same dataset, split, horizon (single or averaged), metric definition, and a note on whether a value is copied from another paper. Each case gets one outcome:

- **comparable:** all stated context matches and nothing conflicts.
- **incompatible:** at least one stated field differs, or a source states a non-standard metric calculation.
- **insufficient:** nothing conflicts, but a context field needed for the comparison is not stated.

Two systems answer the same cases from the same arXiv HTML text:

- **Relay:** extracts each result with its context, checks the context against the source (quotes, table cells, appendix corrections, sensor-count dataset identity), runs an investigation for missing fields, then applies the same comparison rules.
- **Baseline:** one model call per case, given both full paper texts and the policy, returning the outcome directly.

Both systems use `nvidia/nemotron-3-super-120b-a12b` on Nebius Token Factory.

## Data

- 14 papers on traffic forecasting, from arXiv HTML full text.
- 47 target results (number, method, metric, and the context the paper states).
- 44 comparison cases: 24 comparable, 13 incompatible, 7 insufficient gold labels.
- 14 cases are held out by case ID. The held-out cases reuse papers from the development split.
- Gold labels are based on paper text only, not on author code. Each target and each gold context value carries a verbatim quote. `python3 eval/run.py --validate` confirms all 82 quotes and 47 table cells against the cached sources.
- Source: `eval/cases.json`. Cached text is gitignored (`eval/.cache/`).

Known annotation choices: a result whose paper says it is "computed differently" is incompatible even if the other side's definition is unstated. A cited baseline is labelled as cited only when a table legend or sentence says so.

## Results

Each row is one full run. The same code ran twice on the development split. Its Relay result changed by 7 of 30 cases, which shows the model's run-to-run variance.

| Run | Split | System | Accuracy | Comparable precision | Comparable recall | Wrongly accepted | Coverage |
|---|---|---|---|---|---|---|---|
| 063613 | dev (frozen code) | Relay | 0.77 | 0.86 | 0.71 | 2 of 13 | 0.77 |
| 063613 | dev (frozen code) | Baseline | 0.70 | 0.79 | 0.88 | 4 of 13 | 0.93 |
| 064358 | dev (same code) | Relay | 0.73 | 1.00 | 0.59 | 0 of 13 | 0.77 |
| 064358 | dev (same code) | Baseline | 0.70 | 0.77 | 0.77 | 4 of 13 | 0.93 |
| 063908 | held-out, run once | Relay | 1.00 | 1.00 | 1.00 | 0 of 7 | 0.79 |
| 063908 | held-out, run once | Baseline | 0.50 | 0.67 | 0.57 | 2 of 7 | 1.00 |

Reading the table:

- **Coverage** is the share of cases where the system gave a decisive answer (comparable or incompatible). A system that refuses everything scores 0 here, so accuracy must be read with it.
- **Wrongly accepted** counts cases where the system said "comparable" but the gold label is not. Relay accepted fewer wrong comparisons than the baseline in every run.
- **Relay's recall** on development runs ranged from 0.59 to 0.71. Most of its misses are "insufficient" answers where the gold label is comparable, and some are wrong metric names (see errors below). This is the main weakness.
- **Held-out:** 14 cases is small. A perfect score here is not a claim of general accuracy.

An earlier development run (`20261026-175214-dev`, before several fixes) is kept in `eval/results/` for history. It is not comparable to the runs above.

## Cost

Model time is summed across calls, so it is larger than wall-clock time, which is shown separately.

| Run | System | Model calls | Tokens | Summed model time | Wall time |
|---|---|---|---|---|---|
| 063613 (dev) | Relay | 63 | 230k | 736 s | 362 s |
| 063613 (dev) | Baseline | 30 | 900k | 701 s | 362 s |
| 063908 (held-out) | Relay | 37 | 157k | 418 s | 168 s |
| 063908 (held-out) | Baseline | 14 | 515k | 246 s | 168 s |

The baseline sends whole papers for every case, so it uses more tokens per case. Relay sends only the table block and ranked passages for each target. Both systems ran in the same process, so the wall time for each run is shared.

## Errors that remain

Dev run 063613 and dev run 064358 show the main failure patterns. Each item lists the case, what went wrong, and why.

1. **Metric name read as a dataset** (run 064358, cases C07, C08, C10, C19). The model put "PeMSD4" in the metric name field. Relay reported "Different metrics: PeMSD4 vs MAE" and marked the pair incompatible. The name check does not yet reject values that are not metric names. This is the most damaging error in the dev runs.
2. **Dataset unknown for GMAN** (both runs, cases C34 to C36). GMAN calls its 325-sensor data "PeMS". The model returned "unknown" for the dataset, so the sensor-count rule never ran and the pair was marked insufficient.
3. **Horizon not stated, but the table column says it** (run 063613, C10, C18, C19; run 064358, C17). The model left the horizon unknown for STAEformer and STID averages. The table caption and column label did not always make it into the extracted row.
4. **Provenance copied from a sentence about the table** (run 063613, `agcrn_dcrnn_p4`, `gwn_mla_mean`). The model wrote a table reference as the provenance, and the check did not reject it.
5. **Split misread for MTGNN** (both runs). The model returned 60/20/20 for the paper's 70/20/10 statement. Relay then compared it against the wrong split and reported a different outcome.
6. **Metric definition unknown when the paper states masking** (run 063613, `gwn_mla_15`; run 064358, `gwn_bay_60`, `pdf_dcrnn_p4`). The model returned "unknown", so the check treated the definition as unstated. Relay then marked a comparable pair insufficient.

Items 1 and 2 are the next fixes. Item 1 needs a name check that rejects dataset tokens and recovers the metric from the table column. Item 2 needs the sensor-count rule to run on the dataset name extracted from the table row or the paper's dataset passage.

## What this supports and what it does not

Supported by these runs:

- Relay wrongly called two cases comparable in one development run (C10), and none in the others. The baseline wrongly accepted four in each development run, including the cases that matter most: the GTS non-standard metric, MTGNN's split, and the "PeMS" dataset name.
- Relay refuses to decide more often than the baseline, so it misses comparable pairs. Its precision is high and its recall is not.

Not supported:

- A general accuracy claim for other papers, models, or fields.
- A comparison with a researcher's judgement. No researcher has checked the gold labels.
- Any claim about the model beyond these runs. Nemotron output varied between runs with identical code.

## Next steps

1. Add the metric-name check and dataset recovery described above. Rerun the development split. Then, and only then, run the held-out split again and report it as a second held-out run, not as the first.
2. Ask a traffic-forecasting researcher to check the 44 gold labels. Record disagreements in `eval/cases.json` and report them here.
3. Increase the number of papers and cases before making a rate claim. Fourteen papers is enough for a demonstration, not for a benchmark.
4. Repeat each development run at least three times and report the range, not a single number.

## Reproduce

```sh
python3 eval/run.py --validate           # check gold quotes and table cells
python3 eval/run.py --split dev          # development split, both systems
python3 eval/run.py --split heldout      # held-out split, run once per code version
```

Results are written to `eval/results/` with the code state, models, source hashes, and per-case outputs.

## Runs after the metric-name and dataset fixes (27 October, later)

Fixes made from development errors: a metric field that names a dataset is rejected and the metric is read from the table column; a dataset that is "unknown" is taken from the table column label and then resolved from the paper's sensor count. Code was frozen before these two runs.

| Run | Split | System | Accuracy | Comparable precision | Comparable recall | Wrongly accepted | Coverage | Failed |
|---|---|---|---|---|---|---|---|---|
| 070410 | dev | Relay | 0.80 | 0.93 | 0.77 | 1 of 13 | 0.80 | 1 |
| 070410 | dev | Baseline | 0.63 | 0.67 | 0.71 | 6 of 13 | 0.90 | 0 |
| 070559 | held-out | Relay | 1.00 | 1.00 | 1.00 | 0 of 7 | 0.79 | 0 |
| 070559 | held-out | Baseline | 0.71 | 0.78 | 1.00 | 2 of 7 | 1.00 | 0 |

Ranges across all runs so far, with the same policy and cases: the baseline ranged from 0.63 to 0.70 on dev and from 0.50 to 0.71 on held-out. Relay ranged from 0.73 to 0.80 on dev. Single runs are noisy for both systems, so compare ranges, not single numbers.

Cost, from the run records: dev Relay 64 calls and about 227k tokens; dev baseline 30 calls and about 893k tokens. Held-out Relay 40 calls and about 160k tokens; held-out baseline 14 calls and about 514k tokens.

**The one failed Relay case (dev, C16)** is a verifier refusal, not a crash. The starred value 21.19 sits in a table row the model could not tie to a verbatim quote, so Relay returned an error. It counts as a miss in these tables, and a refusal here is the intended behaviour.

**Reading these numbers honestly.**
- Dev numbers are tuned: the fixes above came from dev errors.
- The held-out split is a second look, not a clean test. Some of its papers also appear in dev cases, and the rules were tuned on dev. The held-out result is optimistic.
- Gold labels are from paper text, annotated by an AI coding agent, and not yet checked by a researcher.
- Relay never accepted more wrong comparisons than the baseline in any run here. That is the claim these numbers support. They do not show Relay has higher accuracy than the baseline, because on dev it sometimes does not.

**Status of the errors listed above:** the metric-name bug and the GMAN dataset gap are fixed in code and covered by tests. Their effect on these runs is in the table. The horizon and split errors remain.
