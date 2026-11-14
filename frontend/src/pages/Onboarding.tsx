import { notify } from '../components/Toaster';
import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../App';
import { api } from '../api';
import { Button, Field, PageHeader, Panel, PrivacyBanner } from '../components/ui';

export default function Onboarding() {
  const { me, pack, refresh } = useSession();
  const nav = useNavigate();
  const p = me.profile;
  const [roleId, setRoleId] = useState(p?.roleId ?? pack.roles[0].id);
  const [industry, setIndustry] = useState(p?.industry ?? '');
  const [tenure, setTenure] = useState(p?.tenure ?? '1-3m');
  const [fears, setFears] = useState<string[]>(p?.fears ?? []);
  const [fearNote, setFearNote] = useState(p?.fearNote ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api('PUT', '/profile', { roleId, industry, tenure, fears, fearNote });
      await refresh();
      notify('Profile saved.');
      nav('/');
    } catch (x: any) {
      setError(x.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <PageHeader eyebrow="Welcome" title="Tell us about your new position" lead="Facing a decision in a new role? You will try your options with your own numbers before you commit, and get a ready message to send. Tell us your position (one minute) and we pick the right scenarios." />
      <PrivacyBanner />
      <Panel>
        <form onSubmit={submit}>
          <Field id="role" label="Your new position">{(a) => (
            <select className="input" {...a} value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              {pack.roles.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>)}
          </Field>
          <Field id="industry" label="Industry (optional)">{(a) => <input className="input" {...a} maxLength={80} placeholder="Fintech, healthcare, games" value={industry} onChange={(e) => setIndustry(e.target.value)} />}</Field>
          <Field id="tenure" label="How long have you been in this position?">{(a) => (
            <select className="input" {...a} value={tenure} onChange={(e) => setTenure(e.target.value)}>
              {pack.tenures.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>)}
          </Field>
          <fieldset style={{ border: 0, padding: 0, margin: '16px 0 0' }}>
            <legend style={{ fontSize: 14, fontWeight: 600, padding: 0, marginBottom: 4 }}>What worries you most? Pick any.</legend>
            <div className="checks">
              {pack.fears.map((f) => (
                <label key={f.id} className="check">
                  <input type="checkbox" checked={fears.includes(f.id)} onChange={(e) => setFears(e.target.checked ? [...fears, f.id] : fears.filter((x) => x !== f.id))} />
                  {f.label}
                </label>
              ))}
            </div>
          </fieldset>
          <Field id="note" label="Anything else? (optional)" help="Keep it generic: no names or company details.">
            {(a) => <textarea className="input" {...a} maxLength={500} value={fearNote} onChange={(e) => setFearNote(e.target.value)} />}
          </Field>
          {error && <div className="field error" role="alert">{error}</div>}
          <div className="row" style={{ marginTop: 24 }}><Button type="submit" busy={busy}>Save and continue</Button></div>
        </form>
      </Panel>
    </div>
  );
}
