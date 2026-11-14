import { FormEvent, useEffect, useMemo, useState } from 'react';
import { t } from '../i18n';
import { Question as Q, fmtDate } from '../api';
import { Button, Field, Panel, QuestionField, QuestionGroups } from './ui';

interface Step { title: string; groups: string[]; detailNote?: string }
interface Sit { questions: Q[]; groups?: { id: string; title: string; columns?: number; collapsed?: boolean }[]; steps?: Step[] }

/** The form as a few named steps plus a review. Steps come from the scenario pack (`steps`); a scenario without them gets one step per group. */
export function stepsOf(sit: Sit): Step[] {
  if (sit.steps?.length) return sit.steps;
  const gs = sit.groups ?? [{ id: '', title: '' }];
  return gs.map((g) => ({ title: g.title || t('Details'), groups: [g.id] }));
}

const empty = (v: unknown) => v === undefined || v === null || String(v).trim() === '';
/** Quick checks on the visible step so a person is not sent to the end to find a missing field. The server still validates everything. */
export function stepErrors(qs: Q[], answers: Record<string, any>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const q of qs) {
    const v = answers[q.id];
    if (q.type === 'list') {
      const rows = (v ?? []) as Record<string, string>[];
      const filled = rows.filter((r) => !empty(r.name));
      if (filled.length < (q.minRows ?? 1)) out[q.id] = t('Add at least {n}', { n: q.minRows ?? 1 });
      continue;
    }
    if (q.labelFrom) continue;
    if (q.required && empty(v)) { out[q.id] = t('This field is required'); continue; }
    if (q.type === 'number' && !empty(v)) {
      const n = Number(v);
      if (Number.isNaN(n)) out[q.id] = t('Enter a number');
      else if (q.min !== undefined && n < q.min) out[q.id] = t('Must be at least {min}', { min: q.min });
      else if (q.max !== undefined && n > q.max) out[q.id] = t('Must be at most {max}', { max: q.max });
    }
  }
  return out;
}

function shown(q: Q, v: any): string {
  if (q.type === 'list') { const rows = ((v ?? []) as Record<string, string>[]).filter((r) => !empty(r.name)); return rows.length ? rows.map((r) => r.name).join(', ') : ''; }
  if (empty(v)) return '';
  if (q.type === 'number') return `${v}${q.unit ? (q.unit === '%' ? '' : ' ') + q.unit : ''}`;
  if (q.type === 'select') return q.options?.find((o) => o.value === v)?.label ?? String(v);
  if (q.type === 'date') return fmtDate(String(v));
  return String(v);
}

export function Wizard({ step: rawStep, setStep, onDiscard, sit, answers, setAnswers, serverFields, conf, setConf, ack, setAck, error, busy, onSubmit, onExample }: {
  step: number; setStep: (n: number) => void; onDiscard?: () => void; onExample?: () => void; sit: Sit; answers: Record<string, any>; setAnswers: (a: Record<string, any>) => void; serverFields: Record<string, string>;
  conf: string; setConf: (v: string) => void; ack: boolean; setAck: (v: boolean) => void; error: string; busy: boolean; onSubmit: (e: FormEvent) => void;
}) {
  const steps = useMemo(() => stepsOf(sit), [sit]);
  const step = Math.min(Math.max(rawStep, 0), steps.length);  // a stored step from an older form never points past the review
  const [local, setLocal] = useState<Record<string, string>>({});
  const review = step >= steps.length;
  const qsOf = (n: number) => sit.questions.filter((q) => steps[n].groups.includes(q.group ?? ''));
  const essentialOf = (n: number) => qsOf(n).filter((q) => !q.detail);
  const detailOf = (n: number) => qsOf(n).filter((q) => q.detail);
  const stepSit = (n: number) => ({ questions: essentialOf(n), groups: (sit.groups ?? []).filter((g) => steps[n].groups.includes(g.id)).map((g) => ({ ...g, collapsed: false })) });

  // a server error on a field sends the person to the step that holds it
  useEffect(() => {
    const first = Object.keys(serverFields)[0]?.split('.')[0];
    if (!first) return;
    const at = steps.findIndex((_, n) => qsOf(n).some((q) => q.id === first));
    if (at >= 0) setStep(at);
  }, [serverFields]); // eslint-disable-line react-hooks/exhaustive-deps

  const go = (n: number) => { setLocal({}); setStep(n); setTimeout(() => { const el = document.querySelector('.wiz-progress'); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 60); }, 0); };
  const next = () => {
    const errs = stepErrors(qsOf(step), answers);
    if (Object.keys(errs).length) { setLocal(errs); setTimeout(() => document.getElementById('q_' + Object.keys(errs)[0])?.focus(), 0); return; }
    go(step + 1);
  };
  const total = steps.length + 1;
  const names = [...steps.map((s) => s.title), t('Review')];

  return (
    <div>
      <div className="wiz-progress" data-tour="form-steps" role="group" aria-label={t('Form progress')}>
        <div className="wiz-label">{t('Step {n} of {total}', { n: step + 1, total })}: <b>{names[step]}</b>{onExample && step === 0 && <button type="button" className="linkbtn" onClick={onExample}>{t('Fill with an example')}</button>}{onDiscard && <button type="button" className="linkbtn" onClick={() => { if (window.confirm(t('Discard what you have typed and start over?'))) onDiscard(); }}>{t('Start over')}</button>}</div>
        <div className="wiz-bar" role="progressbar" aria-valuemin={1} aria-valuemax={total} aria-valuenow={step + 1}>
          {names.map((nm, i) => <button key={nm} type="button" className={'wiz-seg' + (i <= step ? ' on' : '')} disabled={i > step} onClick={() => go(i)} aria-label={nm} aria-current={i === step ? 'step' : undefined} />)}
        </div>
      </div>
      {!review ? (
        <form noValidate onSubmit={(e) => { e.preventDefault(); next(); }}>
          <QuestionGroups sit={stepSit(step)} answers={answers} fields={{ ...serverFields, ...local }} onChange={setAnswers} />
          {detailOf(step).length > 0 && (
            <details className="more" open={detailOf(step).some((q) => (serverFields[q.id] || local[q.id]))}>
              <summary>{t('Add more detail')}{steps[step].detailNote && <span className="more-note"> {steps[step].detailNote}</span>}</summary>
              {detailOf(step).map((q) => <QuestionField key={q.id} q={q} value={answers[q.id]} error={serverFields[q.id] || local[q.id]} errors={{ ...serverFields, ...local }} answers={answers} onChange={(v) => setAnswers({ ...answers, [q.id]: v })} />)}
            </details>
          )}
          {Object.keys(local).length > 0 && <div className="field error" role="alert">{t('Fill in the highlighted fields to continue.')}</div>}
          <div className="row" style={{ marginTop: 16 }}>
            {step > 0 && <Button type="button" variant="secondary" onClick={() => go(step - 1)}>{t('Back')}</Button>}
            <Button type="submit">{step === steps.length - 1 ? t('Review') : t('Next')}</Button>
          </div>
        </form>
      ) : (
        <form onSubmit={onSubmit} noValidate>
          <Panel title={t('Review')} lead={t('Check what you entered. Press Back to change anything.')}>
            {steps.map((st, n) => {
              const rows = qsOf(n).map((q) => ({ q, v: shown(q, answers[q.id]) })).filter((r) => r.v);
              return (
                <section key={st.title} className="review-block">
                  <h3>{st.title}<button type="button" className="linkbtn review-edit" onClick={() => go(n)}>{t('Edit')}</button></h3>
                  {rows.length === 0 ? <p className="muted small">{t('Nothing entered.')}</p> : (
                    <dl className="review">{rows.map(({ q, v }) => <div key={q.id} className="review-row"><dt>{q.label}</dt><dd>{v}</dd></div>)}</dl>
                  )}
                </section>
              );
            })}
          </Panel>
          <Panel>
            <Field id="conf" label={t('How confident do you feel handling this right now?')} help={t('1 is not at all, 5 is very.')} why={t('After you decide, we ask again. The change shows you whether working through it helped, and it feeds your Progress page. It never affects the calculation.')}>
              {(a) => <select className="input" {...a} value={conf} onChange={(e) => setConf(e.target.value)}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select>}
            </Field>
            <label className="check"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> {t('I did not enter confidential employer or client information.')}</label>
            {error && <div className="field error" role="alert">{error}</div>}
            <div className="row" style={{ marginTop: 24 }}>
              <Button type="button" variant="secondary" onClick={() => go(steps.length - 1)}>{t('Back')}</Button>
              <span data-tour="form-submit"><Button type="submit" busy={busy}>{t('Compare my options')}</Button></span>
            </div>
          </Panel>
        </form>
      )}
    </div>
  );
}
