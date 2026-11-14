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
  if (!p) return <p className="muted">Loading</p>;
  const limitHit = params.get('from') === 'limit';
  return (
    <div className="narrow">
      <PageHeader eyebrow="Pricing" title="Rehearse every hard call in your first months"
        lead="Start free. When the free situations run out, one pass covers your first months in the role. No subscription." />
      {limitHit && <div className="banner" role="note"><strong>You have used your {p.free.cases} free situations.</strong> Your saved cases, documents and journal stay available. Get the pass to start new ones.</div>}
      {b?.plan === 'pass' && <div className="banner ok" role="status">Your pass is active until {fmtDate(b.pass!.expiresAt.slice(0, 10))}.</div>}
      <div className="plans">
        <Panel title={p.free.name}>
          <p className="plan-price">$0</p>
          <ul className="plain">{p.free.features.map((f) => <li key={f}>{f}</li>)}</ul>
          {signedIn && b?.plan === 'free' && <p className="small muted">{b.remaining} of {p.free.cases} left</p>}
          {!signedIn && <Link className="btn btn-secondary" to="/register">Create a free account</Link>}
        </Panel>
        <Panel title={p.pass.name}>
          <p className="plan-price">{price(p.pass.priceCents)} <span className="small muted">{p.pass.billing}</span></p>
          <ul className="plain">{p.pass.features.map((f) => <li key={f}>{f}</li>)}</ul>
          {signedIn
            ? <Button onClick={() => nav('/checkout')} disabled={!p.testCheckout}>{b?.plan === 'pass' ? 'Extend my pass' : 'Get the pass'}</Button>
            : <p className="small muted">Try the demo or create an account first. The demo can buy a test pass too.</p>}
        </Panel>
      </div>
      {p.testCheckout && <p className="small muted">Payments are in test mode for the Business Cup demo: checkout completes without charging anything and asks for no card details.</p>}
      {!signedIn && <p><Link to="/login">Back to sign in</Link></p>}
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
  if (!p) return <p className="muted">Loading</p>;
  if (!p.testCheckout) return <div className="banner" role="note">Checkout is not available right now.</div>;
  const buy = async () => {
    setBusy(true); setError('');
    try {
      await api('POST', '/billing/test-checkout', { plan: p.pass.id, confirm: ok });
      notify(`${p.pass.name} is active. Test purchase, nothing was charged.`);
      nav('/');
    } catch (x: any) { setError(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="narrow">
      <PageHeader eyebrow="Checkout · test mode" title={p.pass.name} />
      <Panel title="Order summary">
        <table className="summary">
          <tbody>
            <tr><td>{p.pass.name} ({p.pass.days} days)</td><td className="num">{price(p.pass.priceCents)}</td></tr>
            <tr><td>Billing</td><td className="num">{p.pass.billing}</td></tr>
            <tr><th scope="row">Total today</th><th className="num">{price(p.pass.priceCents)}</th></tr>
          </tbody>
        </table>
        <div className="banner" role="note" style={{ marginTop: 16 }}>
          <strong>Test mode.</strong> This is a demo checkout for the Business Cup. No card details are needed and no money is charged.
        </div>
        <label className="check"><input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} /> I understand this is a test purchase.</label>
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 24 }}>
          <Button onClick={buy} busy={busy} disabled={!ok}>Complete test purchase</Button>
          <Link to="/pricing">Back</Link>
        </div>
      </Panel>
    </div>
  );
}
