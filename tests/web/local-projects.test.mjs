import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as L from '../../web/local-projects.js';

const memory = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) }; };
const ID = 'a1b2c3d4e5f60718';
const user = { id: ID, hypothesis: 'Do graph networks beat transformers on METR-LA at 60 minutes?', papers: [] };
const sample = { id: '0123456789abcdef', hypothesis: 'Sample question here', studyKey: 'nebius-benchmark-audit-v1', execution: [{ id: 'n1' }, { id: 'n2' }], papers: [] };

test('a starter investigation is a sample, but a copy made from it is the user’s own', () => {
  assert.equal(L.isSample(sample), true);
  assert.equal(L.isSample({ ...sample, parentProject: 'x' }), false);
  assert.equal(L.isSample(user), false);
});

test('removal persists across a reload, and a removed investigation is never saved again', () => {
  const storage = memory();
  L.markRemoved(storage, ID);
  const afterReload = L.readRemoved(storage);          // a new page load reads the same storage
  assert.equal(afterReload.has(ID), true);
  assert.equal(L.mayKeepCopy(user, afterReload), false);
  assert.equal(L.mayKeepCopy(user, new Set()), true);
});

test('samples are never kept as the user’s copies', () => {
  assert.equal(L.mayKeepCopy(sample, new Set()), false);
});

test('a re-imported investigation clears its removal', () => {
  const storage = memory();
  L.markRemoved(storage, ID);
  assert.equal(L.unmarkRemoved(storage, ID).has(ID), false);
});

test('corrupt removal data is ignored rather than breaking the page', () => {
  const storage = memory(); storage.setItem(L.REMOVED_KEY, '{not json');
  assert.equal(L.readRemoved(storage).size, 0);
});

test('a copy is started from a sample’s last saved step', () => {
  const body = L.copyFromSampleBody(sample);
  assert.deepEqual(body, { id: sample.id, node: 'n2', next: 'snapshot', name: 'My copy of Sample question here' });
  assert.throws(() => L.copyFromSampleBody({ ...sample, execution: [] }), /no saved step/);
});

test('exported file names are readable and carry the project id', () => {
  const name = L.exportName(user);
  assert.match(name, /^[a-z0-9-]+-a1b2c3d4\.relay-research\.json$/);
  assert.ok(name.split('-a1b2c3d4')[0].length <= 50);
});

test('import checks give a clear reason for each kind of bad file', () => {
  const good = JSON.stringify({ format: 'relay-research/1', project: user });
  assert.equal(L.checkFile(good, good.length).project.id, ID);
  assert.throws(() => L.checkFile('{oops', 5), /not valid JSON/);
  assert.throws(() => L.checkFile(JSON.stringify({ format: 'other/1', project: user }), 10), /uses format "other\/1"/);
  assert.throws(() => L.checkFile(JSON.stringify({ format: 'relay-research/1', project: { ...user, id: '../../x' } }), 10), /id in this file is not valid/);
  assert.throws(() => L.checkFile(JSON.stringify({ format: 'relay-research/1', project: { ...user, hypothesis: 'short' } }), 10), /10 to 2,000 characters/);
  assert.throws(() => L.checkFile(JSON.stringify({ format: 'relay-research/1', project: { ...user, papers: new Array(21).fill({}) } }), 10), /more than 20 papers/);
  assert.throws(() => L.checkFile(good, 9000000), /larger than 8 MB/);
});
