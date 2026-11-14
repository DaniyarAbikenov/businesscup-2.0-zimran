import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { SavedDoc, api, fmtStamp } from '../api';
import { notify } from '../components/Toaster';
import { Button, PageHeader, Panel } from '../components/ui';

// Library of everything saved: Change Requests (with edits) and messages to the client.
export default function DocumentsPage() {
  const [docs, setDocs] = useState<SavedDoc[] | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => { api('GET', '/documents').then((r) => setDocs(r.documents)).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!docs) return <p className="muted">Loading</p>;
  const copy = async (d: SavedDoc) => {
    try { await navigator.clipboard.writeText(d.body); notify('Copied to clipboard'); } catch { notify('Select the text and copy it manually', 'bad'); }
  };
  return (
    <>
      <PageHeader eyebrow="Library" title="Your documents" lead="Every Change Request and client message you saved. They stay with your account." />
      {docs.length === 0 && <Panel><p className="muted">Nothing saved yet. Decide on a situation and your Change Request appears here.</p></Panel>}
      {docs.map((d) => (
        <Panel key={d.id} title={d.label} lead={`${d.caseTitle} · updated ${fmtStamp(d.updatedAt)}${d.revisions > 1 ? ` · ${d.revisions} versions` : ''}`}>
          {open === d.id && <pre className="docview">{d.body}</pre>}
          <div className="row">
            <Button variant="secondary" onClick={() => setOpen(open === d.id ? null : d.id)}>{open === d.id ? 'Hide' : 'Preview'}</Button>
            <Button variant="secondary" onClick={() => copy(d)}>Copy</Button>
            <Link to={`/case/${d.caseId}`}>Open case</Link>
          </div>
        </Panel>
      ))}
    </>
  );
}
