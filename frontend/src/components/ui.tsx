import { t } from '../i18n';
import { NavLink } from 'react-router-dom';
import { LANGS, getLang, setLang, t as tt, Lang } from '../i18n';
import { notify } from './Toaster';
import { ReactNode, useState } from 'react';
import { Question } from '../api';

export const PrivacyBanner = () => (
  <div className="banner" role="note">
    <strong>{t('Privacy:')}</strong> {t('do not enter confidential employer or client information. Use rounded or made-up numbers and generic names.')}
  </div>
);

/** Four steps of every scenario, with what the person does in each. `current` is 1-4; earlier steps show as done. */
export function Stepper({ current }: { current: 1 | 2 | 3 | 4 }) {
  const steps = [[t('Fill in'), t('Tell us the facts and your numbers.')], [t('Compare'), t('See each option with its outcome.')], [t('Decide'), t('Pick one and get a ready message.')], [t('Follow up'), t('Record how it went.')]];
  return (
    <ol className="stepper" aria-label={t('Steps')} data-tour="stepper">
      {steps.map(([t, d], n) => (
        <li key={t} className={n + 1 === current ? 'on' : n + 1 < current ? 'done' : ''} aria-current={n + 1 === current ? 'step' : undefined}>
          <b><span className="num">{n + 1 < current ? '✓' : n + 1}</span> {t}</b><span>{d}</span>
        </li>
      ))}
    </ol>
  );
}

/** Small expandable "Why we ask", no modal. */
export function Why({ children }: { children: ReactNode }) {
  return <details className="why" data-tour="form-why"><summary>{t('Why we ask')}</summary><p>{children}</p></details>;
}

export function CaseTabs() {
  return (
    <nav className="subtabs" aria-label={t('My cases')} data-tour="cases-tabs">
      <NavLink to="/journal">{t('Journal')}</NavLink><NavLink to="/documents">{t('Documents')}</NavLink>
    </nav>
  );
}

export function PageHeader({ eyebrow, title, lead }: { eyebrow?: string; title: string; lead?: ReactNode }) {
  return (
    <header className="page-header">
      {eyebrow && <div className="caption">{eyebrow}</div>}
      <h1>{title}</h1>
      {lead && <p className="lead">{lead}</p>}
    </header>
  );
}

export const Panel = ({ title, children, lead }: { title?: string; lead?: ReactNode; children: ReactNode }) => (
  <section className="panel">
    {title && <h2>{title}</h2>}
    {lead && <p className="muted">{lead}</p>}
    {children}
  </section>
);

export function Button({ variant = 'primary', busy, children, className, ...rest }: { variant?: 'primary' | 'secondary' | 'quiet'; busy?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...rest} className={`btn btn-${variant}${className ? ' ' + className : ''}`} aria-busy={busy || undefined} disabled={busy || rest.disabled}>
      {children}
    </button>
  );
}

export const Badge = ({ level }: { level: 'low' | 'medium' | 'high' }) => <span className={`badge ${level}`}>{t('Risk on your numbers: {level}', { level: t(level) })}</span>;

interface FieldProps { id: string; label: string; help?: string; why?: string; error?: string; children: (a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }) => ReactNode }
export function Field({ id, label, help, why, error, children }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={id} id={id + '-l'}>{label}</label>
      {help && <div className="help" id={id + '-h'}>{help}</div>}
      {children({ id, 'aria-invalid': error ? true : undefined, 'aria-describedby': error ? id + '-e' : help ? id + '-h' : undefined })}
      {why && <Why>{why}</Why>}
      {error && <div className="error" id={id + '-e'}>{error}</div>}
    </div>
  );
}

/** Renders one question from the scenario pack. A "list" question renders repeatable rows. */
export function QuestionField({ q, value, error, errors, onChange, answers }: { q: Question; value: any; error?: string; errors?: Record<string, string>; onChange: (v: any) => void; answers?: Record<string, any> }) {
  if (q.type === 'list') return <ListField q={q} rows={value ?? []} error={error} errors={errors ?? {}} onChange={onChange} answers={answers ?? {}} />;
  const label = q.label + (q.required || q.labelFrom ? '' : ' (' + t('optional') + ')');
  return (
    <Field id={'q_' + q.id} label={label} help={q.help} why={q.why} error={error}>
      {(a) =>
        q.type === 'select' && q.slider ? (
          <ChoiceSlider q={q} a={a} value={value} onChange={onChange} />
        ) : q.type === 'select' && segmented(q) ? (
          <div className="segs" role="radiogroup" aria-labelledby={a.id + '-l'} id={a.id}>
            {q.options!.map((o) => <button key={o.value} type="button" role="radio" aria-checked={value === o.value} className={'seg' + (value === o.value ? ' on' : '')} onClick={() => onChange(o.value)}>{o.label}</button>)}
          </div>
        ) : q.type === 'number' && sliderOf(q) ? (
          <Slider q={q} a={a} value={value} onChange={onChange} />
        ) : q.type === 'select' ? (
          <select className="input" {...a} value={value} onChange={(e) => onChange(e.target.value)}>
            {q.options!.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ) : q.type === 'textarea' ? (
          <textarea className="input" {...a} maxLength={q.max} value={value} onChange={(e) => onChange(e.target.value)} />
        ) : (
          <>
          <input className="input" {...a} type={q.type === 'number' ? 'number' : q.type === 'date' ? 'date' : 'text'}
            inputMode={q.type === 'number' ? 'decimal' : undefined} min={q.min} max={q.type === 'number' ? q.max : undefined}
            step={q.type === 'number' ? q.step ?? 'any' : undefined} maxLength={q.type === 'text' ? q.max : undefined}
            placeholder={q.placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
          {q.type === 'date' && <DateChips onPick={onChange} compact={q.id.includes('.')} />}
          </>
        )
      }
    </Field>
  );
}

/** A short list of choices (up to 5) outside a table row is shown as buttons, so one click picks it. */
const segmented = (q: Question) => !q.id.includes('.') && !!q.options && q.options.length <= 5;
/** A bounded number with a step and a range of up to 100 steps is a slider; the exact number can still be typed. */
const sliderOf = (q: Question) => q.step !== undefined && q.max !== undefined && q.min !== undefined && q.max - q.min <= 100 && q.max - q.min >= 2 * q.step;

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
/** Quick dates next to a date picker: today, tomorrow, the coming Friday, and one and two weeks from today. */
export function chipDates(now = new Date()): { label: string; value: string }[] {
  const plus = (n: number) => { const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + n); return iso(d); };
  return [
    { label: t('Today'), value: plus(0) }, { label: t('Tomorrow'), value: plus(1) },
    { label: t('This Friday'), value: plus((5 - now.getDay() + 7) % 7) },
    { label: t('In 1 week'), value: plus(7) }, { label: t('In 2 weeks'), value: plus(14) },
  ];
}
export function DateChips({ onPick, compact }: { onPick: (v: string) => void; compact?: boolean }) {
  return <div className="chips">{chipDates().filter((_, i) => !compact || [1, 2, 3].includes(i)).map((c) => <button key={c.label} type="button" className="chip" onClick={() => onPick(c.value)}>{c.label}</button>)}</div>;
}

/** A short ordered list of options (low / medium / high) as a slider: the live word shows the chosen option; the stored value stays the option's key. */
function ChoiceSlider({ q, a, value, onChange }: { q: Question; a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }; value: any; onChange: (v: any) => void }) {
  const opts = q.sliderReverse ? q.options!.slice().reverse() : q.options!;
  const i = Math.max(0, opts.findIndex((o) => o.value === value));
  return (
    <div className="slider">
      <input type="range" {...a} min={0} max={opts.length - 1} step={1} value={i} aria-valuetext={opts[i].label} onChange={(e) => onChange(opts[Number(e.target.value)].value)} />
      <div className="slider-ends" style={{ margin: '-6px 0 0' }} aria-hidden="true"><span>{q.anchors?.[0] ?? opts[0].label}</span><span>{q.anchors?.[1] ?? opts[opts.length - 1].label}</span></div>
      <output className="slider-word" aria-live="polite">{opts[i].label}</output>
    </div>
  );
}

function Slider({ q, a, value, onChange }: { q: Question; a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }; value: any; onChange: (v: any) => void }) {
  const min = q.min!, max = q.max!;
  const empty = value === '' || value === undefined || Number.isNaN(Number(value));
  const shown = empty ? min : Math.min(max, Math.max(min, Number(value)));
  return (
    <div className="slider">
      <div className="slider-top">
        <input type="range" {...a} min={min} max={max} step={q.step} value={shown} onChange={(e) => onChange(e.target.value)} className={empty ? 'unset' : ''} />
        <input className="input slider-num" type="number" inputMode="decimal" aria-label={q.label} min={min} max={max} step={q.step} value={value} placeholder={t('not set')} onChange={(e) => onChange(e.target.value)} />
      </div>
      <div className="slider-ends" aria-hidden="true"><span>{q.anchors?.[0] ?? min}</span><span>{q.anchors?.[1] ?? max}</span></div>
      {!empty && q.words && q.words[Math.round((shown - min) / (q.step || 1))] && <output className="slider-word" aria-live="polite">{q.words[Math.round((shown - min) / (q.step || 1))]}</output>}
    </div>
  );
}

const emptyRow = (fields: Question[]) => Object.fromEntries(fields.map((f) => [f.id, String(f.default ?? '')]));

/** A row field can take its label from another list (a score column named after the criterion typed so far) and is hidden when that criterion row does not exist. */
function dynamicField(f: Question, answers: Record<string, any>): Question | null {
  const l = f.labelFrom;
  if (!l) return f;
  const rows: Record<string, string>[] = answers[l.list] ?? [];
  if (rows.length <= l.index) return null;
  const name = (rows[l.index]?.[l.field] ?? '').trim() || t('criterion {n}', { n: l.index + 1 });
  return { ...f, label: l.template.replace('{name}', name) };
}

function ListField({ q, rows, error, errors, onChange, answers }: { q: Question; rows: Record<string, string>[]; error?: string; errors: Record<string, string>; onChange: (v: any) => void; answers: Record<string, any> }) {
  const fields = q.fields!;
  const item = q.itemLabel ?? t('Item');
  const set = (n: number, id: string, v: string) => onChange(rows.map((r, i) => (i === n ? { ...r, [id]: v } : r)));
  const move = (n: number, d: number) => {
    const next = rows.slice(); const [r] = next.splice(n, 1); next.splice(n + d, 0, r); onChange(next);
  };
  return (
    <div className="listq" id={'q_' + q.id}>
      {q.help && <p className="help">{q.help}</p>}
      {error && <div className="error" role="alert">{error}</div>}
      <ol className="plain listq-rows">
        {rows.map((r, n) => (
          <li key={n} className="listq-row">
            <div className="listq-head">
              <b>{item} {n + 1}</b>
              <span className="row">
                <Button type="button" variant="quiet" disabled={n === 0} onClick={() => move(n, -1)} aria-label={t('Move {item} {n} up', { item: item.toLowerCase(), n: n + 1 })}>{t('Up')}</Button>
                <Button type="button" variant="quiet" disabled={n === rows.length - 1} onClick={() => move(n, 1)} aria-label={t('Move {item} {n} down', { item: item.toLowerCase(), n: n + 1 })}>{t('Down')}</Button>
                <Button type="button" variant="quiet" disabled={rows.length <= (q.minRows ?? 1)} onClick={() => onChange(rows.filter((_, i) => i !== n))} aria-label={t('Remove {item} {n}', { item: item.toLowerCase(), n: n + 1 })}>{t('Remove')}</Button>
              </span>
            </div>
            <div className="grid-3">
              {fields.map((f0) => dynamicField(f0, answers)).filter((f): f is Question => !!f).map((f) => (
                <QuestionField key={f.id} q={{ ...f, id: `${q.id}.${n}.${f.id}` }} value={r[f.id] ?? ''} error={errors[`${q.id}.${n}.${f.id}`]} onChange={(v) => set(n, f.id, v)} />
              ))}
            </div>
          </li>
        ))}
      </ol>
      {rows.length < (q.maxRows ?? 10) && <Button type="button" variant="secondary" onClick={() => onChange([...rows, emptyRow(fields)])}>{t('Add {item}', { item: item.toLowerCase() })}</Button>}
    </div>
  );
}

const asStrings = (fields: Question[], row: Record<string, any>) => Object.fromEntries(fields.map((f) => [f.id, String(row?.[f.id] ?? f.default ?? '')]));

export const initialAnswers = (qs: Question[], from?: Record<string, any>): Record<string, any> =>
  Object.fromEntries(qs.map((q) => [q.id, q.type === 'list'
    ? (from?.[q.id] ?? q.defaultRows ?? Array.from({ length: q.minRows ?? 1 }, () => ({}))).map((r: any) => asStrings(q.fields!, r))
    : String(from?.[q.id] ?? q.default ?? '')]));

/** All questions of a scenario, laid out by the pack's groups. */
export function QuestionGroups({ sit, answers, fields, onChange, skipCollapsed }: { sit: { questions: Question[]; groups?: { id: string; title: string; columns?: number; collapsed?: boolean }[] }; answers: Record<string, any>; fields: Record<string, string>; onChange: (a: Record<string, any>) => void; skipCollapsed?: boolean }) {
  const groups = sit.groups ?? [{ id: '', title: '' }];
  const render = (g: { id: string; columns?: number }) => {
    const qs = sit.questions.filter((q) => (q.group ?? '') === g.id);
    const body = qs.map((q) => <QuestionField key={q.id} q={q} value={answers[q.id]} error={fields[q.id]} errors={fields} answers={answers} onChange={(v) => onChange({ ...answers, [q.id]: v })} />);
    return g.columns === 2 ? <div className="grid-2">{body}</div> : <>{body}</>;
  };
  return (
    <>
      {groups.map((g, n) => <div key={g.id} data-tour={g.id === 'forgot' ? 'form-forgot' : n === 0 ? 'form-first' : undefined}>{g.collapsed
        ? (skipCollapsed ? null : <Panel><details><summary style={{ marginTop: 0 }}>{g.title}</summary>{render(g)}</details></Panel>)
        : <Panel title={g.title || undefined}>{render(g)}</Panel>}</div>)}
    </>
  );
}

export function useToast() {
  return { show: (m: string) => notify(m), node: null as React.ReactNode };
}


/** EN / RU / KZ. Saves the choice (this browser, and the account when signed in) and reloads so every text and every server answer changes. */
export function LanguageSwitch({ signedIn = true }: { signedIn?: boolean }) {
  const change = async (code: Lang) => {
    setLang(code);
    if (signedIn) { try { await fetch('/api/profile/language', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ language: code }) }); } catch { /* the browser choice still applies */ } }
    window.location.reload();
  };
  return (
    <select className="langsel" data-tour="nav-lang" aria-label={tt('Language')} value={getLang()} onChange={(e) => change(e.target.value as Lang)}>
      {LANGS.map((l) => <option key={l.code} value={l.code}>{l.short}</option>)}
    </select>
  );
}
