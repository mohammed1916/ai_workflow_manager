# Relay Research — Check the Comparison

**A research agent that keeps published observations, comparison judgments, and human decisions separate.**

[Open Relay](https://relay-research.onrender.com/) · [Source repository](https://github.com/mohammed1916/ai_workflow_manager)

Built for the Nebius × NVIDIA Global AI Hackathon, Best Apps and Agents track. Runtime inference uses **NVIDIA Nemotron on Nebius Token Factory**. MIT licensed.

## Why Relay

Two papers can report the same metric while measuring different things. A result can be valid in its own experiment yet unsuitable for the researcher's comparison. Conversely, missing extracted context is not proof that a paper lacks the information.

Relay starts with a research question, collects source-addressed observations, and evaluates the conditions under which those observations can support a claim. Researchers inspect the evidence, investigate missing context, approve proposed changes, and carry the consequences into a cited manuscript. Saved executions and branches preserve how the argument changed.

The application does not substitute an example answer when a live run fails. Failed calls, unread passages, rejected extractions, and unresolved criteria remain visible. Recorded executions are explicitly labeled and make no new inference calls when opened.

## Guided first: choose evidence before spending calls

**Guided** is the default in New investigation. Enter a question with the outcome you need (for example, top-1 accuracy) and the conditions that must match. Nemotron plans the criteria; Tavily and OpenAlex discover papers; Relay scans retrieved text for table candidates without inference.

1. Open **Select evidence**. Inspect table captions, headings, and source addresses. Select tables and individual rows. You can also paste an exact source excerpt and additional setup context.
2. **Extract selected evidence** makes bounded model calls for those selections, preserving existing results. It pauses before comparison. Unselected tables are available but are not claimed as analyzed.
3. Inspect the question coverage, choose candidate pairs, then **Assess selected comparisons**. Original-source rechecks still apply before a pair can be comparable. Results are labeled **Ready for human review**.

**Autonomous** retains whole-source extraction. Both modes expose a model-call and elapsed-time budget per execution stage (defaults: 30 logical calls / 15 minutes). A logical call may include provider retries or one JSON repair; the budget is not a price quote. Budgets are checked between operations, so an in-flight request can exceed the time boundary.

**Stop this run** cancels subsequent work for that investigation without restarting the website. The state becomes **Stopping** until the current operation returns, then **Stopped**. Completed evidence and checkpoints remain saved. A request already sent to the provider may finish and incur charges; its response is not applied after a stop request. Reopen Select evidence to scan saved sources and continue with a smaller selection.

Table scanning recognizes structured rows in retrieved text, not every table in every PDF. Captions are candidates for inspection. Image-only tables need a usable text source; exact-excerpt selection is available when automatic table detection misses the desired evidence. Selection submits work; it does not silently mark evidence or criteria as human verified.

## The full-source workflow

1. **Question → comparison plan.** Nemotron proposes the alternatives, requested outcomes, analysis goals, and question-specific criteria. A separate model pass checks coverage against quoted requirements. Invalid structure receives a bounded repair; unresolved requirements stop the run before expensive paper extraction. The plan remains ready for human review.
2. **Discovery → available sources.** OpenAlex supplies scholarly candidates; arXiv supplies available full text. Optional Tavily search adds web-discovered paper references. DOI and arXiv references can be supplied directly. Seed-only mode intentionally skips discovery.
3. **Sources → observation inventory.** Relay walks overlapping passages of the retrieved text. The model identifies reported observations before judging their eligibility. Source-line and table-cell addresses are resolved against the actual text. Rejected output gets one repair; accepted observations survive failed repairs.
4. **Observations → context and scope.** A separate pass uses source-checked notes and table headers to assign entities, requested outcomes, and experimental conditions. Results outside the requested outcome remain saved but are excluded from that comparison queue. Unsupported assignments remain unknown.
5. **Context → provisional comparisons.** Nemotron assesses each criterion with evidence references from both results. Code checks references and missing required fields. Before a proposed pair can appear comparable, a separate model call rechecks entity identity, outcome meaning, and conditions against the original table blocks and surrounding prose. Missing source context or disagreement with that recheck withholds acceptance. This is another model check, not independent human verification. Outcomes are **comparable within scope**, **incompatible**, or **insufficient evidence**. Pending pairs are explicitly awaiting assessment. A comparable pair alone does not answer a causal hypothesis.
6. **Agent → human → investigation.** Review question coverage, source evidence, and comparison judgments separately. Investigate missing fields in retrieved papers, supported author repositories, and optionally Tavily web sources. Accept or reject source-linked proposals; unresolved investigations do not fabricate corrections.
7. **Revision → branch.** Revise criteria using inherited observations without discarding them. Entity/outcome assignments and semantic reviews are reassessed. Alternatively, continue discovery or explicitly re-extract. Checkpoints preserve the parent execution.
8. **Reviewed evidence → manuscript.** Draft a proposed-study abstract, cited related work, comparison discussion, and experimental controls. Corrections invalidate dependent claims. Review and regenerate them, then export LaTeX, BibTeX, and evidence for Overleaf.

The comparison engine contains no built-in dataset list, metric catalog, model-name prefix rule, scientific conversion, or universal matching tolerance. That is an architectural property, **not evidence of validated accuracy across every research field**.

## Check one result under one condition

Open **Check one result**, search for the metric or method, choose a retained observation, and enter the condition to verify. Nemotron checks the reported result and the requested condition against source-addressed rows, headers, and relevant passages. The result is **Supported in retrieved source**, **Source conflict**, or **Insufficient evidence**, with quotations ready for review. This is a focused source check, not permission to ignore other required conditions in a broad comparison. Earlier comparison outcomes remain unchanged. Checks are evidence snapshots; rerun after changing evidence.

Workload selectors explicitly offer **1**, **2**, and larger/custom counts. One result per paper can supply two observations; one comparison means one pair. To compare two specific observations, select exactly one pair in Select evidence.

## Bounded paper workers and opening slides

[Open the four-slide introduction](https://relay-research.onrender.com/intro.html). Arrow keys advance; speaker notes, fullscreen, and print are available. Use the first two slides briefly, then demonstrate the real evidence. Keep the submission video under three minutes.

Guided extraction groups selected rows by paper and runs up to **two independent Nebius/Nemotron paper workers**. Select sequential processing if preferred. Each worker returns source-addressed observations to a coordinator; comparison selection and source rechecks happen afterward. Worker failures retain other papers' evidence. Active calls reserve a shared call budget, Stop prevents further requests, and execution checkpoints remain branchable. These are bounded extraction workers, not independent autonomous research teams.

A paired live trial on the same selected DeiT and T2T-ViT rows retained **12 observations using two model calls** in each mode: **40.05 seconds sequential**, **25.05 seconds with two workers**. Timing uses five-second completion polling and includes extraction only, excluding planning and later comparison checks. This single stochastic trial does not establish general speed, equivalent interpretations, or extraction accuracy. Inspect the recorded trial and model receipts from the research desk. Subsequent comparison work assessed six pairs: zero comparable, two labeled incompatible, and four unresolved; thirty other candidates were not assessed. These are unverified judgments, including questionable model-name interpretation, and remain available for human review. Parallel extraction does not fix semantic reasoning errors. The separate guided recording below remains the demonstration of accepted source-rechecked pairs.

Browser copies remain in **IndexedDB**; the backend keeps content-addressed sources and checkpoints. A vector index is not needed to inspect selected tables or validate exact source addresses. Add semantic retrieval only if measured evidence coverage needs it; retrieval similarity is not evidence that two experiments are comparable. No FAISS or Milvus dependency was added.

## Small cross-model diagnostic

[Raw prompts, sources, expected labels, outputs, and usage](data/research/model-comparison.json) · Re-run with `python3 scripts/compare_research_models.py` using your Nebius key. Re-running spends credits and replaces the receipt; results can vary.

On 2026-10-30, three available Token Factory models received the same six fixed tasks from DeiT and T2T-ViT source excerpts, with the same prompt, temperature 0.2, and 6,000-token output cap. One request per model; no repairs or retries. Expected answers were checked against the excerpts by the coding assistant, not an independent expert.

| Model | Exact value sets | Expected status labels | Time | Total tokens |
|---|---:|---:|---:|---:|
| Nemotron 3 Super | 6/6 | 6/6 | 15.73 s | 4,114 |
| Nemotron 3 Nano | 6/6 | 6/6 | 31.11 s | 5,868 |
| GPT-OSS-120B | 6/6 | 6/6 | 3.68 s | 3,047 |

**Correct labels were not always correct reasoning.** Nano attributed the Ti224/S224 incompatibility to input resolution, although both are 224 and the base variant differs. Super and GPT-OSS identified the variant conflict correctly. Every returned citation identifier exists, but citations were not consistently complete: Nano and GPT-OSS omitted headings, and Super did not consistently cite all metric/context headings. No unsupported acceptance appeared in the three deliberately conflicting/missing-condition cases.

This is a small development diagnostic on already-used papers, not a held-out benchmark, independent evaluation, full-pipeline test, or statistical model ranking. GPT-OSS was faster in this run; that does not establish general latency or cost superiority. Production remains on Nemotron Super; Nano and GPT-OSS were tested as alternatives, not silently substituted into the recorded investigations.

## Recorded guided accuracy investigation

Open **Research desk → Open guided results**. The saved [guided study](data/research/guided-study.json) records real Nemotron calls and two Tavily discovery queries. Two selected rows from DeiT Table 3 produce **8 top-1 accuracy observations**, **16 assessed pairs**, **3 comparable**, **12 incompatible**, and **1 insufficient-evidence** result. The three accepted, source-rechecked pairs report 72.2→74.5, 79.8→81.2, and 81.8→83.4 at matched 224-resolution variants. These are descriptive within-paper differences, not an independent experiment.

The fourth matched-column pair remains withheld by the model's interpretation of the mathematical header. Its values are retained; the paper is not claimed to omit them. The run includes 10 calls for selected extraction, comparisons, source rechecks, and synthesis; its inherited discovery plan used two additional calls. Recorded checkpoints preserve the real execution. Criteria, observations, and conclusions are **Ready for human review**, not marked human verified.

## What to inspect in the app

Start at the **Research desk**. Recent runs show actual retained results, calls, and tokens. If a recorded workflow validation is installed, its separate card opens the saved execution without inference. Historical comparator evaluations are labeled separately; they do not measure the current engine.

For a fresh investigation:

- Enter a question and optional DOI/arXiv references. Choose the model and workload under **Research scope**.
- Open **Comparisons** to inspect question coverage, hypothesis judgments, and per-paper extraction coverage. **All retained observations** lists every extracted result, including results outside the requested outcome scope and unresolved assignments. Search or filter the inventory, inspect source quotes, and expand pair-outcome reasons. Observation counts, reported metric-label counts, and assessed pair counts are distinct. A result may participate in several different pair outcomes; unassessed pairs are never counted as incompatibilities.
- Open a paper to inspect retained results, source lines, rejected claims, and retrieval/extraction failures. **Continue / retry unread passages** preserves successful work.
- Use **Assess pending comparisons** to process more pairs. Viewing or filtering saved pairs does not call a model.
- Use **Revise criteria in a branch** when the interpretation needs changing. This actually starts the selected agent continuation; it is not merely renaming a saved result.
- Inspect **Executions & branches** for checkpoints, model calls, and token usage.

Paper count, results per paper, and comparison workload support preset counts, a custom positive count, or **All available**. Batch sizes limit individual calls, not the selected total. All available means the retrieved candidate/source set, not all published literature. Discovery currently uses two queries, with up to 200 initial candidates per query for All available. Provider output limits and extraction failures can still reduce coverage.

## Where Nebius, NVIDIA, and Tavily are used

| Component | Actual responsibility |
| --- | --- |
| Nebius Token Factory + NVIDIA Nemotron | Search planning, requirement audit, relevance assessment, observation extraction, context completion, semantic comparisons, investigations, hypothesis synthesis, and manuscript drafting/revision |
| OpenAlex / arXiv | Scholarly discovery, metadata, and available source retrieval |
| Tavily, optional | Initial web discovery of scholarly references and investigation of unresolved context beyond retrieved papers/code |
| Relay's Python backend | Source-address checks, evidence fingerprints, queue handling, review attribution, revision conflicts, checkpoint integrity, and stale-claim tracking |
| Researcher | Review applicability, resolve uncertainty, approve corrections and manuscript claims |

Provider, model, call type, timing, attempts, and token usage are recorded. Tavily snippets do not become paper results merely because search returned them. Investigation passages retain source URLs and remain proposals.

The earlier Tavily runtime receipt is in [tavily-search-receipt.json](data/research/tavily-search-receipt.json). It verifies retrieval, not a successful correction. Seed-only validation runs do not demonstrate Tavily discovery. No universal macOS automation or connection to an existing Overleaf account is claimed.

## Run locally

Python 3.10 or later; no pip or npm dependencies for the application.

```sh
git clone https://github.com/mohammed1916/ai_workflow_manager.git
cd ai_workflow_manager
python3 -m relay.server
```

Open **http://127.0.0.1:4280/**. On Windows, use `py -m relay.server`.

Create `.env` from `.env.example`:

```dotenv
NEBIUS_API_KEY=your_key_here
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
RELAY_PORT=4280
```

Use **Choose model** to fetch the provider's model catalog and select a model. Existing projects keep their original selection. Add a Tavily key through model settings for optional web search. Inference consumes the provider account's credits; inspect recorded token usage when selecting a workload.

Credentials are excluded from project exports, model-call records, and API responses. Research questions and selected source text are sent to the chosen services. Local `.env` configuration remains private. Browser-entered keys stay in tab memory, not browser project storage.

## APIs in the application

**Research desk → Explore the APIs** displays the machine-readable catalog from `GET /api/schema`. UI and API clients use the same backend state and checks.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/state` | Session token and provider availability, without provider credentials |
| `GET /api/desk` | Recent runs and installed recorded validation |
| `POST /api/desk/load` | Load an explicitly selected recorded study |
| `GET /api/research` | Projects, evidence metadata, call records, corrections, and drafts |
| `GET /api/research/source?id=…&paper=…` | Retrieved source text, URL, and hash |
| `GET /api/research/checkpoint?id=…&node=…` | Inspect an integrity-checked saved state |
| `POST /api/research/start` | Start a question-specific investigation |
| `POST /api/research/compare` | Render saved comparison assessments |
| `POST /api/research/stop` | Stop one investigation; preserve completed evidence |
| `POST /api/research/scan-tables` | Scan retrieved source tables without model calls |
| `POST /api/research/extract-selected` | Extract chosen rows or exact excerpts, then pause |
| `POST /api/research/assess-comparisons` | Run model assessments for selected pending pairs |
| `POST /api/research/review-contract` | Record review of question coverage |
| `POST /api/research/review-comparison` | Review a current semantic assessment |
| `POST /api/research/investigate` | Investigate evidence gaps |
| `POST /api/research/update` | Review sources, correct results, decide proposals, retry extraction, add papers, or edit drafts |
| `POST /api/research/branch` | Branch and continue planning, discovery, extraction, or synthesis |
| `POST /api/research/draft` | Draft from reviewed sources |
| `POST /api/research/regenerate` | Rewrite stale claims |
| `POST /api/research/compile` | Compile locally in the supported sandbox |
| `GET /api/research/export/PROJECT` | Export manuscript, bibliography, and evidence |

POST requests require JSON and `Authorization: Bearer TOKEN`, using the session token from `/api/state`. Mutations require the current project revision; stale revisions cannot silently overwrite newer work. Review requests can identify `actor: "agent"`. Agent review cannot set a result, question coverage, or semantic assessment to human-verified.

## Validation and limitations

Run the software checks:

```sh
python3 -m unittest discover -s tests -v
node --test tests/web/*.test.mjs
node --input-type=module --check < web/research.js
node --input-type=module --check < web/desk.js
node --input-type=module --check < web/execution.js
```

Regression coverage includes complete passage traversal, partial-run resumption, preserving accepted evidence after repair failure, source-cell validation, required stratification, outcome scoping, human-review separation, plan failures stopping before extraction, branch preservation, correction propagation, portability, and revision conflicts. Fixtures across several disciplines test software behavior; they do not establish scientific accuracy.

To reproduce a live run on your own question, use the isolated validation command (consumes Nebius credits):

```sh
python3 scripts/validate_workflow.py --question "$RESEARCH_QUESTION" --seed "$PAPER_REFERENCE" --results 25 --comparisons 6 --output /tmp/relay-validation.json
```

Set those variables to your question and a DOI/arXiv reference. Repeat `--seed` for additional papers; add `--discover` to include scholarly and configured Tavily search. `--results all` reads all retrieved passages unless a call fails. The command saves failure receipts as well as successful runs and leaves application projects untouched.

The recorded real-paper validation is installed in [workflow-validation.json](data/research/workflow-validation.json) and opens from the Research desk. It contains **95 retained observations from two papers**, complete traversal of their retrieved text, and **six current pair assessments**. Dense-passage response failures were recovered by resuming with smaller source windows. The remaining comparison queue is explicitly pending; it is not counted as insufficient evidence.

The first-pass model incorrectly accepted three pairs. Rechecking original table context changed two to incompatible and one to insufficient evidence. The final current assessments are **zero comparable, five incompatible, and one insufficient**. This is a documented failure-and-recovery example, not an accuracy benchmark or evidence that these papers have no valid comparisons. Human verification remains outstanding. Manuscript wording flags are conservative lexical checks and can flag negated or cautious language; they are prompts for review, not semantic proof of a false claim. Citation-format failures also occurred during manuscript generation; explicit source handles and bounded validation repair were added.

Token counts in this record are cumulative across development continuations and repairs, not the cost of a single fresh investigation. Earlier development attempts and failed logical calls are retained. This was seed-only validation: it does not demonstrate discovery or Tavily usage.

The software checks currently pass **168 Python tests and 12 JavaScript tests**, including API loading of a recorded execution without inference. UI source syntax is checked; visual acceptance is left to the researcher, as requested. A successful provider call or completed source traversal does not prove complete extraction, correct interpretation, or an exhaustive literature review. Quote containment proves that text occurs in the source, not that the model understood it. Plans and semantic judgments can still be wrong and require expert review.

The retired traffic comparator and its runner have been removed. Historical receipts remain in `eval/results/`; `python3 scripts/verify_evaluation.py` reconstructs their recorded metrics. Those agent-annotated cases share papers between development and held-out sets and were used during tuning. Their scores must not be presented as accuracy for the current generic workflow. Earlier live records in `data/research/` also predate this redesign unless explicitly identified otherwise.

Source access is uneven. arXiv HTML is supported; other DOI records may provide only abstracts or metadata. Coverage describes retrieved text, not inaccessible content. Users can add source excerpts. Unknown fields are preserved rather than filled from unrelated example studies. No new scientific experiment, independent replication, researcher-validated accuracy, or measured time saving is claimed.

## Projects, hosting, and exports

Browser project copies support local persistence and import/export through **Your projects**. Back up a `.relay-research.json` file before moving machines. Removing a browser copy does not imply deletion of every server-side working copy.

The optional `render.yaml` configures persistent hosting. Hosted mode ignores server-side provider credentials; visitors supply their own key. This is a shared workspace without multi-user account isolation. Use a dedicated deployment for private research. Hosted PDF compilation is disabled.

For local macOS PDF compilation:

```sh
python3 scripts/install-tectonic.py
```

Then choose **Experiment & manuscript → Compile PDF**. The compiler uses the macOS sandbox. On other systems, or without the compiler, export the Overleaf-compatible ZIP.

## Repository

- `relay/`: backend, evidence pipeline, providers, API, checkpoints, and compiler.
- `web/`: research workspace, execution graph, contextual help, and API catalog.
- `tests/`: software regression checks.
- `data/research/`: explicitly labeled runtime records, not fallback answers.
- `eval/`: historical evaluation cases and receipts for the retired comparator.
- `scripts/`: installation, validation, and packaging utilities.
- `.relay/`: ignored local working state and source cache.

All project documentation is in this README. `.env` and `.relay/` are not committed. Third-party source text retains its original rights; source URLs and provenance accompany recorded evidence. Software license: [MIT](LICENSE).

## Submission story

**Relay makes the research argument inspectable:** what was retrieved, what was extracted, which conditions permit a comparison, what remains unresolved, and which claims change after review. The demo should follow one real execution through those decisions, including a limitation or failed assumption. Label cuts in processing time and distinguish recorded runs from fresh inference. Show a correction only if supported by the actual run; never manufacture one for the story.

[Hosted app](https://relay-research.onrender.com/) · [Repository](https://github.com/mohammed1916/ai_workflow_manager). The final public video and submission declarations remain separate deliverables.
