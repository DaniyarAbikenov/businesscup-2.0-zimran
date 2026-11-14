// Tests the draft helpers: node scripts/check-draft.mjs
import assert from 'node:assert/strict';

const store = new Map();
globalThis.sessionStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
const { loadDraft, saveDraft, clearDraft } = await import('../src/lib/draft.ts');

assert.equal(loadDraft('a'), null);                                                        // nothing yet
saveDraft('a', { answers: { title: 'x', tasks: [{ name: 'T' }] }, conf: '4', step: 1, storyId: 's1' });
assert.deepEqual(loadDraft('a'), { answers: { title: 'x', tasks: [{ name: 'T' }] }, conf: '4', step: 1, storyId: 's1' });   // restored as saved
assert.equal(loadDraft('b'), null);                                                        // another scenario is separate
store.set('roleshift.draft.c', '{not json'); assert.equal(loadDraft('c'), null);          // a damaged value is ignored
store.set('roleshift.draft.d', '"a string"'); assert.equal(loadDraft('d'), null);
clearDraft('a'); assert.equal(loadDraft('a'), null);                                       // cleared after Calculate or Discard
globalThis.sessionStorage = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
assert.equal(loadDraft('a'), null); saveDraft('a', { answers: {}, conf: '3', step: 0, storyId: null }); clearDraft('a');   // blocked storage: no error
console.log('draft: ok');
