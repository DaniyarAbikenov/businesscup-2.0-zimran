// Tests the what-if helpers (paths into the inputs, slider ranges): node scripts/check-whatif.mjs
import assert from 'node:assert/strict';
import { get, put, questionOf, rangeFor } from '../src/lib/whatif.ts';

const inputs = { bufferDays: 2, criteria: [{ name: 'Cost', weight: 3 }, { name: 'Fit', weight: 5 }] };
assert.equal(get(inputs, 'bufferDays'), 2);
assert.equal(get(inputs, 'criteria.1.weight'), 5);
assert.deepEqual(put(inputs, 'bufferDays', 4).bufferDays, 4);
const moved = put(inputs, 'criteria.0.weight', 1);
assert.equal(moved.criteria[0].weight, 1); assert.equal(moved.criteria[1].weight, 5);   // only the chosen row changes
assert.equal(inputs.criteria[0].weight, 3);                                              // the original is untouched
const sit = { questions: [{ id: 'bufferDays', min: 0, max: 365, step: 1 }, { id: 'criteria', type: 'list', fields: [{ id: 'weight', min: 1, max: 5, step: 1 }] }] };
assert.equal(questionOf(sit, 'criteria.0.weight').max, 5);
assert.deepEqual(rangeFor({ min: 1, max: 5, step: 1 }, 3), { min: 1, max: 5, step: 1 });          // small range: the question's own
assert.deepEqual(rangeFor({ min: 0, max: 365, step: 1 }, 10), { min: 5, max: 365 > 20 ? 20 : 20, step: 1 }); // wide range: half to twice the value
const r = rangeFor({ min: 0.5, max: 5000, step: 0.5 }, 8); assert.ok(r.min <= 8 && r.max >= 16 && r.step === 0.5);
const t = rangeFor({ min: 1, max: 20000 }, 600); assert.ok(t.min <= 600 && t.max >= 1200);
console.log('what-if helpers: ok');
