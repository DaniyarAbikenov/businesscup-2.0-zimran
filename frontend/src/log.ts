// Client-side logging. Every event goes to the browser console (open DevTools to read it) and is sent in
// small batches to POST /api/client-log, so errors seen by a user also show up in `docker compose logs backend`.
// Never log form contents, passwords or document text: only event names, ids, statuses and timings.
type Level = 'debug' | 'info' | 'warn' | 'error';
interface Entry { level: Level; event: string; message: string; meta: Record<string, unknown>; at: string; path: string }

const queue: Entry[] = [];
let timer: number | undefined;
const history: Entry[] = [];
export const recentLogs = () => history.slice();

function flush() {
  timer = undefined;
  if (!queue.length) return;
  const events = queue.splice(0, 20);
  fetch('/api/client-log', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ events }), keepalive: true,
  }).catch(() => { /* logging must never break the app */ });
  if (queue.length) timer = window.setTimeout(flush, 500);
}

function emit(level: Level, event: string, message = '', meta: Record<string, unknown> = {}) {
  const entry: Entry = { level, event, message: String(message).slice(0, 500), meta, at: new Date().toISOString(), path: location.pathname };
  history.push(entry);
  if (history.length > 100) history.shift();
  const fn = level === 'debug' ? console.debug : level === 'info' ? console.info : level === 'warn' ? console.warn : console.error;
  fn(`[roleshift] ${event}${message ? ' - ' + message : ''}`, meta);
  if (level === 'debug') return; // debug stays in the console
  queue.push(entry);
  if (level === 'error') { flush(); return; }
  timer ??= window.setTimeout(flush, 1500);
}

export const log = {
  debug: (e: string, m?: string, meta?: Record<string, unknown>) => emit('debug', e, m, meta),
  info: (e: string, m?: string, meta?: Record<string, unknown>) => emit('info', e, m, meta),
  warn: (e: string, m?: string, meta?: Record<string, unknown>) => emit('warn', e, m, meta),
  error: (e: string, m?: string, meta?: Record<string, unknown>) => emit('error', e, m, meta),
};

export function installGlobalHandlers() {
  window.addEventListener('error', (ev) => log.error('window.error', ev.message, { file: ev.filename, line: ev.lineno }));
  window.addEventListener('unhandledrejection', (ev) => log.error('unhandled.rejection', String((ev.reason as Error)?.message ?? ev.reason)));
  window.addEventListener('pagehide', flush);
}
