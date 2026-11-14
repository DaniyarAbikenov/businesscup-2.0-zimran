import { t } from '../i18n';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useSession } from '../App';
import { Intake, Storyline, api } from '../api';
import { notify } from '../components/Toaster';
import { TourScreen } from '../tour/TourHost';
import { Wizard } from '../components/Wizard';
import { Button, DateChips, Field, PageHeader, Panel, PrivacyBanner, QuestionGroups, Stepper, initialAnswers } from '../components/ui';

/** Keyed by scenario so moving between scenarios starts a fresh form. */
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
  const [guessing, setGuessing] = useState<null | { engine: string; preview: any }>(null);
  const [guess, setGuess] = useState<Record<string, any>>({});
  const exampleId = (loc.state as { example?: string } | null)?.example;
  const ran = useRef(false);
  useEffect(() => {
    // "Try a worked example": fill in the example and go straight to the result (made-up numbers, no personal data)
    const s = sit?.storylines?.find((x) => x.id === exampleId);
    if (!sit || !s || ran.current) return;
    ran.current = true;
    const a = initialAnswers(sit.questions, s.answers);
    setStory(s); setAnswers(a); setAck(true); setBusy(true);
    api('POST', '/cases', { situationId: sit.id, privacyAck: true, confidenceBefore: 3, inputs: a })
      .then((r) => nav(`/case/${r.case.id}`, { replace: true }))
      .catch((x: any) => { if (x.status === 402) nav('/pricing?from=limit'); else { setError(x.message); setBusy(false); } });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!sit) return <Navigate to="/" replace />;

  const pick = (s: Storyline | null) => {
    setStory(s); setFields({}); setError(''); setShowIntake(false);
    setAnswers(initialAnswers(sit.questions, s?.answers));
    if (s) notify(t('Storyline loaded: {title}. Change anything you like.', { title: s.title }));
  };

  async function create(prediction: Record<string, any> | null) {
    setBusy(true); setError('');
    try {
      const r = await api('POST', '/cases', { situationId: sit!.id, privacyAck: ack, confidenceBefore: Number(conf), inputs: answers, ...(prediction ? { prediction } : {}) });
      nav(`/case/${r.case.id}`);
    } catch (x: any) {
      if (x.status === 402) { nav('/pricing?from=limit'); return; }
      setError(x.message);
      if (x.fields && Object.keys(x.fields).some((k) => !k.startsWith('prediction'))) setGuessing(null);
    } finally { setBusy(false); }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!ack) { setError(t('Confirm that you did not enter confidential information.')); return; }
    setBusy(true);
    setError('');
    setFields({});
    try {
      // for scenarios with a guess step, check the numbers first, then ask for a guess before showing any result
      const chk = await api('POST', '/cases/check', { situationId: sit!.id, inputs: answers });
      if (chk.preview) { setGuessing({ engine: chk.engine, preview: chk.preview }); setGuess({}); window.scrollTo(0, 0); return; }
      await create(null);
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

  if (guessing) {
    return (
      <div className="narrow">
        <Stepper current={1} />
        <TourScreen name="guess" />
        <PageHeader eyebrow={t('Your guess first')} title={t('What do you think the numbers will say?')} lead={t('Ten seconds. It trains your intuition: afterwards you see your guess next to the calculation. You can skip it.')} />
        <GuessStep sit={sit} g={guessing} value={guess} onChange={setGuess} busy={busy} error={error} onGo={() => create(guess)} onSkip={() => create(null)} onBack={() => setGuessing(null)} />
      </div>
    );
  }

  return (
    <div className="narrow">
      {!exampleId && <TourScreen name="form" />}
      <Stepper current={1} />
      <PageHeader eyebrow={t('Fill in{category}', { category: sit.category ? ' · ' + sit.category : '' })} title={sit.title} lead={sit.summary} />
      {exampleId && busy && <div className="banner ok" role="status">{t('Loading a worked example with made-up numbers. You will see the result in a moment.')}</div>}
      <PrivacyBanner />
      {showIntake && fromText && <IntakeNote intake={fromText} text={introText} labels={Object.fromEntries(sit.questions.map((q) => [q.id, q.label]))}
        titles={Object.fromEntries(pack.situations.map((s) => [s.id, s.title]))} />}
      {sit.storylines && sit.storylines.length > 0 && (
        <Panel title={t('Start from a storyline')} lead={t('A realistic example with the numbers filled in. Use it to try the scenario, or start blank with your own.')}>
          <div className="stories">
            {sit.storylines.map((s) => (
              <button key={s.id} type="button" className={'story' + (story?.id === s.id ? ' on' : '')} aria-pressed={story?.id === s.id} onClick={() => pick(s)}>
                <b>{s.title}</b><span>{s.story}</span>
              </button>
            ))}
            <button type="button" className={'story' + (story === null ? ' on' : '')} aria-pressed={story === null} onClick={() => pick(null)}>
              <b>{t('My own scenario')}</b><span>{t('Start with an empty form.')}</span>
            </button>
          </div>
        </Panel>
      )}
      {story && <div className="banner ok" role="note"><strong>{t('Example: {title}.', { title: story.title })}</strong> {t('These are example numbers, not yours. Edit them freely.')}</div>}
      <Wizard sit={sit} answers={answers} setAnswers={setAnswers} serverFields={fields} conf={conf} setConf={setConf} ack={ack} setAck={setAck} error={error} busy={busy} onSubmit={submit} />
    </div>
  );
}

function IntakeNote({ intake, labels, titles, text }: { intake: Intake; labels: Record<string, string>; titles: Record<string, string>; text?: string }) {
  return (
    <div className="banner ok intake-note" role="note">
      <strong>{intake.source === 'ai' ? t('Filled in from your description by AI. Check every value.') : t('Matched from your description by keywords.')}</strong>
      {intake.filled.length > 0 && <p>{t('Filled in: {list}.', { list: intake.filled.map((id) => labels[id] ?? id).join(', ') })}</p>}
      {intake.missing.length > 0 && <p>{t('Still needs your input: {list}.', { list: intake.missing.join(', ') })}</p>}
      {intake.notes.length > 0 && <ul>{intake.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
      {intake.noMatch && <p className="small"><strong>{t('Nothing in the catalog fits well?')}</strong> <Link to="/my/new" state={{ text }}>{t('Create a new scenario from this text')}</Link></p>}
      {intake.alternatives.length > 0 && <p className="small">{t('Wrong scenario?')} {intake.alternatives.map((id, i) => <span key={id}>{i > 0 && ', '}<Link to={`/new/${id}`}>{titles[id] ?? id}</Link></span>)}</p>}
    </div>
  );
}

/** The guess before the numbers: big buttons, always skippable. Nothing is computed here; the server scores it. */
function GuessStep({ sit, g, value, onChange, busy, error, onGo, onSkip, onBack }: { sit: { id: string; options: Record<string, { label: string }> }; g: { engine: string; preview: any }; value: Record<string, any>; onChange: React.Dispatch<React.SetStateAction<Record<string, any>>>; busy: boolean; error: string; onGo: () => void; onSkip: () => void; onBack: () => void }) {
  const set = (k: string, v: any) => onChange((prev) => ({ ...prev, [k]: v }));
  const choice = (on: boolean, label: string, onClick: () => void) => <button type="button" className={'story' + (on ? ' on' : '')} aria-pressed={on} onClick={onClick}><b>{label}</b></button>;
  let ready = false;
  let body: JSX.Element;
  if (g.engine === 'priorities') {
    ready = value.lateCount !== undefined && !!value.bestOrder;
    body = (<>
      <Panel title={t('If you work in the order you listed, how many tasks finish late?')}>
        <div className="stories">{Array.from({ length: g.preview.tasks + 1 }, (_, n) => choice(value.lateCount === n, String(n), () => set('lateCount', n)))}</div>
      </Panel>
      <Panel title={t('Which order will carry the lowest risk?')}>
        <div className="stories">{g.preview.orders.map((o: { key: string; label: string }) => choice(value.bestOrder === o.key, o.label, () => set('bestOrder', o.key)))}</div>
      </Panel>
      {g.preview.cheapestAsk && <Panel title={t('Which is cheaper in total money?')} lead={t('Optional. Cut scope on the late tasks, or pay for extra hours.')}>
        <div className="stories">{choice(value.cheapest === 'scope', t('Cut scope'), () => set('cheapest', 'scope'))}{choice(value.cheapest === 'pay', t('Pay for extra hours'), () => set('cheapest', 'pay'))}</div>
      </Panel>}
    </>);
  } else if (g.engine === 'estimate') {
    ready = !!value.date;
    body = (
      <Panel title={t('By which date could you safely commit?')}>
        <Field id="guessdate" label={t('Date')} help={t('The date you would give without worrying about missing it.')}>
          {(a) => <input className="input" {...a} type="date" min={g.preview.start} value={value.date ?? ''} onChange={(e) => set('date', e.target.value)} />}
        </Field>
        <DateChips onPick={(v) => set('date', v)} />
      </Panel>
    );
  } else {
    ready = value.winner !== undefined;
    body = (
      <Panel title={t('Which option do you think wins?')}>
        <div className="stories">{g.preview.options.map((name: string, i: number) => choice(value.winner === i, name, () => set('winner', i)))}</div>
      </Panel>
    );
  }
  return (
    <>
      <div data-tour="guess-controls">{body}</div>
      {error && <div className="banner bad" role="alert">{error}</div>}
      <div className="row" style={{ marginTop: 16 }}>
        <Button onClick={onGo} busy={busy} disabled={!ready}>{t('Save my guess and show the numbers')}</Button>
        <span data-tour="guess-skip"><Button variant="secondary" onClick={onSkip} busy={busy}>{t('Skip, show me the numbers')}</Button></span>
        <Button variant="quiet" onClick={onBack}>{t('Back to the form')}</Button>
      </div>
    </>
  );
}
