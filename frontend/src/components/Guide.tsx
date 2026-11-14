import { t } from '../i18n';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSession } from '../App';
import { Button, Panel } from './ui';
import { useTour } from '../tour/TourHost';

export const PROMISE = t('Facing a decision in a new role? Try your options with your own numbers before you commit, and get a ready message to send.');
export const STEPS: [string, string][] = [
  [t('Describe or pick'), t('Tell us what you are facing in your own words, or choose a ready scenario.')],
  [t('Compare options'), t('Enter your numbers. We calculate what each option would cost, delay or risk.')],
  [t('Decide and get a message'), t('Pick one. You get a short document you can send, with your reasoning.')],
  [t('Come back'), t('Later, record how it went. Your progress and lessons build up.')],
];

const KEY = 'roleshift.guide.done';
export const guideDone = (): boolean => { try { return localStorage.getItem(KEY) === '1'; } catch { return false; } };
export const setGuideDone = () => { try { localStorage.setItem(KEY, '1'); } catch { /* storage may be blocked: the guide just shows again */ } };

/** The worked example for a role: opens a scenario with its example filled in and goes straight to the result. */
export function exampleFor(roleId: string): { scenario: string; story: string } {
  return ['promoted-to-lead', 'head-of-function'].includes(roleId) ? { scenario: 'choose-between-options', story: 'hire' } : { scenario: 'competing-priorities', story: 'month1' };
}

export function StepsList() {
  return <ol className="guide-steps">{STEPS.map(([t, d], n) => <li key={t}><b>{n + 1}. {t}</b><span>{d}</span></li>)}</ol>;
}

export function ExampleButton({ label = t('Try a worked example') }: { label?: string }) {
  const { me } = useSession();
  const nav = useNavigate();
  const ex = exampleFor(me.profile?.roleId ?? '');
  return <Button onClick={() => { setGuideDone(); nav(`/new/${ex.scenario}`, { state: { example: ex.story } }); }}>{label}</Button>;
}

/** Short welcome, skippable, remembered in this browser. */
export function Welcome({ onClose }: { onClose: () => void }) {
  return (
    <Panel title={t('Welcome. Here is how this works')}>
      <StepsList />
      <p className="small muted" style={{ margin: '0 0 12px' }}>{t('The numbers are calculated by code, not guessed by AI. The example takes under a minute and uses made-up numbers.')}</p>
      <div className="row">
        <ExampleButton />
        <Button variant="secondary" onClick={() => { setGuideDone(); onClose(); }}>{t('Skip, I will explore')}</Button>
      </div>
    </Panel>
  );
}

export function HowItWorksPage() {
  const [, force] = useState(0);
  const tour = useTour();
  return (
    <div className="narrow">
      <header className="page-header"><div className="caption">{t('How it works')}</div><h1>{t('Test your options before you commit')}</h1><p className="lead">{PROMISE}</p></header>
      <Panel title={t('Four steps')}><StepsList /></Panel>
      <Panel title={t('Words we use')}>
        <ul className="plain">
          <li><b>{t('Scenario')}</b>: {t('a kind of moment at work, such as a late change request, several urgent asks, or a choice between options.')}</li>
          <li><b>{t('Example')}</b>: {t('a scenario with made-up numbers already filled in, so you can see the result in seconds.')}</li>
          <li><b>{t('Option')}</b>: {t('one thing you could do. Each has a risk label, which is a rule-of-thumb check, not a prediction.')}</li>
          <li><b>{t('Follow-up')}</b>: {t('a note to yourself about how it turned out. It is what you tell us; we cannot see your workplace.')}</li>
        </ul>
      </Panel>
      <div className="row"><ExampleButton /><Link className="btn btn-secondary" to="/" onClick={() => { force(1); tour.resetAll(); }}>{t('Start the tour')}</Link><Link className="btn btn-quiet" to="/">{t('Back to Home')}</Link></div>
    </div>
  );
}
