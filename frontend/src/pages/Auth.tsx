import { t } from '../i18n';
import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Button, Field, PrivacyBanner } from '../components/ui';

export default function Auth({ mode, onDone }: { mode: 'login' | 'register'; onDone: () => Promise<void> }) {
  const reg = mode === 'register';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(false);
  useEffect(() => { api('GET', '/public-config').then((c) => setDemoEnabled(c.demoEnabled)).catch(() => {}); }, []);

  async function startDemo() {
    setError('');
    setBusy(true);
    try { await api('POST', '/auth/demo', {}); await onDone(); } catch (x: any) { setError(x.message); setBusy(false); }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api('POST', reg ? '/auth/register' : '/auth/login', { email, password });
      await onDone();
    } catch (x: any) {
      setError(x.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page narrow">
      <div className="caption">{t('RoleShift')}</div>
      <h1 style={{ marginTop: 8 }}>{t('The first 90 days in a new position are the hardest. Decide with numbers, not nerves.')}</h1>
      <p className="lead muted" style={{ marginTop: 12, fontSize: 18 }}>
        
        {t('Work through a real scenario with your real figures. See what each choice costs, then send a document you can stand behind.')}
      </p>
      {demoEnabled && (
        <div className="panel">
          <h2>{t('See it in one click')}</h2>
          <p className="muted">{t('Opens a demo account with a finished case, a decision waiting for follow-up and a draft ready to decide. No sign-up.')}</p>
          <div className="row" style={{ marginTop: 16 }}><Button onClick={startDemo} busy={busy}>{t('Try the demo')}</Button></div>
        </div>
      )}
      <PrivacyBanner />
      <form className="panel" onSubmit={submit} noValidate>
        <h2>{reg ? t('Create your account') : t('Sign in')}</h2>
        <Field id="email" label={t('Email')}>{(a) => <input className="input" {...a} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />}</Field>
        <Field id="password" label={t('Password') + (reg ? t(' (at least 8 characters)') : '')}>
          {(a) => <input className="input" {...a} type="password" autoComplete={reg ? 'new-password' : 'current-password'} value={password} onChange={(e) => setPassword(e.target.value)} />}
        </Field>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}>
          <Button type="submit" busy={busy}>{reg ? t('Create account') : t('Sign in')}</Button>
          <Link to={reg ? '/login' : '/register'}>{reg ? t('I already have an account') : t('Create an account')}</Link>{' · '}<Link to="/pricing">{t('Pricing')}</Link>
        </div>
      </form>
    </main>
  );
}
