import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { Me, Pack, api } from './api';
import Auth from './pages/Auth';
import CasePage from './pages/Case';
import Home from './pages/Home';
import JournalPage from './pages/Journal';
import NewCase from './pages/NewCase';
import Onboarding from './pages/Onboarding';

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
  if (!state.me || !state.pack) return <Routes><Route path="/register" element={<Auth mode="register" onDone={refresh} />} /><Route path="*" element={<Auth mode="login" onDone={refresh} />} /></Routes>;
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
              <Route path="/case/:id" element={<CasePage />} />
              <Route path="/journal" element={<JournalPage />} />
              <Route path="/login" element={<Navigate to="/" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          )}
        </Routes>
      </main>
      <footer className="footer">Practice with realistic numbers. Do not enter confidential employer or client data.</footer>
    </Ctx.Provider>
  );
}

function TopBar() {
  const { refresh } = useSession();
  const nav = useNavigate();
  const [due, setDue] = useState(0);
  useEffect(() => {
    api<{ due: number }>('GET', '/reminders').then((r) => setDue(r.due)).catch(() => {});
  }, [location.pathname]);
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="brand">Role<span>Shift</span></Link>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/journal">Journal{due > 0 && <span className="count" aria-label={`${due} follow-ups due`}>{due}</span>}</NavLink>
          <button onClick={async () => { await api('POST', '/auth/logout', {}); await refresh(); nav('/'); }}>Sign out</button>
        </nav>
      </div>
    </header>
  );
}
