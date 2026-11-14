import { t } from '../i18n';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Billing, Pricing, api, fmtDate, price } from '../api';
import { notify } from '../components/Toaster';
import { Button, PageHeader, Panel } from '../components/ui';

/** Works signed in and signed out (the jury must reach it without an account). */
export default function PricingPage({ signedIn }: { signedIn: boolean }) {
  const [p, setP] = useState<Pricing | null>(null);
  const [b, setB] = useState<Billing | null>(null);
  const [error, setError] = useState('');
  const [params] = useSearchParams();
  const nav = useNavigate();
  useEffect(() => {
    api<Pricing>('GET', '/pricing').then(setP).catch((e) => setError(e.message));
    if (signedIn) api<Billing>('GET', '/billing').then(setB).catch(() => {});
  }, [signedIn]);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!p) return <p className="muted">{t('Loading')}</p>;
  const limitHit = params.get('from') === 'limit';
  return (
    <div className="narrow">
      <PageHeader eyebrow={t('Pricing')} title={t('Rehearse every hard call in your first months')}
        lead={t('Start free. When the free scenarios run out, one pass covers your first months in the role. No subscription.')} />
      {limitHit && <div className="banner" role="note"><strong>{t('You have used your {n} free scenarios.', { n: p.free.cases })}</strong> {t('Your saved cases, documents and journal stay available. Get the pass to start new ones.')}</div>}
      {b?.plan === 'pass' && <div className="banner ok" role="status">{t('Your pass is active until {date}.', { date: fmtDate(b.pass!.expiresAt.slice(0, 10)) })}</div>}
      <div className="plans">
        <Panel title={p.free.name}>
          <p className="plan-price">$0</p>
          <ul className="plain">{p.free.features.map((f) => <li key={f}>{f}</li>)}</ul>
          {signedIn && b?.plan === 'free' && <p className="small muted">{t('{remaining} of {total} left', { remaining: b.remaining, total: p.free.cases })}</p>}
          {!signedIn && <Link className="btn btn-secondary" to="/register">{t('Create a free account')}</Link>}
        </Panel>
        <Panel title={p.pass.name}>
          <p className="plan-price">{price(p.pass.priceCents)} <span className="small muted">{p.pass.billing}</span></p>
          <ul className="plain">{p.pass.features.map((f) => <li key={f}>{f}</li>)}</ul>
          {signedIn
            ? <Button onClick={() => nav('/checkout')} disabled={!p.testCheckout}>{b?.plan === 'pass' ? t('Extend my pass') : t('Get the pass')}</Button>
            : <p className="small muted">{t('Try the demo or create an account first. The demo can buy a test pass too.')}</p>}
        </Panel>
      </div>
      {p.testCheckout && <p className="small muted">{t('Payments are in test mode for the Business Cup demo: checkout completes without charging anything and asks for no card details.')}</p>}
      {!signedIn && <p><Link to="/login">{t('Back to sign in')}</Link></p>}
    </div>
  );
}

export function CheckoutPage() {
  const [p, setP] = useState<Pricing | null>(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  const [error, setError] = useState('');
  const nav = useNavigate();
  useEffect(() => { api<Pricing>('GET', '/pricing').then(setP).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="banner bad" role="alert">{error}</div>;
  if (!p) return <p className="muted">{t('Loading')}</p>;
  if (!p.testCheckout) return <div className="banner" role="note">{t('Checkout is not available right now.')}</div>;
  const buy = async () => {
    setBusy(true); setError('');
    try {
      await api('POST', '/billing/test-checkout', { plan: p.pass.id, confirm: ok });
      notify(t('{name} is active. Test purchase, nothing was charged.', { name: p.pass.name }));
      nav('/');
    } catch (x: any) { setError(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="narrow">
      <PageHeader eyebrow={t('Checkout · test mode')} title={p.pass.name} />
      <Panel title={t('Order summary')}>
        <table className="summary">
          <tbody>
            <tr><td>{p.pass.name} ({t('{n} days', { n: p.pass.days })})</td><td className="num">{price(p.pass.priceCents)}</td></tr>
            <tr><td>{t('Billing')}</td><td className="num">{p.pass.billing}</td></tr>
            <tr><th scope="row">{t('Total today')}</th><th className="num">{price(p.pass.priceCents)}</th></tr>
          </tbody>
        </table>
        <div className="banner" role="note" style={{ marginTop: 16 }}>
          <strong>{t('Test mode.')}</strong> {t('This is a demo checkout for the Business Cup. No card details are needed and no money is charged.')}
        </div>
        <label className="check"><input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} /> {t('I understand this is a test purchase.')}</label>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}>
          <Button onClick={buy} busy={busy} disabled={!ok}>{t('Complete test purchase')}</Button>
          <Link to="/pricing">{t('Back')}</Link>
        </div>
      </Panel>
    </div>
  );
}
