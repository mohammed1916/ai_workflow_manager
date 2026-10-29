# Relay Research — Check the Comparison

**A research agent that keeps published observations, comparison judgments, and human decisions separate.**

[Open Relay](https://relay-research.onrender.com/) · [Source repository](https://github.com/mohammed1916/ai_workflow_manager)

Built for the Nebius × NVIDIA Global AI Hackathon, Best Apps and Agents track. Runtime inference uses **NVIDIA Nemotron on Nebius Token Factory**. MIT licensed.

## Why Relay

Two papers can report the same metric while measuring different things. A result can be valid in its own experiment yet unsuitable for the researcher's comparison. Conversely, missing extracted context is not proof that a paper lacks the information.

Relay starts with a research question, collects source-addressed observations, and evaluates the conditions under which those observations can support a claim. Researchers inspect the evidence, investigate missing context, approve proposed changes, and carry the consequences into a cited manuscript. Saved executions and branches preserve how the argument changed.

The application does not substitute an example answer when a live run fails. Failed calls, unread passages, rejected extractions, and unresolved criteria remain visible. Recorded executions are explicitly labeled and make no new inference calls when opened.

## The workflow

1. **Question → comparison plan.** Nemotron proposes the alternatives, requested outcomes, analysis goals, and question-specific criteria. A separate model pass checks coverage against quoted requirements. Invalid structure receives a bounded repair; unresolved requirements stop the run before expensive paper extraction. The plan remains ready for human review.
2. **Discovery → available sources.** OpenAlex supplies scholarly candidates; arXiv supplies available full text. Optional Tavily search adds web-discovered paper references. DOI and arXiv references can be supplied directly. Seed-only mode intentionally skips discovery.
3. **Sources → observation inventory.** Relay walks overlapping passages of the retrieved text. The model identifies reported observations before judging their eligibility. Source-line and table-cell addresses are resolved against the actual text. Rejected output gets one repair; accepted observations survive failed repairs.
4. **Observations → context and scope.** A separate pass uses source-checked notes and table headers to assign entities, requested outcomes, and experimental conditions. Results outside the requested outcome remain saved but are excluded from that comparison queue. Unsupported assignments remain unknown.
5. **Context → provisional comparisons.** Nemotron assesses each criterion with evidence references from both results. Code checks references and missing required fields. Before a proposed pair can appear comparable, a separate model call rechecks entity identity, outcome meaning, and conditions against the original table blocks and surrounding prose. Missing source context or disagreement with that recheck withholds acceptance. This is another model check, not independent human verification. Outcomes are **comparable within scope**, **incompatible**, or **insufficient evidence**. Pending pairs are explicitly awaiting assessment. A comparable pair alone does not answer a causal hypothesis.
6. **Agent → human → investigation.** Review question coverage, source evidence, and comparison judgments separately. Investigate missing fields in retrieved papers, supported author repositories, and optionally Tavily web sources. Accept or reject source-linked proposals; unresolved investigations do not fabricate corrections.
7. **Revision → branch.** Revise criteria using inherited observations without discarding them. Entity/outcome assignments and semantic reviews are reassessed. Alternatively, continue discovery or explicitly re-extract. Checkpoints preserve the parent execution.
8. **Reviewed evidence → manuscript.** Draft a proposed-study abstract, cited related work, comparison discussion, and experimental controls. Corrections invalidate dependent claims. Review and regenerate them, then export LaTeX, BibTeX, and evidence for Overleaf.

The comparison engine contains no built-in dataset list, metric catalog, model-name prefix rule, scientific conversion, or universal matching tolerance. That is an architectural property, **not evidence of validated accuracy across every research field**.

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

The software checks currently pass **146 Python tests and 12 JavaScript tests**, including API loading of a recorded execution without inference. UI source syntax is checked; visual acceptance is left to the researcher, as requested. A successful provider call or completed source traversal does not prove complete extraction, correct interpretation, or an exhaustive literature review. Quote containment proves that text occurs in the source, not that the model understood it. Plans and semantic judgments can still be wrong and require expert review.

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
