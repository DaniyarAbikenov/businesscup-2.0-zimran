import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../App';
import { Progress, api, fmtDate } from '../api';
import { notify } from '../components/Toaster';
import { PageHeader, Panel } from '../components/ui';

/** Opt-in email reminders: off by default. Used here and on the Account page. */
export function ReminderToggle({ onChange }: { onChange?: () => void }) {
  const { me, refresh } = useSession();
  const [on, setOn] = useState(!!me.profile?.emailReminders);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState('');
  const set = async (v: boolean) => {
    setBusy(true);
    try { await api('POST', '/progress/reminders', { enabled: v }); setOn(v); await refresh(); onChange?.(); notify(v ? 'Email reminders are on.' : 'Email reminders are off.'); }
    catch (x: any) { notify(x.message, 'bad'); } finally { setBusy(false); }
  };
  const sendNow = async () => {
    try { const r = await api<{ sent: number; logMailer: boolean }>('POST', '/progress/send-reminders-now', {}); setInfo(r.sent ? `${r.sent} reminder${r.sent === 1 ? '' : 's'} ${r.logMailer ? 'written to the server log' : 'sent'}.` : 'Nothing is due right now.'); }
    catch (x: any) { setInfo(x.message); }
  };
  return (
    <>
      <label className="check"><input type="checkbox" checked={on} disabled={busy} onChange={(e) => set(e.target.checked)} /> Email me when a follow-up is due, and once after a week if I have not started a second scenario. Every email has a link to turn this off.</label>
      <p className="small muted">We only use your sign-in email. Emails contain the title of your case, never your numbers.</p>
      {on && me.isDemo === false && <p className="small"><button type="button" className="btn btn-quiet" onClick={sendNow}>Send my due reminders now (testing)</button> {info}</p>}
    </>
  );
}

function ConfidenceChart({ items }: { items: Progress['confidence'] }) {
  const W = 320, H = 140, pad = 24;
  const x = (i: number) => (items.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (items.length - 1));
  const y = (v: number) => H - pad - ((v - 1) * (H - 2 * pad)) / 4;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" style={{ width: '100%', maxWidth: 520, height: 'auto' }}
      aria-label={'Confidence before and after: ' + items.map((c) => `${c.title} ${c.before} to ${c.after ?? 'not rated yet'}`).join('; ')}>
      {[1, 2, 3, 4, 5].map((v) => <g key={v}><line x1={pad} x2={W - 8} y1={y(v)} y2={y(v)} stroke="currentColor" opacity=".12" /><text x={6} y={y(v) + 4} fontSize="10" fill="currentColor" opacity=".6">{v}</text></g>)}
      {items.map((c, i) => c.after !== null && <line key={'l' + i} x1={x(i)} x2={x(i)} y1={y(c.before)} y2={y(c.after)} stroke="var(--accent-700)" strokeWidth="2" />)}
      {items.map((c, i) => <circle key={'b' + i} cx={x(i)} cy={y(c.before)} r="5" fill="none" stroke="currentColor" strokeWidth="2"><title>{`${c.title}: before ${c.before}`}</title></circle>)}
      {items.map((c, i) => c.after !== null && <circle key={'a' + i} cx={x(i)} cy={y(c.after)} r="5" fill="var(--accent-700)"><title>{`${c.title}: after ${c.after}`}</title></circle>)}
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
  if (!p) return <p className="muted">Loading</p>;
  const stat = (n: string | number, l: string) => <div className="stat"><b>{n}</b><span>{l}</span></div>;
  const pct = Math.min(100, Math.round((p.day / p.windowDays) * 100));
  const mile = [['First situation', p.firsts.situation], ['First decision', p.firsts.decision], ['First debrief', p.firsts.debrief]] as const;
  const title = (id: string) => pack.situations.find((s) => s.id === id)?.title ?? id;

  return (
    <>
      <PageHeader eyebrow="Progress" title="Your first 90 days" lead="Everything here comes from what you entered and reported. RoleShift cannot see your workplace." />
      <Panel>
        <p style={{ margin: 0 }}><b>Day {p.day}</b> {p.inWindow ? `of ${p.windowDays}` : `(past the first ${p.windowDays})`} · started {fmtDate(p.startedAt)}</p>
        <div className="daybar" role="img" aria-label={`Day ${p.day} of ${p.windowDays}`}>
          <span style={{ width: `${pct}%` }} />
          {p.milestones.map((m) => <i key={m} style={{ left: `${(m / p.windowDays) * 100}%` }}><em>{m}</em></i>)}
        </div>
        <div className="stats" style={{ marginTop: 28 }}>
          {stat(p.counts.situations, 'situations tried')}{stat(p.counts.decisions, 'decisions made')}{stat(p.counts.followups, 'follow-ups done')}{stat(`${p.counts.documents} / ${p.counts.exported}`, 'documents saved / exported')}
        </div>
        {p.inactiveHint && <div className="banner" role="note" style={{ marginTop: 16 }}>It has been {p.inactiveDays} days since your last scenario. Is something coming up at work?</div>}
      </Panel>

      {p.counts.situations === 0 ? (
        <Panel title="Nothing here yet" lead="Your progress appears as you work through scenarios. Start with one you expect this week.">
          <div className="row"><Link className="btn btn-primary" to="/">Choose a scenario</Link><Link className="btn btn-secondary" to="/">Describe your scenario</Link></div>
        </Panel>
      ) : (
        <>
          <Panel title="Milestones">
            <ul className="plain">{mile.map(([l, d]) => <li key={l}>{d ? <>✓ {l} <span className="muted">{fmtDate(d)}</span></> : <span className="muted">○ {l}</span>}</li>)}</ul>
          </Panel>
          <Panel title="Confidence" lead={p.averageChange === null ? 'Rate your confidence after a decision (the reflection step) to see how it changes.' : `Average change: ${p.averageChange > 0 ? '+' : ''}${p.averageChange}. Open circle: before, filled: after.`}>
            {p.confidence.length > 0 ? <ConfidenceChart items={p.confidence} /> : <p className="muted">No decisions yet.</p>}
          </Panel>
          <Panel title="Decisions">
            <ul className="timeline">{p.timeline.map((t) => (
              <li key={t.caseId}><time dateTime={t.date}>{fmtDate(t.date)}</time>
                <span><Link to={`/case/${t.caseId}`}>{t.title}</Link><span className="small muted"> · {t.situation}{t.chosen ? ` · ${t.chosen}` : ''}</span><br />
                  <span className={'small ' + (t.status === 'due' ? 'late' : 'muted')}>{t.outcomeLabel ? `${t.statusLabel}: ${t.outcomeLabel} (as you reported)` : t.statusLabel}</span></span></li>
            ))}</ul>
          </Panel>
          {p.outcomesTotal > 0 && (
            <Panel title="How it turned out" lead="As you reported in your follow-ups.">
              <div className="stats">{Object.entries(p.outcomes).filter(([, n]) => n > 0).map(([k, n]) => stat(`${n} of ${p.outcomesTotal}`, ({ worked: 'It worked', partly: 'Partly worked', not_yet: 'Not resolved yet', not_applied: 'Not used at work' } as Record<string, string>)[k]))}</div>
            </Panel>
          )}
          <Panel title="What you practiced">
            {p.practiced.map((c) => <div key={c.category} className="stack"><div className="caption">{c.category}</div><ul className="plain">{c.situations.map((s) => <li key={s.title}>{s.title} <span className="muted">× {s.count}</span></li>)}</ul></div>)}
            {p.tryNext && <p style={{ marginTop: 16 }}>Try next: <Link to={`/new/${p.tryNext.id}`}>{title(p.tryNext.id)}</Link> <span className="muted">{p.tryNext.summary}</span></p>}
          </Panel>
        </>
      )}
      <Panel title="Email reminders" lead={p.logMailer ? 'This server has no mail account set up, so reminders are written to the server log instead of being sent.' : undefined}>
        <ReminderToggle onChange={load} />
      </Panel>
    </>
  );
}
