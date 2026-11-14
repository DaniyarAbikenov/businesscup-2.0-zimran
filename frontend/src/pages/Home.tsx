import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSession } from '../App';
import { Journal, api, fmtDate } from '../api';
import { PageHeader, Panel, PrivacyBanner } from '../components/ui';

export default function Home() {
  const { me, pack } = useSession();
  const [j, setJ] = useState<Journal | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { api<Journal>('GET', '/journal').then(setJ).catch((e) => setError(e.message)); }, []);
  const profile = me.profile!;
  const role = pack.roles.find((r) => r.id === profile.roleId)!;
  const fears = pack.fears.filter((f) => profile.fears.includes(f.id)).map((f) => f.label.toLowerCase());
  const sits = pack.situations.filter((s) => s.applies_to.includes('*') || s.applies_to.includes(profile.roleId));

  return (
    <>
      <PageHeader eyebrow={role.label + (profile.industry ? ' · ' + profile.industry : '')} title="What are you facing this week?"
        lead={fears.length ? `You told us you worry about ${fears.join('; ')}. Pick a situation and test your options before you commit.` : 'Pick a situation and test your options before you commit.'} />
      <PrivacyBanner />
      {error && <div className="banner bad" role="alert">{error}</div>}
      {j && j.followups.length > 0 && (
        <Panel title="What happened?" lead="You made these decisions. Tell us how they played out so your journal reflects reality.">
          <ul className="plain">{j.followups.map((f) => <li key={f.caseId}><Link to={`/case/${f.caseId}`}>{f.title}</Link> <span className="muted">{f.overdue ? '(due now)' : `(due ${fmtDate(f.due)})`}</span></li>)}</ul>
        </Panel>
      )}
      <Panel title="Situations">
        {sits.map((s) => (
          <div key={s.id} className="stack">
            <h3>{s.title}</h3>
            <p className="muted" style={{ maxWidth: '62ch' }}>{s.summary}</p>
            <Link className="btn btn-primary" to={`/new/${s.id}`}>Start this situation</Link>
          </div>
        ))}
        <p className="small muted" style={{ marginTop: 24 }}>Next: late vendor delivery, scope creep, status report.</p>
      </Panel>
      {j && j.cases.length > 0 && (
        <Panel title="Your cases">
          <ul className="plain">{j.cases.slice(0, 6).map((c) => (
            <li key={c.id}><Link to={`/case/${c.id}`}>{c.title}</Link> <span className="muted">{c.status === 'draft' ? 'not decided yet' : c.followupDone ? 'decided, follow-up done' : 'decided'}</span></li>
          ))}</ul>
        </Panel>
      )}
      <p style={{ marginTop: 24 }}><Link to="/onboarding">Edit my role and concerns</Link></p>
    </>
  );
}
