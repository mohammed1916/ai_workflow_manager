// Rules for investigations kept in this browser: samples, user copies, removals, and file checks.
// Pure functions only, so they can be tested without the page.

// Bundled starter investigations. The server installs them from data/research/.
export const SAMPLE_KEYS = ['nebius-benchmark-audit-v1', 'nebius-discovery-v1'];
export const REMOVED_KEY = 'relay-removed-copies';

export const idOK = (id) => /^[a-f0-9]{16}$/.test(String(id || ''));

// A sample is a starter example. A branch made from a sample has a parent, so it is the user's own project.
export const isSample = (p) => !!p && SAMPLE_KEYS.includes(p.studyKey) && !p.parentProject;

// Removals are stored in this browser, so they survive reloads.
export function readRemoved(storage) {
  try {
    const value = JSON.parse(storage.getItem(REMOVED_KEY) || '[]');
    return new Set(Array.isArray(value) ? value.filter(idOK) : []);
  } catch { return new Set(); }
}
export function writeRemoved(storage, set) { storage.setItem(REMOVED_KEY, JSON.stringify([...set])); }
export function markRemoved(storage, id) { const s = readRemoved(storage); s.add(id); writeRemoved(storage, s); return s; }
export function unmarkRemoved(storage, id) { const s = readRemoved(storage); s.delete(id); writeRemoved(storage, s); return s; }

// A browser copy is kept only for a user's own investigation that was not removed.
export function mayKeepCopy(p, removed) { return !!p && !isSample(p) && !removed.has(p.id); }

export function exportName(p) {
  const slug = String(p.hypothesis || 'investigation').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 50).replace(/^-|-$/g, '') || 'investigation';
  return `${slug}-${p.id.slice(0, 8)}.relay-research.json`;
}

// Validates an imported file and returns the parsed document, or throws a message the person can act on.
export function checkFile(text, size) {
  if (size > 8000000) throw Error('This file is larger than 8 MB, so it cannot be a Relay Research project.');
  let doc;
  try { doc = JSON.parse(text); } catch { throw Error('This file is not valid JSON. Export the project again from Relay, or check that the file was not edited.'); }
  if (!doc || typeof doc !== 'object' || !doc.project || typeof doc.project !== 'object') throw Error('This file does not contain a Relay Research project.');
  if (doc.format !== 'relay-research/1') throw Error(`This file uses format "${doc.format || 'unknown'}". Relay can import "relay-research/1" files.`);
  const p = doc.project;
  if (!idOK(p.id)) throw Error('The project id in this file is not valid.');
  if (typeof p.hypothesis !== 'string' || p.hypothesis.length < 10 || p.hypothesis.length > 2000) throw Error('The question in this file must be 10 to 2,000 characters.');
  if (!Array.isArray(p.papers) || p.papers.length > 20) throw Error('The paper list in this file is missing or has more than 20 papers.');
  return doc;
}

// The request that starts a user's own copy of a sample: a branch from its last saved step.
export function copyFromSampleBody(sample) {
  const step = (sample.execution || []).at(-1);
  if (!step) throw Error('This sample has no saved step to copy from.');
  return { id: sample.id, node: step.id, next: 'snapshot', name: 'My copy of ' + String(sample.branchName || sample.hypothesis).slice(0, 80) };
}
