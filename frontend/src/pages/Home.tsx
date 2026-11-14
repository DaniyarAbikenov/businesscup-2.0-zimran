import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../App';
import { Billing, Journal, Progress, api, fmtDate } from '../api';
import Describe from '../components/Describe';
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
  const recommended = [...sits].sort((a, b2) => Number(!!a.aiMade) - Number(!!b2.aiMade)).slice(0, 4);

  return (
    <>
      <PageHeader eyebrow={role.label + (profile.industry ? ' · ' + profile.industry : '')} title="What are you facing this week?" lead={PROMISE} />
      {me.isDemo && (
        <div className="strip" role="note"><span><strong>You are in the demo.</strong> The cases under My cases are sample data. Start here to see a result in seconds.</span><ExampleButton label="Start here: a worked example" /></div>
      )}
      {error && <div className="banner bad" role="alert">{error}</div>}
      {j && j.followups.length > 0 && (
        <div className="strip" role="note"><span><strong>How did it go?</strong> {j.followups.length} decision{j.followups.length === 1 ? ' is' : 's are'} waiting for your note: {j.followups.slice(0, 2).map((f, i) => <span key={f.caseId}>{i > 0 && ', '}<Link to={`/case/${f.caseId}`}>{f.title}</Link></span>)}.</span></div>
      )}
      {welcome && isNew && !me.isDemo && <Welcome onClose={() => setWelcome(false)} />}
      <Describe />
      <Panel title="Or start from a ready scenario" lead="Each one asks for a few facts, compares your options with calculated outcomes, and gives you a message to send.">
        <div className="cards">
          {recommended.map((s) => (
            <div key={s.id} className="card">
              <div><h3>{s.title}{s.aiMade && <span className="ai-badge">AI-made, not expert-checked</span>}</h3><p>{firstSentence(s.summary)}</p></div>
              <div className="row"><Link className="btn btn-primary" to={`/new/${s.id}`}>Start</Link>{s.storylines && s.storylines.length > 0 && <span className="small muted">{s.storylines.length} examples</span>}</div>
            </div>
          ))}
        </div>
        {isNew && !welcome && <p className="small muted" style={{ marginTop: 16 }}>New here? <Link to="/guide">See how it works</Link> or <ExampleButton label="try a worked example" />.</p>}
      </Panel>

      {open.length > 0 && (
        <Panel title="Continue where you left off">
          <ul className="plain">{open.slice(0, 5).map((c) => <li key={c.id}><Link to={`/case/${c.id}`}>{c.title}</Link> <span className="muted">not decided yet</span></li>)}</ul>
        </Panel>
      )}
      {pr && pr.counts.situations > 0 && (
        <Panel title="Your first 90 days">
          <p className="small muted" style={{ margin: 0 }}>
            {pr.inWindow ? `Day ${pr.day} of ${pr.windowDays}.` : `Day ${pr.day}, past the first ${pr.windowDays}.`} {pr.counts.decisions} decision{pr.counts.decisions === 1 ? '' : 's'} made
            {pr.averageChange !== null && <>, confidence {pr.averageChange > 0 ? '+' : ''}{pr.averageChange} on average</>}. {pr.inactiveHint && <>It has been {pr.inactiveDays} days since your last scenario. </>}
            <Link to="/progress">See your progress</Link>
          </p>
        </Panel>
      )}
      <details className="more">
        <summary>Browse all scenarios</summary>
        <div style={{ marginTop: 16 }}>
          {b && <p className="small muted plan-line">{b.plan === 'pass'
            ? <>Pass active until {fmtDate(b.pass!.expiresAt.slice(0, 10))}.</>
            : <>Free plan: {b.remaining} of {b.limit} scenarios left. <Link to="/pricing">See pricing</Link></>}</p>}
          {Array.from(new Set(sits.map((s) => s.category ?? 'Other'))).map((cat) => (
            <div key={cat} className="catalog-group">
              <div className="caption">{cat}</div>
              {sits.filter((s) => (s.category ?? 'Other') === cat).map((s) => (
                <div key={s.id} className="stack catalog-item">
                  <h3>{s.title}{s.aiMade && <span className="ai-badge">AI-made, not expert-checked</span>}</h3>
                  <p className="muted" style={{ maxWidth: '62ch' }}>{s.summary}</p>
                  <div className="row">
                    <Link className="btn btn-primary" to={`/new/${s.id}`}>Start</Link>
                    {s.aiMade && <Button variant="quiet" type="button" onClick={async () => {
                      if (!window.confirm(`Delete "${s.title}" from your scenarios?`)) return;
                      try { await api('DELETE', `/situations/${s.id.slice(3)}`, {}); notify('Scenario deleted.'); await refresh(); } catch (x: any) { notify(x.message, 'bad'); }
                    }}>Delete</Button>}
                    {s.storylines && s.storylines.length > 0 && <span className="small muted">{s.storylines.length} examples to try</span>}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </details>
      <details className="more">
        <summary>Cannot find your case? Create a scenario with AI</summary>
        <div style={{ marginTop: 16 }}><p className="small muted">Describe a case that is not in the list. AI turns it into a scenario that uses one of our calculators, and you review it before saving.</p><CreateSituation compact /></div>
      </details>
      <p style={{ marginTop: 24 }}><Link to="/onboarding">Edit my position and concerns</Link></p>
    </>
  );
}
