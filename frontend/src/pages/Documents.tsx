import { TourScreen } from '../tour/TourHost';
import { t } from '../i18n';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { SavedDoc, api, fmtStamp } from '../api';
import { notify } from '../components/Toaster';
import { Button, CaseTabs, PageHeader, Panel } from '../components/ui';

// Library of everything saved: Change Requests (with edits) and messages to the client.
export default function DocumentsPage() {
  const [docs, setDocs] = useState<SavedDoc[] | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => { api('GET', '/documents').then((r) => setDocs(r.documents)).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!docs) return <p className="muted">{t('Loading')}</p>;
  const copy = async (d: SavedDoc) => {
    try { await navigator.clipboard.writeText(d.body); notify(t('Copied to clipboard')); } catch { notify(t('Select the text and copy it manually'), 'bad'); }
  };
  return (
    <>
      <TourScreen name="cases" />
      <CaseTabs />
      <PageHeader eyebrow={t('Library')} title={t('Your documents')} lead={t('Every message and document you saved. They stay with your account.')} />
      {docs.length === 0 && <Panel><p className="muted">{t('Nothing saved yet. When you decide on a scenario, the message or document it creates appears here, and you can edit and copy it.')}</p></Panel>}
      {docs.map((d) => (
        <Panel key={d.id} title={d.label} lead={t('{caseTitle} · updated {updatedAt}{versions}', { caseTitle: d.caseTitle, updatedAt: fmtStamp(d.updatedAt), versions: d.revisions > 1 ? ` · ${d.revisions} versions` : '' })}>
          {open === d.id && <pre className="docview">{d.body}</pre>}
          <div className="row">
            <Button variant="secondary" onClick={() => setOpen(open === d.id ? null : d.id)}>{open === d.id ? t('Hide') : t('Preview')}</Button>
            <Button variant="secondary" onClick={() => copy(d)}>{t('Copy')}</Button>
            <Link to={`/case/${d.caseId}`}>{t('Open case')}</Link>
          </div>
        </Panel>
      ))}
    </>
  );
}
