// Parity check: every t('...') / tn(n, '..', '..') text used in src has a translation in each dictionary, with the same {placeholders}.
// Run: docker compose exec frontend node scripts/check-i18n.mjs
import fs from 'fs';
import path from 'path';

const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk('src').filter((f) => /\.(tsx?|ts)$/.test(f) && !f.includes('/i18n/'));
const str = "'((?:[^'\\\\]|\\\\.)*)'";
const keys = new Set();
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  for (const m of src.matchAll(new RegExp(`(?<![\\w.])(?:t|tt)\\(\\s*${str}`, 'g'))) keys.add(m[1].replace(/\\'/g, "'").replace(/\\n/g, '\n'));
  for (const m of src.matchAll(new RegExp(`(?<![\\w.])tn\\([^,]+,\\s*${str}\\s*,\\s*${str}`, 'g'))) { keys.add(m[1].replace(/\\'/g, "'")); keys.add(m[2].replace(/\\'/g, "'")); }
}
const load = (name) => {
  const t = fs.readFileSync(`src/i18n/${name}.ts`, 'utf8');
  const start = t.indexOf('{', t.indexOf('Record<string, string>'));
  const end = t.lastIndexOf('}');
  return start > 0 ? JSON.parse(t.slice(start, end + 1)) : {};
};
const ph = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',');
const SKIP = new Set(['Shift', 'RoleShift', 'DELETE', 'low', 'medium', 'high']);
let bad = 0;
for (const lang of ['ru', 'kk']) {
  if (!fs.existsSync(`src/i18n/${lang}.ts`)) continue;
  const d = load(lang);
  if (!Object.keys(d).length) { console.log(`${lang}: empty dictionary, skipped`); continue; }
  for (const k of keys) {
    if (SKIP.has(k)) continue;
    const v = d[k];
    if (v === undefined) { console.log(`${lang}: missing "${k.slice(0, 80)}"`); bad++; continue; }
    const forms = v.split(' | ');
    if (forms.some((f) => ph(f) !== ph(forms[0]))) { console.log(`${lang}: placeholders differ between plural forms "${k.slice(0, 60)}"`); bad++; }
    if (!k.includes(' | ') && forms.length === 1 && ph(v) !== ph(k)) { console.log(`${lang}: placeholders differ "${k.slice(0, 60)}"`); bad++; }
  }
  console.log(`${lang}: ${Object.keys(d).length} texts`);
}
console.log(`${keys.size} keys in code, ${bad} problems`);
process.exit(bad ? 1 : 0);
