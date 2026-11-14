import { FormEvent, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { useSession } from '../App';
import { api } from '../api';
import { notify } from '../components/Toaster';
import { Button, Field, PageHeader, Panel, PrivacyBanner, QuestionField, initialAnswers } from '../components/ui';

export default function NewCase() {
  const { pack } = useSession();
  const { situationId } = useParams();
  const sit = pack.situations.find((s) => s.id === situationId);
  const nav = useNavigate();
  const [answers, setAnswers] = useState(() => (sit ? initialAnswers(sit.questions) : {}));
  const [conf, setConf] = useState('3');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [ack, setAck] = useState(false);
  const [sampleOn, setSampleOn] = useState(false);
  if (!sit) return <Navigate to="/" replace />;

  const group = (g: string) => sit.questions.filter((q) => q.group === g).map((q) => (
    <QuestionField key={q.id} q={q} value={answers[q.id]} error={fields[q.id]} onChange={(v) => setAnswers({ ...answers, [q.id]: v })} />
  ));

  const loadSample = () => {
    setAnswers({ ...answers, ...Object.fromEntries(Object.entries(sit!.sample ?? {}).map(([k, v]) => [k, String(v)])) });
    setSampleOn(true); setFields({});
    notify('Sample numbers loaded. Replace them with your own.');
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!ack) { setError('Confirm that you did not enter confidential information.'); return; }
    setBusy(true);
    setError('');
    setFields({});
    try {
      const r = await api('POST', '/cases', { situationId: sit!.id, privacyAck: ack, confidenceBefore: Number(conf), inputs: answers });
      nav(`/case/${r.case.id}`);
    } catch (x: any) {
      setError(x.message);
      setFields(x.fields ?? {});
      const first = Object.keys(x.fields ?? {})[0];
      if (first) setTimeout(() => document.getElementById('q_' + first)?.focus(), 0);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <PageHeader eyebrow="Step 1 of 3 · Clarify" title={sit.title} lead="Good answers here make the result useful. Ask the client and your team instead of guessing." />
      <PrivacyBanner />
      {sit.sample && (
        <div className="row" style={{ marginBottom: 16 }}>
          <Button type="button" variant="secondary" onClick={loadSample}>Try with sample data</Button>
          {sampleOn && <span className="small muted">Sample numbers, not yours. Edit them freely.</span>}
        </div>
      )}
      <form onSubmit={submit} noValidate>
        <Panel title="The change">{group('change')}</Panel>
        <Panel title="Your project numbers"><div className="grid-2">{group('numbers')}</div></Panel>
        <Panel>
          <details>
            <summary style={{ marginTop: 0 }}>Calculation assumptions (defaults are reasonable)</summary>
            <div className="grid-2">{group('assumptions')}</div>
          </details>
          <Field id="conf" label="How confident do you feel handling this right now?" help="1 is not at all, 5 is very. We compare it with how you feel afterwards.">
            {(a) => <select className="input" {...a} value={conf} onChange={(e) => setConf(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select>}
          </Field>
          <label className="check"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I did not enter confidential employer or client information.</label>
          {error && <div className="field error" role="alert">{error}</div>}
          <div className="row" style={{ marginTop: 24 }}><Button type="submit" busy={busy}>Calculate the impact</Button></div>
        </Panel>
      </form>
    </div>
  );
}
