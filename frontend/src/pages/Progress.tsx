import { t, tn } from '../i18n';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../App';
import { Progress, api, fmtDate } from '../api';
import { notify } from '../components/Toaster';
import { TourScreen } from '../tour/TourHost';
import { PageHeader, Panel } from '../components/ui';

/** Opt-in email reminders: off by default. Used here and on the Account page. */
export function ReminderToggle({ onChange }: { onChange?: () => void }) {
  const { me, refresh } = useSession();
  const [on, setOn] = useState(!!me.profile?.emailReminders);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState('');
  const set = async (v: boolean) => {
    setBusy(true);
    try { await api('POST', '/progress/reminders', { enabled: v }); setOn(v); await refresh(); onChange?.(); notify(v ? t('Email reminders are on.') : t('Email reminders are off.')); }
    catch (x: any) { notify(x.message, 'bad'); } finally { setBusy(false); }
  };
  const sendNow = async () => {
    try { const r = await api<{ sent: number; logMailer: boolean }>('POST', '/progress/send-reminders-now', {}); setInfo(r.sent ? (r.logMailer ? tn(r.sent, '{n} reminder written to the server log.', '{n} reminders written to the server log.') : tn(r.sent, '{n} reminder sent.', '{n} reminders sent.')) : t('Nothing is due right now.')); }
    catch (x: any) { setInfo(x.message); }
  };
  return (
    <>
      <label className="check"><input type="checkbox" checked={on} disabled={busy} onChange={(e) => set(e.target.checked)} /> {t('Email me when a follow-up is due, and once after a week if I have not started a second scenario. Every email has a link to turn this off.')}</label>
      <p className="small muted">{t('We only use your sign-in email. Emails contain the title of your case, never your numbers.')}</p>
      {on && me.isDemo === false && <p className="small"><button type="button" className="btn btn-quiet" onClick={sendNow}>{t('Send my due reminders now (testing)')}</button> {info}</p>}
    </>
  );
}

function ConfidenceChart({ items }: { items: Progress['confidence'] }) {
  const W = 320, H = 140, pad = 24;
  const x = (i: number) => (items.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (items.length - 1));
  const y = (v: number) => H - pad - ((v - 1) * (H - 2 * pad)) / 4;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" style={{ width: '100%', maxWidth: 520, height: 'auto' }}
      aria-label={t('Confidence before and after:') + ' ' + items.map((c) => `${c.title} ${c.before} → ${c.after ?? t('not rated yet')}`).join('; ')}>
      {[1, 2, 3, 4, 5].map((v) => <g key={v}><line x1={pad} x2={W - 8} y1={y(v)} y2={y(v)} stroke="currentColor" opacity=".12" /><text x={6} y={y(v) + 4} fontSize="10" fill="currentColor" opacity=".6">{v}</text></g>)}
      {items.map((c, i) => c.after !== null && <line key={'l' + i} x1={x(i)} x2={x(i)} y1={y(c.before)} y2={y(c.after)} stroke="var(--accent-700)" strokeWidth="2" />)}
      {items.map((c, i) => <circle key={'b' + i} cx={x(i)} cy={y(c.before)} r="5" fill="none" stroke="currentColor" strokeWidth="2"><title>{t('{title}: before {n}', { title: c.title, n: c.before })}</title></circle>)}
      {items.map((c, i) => c.after !== null && <circle key={'a' + i} cx={x(i)} cy={y(c.after)} r="5" fill="var(--accent-700)"><title>{t('{title}: after {n}', { title: c.title, n: c.after })}</title></circle>)}
    </svg>
  );
}

export default function ProgressPage() {
  const { pack, me } = useSession();
  const [p, setP] = useState<Progress | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => { api<Progress>('GET', '/progress').then(setP).catch((e) => setError(e.message)); }, []);
  useEffect(load, [load]);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!p) return <p className="muted">{t('Loading')}</p>;
  const stat = (n: string | number, l: string) => <div className="stat"><b>{n}</b><span>{l}</span></div>;
  const pct = Math.min(100, Math.round((p.day / p.windowDays) * 100));
  const mile = [[t('First situation'), p.firsts.situation], [t('First decision'), p.firsts.decision], [t('First debrief'), p.firsts.debrief]] as const;
  const title = (id: string) => pack.situations.find((s) => s.id === id)?.title ?? id;

  return (
    <>
      <TourScreen name="progress" />
      <PageHeader eyebrow={t('Progress')} title={t('Your first 90 days')} lead={t('Everything here comes from what you entered and reported. RoleShift cannot see your workplace.')} />
      <Panel>
        <p style={{ margin: 0 }}><b>{t('Day {day}', { day: p.day })}</b> {p.inWindow ? t('of {total}', { total: p.windowDays }) : t('(past the first {total})', { total: p.windowDays })} · {t('started {date}', { date: fmtDate(p.startedAt) })}</p>
        <div data-tour="pr-bar"><div className="daybar" role="img" aria-label={t('Day {day} of {windowDays}', { day: p.day, windowDays: p.windowDays })}>
          <span style={{ width: `${pct}%` }} />
          {p.milestones.map((m) => <i key={m} style={{ left: `${(m / p.windowDays) * 100}%` }}><em>{m}</em></i>)}
        </div></div>
        <div className="stats" style={{ marginTop: 28 }}>
          {stat(p.counts.situations, t('scenarios tried'))}{stat(p.counts.decisions, t('decisions made'))}{stat(p.counts.followups, t('follow-ups done'))}{stat(`${p.counts.documents} / ${p.counts.exported}`, t('documents saved / exported'))}
        </div>
        {p.inactiveHint && <div className="banner" role="note" style={{ marginTop: 16 }}>{t('It has been {n} days since your last scenario. Is something coming up at work?', { n: p.inactiveDays })}</div>}
      </Panel>

      {p.counts.situations === 0 ? (
        <Panel title={t('Nothing here yet')} lead={t('Your progress appears as you work through scenarios. Start with one you expect this week.')}>
          <div className="row"><Link className="btn btn-primary" to="/">{t('Choose a scenario')}</Link><Link className="btn btn-secondary" to="/">{t('Describe your scenario')}</Link></div>
        </Panel>
      ) : (
        <>
          <Panel title={t('Milestones')}>
            <ul className="plain">{mile.map(([l, d]) => <li key={l}>{d ? <>✓ {l} <span className="muted">{fmtDate(d)}</span></> : <span className="muted">○ {l}</span>}</li>)}</ul>
          </Panel>
          <Panel title={t('Confidence')} lead={p.averageChange === null ? t('Rate your confidence after a decision (the reflection step) to see how it changes.') : t('Average change: {v0}{averageChange}. Open circle: before, filled: after.', { v0: p.averageChange > 0 ? '+' : '', averageChange: p.averageChange })}>
            {p.confidence.length > 0 ? <ConfidenceChart items={p.confidence} /> : <p className="muted">{t('No decisions yet.')}</p>}
          </Panel>
          <div data-tour="pr-skills"><Panel title={t('Your intuition vs the numbers')} lead={t('Before the numbers appear you can guess. This shows how often your guess agreed with the calculator on your own numbers. It does not measure how good your decisions are in the real world.')}>
            {p.skills.filter((s) => s.cases > 0 || s.guesses > 0).length === 0 && <p className="muted">{t('Make a guess before the numbers in any scenario to see your practice here.')}</p>}
            {p.skills.filter((s) => s.cases > 0 || s.guesses > 0).map((s) => (
              <div key={s.key} className="skillrow">
                <div><b>{s.label}</b><div className="small muted">{tn(s.cases, '{n} case practised', '{n} cases practised')} · {tn(s.guesses, '{n} guess', '{n} guesses')}</div></div>
                {s.enough
                  ? <div><span className="ticks" role="img" aria-label={s.ticks.map((x) => Math.round(x * 100) + '%').join(', ')}>{s.ticks.map((x, i) => <i key={i} style={{ height: 6 + Math.round(x * 18) + 'px', opacity: 0.35 + 0.65 * x }} />)}</span> <b>{s.hitRate}%</b> <span className="small muted">{t('agreement with the numbers')}</span></div>
                  : <div className="small muted">{t('Not enough guesses yet. Make {n} to see a trend.', { n: p.minForTrend })}</div>}
              </div>
            ))}
          </Panel></div>
          <div data-tour="pr-timeline"><Panel title={t('Decisions')}>
            <ul className="timeline">{p.timeline.map((tl) => (
              <li key={tl.caseId}><time dateTime={tl.date}>{fmtDate(tl.date)}</time>
                <span><Link to={`/case/${tl.caseId}`}>{tl.title}</Link><span className="small muted"> · {tl.situation}{tl.chosen ? ` · ${tl.chosen}` : ''}</span><br />
                  <span className={'small ' + (tl.status === 'due' ? 'late' : 'muted')}>{tl.outcomeLabel ? t('{statusLabel}: {outcomeLabel} (as you reported)', { statusLabel: tl.statusLabel, outcomeLabel: tl.outcomeLabel }) : tl.statusLabel}{tl.guess ? ' · ' + t('Guess: {hits} of {parts} right', { hits: tl.guess.hits, parts: tl.guess.parts }) : ''}</span></span></li>
            ))}</ul>
          </Panel></div>
          {p.outcomesTotal > 0 && (
            <Panel title={t('How it turned out')} lead={t('As you reported in your follow-ups.')}>
              <div className="stats">{Object.entries(p.outcomes).filter(([, n]) => n > 0).map(([k, n]) => stat(`${n} of ${p.outcomesTotal}`, ({ worked: t('It worked'), partly: t('Partly worked'), not_yet: t('Not resolved yet'), not_applied: t('Not used at work') } as Record<string, string>)[k]))}</div>
            </Panel>
          )}
          <Panel title={t('What you practiced')}>
            {p.practiced.map((c) => <div key={c.category} className="stack"><div className="caption">{c.category}</div><ul className="plain">{c.situations.map((s) => <li key={s.title}>{s.title} <span className="muted">× {s.count}</span></li>)}</ul></div>)}
            {p.tryNext && <p style={{ marginTop: 16 }}>{t('Try next:')} <Link to={`/new/${p.tryNext.id}`}>{title(p.tryNext.id)}</Link> <span className="muted">{p.tryNext.summary}</span></p>}
          </Panel>
        </>
      )}
      <div data-tour="pr-reminders"><Panel title={t('Email reminders')} lead={p.logMailer ? t('This server has no mail account set up, so reminders are written to the server log instead of being sent.') : undefined}>
        <ReminderToggle onChange={load} />
      </Panel></div>
    </>
  );
}
