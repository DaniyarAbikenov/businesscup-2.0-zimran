import { FormEvent, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useSession } from '../App';
import { Intake, Storyline, api } from '../api';
import { notify } from '../components/Toaster';
import { Button, Field, PageHeader, Panel, PrivacyBanner, QuestionGroups, initialAnswers } from '../components/ui';

/** Keyed by situation so moving between situations starts a fresh form. */
export default function NewCasePage() {
  const { situationId } = useParams();
  return <NewCase key={situationId} />;
}

function NewCase() {
  const { pack } = useSession();
  const { situationId } = useParams();
  const sit = pack.situations.find((s) => s.id === situationId);
  const nav = useNavigate();
  const loc = useLocation();
  const intake = (loc.state as { intake?: Intake } | null)?.intake;
  const introText = (loc.state as { text?: string } | null)?.text;
  const fromText = intake && intake.situationId === situationId ? intake : null;
  const [answers, setAnswers] = useState(() => (sit ? initialAnswers(sit.questions, fromText?.answers) : {}));
  const [story, setStory] = useState<Storyline | null>(null);
  const [showIntake, setShowIntake] = useState(!!fromText);
  const [conf, setConf] = useState('3');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [ack, setAck] = useState(false);
  if (!sit) return <Navigate to="/" replace />;

  const pick = (s: Storyline | null) => {
    setStory(s); setFields({}); setError(''); setShowIntake(false);
    setAnswers(initialAnswers(sit.questions, s?.answers));
    if (s) notify(`Storyline loaded: ${s.title}. Change anything you like.`);
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
      if (x.status === 402) { nav('/pricing?from=limit'); return; }
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
      <PageHeader eyebrow={`Step 1 of 3 · Clarify${sit.category ? ' · ' + sit.category : ''}`} title={sit.title} lead={sit.summary} />
      <PrivacyBanner />
      {showIntake && fromText && <IntakeNote intake={fromText} text={introText} labels={Object.fromEntries(sit.questions.map((q) => [q.id, q.label]))}
        titles={Object.fromEntries(pack.situations.map((s) => [s.id, s.title]))} />}
      {sit.storylines && sit.storylines.length > 0 && (
        <Panel title="Start from a storyline" lead="A realistic example with the numbers filled in. Use it to try the situation, or start blank with your own.">
          <div className="stories">
            {sit.storylines.map((s) => (
              <button key={s.id} type="button" className={'story' + (story?.id === s.id ? ' on' : '')} aria-pressed={story?.id === s.id} onClick={() => pick(s)}>
                <b>{s.title}</b><span>{s.story}</span>
              </button>
            ))}
            <button type="button" className={'story' + (story === null ? ' on' : '')} aria-pressed={story === null} onClick={() => pick(null)}>
              <b>My own situation</b><span>Start with an empty form.</span>
            </button>
          </div>
        </Panel>
      )}
      {story && <div className="banner ok" role="note"><strong>Storyline: {story.title}.</strong> These are example numbers, not yours. Edit them freely.</div>}
      <form onSubmit={submit} noValidate>
        <QuestionGroups sit={sit} answers={answers} fields={fields} onChange={setAnswers} />
        <Panel>
          <Field id="conf" label="How confident do you feel handling this right now?" help="1 is not at all, 5 is very. We compare it with how you feel afterwards.">
            {(a) => <select className="input" {...a} value={conf} onChange={(e) => setConf(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select>}
          </Field>
          <label className="check"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I did not enter confidential employer or client information.</label>
          {error && <div className="field error" role="alert">{error}</div>}
          <div className="row" style={{ marginTop: 24 }}><Button type="submit" busy={busy}>Compare my options</Button></div>
        </Panel>
      </form>
    </div>
  );
}

function IntakeNote({ intake, labels, titles, text }: { intake: Intake; labels: Record<string, string>; titles: Record<string, string>; text?: string }) {
  return (
    <div className="banner ok intake-note" role="note">
      <strong>{intake.source === 'ai' ? 'Filled in from your description by AI. Check every value.' : 'Matched from your description by keywords.'}</strong>
      {intake.filled.length > 0 && <p>Filled in: {intake.filled.map((id) => labels[id] ?? id).join(', ')}.</p>}
      {intake.missing.length > 0 && <p>Still needs your input: {intake.missing.join(', ')}.</p>}
      {intake.notes.length > 0 && <ul>{intake.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
      {intake.noMatch && <p className="small"><strong>Nothing in the catalog fits well?</strong> <Link to="/my/new" state={{ text }}>Create a new situation from this text</Link></p>}
      {intake.alternatives.length > 0 && <p className="small">Wrong situation? {intake.alternatives.map((id, i) => <span key={id}>{i > 0 && ', '}<Link to={`/new/${id}`}>{titles[id] ?? id}</Link></span>)}</p>}
    </div>
  );
}
