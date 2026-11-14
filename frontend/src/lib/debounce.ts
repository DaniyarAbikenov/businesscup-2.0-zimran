/** Calls fn once, `ms` after the last call. cancel() drops a pending call. Used by the live panel so typing does not hit the server on every key. */
export function debounce<A extends unknown[]>(fn: (...a: A) => void, ms: number) {
  let t: ReturnType<typeof setTimeout> | undefined;
  const d = (...a: A) => { if (t !== undefined) clearTimeout(t); t = setTimeout(() => { t = undefined; fn(...a); }, ms); };
  d.cancel = () => { if (t !== undefined) clearTimeout(t); t = undefined; };
  return d;
}

/** Keeps only the answer to the latest request: a slow reply for an older one is ignored. */
export function latest() {
  let n = 0;
  return { next: () => ++n, isCurrent: (id: number) => id === n };
}
