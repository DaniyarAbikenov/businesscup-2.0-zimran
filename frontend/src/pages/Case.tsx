import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useSession } from '../App';
import { Case, Option, Situation, api, fmtDate, usd } from '../api';
import { notify } from '../components/Toaster';
import { Badge, Button, Field, PageHeader, Panel, QuestionField, initialAnswers, useToast } from '../components/ui';

export default function CasePage() {
  const { id } = useParams();
  const { pack } = useSession();
  const [c, setC] = useState<Case | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { setC(null); api('GET', `/cases/${id}`).then((r) => setC(r.case)).catch((e) => setError(e.message)); }, [id]);
  if (error) return <><div className="banner bad" role="alert">{error}</div><Link to="/">Back to Home</Link></>;
  if (!c) return <p className="muted">Loading</p>;
  const sit = pack.situations.find((s) => s.id === c.situationId)!;
  return c.status === 'draft' ? <Draft c={c} sit={sit} onChange={setC} /> : <Decided c={c} sit={sit} onChange={setC} />;
}

const summary = (c: Case) => {
  const i = c.inputs;
  return `Requested by ${i.requestedBy}. Release ${fmtDate(i.releaseDate)}, ${i.teamSize} people, ${usd(i.dailyRate)} per person-day, ${usd(i.budgetRemaining)} budget left, ${i.changeEffortDays} person-days estimated, ${i.bufferDays} buffer days.`;
};

// ---------------- Step 2 and 3 ----------------
function Ledger({ c, sit, chosen, onPick }: { c: Case; sit: Situation; chosen: string | null; onPick: (k: string) => void }) {
  const opts = c.result.options;
  const cell = (o: Option, label: string, content: React.ReactNode, num = true) => (
    <td key={o.key} data-label={label} className={(num ? 'num ' : '') + (chosen === o.key ? 'sel' : '')}>{content}</td>
  );
  return (
    <table className="ledger">
      <caption className="visually-hidden">Comparison of your three options</caption>
      <thead>
        <tr>
          <th scope="col"><span className="visually-hidden">Measure</span></th>
          {opts.map((o) => (
            <th key={o.key} scope="col" className={chosen === o.key ? 'sel' : ''}>
              {sit.options[o.key].label}
              {c.result.lowestRiskKey === o.key && <span className="tag">Lowest risk on these numbers</span>}
              <div><Button className="pickbtn" variant={chosen === o.key ? 'primary' : 'secondary'} aria-pressed={chosen === o.key} onClick={() => onPick(o.key)} type="button">{chosen === o.key ? 'Selected' : 'Choose'}</Button></div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr><td>Release date</td>{opts.map((o) => cell(o, sit.options[o.key].label, <>{fmtDate(o.newReleaseDate)}{o.slipWorkdays > 0 && <div className="small muted">+{o.slipWorkdays} working days</div>}</>))}</tr>
        <tr><td>Extra cost now</td>{opts.map((o) => cell(o, sit.options[o.key].label, usd(o.extraCost)))}</tr>
        <tr><td>Cost later</td>{opts.map((o) => cell(o, sit.options[o.key].label, o.key === 'defer' ? usd(o.laterCost!) : '-'))}</tr>
        <tr><td>Budget left</td>{opts.map((o) => cell(o, sit.options[o.key].label, usd(o.budgetAfter)))}</tr>
        <tr><td>Risk</td>{opts.map((o) => cell(o, sit.options[o.key].label, <Badge level={o.riskLevel} />))}</tr>
        <tr><td>What to watch</td>{opts.map((o) => cell(o, sit.options[o.key].label, <ul className="risks">{o.risks.map((r, i) => <li key={i}>{r.text}</li>)}</ul>, false))}</tr>
      </tbody>
    </table>
  );
}

function Draft({ c, sit, onChange }: { c: Case; sit: Situation; onChange: (c: Case) => void }) {
  const [chosen, setChosen] = useState<string | null>(null);
  const [rationale, setRationale] = useState('');
  const [days, setDays] = useState('3');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [answers, setAnswers] = useState(() => initialAnswers(sit.questions, c.inputs));
  const [fields, setFields] = useState<Record<string, string>>({});
  const [recalcErr, setRecalcErr] = useState('');

  async function decide() {
    if (!chosen) return setError('Choose one of the three options first.');
    setBusy(true); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/decision`, { option: chosen, rationale, followupDays: Number(days) })).case); window.scrollTo(0, 0); notify('Decision saved. Your Change Request is ready.'); }
    catch (x: any) { setError(x.message); } finally { setBusy(false); }
  }
  async function recalc(e: FormEvent) {
    e.preventDefault(); setRecalcErr(''); setFields({}); setChosen(null);
    try { onChange((await api('PUT', `/cases/${c.id}/inputs`, { inputs: answers })).case); notify('Recalculated with your new numbers.'); }
    catch (x: any) { setRecalcErr(x.message); setFields(x.fields ?? {}); }
  }

  return (
    <>
      <PageHeader eyebrow="Step 2 of 3 · Compare" title={c.inputs.changeTitle} lead={summary(c)} />
      <Panel title="Your three options" lead={`${c.result.workdaysToRelease} working days to release. The change adds about ${c.result.addedWorkdays} working days of work. Every figure is calculated from your inputs. The risk label is a rule-of-thumb check, and the decision is yours.`}>
        <Ledger c={c} sit={sit} chosen={chosen} onPick={setChosen} />
        <details><summary>How was this calculated?</summary><p className="small muted">{c.result.assumptions}</p></details>
      </Panel>
      <Panel title="Decide">
        <p className="caption" style={{ marginBottom: 8 }}>Step 3 of 3</p>
        <Field id="rationale" label="Your reasoning" help="It goes into the document. What would change your mind?">{(a) => <textarea className="input" {...a} maxLength={600} value={rationale} onChange={(e) => setRationale(e.target.value)} />}</Field>
        <Field id="days" label="Ask me how it went">{(a) => (
          <select className="input" {...a} value={days} onChange={(e) => setDays(e.target.value)}>
            <option value="1">Tomorrow</option><option value="3">In 3 days</option><option value="7">In a week</option><option value="14">In 2 weeks</option>
          </select>)}
        </Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button onClick={decide} busy={busy}>Save decision and create Change Request</Button></div>
      </Panel>
      <Panel>
        <details>
          <summary style={{ marginTop: 0 }}>What if the numbers are different? Edit and recalculate</summary>
          <form onSubmit={recalc} noValidate>
            <div className="grid-2">{sit.questions.map((q) => <QuestionField key={q.id} q={q} value={answers[q.id]} error={fields[q.id]} onChange={(v) => setAnswers({ ...answers, [q.id]: v })} />)}</div>
            {recalcErr && <div className="field error" role="alert">{recalcErr}</div>}
            <div className="row" style={{ marginTop: 16 }}><Button type="submit" variant="secondary">Recalculate</Button></div>
          </form>
        </details>
      </Panel>
    </>
  );
}

// ---------------- After the decision ----------------
function Decided({ c, sit, onChange }: { c: Case; sit: Situation; onChange: (c: Case) => void }) {
  const { me } = useSession();
  const chosen = c.result.options.find((o) => o.key === c.chosenOption)!;
  const [doc, setDoc] = useState(c.document ?? '');
  const toast = useToast();
  const [hint, setHint] = useState(c.clientMessage ?? '');
  const [savedDoc, setSavedDoc] = useState(c.document ?? '');
  const [savedHint, setSavedHint] = useState(c.clientMessage ?? '');
  const [saving, setSaving] = useState('');
  const [hintErr, setHintErr] = useState('');
  const [hintBusy, setHintBusy] = useState(false);
  const d = c.debrief!;

  const copy = async () => {
    try { await navigator.clipboard.writeText(doc); toast.show('Change Request copied to clipboard'); } catch { toast.show('Select the text and copy it manually'); }
  };
  const download = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([doc], { type: 'text/markdown' }));
    a.download = `change-request-${c.id}.md`;
    document.body.append(a); a.click(); a.remove();
    notify('Downloaded change-request-' + c.id + '.md');
  };
  const getHint = async () => {
    setHintBusy(true); setHintErr('');
    try { const t = (await api('POST', `/cases/${c.id}/hint`, {})).text; setHint(t); setSavedHint(t); notify('Draft saved with this case.'); }
    catch (x: any) { setHintErr(x.message); } finally { setHintBusy(false); }
  };
  const saveDoc = async (kind: 'change_request' | 'client_message', body: string) => {
    setSaving(kind); setHintErr('');
    try {
      const next: Case = (await api('PUT', `/cases/${c.id}/documents/${kind}`, { body })).case;
      onChange(next);
      if (kind === 'change_request') setSavedDoc(body); else setSavedHint(body);
      notify(kind === 'change_request' ? 'Change Request saved.' : 'Message saved.');
    } catch (x: any) { notify(x.message, 'bad'); } finally { setSaving(''); }
  };

  return (
    <>
      <PageHeader eyebrow="Decision saved" title={c.inputs.changeTitle} />
      <div className="banner ok" role="status">
        {sit.options[c.chosenOption!].label}.{' '}
        {chosen.newReleaseDate !== c.inputs.releaseDate && <>New release date {fmtDate(chosen.newReleaseDate)}. </>}Extra cost {usd(chosen.extraCost)}.
      </div>
      <Panel title="Your Change Request" lead="Edit it if you like and save. Your changes are kept with this case. Check the facts before you send it.">
        <textarea className="input doc" aria-label="Change Request document" spellCheck={false} wrap="off" value={doc} onChange={(e) => setDoc(e.target.value)} />
        <div className="row" style={{ marginTop: 16 }}>
          <Button onClick={() => saveDoc('change_request', doc)} busy={saving === 'change_request'} disabled={doc === savedDoc || !doc.trim()}>Save changes</Button>
          <span className="small muted" role="status">
            {doc !== savedDoc ? 'Unsaved changes' : c.documentUpdatedAt ? `Saved ${new Date(c.documentUpdatedAt).toLocaleString()}${(c.documentRevisions ?? 1) > 1 ? ` · ${c.documentRevisions} versions` : ''}` : 'Saved'}
          </span>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <Button variant="secondary" onClick={copy}>Copy</Button>
          <Button variant="secondary" onClick={download}>Download .md</Button>
          {me.llmEnabled && <Button variant="secondary" onClick={getHint} busy={hintBusy}>Draft a message to the client (AI)</Button>}
        </div>
        {hintErr && <div className="field error" role="alert">{hintErr}</div>}
        {(hint || savedHint) && (
          <div className="field">
            <div className="label">Message to the client. Edit before sending.</div>
            <textarea className="input" style={{ minHeight: 160 }} aria-label="Message to the client" value={hint} onChange={(e) => setHint(e.target.value)} />
            <div className="row" style={{ marginTop: 8 }}>
              <Button variant="secondary" onClick={() => saveDoc('client_message', hint)} busy={saving === 'client_message'} disabled={hint === savedHint || !hint.trim()}>Save message</Button>
              <span className="small muted">{hint !== savedHint ? 'Unsaved changes' : 'Saved'}</span>
            </div>
          </div>
        )}
      </Panel>
      <Panel title="Debrief">
        <ul className="plain">{d.points.map((p, i) => <li key={i}>{p}</li>)}</ul>
        <h3 style={{ marginTop: 24 }}>Next steps for this option</h3>
        <ol className="plain">{d.nextSteps.map((s, i) => <li key={i}>{s}</li>)}</ol>
        <h3 style={{ marginTop: 24 }}>Common mistakes to avoid</h3>
        <ul className="plain">{d.pitfalls.map((s, i) => <li key={i}>{s}</li>)}</ul>
      </Panel>
      <Reflection c={c} sit={sit} onChange={onChange} />
      <Followup c={c} onChange={onChange} />
      {toast.node}
    </>
  );
}

function Reflection({ c, sit, onChange }: { c: Case; sit: Situation; onChange: (c: Case) => void }) {
  const [vals, setVals] = useState<Record<string, string>>({});
  const [conf, setConf] = useState(String(Math.min(5, c.confidenceBefore + 1)));
  const [error, setError] = useState('');
  if (c.reflection) {
    return (
      <Panel title="Your reflection">
        <p>Confidence: {c.confidenceBefore} before, {c.reflection.confidenceAfter} after.</p>
        {c.reflection.learned && <p className="stack"><b>Learned:</b> {c.reflection.learned}</p>}
        {c.reflection.different && <p className="stack"><b>Next time:</b> {c.reflection.different}</p>}
      </Panel>
    );
  }
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/reflection`, { ...vals, confidenceAfter: Number(conf) })).case); notify('Reflection saved to your journal.'); } catch (x: any) { setError(x.message); }
  };
  return (
    <Panel title="Reflect" lead="One minute. This is what turns a decision into learning.">
      <form onSubmit={submit}>
        {sit.reflectionPrompts.map((p) => (
          <Field key={p.id} id={'r_' + p.id} label={p.label}>{(a) => <textarea className="input" {...a} maxLength={600} value={vals[p.id] ?? ''} onChange={(e) => setVals({ ...vals, [p.id]: e.target.value })} />}</Field>
        ))}
        <Field id="rc" label={`How confident do you feel now? You said ${c.confidenceBefore} before.`}>
          {(a) => <select className="input" {...a} value={conf} onChange={(e) => setConf(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>}
        </Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button type="submit">Save reflection</Button></div>
      </form>
    </Panel>
  );
}

const OUTCOMES: Record<string, string> = { worked: 'It worked', partly: 'Partly worked', not_yet: 'Not resolved yet', not_applied: 'I did not use it at work' };

function Followup({ c, onChange }: { c: Case; onChange: (c: Case) => void }) {
  const [outcome, setOutcome] = useState('worked');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const due = (c.followupDue ?? '') <= new Date().toISOString().slice(0, 10);
  const submit = useCallback(async (e: FormEvent) => {
    e.preventDefault(); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/followup`, { outcome, notes })).case); notify('Follow-up saved to your journal.'); } catch (x: any) { setError(x.message); }
  }, [c.id, outcome, notes, onChange]);
  if (c.followup) {
    return (
      <Panel title="Follow-up">
        <p>As you reported: {OUTCOMES[c.followup.outcome]}.</p>
        {c.followup.notes && <p className="stack">{c.followup.notes}</p>}
        <p className="small muted stack">Self-reported. RoleShift cannot verify what happened at work.</p>
      </Panel>
    );
  }
  return (
    <Panel title="What happened?" lead={due ? 'It is time to check in.' : `We will remind you on ${fmtDate(c.followupDue!)}. You can also answer now.`}>
      <form onSubmit={submit}>
        <Field id="fo" label="Outcome">{(a) => <select className="input" {...a} value={outcome} onChange={(e) => setOutcome(e.target.value)}>{Object.entries(OUTCOMES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}</Field>
        <Field id="fn" label="Notes (optional)">{(a) => <textarea className="input" {...a} maxLength={800} placeholder="What happened? What would you change?" value={notes} onChange={(e) => setNotes(e.target.value)} />}</Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button type="submit">Save follow-up</Button></div>
      </form>
    </Panel>
  );
}
