# Relay Research

The main app is now an evidence-first research workspace: real paper discovery, topic maps, context-aware comparisons, reviewed LaTeX drafting, and local PDF compilation. See [the research guide](docs/RESEARCH.md) for setup, evidence guarantees, and current limits. Start with `python3 -m relay.server` and open http://127.0.0.1:4280/.

# Relay

**A little help between apps.** A local Mac workflow companion powered by NVIDIA Nemotron on Nebius Token Factory.

Relay turns selected notes and browser context into reviewable deliverables. You inspect and edit the exact plan; the companion saves the approved files and verifies their contents. The interface includes research, meeting-action, and project-handoff starters, a source shelf, plan revisions, rejection feedback, and an activity trail.

## Run

Requires Python 3.10+; no pip or npm dependencies.

```sh
python3 -m relay.server
```

Open http://127.0.0.1:4280. Keep the terminal running. The server binds only to loopback.

An offline sample works without credentials. It creates a **deterministic source packet**, not an AI summary. Sample notes describe a fictional product team. They are clearly labeled throughout the experience.

## Enable live Nemotron

Create `.env` locally using `.env.example` as a guide. Never commit it.

```dotenv
NEBIUS_API_KEY=your_key_here
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
```

Configuration is read at each live request. Choose **Nebius Token Factory** and your Nemotron model in the upper-right model selector, select your sources, and check the source-sharing checkbox. Only selected source text and the task are sent to Nebius. Keys stay in Python, never in frontend bundles, API responses, or the extension. The app validates the official provider endpoint and selected model against the live catalog. Exact model access depends on your account; use the catalog's API ID if yours differs.

## Try a complete workflow

1. Select **Notes to next steps**. The two fictional sample files are selected initially.
2. Build the workflow. Live mode synthesizes actions and decisions; demo mode packages source excerpts.
3. Open **View output**. Optionally edit the content; this increments the plan revision.
4. **Approve & run** saves a new directory under `workspace/outputs/<run-id>/`.
5. Inspect the receipt, download outputs, or reveal the directory in Finder.
6. Try **Request changes** instead of approving. Feedback is carried into the next workflow prompt.

Add your own `.md`, `.txt`, `.csv`, or `.json` files to `workspace/inbox`, or paste a source in the UI. Source files are limited to 100 KB, 8 selected sources, and 60,000 total characters per plan. Files in other folders are not scanned.

## Chrome capture extension

The optional Manifest V3 extension captures only the page or selection you explicitly preview and share. It is not installed automatically.

1. In Chrome, open `chrome://extensions` and load this repository's `extension/` directory as an unpacked extension.
2. In Relay → Connections, show the pairing code.
3. Open the extension on an HTTPS page, paste the code, and choose **Preview this page**.
4. Review or redact the text, then **Add this source to Relay**.
5. Select that source in your next workflow.

The extension uses `activeTab`, `scripting`, and session storage. It does not request access to every website or read background tabs. URL queries/fragments are omitted from captures. The pairing credential permits source ingestion only, not approval/execution. It expires when the companion restarts. The bundled extension expects port 4280.

## Supported actions and limits

- `write_file`: save complete, reviewed Markdown, text, CSV or JSON to a new run folder; verify SHA-256 against the approved content.
- `create_archive`: package only earlier approved outputs into a verified ZIP.
- `open_url`: hand an explicit HTTPS URL to macOS when it appears in the task or selected context. A successful OS handoff does **not** mean page contents were verified.
- User-triggered **Show in Finder**: open the completed output folder.
- Chrome extension: capture selected-page text into the source shelf.

This build does not perform arbitrary GUI clicks, unrestricted shell execution, emails, scheduled runs, or universal Mac automation. It is a focused source-to-deliverable workflow app. Integrity checks prove file contents match approval; they do not prove generated claims are true. Review the substance before use.

## Engineering boundaries

- Server-side action validation and strict flat output filenames.
- Per-plan revision checks and source fingerprints; stale approval is refused.
- Exclusive file creation in unique run folders; existing files are not overwritten.
- No model-generated scripts or commands executed.
- Origin, Host, Fetch Metadata and per-session token checks for the local API.
- Distinct extension pairing token restricted to source capture.
- Prompt treats source material as untrusted data; it cannot widen the executor's action allowlist.
- Failed plans never silently switch to offline output. One bounded schema-repair attempt is available.
- Partial results are preserved and visible on failure. Stop takes effect between actions, not mid-write.
- State survives restart in `.relay/state.json`; interrupted work is marked explicitly rather than rerun.

`.relay/` stores source snapshots, plans and run records locally. `workspace/outputs/` stores results. Both are ignored by Git. This is a single-user local companion, not a multi-user hosted service or a sandbox against another process running as your OS user.

## Test

```sh
python3 -m unittest discover -s tests -v
```

See [validation](docs/VALIDATION.md), [hackathon strategy](docs/STRATEGY.md), and [demo script](docs/DEMO.md).

## Model selector and complex workflows (updated)

Click the model pill in the top-right corner. Choose **Ollama Cloud** or **Nebius**, then select a model fetched directly from that provider. **Refresh models** fetches the current catalog. The selected provider/model is saved in this browser, and every run records the actual choice. A listed model may not support chat/JSON; provider errors remain visible rather than silently switching models.

Ollama testing uses `OLLAMA_TEST_API_KEY` from `.env` (preferred over `OLLAMA_API_KEY`), with `gpt-oss:120b` as the default. `OLLAMA_MODEL` can override the initial model. Requests use Ollama's native cloud `/api/chat`; discovery uses `/api/tags`. No credentials reach the browser. See https://docs.ollama.com/cloud.

The earlier NVIDIA-only validation has been replaced by provider catalog validation. Use Ollama/GPT-OSS for development; choose Nebius/Nemotron for the NVIDIA integration in the hackathon demonstration.

Two additional workflows support longer tasks:

- **Launch readiness review:** cross-source decisions, blockers, risk register, owner actions, checklist, and a launch-kit ZIP.
- **Metrics to decisions:** deterministic local CSV profiling (row counts, missing values, duplicates, numeric min/max/sum/mean), followed by a model-written trends report, experiment list, JSON quality report, and ZIP.

Plans support up to ten actions. `create_archive` can reference only outputs from earlier steps, preserves human edits, and verifies each ZIP member against its original file. Models still generate analyses and proposals; review recommendations and arithmetic that fall outside the local profile calculations.

## Research workspace: evidence checks (27 October 2026)

The research workspace checks whether two published results can be compared. It extracts each result with its experimental context, verifies each claim against the source text and table cells, and returns one of three outcomes: comparable, incompatible, or insufficient evidence.

- Reproduce the evaluation: `python3 eval/run.py --validate`, then `python3 eval/run.py --split dev`. See [the evaluation report](docs/EVALUATION.md) for results, limits, and known errors.
- Run the tests: `python3 -m unittest discover -s tests`.
- Live model runs use Nebius Token Factory with `NEBIUS_API_KEY` in `.env`. Live test scripts are in `scripts/live/`.

Limits: the interface has not been browser-tested, the gold labels are not yet checked by a researcher, and single evaluation runs vary.

## Hosted deployment (visitors bring their own key)

Set `RELAY_HOSTED=1` on the server. In this mode the server never uses a key from its own environment. Each visitor pastes their own Nebius or Ollama key in the app; the browser keeps it in the tab (session storage) and sends it with each request. The server holds it only in memory while that visitor's work runs, and never writes it to disk or logs it.

- Start command: `python3 -m relay.server`. Standard library only.
- Required: `RELAY_PUBLIC_HOST` set to the public hostname, and `RELAY_HOST=0.0.0.0`. The server rejects other Host and Origin headers.
- Persistent state lives in `.relay/`. Mount a disk there so investigations survive restarts.
- PDF compilation runs only on a computer with the macOS sandbox. In hosted mode the app refuses to compile and offers the ZIP to compile locally with Tectonic or import into Overleaf.
- Local-only features: opening links and revealing folders in Finder need macOS.
- Blueprint: `render.yaml`.

Local use is unchanged: keys can still come from `.env`, and PDF compilation runs inside the macOS sandbox.
