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
  const res = await fetch('/api' + path, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || 'Request failed', res.status, data.fields);
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
export interface Me { user: { id: number; email: string }; profile: Profile | null; llmEnabled: boolean }
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
