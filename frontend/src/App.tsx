import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Me, Pack, api } from './api';
import Auth from './pages/Auth';
import CasePage from './pages/Case';
import AccountPage from './pages/Account';
import PricingPage, { CheckoutPage } from './pages/Pricing';
import DocumentsPage from './pages/Documents';
import Home from './pages/Home';
import JournalPage from './pages/Journal';
import NewCase from './pages/NewCase';
import Onboarding from './pages/Onboarding';
import ProgressPage from './pages/Progress';
import { HowItWorksPage } from './components/Guide';
import { CreateSituationPage, PreviewSituationPage } from './pages/MySituations';

interface Session { me: Me; pack: Pack; refresh: () => Promise<void> }
const Ctx = createContext<Session>(null as unknown as Session);
export const useSession = () => useContext(Ctx);

export default function App() {
  const [state, setState] = useState<{ me: Me | null; pack: Pack | null; loading: boolean }>({ me: null, pack: null, loading: true });

  const refresh = useCallback(async () => {
    try {
      const [me, pack] = await Promise.all([api<Me>('GET', '/me'), api<Pack>('GET', '/packs')]);
      setState({ me, pack, loading: false });
    } catch {
      setState({ me: null, pack: null, loading: false });
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  if (state.loading) return <main className="page"><p className="muted">Loading</p></main>;
  if (!state.me || !state.pack) return <Routes><Route path="/pricing" element={<main className="page"><PricingPage signedIn={false} /></main>} /><Route path="/register" element={<Auth mode="register" onDone={refresh} />} /><Route path="*" element={<Auth mode="login" onDone={refresh} />} /></Routes>;
  const session = { me: state.me, pack: state.pack, refresh };
  const needsProfile = !state.me.profile;

  return (
    <Ctx.Provider value={session}>
      <TopBar />
      <main className="page">
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          {needsProfile ? (
            <Route path="*" element={<Navigate to="/onboarding" replace />} />
          ) : (
            <>
              <Route path="/" element={<Home />} />
              <Route path="/new/:situationId" element={<NewCase />} />
              <Route path="/my/new" element={<CreateSituationPage />} />
              <Route path="/my/preview" element={<PreviewSituationPage />} />
              <Route path="/case/:id" element={<CasePage />} />
              <Route path="/journal" element={<JournalPage />} />
              <Route path="/progress" element={<ProgressPage />} />
              <Route path="/guide" element={<HowItWorksPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/account" element={<AccountPage />} />
              <Route path="/pricing" element={<PricingPage signedIn />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/login" element={<Navigate to="/" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          )}
        </Routes>
      </main>
      <footer className="footer">Practice with realistic numbers. Do not enter confidential employer or client data. <Link to="/guide">How it works</Link> · <Link to="/account">Account and data</Link> · <Link to="/pricing">Pricing</Link></footer>
    </Ctx.Provider>
  );
}

function TopBar() {
  const { refresh } = useSession();
  const nav = useNavigate();
  const [due, setDue] = useState(0);
  const loc = useLocation();
  useEffect(() => {
    api<{ due: number }>('GET', '/reminders').then((r) => setDue(r.due)).catch(() => {});
  }, [loc.pathname]);
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="brand">Role<span>Shift</span></Link>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/journal" className={() => (/^\/(journal|documents)/.test(loc.pathname) ? 'active' : '')} aria-current={/^\/(journal|documents)/.test(loc.pathname) ? 'page' : undefined}>My cases{due > 0 && <span className="count" aria-label={`${due} follow-ups due`}>{due}</span>}</NavLink>
          <NavLink to="/progress">Progress</NavLink>
          <NavLink to="/guide" className="hide-sm">How it works</NavLink>
          <NavLink to="/account">Account</NavLink>
          <button onClick={async () => { await api('POST', '/auth/logout', {}); await refresh(); nav('/'); }}>Sign out</button>
        </nav>
      </div>
    </header>
  );
}
