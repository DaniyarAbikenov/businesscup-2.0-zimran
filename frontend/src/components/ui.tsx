import { t } from '../i18n';
import { NavLink } from 'react-router-dom';
import { LANGS, getLang, setLang, t as tt, Lang } from '../i18n';
import { notify } from './Toaster';
import { ReactNode, useState } from 'react';
import { Question, fmtDate } from '../api';

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

interface FieldProps { id: string; label: string; help?: string; hint?: string; why?: string; error?: string; children: (a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }) => ReactNode }
export function Field({ id, label, help, hint, why, error, children }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={id} id={id + '-l'}>{label}</label>
      {help && <div className="help" id={id + '-h'}>{help}</div>}
      {hint && <div className="hint">{hint}</div>}
      {children({ id, 'aria-invalid': error ? true : undefined, 'aria-describedby': error ? id + '-e' : help ? id + '-h' : undefined })}
      {why && <Why>{why}</Why>}
      {error && <div className="error" id={id + '-e'}>{error}</div>}
    </div>
  );
}

/** Renders one question from the scenario pack. A "list" question renders repeatable rows. */
export function QuestionField({ q, value, error, errors, onChange, answers }: { q: Question; value: any; error?: string; errors?: Record<string, string>; onChange: (v: any) => void; answers?: Record<string, any> }) {
  if (q.type === 'list') return <ListField q={q} rows={value ?? []} error={error} errors={errors ?? {}} onChange={onChange} answers={answers ?? {}} />;
  const label = q.label;
  return (
    <Field id={'q_' + q.id} label={label} help={q.help} hint={q.example} why={q.why} error={error}>
      {(a) =>
        q.type === 'select' && q.slider ? (
          <ChoiceSlider q={q} a={a} value={value} onChange={onChange} />
        ) : q.type === 'select' && segmented(q) ? (
          <SegGroup id={a.id} options={q.options!} value={value} onChange={onChange} />
        ) : q.type === 'number' && sliderOf(q) ? (
          <Slider q={q} a={a} value={value} onChange={onChange} />
        ) : q.type === 'number' ? (
          <NumberStepper q={q} a={a} value={value} onChange={onChange} />
        ) : q.type === 'select' ? (
          <select className="input" {...a} value={value} onChange={(e) => onChange(e.target.value)}>
            {q.options!.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ) : q.type === 'textarea' ? (
          <textarea className="input" {...a} maxLength={q.max} value={value} onChange={(e) => onChange(e.target.value)} />
        ) : (
          <>
          <input className="input" {...a} type={q.type === 'date' ? 'date' : 'text'} maxLength={q.type === 'text' ? q.max : undefined}
            placeholder={q.placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
          {q.type === 'date' && <DateChips onPick={onChange} compact={q.id.includes('.')} />}
          </>
        )
      }
    </Field>
  );
}

/** One tab stop for the whole group; arrow keys move and select, like a native radio group. */
function SegGroup({ id, options, value, onChange }: { id: string; options: { value: string; label: string }[]; value: string; onChange: (v: string) => void }) {
  const at = Math.max(0, options.findIndex((o) => o.value === value));
  const move = (e: React.KeyboardEvent, d: number) => {
    e.preventDefault();
    const n = (at + d + options.length) % options.length;
    onChange(options[n].value);
    setTimeout(() => (document.getElementById(`${id}-${n}`) as HTMLElement | null)?.focus(), 0);
  };
  return (
    <div className="segs" role="radiogroup" aria-labelledby={id + '-l'} id={id}>
      {options.map((o, n) => (
        <button key={o.value} id={`${id}-${n}`} type="button" role="radio" aria-checked={value === o.value} tabIndex={n === at ? 0 : -1} className={'seg' + (value === o.value ? ' on' : '')}
          onClick={() => onChange(o.value)} onKeyDown={(e) => { if (e.key === 'ArrowRight' || e.key === 'ArrowDown') move(e, 1); else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') move(e, -1); }}>{o.label}</button>
      ))}
    </div>
  );
}

/** A short list of choices (up to 5) outside a table row is shown as buttons, so one click picks it. */
const segmented = (q: Question) => !!q.options && q.options.length <= 5;
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
  return <div className="chips">{chipDates().filter((_, i) => !compact || [1, 2, 3].includes(i)).map((c) => <button key={c.label} type="button" className="chip" aria-label={`${c.label}, ${fmtDate(c.value)}`} onClick={() => onPick(c.value)}>{c.label}</button>)}</div>;
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

/** The unit shown next to a number: % for ...Pct fields, h for hours. Money fields name their currency in the label, so they get none. */
const unitOf = (id: string, q?: Question): string => q?.unit ?? (/Pct$/.test(id) ? '%' : /Hours(PerWeek)?$/.test(id) ? t('h') : /Days$/.test(id) ? t('days') : '');

/** A number without a small range: type it, or step it up and down. The unit sits next to the value. */
function NumberStepper({ q, a, value, onChange }: { q: Question; a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }; value: any; onChange: (v: any) => void }) {
  const step = q.step ?? 1;
  const bump = (d: number) => {
    const cur = value === '' || Number.isNaN(Number(value)) ? (q.min ?? 0) : Number(value);
    let n = Math.round((cur + d * step) * 1000) / 1000;
    if (q.min !== undefined) n = Math.max(q.min, n);
    if (q.max !== undefined) n = Math.min(q.max, n);
    onChange(String(n));
  };
  const u = unitOf(q.id.split('.').pop()!, q);
  return (
    <div className="stepper-num">
      <button type="button" className="step-btn" aria-label={`${t('Decrease')}: ${q.label}`} onClick={() => bump(-1)}>−</button>
      <input className="input" {...a} type="number" inputMode="decimal" min={q.min} max={q.max} step={q.step ?? 'any'} value={value} placeholder={t('not set')} onChange={(e) => onChange(e.target.value)} />
      <button type="button" className="step-btn" aria-label={`${t('Increase')}: ${q.label}`} onClick={() => bump(1)}>+</button>
      {u && <span className="slider-unit" aria-hidden="true">{u}</span>}
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
        <input type="range" {...a} min={min} max={max} step={q.step} value={shown} aria-valuetext={empty ? t('not set') : `${shown}${unitOf(q.id.split('.').pop()!, q) ? (q.unit === '%' ? '' : ' ') + unitOf(q.id.split('.').pop()!, q) : ''}${q.words?.[Math.round((shown - min) / (q.step || 1))] ? ', ' + q.words[Math.round((shown - min) / (q.step || 1))] : ''}`} onChange={(e) => onChange(e.target.value)} className={empty ? 'unset' : ''} />
        <input className="input slider-num" type="number" inputMode="decimal" aria-label={q.label} min={min} max={max} step={q.step} value={value} placeholder={t('not set')} onChange={(e) => onChange(e.target.value)} />
        {unitOf(q.id.split('.').pop()!, q) && <span className="slider-unit" aria-hidden="true">{unitOf(q.id.split('.').pop()!, q)}</span>}
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
  const [open, setOpen] = useState<Set<number>>(new Set());
  const collapsible = !!q.collapsible;
  const hasErr = (n: number) => Object.keys(errors).some((k) => k.startsWith(`${q.id}.${n}.`));
  const isOpen = (n: number) => !collapsible || open.has(n) || !(rows[n]?.name ?? '').trim() || hasErr(n);
  const toggle = (n: number) => setOpen((s) => { const x = new Set(s); x.has(n) ? x.delete(n) : x.add(n); return x; });
  const summary = (r: Record<string, string>) => [r.name, ...(q.summaryFields ?? []).map((id) => {
    const v = r[id]; if (!v) return ''; const f = fields.find((x) => x.id === id);
    return f?.type === 'date' ? fmtDate(v) : v + (unitOf(id) ? ' ' + unitOf(id) : '');
  })].filter(Boolean).join(' · ');
  const move = (n: number, d: number) => {
    setOpen(new Set()); const next = rows.slice(); const [r] = next.splice(n, 1); next.splice(n + d, 0, r); onChange(next);
  };
  return (
    <div className="listq" id={'q_' + q.id}>
      {q.help && <p className="help">{q.help}</p>}
      {error && <div className="error" role="alert">{error}</div>}
      <ol className="plain listq-rows">
        {rows.map((r, n) => (
          <li key={n} className="listq-row">
            <div className="listq-head">
              <b>{collapsible && !isOpen(n) ? (r.name?.trim() || `${item} ${n + 1}`) : `${item} ${n + 1}`}{collapsible && !isOpen(n) && summary(r).includes(' · ') && <span className="listq-sum"> · {summary(r).split(' · ').slice(1).join(' · ')}</span>}</b>
              <span className="row">
                {collapsible && ((rows[n]?.name ?? '').trim() ? <Button type="button" variant="quiet" aria-expanded={isOpen(n)} onClick={() => toggle(n)}>{isOpen(n) ? t('Collapse') : t('Edit')}</Button> : null)}
                <Button type="button" variant="quiet" disabled={n === 0} onClick={() => move(n, -1)} aria-label={t('Move {item} {n} up', { item: item.toLowerCase(), n: n + 1 })}>{t('Up')}</Button>
                <Button type="button" variant="quiet" disabled={n === rows.length - 1} onClick={() => move(n, 1)} aria-label={t('Move {item} {n} down', { item: item.toLowerCase(), n: n + 1 })}>{t('Down')}</Button>
                <Button type="button" variant="quiet" disabled={rows.length <= (q.minRows ?? 1)} onClick={() => { setOpen(new Set()); onChange(rows.filter((_, i) => i !== n)); }} aria-label={t('Remove {item} {n}', { item: item.toLowerCase(), n: n + 1 })}>{t('Remove')}</Button>
              </span>
            </div>
            {isOpen(n) && <>
              <div className="grid-3">
                {fields.filter((f) => !f.detail).map((f0) => dynamicField(f0, answers)).filter((f): f is Question => !!f).map((f) => (
                  <QuestionField key={f.id} q={{ ...f, id: `${q.id}.${n}.${f.id}` }} value={r[f.id] ?? ''} error={errors[`${q.id}.${n}.${f.id}`]} onChange={(v) => set(n, f.id, v)} />
                ))}
              </div>
              {fields.some((f) => f.detail) && <details className="more"><summary>{t('Add more detail')}</summary>
                <div className="grid-3">
                  {fields.filter((f) => f.detail).map((f) => <QuestionField key={f.id} q={{ ...f, id: `${q.id}.${n}.${f.id}` }} value={r[f.id] ?? ''} error={errors[`${q.id}.${n}.${f.id}`]} onChange={(v) => set(n, f.id, v)} />)}
                </div>
              </details>}
            </>}
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
