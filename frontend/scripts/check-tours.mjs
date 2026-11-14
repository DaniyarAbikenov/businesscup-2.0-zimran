// Every tour step points at a data-tour="..." anchor that exists in the source, and every tour has a screen that registers it.
// Run: docker compose exec frontend node scripts/check-tours.mjs
import fs from 'fs';
import path from 'path';

const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk('src').filter((f) => /\.tsx?$/.test(f));
const steps = fs.readFileSync('src/tour/steps.ts', 'utf8');
const used = [...steps.matchAll(/d\('([\w-]+)'\)/g)].map((m) => m[1]);
const anchors = new Set();
const screens = new Set();
for (const f of files) {
  const s = fs.readFileSync(f, 'utf8');
  for (const m of s.matchAll(/data-tour="([\w-]+)"/g)) anchors.add(m[1]);
  for (const m of s.matchAll(/data-tour=\{([^}]*)\}/g)) for (const q of m[1].matchAll(/'([\w-]+)'/g)) anchors.add(q[1]);
  for (const m of s.matchAll(/<TourScreen name="(\w+)"/g)) screens.add(m[1]);
}
const keys = [...steps.matchAll(/^\s{2}(\w+): \[/gm)].map((m) => m[1]);
let bad = 0;
for (const k of used) if (!anchors.has(k)) { console.log(`no element has data-tour="${k}"`); bad++; }
for (const k of keys) if (!screens.has(k)) { console.log(`no screen registers the "${k}" tour`); bad++; }
console.log(`${used.length} step targets, ${keys.length} tours, ${bad} problems`);
process.exit(bad ? 1 : 0);
