import { notify } from './Toaster';
import { ReactNode, useState } from 'react';
import { Question } from '../api';

export const PrivacyBanner = () => (
  <div className="banner" role="note">
    <strong>Privacy:</strong> do not enter confidential employer or client information. Use rounded or made-up numbers and generic names.
  </div>
);

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

export const Badge = ({ level }: { level: 'low' | 'medium' | 'high' }) => <span className={`badge ${level}`}>{level} risk</span>;

interface FieldProps { id: string; label: string; help?: string; error?: string; children: (a: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }) => ReactNode }
export function Field({ id, label, help, error, children }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {help && <div className="help" id={id + '-h'}>{help}</div>}
      {children({ id, 'aria-invalid': error ? true : undefined, 'aria-describedby': error ? id + '-e' : help ? id + '-h' : undefined })}
      {error && <div className="error" id={id + '-e'}>{error}</div>}
    </div>
  );
}

/** Renders one question from the situation pack. A "list" question renders repeatable rows. */
export function QuestionField({ q, value, error, errors, onChange, answers }: { q: Question; value: any; error?: string; errors?: Record<string, string>; onChange: (v: any) => void; answers?: Record<string, any> }) {
  if (q.type === 'list') return <ListField q={q} rows={value ?? []} error={error} errors={errors ?? {}} onChange={onChange} answers={answers ?? {}} />;
  const label = q.label + (q.required || q.labelFrom ? '' : ' (optional)');
  return (
    <Field id={'q_' + q.id} label={label} help={q.help} error={error}>
      {(a) =>
        q.type === 'select' ? (
          <select className="input" {...a} value={value} onChange={(e) => onChange(e.target.value)}>
            {q.options!.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ) : q.type === 'textarea' ? (
          <textarea className="input" {...a} maxLength={q.max} value={value} onChange={(e) => onChange(e.target.value)} />
        ) : (
          <input className="input" {...a} type={q.type === 'number' ? 'number' : q.type === 'date' ? 'date' : 'text'}
            inputMode={q.type === 'number' ? 'decimal' : undefined} min={q.min} max={q.type === 'number' ? q.max : undefined}
            step={q.type === 'number' ? q.step ?? 'any' : undefined} maxLength={q.type === 'text' ? q.max : undefined}
            placeholder={q.placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
        )
      }
    </Field>
  );
}

const emptyRow = (fields: Question[]) => Object.fromEntries(fields.map((f) => [f.id, String(f.default ?? '')]));

/** A row field can take its label from another list (a score column named after the criterion typed so far) and is hidden when that criterion row does not exist. */
function dynamicField(f: Question, answers: Record<string, any>): Question | null {
  const l = f.labelFrom;
  if (!l) return f;
  const rows: Record<string, string>[] = answers[l.list] ?? [];
  if (rows.length <= l.index) return null;
  const name = (rows[l.index]?.[l.field] ?? '').trim() || `criterion ${l.index + 1}`;
  return { ...f, label: l.template.replace('{name}', name) };
}

function ListField({ q, rows, error, errors, onChange, answers }: { q: Question; rows: Record<string, string>[]; error?: string; errors: Record<string, string>; onChange: (v: any) => void; answers: Record<string, any> }) {
  const fields = q.fields!;
  const item = q.itemLabel ?? 'Item';
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
                <Button type="button" variant="quiet" disabled={n === 0} onClick={() => move(n, -1)} aria-label={`Move ${item.toLowerCase()} ${n + 1} up`}>Up</Button>
                <Button type="button" variant="quiet" disabled={n === rows.length - 1} onClick={() => move(n, 1)} aria-label={`Move ${item.toLowerCase()} ${n + 1} down`}>Down</Button>
                <Button type="button" variant="quiet" disabled={rows.length <= (q.minRows ?? 1)} onClick={() => onChange(rows.filter((_, i) => i !== n))} aria-label={`Remove ${item.toLowerCase()} ${n + 1}`}>Remove</Button>
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
      {rows.length < (q.maxRows ?? 10) && <Button type="button" variant="secondary" onClick={() => onChange([...rows, emptyRow(fields)])}>Add {item.toLowerCase()}</Button>}
    </div>
  );
}

const asStrings = (fields: Question[], row: Record<string, any>) => Object.fromEntries(fields.map((f) => [f.id, String(row?.[f.id] ?? f.default ?? '')]));

export const initialAnswers = (qs: Question[], from?: Record<string, any>): Record<string, any> =>
  Object.fromEntries(qs.map((q) => [q.id, q.type === 'list'
    ? (from?.[q.id] ?? Array.from({ length: q.minRows ?? 1 }, () => ({}))).map((r: any) => asStrings(q.fields!, r))
    : String(from?.[q.id] ?? q.default ?? '')]));

/** All questions of a situation, laid out by the pack's groups. */
export function QuestionGroups({ sit, answers, fields, onChange, skipCollapsed }: { sit: { questions: Question[]; groups?: { id: string; title: string; columns?: number; collapsed?: boolean }[] }; answers: Record<string, any>; fields: Record<string, string>; onChange: (a: Record<string, any>) => void; skipCollapsed?: boolean }) {
  const groups = sit.groups ?? [{ id: '', title: '' }];
  const render = (g: { id: string; columns?: number }) => {
    const qs = sit.questions.filter((q) => (q.group ?? '') === g.id);
    const body = qs.map((q) => <QuestionField key={q.id} q={q} value={answers[q.id]} error={fields[q.id]} errors={fields} answers={answers} onChange={(v) => onChange({ ...answers, [q.id]: v })} />);
    return g.columns === 2 ? <div className="grid-2">{body}</div> : <>{body}</>;
  };
  return (
    <>
      {groups.map((g) => g.collapsed
        ? (skipCollapsed ? null : <Panel key={g.id}><details><summary style={{ marginTop: 0 }}>{g.title}</summary>{render(g)}</details></Panel>)
        : <Panel key={g.id} title={g.title || undefined}>{render(g)}</Panel>)}
    </>
  );
}

export function useToast() {
  return { show: (m: string) => notify(m), node: null as React.ReactNode };
}
