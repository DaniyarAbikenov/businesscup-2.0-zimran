import { useEffect, useMemo, useRef, useState } from 'react';
import { t } from '../i18n';
import { Case, Question, Situation, api, fmtDate, usd } from '../api';
import { debounce, latest } from '../lib/debounce';
import { get, put, questionOf, rangeFor } from '../lib/whatif';
import { notify } from './Toaster';
import { Button } from './ui';

type Ctl = { path: string; label: string; q: Question; min: number; max: number; step: number };

function numbers(sit: Situation, r: any): { label: string; value: string }[] {
  const best = r.options.find((o: any) => o.key === r.lowestRiskKey);
  const label = sit.options[best.key]?.label ?? best.key;
  const base = [{ label: t('Best choice'), value: sit.engine === 'decision' ? best.pick : label }, { label: t('Risk'), value: t(best.riskLevel) }];
  if (sit.engine === 'change_request') {
    const a = r.options.find((o: any) => o.key === 'accept');
    return [...base, { label: t('If accepted: release slips'), value: a.slipWorkdays ? t('{n} working days', { n: a.slipWorkdays }) : t('not at all') }, { label: t('If accepted: extra cost'), value: usd(a.extraCost) }];
  }
  if (sit.engine === 'priorities') return [...base, { label: t('Late tasks'), value: String(best.lateCount) }, { label: t('Late days in total'), value: String(best.totalLateDays) }];
  if (sit.engine === 'estimate') { const s = r.options.find((o: any) => o.key === 'safe'); return [...base, { label: t('Safe date'), value: fmtDate(s.date) }, { label: t('Chance to make the best choice'), value: `${best.probability}%` }]; }
  return [...base, { label: t('Highest score'), value: r.winner }];
}

/** Drag two or three of the numbers that move the outcome most and see the answer change. Nothing is saved until Save is pressed. */
export function WhatIf({ c, sit, onSaved }: { c: Case; sit: Situation; onSaved: (c: Case) => void }) {
  const paths: string[] = (sit as any).whatIf ?? [];
  const [vals, setVals] = useState<any>(c.inputs);
  const [alt, setAlt] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const guard = useRef(latest());
  const run = useRef(debounce((inputs: any) => {
    const my = guard.current.next();
    api('POST', '/cases/preview', { situationId: sit.id, inputs })
      .then((r) => { if (guard.current.isCurrent(my)) setAlt(r.ready ? r.result : null); })
      .catch(() => { if (guard.current.isCurrent(my)) setAlt(null); });
  }, 400));
  useEffect(() => () => run.current.cancel(), []);
  const ctls: Ctl[] = useMemo(() => paths.flatMap((p) => {
    const q = questionOf(sit, p); const cur = Number(get(c.inputs, p));
    if (!q || Number.isNaN(cur)) return [];
    const name = p.includes('.') ? (c.inputs[p.split('.')[0]][Number(p.split('.')[1])]?.name ?? '') : '';
    return [{ path: p, label: name ? t('How much does "{name}" matter?', { name }) : q.label, q, ...rangeFor(q, cur) }];
  }), [c.id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (ctls.length === 0 || c.status !== 'draft') return null;
  const changed = ctls.some((x) => Number(get(vals, x.path)) !== Number(get(c.inputs, x.path)));
  const set = (path: string, v: number) => { const next = put(vals, path, v); setVals(next); run.current(next); };
  const reset = () => { run.current.cancel(); guard.current.next(); setVals(c.inputs); setAlt(null); };
  const save = async () => {
    setBusy(true);
    try { const r = await api('PUT', `/cases/${c.id}/inputs`, { inputs: vals }); onSaved(r.case); notify(t('Saved. The comparison above now uses these numbers.')); setAlt(null); }
    catch (x: any) { notify(x.message, 'bad'); } finally { setBusy(false); }
  };
  const saved = numbers(sit, c.result);
  const what = alt ? numbers(sit, alt) : null;
  return (
    <div className="whatif" data-tour="res-whatif">
      <h3 style={{ fontSize: 16, margin: '16px 0 4px' }}>{t('What if?')}</h3>
      <p className="small muted" style={{ margin: '0 0 8px' }}>{t('Move a number and watch the answer change. Your saved case stays as it is until you press Save.')}</p>
      <div className="whatif-ctls">
        {ctls.map((x) => {
          const v = Number(get(vals, x.path));
          const word = x.q.words?.[Math.round((v - x.min) / x.step)];
          return (
            <label key={x.path} className="whatif-ctl">
              <span>{x.label}</span>
              <span className="whatif-row">
                <input type="range" min={x.min} max={x.max} step={x.step} value={Math.min(x.max, Math.max(x.min, v))} aria-valuetext={word ? `${v} ${word}` : `${v}${x.q.unit ? ' ' + x.q.unit : ''}`} onChange={(e) => set(x.path, Number(e.target.value))} />
                <b className="whatif-val">{v}{x.q.unit ? (x.q.unit === '%' ? '' : ' ') + x.q.unit : ''}</b>
              </span>
              {word && <span className="slider-word">{word}</span>}
            </label>
          );
        })}
      </div>
      {changed && (
        <table className="ledger whatif-table" aria-live="polite">
          <thead><tr><th scope="col" /><th scope="col">{t('Saved')}</th><th scope="col">{t('What if')}</th></tr></thead>
          <tbody>{saved.map((s, i) => <tr key={s.label}><th scope="row">{s.label}</th><td>{s.value}</td><td className={what && what[i].value !== s.value ? 'whatif-diff' : ''}>{what ? what[i].value : '…'}</td></tr>)}</tbody>
        </table>
      )}
      <div className="row" style={{ marginTop: 8 }}>
        <Button type="button" variant="secondary" disabled={!changed} onClick={reset}>{t('Reset')}</Button>
        <Button type="button" disabled={!changed || !alt} busy={busy} onClick={save}>{t('Save these numbers')}</Button>
      </div>
    </div>
  );
}
