# Handoff: evidence-quality work in progress

Last updated: 27 October 2026. Nothing is committed yet. All work is in the working tree.

## Goal

Reposition Relay Research for the Best Apps and Agents track as: "Before you build on a paper's results, check whether the comparison holds." The plan came from an external review pasted into the session. Its priorities, in order:

1. Run the research workflow live on Nemotron through Nebius.
2. Make experimental evidence the central object, with explicit missing fields and own vs cited results.
3. Turn "not comparable" into an investigation with three outcomes: comparable, incompatible, insufficient evidence.
4. Propagate corrections to comparisons and manuscript claims, regenerate after review, keep the old state as a branch.
5. Build a small honest evaluation against a single-pass Nemotron baseline.
6. Test with researchers and record a demo (user's job; not started).

## State of the code

All 97 tests pass: `python3 -m unittest discover -s tests`. JavaScript passes `node --check`.

| Area | Where | Status |
|---|---|---|
| Evidence records, table-aware HTML parser, cell checks, normalizers, three-outcome comparisons, retrieval | `relay/evidence.py` (new) | Done, tuned on dev data |
| Research engine: source store, arXiv seed papers, split assess/extract calls, retries and JSON repair, investigation proposals, corrections with propagation, stale-claim regeneration, claim checks, targeted "check a number" | `relay/research.py` | Done |
| Provider timeout, output limit, HTTP status on errors | `relay/providers.py` | Done |
| Routes `/api/research/investigate` and `/api/research/regenerate` | `relay/server.py` | Done |
| UI: journey tabs, evidence cards, pair cards, proposals, corrections timeline, claim badges, model call records, check-a-number form | `web/research.js`, `web/research-design.css`, `web/execution.js` | Done, never opened in a browser |
| Evaluation set and harness | `eval/cases.json`, `eval/run.py` | Done; needs a rerun |
| Live API scripts | `scripts/live/` | Port 4281, isolated copy (see below) |
| Docs: EVALUATION | `docs/EVALUATION.md` | Written |
| Docs: README, RESEARCH, VALIDATION, STRATEGY, DEMO | `docs/` | Not updated yet |

## Real, source-verified findings for the demo

All verified from arXiv HTML and author repositories on 26 October 2026.

- **GTS (arXiv 2101.06861):** Table 1 reports METR-LA 60-minute MAE 2.99. Appendix D says that version "calculated the evaluation metrics MAE/RMSE/MAPE in a manner slightly different from that used to report the results of DCRNN in the official publication". Corrected Table 4 gives 3.41. Against Graph WaveNet's 3.53 (arXiv 1906.00121, Table 2), the apparent 15% gain becomes about 3.4%. STEP (2206.09113) re-ran GTS under unified evaluation: 3.46, best of five runs.
- **MTGNN (2005.11650):** says it follows DCRNN but states "training set (70%), validation set (20%), and test set (10%)". Its code `generate_training_data.py` uses `num_test = round(num_samples * 0.2)` and `num_train = round(num_samples * 0.7)`, which is 70/10/20. On paper text, MTGNN vs Graph WaveNet is incompatible; with the code evidence it becomes comparable.
- **AGCRN (2007.02842) vs STAEformer (2308.10425) on PEMS04:** both 6:2:2 and both averaged over 12 horizons. STAEformer states this: "we select the average performance of all predicted 12 horizons". (An earlier claim in this session that STAEformer does not state it was wrong.) Neither paper states the metric definition. Code: STAEformer `lib/metrics.py` masks zero targets (`np.not_equal(y_true, 0)`); AGCRN `model/PEMSD4_AGCRN.conf` sets `mae_thresh = None`, so MAE is unmasked. Paper-only says comparable with a caveat; code makes it incompatible.
- **Baseline spread:** DCRNN on PEMS04, all stated 6:2:2: 19.63 (STAEformer), 19.71 (STID), 21.22 (AGCRN), 22.737 (PDFormer), 24.70 (STFGNN). BasicTS+ (2310.06119) Table I documents the same problem, with gaps up to 33%.
- **Cited copies:** Graph WaveNet and MTGNN print DCRNN METR-LA 1-hour RMSE as 7.60. DCRNN's own table says 7.59. MegaCRN says most baselines are "reported from their original papers".

## Live Nemotron runs so far

- Model: `nvidia/nemotron-3-super-120b-a12b` on Nebius. The key works; five Nemotron models are in the catalog.
- Seeded run (five papers, seed-only): about 5 to 6.5 minutes, 12 to 13 calls, all papers extracted, all cells matched. One empty extraction per run is common; the logged retry recovers it.
- Investigations with repository retrieval worked on all four repos, pinned to commits. They proposed STAEformer masking (code), Graph WaveNet masking (paper), and MTGNN masking (code). They did not yet find MTGNN's code split, and left AGCRN masking unresolved. Code-pattern and prompt fixes for both were made afterwards and are untested live.
- 27 October journey (see item 4 above): proposals, draft, compile, export, and branch ran live. Regenerate after a correction did not run live.

## Evaluation status

- `eval/cases.json`: 14 papers, 47 target results, 44 cases (24 comparable, 13 incompatible, 7 insufficient). 14 cases are held out by paper. Gold labels come from paper text only, each with a verbatim quote. The annotator is Claude, not yet reviewed by a researcher; say so in any write-up.
- `python3 eval/run.py --validate` confirms all 82 gold quotes and 47 target cells against the sources.
- Dev run 1 (`eval/results/20261026-175214-dev.json`) used code from before the latest fixes. Do not report it as the final result:

| System | Accuracy | Comparable precision | Comparable recall | Wrongly accepted | Coverage |
|---|---|---|---|---|---|
| Relay | 0.60 | 1.00 | 0.47 | 0 of 13 | 0.63 |
| Single-pass baseline | 0.77 | 0.82 | 0.82 | 3 of 13 | 0.90 |

The baseline accepted the GTS and MTGNN traps. Relay's low recall came from parsing problems that have since been fixed (horizon formats, single vs average, dataset-aware splits, sensor-count dataset identity, "own" provenance, generic formulas).

## Progress since the first handoff (27 October 2026)

Done:

1. The three evidence fixes: proposal detection (GMAN no longer flags Graph WaveNet, STID is found after "i.e."), every ratio in a sentence is read, and ratios are scoped to the named dataset. Regression tests added.
2. Four more fixes found on dev: average horizon span uses the longest horizon or steps times the sample interval; unknown metric names are recovered from the table column; bare "PeMS" is resolved from the paper's sensor count; `runs_key` crashed on words such as "ten" (a real app bug, now fixed and tested). 101 tests pass at that point (105 now).
3. Evaluation rules frozen. Dev runs 063613 and 064358 used identical code and differed on 7 of 30 cases, so model variance is large. Held-out split run once: Relay 1.00 accuracy on 14 cases, baseline 0.50.
4. `docs/EVALUATION.md` written. It lists the remaining errors. The held-out number is optimistic because rules were tuned on papers shared with held-out cases.

Remaining, in order:

1. DONE 27 Oct: metric-name bug fixed (dataset-like names rejected; metric read from column). Dev and held-out rerun on the fixed code: see docs/EVALUATION.md, "Runs after the metric-name and dataset fixes".
2. DONE 27 Oct: GMAN dataset gap fixed (dataset read from the table column, then resolved from the sensor count).
3. Researcher check of the 44 gold labels (needs a person).
4. Live Nemotron journey: DONE on 27 October. Investigations, proposals, draft, PDF, ZIP, and branch in `docs/research-nemotron-evidence.json`. A correction (GTS 2.99 metric definition, applied by test script) marked 4 claims stale, and regeneration cleared them, in `docs/research-nemotron-evidence-correction.json`. Not yet live: a researcher applying the correction, and a fresh draft after the citation fix.
5. BLOCKED: open the UI in a browser. No browser tool was available on 27 Oct. Needs a browser session.
6. DONE 27 Oct: `README.md`, `docs/RESEARCH.md`, `docs/VALIDATION.md`, `docs/STRATEGY.md`, `docs/DEMO.md` (appended sections; older content kept).
7. Ask the user before committing, pushing, or hosting. Hosting a build that holds a Nebius key on a server is the user's decision.
8. Devpost rules could not be fetched on 27 Oct (HTTP 403). Verify the submission requirements on the event page.

## How to resume

- The user's own Relay server runs on port 4280 (process 97976 at the time of writing) with the **old** code. Do not run a second server against the repository's `.relay/` folder, because two servers overwrite each other's state. Ask the user to restart theirs to load the new code.
- For live tests, make an isolated copy outside the repo (excluding `.git`, `.relay`, `workspace`), copy `.env` with `RELAY_PORT=4281`, copy `.relay/bin/tectonic`, and run `python3 -m relay.server --port 4281` from the copy. The previous copy lived in a session scratchpad and may be gone.
- `scripts/live/client.py` talks to port 4281. Phase scripts write `project_id` in the working directory, so run them from a scratch folder.
- `eval/.cache/` holds the 17 arXiv HTML files (gitignored; the harness re-downloads them if missing).
