import { FormEvent, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useSession } from '../App';
import { Draft, api } from '../api';
import { notify } from '../components/Toaster';
import { Button, Field, PageHeader, Panel, PrivacyBanner } from '../components/ui';

/** Text box that asks the AI for a new situation. Hidden, with the reason, when the server has no AI. */
export function CreateSituation({ compact, initialText = '' }: { compact?: boolean; initialText?: string }) {
  const { me } = useSession();
  const nav = useNavigate();
  const [text, setText] = useState(initialText);
  const [ack, setAck] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (!me.llmEnabled) return <p className="small muted">Creating your own situation needs the AI, and the AI is not configured on this server (no ANTHROPIC_API_KEY). The catalog above still works without it.</p>;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (text.trim().length < 30) return setError('Write a few sentences (at least 30 characters).');
    if (!ack) return setError('Confirm there is no confidential information.');
    setBusy(true);
    try {
      const draft = await api<Draft>('POST', '/situations/draft', { text, privacyAck: ack });
      nav('/my/preview', { state: { draft } });
    } catch (x: any) { setError(x.message); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={submit} noValidate>
      <Field id="newsit" label="Describe the case" help="What happens, who is involved, what you have to decide. Leave out names and confidential details.">
        {(a) => <textarea className="input" rows={compact ? 4 : 6} maxLength={4000} {...a} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="A client asked me to change the invoice terms after the contract was signed. I am not sure whether to ask my manager first, and the project lead wants me to answer today." />}
      </Field>
      <label className="check"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> The text has no confidential employer or client information. It is sent to our AI provider, Anthropic, and not stored by us.</label>
      {error && <div className="field error" role="alert">{error}</div>}
      <div className="row" style={{ marginTop: 16 }}><Button type="submit" busy={busy}>Generate a situation</Button></div>
    </form>
  );
}

export function CreateSituationPage() {
  const text = (useLocation().state as { text?: string } | null)?.text ?? '';
  return (
    <div className="narrow">
      <PageHeader eyebrow="My situations" title="Create a new situation" lead="AI proposes the wording, the steps and an example. The calculation stays with our calculators, and you see everything before it is saved." />
      <PrivacyBanner />
      <Panel><CreateSituation initialText={text} /></Panel>
    </div>
  );
}

export function PreviewSituationPage() {
  const draft = (useLocation().state as { draft?: Draft } | null)?.draft;
  const { refresh } = useSession();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!draft) return <Navigate to="/" replace />;
  const s = draft.situation;
  const engineName = s.engine === 'priorities' ? 'competing priorities' : 'change request';

  async function save() {
    setBusy(true); setError('');
    try {
      const r = await api<{ situation: { id: string } }>('POST', '/situations', { preset: draft!.preset });
      await refresh();
      notify('Saved to My situations.');
      nav(`/new/${r.situation.id}`, { replace: true });
    } catch (x: any) { setError(x.message); } finally { setBusy(false); }
  }
  const qs = s.questions.flatMap((q) => [q, ...(q.fields ?? [])]);
  return (
    <div className="narrow">
      <PageHeader eyebrow="Preview · nothing is saved yet" title={s.title} lead={s.summary} />
      <div className="banner ok" role="note"><strong className="ai-badge">AI-made, not expert-checked</strong> The wording and example come from AI. The numbers come from our {engineName} calculator, and every value is checked by code. Read it before you rely on it.</div>
      <Panel title="Questions you will answer" lead="The questions are fixed by the calculator. The AI may only reword them.">
        <ul className="plain">{qs.map((q) => <li key={q.id}><b>{q.label}</b>{q.help && <span className="muted"> {q.help}</span>}</li>)}</ul>
      </Panel>
      <Panel title="Options it will compare">
        {Object.entries(s.options).map(([k, o]) => (
          <div key={k} className="stack"><h3>{o.label}</h3><ol className="plain">{o.nextSteps.map((n, i) => <li key={i}>{n}</li>)}</ol></div>
        ))}
      </Panel>
      <Panel title="Common mistakes"><ul className="plain">{s.pitfalls.map((p, i) => <li key={i}>{p}</li>)}</ul></Panel>
      {s.storylines && s.storylines.length > 0 && (
        <Panel title="Example storyline" lead="Invented numbers to try it out. You can also start with your own.">
          {s.storylines.map((st) => <div key={st.id}><b>{st.title}</b><p className="muted">{st.story}</p></div>)}
        </Panel>
      )}
      {error && <div className="banner bad" role="alert">{error}</div>}
      <div className="row" style={{ marginTop: 16 }}>
        <Button onClick={save} busy={busy}>Save to My situations</Button>
        <Link className="btn btn-secondary" to="/">Discard</Link>
      </div>
    </div>
  );
}
