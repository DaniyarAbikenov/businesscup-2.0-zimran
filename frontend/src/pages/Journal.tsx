import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Journal, api, fmtDate, fmtStamp } from '../api';
import { CaseTabs, PageHeader, Panel } from '../components/ui';

export default function JournalPage() {
  const [j, setJ] = useState<Journal | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { api<Journal>('GET', '/journal').then(setJ).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!j) return <p className="muted">Loading</p>;
  const s = j.stats;
  const stat = (n: string | number, l: string) => <div className="stat"><b>{n}</b><span>{l}</span></div>;
  return (
    <>
      <CaseTabs />
      <PageHeader eyebrow="Progress" title="Your journal" lead="Follow-up entries are what you told us. RoleShift cannot see your workplace." />
      <Panel>
        <div className="stats">
          {stat(s.started, 'situations started')}
          {stat(s.decided, 'decisions made')}
          {stat(s.followedUp, 'follow-ups done')}
          {stat(s.confidenceChange === null ? '-' : (s.confidenceChange > 0 ? '+' : '') + s.confidenceChange, 'average confidence change')}
        </div>
      </Panel>
      {j.followups.length > 0 && (
        <Panel title="Waiting for your follow-up">
          <ul className="plain">{j.followups.map((f) => <li key={f.caseId}><Link to={`/case/${f.caseId}`}>{f.title}</Link> <span className="muted">{f.overdue ? '(due now)' : `(due ${fmtDate(f.due)})`}</span></li>)}</ul>
        </Panel>
      )}
      <Panel title="Timeline">
        {j.entries.length === 0 ? <p className="muted">Nothing yet. Start a scenario from Home.</p> : (
          <ul className="timeline">{j.entries.map((e) => (
            <li key={e.id}><time dateTime={e.created_at}>{fmtStamp(e.created_at)}</time><span>{e.case_id ? <Link to={`/case/${e.case_id}`}>{e.text}</Link> : e.text}</span></li>
          ))}</ul>
        )}
      </Panel>
    </>
  );
}
