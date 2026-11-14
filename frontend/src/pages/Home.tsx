import { t, tn } from '../i18n';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../App';
import { Billing, Journal, Progress, api, fmtDate } from '../api';
import Describe from '../components/Describe';
import { skillLabel } from '../components/skills';
import { ExampleButton, PROMISE, Welcome, guideDone } from '../components/Guide';
import { notify } from '../components/Toaster';
import { Button, PageHeader, Panel } from '../components/ui';
import { CreateSituation } from './MySituations';

const firstSentence = (t: string) => (t.match(/^.*?[.!?](\s|$)/)?.[0] ?? t).trim();

export default function Home() {
  const { me, pack, refresh } = useSession();
  const [j, setJ] = useState<Journal | null>(null);
  const [error, setError] = useState('');
  const [b, setB] = useState<Billing | null>(null);
  const [pr, setPr] = useState<Progress | null>(null);
  const [welcome, setWelcome] = useState(!guideDone());
  useEffect(() => {
    api<Journal>('GET', '/journal').then(setJ).catch((e) => setError(e.message));
    api<Billing>('GET', '/billing').then(setB).catch(() => {});
    api<Progress>('GET', '/progress').then(setPr).catch(() => {});
  }, []);
  const profile = me.profile!;
  const role = pack.roles.find((r) => r.id === profile.roleId)!;
  const sits = pack.situations.filter((s) => s.applies_to.includes('*') || s.applies_to.includes(profile.roleId));
  const isNew = !!j && j.cases.length === 0;
  const open = (j?.cases ?? []).filter((c) => c.status === 'draft');
  const order = role.recommended ?? [];
  const rank = (id: string) => (order.includes(id) ? order.indexOf(id) : 99);
  const recommended = [...sits].sort((a, b2) => Number(!!a.aiMade) - Number(!!b2.aiMade) || rank(a.id) - rank(b2.id)).slice(0, 4);

  return (
    <>
      <PageHeader eyebrow={role.label + (profile.industry ? ' · ' + profile.industry : '')} title={t('What are you facing this week?')} lead={PROMISE} />
      {me.isDemo && (
        <div className="strip" role="note"><span><strong>{t('You are in the demo.')}</strong> {t('The cases under My cases are sample data. Start here to see a result in seconds.')}</span><ExampleButton label={t('Start here: a worked example')} /></div>
      )}
      {error && <div className="banner bad" role="alert">{error}</div>}
      {j && j.followups.length > 0 && (
        <div className="strip" role="note"><span><strong>{t('How did it go?')}</strong> {tn(j.followups.length, '{n} decision is waiting for your note: ', '{n} decisions are waiting for your note: ')}{j.followups.slice(0, 2).map((f, i) => <span key={f.caseId}>{i > 0 && ', '}<Link to={`/case/${f.caseId}`}>{f.title}</Link></span>)}.</span></div>
      )}
      {welcome && isNew && !me.isDemo && <Welcome onClose={() => setWelcome(false)} />}
      <Describe />
      <Panel title={t('Or start from a ready scenario')} lead={t('Each one asks for a few facts, compares your options with calculated outcomes, and gives you a message to send.')}>
        <div className="cards">
          {recommended.map((s) => (
            <div key={s.id} className="card">
              <div><h3>{s.title}{s.aiMade && <span className="ai-badge">{t('AI-made, not expert-checked')}</span>}</h3><p>{firstSentence(s.summary)}</p>{skillLabel(s.skill) && <p className="small muted">{t('Trains: {skill}', { skill: skillLabel(s.skill) })}</p>}</div>
              <div className="row"><Link className="btn btn-primary" to={`/new/${s.id}`}>{t('Start')}</Link>{s.storylines && s.storylines.length > 0 && <span className="small muted">{tn(s.storylines.length, '{n} example', '{n} examples')}</span>}</div>
            </div>
          ))}
        </div>
        {isNew && !welcome && <p className="small muted" style={{ marginTop: 16 }}>{t('New here?')} <Link to="/guide">{t('See how it works')}</Link> {t('or')} <ExampleButton label={t('try a worked example')} />.</p>}
      </Panel>

      {open.length > 0 && (
        <Panel title={t('Continue where you left off')}>
          <ul className="plain">{open.slice(0, 5).map((c) => <li key={c.id}><Link to={`/case/${c.id}`}>{c.title}</Link> <span className="muted">{t('not decided yet')}</span></li>)}</ul>
        </Panel>
      )}
      {pr && pr.counts.situations > 0 && (
        <Panel title={t('Your first 90 days')}>
          <p className="small muted" style={{ margin: 0 }}>
            {pr.inWindow ? t('Day {day} of {total}.', { day: pr.day, total: pr.windowDays }) : t('Day {day}, past the first {total}.', { day: pr.day, total: pr.windowDays })} {tn(pr.counts.decisions, '{n} decision made', '{n} decisions made')}
            {pr.averageChange !== null && <>, {t('confidence {change} on average', { change: (pr.averageChange > 0 ? '+' : '') + pr.averageChange })}</>}. {pr.inactiveHint && <>{t('It has been {n} days since your last scenario.', { n: pr.inactiveDays })} </>}
            <Link to="/progress">{t('See your progress')}</Link>
          </p>
        </Panel>
      )}
      <details className="more">
        <summary>{t('Browse all scenarios')}</summary>
        <div style={{ marginTop: 16 }}>
          {b && <p className="small muted plan-line">{b.plan === 'pass'
            ? <>Pass active until {fmtDate(b.pass!.expiresAt.slice(0, 10))}.</>
            : <>{t('Free plan: {remaining} of {limit} scenarios left.', { remaining: b.remaining, limit: b.limit })} <Link to="/pricing">{t('See pricing')}</Link></>}</p>}
          {Array.from(new Set(sits.map((s) => s.category ?? t('Other')))).map((cat) => (
            <div key={cat} className="catalog-group">
              <div className="caption">{cat}</div>
              {sits.filter((s) => (s.category ?? t('Other')) === cat).map((s) => (
                <div key={s.id} className="stack catalog-item">
                  <h3>{s.title}{s.aiMade && <span className="ai-badge">{t('AI-made, not expert-checked')}</span>}</h3>
                  <p className="muted" style={{ maxWidth: '62ch' }}>{s.summary}</p>
                  <div className="row">
                    <Link className="btn btn-primary" to={`/new/${s.id}`}>{t('Start')}</Link>
                    {s.aiMade && <Button variant="quiet" type="button" onClick={async () => {
                      if (!window.confirm(t('Delete "{title}" from your scenarios?', { title: s.title }))) return;
                      try { await api('DELETE', `/situations/${s.id.slice(3)}`, {}); notify(t('Scenario deleted.')); await refresh(); } catch (x: any) { notify(x.message, 'bad'); }
                    }}>{t('Delete')}</Button>}
                    {s.storylines && s.storylines.length > 0 && <span className="small muted">{tn(s.storylines.length, '{n} example to try', '{n} examples to try')}</span>}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </details>
      <details className="more">
        <summary>{t('Cannot find your case? Create a scenario with AI')}</summary>
        <div style={{ marginTop: 16 }}><p className="small muted">{t('Describe a case that is not in the list. AI turns it into a scenario that uses one of our calculators, and you review it before saving.')}</p><CreateSituation compact /></div>
      </details>
      <p style={{ marginTop: 24 }}><Link to="/onboarding">{t('Edit my position and concerns')}</Link></p>
    </>
  );
}
