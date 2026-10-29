# Relay Research — Check the Comparison

**Before you build on a paper’s results, check whether the comparison holds.**

[Open the hosted app](https://relay-research.onrender.com/) · [Public repository](https://github.com/mohammed1916/ai_workflow_manager) · [Download the source](https://github.com/mohammed1916/ai_workflow_manager/archive/refs/heads/main.zip)

Built for **Best Apps and Agents** in the Nebius × NVIDIA Global AI Hackathon. Powered by **NVIDIA Nemotron 3 Super on Nebius Token Factory**. MIT licensed.

## The research mistake Relay helps you catch

A benchmark table shows GTS reporting **2.99 MAE** for a 60-minute METR-LA forecast. A later appendix corrects the metric calculation and reports **3.41**. Treating either number as just another cell in a leaderboard can change the apparent argument for a new experiment.

Relay keeps the number attached to its table, experimental settings, and provenance. It investigates missing context in papers and author code, explains whether a comparison holds, and tracks which conclusions need revision after a correction. The example comes from [GTS, Appendix D](https://arxiv.org/html/2101.06861); these are reported results, not experiments run by Relay.

## The lesson from the earlier WebMCP project

The strongest lesson from our earlier winner analysis was **validation → feedback → correction**: human and agent should work on the same domain state, and the agent needs meaningful feedback when a result does not hold. Relay applies that lesson to experimental evidence. A source check or comparison conflict becomes an investigation; an accepted correction updates the shared evidence; dependent claims become stale; regeneration and saved branches make the consequences inspectable.

The workflow is deliberate: **question → source evidence → compare → investigate gaps → review a proposal → propagate the correction → revise the manuscript**. Starting discovery does not fabricate corrections. Investigations can return no answer, proposals require review, and unresolved context remains unresolved.

## What each service actually does

- **OpenAlex and arXiv:** initial scholarly discovery and available full-text retrieval.
- **NVIDIA Nemotron on Nebius Token Factory:** assess and extract evidence, reason over experimental context, propose source-linked corrections, and draft or revise the argument.
- **Tavily, when configured:** initial discovery retrieves web candidates and resolves arXiv paper links alongside OpenAlex; seed-only runs skip both searches. During investigation, Tavily also retrieves evidence for protocol fields that paper/code inspection has not settled. Add its key in Model settings, open a comparison with context gaps, and choose **Investigate**. Web passages retain source links and remain proposals for review.
- **Relay's deterministic checks:** source/table validation, three-outcome comparisons, revision conflicts, correction impact, and checkpoint integrity.

The Tavily fallback was live-smoke-tested on 28 October 2026 and returned four passages, including the MTGNN author repository. The receipt is in `data/research/tavily-search-receipt.json`. That verifies runtime retrieval; it does not establish a successful correction. The older prepared Nemotron studies predate Tavily integration and must not be presented as Tavily runs.

## Try it in two minutes

1. Open the [Research desk](https://relay-research.onrender.com/#screen=desk).
2. Choose **Load recorded study** or **Open prepared study**. Inspect the five-paper Nemotron study without making a new model call. Public source retrieval may take a moment.
3. Open **Comparisons** and inspect a result’s dataset, split, horizon, metric definition, and source evidence.
4. Open **Corrections** to inspect how a correction affected comparisons and manuscript claims. Inspect the saved before/after states through **Execution record**.
5. Open **Experiment & manuscript** to read the cited proposed study and export its LaTeX, bibliography, and evidence.
6. Choose **Open recorded discovery** for the separate four-paper search run, or **Run a fresh investigation** with your own Nebius key.

The prepared runs are genuine saved inference records, clearly labeled as recorded studies. Their source reviews were performed by agents/scripts. They are not independent researcher validation. Hosted PDF compilation is disabled; use the local app or export to Overleaf.

## What makes the workflow useful

| Research decision | What Relay provides |
| --- | --- |
| Can I reuse this reported baseline? | Three outcomes: comparable, incompatible, or insufficient evidence, with field-by-field reasons. |
| Why are these results inconsistent? | Paper and author-code investigations produce source-linked proposals. |
| Is this an independent result? | Own, re-run, cited, or unknown provenance stays attached to each number. |
| What changed after my correction? | Affected comparisons and manuscript claims are tracked; stale claims can be regenerated. |
| Can I inspect an earlier conclusion? | Immutable checkpoints and independent branches preserve saved states. |
| What experiment should I run next? | A proposed evaluation with shared experimental controls and a cited manuscript. |

## Where Nebius and NVIDIA are essential

Nemotron plans searches, assesses relevance, extracts experimental evidence, reasons over missing paper/code context, proposes corrections, synthesizes findings, and drafts or revises the manuscript. These are runtime calls to **Nebius Token Factory**, with provider, model, attempts, token usage, and call timing recorded. Source matching, comparison checks, revision protection, and file hashes run deterministically in Python.

The included fresh discovery record contains **four papers, 12 Nemotron calls, and 114,655 tokens**. The five-paper correction record contains **22 cumulative calls and 312,770 tokens**. The app exposes the actual call records and source evidence; it does not rely on a provider logo as proof of integration.

## Evidence, not a broad accuracy claim

**135 automated tests pass.** The latest small development evaluation accepted **1 of 13 non-comparable cases incorrectly**, versus **6 of 13** for a single-pass baseline using the same Nemotron model and papers. Relay’s decisive-answer coverage was **80%**, versus **90%** for the baseline. This illustrates the trade-off between caution and coverage.

The dataset is agent-annotated, development cases informed fixes, and held-out cases share papers with development. These results are demonstration evidence, not independently validated scientific accuracy. Full runs, failures, costs, and caveats are included below and in the app. The recorded accuracy evaluation covers **ML/time-series benchmark auditing**, particularly traffic forecasting; it does not validate the new question-specific comparison contracts across domains.

## Open the application

Requires Python 3.10 or later. The application has no pip or npm dependencies.

```sh
git clone https://github.com/mohammed1916/ai_workflow_manager.git
cd ai_workflow_manager
python3 -m relay.server
```

Open **http://127.0.0.1:4280/**. The first screen is the **Research desk**. It shows findings, recorded evaluation results, the prepared Nebius study, and the API catalog.

- **Open prepared study:** inspect comparisons, evidence, corrections, the manuscript, and saved execution states.
- **Run a fresh investigation:** use a question and optional arXiv papers; leave “Only analyze these papers” unchecked for literature discovery.
- **Executions & branches:** inspect saved checkpoints and continue from a chosen state.
- **Methods & setup:** opens this README. All project documentation is kept here.

On a clean checkout, choose **Load recorded study**. This imports two recorded live-run snapshots and checks source hashes. It makes no new inference calls. Public arXiv source text is downloaded when the local evaluation cache is absent; if a source version has changed, loading stops rather than silently substituting new text. Historical intermediate checkpoint metadata is retained as provenance, but only the two imported snapshots can be inspected or branched locally.

## Configure live inference

Create `.env` using `.env.example`:

```dotenv
NEBIUS_API_KEY=your_key_here
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
RELAY_PORT=4280
```

Use **Choose model** in the application to select Nebius Token Factory and a model from its live catalog. Existing projects retain their original model. Ollama Cloud is an optional development provider; it is not a substitute for the submission's required Nebius/NVIDIA runtime.

Credentials are never included in saved projects, source bundles, execution records, or API responses. Public paper text, the research question, and selected repository excerpts are sent to the selected model. Locally the server binds to loopback. Provider access and inference incur the account's normal usage.

## Research workflow

1. State a question. Optionally supply arXiv IDs or URLs for candidate baselines.
2. The agent plans complementary OpenAlex searches, retrieves available arXiv HTML, and extracts results with their experimental context.
3. Inspect source quotations, table cells, model names, datasets, splits, horizons, aggregation, preprocessing, metric definitions, and provenance.
4. Compare results. Outcomes are **comparable**, **incompatible**, or **insufficient evidence**. Missing evidence does not prove a conflict.
5. Investigate missing or conflicting settings. The agent searches paper passages and supported author repository files and presents proposals.
6. Review a proposal or apply a source-backed correction. A correction records before/after values and affected comparisons. Dependent manuscript paragraphs become stale.
7. Regenerate affected claims. Inspect changes and the saved earlier state. Branch when exploring alternatives.
8. Draft a proposed-study abstract, cited related work, comparison discussion, and experimental controls. Edit LaTeX and bibliography, compile locally, and export an Overleaf-compatible ZIP.

The agent does not universally control macOS or an existing Overleaf account. The old CSV/document handoff product and Chrome capture extension have been removed. Browser automation is not required to run or test Relay: the UI and API clients use the same backend endpoints.

## APIs inside the application

Open **Research desk → Explore application APIs**. The complete machine-readable catalog is available at `GET /api/schema`, with example request bodies.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/state` | Session token and provider availability, without credentials |
| `GET /api/desk` | Findings, evaluation summaries, prepared-study links |
| `POST /api/desk/load` | Idempotently load recorded study snapshots |
| `GET /api/research` | Project state, evidence metadata, corrections, drafts, call records |
| `GET /api/research/source?id=…&paper=…` | Retrieved source text, URL, and hash |
| `GET /api/research/checkpoint?id=…&node=…` | Inspect saved state with integrity verification |
| `POST /api/research/start` | Start discovery and extraction |
| `POST /api/research/compare` | Calculate comparisons from current evidence |
| `POST /api/research/investigate` | Investigate paper/code context gaps |
| `POST /api/research/update` | Review, correct, accept/reject, check a number, add paper, amend a draft, save edits |
| `POST /api/research/branch` | Copy a checkpoint or continue a research path |
| `POST /api/research/draft` | Draft from reviewed sources |
| `POST /api/research/regenerate` | Rewrite stale claims after corrections |
| `POST /api/research/compile` | Compile locally in the compiler sandbox |
| `GET /api/research/export/PROJECT` | Download LaTeX, BibTeX, and research evidence ZIP |

POST requests require `Content-Type: application/json` and `Authorization: Bearer TOKEN`, using the session token returned by `/api/state`. Use the project's current revision for edits. Stale revisions return a conflict rather than overwriting newer work. The token is a local session credential; do not commit it.

```python
import json, urllib.request
base = 'http://127.0.0.1:4280'
def get(path):
    return json.load(urllib.request.urlopen(base + path))
token = get('/api/state')['token']
body = {'hypothesis': 'Which forecasting baselines use comparable experimental protocols?',
        'provider': 'nebius', 'model': 'nvidia/nemotron-3-super-120b-a12b',
        'seeds': ['2101.06861', '1906.00121'], 'seedOnly': False, 'paperLimit': 4}
request = urllib.request.Request(base + '/api/research/start', data=json.dumps(body).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
project_id = json.load(urllib.request.urlopen(request))['id']
# Poll GET /api/research for status and execution events.
```

API reviews may include `actor: "agent"`; these are recorded as agent reviews. A checked review flag permits drafting; it does not turn an agent assessment into independent human validation. The prepared study's manuscript approval remains unchecked.

Discovery defaults to at most 12 papers and two search queries; `paperLimit` can be 2–12. An investigation can contain up to 20 papers after additions. These are bounded runs, not exhaustive systematic reviews.

## Recorded findings and sources

The prepared study concerns GTS, Graph WaveNet, MTGNN, AGCRN, and STAEformer. Numbers below are reported paper results; Relay has not reproduced the experiments.

- **GTS metric correction:** [GTS](https://arxiv.org/html/2101.06861) Table 1 reports METR-LA 60-minute MAE 2.99. Appendix D explains a different metric calculation; corrected Table 4 gives 3.41. Comparing a headline result without its appendix can change the apparent conclusion.
- **Paper/code split disagreement:** [MTGNN](https://arxiv.org/html/2005.11650) states training/validation/test percentages of 70/20/10. Its published data-generation code allocates 70% to training and 20% to testing, leaving 10% for validation. The interface retains the conflict and its provenance.
- **Metric masking:** [AGCRN](https://arxiv.org/html/2007.02842) and [STAEformer](https://arxiv.org/html/2308.10425) require inspection beyond dataset and metric labels. Author code can reveal different handling of zero targets. Matching metric names alone does not settle comparability.
- [Graph WaveNet](https://arxiv.org/html/1906.00121) provides another candidate baseline and source of protocol context.

Live records in `data/research/` contain real calls to `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory, including investigations, proposals, draft generation, a correction, and regeneration. The earlier full journey used five seed papers. Reviews and proposal decisions were performed by coding agents/test scripts. The records explicitly retain that attribution.

The records omit original TeX/BibTeX; importing renders these from the saved structured draft. Compilation must be performed on the installed build. Reconstructed TeX is not represented as the original live-run bytes.

A second saved run in `data/research/discovery-study.json` uses two seed papers plus two OpenAlex search queries, assesses four papers, and records 12 Nemotron calls (114,655 tokens). Two papers were source-reviewed by Codex with agent attribution. A focused check recovered GTS 2.99 with its appendix context. A source-reviewed manuscript amendment removes ambiguous generated claims; numeric results remain unverified. The local application contains a compiled PDF and a branch of this run. Choose **Open recorded discovery** to load its saved snapshot on a clean build.

## Evaluation and limitations

To check every number yourself, run `python3 scripts/verify_evaluation.py`. It rebuilds the table from the recorded run files in `eval/results/`, which are committed in this repository.


The evaluation dataset is in `eval/cases.json`; runs are in `eval/results/`. The Research desk displays the recorded metrics and caveats.

- 14 traffic-forecasting papers, 47 target results, 44 comparison cases.
- Gold labels were annotated by an AI coding agent, without independent domain-researcher validation.
- Development and held-out cases share papers. Rules were tuned on development material; held-out results are optimistic and are not a clean generalization test.
- Both Relay and the single-pass baseline use the same Nemotron model and source papers. Relay retrieves focused passages; the baseline receives full papers per case. Token comparisons therefore reflect different input strategies.
- Comparable precision must be read with recall and coverage. Refusing every comparison is not useful success.

Latest recorded runs after metric-name/dataset recovery fixes:

| Split / run | System | Accuracy | Comparable precision | Comparable recall | Wrongly accepted | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Dev / 070410 | Relay | 0.80 | 0.93 | 0.77 | 1 / 13 | 0.80 |
| Dev / 070410 | Single pass | 0.63 | 0.67 | 0.71 | 6 / 13 | 0.90 |
| Held-out, second look / 070559 | Relay | 1.00 | 1.00 | 1.00 | 0 / 7 | 0.79 |
| Held-out, second look / 070559 | Single pass | 0.71 | 0.78 | 1.00 | 2 / 7 | 1.00 |

The held-out set contains only 14 cases. Its perfect score is not evidence of general accuracy. Nemotron output varied across repeated runs. Remaining failures include misread splits, missed horizon/aggregation context, missing masking definitions, and ambiguous cited-result provenance. One development case was refused because its result could not be tied to a supporting quote; it counts as a miss.

New investigations generate an explicit question-specific comparison contract. Forecasting keeps specialized horizon checks; classification and general tasks use source-backed experimental factors chosen from the question. Named evaluation partitions are supported. Clinical and qualitative research are not independently validated, and non-numeric research is outside the current result-comparison workflow. A relevance score estimates hypothesis fit, not scientific quality. Source-quote and table-cell matching do not prove semantic correctness. Claim checks use heuristics and require review.

No new forecasting experiment, user study, independently validated time saving, or scientific discovery is claimed. A software agent can conduct source analysis, but cannot substitute for independent domain validation by relabeling its own reviews.

## Verify and reproduce

```sh
python3 -m unittest discover -s tests -v
python3 eval/run.py --validate
node --input-type=module --check < web/research.js
node --input-type=module --check < web/desk.js
node --input-type=module --check < web/execution.js
```

`--validate` checks 82 gold quotations and 47 table cells against cached/downloaded public sources. It is not a model inference run.

```sh
python3 eval/run.py --split dev
python3 eval/run.py --split heldout
```

These commands call Nebius and consume inference credits. Do not tune on the held-out split and then present it as unseen. API acceptance helpers in `scripts/live/` use `RELAY_URL` (default `http://127.0.0.1:4280`). Their review actions are scripted and must remain labeled accordingly.

Current automated verification: **135 tests pass**. JavaScript modules pass syntax checks. Tests cover source checks, comparison rules, provider separation, revision conflicts, correction propagation, stale-claim regeneration, immutable checkpoints, branch isolation, compiler restrictions, API origin/host/token enforcement, and saved-study imports. No GUI automation is required. Current changes have not received a visual browser review; the user will inspect the UI.

## PDF compilation

Install the project-local Tectonic compiler from its official release:

```sh
python3 scripts/install-tectonic.py
```

Then choose **Experiment & manuscript → Compile PDF**. macOS compilation uses a sandbox with restricted file access. LaTeX and evidence can be exported even without the compiler. Hosted compilation is disabled; use local compilation or import the ZIP into Overleaf.

## Project structure

- `relay/`: research engine, source checks, comparisons, API server, model providers, checkpoints, compiler.
- `web/`: research interface, research desk, execution graph, dark design and reduced-motion support.
- `data/research/`: recorded live study snapshots used by the application.
- `eval/`: annotated cases, evaluation runner, measured results. Downloaded full-text cache is ignored by Git.
- `tests/`: automated checks.
- `scripts/`: compiler installation, API acceptance, submission packaging.
- `.relay/`: local projects, retrieved source text, checkpoints, compiler and PDFs; never committed.

All documentation is in this README. LICENSE is the software license. `.env` is local configuration and must remain private.

## Your data and optional web search

Projects are saved in your browser, the way Excalidraw and Obsidian keep your work on your own machine. There is no account and no sign-in. Use **Your projects** to export a `.relay-research.json` file for a backup or to move a project to another computer, or to import one. Removing a project deletes only this browser's copy. The hosted server keeps working copies while it runs, and Relay restores them from your browser copy after a restart.

Keys are never saved in the browser's storage or in files. Your model key and optional Tavily key stay in this browser tab only and are sent with each request. Tavily is optional: when a paper leaves out a detail such as its evaluation protocol, Relay can search the web for it. Web passages are labelled as web sources with their links, and you still accept or reject every proposal. Without a Tavily key, Relay tells you once that the search is available.

## Running on Windows

The server and the web app use only the Python standard library, so they run on Windows with Python 3.10 or newer:

```
py -m relay.server
```

Then open http://127.0.0.1:4280 in Chrome or Edge. Text files are read and written as UTF-8 on every platform.

Local PDF compilation requires the macOS sandbox. On Windows, export the Overleaf ZIP and compile it with an appropriate local toolchain or import it into Overleaf instead.

Back up your work from **Your projects → Export file**. Keep the files in a folder you control, such as OneDrive or an external drive.

## Hosting and judge access

`render.yaml` is an optional hosting blueprint. It requires persistent storage and a service hostname. In hosted mode, server-side provider keys are ignored and visitors bring their own key through the model menu. This build is a shared workspace; it has no multi-user account isolation. Deploy a dedicated judge/test instance rather than storing confidential research in a public instance.

Hosted application: https://relay-research.onrender.com/. Source and local test build: https://github.com/mohammed1916/ai_workflow_manager. The hosted app uses visitor-supplied inference keys; recorded-study inspection does not require a new inference call. A public YouTube demonstration will be added after recording.

## Submission material

**Suggested title:** Relay Research — Check the Comparison

**Tagline:** A Nemotron-powered research agent that audits benchmark evidence, investigates protocol gaps, and revises conclusions when sources change.

**Problem:** ML researchers choose baselines from tables whose dataset versions, splits, forecast horizons, metric definitions, and result provenance can differ. A lower number can look persuasive while supporting a different experiment.

**Solution:** Relay combines Nemotron's paper/code reasoning with deterministic evidence checks, three-outcome comparisons, source-linked proposals, correction propagation, immutable branches, and cited proposed-study manuscripts. The researcher can inspect and revise the shared evidence state.

**Nebius/NVIDIA use:** Runtime calls to Nemotron on Nebius Token Factory power search planning, assessment, extraction, investigation, synthesis and drafting. Provider/model, attempts, tokens and latency are recorded. Comparison arithmetic and source integrity checks run locally.

**What is new in this event build:** The research product replaces the earlier document-handoff prototype. It adds table-aware extraction, source-addressed evidence, protocol investigations, comparison outcomes, dependent-claim invalidation, branching, manuscript/PDF export, an evaluation harness, live Nemotron research records, and the in-app API/research desk.

**Demo outline, under three minutes:** Show the question and live model → open GTS's result and appendix context → inspect an incompatible or uncertain comparison → show the agent's evidence proposal → apply a sourced correction → show affected claims and a prior branch → regenerate → display the cited manuscript and compiled PDF. Trim waiting periods and label shortened processing. Attribute agent reviews honestly; do not invent a successful outcome to fit the script.

**Technology feedback:** Recorded runs exposed empty extractions, response variability, occasional schema/citation issues, and confusion between table labels and protocol settings. Bounded retries, JSON repair, table-context validation and explicit unknowns improve recovery. See call records and evaluation failures for concrete evidence rather than attributing every error to the provider.

**Submission links:** [hosted application](https://relay-research.onrender.com/) · [public MIT-licensed repository](https://github.com/mohammed1916/ai_workflow_manager). The public YouTube video is pending recording. Final entry and eligibility declarations remain the submitter’s responsibility; consult the [event rules](https://nebiusglobalaihackathon.devpost.com/rules).

## License

MIT; see LICENSE. Third-party paper text and author code retain their own rights and licenses. Cached source text is not included in the source submission archive. Citation and source URLs remain attached to research records.

### Contextual explanations

Use the circled info buttons on the Research Desk, evaluation scores, investigation steps, evidence fields, review controls, and model settings. Explanations open separately from editors so unsaved corrections stay intact. Evaluation help defines denominators and discloses tuning and annotation limitations. “Authors’ own-method result” refers to the source paper’s experiment, never an experiment performed by Relay; unknown provenance remains unresolved until supported by evidence.

### Question-specific comparisons and revised investigations

Nemotron proposes a task and experimental factors from the question and branch direction. The comparison screen shows this contract for human review. Factors are dynamic (for example resolution, pretraining data, distillation, population, or budget), not a fixed traffic schema. Each extracted factor needs its own source quote. Unknown stays unknown; differing wording stays unresolved unless a concrete mismatch can be established. Top-1, top-5, and error metrics remain distinct; unnamed metrics are excluded from pairing. A comparable result is conditional on the selected criteria, not proof of causal superiority or statistical significance.

Use **Revise criteria in a branch → Re-extract evidence with revised criteria** to change the question, add conditions, or explicitly exclude a factor with a reason. Re-extraction resets the branch's reviews, proposals, corrections, and draft while preserving the parent checkpoint. **Reassess** updates relevance only. **New discovery** searches again, even if the original run was seed-only. Existing saved runs retain their original evidence and require re-extraction to adopt the new contract.

Tavily discovery records candidate URLs in `searchReceipts` and resolves arXiv candidates before extraction; search snippets are not treated as paper results. Missing keys or retrieval failures leave OpenAlex discovery available. The earlier traffic evaluation records describe the previous comparator, not a fresh cross-domain evaluation of this redesign.

Live validation on 29 October 2026 used Nemotron on Nebius to plan classification factors, extract two source-linked DeiT results, and propose a model-size correction from a quoted paper passage. The proposal remains ready for human review; unresolved fields were retained. The sanitized receipt is [data/research/protocol-smoke.json](data/research/protocol-smoke.json). This one-paper smoke test is not a cross-domain accuracy evaluation.

### Focus, inspect, investigate, review

Open an existing investigation's **Comparisons** view. Enter two model families (for example `ViT` and `DeiT`) under **Which models should be compared?** and apply the focus. This filters saved evidence without a model call. New comparison plans can supply this focus automatically. All models remains available; the scope count makes excluded pairs visible.

The current comparator consolidates duplicate evaluation-partition fields without rewriting the underlying evidence. Named validation partitions and redundant metric wording are normalized only when supported by the row's existing context. Explicit image dimensions such as `384²`, `384^{2}`, and `384×384` match. Flattened legacy values such as `3842` remain unresolved. Close/rounded parameter counts require review; they are not silently accepted or called incompatible. Non-distilled eligibility remains a separate requirement when the question requests it.

Click **Investigate blockers**, select up to six conditions, and optionally enter instructions. Only the selected one or two results are investigated. The agent inspects paper passages, available author code, and configured Tavily results. For resolution problems it can retrieve the original arXiv HTML again with preserved mathematical notation; the old source snapshot remains intact. Proposed corrections require review, then propagate to comparisons and dependent manuscript claims. Use a branch only when changing the question or experimental criteria; a full re-extraction is unnecessary for these deterministic comparison fixes.

On 29 October, a live Nemotron call proposed replacing the legacy `3842` resolution with the original paper's `384^{2}` notation for ViT-B/16. The focused call used 1,621 tokens. Its unaccepted proposal, quote, and usage receipt are in [data/research/notation-correction-smoke.json](data/research/notation-correction-smoke.json). This does not establish overall extraction accuracy. Legacy recorded studies retain their original parser output and source hashes; new retrieval preserves math notation.
