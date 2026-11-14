/** Tiny i18n. The English text is the key: t('Save') returns the Russian or Kazakh text if there is one,
 *  and the English text otherwise. {name} placeholders are filled from vars. */
import kk from './kk';
import ru from './ru';

export type Lang = 'en' | 'ru' | 'kk';
export const LANGS: { code: Lang; short: string; name: string }[] = [{ code: 'en', short: 'EN', name: 'English' }, { code: 'ru', short: 'RU', name: 'Русский' }, { code: 'kk', short: 'KZ', name: 'Қазақша' }];
const KEY = 'roleshift.lang';
const dicts: Record<Lang, Record<string, string>> = { en: {}, ru, kk };

function detect(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'en' || saved === 'ru' || saved === 'kk') return saved;
  } catch { /* storage blocked */ }
  const nav = (typeof navigator !== 'undefined' ? navigator.language : 'en').slice(0, 2).toLowerCase();
  return nav === 'ru' ? 'ru' : nav === 'kk' ? 'kk' : 'en';
}

let current: Lang = detect();
const warned = new Set<string>();

export const getLang = (): Lang => current;
export const locale = () => ({ en: 'en-US', ru: 'ru-RU', kk: 'kk-KZ' }[current]);
export function setLang(l: Lang) {
  current = l;
  try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
}
/** The server's saved choice wins once signed in. */
export function adopt(l: string | null | undefined) {
  if (l === 'en' || l === 'ru' || l === 'kk') { current = l; try { localStorage.setItem(KEY, l); } catch { /* ignore */ } }
}

export function t(s: string, vars?: Record<string, string | number | null | undefined>): string {
  let out = dicts[current][s];
  if (out === undefined) {
    out = s;
    if (current !== 'en' && import.meta.env?.DEV && !warned.has(s)) { warned.add(s); console.warn(`[i18n] missing ${current}: ${s}`); }
  }
  return vars ? out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k] ?? '') : m)) : out;
}

/** Plural: tn(n, 'one {n} day', 'many {n} days') for en; ru/kk dictionaries use 'one|few|many' joined by ' | '. */
export function tn(n: number, one: string, many: string): string {
  const raw = dicts[current][one] ?? (current === 'en' ? undefined : undefined);
  if (current === 'en' || !raw) return t(n === 1 ? one : many, { n });
  const forms = raw.split(' | ');
  const m10 = n % 10, m100 = n % 100;
  const i = current === 'ru' ? (m10 === 1 && m100 !== 11 ? 0 : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? 1 : 2) : n === 1 ? 0 : 1;
  return (forms[Math.min(i, forms.length - 1)] ?? forms[0]).replace('{n}', String(n));
}
