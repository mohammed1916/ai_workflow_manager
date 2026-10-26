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
