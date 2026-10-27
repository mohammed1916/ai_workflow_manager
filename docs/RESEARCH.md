# Relay Research

A local hypothesis-to-manuscript workspace. Launch `python3 -m relay.server`, then open http://127.0.0.1:4280/. The original workflow application remains at `/index.html`.

## Research workflow

1. Select Ollama Cloud / GPT-OSS or a live Nebius model from the model menu. Credentials remain server-side. Ollama uses `OLLAMA_TEST_API_KEY`, falling back to `OLLAMA_API_KEY`.
2. Enter a hypothesis. The agent generates two complementary queries, searches OpenAlex, deduplicates up to 12 records, and attempts full-text retrieval from arXiv locations. Other records retain their abstracts and explicit coverage labels.
3. Explore the scrollable, zoomable topic map. Double-click a paper or click a metric to open its source, experimental context, exact quote, and review form. Topic families and metric fields can be corrected. Keyboard Enter opens paper nodes.
4. Drag papers into the comparison tray, or use Add to comparison in the drawer/library. Compare dataset, split, forecast horizon, metric, units, and evaluation protocol. Ranking is blocked without human verification and exact normalized matching context. Method names distinguish a paper's proposed model from its reported baselines. A best reported value is not statistical significance or a universal best paper.
5. Select reviewed papers for drafting and provide direction. The model writes a proposed-study abstract, cited related work, and an evaluation plan. It receives source text, approved metrics, and review notes. Citation keys must refer to reviewed records. The manuscript remains unapproved until the user checks it.
6. Edit `main.tex` and `references.bib`, save, and compile a real PDF with Tectonic. Download the ZIP to import as a new Overleaf project. No existing Overleaf project is modified.

## Compilation

Install the pinned official binary with `python3 scripts/install-tectonic.py`. First compilation downloads TeX resources and can exceed the 120-second request limit; retry after resources are cached. Subsequent standard article compilations are fast. Compilation logs are shown in the editor.

macOS `sandbox-exec` restricts personal/workspace reads and writes outside the individual build directory and Tectonic resource cache. TeX also runs in untrusted mode with a sanitized environment (no provider keys). Tests verify that sibling and absolute workspace reads fail. Compilation is refused on systems without this sandbox. The engine may read normal system libraries/resources. This is not an unrestricted shell runner.

## Evidence contract and limits

- Source quotes must occur in the retrieved/pasted text, and numeric values must occur in their quotes. This verifies text provenance, **not** correct interpretation of table columns. Human checking of context is required.
- Source coverage is bounded (first 65,000 full-text characters); assessment prioritizes experiment sections. PDFs without available arXiv HTML are not automatically parsed. Paste a table/experimental excerpt to enrich them; these excerpts remain visibly user-supplied.
- The relevance score is a model estimate, not a validated scientific-quality score. Retrieval is a bounded discovery pass, not a systematic review or exhaustive literature search.
- Suggested topics are hypotheses to investigate, not verified gaps. Without verified metrics, the UI withholds a performance conclusion.
- Exact context matching is conservative. Semantically equivalent free-text protocols may require manual normalization; unknown context is excluded.
- Reviews and edits use revisions; stale changes fail. Interrupted jobs are explicitly marked after restart. Per-paper reassessment provides recovery from an inference timeout.
- Model output can still misinterpret evidence or draft incorrect prose. Review source citations and scientific claims before using a manuscript.

## Official references

- OpenAlex API: https://help.openalex.org/api/
- OpenAlex works: https://help.openalex.org/data/works/
- arXiv API: https://info.arxiv.org/help/api/user-manual.html
- Tectonic installation: https://tectonic-typesetting.github.io/book/latest/installation/
- Overleaf recompilation: https://docs.overleaf.com/getting-started/recompiling-your-project
- Overleaf Git integration: https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization

Overleaf Cloud Git/GitHub integrations are premium features. The implemented path is local editing and compilation plus ZIP import; browser automation of an unrelated logged-in project is not an application integration.

## Evidence checks and what they do not do (27 October 2026)

- Every reported number carries dataset, split, horizon, aggregation, metric definition, and provenance. Missing fields are shown as missing, not guessed.
- Each model-claimed value is checked against the retrieved text. Values or quotes that are not in the source are rejected and listed on the result card.
- Table cells are located and their row and column labels are compared with the method and metric. A mismatch is shown as a warning.
- A paper's own correction or appendix note (for example "Table 1 was computed differently; see Table 4") marks the original value as non-standard.
- A dataset named only as "PeMS" is resolved from the sensor count stated in the paper.
- Comparisons return one of three outcomes: comparable, incompatible, or insufficient evidence. Missing context never produces "incompatible".
- A repository check reads the authors' code at a pinned commit. Repository evidence is labelled as such and is not used in the paper-only evaluation.

Limits:
- The model can still misread a table, and the verifier can still miss a misreading when the quoted text is correct but the reading is wrong.
- Comparisons in this app are only as complete as the papers provided. They are not a systematic review.
- A "comparable" label means the stated context matches and nothing conflicts. It does not mean the methods are equally well implemented.
- Every correction and proposal decision is recorded with its source and reason. Accepting a proposal changes the comparison; check the source first.

## Keys and hosting (27 October 2026)

- Hosted mode (`RELAY_HOSTED=1`): visitors enter their own key. It is held in memory only, for their work, and never saved or logged. The server ignores any key in its own environment.
- Local mode: keys can come from `.env`, as before.
- The statement "keys stay on the server" no longer applies to hosted mode; the key is sent by the visitor's browser with each request.
