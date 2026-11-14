// Tests the live-panel debounce without a test framework: node scripts/check-debounce.mjs (Node 22.6+ runs .ts directly)
import assert from 'node:assert/strict';
import { debounce, latest } from '../src/lib/debounce.ts';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const calls = [];
const d = debounce((v) => calls.push(v), 50);
d(1); d(2); d(3);                       // a burst of typing
await sleep(20); assert.deepEqual(calls, []);       // nothing yet
await sleep(60); assert.deepEqual(calls, [3]);      // one call with the last value
d(4); d.cancel(); await sleep(80);
assert.deepEqual(calls, [3]);                       // cancelled
d(5); await sleep(80); d(6); await sleep(80);
assert.deepEqual(calls, [3, 5, 6]);                 // separate pauses give separate calls
const l = latest(); const a = l.next(); const b = l.next();
assert.equal(l.isCurrent(a), false); assert.equal(l.isCurrent(b), true);  // the older reply is ignored
console.log('debounce: ok');
