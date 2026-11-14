import { getLang, locale } from './i18n';
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
      headers: { 'content-type': 'application/json', 'x-request-id': rid, 'x-lang': getLang() },
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
  id: string; group?: string; type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'list';
  fields?: Question[]; minRows?: number; maxRows?: number; itemLabel?: string;
  label: string; help?: string; required?: boolean; placeholder?: string; max?: number; min?: number; step?: number;
  default?: string | number; options?: { value: string; label: string }[];
  why?: string;
  labelFrom?: { list: string; field: string; index: number; template: string };
}
export interface Storyline { id: string; title: string; story: string; answers: Record<string, any> }
export interface Situation {
  id: string; engine: 'change_request' | 'priorities' | 'estimate' | 'decision'; aiMade?: boolean; category?: string; title: string; summary: string; applies_to: string[]; questions: Question[];
  titleField?: string; documentName?: string; storylines?: Storyline[];
  groups?: { id: string; title: string; columns?: number; collapsed?: boolean }[];
  options: Record<string, { label: string; nextSteps: string[] }>;
  reflectionPrompts: { id: string; label: string }[]; pitfalls: string[];
}
export interface Pack {
  roles: { id: string; label: string; terms: Record<string, string> }[];
  tenures: { id: string; label: string }[];
  fears: { id: string; label: string }[];
  situations: Situation[];
}
export interface Profile { roleId: string; industry: string; tenure: string; fears: string[]; fearNote: string; emailReminders?: boolean; language?: string | null }
export interface Me { user: { id: number; email: string }; profile: Profile | null; llmEnabled: boolean; isDemo: boolean }
export interface ScheduledTask { index: number; name: string; finish: string; deadline: string; lateDays: number; requester: string; impact: string }
export interface Option {
  key: string; pick?: string; score?: number; rank?: number; date?: string; dateFrom?: string | null; recheckDate?: string | null; workdays?: number; hours?: number; probability?: number; lateDays?: number; sameAs?: string[]; schedule?: ScheduledTask[]; lateCount?: number; totalLateDays?: number; riskLevel: 'low' | 'medium' | 'high'; riskScore: number;
  newReleaseDate: string; slipWorkdays: number; extraCost: number; budgetAfter: number; laterCost?: number;
  costBreakdown?: { labor: number; extendedRun: number; delayPenalty: number; clientCovers: number };
  risks: { severity: number; text: string }[];
}
export interface Case {
  id: number; situationId: string; title: string; inputs: Record<string, any>; confidenceBefore: number;
  status: 'draft' | 'decided'; chosenOption: string | null; document: string | null; followupDue: string | null;
  result: { headline?: string; fits?: boolean; workdaysToRelease: number; addedWorkdays: number; assumptions: string; lowestRiskKey: string; options: Option[] };
  reflection: { learned: string; different: string; confidenceAfter: number } | null;
  followup: { outcome: string; notes: string } | null;
  documentUpdatedAt?: string | null; documentRevisions?: number; clientMessage?: string | null;
  debrief?: { points: string[]; pitfalls: string[]; nextSteps: string[] };
}
export interface Journal {
  entries: { id: number; case_id: number | null; type: string; text: string; created_at: string }[];
  cases: { id: number; title: string; status: string; followupDone: boolean }[];
  followups: { caseId: number; title: string; due: string; overdue: boolean }[];
  stats: { exported?: number; started: number; decided: number; followedUp: number; reportedWorked: number; confidenceChange: number | null };
}

export const usd = (n: number) => (n < 0 ? '-$' : '$') + Math.abs(Math.round(n)).toLocaleString(locale());
export const fmtDate = (s: string) => new Date(s + 'T00:00:00Z').toLocaleDateString(locale(), { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
export const fmtStamp = (s: string) => new Date(s).toLocaleDateString(locale(), { month: 'short', day: 'numeric' });

export interface SavedDoc {
  id: number; caseId: number; kind: 'change_request' | 'client_message'; label: string; caseTitle: string; body: string;
  revisions: number; createdAt: string; updatedAt: string;
}

export interface Pricing {
  free: { name: string; priceCents: number; cases: number; features: string[] };
  pass: { id: string; name: string; priceCents: number; days: number; billing: string; features: string[] };
  testCheckout: boolean;
}
export interface Billing { plan: 'free' | 'pass'; used: number; limit: number | null; remaining: number | null; pass: { expiresAt: string; provider: string } | null }
export const price = (cents: number) => '$' + (cents / 100).toFixed(cents % 100 ? 2 : 0);

export interface Intake {
  situationId: string; answers: Record<string, any>; filled: string[]; missing: string[]; notes: string[];
  source: 'ai' | 'keywords'; alternatives: string[]; noMatch?: boolean;
}
export interface Draft { preset: Record<string, any>; situation: Situation }

export interface Progress {
  startedAt: string; day: number; windowDays: number; inWindow: boolean; milestones: number[];
  confidence: { caseId: number; title: string; date: string; before: number; after: number | null }[]; averageChange: number | null;
  timeline: { caseId: number; date: string; title: string; situation: string; category: string; chosen: string | null; status: string; statusLabel: string; outcome: string | null; outcomeLabel: string | null }[];
  counts: { situations: number; decisions: number; followups: number; documents: number; exported: number };
  practiced: { category: string; situations: { title: string; count: number }[] }[];
  outcomes: Record<string, number>; outcomesTotal: number;
  firsts: { situation: string | null; decision: string | null; debrief: string | null };
  inactiveDays: number | null; inactiveHint: boolean; tryNext: { id: string; title: string; summary: string } | null;
  emailReminders: boolean; logMailer: boolean;
}
