# Validation — 26 October 2026

## Automated

`python3 -m unittest discover -s tests -v`: **28 tests passed**, 3.813 seconds on the development Mac.

Covered real temporary-filesystem execution, human edits, content verification, changed/deleted sources, stale revisions, duplicate approval, rejected plans, invalid paths, duplicate output names, malformed CSV/JSON, unsupported actions, unsafe URL schemes, source symlinks, existing output preservation, restart recovery, input limits, missing credentials, provider schema repair, provider HTTP errors, official endpoint enforcement, and local HTTP access restrictions. Provider error/repair tests use mocks; the live smoke test below is separate.

## Browser and native Mac

Tested in the connected Chrome browser through UI interactions:

- App loads and renders its home, recipes, review screens and activity trail.
- Offline research recipe produces a clearly labeled source packet.
- Edit a proposed output; revision increases from 1 to 2.
- Approve revision 2; exact human edit survives in the saved file.
- Switch to live mode and explicitly select cloud sharing of fictional sample notes.
- Build a live meeting-notes plan, reject it with specific feedback, and rebuild.
- Rejection feedback survives a companion restart and appears in the next prompt.
- Edit the final decisions file to improve headings and source attribution.
- Approve the live plan; both output hashes match the approved bytes.
- Use Show in Finder; Finder visibly shows action-items.csv and decisions.md in the correct run folder.

## Live NVIDIA/Nebius result

Model: `nvidia/nemotron-3-super-120b-a12b` through `https://api.tokenfactory.nebius.com/v1`.

The initial live plan required automatic schema repair. Human review then identified a CSV comment prefix and missing private-beta decision. That plan was declined. CSV/JSON format validation and prompt instructions were strengthened. The subsequent live request succeeded in one provider call:

- Prompt tokens: 945
- Completion tokens: 1,573
- Total tokens: 2,518
- Approximately 9 seconds from planning start to review-ready (activity timestamps)
- `action-items.csv`: 377 bytes; four actions, including explicit Maya/Arun owners and Unassigned where the notes provided none.
- `decisions.md`: 324 bytes after human edit; includes private beta for 20 design partners and the unresolved PDF-export question.

Machine-readable evidence: [live-run-evidence.json](live-run-evidence.json). No API keys are included. The initial run's legacy usage record only counted the last provider attempt; current code aggregates attempts, covered by the repair test. Do not use the old record to claim total cost.

## Limits of this evidence

The optional Chrome extension was implemented and its restricted ingestion endpoint tested, but the extension was not installed or end-to-end tested. Mobile breakpoints are implemented but have not been browser-verified. The `open_url` adapter was not exercised in a live model run. Research and handoff recipes have not yet received their own live acceptance runs. No user study, accuracy benchmark, or measured time-saving claim is made. File integrity does not establish semantic correctness.

## Model selector and complex-workflow validation

After the provider/complex-workflow update: **38 tests passed**. New coverage includes credential separation and precedence, native Ollama model discovery and response parsing, deterministic CSV profiles, invalid CSV shape, archive dependency/path validation, and preservation of human edits inside a real ZIP.

Live browser acceptance used `OLLAMA_TEST_API_KEY` with **gpt-oss:120b**. The selector fetched 23 models from Ollama's `/api/tags` and defaulted to GPT-OSS 120B. The metrics recipe completed one provider call (2,894 total tokens), producing three reviewable documents and a dependent ZIP. Human review removed unsupported numerical impact predictions before approving revision 2. All four saved output hashes matched; all three ZIP members matched their source outputs, including the human edit. Evidence is in `ollama-live-evidence.json`.

This turn's live inference used Ollama, not Nebius. Nebius remains available in the selector, with existing prior live validation; its newly fetched catalog selector has not received separate browser acceptance. The new launch-readiness recipe has not had a separate live acceptance run. Arbitrary GUI automation remains outside this build's supported actions.

## Research workspace validation — 26 October 2026

- Live Ollama Cloud `gpt-oss:120b`, authenticated with the existing server-side environment key. Recorded evidence: `docs/research-live-evidence.json`.
- Accepted test hypothesis: graph neural networks versus transformers for traffic forecasting under comparable datasets and horizons.
- Two autonomous search queries retrieved 12 deduplicated OpenAlex records; available arXiv HTML was inspected. Six quoted metric rows remain in the final project. None are marked human-verified.
- PDFormer inference timed out once; focused per-paper reassessment recovered. D2STGNN's later extraction produced no accepted numeric quotes, so its performance rank is withheld.
- Model limitations contained incorrect claims about absent baselines/statistical tests. Validation corrected these against source text, added editable assessment fields, and prevented an unverified hypothesis conclusion. This is not a benchmark of extraction accuracy; source-quote matching does not prove table interpretation.
- Chrome verified: expandable topic families, double-click paper inspection, editable review checkpoint, pointer dragging two paper nodes into the tray, comparison view, and the absence of an unsupported winner.
- Two coding-agent review notes enabled a test draft; these were explicitly not user approval. GPT-OSS generated a proposed-study abstract, related work with two valid paper citations, and an evaluation plan. Human manuscript approval remains unchecked.
- Actual Tectonic compilation produced a three-page PDF. All three pages were rendered with Poppler and visually inspected. Chrome displays the compiled PDF alongside the LaTeX editor. BibTeX has missing-journal/spacing warnings, not missing citations or fatal errors.
- ZIP contents verified: `main.tex`, `references.bib`, `evidence.json`. No existing Overleaf project was edited.
- 53 automated tests pass, including source-quote/value validation, conservative comparability, stale revisions, review-before-draft, topic normalization, escaped Markdown-to-LaTeX conversion, and compiler sandbox denial of parent/absolute file reads. Python compilation and `git diff --check` pass.
- Screenshots: `docs/research-map.png`, `docs/research-manuscript.png`.

Research-specific live Nemotron/Nebius testing, external user evaluation, and an annotated extraction benchmark remain submission preparation work. The earlier generic-workflow Nebius test is not counted as research-agent validation.
