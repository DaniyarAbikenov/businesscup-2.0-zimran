import type { Question } from '../api';

/** A path is a top-level question id ("bufferDays") or "list.index.field" ("criteria.0.weight"). */
export const get = (inputs: any, path: string) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), inputs);
export const put = (inputs: any, path: string, v: number) => {
  const [a, b, c] = path.split('.');
  if (!b) return { ...inputs, [a]: v };
  return { ...inputs, [a]: inputs[a].map((row: any, i: number) => (i === Number(b) ? { ...row, [c]: v } : row)) };
};
export const questionOf = (sit: { questions: Question[] }, path: string): Question | undefined => {
  const [a, , c] = path.split('.');
  const top = sit.questions.find((x) => x.id === a);
  return c ? top?.fields?.find((f) => f.id === c) : top;
};

/** The slider's own range: the question's range when it is small, otherwise from half to twice the current value. */
export function rangeFor(q: Question, cur: number): { min: number; max: number; step: number } {
  const step = q.step ?? (Math.abs(cur) >= 100 ? 10 : 1);
  const lo = q.min ?? 0, hi = q.max ?? cur * 2;
  if (hi - lo <= 100) return { min: lo, max: hi, step };
  const min = Math.max(lo, Math.floor((cur * 0.5) / step) * step);
  const max = Math.min(hi, Math.max(Math.ceil((cur * 2) / step) * step, cur + step * 4));
  return { min, max, step };
}

