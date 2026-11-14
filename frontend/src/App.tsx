import { t } from './i18n';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Me, Pack, api } from './api';
import { adopt, getLang } from './i18n';
import { TourProvider, useTour } from './tour/TourHost';
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
      const me = await api<Me>('GET', '/me');
      const saved = me.profile?.language;
      if (saved && saved !== getLang()) { adopt(saved); window.location.reload(); return; } // the account's language wins
      const pack = await api<Pack>('GET', '/packs');
      setState({ me, pack, loading: false });
    } catch {
      setState({ me: null, pack: null, loading: false });
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  if (state.loading) return <main className="page"><p className="muted">{t('Loading')}</p></main>;
  if (!state.me || !state.pack) return <Routes><Route path="/pricing" element={<main className="page"><PricingPage signedIn={false} /></main>} /><Route path="/register" element={<Auth mode="register" onDone={refresh} />} /><Route path="*" element={<Auth mode="login" onDone={refresh} />} /></Routes>;
  const session = { me: state.me, pack: state.pack, refresh };
  const needsProfile = !state.me.profile;

  return (
    <Ctx.Provider value={session}>
      <TourProvider>
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
      <footer className="footer">{t('Practice with realistic numbers. Do not enter confidential employer or client data.')} <Link to="/guide">{t('How it works')}</Link> · <Link to="/account">{t('Account and data')}</Link> · <Link to="/pricing">{t('Pricing')}</Link></footer>
      </TourProvider>
    </Ctx.Provider>
  );
}

function TopBar() {
  const { refresh } = useSession();
  const nav = useNavigate();
  const [due, setDue] = useState(0);
  const loc = useLocation();
  const tour = useTour();
  useEffect(() => {
    api<{ due: number }>('GET', '/reminders').then((r) => setDue(r.due)).catch(() => {});
  }, [loc.pathname]);
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="brand">Role<span>{t('Shift')}</span></Link>
        <nav className="nav" aria-label={t('Main')}>
          <NavLink to="/" end>{t('Home')}</NavLink>
          <NavLink to="/journal" className={() => (/^\/(journal|documents)/.test(loc.pathname) ? 'active' : '')} aria-current={/^\/(journal|documents)/.test(loc.pathname) ? 'page' : undefined}>{t('My cases')}{due > 0 && <span className="count" aria-label={t('{due} follow-ups due', { due: due })}>{due}</span>}</NavLink>
          <NavLink to="/progress" data-tour="nav-progress">{t('Progress')}</NavLink>
          <NavLink to="/guide" className="hide-sm">{t('How it works')}</NavLink>
          <NavLink to="/account">{t('Account')}</NavLink>
          <button type="button" className="tourbtn" onClick={tour.replay} aria-label={t('Show the tour for this page')} title={t('Show the tour for this page')}>?</button>
          <button onClick={async () => { await api('POST', '/auth/logout', {}); await refresh(); nav('/'); }}>{t('Sign out')}</button>
        </nav>
      </div>
    </header>
  );
}
