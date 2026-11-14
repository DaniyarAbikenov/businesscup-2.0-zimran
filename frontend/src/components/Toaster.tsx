import { Component, ReactNode, useEffect, useState } from 'react';
import { log } from '../log';

// One global toast stack. Call notify() from anywhere (after a save, on a network failure).
type Kind = 'ok' | 'bad';
interface Toast { id: number; msg: string; kind: Kind }
let seq = 0;
const listeners = new Set<(t: Toast) => void>();

export function notify(msg: string, kind: Kind = 'ok') {
  log.info('ui.toast', msg, { kind });
  listeners.forEach((l) => l({ id: ++seq, msg, kind }));
}

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => {
    const on = (t: Toast) => {
      setItems((cur) => [...cur.slice(-2), t]);
      window.setTimeout(() => setItems((cur) => cur.filter((x) => x.id !== t.id)), t.kind === 'bad' ? 6000 : 3500);
    };
    listeners.add(on);
    return () => { listeners.delete(on); };
  }, []);
  return (
    <div className="toasts" aria-live="polite">
      {items.map((t) => <div key={t.id} className={'toast ' + t.kind} role={t.kind === 'bad' ? 'alert' : 'status'}>{t.msg}</div>)}
    </div>
  );
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    log.error('react.crash', error.message, { stack: (info.componentStack ?? '').slice(0, 600) });
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="page">
        <div className="banner bad" role="alert">Something broke on this screen. Your saved data is safe. The problem was reported.</div>
        <p><a href="/">Reload RoleShift</a></p>
      </main>
    );
  }
}
