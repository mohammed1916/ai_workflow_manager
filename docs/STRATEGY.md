# Product choice and hackathon strategy

Research date: 26 October 2026 (India time).

## Choice: Relay — Best Apps and Agents

The event's public overview describes this track as practical apps, copilots, and workflows powered by Nemotron on Nebius Token Factory. Relay fits a specific audience: small product teams converting fragmented research and meeting notes into useful handoffs. NVIDIA Nemotron is responsible for synthesis and structured action planning; the local executor makes its output operational.

The alternate coding playground has substantial existing runtime/visualization technology. It would fit Coding and Agentic Engineering if developed into a trace-grounded agent debugger. Relay was selected because the user prefers trying Mac workflows and a fresh, coherent product can demonstrate that direction without importing the large existing application. No code from the visualizer was copied or changed.

The differentiator must be the complete handoff: selected browser/page context + local notes → editable plan → explicit human changes → execution → byte-level evidence. A universal computer-control claim would exceed this implementation and weaken the demo.

## Lessons applied from lessons.txt

- Human and agent share one plan. Human edits increment its revision.
- Stale plans cannot silently overwrite newer work: source hashes and revision checks block approval.
- Every action has visible provenance and lifecycle events.
- Rejection feedback is carried into the next planning request.
- Tool failures are actionable and bounded. Invalid model JSON receives one repair attempt.
- Completion has evidence: exclusive file creation and a content hash receipt.
- Validate the agent boundary with adversarial action inputs, stale approvals, provider failures, and end-to-end UI testing.

## What remains before a competitive submission

- Test the optional Chrome extension end-to-end in an installed, paired browser.
- Collect real user feedback and measure time-to-deliverable against a manual baseline. Do not invent a time-saved metric.
- Exercise all three recipes with live Nemotron and document failures as well as successes.
- Record a concise demo with at least a minute of actual app operation; verify current video-length rules before recording the final cut.
- Publish a public licensed repository and provide a reproducible working test build/demo.
- Complete Devpost registration/submission only with the user's authorization and current eligibility/rules review.

The connected Devpost API returned a reauthentication error. No registration or submission was performed. Public overview, rules and resources were retrieved before that error; use the event website to recheck final requirements. No chance of winning is promised.

## Sources

- Event and track: https://nebiusglobalaihackathon.devpost.com/
- Rules and deliverables: https://nebiusglobalaihackathon.devpost.com/rules
- Organizer resources: https://nebiusglobalaihackathon.devpost.com/resources
- Nebius API: https://docs.tokenfactory.nebius.com/api-reference/introduction
- NVIDIA Nemotron on Nebius: https://nebius.com/services/token-factory/nemotron
- Signed-in catalog inspected through Chrome: https://tokenfactory.nebius.com/models/catalog

## Checking the Gemini explanation

Official OpenAI documentation confirms the desktop Work/Codex setup, Chrome extension controls, app mentions, and macOS Screen Recording/Accessibility permissions. It does not establish that AppleScript is the implementation underlying ChatGPT's computer-use integration. A custom app can use Apple's supported automation interfaces, but that is a separate architectural choice.

Relay does not depend on ChatGPT, its extension, or this assistant's computer-use tools at runtime. Its own extension captures source text, Python calls Nebius, and a deterministic local executor handles approved outputs.

References:
- https://learn.chatgpt.com/docs/computer-use
- https://developer.chrome.com/docs/extensions/develop/concepts/activeTab
- https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/index.html
