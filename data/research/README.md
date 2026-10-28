# Recorded research records

These files are saved outputs of Relay Research runs. The hosted site shows them so you can read a complete investigation without making new model calls. Each file is the project's own record: papers, extracted results, model calls, proposals, decisions, and drafts.

## Files

| File | What it records | Model calls | Tokens |
|---|---|---|---|
| `discovery-study.json` | Discovery from the question "Which published traffic forecasting results can serve as defensible baselines when forecast horizon and metric masking differ?" Four papers, 25 extracted results. | 12 | 114,655 |
| `before-correction.json` | Comparison of the METR-LA and PEMS04 baselines, before the GTS correction. Five papers, 33 extracted results, seven proposals. | 21 | 295,089 |
| `after-correction.json` | The same investigation after the GTS 2.99 metric-definition correction. Eight correction records; four claims were marked stale and then regenerated. | 22 | 312,770 |
| `tavily-search-receipt.json` | One live Tavily search, run on 28 October 2026, to test the runtime web search. It shows the search works. It does not show a correction was found. | n/a | n/a |

All three investigation files use `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory. They were run on 27 October 2026. API keys are not included.

## How the values were produced

1. **Papers.** Full text comes from arXiv HTML, and bibliographic data comes from OpenAlex. Each source text is stored with a SHA-256 hash.
2. **Extraction.** Nemotron returns each reported result as structured JSON. The code keeps a value only if it appears verbatim in the source text. Each context field (split, horizon, metric definition, and so on) is marked as quoted in the source, found nearby, missing, or rejected.
3. **Comparisons.** The comparison outcomes (comparable, incompatible, insufficient) are computed by code from the recorded context. The model does not decide them.
4. **Decisions.** Proposals and reviews were accepted or rejected by the process named in each file's `_recordNote`. In `before-correction.json`, five proposal decisions and the draft acceptance were made by `scripts/live/phase3.py`. In `after-correction.json`, the correction was applied by test code. In `discovery-study.json`, the reviews are recorded as agent reviews.
5. **Drafts.** The draft is generated from the reviewed papers. The claim check labels each paragraph as supported, provisional, attributed, descriptive, or unsupported.

## Limits

- The numeric metrics in `discovery-study.json` are recorded as unverified.
- Every review in these records is recorded as an agent or script decision.
- No new forecasting experiments were run.
- Some top-level `error` fields are stale. Each file's `_recordNote` explains which error was fixed afterwards.
- The records are a demonstration of the workflow, not a benchmark result. For the evaluation numbers, see `eval/` and run `python3 scripts/verify_evaluation.py`.
