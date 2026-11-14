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

/** Renders one question from the situation pack. */
export function QuestionField({ q, value, error, onChange }: { q: Question; value: string; error?: string; onChange: (v: string) => void }) {
  const label = q.label + (q.required ? '' : ' (optional)');
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

export const initialAnswers = (qs: Question[], from?: Record<string, any>) =>
  Object.fromEntries(qs.map((q) => [q.id, String(from?.[q.id] ?? q.default ?? '')]));

export function useToast() {
  const [msg, setMsg] = useState('');
  const show = (m: string) => { setMsg(m); setTimeout(() => setMsg(''), 2500); };
  const node = msg ? <div className="toast" role="status">{msg}</div> : null;
  return { show, node };
}
