/** An unsaved form kept in the browser tab (sessionStorage), per scenario, so a reload or the Back button does not lose it.
 *  Every access is wrapped: with storage blocked or full, the form still works and just forgets. */
export interface Draft { answers: Record<string, any>; conf: string; step: number; storyId: string | null }
const key = (sitId: string) => `roleshift.draft.${sitId}`;

export function loadDraft(sitId: string): Draft | null {
  try {
    const raw = sessionStorage.getItem(key(sitId));
    if (!raw) return null;
    const d = JSON.parse(raw);
    return d && typeof d === 'object' && d.answers && typeof d.answers === 'object' ? { answers: d.answers, conf: String(d.conf ?? '3'), step: Number(d.step) || 0, storyId: d.storyId ?? null } : null;
  } catch { return null; }
}
export function saveDraft(sitId: string, d: Draft) { try { sessionStorage.setItem(key(sitId), JSON.stringify(d)); } catch { /* storage blocked or full */ } }
export function clearDraft(sitId: string) { try { sessionStorage.removeItem(key(sitId)); } catch { /* ignore */ } }
