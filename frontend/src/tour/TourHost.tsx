import { ReactNode, createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useSession } from '../App';
import { api } from '../api';
import { t } from '../i18n';
import { TOUR_KEYS, TourKey, TourStep, tours } from './steps';

interface Ctl { setScreen: (k: TourKey | null) => void; replay: () => void; resetAll: () => Promise<void>; screen: TourKey | null }
const Ctx = createContext<Ctl>({ setScreen: () => {}, replay: () => {}, resetAll: async () => {}, screen: null });
export const useTour = () => useContext(Ctx);

/** Put this on a screen to say which tour belongs to it. It starts once, the first time the screen is shown. */
export function TourScreen({ name }: { name: TourKey }) {
  const { setScreen } = useTour();
  useEffect(() => { setScreen(name); return () => setScreen(null); }, [name, setScreen]);
  return null;
}

const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const mobile = () => window.innerWidth <= 560;
const LOCAL = 'roleshift.tours';
const local = (): string[] => { try { return JSON.parse(localStorage.getItem(LOCAL) || '[]'); } catch { return []; } };

export function TourProvider({ children }: { children: ReactNode }) {
  const { me, refresh } = useSession();
  const demo = !!me.isDemo;
  const [screen, setScreenState] = useState<TourKey | null>(null);
  const [seen, setSeen] = useState<string[]>(demo ? [] : (me.profile?.toursSeen ?? local()));
  const [disabled, setDisabled] = useState<boolean>(!!me.profile?.toursDisabled);
  const [run, setRun] = useState<{ key: TourKey; steps: TourStep[]; i: number } | null>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [dontShow, setDontShow] = useState(false);
  const [dock, setDock] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<Element | null>(null);

  const present = useCallback((k: TourKey) => tours()[k].filter((s) => document.querySelector(s.target)), []);
  const save = useCallback((keys: string[]) => {
    try { localStorage.setItem(LOCAL, JSON.stringify([...new Set([...local(), ...keys])])); } catch { /* ignore */ }
    api('PUT', '/profile/tours', { seen: keys }).catch(() => {});
  }, []);

  const finish = useCallback((markDisable: boolean) => {
    setRun((r) => {
      if (r) { setSeen((s) => [...new Set([...s, r.key])]); save([r.key]); }
      return null;
    });
    if (markDisable) { setDisabled(true); api('PUT', '/profile/tours', { disable: true }).catch(() => {}); }
    document.querySelectorAll('.tour-hl').forEach((e) => e.classList.remove('tour-hl'));
    (returnFocus.current as HTMLElement | null)?.focus?.();
  }, [save]);

  const start = useCallback((k: TourKey) => {
    const steps = present(k);
    if (!steps.length) return;
    returnFocus.current = document.activeElement;
    setDontShow(false);
    setRun({ key: k, steps, i: 0 });
  }, [present]);

  // a screen appears: start its tour once
  useEffect(() => {
    if (!screen || disabled || seen.includes(screen) || run) return;
    const id = window.setTimeout(() => start(screen), 800);
    return () => window.clearTimeout(id);
  }, [screen, disabled, seen, run, start]);

  // the person moved to another screen mid-tour: end it and count it as seen
  useEffect(() => { if (run && screen !== run.key) finish(false); }, [screen]); // eslint-disable-line react-hooks/exhaustive-deps

  const step = run?.steps[run.i];
  useLayoutEffect(() => {
    if (!step) return;
    const el = document.querySelector(step.target) as HTMLElement | null;
    if (!el) { setRun((r) => (r && r.i < r.steps.length - 1 ? { ...r, i: r.i + 1 } : null)); return; }
    document.querySelectorAll('.tour-hl').forEach((e) => e.classList.remove('tour-hl'));
    el.classList.add('tour-hl');
    const behavior = reduced() ? 'auto' : 'smooth';
    const tall = el.getBoundingClientRect().height > window.innerHeight * 0.45;  // a big block: show its top and dock the tip at the bottom of the screen
    setDock(tall || mobile());
    if (tall || mobile()) window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - 80), behavior });
    else el.scrollIntoView({ block: 'center', behavior });
    const upd = () => setRect(el.getBoundingClientRect());
    upd();
    const tm = window.setTimeout(upd, 450);
    window.addEventListener('resize', upd); window.addEventListener('scroll', upd, true);
    popRef.current?.focus();
    return () => { window.clearTimeout(tm); window.removeEventListener('resize', upd); window.removeEventListener('scroll', upd, true); };
  }, [step, run?.i]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!run) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') finish(dontShow);
      else if (e.key === 'ArrowRight') setRun((r) => (r && r.i < r.steps.length - 1 ? { ...r, i: r.i + 1 } : r));
      else if (e.key === 'ArrowLeft') setRun((r) => (r && r.i > 0 ? { ...r, i: r.i - 1 } : r));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [run, finish, dontShow]);

  const setScreen = useCallback((k: TourKey | null) => setScreenState(k), []);
  const replay = useCallback(() => { if (screen) start(screen); }, [screen, start]);
  const resetAll = useCallback(async () => {
    await api('PUT', '/profile/tours', { reset: true });
    try { localStorage.removeItem(LOCAL); } catch { /* ignore */ }
    setSeen([]); setDisabled(false);
    await refresh();
  }, [refresh]);
  const ctl = useMemo(() => ({ setScreen, replay, resetAll, screen }), [setScreen, replay, resetAll, screen]);

  let pop: ReactNode = null;
  if (run && step && rect) {
    const last = run.i === run.steps.length - 1;
    const sheet = dock || mobile();
    const W = Math.min(340, window.innerWidth - 24);
    let style: React.CSSProperties;
    if (sheet) style = mobile() ? { left: 12, right: 12, bottom: 12, width: 'auto' } : { left: 12, bottom: 12, width: Math.min(420, window.innerWidth - 24) };
    else {
      const H = 200, gap = 12;
      const fitsBelow = rect.bottom + gap + H < window.innerHeight, fitsAbove = rect.top - gap - H > 0;
      const fitsRight = rect.right + gap + W < window.innerWidth;
      const left = Math.min(Math.max(12, rect.left), window.innerWidth - W - 12);
      if (fitsBelow) style = { top: rect.bottom + gap, left, width: W };
      else if (fitsAbove) style = { top: rect.top - gap - H, left, width: W };
      else if (fitsRight) style = { top: Math.max(12, rect.top), left: rect.right + gap, width: W };
      else style = { top: Math.max(12, Math.min(rect.top, window.innerHeight - H - 12)), left: 12, width: W };
    }
    pop = (
      <>
        <div className="tour-backdrop" onClick={() => finish(dontShow)} aria-hidden="true" />
        <div ref={popRef} className="tour" role="dialog" aria-modal="false" aria-labelledby="tour-title" aria-describedby="tour-text" tabIndex={-1} style={style}>
          <button type="button" className="tour-x" onClick={() => finish(dontShow)} aria-label={t('Close tips')}>×</button>
          <div className="small muted">{t('Step {n} of {total}', { n: run.i + 1, total: run.steps.length })}</div>
          <b id="tour-title">{step.title}</b>
          <p id="tour-text">{step.text}</p>
          <label className="check small"><input type="checkbox" checked={dontShow} onChange={(e) => setDontShow(e.target.checked)} /> {t('Do not show tours again')}</label>
          <div className="row">
            {run.i > 0 && <button type="button" className="btn btn-quiet" onClick={() => setRun({ ...run, i: run.i - 1 })}>{t('Back')}</button>}
            <button type="button" className="btn btn-primary" onClick={() => (last ? finish(dontShow) : setRun({ ...run, i: run.i + 1 }))}>{last ? t('Got it') : t('Next')}</button>
            {!last && <button type="button" className="btn btn-quiet" onClick={() => finish(dontShow)}>{t('Skip tour')}</button>}
          </div>
        </div>
      </>
    );
  }
  return <Ctx.Provider value={ctl}>{children}{pop}</Ctx.Provider>;
}

export { TOUR_KEYS };
