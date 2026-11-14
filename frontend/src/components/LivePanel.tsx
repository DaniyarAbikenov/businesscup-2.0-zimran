import { useEffect, useRef, useState } from 'react';
import { t, tn } from '../i18n';
import { api, fmtDate, usd } from '../api';
import { debounce, latest } from '../lib/debounce';

interface Preview { ready: boolean; needed?: string[]; more?: number; engine?: string; facts?: { key: string; value: number; unit: string }[]; result?: any; hasGuess?: boolean }
interface Sit { id: string; engine: string; options: Record<string, { label: string }> }

const FACT: Record<string, string> = {
  totalHours: 'Total work', freeHoursPerDay: 'Free time per day', meanHours: 'Expected work', hoursPerDay: 'Real hours per working day',
  criteria: 'Criteria', options: 'Options', workdaysToRelease: 'Working days to release', totalChangeDays: 'The change with overhead',
};
const factLabel = (k: string) => ({ totalHours: t('Total work'), freeHoursPerDay: t('Free time per day'), meanHours: t('Expected work'), hoursPerDay: t('Real hours per working day'), criteria: t('Criteria'), options: t('Options'), workdaysToRelease: t('Working days to release'), totalChangeDays: t('The change with overhead') } as Record<string, string>)[k] ?? FACT[k] ?? k;

/** The bottom line so far, from the real calculation. Only shown when it does not give away the answer to the guess question. */
function liveLine(sit: Sit, r: any): string {
  const o = r.options.find((x: any) => x.key === r.lowestRiskKey);
  const label = sit.options[o.key]?.label ?? o.key;
  const risk = t('{level} risk', { level: t(o.riskLevel) });
  if (sit.engine === 'decision') return t('Highest score so far: {top}.', { top: r.winner });
  if (sit.engine === 'estimate') return t('"{label}": {date}, about {p}% chance to make it ({risk}).', { label, date: fmtDate(o.date), p: o.probability, risk });
  if (sit.engine === 'priorities') return o.lateCount ? t('"{label}" still leaves {n} late ({risk}).', { label, n: tn(o.lateCount, '{n} task', '{n} tasks'), risk }) : t('"{label}" leaves nothing late ({risk}).', { label, risk });
  return t('"{label}" has the lowest risk ({risk}). Release {date}, extra cost {cost}.', { label, risk, date: fmtDate(o.newReleaseDate), cost: usd(o.extraCost) });
}

/** A side panel that updates while the form is filled in. It saves nothing and never calls an AI: it asks the same calculation the result page uses. */
export function LivePanel({ sit, answers }: { sit: Sit; answers: Record<string, any> }) {
  const [p, setP] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [showLive, setShowLive] = useState(false);
  const guard = useRef(latest());
  const run = useRef(debounce((id: string, inputs: Record<string, any>) => {
    const my = guard.current.next();
    setBusy(true);
    api('POST', '/cases/preview', { situationId: id, inputs })
      .then((r) => { if (guard.current.isCurrent(my)) setP(r); })
      .catch(() => { if (guard.current.isCurrent(my)) setP(null); })
      .finally(() => { if (guard.current.isCurrent(my)) setBusy(false); });
  }, 500));
  useEffect(() => { run.current(sit.id, answers); }, [answers, sit.id]);
  useEffect(() => () => run.current.cancel(), []);

  const spoils = !!p?.ready && !!p.hasGuess && !showLive;
  return (
    <aside className="livepanel" aria-live="polite" aria-label={t('Where this stands')} data-tour="form-live">
      <h2>{t('Where this stands')}{busy && <span className="live-dot" aria-hidden="true" />}</h2>
      {!p && <p className="muted small">{t('Start typing and the numbers that follow will appear here.')}</p>}
      {p && !p.ready && (
        <>
          <p className="small">{t('Still needed to calculate:')}</p>
          <ul className="plain small">{(p.needed ?? []).map((n) => <li key={n}>{n}</li>)}</ul>
          {!!p.more && <p className="muted small">{t('and {n} more', { n: p.more })}</p>}
        </>
      )}
      {p?.ready && (
        <>
          <dl className="live-facts">{(p.facts ?? []).map((f) => <div key={f.key}><dt>{factLabel(f.key)}</dt><dd>{f.value}{f.unit ? ' ' + f.unit : ''}</dd></div>)}</dl>
          {spoils ? (
            <>
              <p className="small">{t('Your guess comes first, so the answer stays hidden until you compare.')}</p>
              <button type="button" className="linkbtn" style={{ paddingLeft: 0 }} onClick={() => setShowLive(true)}>{t('Show the live result instead')}</button>
            </>
          ) : (
            <p className="live-line">{liveLine(sit, p.result)}</p>
          )}
          <p className="muted small">{t('Not saved. This is the same calculation as the result page, on the numbers typed so far.')}</p>
        </>
      )}
    </aside>
  );
}
