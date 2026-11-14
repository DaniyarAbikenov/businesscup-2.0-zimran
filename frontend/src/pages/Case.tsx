import { locale, t, tn } from '../i18n';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useSession } from '../App';
import { Case, Option, Situation, api, fmtDate, usd } from '../api';
import { notify } from '../components/Toaster';
import { Badge, Button, Field, PageHeader, Panel, QuestionGroups, Stepper, Why, initialAnswers, useToast } from '../components/ui';

export default function CasePage() {
  const { id } = useParams();
  const { pack } = useSession();
  const [c, setC] = useState<Case | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { setC(null); api('GET', `/cases/${id}`).then((r) => setC(r.case)).catch((e) => setError(e.message)); }, [id]);
  if (error) return <><div className="banner bad" role="alert">{error}</div><Link to="/">{t('Back to Home')}</Link></>;
  if (!c) return <p className="muted">{t('Loading')}</p>;
  const sit = pack.situations.find((s) => s.id === c.situationId)!;
  return c.status === 'draft' ? <Draft c={c} sit={sit} onChange={setC} /> : <Decided c={c} sit={sit} onChange={setC} />;
}

/** The answer first: one sentence from the server's numbers, before the details. */
/** "Why this label": the points behind a risk label, the thresholds, and what would change it. Everything comes from the server's numbers. */
function WhyLabel({ o }: { o: Option }) {
  const next = o.riskLevel === 'high' ? 3 : o.riskLevel === 'medium' ? 1 : null;
  const biggest = [...o.risks].filter((r) => r.severity > 0).sort((a, b) => b.severity - a.severity)[0];
  return (
    <details className="why">
      <summary>{t('Why this label')}</summary>
      <ul className="risks">{o.risks.map((r, i) => <li key={i}><b>{r.severity > 0 ? '+' + r.severity : '0'}</b> {r.text}</li>)}</ul>
      <p className="small muted">{t('Total {n} points. 0 to 1 is low, 2 to 3 is medium, 4 or more is high.', { n: o.riskScore })}
        {next !== null && biggest ? ' ' + t('To get one level lower, remove at least {n} points, for example the biggest one: {text}', { n: o.riskScore - next, text: biggest.text }) : ''}
        {next === null ? ' ' + t('It is already the lowest label; it becomes medium with {n} more points.', { n: 2 - o.riskScore }) : ''}</p>
    </details>
  );
}

function bestLine(c: Case, sit: Situation): string {
  const o = c.result.options.find((x) => x.key === c.result.lowestRiskKey)!;
  const label = sit.options[o.key].label;
  const risk = t('{level} risk', { level: t(o.riskLevel) });
  if (sit.engine === 'decision') return t('Best by the numbers: {pick} (score {score} out of 100). {note}', { pick: o.pick, score: o.score, note: (c.result as any).notes?.[0] ?? '' });
  if (sit.engine === 'estimate') return t('Best by the numbers: "{label}" ({when}, about {p}% chance to make it, {risk}).', { label, when: o.dateFrom ? t('{from} to {to}', { from: fmtDate(o.dateFrom), to: fmtDate(o.date!) }) : fmtDate(o.date!), p: o.probability, risk });
  if (sit.engine === 'priorities') return t('Best by the numbers: "{label}" {what} ({risk}).', { label, what: o.lateCount ? tn(o.lateCount, 'still leaves {n} task late', 'still leaves {n} tasks late') : t('leaves nothing late'), risk });
  return t('Best by the numbers: "{label}" has the lowest risk ({risk}). New release date {date}, extra cost {cost}.', { label, risk, date: fmtDate(o.newReleaseDate), cost: usd(o.extraCost) });
}
const HOW_READ: Record<string, string> = {
  change_request: t('Each column is one thing you could answer. Read down: date, cost, then the risks to watch. Green-to-red labels are a rule-of-thumb check.'),
  priorities: t('Each column is a different order of doing the work. Read down to see when each task finishes and what ends up late.'),
  estimate: t('Each column is a date you could promise. The percentage is the chance you make it, based on your three estimates and your real free time.'),
  decision: t('The top table ranks your options by your own weights and scores. The columns below are four ways to pick; if they agree, the choice is solid.'),
};

const summary = (c: Case, sit: Situation) => {
  const i = c.inputs;
  if (sit.engine !== 'change_request') return c.result.headline ?? sit.summary;
  return t('Requested by {who}. Release {date}, {people} people, {rate} per person-day, {budget} budget left, {effort} person-days estimated, {buffer} buffer days.', { who: i.requestedBy, date: fmtDate(i.releaseDate), people: i.teamSize, rate: usd(i.dailyRate), budget: usd(i.budgetRemaining), effort: i.changeEffortDays, buffer: i.bufferDays });
};

// ---------------- Step 2 and 3 ----------------
function Ledger({ c, sit, chosen, onPick }: { c: Case; sit: Situation; chosen: string | null; onPick: (k: string) => void }) {
  const opts = c.result.options;
  const cell = (o: Option, label: string, content: React.ReactNode, num = true) => (
    <td key={o.key} data-label={label} className={(num ? 'num ' : '') + (chosen === o.key ? 'sel' : '')}>{content}</td>
  );
  return (
    <table className="ledger">
      <caption className="visually-hidden">{t('Comparison of your three options')}</caption>
      <thead>
        <tr>
          <th scope="col"><span className="visually-hidden">{t('Measure')}</span></th>
          {opts.map((o) => (
            <th key={o.key} scope="col" className={chosen === o.key ? 'sel' : ''}>
              {sit.options[o.key].label}
              {c.result.lowestRiskKey === o.key && <span className="tag">{t('Lowest risk on these numbers')}</span>}
              <div><Button className="pickbtn" variant={chosen === o.key ? 'primary' : 'secondary'} aria-pressed={chosen === o.key} onClick={() => onPick(o.key)} type="button">{chosen === o.key ? t('Selected') : t('Choose')}</Button></div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr><td>{t('Release date')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, <>{fmtDate(o.newReleaseDate)}{o.slipWorkdays > 0 && <div className="small muted">{t('+{n} working days', { n: o.slipWorkdays })}</div>}</>))}</tr>
        <tr><td>{t('Extra cost now')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, usd(o.extraCost)))}</tr>
        <tr><td>{t('Cost later')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, o.key === 'defer' ? usd(o.laterCost!) : '-'))}</tr>
        <tr><td>{t('Budget left')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, usd(o.budgetAfter)))}</tr>
        <tr><td>{t('Risk')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, <Badge level={o.riskLevel} />))}</tr>
        <tr><td>{t('What to watch')}</td>{opts.map((o) => cell(o, sit.options[o.key].label, <><ul className="risks">{o.risks.map((r, i) => <li key={i}>{r.text}</li>)}</ul><WhyLabel o={o} /></>, false))}</tr>
      </tbody>
    </table>
  );
}

function DecisionRanking({ c }: { c: Case }) {
  const r = c.result as any;
  return (
    <div className="decision-box">
      <table className="ledger">
        <caption className="visually-hidden">{t('Options ranked by weighted score')}</caption>
        <thead><tr><th scope="col">{t('Option')}</th><th scope="col">{t('Score (0 to 100)')}</th>{r.criteria.map((k: any) => <th key={k.name} scope="col">{k.name} <span className="small muted">{t('weight {n}', { n: k.weight })}</span></th>)}</tr></thead>
        <tbody>
          {r.ranking.map((o: any) => (
            <tr key={o.index}>
              <td data-label="Option"><b>{o.rank}. {o.name}</b>{o.marginToNext != null && <div className="small muted">{t('{n} ahead of the next', { n: o.marginToNext })}</div>}</td>
              <td data-label="Score" className="num"><div className="bar" role="img" aria-label={t('{score} out of 100', { score: o.score })}><span style={{ width: `${o.score}%` }} /></div>{o.score}</td>
              {o.scores.map((s: any) => <td key={s.criterion} data-label={s.criterion} className={'num' + (s.score <= 2 ? ' late' : '')}>{s.score}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="banner ok" role="note" style={{ marginTop: 16 }}>
        <strong>{t('What would change the winner')}</strong>
        <ul className="plain">{r.notes.map((n: string, i: number) => <li key={i}>{n}</li>)}</ul>
      </div>
    </div>
  );
}

function DecisionLedger({ c, sit, chosen, onPick }: { c: Case; sit: Situation; chosen: string | null; onPick: (k: string) => void }) {
  const opts = c.result.options;
  const label = (k: string) => sit.options[k].label;
  const cell = (o: Option, content: React.ReactNode, num = true) => (
    <td key={o.key} data-label={label(o.key)} className={(num ? 'num ' : '') + (chosen === o.key ? 'sel' : '')}>{content}</td>
  );
  return (
    <table className="ledger">
      <caption className="visually-hidden">{t('Comparison of {n} ways to pick', { n: opts.length })}</caption>
      <thead>
        <tr>
          <th scope="col"><span className="visually-hidden">{t('Measure')}</span></th>
          {opts.map((o) => (
            <th key={o.key} scope="col" className={chosen === o.key ? 'sel' : ''}>
              {label(o.key)}
              {c.result.lowestRiskKey === o.key && <span className="tag">{t('Lowest risk on these numbers')}</span>}
              {o.sameAs && o.sameAs.length > 0 && <span className="tag muted-tag">{t('Same pick as {list}', { list: o.sameAs.map(label).join(', ').toLowerCase() })}</span>}
              <div><Button className="pickbtn" variant={chosen === o.key ? 'primary' : 'secondary'} aria-pressed={chosen === o.key} onClick={() => onPick(o.key)} type="button">{chosen === o.key ? t('Selected') : t('Choose')}</Button></div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr><td>{t('It picks')}</td>{opts.map((o) => cell(o, <b>{o.pick}</b>, false))}</tr>
        <tr><td>{t('Its score')}</td>{opts.map((o) => cell(o, <>{o.score}<div className="small muted">{t('rank {n}', { n: o.rank })}</div></>))}</tr>
        <tr><td>{t('Risk')}</td>{opts.map((o) => cell(o, <Badge level={o.riskLevel} />))}</tr>
        <tr><td>{t('What to watch')}</td>{opts.map((o) => cell(o, <><ul className="risks">{o.risks.map((r, i) => <li key={i}>{r.text}</li>)}</ul><WhyLabel o={o} /></>, false))}</tr>
      </tbody>
    </table>
  );
}

function EstimateLedger({ c, sit, chosen, onPick }: { c: Case; sit: Situation; chosen: string | null; onPick: (k: string) => void }) {
  const opts = c.result.options;
  const label = (k: string) => sit.options[k].label;
  const asked: string | null = (c.result as any).askedDeadline;
  const cell = (o: Option, content: React.ReactNode, num = true) => (
    <td key={o.key} data-label={label(o.key)} className={(num ? 'num ' : '') + (chosen === o.key ? 'sel' : '')}>{content}</td>
  );
  return (
    <table className="ledger">
      <caption className="visually-hidden">{t('Comparison of {n} dates you could promise', { n: opts.length })}</caption>
      <thead>
        <tr>
          <th scope="col"><span className="visually-hidden">{t('Measure')}</span></th>
          {opts.map((o) => (
            <th key={o.key} scope="col" className={chosen === o.key ? 'sel' : ''}>
              {label(o.key)}
              {c.result.lowestRiskKey === o.key && <span className="tag">{t('Lowest risk on these numbers')}</span>}
              <div><Button className="pickbtn" variant={chosen === o.key ? 'primary' : 'secondary'} aria-pressed={chosen === o.key} onClick={() => onPick(o.key)} type="button">{chosen === o.key ? t('Selected') : t('Choose')}</Button></div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr><td>{t('You would say')}</td>{opts.map((o) => cell(o, o.dateFrom ? <>{fmtDate(o.dateFrom)} to {fmtDate(o.date!)}<div className="small muted">{t('re-check {date}', { date: fmtDate(o.recheckDate!) })}</div></> : fmtDate(o.date!)))}</tr>
        <tr><td>{t('Chance to make it')}</td>{opts.map((o) => cell(o, `${o.probability}%`))}</tr>
        <tr><td>{t('Working days')}</td>{opts.map((o) => cell(o, o.workdays))}</tr>
        <tr><td>{asked ? t('Against {asked}', { asked: fmtDate(asked) }) : t('Their deadline')}</td>{opts.map((o) => cell(o, asked ? <span className={o.lateDays ? 'late' : 'muted'}>{o.lateDays ? tn(o.lateDays, '{n} working day after', '{n} working days after') : t('in time')}</span> : <span className="muted">{t('none given')}</span>))}</tr>
        <tr><td>{t('Risk')}</td>{opts.map((o) => cell(o, <Badge level={o.riskLevel} />))}</tr>
        <tr><td>{t('What to watch')}</td>{opts.map((o) => cell(o, <><ul className="risks">{o.risks.map((r, i) => <li key={i}>{r.text}</li>)}</ul><WhyLabel o={o} /></>, false))}</tr>
      </tbody>
    </table>
  );
}

const lateText = (d: number) => (d === 0 ? t('on time') : tn(d, '{n} working day late', '{n} working days late'));

function PriorityLedger({ c, sit, chosen, onPick }: { c: Case; sit: Situation; chosen: string | null; onPick: (k: string) => void }) {
  const opts = c.result.options;
  const tasks: { name: string; deadline: string }[] = c.inputs.tasks;
  const label = (k: string) => sit.options[k].label;
  const cell = (o: Option, content: React.ReactNode, num = true) => (
    <td key={o.key} data-label={label(o.key)} className={(num ? 'num ' : '') + (chosen === o.key ? 'sel' : '')}>{content}</td>
  );
  return (
    <table className="ledger">
      <caption className="visually-hidden">{t('Comparison of {n} orders of work', { n: opts.length })}</caption>
      <thead>
        <tr>
          <th scope="col"><span className="visually-hidden">{t('Measure')}</span></th>
          {opts.map((o) => (
            <th key={o.key} scope="col" className={chosen === o.key ? 'sel' : ''}>
              {label(o.key)}
              {c.result.lowestRiskKey === o.key && <span className="tag">{t('Least damage on these numbers')}</span>}
              {o.sameAs && o.sameAs.length > 0 && <span className="tag muted-tag">{t('Same order as {list}', { list: o.sameAs.map(label).join(', ').toLowerCase() })}</span>}
              <div><Button className="pickbtn" variant={chosen === o.key ? 'primary' : 'secondary'} aria-pressed={chosen === o.key} onClick={() => onPick(o.key)} type="button">{chosen === o.key ? t('Selected') : t('Choose')}</Button></div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr><td>{t('Order of work')}</td>{opts.map((o) => cell(o, <ol className="order">{o.schedule!.map((s) => <li key={s.index}>{s.name}</li>)}</ol>, false))}</tr>
        {tasks.map((tk, ix) => (
          <tr key={ix}>
            <td>{tk.name}<div className="small muted">{t('due {date}', { date: fmtDate(tk.deadline) })}</div></td>
            {opts.map((o) => {
              const s = o.schedule!.find((x) => x.index === ix)!;
              return cell(o, <>{fmtDate(s.finish)}<div className={'small ' + (s.lateDays ? 'late' : 'muted')}>{lateText(s.lateDays)}</div></>);
            })}
          </tr>
        ))}
        <tr><td>{t('Late tasks')}</td>{opts.map((o) => cell(o, o.lateCount ? t('{lateCount}, {totalLateDays} days in total', { lateCount: o.lateCount, totalLateDays: o.totalLateDays }) : 'none'))}</tr>
        <tr><td>{t('Risk')}</td>{opts.map((o) => cell(o, <Badge level={o.riskLevel} />))}</tr>
        <tr><td>{t('What to watch')}</td>{opts.map((o) => cell(o, <><ul className="risks">{o.risks.map((r, i) => <li key={i}>{r.text}</li>)}</ul><WhyLabel o={o} /></>, false))}</tr>
      </tbody>
    </table>
  );
}

function Challenge({ c }: { c: Case }) {
  const [res, setRes] = useState<{ tests: { what: string; holds: boolean; text: string }[]; allHold: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); try { setRes(await api('GET', `/cases/${c.id}/challenge`)); } catch (x: any) { notify(x.message, 'bad'); } finally { setBusy(false); } };
  return (
    <div className="challenge">
      <Button variant="secondary" type="button" onClick={run} busy={busy}>{t('Challenge my numbers')}</Button>
      <span className="small muted"> {t('Recalculates with worse numbers to see if the conclusion holds.')}</span>
      {res && (
        <div className={'banner ' + (res.allHold ? 'ok' : '')} role="status" style={{ marginTop: 12 }}>
          <strong>{res.allHold ? t('The conclusion holds in both tests.') : t('The conclusion is fragile in at least one test.')}</strong>
          <ul className="plain">{res.tests.map((x, i) => <li key={i}>{x.holds ? '✓' : '✗'} {x.text}</li>)}</ul>
        </div>
      )}
    </div>
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
    if (!chosen) return setError(t('Choose one of the options first.'));
    setBusy(true); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/decision`, { option: chosen, rationale, followupDays: Number(days) })).case); window.scrollTo(0, 0); notify(t('Decision saved. Your Change Request is ready.')); }
    catch (x: any) { setError(x.message); } finally { setBusy(false); }
  }
  async function recalc(e: FormEvent) {
    e.preventDefault(); setRecalcErr(''); setFields({}); setChosen(null);
    try { onChange((await api('PUT', `/cases/${c.id}/inputs`, { inputs: answers })).case); notify(t('Recalculated with your new numbers.')); }
    catch (x: any) { setRecalcErr(x.message); setFields(x.fields ?? {}); }
  }

  return (
    <>
      <Stepper current={2} />
      <PageHeader eyebrow={t('Compare')} title={c.title} lead={summary(c, sit)} />
      <div className="banner ok" role="note"><p className="bestline">{bestLine(c, sit)}</p><p className="howread" style={{ margin: 0 }}>{HOW_READ[sit.engine]} {t('The decision is yours.')}</p>
        <p className="howread" style={{ margin: '8px 0 0' }}>{t('This is a calculation on your numbers, not a forecast. Real outcomes depend on people and circumstances not listed here.')}</p></div>
      <Panel title={t('Your {n} options', { n: c.result.options.length })} lead={sit.engine === 'decision'
        ? t('Your scores ranked, then four ways to pick. All numbers follow from your own weights and scores. The risk label is a rule-of-thumb check, and the decision is yours.')
        : sit.engine === 'estimate'
        ? t('Each column is something you could say. Dates and chances are calculated from your three-point estimate and your real free hours. The risk label is a rule-of-thumb check, and the decision is yours.')
        : sit.engine === 'priorities'
        ? t('Each column is a different order of work. Every date is calculated from your hours and estimates. The risk label is a rule-of-thumb check, and the decision is yours.')
        : t('{workdaysToRelease} working days to release. The change adds about {addedWorkdays} working days of work. Every figure is calculated from your inputs. The risk label is a rule-of-thumb check, and the decision is yours.', { workdaysToRelease: c.result.workdaysToRelease, addedWorkdays: c.result.addedWorkdays })}>
        {sit.engine === 'decision' ? <><DecisionRanking c={c} /><DecisionLedger c={c} sit={sit} chosen={chosen} onPick={setChosen} /></>
          : sit.engine === 'estimate' ? <EstimateLedger c={c} sit={sit} chosen={chosen} onPick={setChosen} />
          : sit.engine === 'priorities' ? <PriorityLedger c={c} sit={sit} chosen={chosen} onPick={setChosen} /> : <Ledger c={c} sit={sit} chosen={chosen} onPick={setChosen} />}
        <Challenge c={c} />
        <details><summary>{t('How was this calculated?')}</summary><p className="small muted">{c.result.assumptions}</p></details>
      </Panel>
      <Panel title={t('Decide')}>
        <p className="caption" style={{ marginBottom: 8 }}>{t('Decide: choose one option above and say why.')}</p>
        <Field id="rationale" label={t('Your reasoning')} help={t('It goes into the document. What would change your mind?')}>{(a) => <textarea className="input" {...a} maxLength={600} value={rationale} onChange={(e) => setRationale(e.target.value)} />}</Field>
        <Field id="days" label={t('Ask me how it went')}>{(a) => (
          <select className="input" {...a} value={days} onChange={(e) => setDays(e.target.value)}>
            <option value="1">{t('Tomorrow')}</option><option value="3">{t('In 3 days')}</option><option value="7">{t('In a week')}</option><option value="14">{t('In 2 weeks')}</option>
          </select>)}
        </Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button onClick={decide} busy={busy}>{t('Save decision and create {name}', { name: sit.documentName ?? t('the document') })}</Button></div>
      </Panel>
      <Panel>
        <details>
          <summary style={{ marginTop: 0 }}>{t('What if the numbers are different? Edit and recalculate')}</summary>
          <form onSubmit={recalc} noValidate>
            <QuestionGroups sit={sit} answers={answers} fields={fields} onChange={setAnswers} />
            {recalcErr && <div className="field error" role="alert">{recalcErr}</div>}
            <div className="row" style={{ marginTop: 16 }}><Button type="submit" variant="secondary">{t('Recalculate')}</Button></div>
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
    try { await navigator.clipboard.writeText(doc); toast.show(t('{Document} copied to clipboard', { Document: sit.documentName ?? t('Document') })); api('POST', `/cases/${c.id}/export`, { how: 'copy' }).catch(() => {}); } catch { toast.show(t('Select the text and copy it manually')); }
  };
  const download = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([doc], { type: 'text/markdown' }));
    a.download = `${(sit.documentName ?? 'document').toLowerCase().replace(/\s+/g, '-')}-${c.id}.md`;
    document.body.append(a); a.click(); a.remove();
    notify('Downloaded ' + a.download);
    api('POST', `/cases/${c.id}/export`, { how: 'download' }).catch(() => {});
  };
  const getHint = async () => {
    setHintBusy(true); setHintErr('');
    try { const t = (await api('POST', `/cases/${c.id}/hint`, {})).text; setHint(t); setSavedHint(t); notify(t('Draft saved with this case.')); }
    catch (x: any) { setHintErr(x.message); } finally { setHintBusy(false); }
  };
  const saveDoc = async (kind: 'change_request' | 'client_message', body: string) => {
    setSaving(kind); setHintErr('');
    try {
      const next: Case = (await api('PUT', `/cases/${c.id}/documents/${kind}`, { body })).case;
      onChange(next);
      if (kind === 'change_request') setSavedDoc(body); else setSavedHint(body);
      notify(kind === 'change_request' ? `${sit.documentName ?? t('Document')} saved.` : t('Message saved.'));
    } catch (x: any) { notify(x.message, 'bad'); } finally { setSaving(''); }
  };

  return (
    <>
      <Stepper current={4} />
      <PageHeader eyebrow={t('Decision saved. Next: use your message, then come back to record how it went.')} title={c.title} />
      <div className="banner ok" role="status">
        {sit.options[c.chosenOption!].label}.{' '}
        {sit.engine === 'decision'
          ? <>{chosen.pick} (score {chosen.score} out of 100, rank {chosen.rank}).</>
          : sit.engine === 'estimate'
          ? <>{chosen.dateFrom ? `${fmtDate(chosen.dateFrom)} to ${fmtDate(chosen.date!)}` : fmtDate(chosen.date!)}, about {chosen.probability}% chance to make it.</>
          : sit.engine === 'priorities'
          ? <>{chosen.lateCount ? t('{tasks} late, {days} working days in total.', { tasks: tn(chosen.lateCount, '{n} task', '{n} tasks'), days: chosen.totalLateDays }) : t('Every task on time.')}</>
          : <>{chosen.newReleaseDate !== c.inputs.releaseDate && <>New release date {fmtDate(chosen.newReleaseDate)}. </>}Extra cost {usd(chosen.extraCost)}.</>}
      </div>
      <Panel title={t('Your {document}', { document: sit.documentName ?? 'document' })} lead={t('Edit it if you like and save. Your changes are kept with this case. Check the facts before you send it.')}>
        <textarea className="input doc" aria-label={t('Change Request document')} spellCheck={false} wrap="off" value={doc} onChange={(e) => setDoc(e.target.value)} />
        <div className="row" style={{ marginTop: 16 }}>
          <Button onClick={() => saveDoc('change_request', doc)} busy={saving === 'change_request'} disabled={doc === savedDoc || !doc.trim()}>{t('Save changes')}</Button>
          <span className="small muted" role="status">
            {doc !== savedDoc ? t('Unsaved changes') : c.documentUpdatedAt ? t('Saved {when}{versions}', { when: new Date(c.documentUpdatedAt).toLocaleString(locale()), versions: (c.documentRevisions ?? 1) > 1 ? ' · ' + t('{n} versions', { n: c.documentRevisions }) : '' }) : t('Saved')}
          </span>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <Button variant="secondary" onClick={copy}>{t('Copy')}</Button>
          <Button variant="secondary" onClick={download}>{t('Download .md')}</Button>
          {me.llmEnabled && sit.engine === 'change_request' && <Button variant="secondary" onClick={getHint} busy={hintBusy}>{t('Draft a message to the client (AI)')}</Button>}
        </div>
        {hintErr && <div className="field error" role="alert">{hintErr}</div>}
        {(hint || savedHint) && (
          <div className="field">
            <div className="label">{t('Message to the client. Edit before sending.')}</div>
            <textarea className="input" style={{ minHeight: 160 }} aria-label={t('Message to the client')} value={hint} onChange={(e) => setHint(e.target.value)} />
            <div className="row" style={{ marginTop: 8 }}>
              <Button variant="secondary" onClick={() => saveDoc('client_message', hint)} busy={saving === 'client_message'} disabled={hint === savedHint || !hint.trim()}>{t('Save message')}</Button>
              <span className="small muted">{hint !== savedHint ? t('Unsaved changes') : t('Saved')}</span>
            </div>
          </div>
        )}
      </Panel>
      <Panel title={t('Debrief')}>
        <ul className="plain">{d.points.map((p, i) => <li key={i}>{p}</li>)}</ul>
        <h3 style={{ marginTop: 24 }}>{t('Next steps for this option')}</h3>
        <ol className="plain">{d.nextSteps.map((s, i) => <li key={i}>{s}</li>)}</ol>
        <h3 style={{ marginTop: 24 }}>{t('Common mistakes to avoid')}</h3>
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
      <Panel title={t('Your reflection')}>
        <p>{t('Confidence: {before} before, {after} after.', { before: c.confidenceBefore, after: c.reflection.confidenceAfter })}</p>
        {c.reflection.learned && <p className="stack"><b>{t('Learned:')}</b> {c.reflection.learned}</p>}
        {c.reflection.different && <p className="stack"><b>{t('Next time:')}</b> {c.reflection.different}</p>}
      </Panel>
    );
  }
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/reflection`, { ...vals, confidenceAfter: Number(conf) })).case); notify(t('Reflection saved to your journal.')); } catch (x: any) { setError(x.message); }
  };
  return (
    <Panel title={t('Reflect')} lead={t('One minute. This is what turns a decision into learning.')}>
      <form onSubmit={submit}>
        {sit.reflectionPrompts.map((p) => (
          <Field key={p.id} id={'r_' + p.id} label={p.label}>{(a) => <textarea className="input" {...a} maxLength={600} value={vals[p.id] ?? ''} onChange={(e) => setVals({ ...vals, [p.id]: e.target.value })} />}</Field>
        ))}
        <Field id="rc" label={t('How confident do you feel now? You said {confidenceBefore} before.', { confidenceBefore: c.confidenceBefore })}>
          {(a) => <select className="input" {...a} value={conf} onChange={(e) => setConf(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>}
        </Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button type="submit">{t('Save reflection')}</Button></div>
      </form>
    </Panel>
  );
}

const OUTCOMES: Record<string, string> = { worked: t('It worked'), partly: t('Partly worked'), not_yet: t('Not resolved yet'), not_applied: t('I did not use it at work') };

function Followup({ c, onChange }: { c: Case; onChange: (c: Case) => void }) {
  const [outcome, setOutcome] = useState('worked');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const due = (c.followupDue ?? '') <= new Date().toISOString().slice(0, 10);
  const submit = useCallback(async (e: FormEvent) => {
    e.preventDefault(); setError('');
    try { onChange((await api('POST', `/cases/${c.id}/followup`, { outcome, notes })).case); notify(t('Follow-up saved to your journal.')); } catch (x: any) { setError(x.message); }
  }, [c.id, outcome, notes, onChange]);
  if (c.followup) {
    return (
      <Panel title={t('Follow-up')}>
        <p>{t('As you reported: {outcome}.', { outcome: OUTCOMES[c.followup.outcome] })}</p>
        {c.followup.notes && <p className="stack">{c.followup.notes}</p>}
        <p className="small muted stack">{t('Self-reported. RoleShift cannot verify what happened at work.')}</p>
      </Panel>
    );
  }
  return (
    <Panel title={t('What happened?')} lead={due ? t('It is time to check in.') : t('We will remind you on {followupDue}. You can also answer now.', { followupDue: fmtDate(c.followupDue!) })}>
      <form onSubmit={submit}>
        <Field id="fo" label={t('Outcome')}>{(a) => <select className="input" {...a} value={outcome} onChange={(e) => setOutcome(e.target.value)}>{Object.entries(OUTCOMES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}</Field>
        <Field id="fn" label={t('Notes (optional)')}>{(a) => <textarea className="input" {...a} maxLength={800} placeholder={t('What happened? What would you change?')} value={notes} onChange={(e) => setNotes(e.target.value)} />}</Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><Button type="submit">{t('Save follow-up')}</Button></div>
      </form>
    </Panel>
  );
}
