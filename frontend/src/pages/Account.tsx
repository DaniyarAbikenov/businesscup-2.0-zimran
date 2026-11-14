import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../App';
import { api } from '../api';
import { notify } from '../components/Toaster';
import { Button, Field, PageHeader, Panel } from '../components/ui';

export default function AccountPage() {
  const { me, refresh } = useSession();
  const nav = useNavigate();
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function remove(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      await api('DELETE', '/account', { confirm });
      await refresh(); nav('/'); notify('Your account and all its data were deleted.');
    } catch (x: any) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <div className="narrow">
      <PageHeader eyebrow="Account" title="Account and data" lead={`Signed in as ${me.user.email}.`} />
      <Panel title="What we keep"><p>Your profile, the situations you worked through with the numbers you entered, the documents you saved with their earlier versions, your reflections and follow-ups, and your journal. Nothing is shared with other users. If you ask for an AI draft, only the change title, decision, date, cost and your reasoning are sent to the AI provider.</p></Panel>
      <Panel title="Delete my account">
        <p>This permanently deletes your account and everything above. It cannot be undone.</p>
        <form onSubmit={remove}>
          <Field id="del" label="Type DELETE to confirm">{(a) => <input className="input" {...a} autoComplete="off" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
          {error && <div className="field error" role="alert">{error}</div>}
          <div className="row" style={{ marginTop: 16 }}><Button type="submit" busy={busy} disabled={confirm !== 'DELETE'}>Delete account and data</Button></div>
        </form>
      </Panel>
    </div>
  );
}
