// Contextual help stays separate from editor dialogs so unsaved inputs remain intact.
const topics = {
  "focused": ["Check one result", "Verify a retained result and your specified condition against retrieved source rows, headings, and relevant passages. This does not prove that two results satisfy every condition of the original hypothesis. Supported, conflicting, and unresolved findings retain source quotes and remain ready for human review."],
  "guided": ["Guided evidence selection", "Tables are detected from retrieved text without inference. Select rows and exact supporting context, then extract the requested outcomes. Inspect the proposed criteria and choose pairs before assessment. Comparability is a source-supported interpretation, not independent replication. Stop prevents subsequent requests; a request already sent may finish and be billed."],
  "source-coverage": ["Retrieved source coverage", "Shows how much retrieved text was supplied to the model, the observations returned, rejected source claims, and retained results. Reading every passage does not prove exhaustive extraction or scientific correctness. Partial coverage can be resumed without discarding accepted results."],
  "evaluations": [
    "How evaluations work",
    "These are recorded comparison-classification runs, not new experiments on forecasting models. Labels were annotated by agents, not independently validated by domain experts. Development cases informed tuning; held-out cases share papers with development, so they are not a clean unseen-domain test. Read accuracy together with coverage and wrong acceptances."
  ],
  "cases": [
    "Development cases",
    "A case is a pair of published results with an annotated comparison outcome. Several cases can come from the same paper. The case count is not a count of independent papers, users, or experiments."
  ],
  "accuracy": [
    "Outcome accuracy",
    "Correct predicted outcomes divided by all evaluation cases, including failed cases in the denominator. The three labels are comparable, incompatible, and insufficient evidence. Correctly withholding judgment can count as correct. Development accuracy is measured on tuned data, not a general reliability guarantee."
  ],
  "precision": [
    "Comparable precision and recall",
    "Precision: correctly accepted comparable pairs divided by all pairs predicted comparable. Recall: correctly accepted comparable pairs divided by all pairs annotated comparable. A dash means the denominator is zero. These depend on the quality of the annotated labels."
  ],
  "wrong": [
    "Wrongly accepted comparisons",
    "Pairs predicted comparable even though their reference label is incompatible or insufficient evidence. The denominator shown is all reference non-comparable pairs. Lower is better; inspect these errors before trusting a baseline claim."
  ],
  "coverage": [
    "Decisive-answer coverage",
    "Cases labeled comparable or incompatible divided by all cases. Insufficient-evidence answers and failures are not decisive. Higher coverage alone is not better: unsupported certainty can increase it. Pair this score with accuracy and wrong acceptances."
  ],
  "saved": [
    "Recorded versus fresh studies",
    "Opening a prepared study loads saved evidence and model-call records; it does not rerun inference. Run a fresh investigation to analyze your own question. Prepared source reviews are agent reviews, not independent human validation."
  ],
  "question": [
    "Start an investigation",
    "Describe the methods, task, datasets, and conditions you want to compare. Optional arXiv seeds focus the search; seed-only mode skips discovery. Results depend on available source text. Nemotron proposes question-specific comparison criteria. Review them in Comparisons or revise them in a branch. The traffic-forecasting evaluation does not establish accuracy for every research field."
  ],
  "map": [
    "Question and papers",
    "Explore topic groups and open papers to inspect their evidence. The relevance score is model-estimated fit to your question, not paper quality. Add papers or select a subset for focused comparisons."
  ],
  "papers": [
    "Evidence and source checks",
    "Each number belongs to a method, dataset, protocol, and source location. Text and table checks help locate evidence but do not prove the interpretation is correct. Inspect the quote, table headers, and appendix before verifying a result. Unknown means unresolved in the available evidence, not necessarily absent from the full paper."
  ],
  "compare": [
    "Interpreting comparisons",
    "Comparable means the recorded context passes the implemented compatibility checks. Incompatible means a supported difference was found. Insufficient evidence means a required condition remains unresolved. A numeric advantage is not statistical significance, causal evidence, or proof that one architecture is generally better."
  ],
  "corrections": [
    "Corrections and propagation",
    "Review the proposed value, quote, origin, and source before accepting. Accepted corrections recompute affected comparisons and mark dependent manuscript claims stale. Review or regenerate those claims; a field edit does not itself validate a new scientific conclusion."
  ],
  "write": [
    "Experiment and manuscript",
    "Drafts synthesize reviewed evidence and propose future experiments. They do not report experiments run by Relay. Check citations and stale claims, edit the argument, and complete human review before using the manuscript. PDF compilation requires the supported local compiler setup; export LaTeX when unavailable."
  ],
  "execution": [
    "Executions, checkpoints, and branches",
    "The execution record shows saved steps, status, and model calls. A checkpoint captures a saved research state. Branching creates a separate path from that state without changing the original. Copying inherited history does not rerun or rebill those calls. Imported records may have fewer inspectable checkpoints than their historical run."
  ],
  "calls": [
    "Model usage and timing",
    "Tokens and timings come from recorded provider calls. Summed model time is not end-to-end wall-clock time. Failed calls and retries can add latency and usage. A saved record is evidence of its original run, not a newly completed inference."
  ],
  "provenance": [
    "Who performed the experiment?",
    "own = the source paper’s proposed-method result; reproduced = a baseline rerun by the source paper’s authors; cited = a result copied or cited from another paper; unknown = unresolved. None means Relay independently ran that experiment. Keep unknown until source evidence supports a classification. Original and corrected tables must retain their own locations and metric definitions."
  ],
  "review": [
    "Review versus numeric verification",
    "Including a paper in drafting and verifying a numeric result are separate decisions. The verification checkbox records that you checked the value and experimental context against its source. Agent-reviewed records are not independent human reviews. Add a reason when correcting evidence."
  ],
  "model": [
    "Model and web-search roles",
    "Nebius hosts the selected inference model. Existing investigations retain their chosen model. OpenAlex and arXiv support paper discovery. When configured, Tavily also finds arXiv candidates during initial discovery and searches for unresolved context during investigation; seed-only discovery stays restricted to your papers. It is not a replacement model or a static answer fallback. Web results still require source checks and review."
  ],
  "support": [
    "Evidence support",
    "Quoted, nearby, in-paper, derived, code, and researcher labels describe where support was found. They are not confidence percentages. A default is an assumption, and a rejected value failed a source check. Inspect the underlying quote and location."
  ],
  "context": [
    "Experimental context",
    "Match the dataset and version, split, forecast horizon, aggregation, preprocessing, metric definition, and provenance before comparing numbers. Keep unsupported fields unknown. A paper-wide setting may not apply to every table or corrected result."
  ],
  "projects": [
    "Saved projects",
    "Browser copies help restore projects after server restarts. Export a project backup to move it to another browser or computer. A saved project contains research state, not proof that its results have been independently validated."
  ]
};
export function info(key) {
  if (!topics[key]) return '';
  return `<button type="button" class="info-button" data-help="${key}" aria-label="About ${topics[key][0]}" aria-haspopup="dialog"><span aria-hidden="true">i</span></button>`;
}
const dialog = document.createElement('dialog');
dialog.id = 'help-dialog';
dialog.setAttribute('aria-labelledby', 'help-title');
dialog.setAttribute('aria-describedby', 'help-description');
dialog.innerHTML = '<button type="button" class="help-close" aria-label="Close explanation">×</button><div class="kicker">UNDERSTAND THE EVIDENCE</div><h2 id="help-title"></h2><p id="help-description"></p><button type="button" class="help-done">Got it</button>';
document.body.append(dialog);
dialog.querySelector('.help-close').onclick = dialog.querySelector('.help-done').onclick = () => dialog.close();
document.addEventListener('click', event => {
  const button = event.target.closest('[data-help]');
  if (!button || !topics[button.dataset.help]) return;
  event.preventDefault();
  const [title, description] = topics[button.dataset.help];
  dialog.querySelector('#help-title').textContent = title;
  dialog.querySelector('#help-description').textContent = description;
  if (!dialog.open) dialog.showModal();
});
