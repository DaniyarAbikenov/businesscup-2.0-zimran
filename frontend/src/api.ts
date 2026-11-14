import { log } from './log';
import { notify } from './components/Toaster';

export class ApiError extends Error {
  status: number;
  fields?: Record<string, string>;
  constructor(message: string, status: number, fields?: Record<string, string>) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const rid = Math.random().toString(16).slice(2, 14);
  const t0 = performance.now();
  let res: Response;
  try {
    res = await fetch('/api' + path, {
      method,
      headers: { 'content-type': 'application/json', 'x-request-id': rid },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    log.error('api.network', `${method} ${path}`, { rid });
    notify('Cannot reach the server. Check your connection and try again.', 'bad');
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0);
  }
  const data = await res.json().catch(() => ({}));
  const meta = { rid, status: res.status, ms: Math.round(performance.now() - t0) };
  if (!res.ok) {
    // 401 on /me is the normal signed-out state, not a problem
    (res.status >= 500 ? log.error : res.status === 401 ? log.debug : log.warn)('api.fail', `${method} ${path}: ${data.error ?? ''}`, meta);
    if (res.status >= 500) notify(data.error || 'Something went wrong on our side. Try again.', 'bad');
    throw new ApiError(data.error || 'Request failed', res.status, data.fields);
  }
  log.debug('api.ok', `${method} ${path}`, meta);
  return data as T;
}

// ---- types (only what the UI reads) ----
export interface Question {
  id: string; group: string; type: 'text' | 'textarea' | 'number' | 'date' | 'select';
  label: string; help?: string; required?: boolean; placeholder?: string; max?: number; min?: number; step?: number;
  default?: string | number; options?: { value: string; label: string }[];
}
export interface Situation {
  id: string; title: string; summary: string; applies_to: string[]; questions: Question[];
  options: Record<string, { label: string; nextSteps: string[] }>;
  reflectionPrompts: { id: string; label: string }[];
}
export interface Pack {
  roles: { id: string; label: string; terms: Record<string, string> }[];
  tenures: { id: string; label: string }[];
  fears: { id: string; label: string }[];
  situations: Situation[];
}
export interface Profile { roleId: string; industry: string; tenure: string; fears: string[]; fearNote: string }
export interface Me { user: { id: number; email: string }; profile: Profile | null; llmEnabled: boolean; isDemo: boolean }
export interface Option {
  key: 'accept' | 'defer' | 'decline'; riskLevel: 'low' | 'medium' | 'high'; riskScore: number;
  newReleaseDate: string; slipWorkdays: number; extraCost: number; budgetAfter: number; laterCost?: number;
  costBreakdown?: { labor: number; extendedRun: number; delayPenalty: number; clientCovers: number };
  risks: { severity: number; text: string }[];
}
export interface Case {
  id: number; situationId: string; inputs: Record<string, any>; confidenceBefore: number;
  status: 'draft' | 'decided'; chosenOption: string | null; document: string | null; followupDue: string | null;
  result: { workdaysToRelease: number; addedWorkdays: number; assumptions: string; lowestRiskKey: string; options: Option[] };
  reflection: { learned: string; different: string; confidenceAfter: number } | null;
  followup: { outcome: string; notes: string } | null;
  debrief?: { points: string[]; pitfalls: string[]; nextSteps: string[] };
}
export interface Journal {
  entries: { id: number; case_id: number | null; type: string; text: string; created_at: string }[];
  cases: { id: number; title: string; status: string; followupDone: boolean }[];
  followups: { caseId: number; title: string; due: string; overdue: boolean }[];
  stats: { started: number; decided: number; followedUp: number; reportedWorked: number; confidenceChange: number | null };
}

export const usd = (n: number) => (n < 0 ? '-$' : '$') + Math.abs(Math.round(n)).toLocaleString('en-US');
export const fmtDate = (s: string) => new Date(s + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
export const fmtStamp = (s: string) => new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
